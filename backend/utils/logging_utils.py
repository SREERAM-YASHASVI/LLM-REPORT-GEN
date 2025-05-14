import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps
import psutil
import os

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno
        }
        
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        if hasattr(record, "metrics"):
            log_obj["metrics"] = record.metrics
            
        return json.dumps(log_obj)

class MetricsLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{service_name}_metrics")
        self._setup_logger()
        
    def _setup_logger(self):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
    def log_metrics(self, metrics: Dict[str, Any], request_id: Optional[str] = None):
        extra = {
            "metrics": {
                "service": self.service_name,
                "timestamp": datetime.utcnow().isoformat(),
                **metrics
            }
        }
        if request_id:
            extra["request_id"] = request_id
        self.logger.info("Service metrics", extra=extra)
        
    def get_system_metrics(self) -> Dict[str, float]:
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }

def setup_json_logging(service_name: str):
    """Set up JSON logging for a service"""
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add JSON handler
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    logger = logging.getLogger(service_name)
    return logger

def log_execution_time(logger: logging.Logger):
    """Decorator to log execution time of functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    extra={
                        "metrics": {
                            "function": func.__name__,
                            "execution_time": execution_time
                        }
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed: {str(e)}",
                    extra={
                        "metrics": {
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    extra={
                        "metrics": {
                            "function": func.__name__,
                            "execution_time": execution_time
                        }
                    }
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed: {str(e)}",
                    extra={
                        "metrics": {
                            "function": func.__name__,
                            "execution_time": execution_time,
                            "error": str(e)
                        }
                    },
                    exc_info=True
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 