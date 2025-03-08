from fastapi import APIRouter, HTTPException, status, Body, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import logging
import json

from app.database.connection import get_database
from app.models.analysis import Analysis, AnalysisCreate, AnalysisResult
from app.utils.tasks import analyze_company_sec_filings
from app.utils.celery_app import ping as ping_task
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

@router.post("/test/ping", response_model=Dict[str, Any])
async def test_ping():
    """
    Test endpoint to check if Celery is working.
    This will send a simple ping task and return the task ID.
    """
    try:
        # Send a ping task
        result = ping_task.delay()
        logger.info(f"Ping task sent with ID: {result.id}")
        
        return {
            "status": "PENDING",
            "task_id": result.id,
            "message": "Ping task has been queued. Check celery worker logs."
        }
        
    except Exception as e:
        logger.error(f"Error sending ping task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending ping task: {str(e)}"
        )

@router.post("/test/analyze/{company_id}", response_model=Dict[str, Any])
async def test_analyze(company_id: str):
    """
    Test endpoint to directly trigger an analysis task for a company.
    This bypasses the database status checks and directly sends the task to Celery.
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(company_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid company ID format: {company_id}"
            )
            
        # Send the task directly to Celery
        logger.info(f"Directly sending analysis task for company ID: {company_id}")
        result = analyze_company_sec_filings.delay(company_id)
        task_id = result.id
        
        logger.info(f"Analysis task directly sent with ID: {task_id}")
        
        return {
            "status": "PENDING",
            "task_id": task_id,
            "message": "Analysis task has been queued directly. Check celery worker logs for progress."
        }
        
    except Exception as e:
        logger.error(f"Error directly sending analysis task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending analysis task: {str(e)}"
        )

@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(analysis_request: AnalysisCreate = Body(...)):
    """
    Create a new analysis request.
    This will trigger an asynchronous task to analyze SEC filings.
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
    
    # Create a status document to track the analysis
    status_doc = {
        "company_id": ObjectId(analysis_request.company_id),
        "status": "PENDING",
        "created_at": datetime.utcnow(),
        "filings_analyzed": analysis_request.filings_analyzed or ["8-K", "10-K", "10-Q"],
    }
    
    # Insert the status into the database
    result = await db.analysis_status.insert_one(status_doc)
    status_id = str(result.inserted_id)
    
    # Start the Celery task
    try:
        logger.info(f"Sending analysis task to Celery for company ID: {analysis_request.company_id}")
        task = analyze_company_sec_filings.delay(
            analysis_request.company_id, 
            analysis_request.filings_analyzed
        )
        
        # Update the status document with the task ID
        await db.analysis_status.update_one(
            {"_id": result.inserted_id},
            {"$set": {"task_id": task.id}}
        )
        
        logger.info(f"Analysis task started for company ID: {analysis_request.company_id}, Task ID: {task.id}")
        
        return {
            "status": "PENDING",
            "task_id": task.id,
            "status_id": status_id,
            "message": "Analysis task has been queued. Poll the status endpoint to check progress."
        }
    except Exception as e:
        logger.error(f"Error starting Celery task: {str(e)}")
        
        # Update status to error
        await db.analysis_status.update_one(
            {"_id": result.inserted_id},
            {"$set": {"status": "ERROR", "error": str(e)}}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting analysis task: {str(e)}"
        )

@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_analysis_status(task_id: str):
    """
    Get the status of an analysis task.
    """
    db = get_database()
    
    # Look up the task in the database
    status_doc = await db.analysis_status.find_one({"task_id": task_id})
    if status_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis task with ID {task_id} not found"
        )
    
    # Check if the task is complete and has an analysis ID
    analysis_id = status_doc.get("analysis_id")
    if analysis_id:
        analysis = await db.analyses.find_one({"_id": ObjectId(analysis_id)})
        return {
            "status": "COMPLETED",
            "task_id": task_id,
            "analysis_id": str(analysis_id),
            "analysis": analysis
        }
    
    # Otherwise, get the status from Celery
    task = analyze_company_sec_filings.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return {
            "status": "PENDING",
            "task_id": task_id,
            "message": "Task is pending execution"
        }
    elif task.state == 'STARTED':
        return {
            "status": "PROCESSING",
            "task_id": task_id,
            "message": "Task is being processed"
        }
    elif task.state == 'SUCCESS':
        # Task is complete but the status hasn't been updated yet
        analysis_id = task.result
        if analysis_id:
            # Update the status document
            await db.analysis_status.update_one(
                {"task_id": task_id},
                {"$set": {"status": "COMPLETED", "analysis_id": analysis_id}}
            )
            
            # Get the analysis
            analysis = await db.analyses.find_one({"_id": ObjectId(analysis_id)})
            return {
                "status": "COMPLETED",
                "task_id": task_id,
                "analysis_id": analysis_id,
                "analysis": analysis
            }
        
        return {
            "status": "COMPLETED",
            "task_id": task_id,
            "message": "Task completed but no analysis was created"
        }
    elif task.state == 'FAILURE':
        error = str(task.result) if task.result else "Unknown error"
        # Update the status document
        await db.analysis_status.update_one(
            {"task_id": task_id},
            {"$set": {"status": "FAILED", "error": error}}
        )
        
        return {
            "status": "FAILED",
            "task_id": task_id,
            "error": error
        }
    else:
        return {
            "status": task.state,
            "task_id": task_id
        }

