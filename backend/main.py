import os
from dotenv import load_dotenv
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')
import sys
import os as _os
# Add vendored crewai package to path
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), 'vendor'))
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from crew_agents import DocumentAnalysisCrew
from typing import Dict, Any, List
from rate_limiter import EnhancedRateLimiter
from orchestrator import orchestrator
from services.upload_service import upload_service
from services.database_service import database_service
from utils.logging_utils import setup_json_logging, log_execution_time, MetricsLogger
import time
import traceback

# Configure logging
logger = setup_json_logging("api")
metrics_logger = MetricsLogger("api")

app = FastAPI(title="Document Analysis API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3004"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DocumentAnalysisCrew
crew = DocumentAnalysisCrew()

# Initialize rate limiter
limiter = EnhancedRateLimiter(capacity=30, leak_rate_per_sec=5, max_queue_size=20)

class Query(BaseModel):
    query: str

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log request metrics"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    metrics_logger.log_metrics({
        "endpoint": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "duration": duration
    })
    
    return response

@app.get("/health")
@log_execution_time(logger)
async def health_check():
    """Health check endpoint"""
    try:
        health_status = orchestrator.get_health_status()
        system_metrics = metrics_logger.get_system_metrics()
        
        # Get detailed database connection status
        db_status = database_service.get_connection_status()
        
        # Create a new HealthStatus with updated services
        updated_services = dict(health_status.services)
        
        # Add detailed database status
        updated_services["database_service"] = {
            "connected": db_status["is_connected"],
            "last_checked": db_status["last_checked"],
            "connection_attempts": db_status["connection_attempts"],
            "successful_queries": db_status["successful_queries"],
            "failed_queries": db_status["failed_queries"],
            "client_initialized": db_status["client_initialized"]
        }
        
        # Add detailed environment diagnostics
        env_diagnostics = db_status["env_diagnostics"]
        
        return {
            "services": updated_services,
            "system": system_metrics,
            "database": {
                "status": db_status["is_connected"],
                "env_setup": env_diagnostics
            }
        }
    except Exception as e:
        logger.error("Health check failed", exc_info=True)
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_details)

@app.get("/diagnostics/database")
@log_execution_time(logger)
async def database_diagnostics():
    """Detailed database diagnostics endpoint"""
    try:
        # Get comprehensive database status
        db_status = database_service.get_connection_status()
        
        # Force a connection check
        connection_active = database_service.check_connection()
        
        # Check if tables exist by trying simple queries
        tables_status = {}
        
        if connection_active:
            try:
                # Check uploads table
                uploads = await database_service.get_all_documents()
                tables_status["uploads"] = {
                    "exists": True,
                    "count": len(uploads),
                    "sample": uploads[0] if uploads else None
                }
            except Exception as e:
                tables_status["uploads"] = {
                    "exists": False,
                    "error": str(e)
                }
                
            # Check document_chunks table if we have documents
            if uploads:
                try:
                    first_doc_id = uploads[0]["id"]
                    chunks = await database_service.get_document_chunks(first_doc_id)
                    tables_status["document_chunks"] = {
                        "exists": True,
                        "count": len(chunks),
                        "sample": chunks[0] if chunks else None
                    }
                except Exception as e:
                    tables_status["document_chunks"] = {
                        "exists": False,
                        "error": str(e)
                    }
        
        # Prepare comprehensive diagnostics
        diagnostics = {
            "connection": {
                "is_connected": db_status["is_connected"],
                "last_checked": db_status["last_checked"],
                "connection_attempts": db_status["connection_attempts"],
                "successful_queries": db_status["successful_queries"],
                "failed_queries": db_status["failed_queries"]
            },
            "environment": db_status["env_diagnostics"],
            "tables": tables_status
        }
        
        # Include error details if there was a problem
        if not db_status["is_connected"] and "last_error" in db_status and db_status["last_error"]:
            error = db_status["last_error"]
            diagnostics["last_error"] = {
                "message": error["message"],
                "type": error["error_type"],
                "timestamp": error["timestamp"],
                "context": error["context"]
            }
        
        return diagnostics
    except Exception as e:
        logger.error("Database diagnostics failed", exc_info=True)
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_details)

