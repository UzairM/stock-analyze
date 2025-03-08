#!/usr/bin/env python
"""
A simple script to test if Celery tasks are working properly.
Run this from inside the backend container:
    docker-compose exec backend python test_celery.py
"""
import sys
import time
import logging
from app.utils.celery_app import ping
from app.utils.tasks import analyze_company_sec_filings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def test_ping():
    """Test the simple ping task"""
    logger.info("Sending ping task...")
    result = ping.delay()
    logger.info(f"Task ID: {result.id}")
    
    # Wait for the result
    timeout = 5
    start_time = time.time()
    while not result.ready() and time.time() - start_time < timeout:
        logger.info("Waiting for ping result...")
        time.sleep(0.5)
    
    if result.ready():
        logger.info(f"Ping result: {result.get()}")
        return True
    else:
        logger.error("Ping task timed out!")
        return False

def test_analysis(company_id):
    """Test the analysis task with a specific company ID"""
    logger.info(f"Sending analyze task for company {company_id}...")
    result = analyze_company_sec_filings.delay(company_id)
    logger.info(f"Task ID: {result.id}")
    
    # Wait a bit to see if the task is received
    time.sleep(2)
    logger.info(f"Task state: {result.state}")
    
    # Don't wait for completion as it might take a while
    logger.info("Analysis task sent. Check celery_worker logs for detailed progress.")
    return result.id

if __name__ == "__main__":
    # First test ping
    if test_ping():
        logger.info("Ping test successful! Celery connection is working.")
        
        # Ask for a company ID
        company_id = input("Enter a company ID to test analysis task (or press Enter to skip): ").strip()
        if company_id:
            task_id = test_analysis(company_id)
            logger.info(f"Analysis task sent with ID: {task_id}")
            logger.info("Check celery_worker logs for task progress")
    else:
        logger.error("Ping test failed! Celery communication is not working.")
        logger.error("Check Redis connection and Celery worker status.") 