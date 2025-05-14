from typing import Dict, Any, List
import time
import uuid
from datetime import datetime
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ValidationError
from utils.logging_utils import setup_json_logging, log_execution_time, MetricsLogger
from utils.validation_utils import sanitize_numeric, validate_datetime
from utils.transaction_utils import transaction_manager, FileResource, CleanupError
from services.upload_service import upload_service
from services.csv_parser_service import csv_parser
from crew_agents import DocumentAnalysisCrew
import anthropic
import os
from schemas.api_schemas import (
    UploadResponse,
    QueryResponse,
    ErrorResponse,
    HealthStatus,
    CSVAnalysisResult,
    ChartData,
    NarrativeInsight
)
import asyncio
import traceback
from services.document_processor_service import document_processor

# Configure logging
logger = setup_json_logging("orchestrator")
metrics_logger = MetricsLogger("orchestrator")

class RequestContext:
    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.service_timings = {}

    def log_service_timing(self, service_name: str, duration: float):
        self.service_timings[service_name] = duration
        metrics_logger.log_metrics({
            "service": service_name,
            "duration": duration
        }, self.request_id)

class Orchestrator:
    def __init__(self):
        """Initialize the orchestrator with required services"""
        self._request_contexts: Dict[str, RequestContext] = {}
        self._health_status = {
            "upload_service": True,
            "parser_service": True,
            "analysis_service": True,
            "visualization_service": True
        }
        # Log initial system metrics
        self._log_system_metrics()
        # Initialize CrewAI analysis helper
        self.crew = DocumentAnalysisCrew()
        # Initialize Anthropic client
        self.anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _log_system_metrics(self):
        """Log system metrics periodically"""
        system_metrics = metrics_logger.get_system_metrics()
        metrics_logger.log_metrics(system_metrics)

    def _get_file_type(self, filename: str) -> str:
        """Get file MIME type based on extension"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        mime_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }
        return mime_types.get(extension, 'application/octet-stream')

    @log_execution_time(logger)
    def create_request_context(self) -> str:
        """Create a new request context and return its ID"""
        context = RequestContext()
        self._request_contexts[context.request_id] = context
        logger.info("Created request context", extra={"request_id": context.request_id})
        return context.request_id

    @log_execution_time(logger)
    async def handle_file_upload(self, file_data: UploadFile, request_id: str) -> UploadResponse:
        """Orchestrate file upload process"""
        # Start a transaction for this request
        with transaction_manager.start_transaction(request_id) as transaction:
            try:
                logger.info("Starting file upload process", extra={"request_id": request_id})
                start_time = time.time()
                
                # Handle file upload
                upload_result = await upload_service.upload_file(file_data, request_id)
                transaction.register(FileResource(upload_result.path, is_temp=False))
                
                logger.info(f"Processing document: {file_data.filename}", extra={
                    "request_id": request_id,
                    "file_name": file_data.filename
                })

                try:
                    # Get document ID from database
                    document_id = None
                    documents = await upload_service.get_uploaded_documents()
                    for doc in documents:
                        if doc["name"] == file_data.filename:
                            document_id = doc.get("id")
                            break

                    if not document_id:
                        logger.error("Document ID not found after upload", extra={"request_id": request_id})
                        logger.error(traceback.format_exc())
                        raise ValueError("Document ID not found after upload")

                    logger.info(f"Calling process_document for document_id={document_id}", extra={"request_id": request_id})
                    # Process document through document processor service
                    success = await document_processor.process_document(
                        document_id=document_id,
                        file_path=upload_result.path,
                        file_type=self._get_file_type(file_data.filename)
                    )
                    logger.info(f"process_document returned: {success}", extra={"request_id": request_id})

                    if not success:
                        logger.error("Document processing failed (process_document returned False)", extra={"request_id": request_id})
                        logger.error(traceback.format_exc())
                        raise Exception("Document processing failed")

                    # If it's a CSV file, also get analysis results
                    analysis_result = None
                    if file_data.filename.lower().endswith('.csv'):
                        logger.info("CSV detected, calling csv_parser.parse_file", extra={"request_id": request_id})
                        try:
                            analysis_result, _ = csv_parser.parse_file(upload_result.path, request_id)
                            logger.info(f"csv_parser.parse_file returned: {analysis_result}", extra={"request_id": request_id})
                        except Exception as e:
                            logger.error(f"csv_parser.parse_file failed: {e}", extra={"request_id": request_id})
                            logger.error(traceback.format_exc())
                            analysis_result = None
                        # Ensure statistics is always present and valid
                        if analysis_result is None:
                            analysis_result = None

                    duration = time.time() - start_time
                    self._request_contexts[request_id].log_service_timing("document_processing", duration)

                    try:
                        file_info = {
                            "filename": upload_result.filename,
                            "path": upload_result.path,
                            "status": upload_result.status
                        }
                        logger.info(f"Constructing UploadResponse for document_id={document_id}", extra={"request_id": request_id})
                        return UploadResponse(
                            request_id=request_id,
                            file_info=file_info,
                            statistics=analysis_result if analysis_result is not None else "No analysis available",
                            message="File uploaded and processed successfully",
                            timestamp=validate_datetime(datetime.utcnow()).isoformat()
                        )
                    except ValidationError as ve:
                        logger.error("Response validation failed", extra={
                            "request_id": request_id,
                            "validation_errors": ve.errors()
                        })
                        logger.error(traceback.format_exc())
                        raise HTTPException(
                            status_code=500,
                            detail=ErrorResponse(
                                error="Response validation failed",
                                error_type="ValidationError",
                                request_id=request_id,
                                details={"validation_errors": ve.errors()}
                            ).model_dump()
                        )

                except Exception as e:
                    logger.error("Document processing failed (inner block)", extra={
                        "request_id": request_id,
                        "error": str(e)
                    })
                    logger.error(traceback.format_exc())
                    raise
                
                # Record timing
                duration = time.time() - start_time
                self._request_contexts[request_id].log_service_timing("upload_service", duration)
                
                try:
                    current_time = validate_datetime(datetime.utcnow())
                    file_info = {
                        "filename": upload_result.filename,
                        "path": upload_result.path,
                        "status": upload_result.status
                    }
                    return UploadResponse(
                        request_id=request_id,
                        file_info=file_info,
                        message="File uploaded successfully",
                        timestamp=current_time.isoformat()
                    )
                except ValidationError as ve:
                    logger.error("Response validation failed", extra={
                        "request_id": request_id,
                        "validation_errors": ve.errors()
                    })
                    logger.error(traceback.format_exc())
                    raise HTTPException(
                        status_code=500,
                        detail=ErrorResponse(
                            error="Response validation failed",
                            error_type="ValidationError",
                            request_id=request_id,
                            details={"validation_errors": ve.errors()}
                        ).model_dump()
                    )
                
            except Exception as e:
                logger.error("Error in file upload (outer block)", extra={
                    "request_id": request_id,
                    "error": str(e)
                })
                logger.error(traceback.format_exc())
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        error=str(e),
                        error_type=type(e).__name__,
                        request_id=request_id,
                        timestamp=validate_datetime(datetime.utcnow())
                    ).model_dump()
                )

    @log_execution_time(logger)
    async def handle_query(self, query: str, request_id: str) -> QueryResponse:
        """Process query using Anthropic for CSV analysis"""
        with transaction_manager.start_transaction(request_id) as transaction:
            try:
                logger.info("Processing query", extra={
                    "request_id": request_id,
                    "query": query
                })
                start_time = time.time()

                # Get CSV content from request context
                if request_id not in self._request_contexts or not hasattr(self._request_contexts[request_id], 'csv_content'):
                    raise HTTPException(status_code=400, detail="No CSV data found. Please upload a CSV file first.")

                csv_content = self._request_contexts[request_id].csv_content

                # Send query and CSV content to Anthropic
                prompt = f"""Here is a CSV file content:

