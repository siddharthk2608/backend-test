# tax-data-service/main.py
"""
Tax Data Service - MongoDB CRUD operations for tax returns
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from shared.database import Database
from shared.db_models import (
    TaxReturnDocument,
    TaxAnalysisDocument,
    UserDocument,
    model_to_dict,
    dict_to_model
)

# Import logging configuration
from logging_config import setup_logger, get_logger

# Setup logger
logger = setup_logger(
    service_name="tax-data",
    log_level="INFO"
)

# Initialize FastAPI app
app = FastAPI(
    title="Tax Data Service",
    description="CRUD operations for tax returns and analyses",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("Starting up Tax Data Service...")
    await Database.connect_db()
    logger.info("Database connected successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("Shutting down Tax Data Service...")
    await Database.close_db()
    logger.info("Database connection closed")


# ==================== REQUEST/RESPONSE MODELS ====================

class TaxReturnCreate(BaseModel):
    """Request model for creating a tax return"""
    user_id: str
    tax_year: int
    personal_info: Dict[str, Any]
    income: Dict[str, Any]
    deductions: Optional[Dict[str, Any]] = None
    credits: Optional[Dict[str, Any]] = None
    dependents: Optional[List[Dict[str, Any]]] = None
    source: str = "web_form"


class TaxReturnUpdate(BaseModel):
    """Request model for updating a tax return"""
    personal_info: Optional[Dict[str, Any]] = None
    income: Optional[Dict[str, Any]] = None
    deductions: Optional[Dict[str, Any]] = None
    credits: Optional[Dict[str, Any]] = None
    dependents: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = None


class TaxReturnResponse(BaseModel):
    """Response model for tax return"""
    id: str
    user_id: str
    tax_year: int
    created_at: datetime
    updated_at: datetime
    personal_info: Dict[str, Any]
    income: Dict[str, Any]
    deductions: Optional[Dict[str, Any]] = None
    credits: Optional[Dict[str, Any]] = None
    dependents: Optional[List[Dict[str, Any]]] = None
    source: str
    status: str


class AnalysisListResponse(BaseModel):
    """Response model for list of analyses"""
    id: str
    user_id: str
    tax_year: int
    analysis_date: datetime
    total_potential_savings: float
    num_recommendations: int


# ==================== TAX RETURNS ENDPOINTS ====================

@app.post("/api/v1/tax-returns", response_model=TaxReturnResponse)
async def create_tax_return(tax_return: TaxReturnCreate):
    """Create a new tax return"""
    try:
        logger.info(f"Creating tax return for user {tax_return.user_id}, year {tax_return.tax_year}")
        
        db = Database.get_database()
        
        # Create document
        doc = TaxReturnDocument(
            user_id=tax_return.user_id,
            tax_year=tax_return.tax_year,
            personal_info=tax_return.personal_info,
            income=tax_return.income,
            deductions=tax_return.deductions,
            credits=tax_return.credits,
            dependents=tax_return.dependents,
            source=tax_return.source
        )
        
        # Insert into database
        result = await db.tax_returns.insert_one(model_to_dict(doc))
        
        # Fetch the created document
        created_doc = await db.tax_returns.find_one({"_id": result.inserted_id})
        
        logger.info(f"Tax return created with ID: {result.inserted_id}")
        
        return TaxReturnResponse(
            id=str(created_doc["_id"]),
            **{k: v for k, v in created_doc.items() if k != "_id"}
        )
        
    except Exception as e:
        logger.error(f"Error creating tax return: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tax-returns/{return_id}", response_model=TaxReturnResponse)
async def get_tax_return(return_id: str):
    """Get a tax return by ID"""
    try:
        from bson import ObjectId
        
        db = Database.get_database()
        doc = await db.tax_returns.find_one({"_id": ObjectId(return_id)})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Tax return not found")
        
        logger.info(f"Retrieved tax return: {return_id}")
        
        return TaxReturnResponse(
            id=str(doc["_id"]),
            **{k: v for k, v in doc.items() if k != "_id"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tax return: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tax-returns/user/{user_id}", response_model=List[TaxReturnResponse])
async def get_user_tax_returns(
    user_id: str,
    tax_year: Optional[int] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """Get all tax returns for a user"""
    try:
        db = Database.get_database()
        
        # Build query
        query = {"user_id": user_id}
        if tax_year:
            query["tax_year"] = tax_year
        
        # Fetch documents
        cursor = db.tax_returns.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        logger.info(f"Retrieved {len(docs)} tax returns for user {user_id}")
        
        return [
            TaxReturnResponse(
                id=str(doc["_id"]),
                **{k: v for k, v in doc.items() if k != "_id"}
            )
            for doc in docs
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving tax returns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/tax-returns/{return_id}", response_model=TaxReturnResponse)
async def update_tax_return(return_id: str, update: TaxReturnUpdate):
    """Update a tax return"""
    try:
        from bson import ObjectId
        
        db = Database.get_database()
        
        # Build update document
        update_doc = {"updated_at": datetime.utcnow()}
        if update.personal_info:
            update_doc["personal_info"] = update.personal_info
        if update.income:
            update_doc["income"] = update.income
        if update.deductions:
            update_doc["deductions"] = update.deductions
        if update.credits:
            update_doc["credits"] = update.credits
        if update.dependents is not None:
            update_doc["dependents"] = update.dependents
        if update.status:
            update_doc["status"] = update.status
        
        # Update document
        result = await db.tax_returns.update_one(
            {"_id": ObjectId(return_id)},
            {"$set": update_doc}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Tax return not found")
        
        # Fetch updated document
        updated_doc = await db.tax_returns.find_one({"_id": ObjectId(return_id)})
        
        logger.info(f"Updated tax return: {return_id}")
        
        return TaxReturnResponse(
            id=str(updated_doc["_id"]),
            **{k: v for k, v in updated_doc.items() if k != "_id"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tax return: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/tax-returns/{return_id}")
async def delete_tax_return(return_id: str):
    """Delete a tax return"""
    try:
        from bson import ObjectId
        
        db = Database.get_database()
        result = await db.tax_returns.delete_one({"_id": ObjectId(return_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Tax return not found")
        
        logger.info(f"Deleted tax return: {return_id}")
        
        return {"message": "Tax return deleted successfully", "id": return_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tax return: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ANALYSES ENDPOINTS ====================

@app.get("/api/v1/analyses/user/{user_id}", response_model=List[AnalysisListResponse])
async def get_user_analyses(
    user_id: str,
    tax_year: Optional[int] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """Get all analyses for a user"""
    try:
        db = Database.get_database()
        
        # Build query
        query = {"user_id": user_id}
        if tax_year:
            query["tax_year"] = tax_year
        
        # Fetch documents
        cursor = db.tax_analyses.find(query).sort("analysis_date", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        logger.info(f"Retrieved {len(docs)} analyses for user {user_id}")
        
        return [
            AnalysisListResponse(
                id=str(doc["_id"]),
                user_id=doc["user_id"],
                tax_year=doc["tax_year"],
                analysis_date=doc["analysis_date"],
                total_potential_savings=doc["processing_metadata"]["total_potential_savings"],
                num_recommendations=len(doc["recommendations"])
            )
            for doc in docs
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving analyses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get a complete analysis by ID"""
    try:
        from bson import ObjectId
        
        db = Database.get_database()
        doc = await db.tax_analyses.find_one({"_id": ObjectId(analysis_id)})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        logger.info(f"Retrieved analysis: {analysis_id}")
        
        # Convert ObjectId to string
        doc["_id"] = str(doc["_id"])
        if doc.get("tax_return_id"):
            doc["tax_return_id"] = str(doc["tax_return_id"])
        
        return doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH CHECK ====================

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = Database.get_database()
        await db.command("ping")
        
        return {
            "status": "healthy",
            "service": "tax-data",
            "version": "1.0.0",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "tax-data",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Tax Data Service",
        "version": "1.0.0",
        "database": "MongoDB",
        "endpoints": {
            "create_tax_return": "POST /api/v1/tax-returns",
            "get_tax_return": "GET /api/v1/tax-returns/{id}",
            "get_user_returns": "GET /api/v1/tax-returns/user/{user_id}",
            "update_tax_return": "PUT /api/v1/tax-returns/{id}",
            "delete_tax_return": "DELETE /api/v1/tax-returns/{id}",
            "get_user_analyses": "GET /api/v1/analyses/user/{user_id}",
            "get_analysis": "GET /api/v1/analyses/{id}",
            "health": "GET /api/v1/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Tax Data Service on port 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)