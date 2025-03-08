from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

# Helper for ObjectId conversion
def str_to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)

class StockBase(BaseModel):
    """Base model for stock data."""
    symbol: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    sector: Optional[str] = Field(None, description="Industry sector")
    is_biotech: bool = Field(True, description="Whether the stock is a biotech company")

class StockCreate(StockBase):
    """Model for creating a new stock entry."""
    pass

class StockInDB(StockBase):
    """Model for stock data as stored in the database."""
    id: str = Field(..., alias="_id", description="MongoDB ObjectID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Stock(StockInDB):
    """Model for stock data returned to the client."""
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class StockUpdate(BaseModel):
    """Model for updating stock data."""
    company_name: Optional[str] = None
    sector: Optional[str] = None
    is_biotech: Optional[bool] = None 