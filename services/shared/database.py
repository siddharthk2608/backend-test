# shared/database.py
"""
MongoDB Database Configuration and Utilities
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)


class Database:
    """MongoDB Database Manager"""
    
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    # Configuration
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "tax_planning_db")
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        try:
            cls.client = AsyncIOMotorClient(cls.MONGODB_URL)
            cls.db = cls.client[cls.DATABASE_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB: {cls.DATABASE_NAME}")
            logger.info(f"   URL: {cls.MONGODB_URL}")
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_database(cls):
        """Get database instance"""
        return cls.db
    
    @classmethod
    def get_collection(cls, collection_name: str):
        """Get collection by name"""
        return cls.db[collection_name]


# Synchronous client for initialization scripts
def get_sync_client():
    """Get synchronous MongoDB client"""
    url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    return MongoClient(url)


def create_indexes():
    """Create database indexes for better performance"""
    client = get_sync_client()
    db = client[Database.DATABASE_NAME]
    
    logger.info("Creating database indexes...")
    
    # tax_returns collection indexes
    tax_returns = db.tax_returns
    tax_returns.create_index([("user_id", 1), ("tax_year", -1)])
    tax_returns.create_index([("created_at", -1)])
    tax_returns.create_index([("user_id", 1)])
    
    # tax_analyses collection indexes
    tax_analyses = db.tax_analyses
    tax_analyses.create_index([("user_id", 1), ("tax_year", -1)])
    tax_analyses.create_index([("analysis_date", -1)])
    tax_analyses.create_index([("user_id", 1)])
    
    # users collection indexes
    users = db.users
    users.create_index([("user_id", 1)], unique=True)
    users.create_index([("email", 1)], unique=True, sparse=True)
    
    logger.info("✅ Database indexes created successfully")
    
    client.close()


if __name__ == "__main__":
    # Test database connection
    import asyncio
    
    async def test_connection():
        await Database.connect_db()
        db = Database.get_database()
        
        # Test insert
        result = await db.test_collection.insert_one({"test": "data"})
        print(f"✅ Test insert successful: {result.inserted_id}")
        
        # Test find
        doc = await db.test_collection.find_one({"test": "data"})
        print(f"✅ Test find successful: {doc}")
        
        # Clean up
        await db.test_collection.delete_one({"test": "data"})
        print("✅ Test cleanup successful")
        
        await Database.close_db()
    
    asyncio.run(test_connection())