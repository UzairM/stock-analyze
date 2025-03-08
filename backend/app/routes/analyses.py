from fastapi import APIRouter, HTTPException, status, Body, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import logging
import json

from app.database.connection import get_database
from app.models.analysis import Analysis, AnalysisCreate, AnalysisResult
from app.utils.sec_edgar import get_company_filings_text, get_cik_from_ticker
from app.utils.llm import analyze_filings_with_llm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function to convert ObjectId to string in MongoDB documents
def convert_objectid_to_str(doc):
    if not doc:
        return None
    doc_copy = dict(doc)
    if '_id' in doc_copy:
        doc_copy['_id'] = str(doc_copy['_id'])
    if 'company_id' in doc_copy:
        doc_copy['company_id'] = str(doc_copy['company_id'])
    return doc_copy

router = APIRouter(
    prefix="/analyses",
    tags=["analyses"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(analysis_request: AnalysisCreate = Body(...), background_tasks: BackgroundTasks = None):
    """
    Create a new analysis request.
    This will trigger a background task to analyze SEC filings.
    """
    db = get_database()
    
    # Check if the company exists
    if not ObjectId.is_valid(analysis_request.company_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company ID format: {analysis_request.company_id}"
        )
    
    company = await db.companies.find_one({"_id": ObjectId(analysis_request.company_id)})
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {analysis_request.company_id} not found"
        )
    
    # Create a placeholder analysis document
    placeholder_analysis = {
        "company_id": ObjectId(analysis_request.company_id),
        "analysis_date": datetime.utcnow(),
        "filings_analyzed": analysis_request.filings_analyzed or ["8-K", "10-K", "10-Q"],
        "analysis_result": {
            "stock_expected_to_go_up": None,
            "is_good_buy": None,
            "reasoning": "Analysis in progress...",
        },
        "status": "in_progress"
    }
    
    # Insert the placeholder into the database
    result = await db.analyses.insert_one(placeholder_analysis)
    analysis_id = str(result.inserted_id)
    
    # Return the placeholder immediately
    created_analysis = await db.analyses.find_one({"_id": result.inserted_id})
    response_data = convert_objectid_to_str(created_analysis)
    
    # Start the analysis task if background_tasks is provided
    if background_tasks:
        # Define the background task
        async def perform_analysis_task():
            try:
                logger.info(f"Starting background analysis for company ID: {analysis_request.company_id}")
                
                # Get filings text 
                company = await db.companies.find_one({"_id": ObjectId(analysis_request.company_id)})
                if not company.get("cik"):
                    logger.error(f"Company with ID {analysis_request.company_id} does not have a CIK")
                    await db.analyses.update_one(
                        {"_id": result.inserted_id},
                        {"$set": {
                            "analysis_result.reasoning": "Company does not have a CIK. Cannot analyze SEC filings.",
                            "status": "failed"
                        }}
                    )
                    return
                
                # Get filings text
                filings_text = get_company_filings_text(
                    company.get("cik"), 
                    analysis_request.filings_analyzed
                )
                
                if not filings_text:
                    logger.error(f"No SEC filings found for company ID {analysis_request.company_id}")
                    await db.analyses.update_one(
                        {"_id": result.inserted_id},
                        {"$set": {
                            "analysis_result.reasoning": "No SEC filings found for this company.",
                            "status": "failed"
                        }}
                    )
                    return
                
                # Analyze filings with LLM
                analysis_result = analyze_filings_with_llm(company.get('name'), filings_text)
                
                if not analysis_result:
                    logger.error(f"Error analyzing SEC filings with LLM for company ID {analysis_request.company_id}")
                    await db.analyses.update_one(
                        {"_id": result.inserted_id},
                        {"$set": {
                            "analysis_result.reasoning": "Error analyzing SEC filings with LLM.",
                            "status": "failed"
                        }}
                    )
                    return
                
                # Update analysis with result
                await db.analyses.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {
                        "filings_analyzed": list(filings_text.keys()),
                        "analysis_result": analysis_result,
                        "status": "completed"
                    }}
                )
                
                logger.info(f"Analysis completed for company ID: {analysis_request.company_id}, Analysis ID: {analysis_id}")
                
            except Exception as e:
                logger.error(f"Error performing analysis: {str(e)}")
                await db.analyses.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {
                        "analysis_result.reasoning": f"Error during analysis: {str(e)}",
                        "status": "failed"
                    }}
                )
        
        # Add the task to background tasks
        background_tasks.add_task(perform_analysis_task)
        response_data["message"] = "Analysis started in the background."
    else:
        response_data["message"] = "Analysis request created but not started. No background tasks provided."
    
    return response_data

@router.get("/{analysis_id}", response_model=Dict[str, Any])
async def get_analysis(analysis_id: str):
    """
    Get a specific analysis by ID.
    This will return the complete analysis, including status information.
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(analysis_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis ID format: {analysis_id}"
        )
    
    # Get the analysis
    analysis = await db.analyses.find_one({"_id": ObjectId(analysis_id)})
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found"
        )
    
    # Convert ObjectId to string
    result = convert_objectid_to_str(analysis)
    
    return result

@router.get("/company/{company_id}", response_model=List[Analysis])
async def get_analyses_by_company(company_id: str):
    """
    Get all analyses for a specific company.
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(company_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company ID format: {company_id}"
        )
    
    # Get analyses for the company, sorted by date (most recent first)
    analyses = await db.analyses.find(
        {"company_id": ObjectId(company_id)}
    ).sort("analysis_date", -1).to_list(None)
    
    # Convert ObjectId to string
    for analysis in analyses:
        analysis["_id"] = str(analysis["_id"])
        analysis["company_id"] = str(analysis["company_id"])
    
    return analyses

