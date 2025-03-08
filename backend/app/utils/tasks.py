import logging
from datetime import datetime, timedelta
import os
import json
import httpx
from bson import ObjectId
import openai
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from celery import Task
import time

from .celery_app import celery_app
from .sec_edgar import get_company_filings_text
from .llm import analyze_filings_with_llm

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# MongoDB connection settings from environment variables
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "biotech_analysis_db")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

class DatabaseTask(Task):
    """Custom Celery Task that maintains a database connection."""
    _db = None

    @property
    def db(self):
        if self._db is None:
            client = AsyncIOMotorClient(MONGO_URL)
            self._db = client[DB_NAME]
        return self._db

@celery_app.task(bind=True, base=DatabaseTask)
def analyze_company_sec_filings(self, company_id, filings_types=None):
    """
    Task to analyze a company's SEC filings.
    
    Args:
        company_id (str): MongoDB ID of the company to analyze
        filings_types (list, optional): List of filing types to analyze. 
                                      Defaults to ["8-K", "10-K", "10-Q"].
    
    Returns:
        str: ID of the created analysis document
    """
    task_start_time = time.time()
    logger.info(f"🚀 TASK STARTED: Analysis task for company ID: {company_id}")
    logger.info(f"Filing types to analyze: {filings_types or ['8-K', '10-K', '10-Q']}")
    
    # Update task state to STARTED
    self.update_state(state='STARTED', meta={'status': 'Started processing'})
    
    if filings_types is None:
        filings_types = ["8-K", "10-K", "10-Q"]
    
    # Convert to ObjectId
    company_oid = ObjectId(company_id)
    
    # Create a synchronous client for the task
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Get company from database
        company = db.companies.find_one({"_id": company_oid})
        if not company:
            logger.error(f"❌ Company with ID {company_id} not found")
            return None
        
        logger.info(f"📊 Processing company: {company['name']} (Ticker: {company['ticker']})")
        
        # Get company CIK
        cik = company.get("cik")
        if not cik:
            logger.error(f"❌ Company with ID {company_id} does not have a CIK")
            return None
        
        logger.info(f"🔍 Found CIK: {cik} for company {company['name']}")
        
        # Update task state
        self.update_state(state='PROGRESS', meta={
            'status': 'Fetching SEC filings',
            'company': company['name'],
            'progress': 25
        })
        
        # Get the company filings text
        sec_start_time = time.time()
        logger.info(f"📥 DOWNLOADING: Fetching SEC filings for company {company['name']} (CIK: {cik})")
        filings_text = get_company_filings_text(cik, filings_types, lookback_days=365)
        sec_end_time = time.time()
        
        if not filings_text:
            logger.warning(f"⚠️ No filings found for company {company['name']} (CIK: {cik})")
            
            # Create analysis document with error
            analysis_doc = {
                "company_id": company_oid,
                "analysis_date": datetime.utcnow(),
                "filings_analyzed": filings_types,
                "analysis_result": {
                    "stock_expected_to_go_up": False,
                    "expected_by_date": None,
                    "is_good_buy": False,
                    "reasoning": "No SEC filings found in the past year. Unable to perform analysis."
                }
            }
            
            # Insert analysis into the database
            result = db.analyses.insert_one(analysis_doc)
            analysis_id = str(result.inserted_id)
            
            logger.info(f"📝 Created error analysis for company ID: {company_id}, Analysis ID: {analysis_id}")
            return analysis_id
        
        # Log filing statistics
        total_filings = len(filings_text)
        total_chars = sum(len(text) for text in filings_text.values())
        logger.info(f"📄 Downloaded {total_filings} filings with a total of {total_chars} characters")
        logger.info(f"⏱️ SEC filing download completed in {sec_end_time - sec_start_time:.2f} seconds")
        
        for filing_type, text in filings_text.items():
            logger.info(f"  - {filing_type}: {len(text)} characters")
        
        # Update task state
        self.update_state(state='PROGRESS', meta={
            'status': 'Analyzing filings with LLM',
            'company': company['name'],
            'filings': list(filings_text.keys()),
            'progress': 50
        })
        
        # Use LLM to analyze filings
        llm_start_time = time.time()
        logger.info(f"🧠 ANALYZING: Using LLM to analyze SEC filings for company {company['name']}")
        analysis_result = analyze_filings_with_llm(company['name'], filings_text)
        llm_end_time = time.time()
        
        if not analysis_result:
            logger.error(f"❌ Failed to analyze filings for company {company['name']} with LLM")
            
            # Create analysis document with error
            analysis_doc = {
                "company_id": company_oid,
                "analysis_date": datetime.utcnow(),
                "filings_analyzed": list(filings_text.keys()),
                "analysis_result": {
                    "stock_expected_to_go_up": False,
                    "expected_by_date": None,
                    "is_good_buy": False,
                    "reasoning": "Error analyzing SEC filings with LLM. Please try again later."
                }
            }
        else:
            logger.info(f"✅ LLM analysis completed in {llm_end_time - llm_start_time:.2f} seconds")
            logger.info(f"📈 Analysis result: Stock up: {analysis_result['stock_expected_to_go_up']}, Good buy: {analysis_result['is_good_buy']}")
            logger.info(f"📅 Expected by date: {analysis_result.get('expected_by_date', 'Not specified')}")
            logger.info(f"💭 Reasoning summary: {analysis_result['reasoning'][:100]}...")
            
            # Create analysis document
            analysis_doc = {
                "company_id": company_oid,
                "analysis_date": datetime.utcnow(),
                "filings_analyzed": list(filings_text.keys()),
                "analysis_result": analysis_result
            }
        
        # Update task state
        self.update_state(state='PROGRESS', meta={
            'status': 'Saving analysis results',
            'company': company['name'],
            'progress': 90
        })
        
        # Insert analysis into the database
        result = db.analyses.insert_one(analysis_doc)
        analysis_id = str(result.inserted_id)
        
        task_end_time = time.time()
        logger.info(f"🏁 TASK COMPLETED: Analysis for company ID: {company_id}, Analysis ID: {analysis_id}")
        logger.info(f"⏱️ Total task time: {task_end_time - task_start_time:.2f} seconds")
        
        return analysis_id
        
    except Exception as e:
        logger.error(f"❌ ERROR: Analysis failed for company {company_id}: {str(e)}", exc_info=True)
        raise
    finally:
        # Close the client
        client.close() 