import logging
import os
from datetime import datetime, timedelta
import time
from typing import List, Dict, Any, Optional
import re
import json
import httpx
import tempfile
import html2text
from bs4 import BeautifulSoup
import subprocess
import sys
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# SEC EDGAR URLs and constants
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
BROWSE_EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

# SEC requires a valid user agent with contact email
SEC_USER_AGENT = "BiotechAnalysis research@biotechanalysis.com"
HEADERS = {"User-Agent": SEC_USER_AGENT}

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def summarize_filing_with_ollamini(text: str, filing_type: str, filing_date: str) -> str:
    """
    Summarize SEC filing text using OpenAI's o3-mini model,
    focusing on positive sentiments, FDA approval meetings, and Phase 3 trial results.
    
    Args:
        text (str): The filing text to summarize
        filing_type (str): The type of filing (e.g., "10-K", "10-Q")
        filing_date (str): The date of the filing
        
    Returns:
        str: Summarized filing text
    """
    try:
        logger.info(f"📝 Summarizing {filing_type} filing from {filing_date} ({len(text)} chars)")
        
        # Limit input size to avoid token limits
        truncated_text = text[:15000]
        
        # Create a prompt that focuses on extracting the information we want
        prompt = f"""Summarize the following {filing_type} SEC filing from {filing_date}. 
Focus specifically on:
1. Positive sentiments and developments
2. FDA approval meetings, decisions or communications
3. Phase 3 clinical trial results and updates
4. Any breakthrough designations or regulatory milestones
5. Key financial metrics and growth indicators

If none of these topics are mentioned, provide a brief general summary of key points.

Filing text:
{truncated_text}
"""

        # Call the o3-mini model for summarization
        response = client.chat.completions.create(
            model="o3-mini",  # Using o3-mini as specified
            messages=[
                {"role": "system", "content": "You are an expert financial analyst specializing in biotech companies. Extract and summarize key information from SEC filings, focusing on positive developments, FDA approvals, and clinical trial results."},
                {"role": "user", "content": prompt}
            ]
        )
        
        summary = response.choices[0].message.content
        logger.info(f"✅ Successfully summarized {filing_type} filing from {filing_date} ({len(summary)} chars)")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error summarizing filing: {e}")
        # If summarization fails, provide a placeholder summary to avoid breaking the pipeline
        return f"Error summarizing filing: {str(e)}"

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
        
        # Use the SEC API
        response = httpx.get(COMPANY_TICKERS_URL, headers=HEADERS)
        response.raise_for_status()
        
        companies = response.json()
        
        # Search for the ticker in the response
        for key, company in companies.items():
            if company.get("ticker", "").upper() == ticker.upper():
                # Format CIK with leading zeros to 10 digits
                cik = str(company.get("cik_str")).zfill(10)
                logger.info(f"✅ Found CIK: {cik} for ticker: {ticker} using SEC API")
                return cik
        
        logger.warning(f"⚠️ No CIK found for ticker {ticker}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error looking up CIK for ticker {ticker}: {e}")
        return None

def get_company_filings_text(cik: str, filing_types: Optional[List[str]] = None, lookback_days: int = 365, max_filings: int = 10, summarize: bool = True) -> Dict[str, str]:
    """
    Get text content for SEC filings using edgartools Company API.
    
    Args:
        cik (str): The CIK of the company
        filing_types (Optional[List[str]]): List of filing types to retrieve (e.g., ["10-K", "10-Q", "8-K"])
                                          If None or empty, retrieves common filing types
        lookback_days (int): Number of days to look back for filings
        max_filings (int): Maximum number of filings to retrieve per type
        summarize (bool): Whether to summarize the filings (default: True)
        
    Returns:
        Dict[str, str]: Dictionary mapping filing types to their text content or summaries
    """
    # Use default filing types if none provided
    if not filing_types:
        filing_types = ["10-K", "10-Q", "8-K", "S-1", "20-F", "6-K"]
    
    # Format CIK (remove leading zeros if needed)
    cik_stripped = cik.lstrip("0")
    
    logger.info(f"🔍 Searching for {', '.join(filing_types)} filings for CIK {cik}")
    
    try:
        # Import edgartools
        from edgar import Company, set_identity
        
        # Set identity for SEC access
        set_identity("research@biotechanalysis.com")
        
        # Initialize company using CIK
        company = Company(cik_stripped)
        logger.info(f"✅ Successfully initialized company: {company.name}")
        
        filings_text = {}
        
        # Process each filing type
        for filing_type in filing_types:
            try:
                logger.info(f"🔍 Getting {filing_type} filings for {company.name}")
                
                # Get filings for this type
                filings = company.get_filings(form=filing_type)
                
                if not filings:
                    logger.warning(f"⚠️ No {filing_type} filings found for {company.name}")
                    continue
                
                # Get the latest filings
                latest_filings = filings.latest(max_filings)
                
                if not latest_filings:
                    logger.warning(f"⚠️ No recent {filing_type} filings found for {company.name}")
                    continue
                
                combined_text = ""
                filing_count = 0
                
                # Process each filing
                for filing in latest_filings:
                    try:
                        # Get filing text content
                        text = filing.text()
                        
                        if text:
                            filing_count += 1
                            
                            if summarize:
                                # Summarize the filing text
                                summary = summarize_filing_with_ollamini(text, filing_type, filing.filing_date)
                                combined_text += f"\n\n--- {filing_type} FILING DATE: {filing.filing_date} SUMMARY ---\n\n"
                                combined_text += summary
                                combined_text += "\n\n"
                                logger.info(f"✅ Added summarized {filing_type} filing from {filing.filing_date} ({len(summary)} chars)")
                            else:
                                # Use the full text
                                combined_text += f"\n\n--- {filing_type} FILING DATE: {filing.filing_date} ---\n\n"
                                combined_text += f"--- DOCUMENT: {filing.accession_number} ---\n\n"
                                combined_text += text
                                combined_text += "\n\n"
                                logger.info(f"✅ Added {filing_type} filing from {filing.filing_date} ({len(text)} chars)")
                    
                    except Exception as e:
                        logger.error(f"❌ Error getting text for filing {filing.accession_number}: {e}")
                        continue
                
                if combined_text:
                    filings_text[filing_type] = combined_text
                    logger.info(f"📊 {filing_type}: Combined {filing_count} filings into {len(combined_text)} chars")
            
            except Exception as e:
                logger.error(f"❌ Error processing {filing_type} filings: {e}")
                continue
        
        if not filings_text:
            logger.error(f"❌ No filings could be retrieved for {company.name}")
            filings_text["ERROR"] = f"No filings could be retrieved for {company.name}"
        
        return filings_text
    
    except Exception as e:
        logger.error(f"❌ Error initializing edgartools: {e}")
        return {"ERROR": f"Failed to initialize edgartools: {str(e)}"}

