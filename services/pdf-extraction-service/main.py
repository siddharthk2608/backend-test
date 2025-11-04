# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from datetime import datetime

# Import our processing modules
from pdf_extractor import PDFExtractor
from llm_mapper import LLMMapper
from models import TaxReturnResponse, MetaData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Tax Return PDF Processor with Dynamic Chunking",
    description="API for processing tax return PDFs with dynamic chunk sizing and early stopping",
    version="3.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors
pdf_extractor = PDFExtractor()
llm_mapper = LLMMapper()


@app.post("/process-tax-return", response_model=TaxReturnResponse)
async def process_tax_return(file: UploadFile = File(...)):
    """
    Process uploaded tax return PDF with dynamic chunking and early stopping.
    
    Features:
    - Dynamic chunk sizing based on PDF size (min 3 pages per chunk)
    - Early stopping when all required fields are filled
    - Intelligent field tracking and progress monitoring
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        TaxReturnResponse: Structured tax return data
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF files are accepted."
            )
        
        logger.info(f" Processing file: {file.filename}")
        start_time = datetime.utcnow()
        
        # Read file content
        pdf_content = await file.read()
        file_size_mb = len(pdf_content) / (1024 * 1024)
        logger.info(f"   File size: {file_size_mb:.2f} MB")
        
        # Step 1: Extract raw data from PDF
        logger.info(" Extracting data from PDF...")
        extracted_data = await pdf_extractor.extract_pdf_data(pdf_content)
        
        if not extracted_data:
            raise HTTPException(
                status_code=422,
                detail="Failed to extract data from PDF. The file may be corrupted or empty."
            )
        
        num_pages = extracted_data.get('metadata', {}).get('num_pages', 0)
        logger.info(f"    Extracted data from {num_pages} pages")
        
        # Step 2: Map data with dynamic chunking and early stopping
        logger.info(" Mapping extracted data with dynamic chunking...")
        structured_data = await llm_mapper.map_to_structure(extracted_data)
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f" Successfully completed in {processing_time:.2f} seconds")
        
        # Step 3: Calculate statistics
        filled_count = sum(
            1 for v in structured_data.dict().values() 
            if v is not None and v != ""
        )
        total_count = len(structured_data.dict())
        
        response = TaxReturnResponse(
            meta=MetaData(brand="Accountingbiz"),
            success=True,
            message=f"Tax return processed successfully ({filled_count}/{total_count} fields filled)",
            answers=structured_data,
            processing_metadata={
                "filename": file.filename,
                "file_size_mb": round(file_size_mb, 2),
                "processed_at": end_time.isoformat(),
                "processing_time_seconds": round(processing_time, 2),
                "total_pages": num_pages,
                "fields_extracted": len(extracted_data.get('form_fields', {})),
                "tables_found": len(extracted_data.get('tables', [])),
                "fields_filled": filled_count,
                "fields_total": total_count,
                "completion_percentage": round((filled_count / total_count) * 100, 2),
                "features_used": {
                    "dynamic_chunking": True,
                    "early_stopping": True,
                    "min_chunk_size": 3
                }
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing tax return: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the tax return: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0",
        "features": {
            "dynamic_chunking": True,
            "early_stopping": True,
            "min_chunk_size": 3,
            "max_chunk_size": 10
        }
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Tax Return PDF Processor API with Dynamic Chunking",
        "version": "3.0.0",
        "features": [
            " Dynamic chunk sizing based on PDF size",
            " Early stopping when all fields filled",
            " Minimum 3 pages per chunk",
            " Intelligent missing field tracking",
            " Real-time progress monitoring",
            " Optimized API usage"
        ],
        "chunking_strategy": {
            "small_pdfs_10_pages": "3 pages per chunk",
            "small_medium_11_20_pages": "4 pages per chunk",
            "medium_21_50_pages": "5-8 pages per chunk",
            "large_51_100_pages": "8-10 pages per chunk",
            "very_large_100_plus_pages": "10 pages per chunk",
            "minimum_guaranteed": "3 pages per chunk"
        },
        "endpoints": {
            "process": "/process-tax-return",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.post("/estimate-processing")
async def estimate_processing(file: UploadFile = File(...)):
    """
    Estimate processing requirements without actually processing the PDF
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        Estimation details including chunks and API calls
    """
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF files are accepted."
            )
        
        # Read file
        pdf_content = await file.read()
        file_size_mb = len(pdf_content) / (1024 * 1024)
        
        # Extract metadata only
        extracted_data = await pdf_extractor.extract_pdf_data(pdf_content)
        num_pages = extracted_data.get('metadata', {}).get('num_pages', 0)
        
        # Get estimates
        chunk_manager = llm_mapper.chunk_manager
        estimates = chunk_manager.estimate_api_calls(num_pages)
        
        return {
            "success": True,
            "file_info": {
                "filename": file.filename,
                "size_mb": round(file_size_mb, 2),
                "total_pages": num_pages
            },
            "chunking_strategy": {
                "chunk_size": estimates['chunk_size'],
                "min_chunk_size_guaranteed": chunk_manager.min_chunk_size,
                "max_chunks": estimates['max_api_calls']
            },
            "api_call_estimates": {
                "worst_case_api_calls": estimates['max_api_calls'],
                "estimated_with_early_stopping": estimates['estimated_api_calls_with_early_stop'],
                "potential_savings": estimates['potential_api_call_savings']
            },
            "cost_estimates_usd": {
                "max_cost": estimates['max_cost_usd'],
                "estimated_cost_with_early_stop": estimates['estimated_cost_with_early_stop_usd']
            },
            "processing_time_estimate": {
                "min_seconds": estimates['estimated_api_calls_with_early_stop'] * 2,
                "max_seconds": estimates['max_api_calls'] * 3
            }
        }
        
    except Exception as e:
        logger.error(f"Error estimating processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error estimating processing: {str(e)}"
        )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
