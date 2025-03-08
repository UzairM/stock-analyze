from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from bson import ObjectId

# Helper for ObjectId conversion
def str_to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)

# Analysis result model
class AnalysisResult(BaseModel):
    stock_expected_to_go_up: bool = Field(..., description="Whether the stock is expected to go up")
    expected_by_date: Optional[date] = Field(None, description="Expected date for stock to go up")
    is_good_buy: bool = Field(..., description="Whether the stock is a good buy")
    reasoning: str = Field(..., description="Reasoning behind the analysis")

# Base Analysis model
class AnalysisBase(BaseModel):
    company_id: str = Field(..., description="Reference to company ID")
    analysis_date: datetime = Field(default_factory=datetime.utcnow, description="Date of analysis")
    filings_analyzed: List[str] = Field(default=[], description="List of filings analyzed")
    analysis_result: Optional[AnalysisResult] = Field(None, description="Analysis result")

# Model for creating an analysis
class AnalysisCreate(BaseModel):
    company_id: str = Field(..., description="Reference to company ID")
    filings_analyzed: List[str] = Field(default=[], description="List of filings analyzed")

# Model for analysis in database
class AnalysisInDB(AnalysisBase):
    id: str = Field(..., alias="_id", description="MongoDB ObjectID")
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Model for analysis response
class Analysis(AnalysisInDB):
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "60d21b4967d0d8992e610c86",
                "company_id": "60d21b4967d0d8992e610c85",
                "analysis_date": "2023-01-01T00:00:00",
                "filings_analyzed": ["8-K", "10-K", "10-Q"],
                "analysis_result": {
                    "stock_expected_to_go_up": True,
                    "expected_by_date": "2023-12-31",
                    "is_good_buy": True,
                    "reasoning": "Based on positive phase 3 trial results and upcoming FDA approval, the stock is likely to increase."
                }
            }
        }

# Model for updating an analysis
class AnalysisUpdate(BaseModel):
    filings_analyzed: Optional[List[str]] = None
    analysis_result: Optional[AnalysisResult] = None 