def analyze_filing_summaries(summaries: Dict[str, str], ticker: str, company_name: str) -> str:
    """
    Analyze filing summaries for a company, looking for positive sentiments,
    FDA approval information, and Phase 3 trial updates.
    
    Args:
        summaries (Dict[str, str]): Dictionary of filing summaries by filing type
        ticker (str): The company's ticker symbol
        company_name (str): The company's name
        
    Returns:
        str: Analysis of the company's filings
    """
    try:
        logger.info(f"🔍 Analyzing filing summaries for {company_name} ({ticker})")
        
        # Prepare combined input text for analysis
        combined_input = f"Analysis of SEC filings for {company_name} ({ticker}):\n\n"
        
        # Add each filing type's summary
        for filing_type, summary in summaries.items():
            # Skip error messages
            if filing_type == "ERROR":
                continue
                
            # If the summary contains an error message, provide a simplified version
            if summary.startswith("Error summarizing filing:"):
                combined_input += f"## {filing_type} FILINGS:\nNo meaningful summary available for this filing type.\n\n"
                continue
                
            combined_input += f"## {filing_type} FILINGS:\n{summary}\n\n"
            
        # Create analysis prompt
        prompt = f"""Based on the SEC filing summaries for {company_name} ({ticker}), provide a comprehensive analysis focusing on:

1. Overall sentiment and outlook
2. FDA approval status, meetings, and regulatory milestones
3. Phase 3 clinical trial results and progress
4. Key financial indicators and market position
5. Potential catalysts and near-term opportunities

Summaries:
{combined_input}
"""

        # Call OpenAI for the final analysis
        response = client.chat.completions.create(
            model="gpt-4",  # Using a more powerful model for the final analysis
            messages=[
                {"role": "system", "content": "You are an expert financial analyst specializing in biotech stocks. Your task is to analyze SEC filing summaries and extract key insights about the company's prospects, particularly regarding FDA approvals and clinical trials."},
                {"role": "user", "content": prompt}
            ]
        )
        
        analysis = response.choices[0].message.content
        logger.info(f"✅ Successfully generated analysis for {company_name} ({ticker}) ({len(analysis)} chars)")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Error analyzing filing summaries: {e}")
        return f"Error analyzing filing summaries: {str(e)}"

def analyze_sec_filings_for_stock(ticker: str) -> Dict[str, Any]:
    """
    Complete pipeline to analyze SEC filings for a stock.
    
    Args:
        ticker (str): The ticker symbol to analyze
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    try:
        logger.info(f"🚀 Starting SEC filing analysis for ticker: {ticker}")
        
        # Step 1: Get CIK from ticker
        cik = get_cik_from_ticker(ticker)
        if not cik:
            return {"error": f"Could not find CIK for ticker {ticker}"}
            
        # Step 2: Get filing summaries (automatically summarizes with o3-mini)
        filing_summaries = get_company_filings_text(cik, summarize=True)
        
        if "ERROR" in filing_summaries and len(filing_summaries) == 1:
            return {"error": filing_summaries["ERROR"]}
            
        # Step 3: Import edgartools to get company name
        from edgar import Company, set_identity
        set_identity("research@biotechanalysis.com")
        company = Company(cik.lstrip("0"))
        company_name = company.name
            
        # Step 4: Analyze the filing summaries
        analysis = analyze_filing_summaries(filing_summaries, ticker, company_name)
        
        # Step 5: Return results
        return {
            "ticker": ticker,
            "cik": cik,
            "company_name": company_name,
            "filing_summaries": filing_summaries,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"❌ Error in SEC filing analysis pipeline: {e}")
        return {"error": f"Error analyzing SEC filings: {str(e)}"}