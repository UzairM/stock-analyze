#!/usr/bin/env python
"""
Script to update a company's CIK in the database.
"""
import sys
import logging
from pymongo import MongoClient
from bson import ObjectId

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://mongodb:27017')
db = client['biotech_analysis_db']

# Get company with ID
company_id = "67cc7e566dafa718ca3c4ed6"  # The company ID from previous output
company = db.companies.find_one({"_id": ObjectId(company_id)})

if company:
    logger.info(f"Found company: {company.get('name')} with ticker: {company.get('ticker')}")
    
    # CureVac N.V. CIK
    # For demonstration, set a valid CIK - this is CureVac's actual CIK
    cik = "0001809122"
    
    # Update the company with CIK
    result = db.companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": {"cik": cik}}
    )
    
    if result.modified_count > 0:
        logger.info(f"Successfully updated CIK to {cik} for company {company.get('name')}")
    else:
        logger.error(f"Failed to update CIK for company {company.get('name')}")
else:
    logger.error(f"Company with ID {company_id} not found")

client.close() 