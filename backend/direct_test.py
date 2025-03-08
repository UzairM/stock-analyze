#!/usr/bin/env python
"""
A direct test script that skips Celery and directly calls the analysis code.
"""
import sys
import logging
import time
from datetime import datetime
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

# Get a company ID from MongoDB
def get_company_id():
    client = MongoClient('mongodb://mongodb:27017')
    db = client['biotech_analysis_db']
    company = db.companies.find_one()
    client.close()
    
    if company:
        company_id = str(company["_id"])
        company_name = company.get('name', 'Unknown')
        logger.info(f"Found company: {company_name} with ID: {company_id}")
        return company_id
    else:
        logger.error("No companies found in the database")
        return None

# Import the analysis functions directly
from app.utils.sec_edgar import get_company_filings_text
from app.utils.llm import analyze_filings_with_llm

def analyze_company(company_id, filing_types=None):
    """
    Directly analyze a company without using Celery.
    """
    if filing_types is None:
        filing_types = ["8-K", "10-K", "10-Q"]
    
    logger.info(f"Starting direct analysis for company ID: {company_id}")
    
    # Connect to MongoDB
    client = MongoClient('mongodb://mongodb:27017')
    db = client['biotech_analysis_db']
    
    try:
        # Get company from database
        company_oid = ObjectId(company_id)
        company = db.companies.find_one({"_id": company_oid})
        if not company:
            logger.error(f"Company with ID {company_id} not found")
            return None
        
        logger.info(f"Processing company: {company.get('name', 'Unknown')} (Ticker: {company.get('ticker', 'Unknown')})")
        
        # Get company CIK
        cik = company.get("cik")
        if not cik:
            logger.error(f"Company with ID {company_id} does not have a CIK")
            return None
        
        logger.info(f"Found CIK: {cik} for company {company.get('name')}")
        
        # Get the company filings text
        sec_start_time = time.time()
        logger.info(f"Downloading SEC filings for company {company.get('name')} (CIK: {cik})")
        filings_text = get_company_filings_text(cik, filing_types, lookback_days=365)
        sec_end_time = time.time()
        
        if not filings_text:
            logger.warning(f"No filings found for company {company.get('name')} (CIK: {cik})")
            return None
        
        # Log filing statistics
        total_filings = len(filings_text)
        total_chars = sum(len(text) for text in filings_text.values())
        logger.info(f"Downloaded {total_filings} filings with a total of {total_chars} characters")
        logger.info(f"SEC filing download completed in {sec_end_time - sec_start_time:.2f} seconds")
        
        # Use LLM to analyze filings
        llm_start_time = time.time()
        logger.info(f"Using LLM to analyze SEC filings for company {company.get('name')}")
        analysis_result = analyze_filings_with_llm(company.get('name'), filings_text)
        llm_end_time = time.time()
        
        if not analysis_result:
            logger.error(f"Failed to analyze filings for company {company.get('name')} with LLM")
            return None
        
        logger.info(f"LLM analysis completed in {llm_end_time - llm_start_time:.2f} seconds")
        logger.info(f"Analysis result: Stock up: {analysis_result['stock_expected_to_go_up']}, Good buy: {analysis_result['is_good_buy']}")
        logger.info(f"Expected by date: {analysis_result.get('expected_by_date', 'Not specified')}")
        logger.info(f"Reasoning: {analysis_result['reasoning'][:100]}...")
        
        # Create analysis document
        analysis_doc = {
            "company_id": company_oid,
            "analysis_date": datetime.utcnow(),
            "filings_analyzed": list(filings_text.keys()),
            "analysis_result": analysis_result
        }
        
        # Insert analysis into the database
        result = db.analyses.insert_one(analysis_doc)
        analysis_id = str(result.inserted_id)
        
        logger.info(f"Analysis completed for company ID: {company_id}, Analysis ID: {analysis_id}")
        return analysis_id
        
    except Exception as e:
        logger.error(f"Error analyzing company {company_id}: {str(e)}", exc_info=True)
        return None
    finally:
        client.close()

if __name__ == "__main__":
    company_id = get_company_id()
    if company_id:
        logger.info("Starting direct analysis (bypassing Celery)...")
        analysis_id = analyze_company(company_id)
        if analysis_id:
            logger.info(f"Analysis completed and saved with ID: {analysis_id}")
        else:
            logger.error("Analysis failed")
    else:
        logger.error("Cannot proceed without a company ID") 