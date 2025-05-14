"""Pytest configuration and fixtures."""
import os
import pytest
from typing import Dict, Any, Generator
from .test_config import setup_test_environment, cleanup_test_environment
from .test_data_generator import TestDataGenerator
from .test_logging import TestLogger, TestReporter

@pytest.fixture(scope="session", autouse=True)
def test_env() -> Dict[str, Any]:
    """Set up test environment and clean up after all tests."""
    config = setup_test_environment()
    yield config
    cleanup_test_environment()

@pytest.fixture(scope="session")
def data_generator() -> TestDataGenerator:
    """Create a test data generator instance."""
    generator = TestDataGenerator()
    yield generator
    generator.cleanup_test_data()

@pytest.fixture
def test_logger(request) -> Generator[TestLogger, None, None]:
    """Create a test logger for the current test."""
    logger = TestLogger(request.node.name)
    yield logger
    logger.finalize()

@pytest.fixture(scope="session")
def test_reporter() -> TestReporter:
    """Create a test reporter instance."""
    return TestReporter()

@pytest.fixture
def sample_csv(data_generator) -> str:
    """Generate a sample CSV file for testing."""
    return data_generator.generate_csv_file(size="small")

@pytest.fixture
def large_csv(data_generator) -> str:
    """Generate a large CSV file for testing."""
    return data_generator.generate_csv_file(size="large")

@pytest.fixture
def csv_with_errors(data_generator) -> str:
    """Generate a CSV file with intentional errors."""
    return data_generator.generate_csv_file(size="small", with_errors=True)

@pytest.fixture
def malicious_csv(data_generator) -> str:
    """Generate a malicious CSV file for security testing."""
    return data_generator.generate_malicious_file("csv")

@pytest.fixture
def csv_chunks(data_generator) -> list[str]:
    """Generate multiple CSV chunks for testing chunked processing."""
    return data_generator.generate_large_file_chunks()

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "security: mark test as a security test")

def pytest_runtest_setup(item):
    """Set up test environment before each test."""
    # Set up any necessary environment variables or configurations
    os.environ["TESTING"] = "true"
    
    # Log test start
    logger = TestLogger(item.name)
    item.user_properties.append(("logger", logger))

def pytest_runtest_teardown(item, nextitem):
    """Clean up after each test."""
    # Get the logger from user properties
    for name, logger in item.user_properties:
        if name == "logger":
            logger.finalize()
            break 