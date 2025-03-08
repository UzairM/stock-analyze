import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
import time
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def analyze_filings_with_llm(company_name: str, filings_text: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Analyze company SEC filings using an LLM.
    
    Args:
        company_name (str): Name of the company
        filings_text (Dict[str, str]): Dictionary mapping filing types to their text content
        
    Returns:
        Optional[Dict[str, Any]]: Analysis result or None if there was an error
    """
    try:
        logger.info(f"🧠 Starting LLM analysis for {company_name}")
        
        # Prepare system prompt
        system_prompt = """
        You are a financial analysis assistant specializing in biotech companies. 
        You'll analyze SEC filings to identify key information related to:
        
        1. New Drug Applications (NDAs)
        2. Positive phase 3 trial results
        3. Signs of upcoming FDA approval
        4. Any other significant events that could impact stock price
        
        Based on your analysis, determine:
        - If the stock is expected to go up soon (yes/no)
        - By what approximate date (MM/DD/YYYY)
        - If it's a good buy (yes/no)
        - Detailed reasoning for your conclusion
        
        IMPORTANT: Return your analysis ONLY in the following JSON format:
        {
          "stock_expected_to_go_up": boolean,
          "expected_by_date": "YYYY-MM-DD" or null,
          "is_good_buy": boolean,
          "reasoning": "detailed explanation for your conclusion"
        }
        """
        
        logger.info(f"📋 Preparing prompt for {company_name}")
        
        # Prepare user prompt
        user_prompt = f"I need you to analyze the following SEC filings for {company_name}. Focus on information related to NDAs, positive phase 3 trials, and signs of upcoming FDA approval.\n\n"
        
        # Add filing text, limited to reasonable length
        MAX_TOKENS = 32000  # Leave room for response
        current_tokens = 0
        
        # Log filing sizes
        for filing_type, text in filings_text.items():
            logger.info(f"📊 {filing_type} filing: {len(text)} characters (approx. {len(text) // 4} tokens)")
        
        # Add filing text to prompt with token tracking
        included_filings = []
        excluded_filings = []
        
        for filing_type, text in filings_text.items():
            # Estimate tokens (rough approximation: 4 chars ~= 1 token)
            text_tokens = len(text) // 4
            
            # If adding this would exceed token limit, truncate
            if current_tokens + text_tokens > MAX_TOKENS:
                truncation_needed = True
                truncated_text = text[:((MAX_TOKENS - current_tokens) * 4)]
                truncated_tokens = len(truncated_text) // 4
                
                user_prompt += f"[TRUNCATED {filing_type} FILING]\n{truncated_text}\n\n"
                current_tokens += truncated_tokens
                
                logger.info(f"⚠️ {filing_type} filing truncated: Using {truncated_tokens} tokens out of {text_tokens} available")
                included_filings.append(f"{filing_type} (truncated: {truncated_tokens}/{text_tokens} tokens)")
                break
            else:
                user_prompt += f"{filing_type} FILING:\n{text}\n\n"
                current_tokens += text_tokens
                included_filings.append(f"{filing_type} ({text_tokens} tokens)")
        
        # If we had to truncate, note that in the prompt
        if current_tokens >= MAX_TOKENS:
            user_prompt += "\n[Note: Some filings were truncated due to length constraints]"
            
            # Log excluded filings
            for filing_type, text in filings_text.items():
                if filing_type not in [f.split(" ")[0] for f in included_filings]:
                    excluded_filings.append(f"{filing_type} ({len(text) // 4} tokens)")
            
            if excluded_filings:
                logger.warning(f"⚠️ Excluded filings due to token limit: {', '.join(excluded_filings)}")
        
        logger.info(f"📤 Prompt prepared with {current_tokens} tokens from {len(included_filings)} filings")
        logger.info(f"📄 Included filings: {', '.join(included_filings)}")
        
        # Call the OpenAI API
        logger.info(f"🔄 Sending request to OpenAI API for {company_name} analysis")
        start_time = time.time()
        
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",  # Could use more capable models
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic outputs
            response_format={"type": "json_object"}
        )
        
        end_time = time.time()
        api_time = end_time - start_time
        logger.info(f"✅ Received response from OpenAI API in {api_time:.2f} seconds")
        
        # Extract the response
        result_text = response.choices[0].message.content
        
        # Log token usage
        if hasattr(response, 'usage'):
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            logger.info(f"📊 Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        
        logger.info(f"🔍 Parsing analysis result JSON")
        
        # Parse the JSON
        analysis_result = json.loads(result_text)
        
        # Log the key findings
        stock_up = analysis_result.get("stock_expected_to_go_up")
        expected_date = analysis_result.get("expected_by_date")
        is_good_buy = analysis_result.get("is_good_buy")
        
        logger.info(f"📈 Analysis summary for {company_name}:")
        logger.info(f"   - Stock expected to go up: {'Yes' if stock_up else 'No'}")
        logger.info(f"   - Expected by date: {expected_date or 'Not specified'}")
        logger.info(f"   - Good buy: {'Yes' if is_good_buy else 'No'}")
        logger.info(f"   - Reasoning: {analysis_result.get('reasoning', '')[:100]}...")
        
        # Convert date string to date object if present
        if analysis_result.get("expected_by_date"):
            try:
                # Store as string, will be converted to date in MongoDB
                date_str = analysis_result["expected_by_date"]
                # Validate it's a proper date
                datetime.strptime(date_str, "%Y-%m-%d")
                logger.info(f"✅ Successfully validated date format: {date_str}")
            except ValueError:
                # If date is invalid, set to None
                logger.warning(f"⚠️ Invalid date format in response: {analysis_result['expected_by_date']}")
                analysis_result["expected_by_date"] = None
        
        logger.info(f"✅ Successfully analyzed filings for {company_name}")
        return analysis_result
        
    except Exception as e:
        logger.error(f"❌ Error analyzing filings with LLM for {company_name}: {str(e)}", exc_info=True)
        return None 