@router.post("/ticker/{company_id}", response_model=Dict[str, Any])
async def analyze_by_ticker(company_id: str, background_tasks: BackgroundTasks):
    """
    Find CIK using ticker, update the company, and perform analysis.
    This endpoint:
    1. Gets the company's ticker from the database
    2. Searches for the CIK using the ticker
    3. Updates the company document with the CIK
    4. Performs analysis using the updated CIK in a background task
    
    This endpoint retrieves ALL available filing types from the SEC.
    If no filings are found in the past year, it will attempt to retrieve 
    the 10 most recent filings regardless of date.
    """
    db = get_database()
    
    # Check if the company exists
    if not ObjectId.is_valid(company_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company ID format: {company_id}"
        )
    
    company = await db.companies.find_one({"_id": ObjectId(company_id)})
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    # Get ticker symbol
    ticker = company.get("ticker")
    if not ticker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with ID {company_id} does not have a ticker symbol"
        )
    
    logger.info(f"Looking up CIK for company {company.get('name')} (Ticker: {ticker})")
    
    # Search for CIK using ticker
    cik = get_cik_from_ticker(ticker)
    if not cik:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find CIK for ticker {ticker}"
        )
    
    logger.info(f"Found CIK {cik} for {company.get('name')} (Ticker: {ticker})")
    
    # Update company with CIK
    update_result = await db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {"cik": cik}}
    )
    
    if update_result.modified_count == 0:
        logger.warning(f"Failed to update CIK for company {company_id}")
    else:
        logger.info(f"Updated CIK to {cik} for company {company.get('name')}")
    
    # Create a placeholder analysis document
    placeholder_analysis = {
        "company_id": ObjectId(company_id),
        "analysis_date": datetime.utcnow(),
        "filings_analyzed": [],
        "analysis_result": {
            "stock_expected_to_go_up": None,
            "is_good_buy": None,
            "reasoning": "Analysis in progress...",
        },
        "status": "in_progress"
    }
    
    # Insert the placeholder into the database
    placeholder_result = await db.analyses.insert_one(placeholder_analysis)
    analysis_id = str(placeholder_result.inserted_id)
    
    # Return the placeholder immediately
    created_analysis = await db.analyses.find_one({"_id": placeholder_result.inserted_id})
    response_data = convert_objectid_to_str(created_analysis)
    
    # Schedule the actual analysis to run in the background
    async def perform_analysis_task():
        try:
            logger.info(f"Starting background analysis for company {company.get('name')} (CIK: {cik})")
            
            # Get ALL available filing types by passing None
            filings_text = get_company_filings_text(cik, filing_types=None, lookback_days=365)
            
            if not filings_text:
                # No filings found even after trying to get the most recent
                logger.error(f"No SEC filings found for company {company.get('name')} (CIK: {cik})")
                await db.analyses.update_one(
                    {"_id": placeholder_result.inserted_id},
                    {"$set": {
                        "analysis_result.reasoning": "No SEC filings found for this company.",
                        "status": "completed"
                    }}
                )
                return
            
            # Use LLM to analyze filings
            analysis_result = analyze_filings_with_llm(company.get('name'), filings_text)
            
            if not analysis_result:
                logger.error(f"Error analyzing SEC filings with LLM for company with ID {company_id}")
                await db.analyses.update_one(
                    {"_id": placeholder_result.inserted_id},
                    {"$set": {
                        "analysis_result.reasoning": "Error analyzing SEC filings with LLM.",
                        "status": "failed"
                    }}
                )
                return
            
            # Update the placeholder analysis with the real results
            await db.analyses.update_one(
                {"_id": placeholder_result.inserted_id},
                {"$set": {
                    "filings_analyzed": list(filings_text.keys()),
                    "analysis_result": analysis_result,
                    "status": "completed"
                }}
            )
            
            logger.info(f"Analysis completed for company ID: {company_id}, Analysis ID: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error in background analysis task: {str(e)}")
            await db.analyses.update_one(
                {"_id": placeholder_result.inserted_id},
                {"$set": {
                    "analysis_result.reasoning": f"Error during analysis: {str(e)}",
                    "status": "failed"
                }}
            )
    
    # Add the task to the background tasks
    background_tasks.add_task(perform_analysis_task)
    
    # Add a status message indicating that the analysis is running in the background
    response_data["message"] = "Analysis started in the background. Use the progress endpoint to track status."
    return response_data

@router.get("/simple-test", response_model=Dict[str, Any])
async def simple_test():
    """
    A simple test endpoint that returns static data without any dependencies.
    Used to verify basic server connectivity.
    """
    logger.info("Simple test endpoint called")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "This is a static test response",
        "test_data": {
            "company_name": "Test Company",
            "filing_type": "10-K",
            "filing_date": "2023-01-01"
        }
    } 