@app.post("/upload")
@log_execution_time(logger)
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    # Create request context
    request_id = orchestrator.create_request_context()
    
    try:
        # Check rate limit
        if not await limiter.allow_request_with_queue(timeout=5.0):
            logger.warning("Rate limit exceeded for upload request", extra={
                "request_id": request_id
            })
            return JSONResponse(
                content={"error": "Server is busy. Please try again in a few seconds."},
                status_code=429
            )
        
        # Check database connection first
        if not database_service.check_connection():
            error_msg = "Database connection unavailable. Please check /diagnostics/database for details."
            logger.error(error_msg, extra={"request_id": request_id})
            return JSONResponse(
                content={"error": error_msg},
                status_code=503  # Service Unavailable
            )
            
        # Handle upload through orchestrator
        response = await orchestrator.handle_file_upload(file, request_id)
        
        # Convert datetime to ISO format string in the response
        return JSONResponse(
            content=response.model_dump(mode='json', exclude_none=True),
            status_code=200
        )
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error("Error in upload endpoint", extra={
            "request_id": request_id,
            "error": str(e),
            "traceback": error_traceback
        }, exc_info=True)
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_traceback.split("\n")
            },
            status_code=500
        )
    finally:
        orchestrator.cleanup_request_context(request_id)

@app.post("/query")
@log_execution_time(logger)
async def query_documents(query_data: Query = Body(...)) -> Dict[str, Any]:
    # Create request context
    request_id = orchestrator.create_request_context()
    
    try:
        # Check rate limit
        if not await limiter.allow_request_with_queue(timeout=10.0):
            logger.warning("Rate limit exceeded for query request", extra={
                "request_id": request_id
            })
            return JSONResponse(
                content={"error": "Server is busy. Please try again in a few seconds."},
                status_code=429
            )
        
        # Check database connection first
        if not database_service.check_connection():
            error_msg = "Database connection unavailable. Please check /diagnostics/database for details."
            logger.error(error_msg, extra={"request_id": request_id})
            return JSONResponse(
                content={"error": error_msg},
                status_code=503  # Service Unavailable
            )
            
        # Get uploaded documents from database
        documents = await upload_service.get_uploaded_documents()
        if not documents:
            logger.warning("Query attempted with no documents uploaded", extra={
                "request_id": request_id
            })
            raise HTTPException(
                status_code=400,
                detail="No documents uploaded yet"
            )
        
        # Handle query through orchestrator
        response = await orchestrator.handle_query(query_data.query, request_id)
        return JSONResponse(
            content=response.model_dump(mode='json', exclude_none=True),
            status_code=200
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error("Error in query endpoint", extra={
            "request_id": request_id,
            "error": str(e),
            "traceback": error_traceback
        }, exc_info=True)
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_traceback.split("\n")
            },
            status_code=500
        )
    finally:
        orchestrator.cleanup_request_context(request_id)

@app.get("/documents")
@log_execution_time(logger)
async def get_documents():
    """Get list of uploaded documents"""
    try:
        # Simple endpoints can use basic rate limiting
        if not limiter.allow_request():
            logger.warning("Rate limit exceeded for documents list request")
            return JSONResponse(
                content={"error": "Rate limit exceeded. Please try again later."},
                status_code=429
            )
            
        # Check database connection first
        if not database_service.check_connection():
            error_msg = "Database connection unavailable. Please check /diagnostics/database for details."
            logger.error(error_msg)
            return JSONResponse(
                content={"error": error_msg},
                status_code=503  # Service Unavailable
            )
            
        # Get documents from database or local storage
        documents = await upload_service.get_uploaded_documents()
        
        # Format for API response
        doc_list = [
            {
                "id": doc.get("id"),
                "name": doc["name"],
                "type": doc.get("type"),
                "size": doc.get("size"),
                "uploaded_at": doc.get("uploaded_at")
            }
            for doc in documents
        ]
        
        return {"documents": doc_list}
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error("Error getting documents list", exc_info=True)
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_traceback.split("\n")
            },
            status_code=500
        )

@app.delete("/documents/{document_id}")
@log_execution_time(logger)
async def delete_document(document_id: int):
    """Delete a document by ID"""
    try:
        # Simple endpoints can use basic rate limiting
        if not limiter.allow_request():
            logger.warning("Rate limit exceeded for document deletion request")
            return JSONResponse(
                content={"error": "Rate limit exceeded. Please try again later."},
                status_code=429
            )
            
        # Check database connection first
        if not database_service.check_connection():
            error_msg = "Database connection unavailable. Please check /diagnostics/database for details."
            logger.error(error_msg)
            return JSONResponse(
                content={"error": error_msg},
                status_code=503  # Service Unavailable
            )
            
        # Find the document in our list
        documents = await upload_service.get_uploaded_documents()
        document = next((doc for doc in documents if doc.get("id") == document_id), None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # Delete from database and filesystem
        await upload_service.cleanup_file(document["name"])
        
        return {"status": "success", "message": f"Document {document_id} deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error deleting document {document_id}", exc_info=True)
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_traceback.split("\n")
            },
            status_code=500
        )

