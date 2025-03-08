import requests
import json
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_company():
    """Test creating a company."""
    # Sample company data
    company_data = {
        "ticker": "BIIB",
        "name": "Biogen Inc.",
        "sector": "Healthcare",
        "industry": "Biotechnology",
        "country": "USA",
        "exchange": "NASDAQ",
        "market_cap": 35000000000,
        "employees": 7400,
        "incorporation_date": "1978-01-01",
        "website": "https://www.biogen.com",
        "totalRevenue": 10000000000,
        "grossProfits": 8000000000,
        "ebitda": 4000000000,
        "operatingMargins": 0.35,
        "returnOnAssets": 0.12,
        "returnOnEquity": 0.25,
        "currentPrice": 250.0,
        "targetHighPrice": 300.0,
        "targetLowPrice": 200.0,
        "targetMeanPrice": 275.0,
        "recommendationMean": 2.1
    }
    
    # Create the company
    response = requests.post(f"{BASE_URL}/companies/", json=company_data)
    print(f"Create company status: {response.status_code}")
    
    # If the company already exists, we'll get a 409 conflict
    if response.status_code == 409:
        print(f"Company already exists: {response.json()}")
        return None
    
    # Otherwise, we should get a 201 created
    assert response.status_code == 201
    created_company = response.json()
    print(f"Created company: {created_company}")
    return created_company

def test_get_companies():
    """Test getting all companies."""
    response = requests.get(f"{BASE_URL}/companies/")
    print(f"Get companies status: {response.status_code}")
    assert response.status_code == 200
    companies = response.json()
    print(f"Found {len(companies)} companies")
    return companies

def test_get_company_by_id(company_id):
    """Test getting a company by ID."""
    response = requests.get(f"{BASE_URL}/companies/{company_id}")
    print(f"Get company by ID status: {response.status_code}")
    assert response.status_code == 200
    company = response.json()
    print(f"Found company: {company}")
    return company

def test_get_company_by_ticker(ticker):
    """Test getting a company by ticker."""
    response = requests.get(f"{BASE_URL}/companies/ticker/{ticker}")
    print(f"Get company by ticker status: {response.status_code}")
    assert response.status_code == 200
    company = response.json()
    print(f"Found company: {company}")
    return company

def test_update_company(company_id):
    """Test updating a company."""
    # Update data
    update_data = {
        "currentPrice": 260.0,
        "targetHighPrice": 310.0,
        "targetLowPrice": 210.0,
        "targetMeanPrice": 285.0
    }
    
    # Update the company
    response = requests.put(f"{BASE_URL}/companies/{company_id}", json=update_data)
    print(f"Update company status: {response.status_code}")
    assert response.status_code == 200
    updated_company = response.json()
    print(f"Updated company: {updated_company}")
    return updated_company

def main():
    """Run all tests."""
    print("Testing API endpoints...")
    
    # Test health endpoint
    test_health()
    
    # Test creating a company
    created_company = test_create_company()
    
    # Test getting all companies
    companies = test_get_companies()
    
    # If we have companies, test getting one by ID and ticker
    if companies:
        company_id = companies[0]["_id"]
        ticker = companies[0]["ticker"]
        
        # Test getting a company by ID
        test_get_company_by_id(company_id)
        
        # Test getting a company by ticker
        test_get_company_by_ticker(ticker)
        
        # Test updating a company
        test_update_company(company_id)
    
    print("All tests completed successfully!")

if __name__ == "__main__":
    main() 