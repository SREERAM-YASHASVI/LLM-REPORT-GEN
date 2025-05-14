"""Utilities for transaction management and resource cleanup."""
import os
import shutil
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path
from datetime import datetime, timedelta
import logging
from utils.logging_utils import setup_json_logging
from contextlib import contextmanager

# Configure logging
logger = setup_json_logging("transaction")

class CleanupError(Exception):
    """Exception raised when cleanup operations fail."""
    pass

class Resource:
    """Base class for managed resources."""
    def __init__(self, resource_id: str, resource_type: str):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.created_at = datetime.utcnow()
        
    def cleanup(self):
        """Clean up the resource. Must be implemented by subclasses."""
        raise NotImplementedError

class FileResource(Resource):
    """Resource representing a file or directory."""
    def __init__(self, file_path: str, is_temp: bool = True):
        super().__init__(
            resource_id=file_path,
            resource_type="file"
        )
        self.file_path = Path(file_path)
        self.is_temp = is_temp
        
    def cleanup(self):
        """Delete the file or directory."""
        try:
            if self.file_path.exists():
                if self.file_path.is_dir():
                    shutil.rmtree(self.file_path)
                else:
                    self.file_path.unlink()
                logger.info(f"Cleaned up {self.resource_type}", extra={
                    "path": str(self.file_path),
                    "is_temp": self.is_temp
                })
        except Exception as e:
            logger.error(f"Error cleaning up {self.resource_type}", extra={
                "path": str(self.file_path),
                "error": str(e)
            })
            raise CleanupError(f"Failed to clean up file: {str(e)}")

class Transaction:
    """
    Manages resources and cleanup operations for a request.
    
    Usage:
        with Transaction(request_id) as txn:
            # Register resources for cleanup
            txn.register(FileResource("path/to/temp.file"))
            # Do work...
            # Resources are automatically cleaned up after the block
    """
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.resources: List[Resource] = []
        self.started_at = datetime.utcnow()
        self.completed = False
        self.failed = False
        
    def register(self, resource: Resource):
        """Register a resource for cleanup."""
        self.resources.append(resource)
        logger.info("Registered resource", extra={
            "request_id": self.request_id,
            "resource_type": resource.resource_type,
            "resource_id": resource.resource_id
        })
        
    def cleanup(self):
        """Clean up all registered resources."""
        errors = []
        for resource in reversed(self.resources):  # Clean up in reverse order
            try:
                resource.cleanup()
            except Exception as e:
                errors.append(str(e))
                logger.error("Resource cleanup failed", extra={
                    "request_id": self.request_id,
                    "resource_type": resource.resource_type,
                    "resource_id": resource.resource_id,
                    "error": str(e)
                })
        
        if errors:
            raise CleanupError(f"Cleanup errors occurred: {'; '.join(errors)}")
            
    def rollback(self):
        """Roll back changes by cleaning up resources after a failure."""
        self.failed = True
        try:
            self.cleanup()
        except Exception as e:
            logger.error("Rollback failed", extra={
                "request_id": self.request_id,
                "error": str(e)
            })
            
    def __enter__(self):
        """Enter the transaction context."""
        logger.info("Starting transaction", extra={
            "request_id": self.request_id
        })
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the transaction context, cleaning up resources."""
        try:
            if exc_type is not None:
                # An error occurred, roll back
                self.rollback()
            else:
                # Normal completion, clean up
                self.cleanup()
                self.completed = True
        finally:
            duration = datetime.utcnow() - self.started_at
            logger.info("Transaction completed", extra={
                "request_id": self.request_id,
                "duration_seconds": duration.total_seconds(),
                "status": "failed" if self.failed else "completed",
                "resource_count": len(self.resources)
            })

class TransactionManager:
    """
    Manages transactions and performs periodic cleanup of orphaned resources.
    """
    
    def __init__(self, max_age_hours: int = 24):
        self.max_age = timedelta(hours=max_age_hours)
        self.active_transactions: Dict[str, Transaction] = {}
        
    def start_transaction(self, request_id: str) -> Transaction:
        """Start a new transaction."""
        if request_id in self.active_transactions:
            raise ValueError(f"Transaction {request_id} already exists")
            
        transaction = Transaction(request_id)
        self.active_transactions[request_id] = transaction
        return transaction
        
    def cleanup_old_transactions(self):
        """Clean up transactions older than max_age."""
        now = datetime.utcnow()
        old_transactions = [
            (rid, txn) for rid, txn in self.active_transactions.items()
            if now - txn.started_at > self.max_age
        ]
        
        for request_id, transaction in old_transactions:
            try:
                transaction.cleanup()
                del self.active_transactions[request_id]
                logger.info("Cleaned up old transaction", extra={
                    "request_id": request_id,
                    "age_hours": (now - transaction.started_at).total_seconds() / 3600
                })
            except Exception as e:
                logger.error("Failed to clean up old transaction", extra={
                    "request_id": request_id,
                    "error": str(e)
                })

# Create global transaction manager
transaction_manager = TransactionManager() 