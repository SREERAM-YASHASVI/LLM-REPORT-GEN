"""Utilities for data validation and type conversion."""
import numpy as np
from typing import Any, Dict, Union, Optional
from datetime import datetime
import pandas as pd

def sanitize_numeric(value: Any) -> Optional[float]:
    """
    Sanitize numeric values, handling NaN, infinity, and numpy types.
    Returns None for invalid values.
    """
    if value is None:
        return None
        
    try:
        # Convert numpy types to Python types
        if isinstance(value, (np.integer, np.floating)):
            value = value.item()
            
        # Convert to float
        value = float(value)
        
        # Handle special cases
        if np.isnan(value) or np.isinf(value):
            return None
            
        return value
    except (ValueError, TypeError):
        return None

def sanitize_categorical(value: Any) -> Optional[str]:
    """
    Sanitize categorical values, ensuring they're strings.
    Returns None for invalid values.
    """
    if value is None:
        return None
        
    try:
        # Handle numpy types
        if isinstance(value, (np.generic,)):
            value = value.item()
        
        # Convert to string, handling special cases
        if pd.isna(value):
            return None
        
        return str(value)
    except (ValueError, TypeError):
        return None

def validate_statistics_dict(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean statistics dictionary, ensuring all numeric values are valid.
    """
    cleaned = {}
    for key, value in stats.items():
        if isinstance(value, dict):
            cleaned[key] = validate_statistics_dict(value)
        else:
            cleaned_value = sanitize_numeric(value)
            if cleaned_value is not None:
                cleaned[key] = cleaned_value
            else:
                cleaned[key] = 0.0  # Default value for invalid numerics
    return cleaned

def validate_datetime(value: Any) -> Optional[datetime]:
    """
    Validate and convert datetime values.
    Returns None for invalid values.
    """
    if isinstance(value, datetime):
        return value
        
    try:
        if isinstance(value, (np.datetime64, pd.Timestamp)):
            return value.to_pydatetime()
        elif isinstance(value, str):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return None
    except (ValueError, TypeError):
        return None 