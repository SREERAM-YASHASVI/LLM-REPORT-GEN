"""Test configuration and environment settings."""
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

# Test environment configurations
TEST_ENV = {
    "ENVIRONMENT": "test",
    "TEST_DATA_DIR": os.path.join(os.path.dirname(__file__), "data"),
    "TEMP_DIR": tempfile.gettempdir(),
    "MAX_FILE_SIZE": 1024 * 1024 * 10,  # 10MB for test files
    "UPLOAD_DIR": os.path.join(tempfile.gettempdir(), "test_uploads"),
    "LOG_DIR": os.path.join(tempfile.gettempdir(), "test_logs"),
}

# Test data configurations
TEST_DATA_CONFIG = {
    "CSV_SIZES": {
        "small": 100,      # rows
        "medium": 1000,    # rows
        "large": 10000     # rows
    },
    "FILE_TYPES": ["csv", "txt", "pdf"],
    "CONCURRENT_USERS": {
        "low": 5,
        "medium": 20,
        "high": 50
    }
}

# Performance test thresholds
PERFORMANCE_THRESHOLDS = {
    "response_time": {
        "p95": 2.0,    # seconds
        "p99": 5.0     # seconds
    },
    "memory_usage": {
        "max": 512,    # MB
        "warning": 384 # MB
    },
    "cpu_usage": {
        "max": 80,     # percent
        "warning": 70  # percent
    }
}

# Security test configurations
SECURITY_CONFIG = {
    "allowed_file_types": [".csv", ".txt", ".pdf"],
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "sandbox_timeout": 30,  # seconds
    "max_memory": 512 * 1024 * 1024,  # 512MB
}

def setup_test_environment() -> Dict[str, Any]:
    """Set up test environment and return configuration."""
    # Create necessary directories
    for dir_path in [TEST_ENV["TEST_DATA_DIR"], TEST_ENV["UPLOAD_DIR"], TEST_ENV["LOG_DIR"]]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Set environment variables for testing
    os.environ.update({
        "ENVIRONMENT": "test",
        "UPLOAD_DIR": TEST_ENV["UPLOAD_DIR"],
        "LOG_DIR": TEST_ENV["LOG_DIR"]
    })
    
    return {
        "env": TEST_ENV,
        "data_config": TEST_DATA_CONFIG,
        "performance": PERFORMANCE_THRESHOLDS,
        "security": SECURITY_CONFIG
    }

def cleanup_test_environment():
    """Clean up test environment after tests."""
    # Clean up test upload directory
    if os.path.exists(TEST_ENV["UPLOAD_DIR"]):
        for file in os.listdir(TEST_ENV["UPLOAD_DIR"]):
            os.remove(os.path.join(TEST_ENV["UPLOAD_DIR"], file))
    
    # Clean up test logs
    if os.path.exists(TEST_ENV["LOG_DIR"]):
        for file in os.listdir(TEST_ENV["LOG_DIR"]):
            os.remove(os.path.join(TEST_ENV["LOG_DIR"], file)) 