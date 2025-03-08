import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
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

# Check if we're using a dummy API key
MOCK_LLM_RESPONSES = OPENAI_API_KEY is None or OPENAI_API_KEY.startswith('sk-dummy')

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
        # Check if filings_text is empty
        if not filings_text:
            logger.error(f"❌ No SEC filings found for {company_name}")
            return {
                "stock_expected_to_go_up": False,
                "expected_by_date": None,
                "is_good_buy": False,
                "reasoning": f"Error: No SEC filings were retrieved for {company_name}. The edgartools package may not be installed or properly configured, or there may be issues fetching the filings from SEC EDGAR."
            }
            
        logger.info(f"🧠 Starting LLM analysis for {company_name}")
        logger.info(f"🔑 Using {'mock responses' if MOCK_LLM_RESPONSES else 'OpenAI API'} for analysis")
        
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
        
        # Use a mock response if we're in testing mode
        if MOCK_LLM_RESPONSES:
            logger.info(f"🔄 Using mock response for {company_name} analysis (no valid API key)")
            time.sleep(2)  # Simulate API delay
            
            # Generate deterministic but varied result based on company name
            import hashlib
            hash_val = int(hashlib.md5(company_name.encode()).hexdigest(), 16)
            
            # Create mock response that varies by company
            mock_result = {
                "stock_expected_to_go_up": hash_val % 2 == 0,
                "expected_by_date": (datetime.now().replace(day=1) + timedelta(days=(hash_val % 180))).strftime("%Y-%m-%d"),
                "is_good_buy": hash_val % 3 == 0,
                "reasoning": f"This is a mock analysis for testing purposes. The analysis would normally be based on information found in the SEC filings for {company_name}, particularly regarding NDAs, phase 3 trial results, and signs of upcoming FDA approval. Based on simulated analysis, {'positive' if hash_val % 2 == 0 else 'no clear'} indicators were found for stock growth in the near term."
            }
            
            # Log mock response
            logger.info(f"✅ Generated mock response for {company_name}")
            logger.info(f"📈 Mock analysis summary: Stock up: {mock_result['stock_expected_to_go_up']}, Good buy: {mock_result['is_good_buy']}")
            logger.info(f"📅 Expected by date: {mock_result['expected_by_date']}")
            logger.info(f"💭 Reasoning: {mock_result['reasoning'][:100]}...")
            
            return mock_result
        
        # Call the OpenAI API
        logger.info(f"🔄 Sending request to OpenAI API for {company_name} analysis")
        start_time = time.time()
        
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo-0125",  # Could use more capable models
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Lower temperature for more deterministic outputs
                response_format={"type": "json_object"},
                timeout=60  # 60 second timeout
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
            
        except openai.error.AuthenticationError:
            logger.error(f"❌ OpenAI API Authentication Error: Invalid API key")
            logger.info("🔄 Falling back to mock response due to authentication error")
            
            # Return a mock result
            return {
                "stock_expected_to_go_up": False,
                "expected_by_date": None,
                "is_good_buy": False,
                "reasoning": f"Unable to analyze SEC filings due to OpenAI API authentication error. Please check your API key configuration."
            }
            
        except openai.error.Timeout:
            logger.error(f"❌ OpenAI API Timeout: Request took too long")
            return {
                "stock_expected_to_go_up": False,
                "expected_by_date": None,
                "is_good_buy": False,
                "reasoning": f"Analysis timed out. The SEC filings for {company_name} may be too extensive for processing within the allocated time."
            }
            
        except openai.error.RateLimitError:
            logger.error(f"❌ OpenAI API Rate Limit Error: Too many requests")
            return {
                "stock_expected_to_go_up": False,
                "expected_by_date": None,
                "is_good_buy": False,
                "reasoning": f"Unable to analyze SEC filings due to OpenAI API rate limits. Please try again later."
            }
            
        except openai.error.APIError as e:
            logger.error(f"❌ OpenAI API Error: {str(e)}")
            return {
                "stock_expected_to_go_up": False,
                "expected_by_date": None,
                "is_good_buy": False,
                "reasoning": f"Unable to analyze SEC filings due to an API error. Details: {str(e)}"
            }
        
        logger.info(f"🔍 Parsing analysis result JSON")
        
        try:
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
            
        except json.JSONDecodeError:
            logger.error(f"❌ Failed to parse LLM response as JSON")
            logger.error(f"Response text: {result_text[:500]}...")
            return {
                "stock_expected_to_go_up": False,
                "expected_by_date": None,
                "is_good_buy": False,
                "reasoning": f"Error parsing analysis results. The LLM response could not be interpreted correctly."
            }
        
    except Exception as e:
        logger.error(f"❌ Error analyzing filings with LLM for {company_name}: {str(e)}", exc_info=True)
        return {
            "stock_expected_to_go_up": False,
            "expected_by_date": None,
            "is_good_buy": False,
            "reasoning": f"An unexpected error occurred during analysis: {str(e)}"
        } 