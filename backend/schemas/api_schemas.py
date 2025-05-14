from typing import Dict, List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime

class ColumnType(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"
    DATETIME = "datetime"

class NumericStatistics(BaseModel):
    type: Literal[ColumnType.NUMERIC] = ColumnType.NUMERIC
    mean: float
    std: float
    min: float
    max: float
    count: int

class CategoricalStatistics(BaseModel):
    type: Literal[ColumnType.CATEGORICAL] = ColumnType.CATEGORICAL
    unique_values: int
    top_values: Dict[str, int]

class ColumnStatistics(BaseModel):
    name: str
    type: ColumnType
    statistics: Union[NumericStatistics, CategoricalStatistics]

class CSVAnalysisResult(BaseModel):
    total_rows: int
    columns: List[str]
    column_statistics: Dict[str, Union[NumericStatistics, CategoricalStatistics]]
    sample_rows: List[Dict[str, Any]]

class ChartData(BaseModel):
    chart_type: str = Field(..., description="Type of chart (e.g., 'bar', 'line', 'scatter')")
    title: str
    x_axis: str
    y_axis: str
    data: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]] = None

class NarrativeInsight(BaseModel):
    type: str = Field(..., description="Type of insight (e.g., 'trend', 'correlation', 'anomaly')")
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_data: Optional[ChartData] = None

class AnalysisResponse(BaseModel):
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    file_info: Dict[str, str]
    statistics: CSVAnalysisResult
    insights: List[NarrativeInsight]
    visualizations: List[ChartData]

    @field_validator('insights')
    def validate_insights_confidence(cls, v):
        for insight in v:
            if not 0 <= insight.confidence <= 1:
                raise ValueError(f"Confidence must be between 0 and 1, got {insight.confidence}")
        return v

class ErrorResponse(BaseModel):
    error: str
    error_type: str
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None

class HealthStatus(BaseModel):
    status: str = Field(..., description="Overall health status")
    services: Dict[str, bool]
    system: Dict[str, float]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UploadResponse(BaseModel):
    request_id: str
    file_info: Dict[str, str]
    statistics: Optional[CSVAnalysisResult] = None
    message: str
    timestamp: str

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    request_id: str
    query: str
    response: str
    insights: List[NarrativeInsight]
    visualizations: List[ChartData]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "Show me sales trends over time",
                "response": "Sales have shown an upward trend...",
                "insights": [{
                    "type": "trend",
                    "description": "Consistent growth in Q3",
                    "confidence": 0.95,
                    "supporting_data": {
                        "chart_type": "line",
                        "title": "Quarterly Sales Growth",
                        "x_axis": "Quarter",
                        "y_axis": "Sales",
                        "data": []
                    }
                }],
                "visualizations": [{
                    "chart_type": "line",
                    "title": "Sales Over Time",
                    "x_axis": "Date",
                    "y_axis": "Sales",
                    "data": []
                }],
                "timestamp": "2024-03-20T10:00:00Z"
            }
        }