@router.get("/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str):
    """
    Get a single analysis by ID.
    """
    db = get_database()
    
    # Check if the ID is a valid ObjectId
    if not ObjectId.is_valid(analysis_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis ID format: {analysis_id}"
        )
    
    analysis = await db.analyses.find_one({"_id": ObjectId(analysis_id)})
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found"
        )
    
    return analysis

@router.get("/company/{company_id}", response_model=List[Analysis])
async def get_analyses_by_company(company_id: str):
    """
    Get all analyses for a company.
    """
    db = get_database()
    
    # Check if the ID is a valid ObjectId
    if not ObjectId.is_valid(company_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company ID format: {company_id}"
        )
    
    # Check if the company exists
    company = await db.companies.find_one({"_id": ObjectId(company_id)})
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    # Get all analyses for the company
    analyses_cursor = db.analyses.find({"company_id": ObjectId(company_id)})
    analyses = await analyses_cursor.to_list(1000)
    
    # Convert ObjectId to string for all documents
    serialized_analyses = []
    for analysis in analyses:
        serialized_analysis = convert_objectid_to_str(analysis)
        if serialized_analysis:
            serialized_analyses.append(serialized_analysis)
    
    logger.info(f"Found {len(serialized_analyses)} analyses for company {company_id}")
    return serialized_analyses

@router.post("/direct/{company_id}", response_model=Dict[str, Any])
async def direct_analyze(company_id: str):
    """
    Perform a direct analysis without using Celery.
    This is a synchronous endpoint that will block until the analysis is complete.
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
    
    # Get company CIK
    cik = company.get("cik")
    if not cik:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with ID {company_id} does not have a CIK"
        )
    
    logger.info(f"Starting direct analysis for company: {company.get('name')} (CIK: {cik})")
    
    try:
        # Get the company filings text
        filing_types = ["8-K", "10-K", "10-Q"]
        filings_text = get_company_filings_text(cik, filing_types, lookback_days=365)
        
        if not filings_text:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No SEC filings found for company with ID {company_id}"
            )
        
        # Use LLM to analyze filings
        analysis_result = analyze_filings_with_llm(company.get('name'), filings_text)
        
        if not analysis_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error analyzing SEC filings with LLM for company with ID {company_id}"
            )
        
        # Create analysis document
        analysis_doc = {
            "company_id": ObjectId(company_id),
            "analysis_date": datetime.utcnow(),
            "filings_analyzed": list(filings_text.keys()),
            "analysis_result": analysis_result
        }
        
        # Insert analysis into the database
        result = await db.analyses.insert_one(analysis_doc)
        analysis_id = str(result.inserted_id)
        
        logger.info(f"Direct analysis completed for company ID: {company_id}, Analysis ID: {analysis_id}")
        
        # Return the created analysis
        created_analysis = await db.analyses.find_one({"_id": result.inserted_id})
        return created_analysis
        
    except Exception as e:
        logger.error(f"Error performing direct analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing analysis: {str(e)}"
        )

@router.post("/ticker/{company_id}", response_model=Dict[str, Any])
async def analyze_by_ticker(company_id: str):
    """
    Find CIK using ticker, update the company, and perform analysis.
    This endpoint:
    1. Gets the company's ticker from the database
    2. Searches for the CIK using the ticker
    3. Updates the company document with the CIK
    4. Performs analysis using the updated CIK
    
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
    
    # Now get the company filings and analyze them
    try:
        # Get ALL available filing types by passing None
        filings_text = get_company_filings_text(cik, filing_types=None, lookback_days=365)
        
        if not filings_text:
            # No filings found even after trying to get the most recent
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No SEC filings found for company {company.get('name')} (CIK: {cik}). The company may not have any filings or may not be publicly traded."
            )
        
        # Use LLM to analyze filings
        analysis_result = analyze_filings_with_llm(company.get('name'), filings_text)
        
        if not analysis_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error analyzing SEC filings with LLM for company with ID {company_id}"
            )
        
        # Create analysis document
        analysis_doc = {
            "company_id": ObjectId(company_id),
            "analysis_date": datetime.utcnow(),
            "filings_analyzed": list(filings_text.keys()),
            "analysis_result": analysis_result
        }
        
        # Insert analysis into the database
        result = await db.analyses.insert_one(analysis_doc)
        analysis_id = str(result.inserted_id)
        
        logger.info(f"Analysis completed for company ID: {company_id}, Analysis ID: {analysis_id}")
        
        # Return the created analysis with ObjectId converted to string
        created_analysis = await db.analyses.find_one({"_id": result.inserted_id})
        return convert_objectid_to_str(created_analysis)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error performing analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing analysis: {str(e)}"
        ) 