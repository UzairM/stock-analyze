from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from bson import ObjectId

# Helper for ObjectId conversion
def str_to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)

# Base Company model
class CompanyBase(BaseModel):
    ticker: str = Field(..., description="Company ticker symbol")
    name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Company sector")
    industry: Optional[str] = Field(None, description="Company industry")
    country: Optional[str] = Field(None, description="Company country")
    exchange: Optional[str] = Field(None, description="Stock exchange")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    employees: Optional[int] = Field(None, description="Number of employees")
    incorporation_date: Optional[date] = Field(None, description="Date of incorporation")
    website: Optional[str] = Field(None, description="Company website")
    
    # Financial metrics
    totalRevenue: Optional[float] = Field(None, description="Total revenue")
    grossProfits: Optional[float] = Field(None, description="Gross profits")
    ebitda: Optional[float] = Field(None, description="EBITDA")
    operatingMargins: Optional[float] = Field(None, description="Operating margins")
    returnOnAssets: Optional[float] = Field(None, description="Return on assets")
    returnOnEquity: Optional[float] = Field(None, description="Return on equity")
    
    # Stock metrics
    currentPrice: Optional[float] = Field(None, description="Current stock price")
    targetHighPrice: Optional[float] = Field(None, description="Target high price")
    targetLowPrice: Optional[float] = Field(None, description="Target low price")
    targetMeanPrice: Optional[float] = Field(None, description="Target mean price")
    recommendationMean: Optional[float] = Field(None, description="Recommendation mean")

# Model for creating a company
class CompanyCreate(CompanyBase):
    pass

# Model for company in database
class CompanyInDB(CompanyBase):
    id: str = Field(..., alias="_id", description="MongoDB ObjectID")
    cik: Optional[str] = Field(None, description="SEC Central Index Key")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Model for company response
class Company(CompanyInDB):
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "60d21b4967d0d8992e610c85",
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
                "recommendationMean": 2.1,
                "cik": "0000875045",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }

# Model for updating a company
class CompanyUpdate(BaseModel):
    ticker: Optional[str] = None
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None
    employees: Optional[int] = None
    incorporation_date: Optional[date] = None
    website: Optional[str] = None
    totalRevenue: Optional[float] = None
    grossProfits: Optional[float] = None
    ebitda: Optional[float] = None
    operatingMargins: Optional[float] = None
    returnOnAssets: Optional[float] = None
    returnOnEquity: Optional[float] = None
    currentPrice: Optional[float] = None
    targetHighPrice: Optional[float] = None
    targetLowPrice: Optional[float] = None
    targetMeanPrice: Optional[float] = None
    recommendationMean: Optional[float] = None
    cik: Optional[str] = None 