import asyncio
import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB connection settings from environment variables
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "biotech_analysis_db")

async def setup_database():
    """
    Connect to MongoDB, create the database, and verify connectivity.
    """
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGO_URL)
        
        # Verify connection is successful
        await client.admin.command('ping')
        logger.info(f"Connected to MongoDB at {MONGO_URL}")
        
        # Create database (in MongoDB, databases are created when you first store data)
        db = client[DB_NAME]
        
        # Create a test collection and document to ensure the database is created
        result = await db.test_collection.insert_one({"test": "data"})
        logger.info(f"Created test document with id: {result.inserted_id}")
        
        # List all databases to confirm our database exists
        database_list = await client.list_database_names()
        logger.info(f"Available databases: {', '.join(database_list)}")
        
        if DB_NAME in database_list:
            logger.info(f"Database '{DB_NAME}' created successfully")
        else:
            logger.warning(f"Database '{DB_NAME}' not found in database list")
        
        # Clean up test collection
        await db.test_collection.delete_many({})
        logger.info("Cleaned up test collection")
        
        # Close connection
        client.close()
        logger.info("MongoDB connection closed")
        
        return True
    except ConnectionFailure as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        return False

if __name__ == "__main__":
    logger.info(f"Setting up database '{DB_NAME}'")
    success = asyncio.run(setup_database())
    
    if success:
        logger.info("Database setup completed successfully")
    else:
        logger.error("Database setup failed") 