{csv_content}

Question: {query}

Please analyze the CSV data to answer this question. Include any relevant statistics, patterns, or insights you find. If appropriate, suggest visualizations that could help illustrate the answer."""

                response = await self.anthropic.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )

                ai_output = {
                    "result": response.content[0].text,
                    "thinking_steps": [],  # Could be extracted from Claude's response if needed
                    "chartData": []  # Could be generated based on Claude's visualization suggestions
                }

                # Map insights from CrewAI output
                raw_insights = ai_output.get('thinking_steps', [])
                insights = []
                for step in raw_insights:
                    insights.append(NarrativeInsight(
                        type=step.get('type', ''),
                        description=step.get('description', ''),
                        confidence=step.get('confidence', 0.0),
                        supporting_data=ChartData(**step['supporting_data']) if step.get('supporting_data') else None
                    ))
                # Map visualizations from CrewAI output
                raw_charts = ai_output.get('chartData', [])
                visualizations = [ChartData(**chart) for chart in raw_charts]
                qr = QueryResponse(
                    request_id=request_id,
                    query=query,
                    response=ai_output.get("result", ""),
                    insights=insights,
                    visualizations=visualizations,
                    timestamp=validate_datetime(datetime.utcnow())
                )
                # Record service timing
                duration = time.time() - start_time
                self._request_contexts[request_id].log_service_timing("query_processing", duration)
                return qr
                
            except HTTPException as he:
                raise he
            except Exception as e:
                logger.error("Error in query processing", extra={
                    "request_id": request_id,
                    "error": str(e)
                }, exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        error=str(e),
                        error_type=type(e).__name__,
                        request_id=request_id,
                        timestamp=validate_datetime(datetime.utcnow())
                    ).model_dump()
                )

    def get_health_status(self) -> HealthStatus:
        """Get health status of all services"""
        try:
            # Log current system metrics with health check
            self._log_system_metrics()
            system_metrics = metrics_logger.get_system_metrics()
            
            # Validate system metrics
            validated_metrics = {
                k: sanitize_numeric(v) or 0.0
                for k, v in system_metrics.items()
            }
            
            # Determine overall status
            all_healthy = all(self._health_status.values())
            status = "healthy" if all_healthy else "degraded"
            
            return HealthStatus(
                status=status,
                services=self._health_status,
                system=validated_metrics,
                timestamp=validate_datetime(datetime.utcnow())
            )
        except ValidationError as ve:
            logger.error("Health status validation failed", extra={
                "validation_errors": ve.errors()
            })
            return HealthStatus(
                status="error",
                services=self._health_status,
                system={},
                timestamp=validate_datetime(datetime.utcnow())
            )

    def update_service_health(self, service_name: str, is_healthy: bool):
        """Update health status of a service"""
        if service_name in self._health_status:
            previous_status = self._health_status[service_name]
            self._health_status[service_name] = is_healthy
            if previous_status != is_healthy:
                logger.info("Service health status changed", extra={
                    "service": service_name,
                    "status": "healthy" if is_healthy else "unhealthy"
                })

    def cleanup_request_context(self, request_id: str):
        """Clean up request context and associated resources after completion"""
        try:
            # Clean up request context
            if request_id in self._request_contexts:
                context = self._request_contexts[request_id]
                duration = time.time() - context.start_time
                
                # Log final metrics for the request
                metrics_logger.log_metrics({
                    "total_duration": duration,
                    "service_timings": context.service_timings
                }, request_id)
                
                del self._request_contexts[request_id]
                logger.info("Cleaned up request context", extra={"request_id": request_id})
            
            # Clean up any old transactions
            transaction_manager.cleanup_old_transactions()
            
        except Exception as e:
            logger.error("Error cleaning up request context", extra={
                "request_id": request_id,
                "error": str(e)
            })

# Create global orchestrator instance
orchestrator = Orchestrator()
