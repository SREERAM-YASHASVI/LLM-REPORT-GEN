"""Test logging and reporting utilities."""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from .test_config import TEST_ENV

class TestLogger:
    """Handles logging for test execution and results."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.log_dir = TEST_ENV["LOG_DIR"]
        self.start_time = datetime.now()
        self.test_results: Dict[str, Any] = {
            "test_name": test_name,
            "start_time": self.start_time.isoformat(),
            "status": "running",
            "steps": [],
            "performance_metrics": {},
            "errors": []
        }
        
        # Set up logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create a unique log file for this test run
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"{self.test_name}_{timestamp}.log")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(self.test_name)
    
    def log_step(self, step_name: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Log a test step with its status and details."""
        step_data = {
            "name": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.test_results["steps"].append(step_data)
        
        # Log to file
        self.logger.info(f"Step: {step_name} - Status: {status}")
        if details:
            self.logger.info(f"Details: {json.dumps(details, indent=2)}")
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str):
        """Log a performance metric."""
        metric_data = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        
        if metric_name not in self.test_results["performance_metrics"]:
            self.test_results["performance_metrics"][metric_name] = []
        
        self.test_results["performance_metrics"][metric_name].append(metric_data)
        
        self.logger.info(f"Performance metric - {metric_name}: {value} {unit}")
    
    def log_error(self, error_message: str, error_type: str, details: Optional[Dict[str, Any]] = None):
        """Log an error that occurred during testing."""
        error_data = {
            "message": error_message,
            "type": error_type,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.test_results["errors"].append(error_data)
        self.logger.error(f"Error ({error_type}): {error_message}")
        if details:
            self.logger.error(f"Error details: {json.dumps(details, indent=2)}")
    
    def finalize(self, status: str = "completed"):
        """Finalize the test results and save to file."""
        end_time = datetime.now()
        self.test_results.update({
            "status": status,
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds()
        })
        
        # Save results to JSON file
        results_file = os.path.join(
            self.log_dir,
            f"{self.test_name}_{self.start_time.strftime('%Y%m%d_%H%M%S')}_results.json"
        )
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        self.logger.info(f"Test completed with status: {status}")
        self.logger.info(f"Results saved to: {results_file}")
    
    def get_results(self) -> Dict[str, Any]:
        """Get the current test results."""
        return self.test_results.copy()

class TestReporter:
    """Generates test reports from test results."""
    
    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = log_dir or TEST_ENV["LOG_DIR"]
    
    def generate_report(self, test_pattern: Optional[str] = None) -> Dict[str, Any]:
        """Generate a report from test results matching the pattern."""
        all_results = []
        
        # Collect all result files
        for file in Path(self.log_dir).glob("*_results.json"):
            if test_pattern and test_pattern not in file.name:
                continue
                
            with open(file, 'r') as f:
                results = json.load(f)
                all_results.append(results)
        
        # Aggregate results
        report = {
            "total_tests": len(all_results),
            "status_summary": {
                "completed": 0,
                "failed": 0,
                "running": 0
            },
            "error_summary": [],
            "performance_summary": {},
            "test_results": all_results
        }
        
        # Calculate summaries
        for result in all_results:
            report["status_summary"][result["status"]] += 1
            
            # Collect errors
            for error in result.get("errors", []):
                report["error_summary"].append({
                    "test_name": result["test_name"],
                    "error_type": error["type"],
                    "message": error["message"]
                })
            
            # Aggregate performance metrics
            for metric, values in result.get("performance_metrics", {}).items():
                if metric not in report["performance_summary"]:
                    report["performance_summary"][metric] = {
                        "min": float('inf'),
                        "max": float('-inf'),
                        "total": 0,
                        "count": 0
                    }
                
                for value_data in values:
                    value = value_data["value"]
                    report["performance_summary"][metric]["min"] = min(
                        report["performance_summary"][metric]["min"],
                        value
                    )
                    report["performance_summary"][metric]["max"] = max(
                        report["performance_summary"][metric]["max"],
                        value
                    )
                    report["performance_summary"][metric]["total"] += value
                    report["performance_summary"][metric]["count"] += 1
        
        # Calculate averages
        for metric in report["performance_summary"].values():
            metric["average"] = metric["total"] / metric["count"]
            del metric["total"]
            del metric["count"]
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """Save a report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        report_file = os.path.join(self.log_dir, filename)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file 