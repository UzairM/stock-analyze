from fastapi import APIRouter, HTTPException, status, Body, File, UploadFile, Depends
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import csv
import io
import logging
from datetime import datetime, date
from pydantic import BaseModel

from app.database.connection import get_database
from app.models.company import Company, CompanyCreate, CompanyUpdate

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    responses={404: {"description": "Not found"}},
)

# Define a response model for the CSV upload endpoint
class CSVUploadResponse(BaseModel):
    status: str
    companies_added: int
    companies_updated: int
    errors: List[str]
    message: str

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

@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=CSVUploadResponse)
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
    
    # Decode the CSV file and handle BOM character
    try:
        # Check for BOM and remove it if present
        if contents.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
            logger.info("BOM detected in CSV file, removing it")
            contents = contents[3:]
            
        # Decode with standard UTF-8 since we manually handled the BOM
        csv_text = contents.decode('utf-8')
        
        # Print raw CSV for debugging
        logger.debug(f"Raw CSV content (first 200 chars): {csv_text[:200]}")
        
        # Create StringIO buffer for CSV reader
        csv_buffer = io.StringIO(csv_text)
        
        # Read the first line to get headers
        header_line = csv_buffer.readline().strip()
        logger.info(f"Header line: {header_line}")
        
        # Reset buffer position
        csv_buffer.seek(0)
        
        # Create CSV reader
        csv_reader = csv.DictReader(csv_buffer)
        
        # Get and fix fieldnames
        fieldnames = csv_reader.fieldnames
        if fieldnames and fieldnames[0].startswith('\ufeff'):
            logger.info(f"Found BOM in first fieldname: {repr(fieldnames[0])}")
            fieldnames[0] = fieldnames[0].replace('\ufeff', '')
            # Create a new reader with fixed fieldnames
            csv_buffer.seek(0)
            next(csv_buffer)  # Skip header
            csv_reader = csv.DictReader(csv_buffer, fieldnames=fieldnames)
        
        # Process each row
        companies_added = 0
        companies_updated = 0
        errors = []
        
        # Log CSV headers
        logger.info(f"CSV headers after cleaning: {fieldnames}")
        
        for idx, row in enumerate(csv_reader):
            try:
                # Print raw row for debugging
                logger.debug(f"Raw row {idx}: {row}")
                
                # Create clean row
                company_data = {}
                
                # Process each key-value pair
                for key, value in row.items():
                    if not key:
                        continue
                        
                    # Clean BOM from keys
                    clean_key = key.replace('\ufeff', '')
                    
                    # Clean and convert values
                    if isinstance(value, str):
                        clean_value = value.strip()
                    else:
                        clean_value = value
                        
                    company_data[clean_key] = clean_value
                
                # Log the company data for debugging
                logger.info(f"Processing row {idx}, ticker: {company_data.get('ticker')}, name: {company_data.get('name')}")
                
                # Check for required fields
                if 'ticker' not in company_data or not company_data.get('ticker'):
                    error_msg = f"Row {idx} missing ticker field. Keys: {list(company_data.keys())}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
                    
                if 'name' not in company_data or not company_data.get('name'):
                    error_msg = f"Row {idx} missing name field. Keys: {list(company_data.keys())}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Convert numeric fields
                for field in ['market_cap', 'employees', 'totalRevenue', 'grossProfits', 
                             'ebitda', 'operatingMargins', 'returnOnAssets', 'returnOnEquity',
                             'currentPrice', 'targetHighPrice', 'targetLowPrice', 
                             'targetMeanPrice', 'recommendationMean']:
                    if field in company_data:
                        # Check if the value is an empty string or None
                        if not company_data[field] or company_data[field] == '':
                            company_data[field] = None
                        else:
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
                error_msg = f"Error processing row {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "status": "success",
            "companies_added": companies_added,
            "companies_updated": companies_updated,
            "errors": errors,
            "message": "CSV processed successfully",
        }
        
    except Exception as e:
        error_msg = f"Error processing CSV: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        ) 