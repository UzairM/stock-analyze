from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routes.stocks import router as stocks_router
from app.routes.companies import router as companies_router
from app.routes.analyses import router as analyses_router
from app.database.connection import connect_to_mongo, close_mongo_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Biotech Stock Analysis API",
    description="API for analyzing biotech stocks",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stocks_router)
app.include_router(companies_router)
app.include_router(analyses_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Biotech Stock Analysis API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    logger.info("FastAPI application startup complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()
    logger.info("FastAPI application shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 