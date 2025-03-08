import logging
import httpx
import os
import json
from datetime import datetime, timedelta
import time
from typing import List, Dict, Any, Optional
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# SEC EDGAR base URLs
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"
FILING_DETAILS_URL = "https://www.sec.gov/Archives/edgar/data/{}/{}/index.json"
FILING_TEXT_URL = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}"

# SEC API requires a user agent header
HEADERS = {
    "User-Agent": f"BiotechAnalysis research@biotechanalysis.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """
    Get the CIK for a given ticker symbol.
    
    Args:
        ticker (str): The ticker symbol to look up
        
    Returns:
        Optional[str]: The CIK if found, None otherwise
    """
    try:
        logger.info(f"🔍 Looking up CIK for ticker: {ticker}")
        response = httpx.get(COMPANY_TICKERS_URL, headers=HEADERS)
        response.raise_for_status()
        
        companies = response.json()
        
        # Search for the ticker in the response
        for key, company in companies.items():
            if company.get("ticker", "").upper() == ticker.upper():
                # Format CIK with leading zeros to 10 digits
                cik = str(company.get("cik_str")).zfill(10)
                logger.info(f"✅ Found CIK: {cik} for ticker: {ticker}")
                return cik
        
        logger.warning(f"⚠️ No CIK found for ticker {ticker}")
        return None
        
    except httpx.HTTPError as e:
        logger.error(f"❌ HTTP error occurred while fetching CIK for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error occurred while fetching CIK for {ticker}: {e}")
        return None

def get_filings(cik: str, filing_types: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Get filings for a company within a date range.
    
    Args:
        cik (str): The CIK of the company
        filing_types (List[str]): List of filing types to retrieve (e.g., ["10-K", "10-Q", "8-K"])
        start_date (datetime): Start date for filings
        end_date (datetime): End date for filings
        
    Returns:
        List[Dict[str, Any]]: List of filing metadata
    """
    try:
        # Ensure CIK is zero-padded to 10 digits
        cik_padded = cik.zfill(10)
        
        # Remove leading zeros for URL
        cik_for_url = cik.lstrip("0")
        
        # Get submissions data
        url = SUBMISSIONS_URL.format(cik_padded)
        logger.info(f"📊 Fetching submissions from SEC EDGAR: {url}")
        
        response = httpx.get(url, headers=HEADERS)
        response.raise_for_status()
        
        submissions_data = response.json()
        logger.info(f"✅ Successfully retrieved submissions data for CIK: {cik}")
        
        # Get recent filings
        filings = []
        recent_forms = submissions_data.get("filings", {}).get("recent", {}).get("form", [])
        
        logger.info(f"📄 Found {len(recent_forms)} recent filings to filter")
        logger.info(f"🔍 Filtering filings by type ({', '.join(filing_types)}) and date range ({start_date.date()} to {end_date.date()})")
        
        for idx, filing_type in enumerate(recent_forms):
            filing_date_str = submissions_data["filings"]["recent"]["filingDate"][idx]
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
            
            accession_number = submissions_data["filings"]["recent"]["accessionNumber"][idx]
            accession_number_clean = accession_number.replace("-", "")
            
            primary_document = submissions_data["filings"]["recent"]["primaryDocument"][idx]
            
            # Check if filing type and date are within our criteria
            if (filing_type in filing_types and 
                start_date <= filing_date <= end_date):
                
                filing_info = {
                    "cik": cik,
                    "filing_type": filing_type,
                    "filing_date": filing_date,
                    "accession_number": accession_number,
                    "accession_number_clean": accession_number_clean,
                    "primary_document": primary_document
                }
                
                filings.append(filing_info)
                logger.info(f"✅ Found matching {filing_type} filing from {filing_date.date()}")
        
        logger.info(f"📝 Found {len(filings)} filings matching criteria for CIK {cik}")
        return filings
        
    except httpx.HTTPError as e:
        logger.error(f"❌ HTTP error occurred while fetching filings for {cik}: {e}")
        return []
    except Exception as e:
        logger.error(f"❌ Error occurred while fetching filings for {cik}: {e}", exc_info=True)
        return []

def get_filing_text(filing: Dict[str, Any]) -> Optional[str]:
    """
    Get the text content of a filing.
    
    Args:
        filing (Dict[str, Any]): Filing metadata
        
    Returns:
        Optional[str]: Text content of the filing if successful, None otherwise
    """
    try:
        cik = filing["cik"]
        accession_number = filing["accession_number_clean"]
        primary_document = filing["primary_document"]
        filing_type = filing["filing_type"]
        filing_date = filing["filing_date"].date()
        
        # Remove leading zeros for URL
        cik_for_url = cik.lstrip("0")
        
        # Get filing details to find the full text document
        details_url = FILING_DETAILS_URL.format(cik_for_url, accession_number)
        
        logger.info(f"📄 Fetching details for {filing_type} ({filing_date}) from: {details_url}")
        
        # SEC rate limits to 10 requests per second
        time.sleep(0.1)
        
        details_start = time.time()
        response = httpx.get(details_url, headers=HEADERS)
        response.raise_for_status()
        
        filing_details = response.json()
        details_end = time.time()
        logger.info(f"⏱️ Got filing details in {details_end - details_start:.2f} seconds")
        
        # Find the .txt file (typically the complete submission text)
        txt_file = next((file for file in filing_details.get("directory", {}).get("item", []) 
                          if file.get("name", "").endswith(".txt")), None)
        
        if txt_file:
            txt_file_name = txt_file.get("name")
            txt_file_size = int(txt_file.get("size", 0))
            
            # Get the full text
            text_url = FILING_TEXT_URL.format(cik_for_url, accession_number, txt_file_name)
            
            logger.info(f"📥 Downloading {filing_type} filing text ({txt_file_size/1024:.1f} KB) from: {text_url}")
            
            # SEC rate limits to 10 requests per second
            time.sleep(0.1)
            
            text_start = time.time()
            text_response = httpx.get(text_url, headers=HEADERS)
            text_response.raise_for_status()
            text_end = time.time()
            
            # Clean up the text content
            text_content = text_response.text
            orig_length = len(text_content)
            
            # Remove HTML tags if present
            text_content = re.sub(r'<[^>]+>', ' ', text_content)
            
            # Replace multiple whitespace with a single space
            text_content = re.sub(r'\s+', ' ', text_content)
            
            clean_length = len(text_content)
            logger.info(f"⏱️ Downloaded and cleaned text in {text_end - text_start:.2f} seconds")
            logger.info(f"📊 Original size: {orig_length} chars, Cleaned size: {clean_length} chars")
            
            return text_content
            
        else:
            logger.warning(f"⚠️ No text file found for filing {accession_number}")
            return None
        
    except httpx.HTTPError as e:
        logger.error(f"❌ HTTP error occurred while fetching filing text for {filing.get('accession_number')}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error occurred while fetching filing text for {filing.get('accession_number')}: {e}", exc_info=True)
        return None

def get_company_filings_text(cik: str, filing_types: List[str], lookback_days: int = 365) -> Dict[str, str]:
    """
    Get text content for all filings of specified types in the past year.
    
    Args:
        cik (str): The CIK of the company
        filing_types (List[str]): List of filing types to retrieve (e.g., ["10-K", "10-Q", "8-K"])
        lookback_days (int): Number of days to look back for filings
        
    Returns:
        Dict[str, str]: Dictionary mapping filing types to their combined text content
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    logger.info(f"🔍 Searching for {', '.join(filing_types)} filings from {start_date.date()} to {end_date.date()}")
    
    # Get filings
    start_time = time.time()
    filings = get_filings(cik, filing_types, start_date, end_date)
    end_time = time.time()
    
    logger.info(f"⏱️ Filing metadata retrieval completed in {end_time - start_time:.2f} seconds")
    
    if not filings:
        logger.warning(f"⚠️ No filings found for CIK {cik} in the past {lookback_days} days")
        return {}
    
    # Get text content for each filing
    filings_text = {}
    
    for filing_type in filing_types:
        # Get filings of this type
        type_filings = [f for f in filings if f["filing_type"] == filing_type]
        
        if not type_filings:
            logger.info(f"ℹ️ No {filing_type} filings found for CIK {cik}")
            continue
        
        logger.info(f"📥 Starting download of {len(type_filings)} {filing_type} filings")
        
        # Get text for each filing of this type
        combined_text = ""
        download_start = time.time()
        
        for i, filing in enumerate(type_filings):
            logger.info(f"📄 ({i+1}/{len(type_filings)}) Processing {filing_type} from {filing['filing_date'].date()}")
            text = get_filing_text(filing)
            
            if text:
                # Add filing metadata as a header
                header = f"\n\n--- {filing_type} FILING DATE: {filing['filing_date'].strftime('%Y-%m-%d')} ---\n\n"
                combined_text += header + text
                logger.info(f"✅ Successfully added {filing_type} filing from {filing['filing_date'].date()} ({len(text)} chars)")
            else:
                logger.warning(f"⚠️ Failed to get text for {filing_type} filing from {filing['filing_date'].date()}")
        
        download_end = time.time()
        
        if combined_text:
            filings_text[filing_type] = combined_text
            logger.info(f"📊 {filing_type}: Combined {len(type_filings)} filings into {len(combined_text)} chars")
            logger.info(f"⏱️ Download completed in {download_end - download_start:.2f} seconds")
    
    return filings_text 