@app.post("/documents/search")
@log_execution_time(logger)
async def search_documents_endpoint(query_data: Query = Body(...)):
    """Search document chunks by text query"""
    try:
        # Simple endpoints can use basic rate limiting
        if not limiter.allow_request():
            logger.warning("Rate limit exceeded for document search request")
            return JSONResponse(
                content={"error": "Rate limit exceeded. Please try again later."},
                status_code=429
            )
        # Check database connection first
        if not database_service.check_connection():
            error_msg = "Database connection unavailable. Please check /diagnostics/database for details."
            logger.error(error_msg)
            return JSONResponse(
                content={"error": error_msg},
                status_code=503  # Service Unavailable
            )
        # Perform the search
        results = await database_service.search_documents(query_data.query)
        return {"results": results}
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error("Error in document search endpoint", exc_info=True)
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_traceback.split("\n")
            },
            status_code=500
        )

@app.get("/tags")
@log_execution_time(logger)
async def get_tags():
    try:
        tags = await database_service.get_tags()
        return {"tags": tags}
    except Exception as e:
        logger.error("Error getting tags", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

class TagCreate(BaseModel):
    name: str
    color: str = None

@app.post("/tags")
@log_execution_time(logger)
async def add_tag(tag: TagCreate):
    try:
        tag_id = await database_service.add_tag(tag.name, tag.color)
        if tag_id:
            return {"id": tag_id}
        else:
            return JSONResponse(content={"error": "Failed to add tag"}, status_code=400)
    except Exception as e:
        logger.error("Error adding tag", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.delete("/tags/{tag_id}")
@log_execution_time(logger)
async def delete_tag(tag_id: int):
    try:
        success = await database_service.delete_tag(tag_id)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(content={"error": "Failed to delete tag"}, status_code=400)
    except Exception as e:
        logger.error("Error deleting tag", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/documents/{document_id}/tags")
@log_execution_time(logger)
async def get_document_tags(document_id: int):
    try:
        tags = await database_service.get_document_tags(document_id)
        return {"tags": tags}
    except Exception as e:
        logger.error("Error getting document tags", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

class TagAssociation(BaseModel):
    tag_id: int

@app.post("/documents/{document_id}/tags")
@log_execution_time(logger)
async def add_tag_to_document(document_id: int, assoc: TagAssociation):
    try:
        success = await database_service.add_tag_to_document(document_id, assoc.tag_id)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(content={"error": "Failed to add tag to document"}, status_code=400)
    except Exception as e:
        logger.error("Error adding tag to document", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.delete("/documents/{document_id}/tags/{tag_id}")
@log_execution_time(logger)
async def remove_tag_from_document(document_id: int, tag_id: int):
    try:
        success = await database_service.remove_tag_from_document(document_id, tag_id)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(content={"error": "Failed to remove tag from document"}, status_code=400)
    except Exception as e:
        logger.error("Error removing tag from document", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/documents/vector_search")
@log_execution_time(logger)
async def vector_search_documents_endpoint(query_data: Query = Body(...)):
    """Semantic vector search for document chunks using local embeddings"""
    try:
        if not limiter.allow_request():
            logger.warning("Rate limit exceeded for vector search request")
            return JSONResponse(
                content={"error": "Rate limit exceeded. Please try again later."},
                status_code=429
            )
        if not database_service.check_connection():
            error_msg = "Database connection unavailable. Please check /diagnostics/database for details."
            logger.error(error_msg)
            return JSONResponse(
                content={"error": error_msg},
                status_code=503
            )
        results = await database_service.vector_search_documents(query_data.query)
        return {"results": results}
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error("Error in vector search endpoint", exc_info=True)
        return JSONResponse(
            content={
                "error": str(e),
                "details": error_traceback.split("\n")
            },
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting API server")
    uvicorn.run(app, host="0.0.0.0", port=8081)
