from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from bson import ObjectId
from ..models.stock import Stock, StockCreate, StockUpdate
from ..database.connection import get_database

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[Stock])
async def get_stocks(
    skip: int = 0, 
    limit: int = 100,
    sector: Optional[str] = None,
    db = Depends(get_database)
):
    """
    Retrieve a list of stocks.
    
    - **skip**: Number of stocks to skip
    - **limit**: Maximum number of stocks to return
    - **sector**: Filter by sector
    """
    query = {}
    if sector:
        query["sector"] = sector
    
    stocks = []
    cursor = db.stocks.find(query).skip(skip).limit(limit)
    async for document in cursor:
        document["id"] = str(document["_id"])
        stocks.append(document)
    
    return stocks

@router.post("/", response_model=Stock, status_code=status.HTTP_201_CREATED)
async def create_stock(stock: StockCreate, db = Depends(get_database)):
    """
    Create a new stock entry.
    """
    # Check if stock already exists
    if await db.stocks.find_one({"symbol": stock.symbol}):
        raise HTTPException(
            status_code=400,
            detail=f"Stock with symbol {stock.symbol} already exists"
        )
    
    stock_dict = stock.dict()
    result = await db.stocks.insert_one(stock_dict)
    
    created_stock = await db.stocks.find_one({"_id": result.inserted_id})
    created_stock["id"] = str(created_stock["_id"])
    
    return created_stock

@router.get("/{symbol}", response_model=Stock)
async def get_stock(symbol: str, db = Depends(get_database)):
    """
    Retrieve a specific stock by symbol.
    """
    stock = await db.stocks.find_one({"symbol": symbol})
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol {symbol} not found"
        )
    
    stock["id"] = str(stock["_id"])
    return stock

@router.put("/{symbol}", response_model=Stock)
async def update_stock(
    symbol: str, 
    stock_update: StockUpdate,
    db = Depends(get_database)
):
    """
    Update a stock entry.
    """
    stock = await db.stocks.find_one({"symbol": symbol})
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol {symbol} not found"
        )
    
    update_data = {k: v for k, v in stock_update.dict().items() if v is not None}
    
    if update_data:
        await db.stocks.update_one(
            {"symbol": symbol},
            {"$set": update_data}
        )
    
    updated_stock = await db.stocks.find_one({"symbol": symbol})
    updated_stock["id"] = str(updated_stock["_id"])
    
    return updated_stock

@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(symbol: str, db = Depends(get_database)):
    """
    Delete a stock entry.
    """
    result = await db.stocks.delete_one({"symbol": symbol})
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Stock with symbol {symbol} not found"
        )
    
    return None 