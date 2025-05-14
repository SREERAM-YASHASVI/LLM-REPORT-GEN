import logging
import os
import uuid
from datetime import datetime

import colorlog

def setup_logging(test_name: str) -> logging.Logger:
    """Set up logging configuration for agent tests with color-coding and run ID."""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Create a timestamp for the log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f'agent_test_{test_name}_{timestamp}.log')

    # Generate a unique run ID for this test run
    run_id = str(uuid.uuid4())[:8]

    # Configure logger
    logger = logging.getLogger(f'agent_test.{test_name}')
    logger.setLevel(logging.DEBUG)

    # Track start time for delta calculations
    logger.start_time = datetime.now()
    logger.last_time = logger.start_time

    def add_delta(record):
        current_time = datetime.now()
        delta = (current_time - logger.last_time).total_seconds() * 1000  # in milliseconds
        logger.last_time = current_time
        record.delta_ms = f'{delta:.2f}ms'
        record.run_id = run_id
        record.total_time_ms = f'{(current_time - logger.start_time).total_seconds() * 1000:.2f}ms'
        return True

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(run_id)s - %(delta_ms)s - %(total_time_ms)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.addFilter(add_delta)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s%(reset)s - %(run_id)s - %(delta_ms)s - %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.addFilter(add_delta)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info(f'Starting new test run with ID: {run_id}')
    return logger
