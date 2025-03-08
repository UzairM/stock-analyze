from fastapi import APIRouter, HTTPException, status, Body, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from typing import List, Optional, Dict, Any
from bson import ObjectId
from datetime import datetime
import logging

from app.database.connection import get_database
from app.models.analysis import Analysis, AnalysisCreate, AnalysisResult
from app.utils.tasks import analyze_company_sec_filings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analyses",
    tags=["analyses"],
    responses={404: {"description": "Not found"}},
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
    analyses = await db.analyses.find({"company_id": ObjectId(company_id)}).to_list(1000)
    
    return analyses 