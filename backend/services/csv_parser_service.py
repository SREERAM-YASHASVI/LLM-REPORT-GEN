import logging
import pandas as pd
from typing import Dict, Any
from utils.logging_utils import setup_json_logging, log_execution_time
from utils.validation_utils import sanitize_numeric, sanitize_categorical
from schemas.api_schemas import (
    CSVAnalysisResult,
    NumericStatistics,
    CategoricalStatistics,
    ColumnType
)

# Configure logging
logger = setup_json_logging("csv_parser")

class CSVParser:
    @log_execution_time(logger)
    def parse_file(self, file_path: str, request_id: str) -> tuple[CSVAnalysisResult, pd.DataFrame]:
        """
        Parse a CSV file and return both analysis results and the full DataFrame
        
        Args:
            file_path: Path to the CSV file
            request_id: Request ID for logging
        
        Returns:
            Tuple of (CSVAnalysisResult containing summary statistics, full DataFrame)
        """
        try:
            # Read the full CSV file
            df = pd.read_csv(file_path)
            
            logger.info("Parsing CSV file", extra={
                "request_id": request_id,
                "total_rows": len(df),
                "columns": df.columns.tolist()
            })
            
            # Generate summary statistics
            summary = self._generate_summary(df)
            
            return summary, df
            
        except Exception as e:
            logger.error("Error parsing CSV file", extra={
                "request_id": request_id,
                "error": str(e)
            }, exc_info=True)
            raise

    def _generate_summary(self, df: pd.DataFrame) -> CSVAnalysisResult:
        """Generate summary statistics from DataFrame"""
        column_statistics = {}
        
        # Process numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            valid_series = df[col].dropna()
            if len(valid_series) > 0:
                column_statistics[col] = NumericStatistics(
                    type=ColumnType.NUMERIC,
                    mean=float(valid_series.mean()),
                    std=float(valid_series.std()),
                    min=float(valid_series.min()),
                    max=float(valid_series.max()),
                    count=int(valid_series.count())
                )
        
        # Process categorical columns
        categorical_cols = df.select_dtypes(exclude=['number']).columns
        for col in categorical_cols:
            valid_series = df[col].dropna().astype(str)
            if len(valid_series) > 0:
                value_counts = valid_series.value_counts().head(10)
                column_statistics[col] = CategoricalStatistics(
                    type=ColumnType.CATEGORICAL,
                    unique_values=len(valid_series.unique()),
                    top_values={
                        str(k): int(v)
                        for k, v in value_counts.items()
                        if k is not None
                    }
                )
        
        # Get sample rows
        sample_rows = []
        for _, row in df.head(5).iterrows():
            sanitized_row = {}
            for col, value in row.items():
                if col in numeric_cols:
                    sanitized_row[col] = sanitize_numeric(value) or 0.0
                else:
                    sanitized_row[col] = sanitize_categorical(value) or ""
            sample_rows.append(sanitized_row)
        
        return CSVAnalysisResult(
            total_rows=len(df),
            columns=df.columns.tolist(),
            column_statistics=column_statistics,
            sample_rows=sample_rows
        )

# Create global parser instance
csv_parser = CSVParser()
