from fastapi import APIRouter, HTTPException, status, Body, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import csv
import io
import logging
from datetime import datetime

from app.database.connection import get_database
from app.models.company import Company, CompanyCreate, CompanyUpdate

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[Company])
async def get_companies():
    """
    Get all companies from the database.
    """
    db = get_database()
    companies = await db.companies.find().to_list(1500)
    return companies

@router.get("/{company_id}", response_model=Company)
async def get_company(company_id: str):
    """
    Get a single company by ID.
    """
    db = get_database()
    
    # Check if the ID is a valid ObjectId
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
    
    return company

@router.get("/ticker/{ticker}", response_model=Company)
async def get_company_by_ticker(ticker: str):
    """
    Get a single company by ticker symbol.
    """
    db = get_database()
    
    company = await db.companies.find_one({"ticker": ticker})
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker {ticker} not found"
        )
    
    return company

@router.post("/", response_model=Company, status_code=status.HTTP_201_CREATED)
async def create_company(company: CompanyCreate = Body(...)):
    """
    Create a new company in the database.
    """
    db = get_database()
    
    # Check if company with the same ticker already exists
    existing_company = await db.companies.find_one({"ticker": company.ticker})
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company with ticker {company.ticker} already exists"
        )
    
    # Convert the company model to a dict
    company_dict = jsonable_encoder(company)
    
    # Add created_at and updated_at fields
    from datetime import datetime
    now = datetime.utcnow()
    company_dict["created_at"] = now
    company_dict["updated_at"] = now
    
    # Insert the company into the database
    result = await db.companies.insert_one(company_dict)
    
    # Get the created company
    created_company = await db.companies.find_one({"_id": result.inserted_id})
    
    return created_company

@router.put("/{company_id}", response_model=Company)
async def update_company(company_id: str, company_update: CompanyUpdate = Body(...)):
    """
    Update a company in the database.
    """
    db = get_database()
    
    # Check if the ID is a valid ObjectId
    if not ObjectId.is_valid(company_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company ID format: {company_id}"
        )
    
    # Check if the company exists
    existing_company = await db.companies.find_one({"_id": ObjectId(company_id)})
    if existing_company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    # Convert the update model to a dict, excluding unset fields
    update_data = {k: v for k, v in company_update.dict(exclude_unset=True).items() if v is not None}
    
    # Add updated_at field
    from datetime import datetime
    update_data["updated_at"] = datetime.utcnow()
    
    # Update the company in the database
    await db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": update_data}
    )
    
    # Get the updated company
    updated_company = await db.companies.find_one({"_id": ObjectId(company_id)})
    
    return updated_company

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: str):
    """
    Delete a company from the database.
    """
    db = get_database()
    
    # Check if the ID is a valid ObjectId
    if not ObjectId.is_valid(company_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid company ID format: {company_id}"
        )
    
    # Delete the company
    result = await db.companies.delete_one({"_id": ObjectId(company_id)})
    
    # Check if the company was found and deleted
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found"
        )
    
    return None

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_companies_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file containing company data.
    """
    db = get_database()
    
    logger.info(f"Received CSV upload: {file.filename}")
    
    if not file.filename.endswith('.csv'):
        logger.error(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    # Read the CSV file
    contents = await file.read()
    
    # Decode the CSV file
    try:
        csv_text = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        # Process each row
        companies_added = 0
        companies_updated = 0
        errors = []
        
        # Log CSV headers
        logger.info(f"CSV headers: {csv_reader.fieldnames}")
        
        for row in csv_reader:
            try:
                # Clean up the row data
                company_data = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items() if k}
                
                # Log the company data
                logger.info(f"Processing company data: {company_data}")
                
                # Check for required fields
                if not company_data.get('ticker') or not company_data.get('name'):
                    error_msg = f"Row missing required fields (ticker, name): {company_data}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Convert numeric fields
                for field in ['market_cap', 'employees', 'totalRevenue', 'grossProfits', 
                             'ebitda', 'operatingMargins', 'returnOnAssets', 'returnOnEquity',
                             'currentPrice', 'targetHighPrice', 'targetLowPrice', 
                             'targetMeanPrice', 'recommendationMean']:
                    if field in company_data and company_data[field]:
                        try:
                            company_data[field] = float(company_data[field])
                        except ValueError:
                            logger.warning(f"Could not convert {field} to float: {company_data[field]}")
                            company_data[field] = None
                
                # Check if company already exists
                existing_company = await db.companies.find_one({"ticker": company_data['ticker']})
                
                if existing_company:
                    # Update existing company
                    logger.info(f"Updating company {company_data['ticker']}")
                    company_data['updated_at'] = datetime.utcnow()
                    await db.companies.update_one(
                        {"_id": existing_company["_id"]},
                        {"$set": company_data}
                    )
                    companies_updated += 1
                else:
                    # Add created_at and updated_at fields
                    logger.info(f"Adding new company {company_data['ticker']}")
                    now = datetime.utcnow()
                    company_data['created_at'] = now
                    company_data['updated_at'] = now
                    
                    # Insert new company
                    result = await db.companies.insert_one(company_data)
                    logger.info(f"Inserted company with ID: {result.inserted_id}")
                    companies_added += 1
                    
            except Exception as e:
                error_msg = f"Error processing row: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"CSV processing complete: {companies_added} added, {companies_updated} updated, {len(errors)} errors")
        
        return {
            "message": "CSV processed successfully",
            "companies_added": companies_added,
            "companies_updated": companies_updated,
            "errors": errors
        }
        
    except Exception as e:
        error_msg = f"Error processing CSV: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        ) 