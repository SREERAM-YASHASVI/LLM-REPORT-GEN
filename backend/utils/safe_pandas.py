"""Safe wrapper for pandas operations in sandbox environment."""
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
from utils.sandbox_utils import sandbox_decorator

class SafeDataFrame:
    """
    A secure wrapper around pandas DataFrame that only allows safe operations.
    """
    
    def __init__(self, df: pd.DataFrame):
        """Initialize with a pandas DataFrame."""
        self._df = df
        
    @property
    def columns(self) -> List[str]:
        """Get column names."""
        return list(self._df.columns)
        
    @property
    def shape(self) -> tuple:
        """Get DataFrame shape."""
        return self._df.shape
        
    @sandbox_decorator
    def head(self, n: int = 5) -> Dict[str, List[Any]]:
        """Get first n rows as a dictionary."""
        return self._df.head(n).to_dict('list')
        
    @sandbox_decorator
    def describe(self) -> Dict[str, Dict[str, float]]:
        """Get statistical description of numeric columns."""
        return self._df.describe().to_dict()
        
    @sandbox_decorator
    def value_counts(self, column: str, limit: int = 10) -> Dict[str, int]:
        """Get value counts for a column."""
        if column not in self._df.columns:
            raise ValueError(f"Column {column} not found")
        return dict(self._df[column].value_counts().head(limit))
        
    @sandbox_decorator
    def mean(self, column: str) -> float:
        """Get mean of a numeric column."""
        if column not in self._df.columns:
            raise ValueError(f"Column {column} not found")
        return float(self._df[column].mean())
        
    @sandbox_decorator
    def sum(self, column: str) -> float:
        """Get sum of a numeric column."""
        if column not in self._df.columns:
            raise ValueError(f"Column {column} not found")
        return float(self._df[column].sum())
        
    @sandbox_decorator
    def min(self, column: str) -> Any:
        """Get minimum value of a column."""
        if column not in self._df.columns:
            raise ValueError(f"Column {column} not found")
        return self._df[column].min()
        
    @sandbox_decorator
    def max(self, column: str) -> Any:
        """Get maximum value of a column."""
        if column not in self._df.columns:
            raise ValueError(f"Column {column} not found")
        return self._df[column].max()
        
    @sandbox_decorator
    def groupby(self, by: str, agg_column: str, agg_func: str) -> Dict[str, float]:
        """
        Perform a simple groupby operation.
        
        Args:
            by: Column to group by
            agg_column: Column to aggregate
            agg_func: Aggregation function ('mean', 'sum', 'count', 'min', 'max')
        """
        allowed_funcs = {'mean', 'sum', 'count', 'min', 'max'}
        if agg_func not in allowed_funcs:
            raise ValueError(f"Aggregation function must be one of: {allowed_funcs}")
            
        if by not in self._df.columns or agg_column not in self._df.columns:
            raise ValueError("Column not found")
            
        grouped = self._df.groupby(by)[agg_column].agg(agg_func)
        return dict(grouped)
        
    @sandbox_decorator
    def correlation(self, column1: str, column2: str) -> float:
        """Get correlation between two numeric columns."""
        if column1 not in self._df.columns or column2 not in self._df.columns:
            raise ValueError("Column not found")
        return float(self._df[column1].corr(self._df[column2]))
        
    @sandbox_decorator
    def filter_by_value(self, column: str, value: Any) -> 'SafeDataFrame':
        """Filter DataFrame by column value."""
        if column not in self._df.columns:
            raise ValueError(f"Column {column} not found")
        return SafeDataFrame(self._df[self._df[column] == value])
        
    @sandbox_decorator
    def get_numeric_columns(self) -> List[str]:
        """Get list of numeric columns."""
        return list(self._df.select_dtypes(include=[np.number]).columns)
        
    @sandbox_decorator
    def get_categorical_columns(self) -> List[str]:
        """Get list of categorical columns."""
        return list(self._df.select_dtypes(exclude=[np.number]).columns)
        
    @sandbox_decorator
    def to_dict(self, orient: str = 'records') -> Union[List[Dict[str, Any]], Dict[str, List[Any]]]:
        """Convert DataFrame to dictionary."""
        allowed_orients = {'records', 'list'}
        if orient not in allowed_orients:
            raise ValueError(f"Orient must be one of: {allowed_orients}")
        return self._df.to_dict(orient)

def create_safe_dataframe(df: pd.DataFrame) -> SafeDataFrame:
    """Create a SafeDataFrame instance from a pandas DataFrame."""
    return SafeDataFrame(df) 