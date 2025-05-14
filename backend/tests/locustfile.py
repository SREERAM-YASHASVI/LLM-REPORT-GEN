"""Load testing configuration using Locust."""
import os
import json
from locust import HttpUser, task, between
from typing import Dict, Any
import random

class DocumentAnalysisUser(HttpUser):
    """Simulates a user interacting with the document analysis system."""
    
    # Wait between 1 to 5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Setup before starting tasks."""
        # Load test data paths
        self.test_files = self._get_test_files()
    
    def _get_test_files(self) -> Dict[str, str]:
        """Get paths to test files."""
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        files = {}
        
        # Get small CSV
        small_csv = os.path.join(data_dir, "test_data_small.csv")
        if os.path.exists(small_csv):
            files["small"] = small_csv
            
        # Get medium CSV
        medium_csv = os.path.join(data_dir, "test_data_medium.csv")
        if os.path.exists(medium_csv):
            files["medium"] = medium_csv
            
        # Get large CSV
        large_csv = os.path.join(data_dir, "test_data_large.csv")
        if os.path.exists(large_csv):
            files["large"] = large_csv
        
        return files
    
    @task(3)
    def upload_and_analyze_small_file(self):
        """Upload and analyze a small CSV file."""
        if "small" not in self.test_files:
            return
            
        # Upload file
        with open(self.test_files["small"], "rb") as f:
            files = {"file": ("small.csv", f, "text/csv")}
            response = self.client.post("/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                request_id = result["request_id"]
                
                # Query the file
                query = random.choice([
                    "Analyze this CSV and show trends",
                    "Provide summary statistics",
                    "Find anomalies in the data",
                    "Generate visualizations"
                ])
                
                self.client.post(
                    f"/query/{request_id}",
                    json={"query": query}
                )
    
    @task(2)
    def upload_and_analyze_medium_file(self):
        """Upload and analyze a medium CSV file."""
        if "medium" not in self.test_files:
            return
            
        with open(self.test_files["medium"], "rb") as f:
            files = {"file": ("medium.csv", f, "text/csv")}
            response = self.client.post("/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                request_id = result["request_id"]
                
                self.client.post(
                    f"/query/{request_id}",
                    json={"query": "Analyze this CSV and provide insights"}
                )
    
    @task(1)
    def upload_and_analyze_large_file(self):
        """Upload and analyze a large CSV file."""
        if "large" not in self.test_files:
            return
            
        with open(self.test_files["large"], "rb") as f:
            files = {"file": ("large.csv", f, "text/csv")}
            response = self.client.post("/upload", files=files)
            
            if response.status_code == 200:
                result = response.json()
                request_id = result["request_id"]
                
                self.client.post(
                    f"/query/{request_id}",
                    json={"query": "Analyze this CSV and provide insights"}
                )
    
    @task(4)
    def check_health(self):
        """Check system health status."""
        self.client.get("/health") 