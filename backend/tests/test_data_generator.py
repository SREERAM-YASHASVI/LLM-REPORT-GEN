"""Test data generation utilities."""
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import random
import string
from datetime import datetime, timedelta
from .test_config import TEST_ENV, TEST_DATA_CONFIG

class TestDataGenerator:
    """Generates test data for various test scenarios."""
    
    def __init__(self):
        self.data_dir = TEST_ENV["TEST_DATA_DIR"]
        os.makedirs(self.data_dir, exist_ok=True)
    
    def generate_csv_file(self, size: str = "small", with_errors: bool = False) -> str:
        """Generate a CSV file with specified size and optional errors."""
        num_rows = TEST_DATA_CONFIG["CSV_SIZES"][size]
        
        # Generate sample data
        data = {
            'date': [datetime.now() - timedelta(days=x) for x in range(num_rows)],
            'value': np.random.normal(100, 15, num_rows),
            'category': np.random.choice(['A', 'B', 'C'], num_rows),
            'quantity': np.random.randint(1, 1000, num_rows)
        }
        
        if with_errors:
            # Introduce some errors
            error_indices = np.random.choice(num_rows, size=num_rows//10, replace=False)
            for idx in error_indices:
                if random.random() < 0.5:
                    data['value'][idx] = 'invalid'
                else:
                    data['quantity'][idx] = 'N/A'
        
        df = pd.DataFrame(data)
        
        # Save to file
        filename = f"test_data_{size}{'_with_errors' if with_errors else ''}.csv"
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False)
        
        return filepath
    
    def generate_text_file(self, size: str = "small") -> str:
        """Generate a text file with random content."""
        num_paragraphs = TEST_DATA_CONFIG["CSV_SIZES"][size] // 10
        
        content = []
        for _ in range(num_paragraphs):
            words = ''.join(random.choices(string.ascii_letters + ' ', k=100))
            content.append(words)
        
        filename = f"test_data_{size}.txt"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write('\n\n'.join(content))
        
        return filepath
    
    def generate_malicious_file(self, file_type: str) -> str:
        """Generate a potentially malicious file for security testing."""
        filename = f"malicious_test.{file_type}"
        filepath = os.path.join(self.data_dir, filename)
        
        if file_type == 'csv':
            # CSV with formula injection
            content = 'id,name,formula\n1,test,=CMD(\'del *.*\')'
        elif file_type == 'txt':
            # Text with large repetitive content
            content = 'A' * (TEST_ENV["MAX_FILE_SIZE"] + 1)
        else:
            content = 'Unsupported file type'
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        return filepath
    
    def generate_large_file_chunks(self, chunk_size: int = 1000) -> List[str]:
        """Generate multiple file chunks for testing chunked processing."""
        num_chunks = 5
        chunk_files = []
        
        for i in range(num_chunks):
            data = {
                'id': range(i * chunk_size, (i + 1) * chunk_size),
                'value': np.random.normal(100, 15, chunk_size),
                'timestamp': [datetime.now() + timedelta(minutes=x) 
                            for x in range(i * chunk_size, (i + 1) * chunk_size)]
            }
            df = pd.DataFrame(data)
            
            filename = f"chunk_{i}.csv"
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath, index=False)
            chunk_files.append(filepath)
        
        return chunk_files
    
    def generate_test_upload_file(self, file_type: str, size: str = "small") -> Dict[str, Any]:
        """Generate a file suitable for upload testing."""
        if file_type == 'csv':
            filepath = self.generate_csv_file(size)
        elif file_type == 'txt':
            filepath = self.generate_text_file(size)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        return {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'size': os.path.getsize(filepath)
        }
    
    def cleanup_test_data(self):
        """Clean up generated test data."""
        if os.path.exists(self.data_dir):
            for file in os.listdir(self.data_dir):
                os.remove(os.path.join(self.data_dir, file)) 