"""Service for analyzing data in a secure sandbox."""
import logging
import uuid
from typing import Dict, Any, List, Optional
from utils.logging_utils import setup_json_logging
from utils.sandbox_utils import execute_in_sandbox, SecurityViolation, ResourceLimitExceeded
from utils.safe_pandas import create_safe_dataframe
from schemas.api_schemas import (
    CSVAnalysisResult,
    NarrativeInsight,
    ChartData,
    QueryResponse
)

# Configure logging
logger = setup_json_logging("analysis")

class AnalysisService:
    """Service for secure data analysis."""
    
    def __init__(self):
        """Initialize the analysis service."""
        pass
        
    def _generate_response_text(self, query: str, insights: List[NarrativeInsight]) -> str:
        """Generate a natural language response based on insights."""
        if not insights:
            return "No significant insights found in the data for your query."
            
        response_parts = []
        
        # Group insights by type
        stats = [i for i in insights if i.type == 'statistic']
        correlations = [i for i in insights if i.type == 'correlation']
        text_matches = [i for i in insights if i.type == 'text_match']
        
        # Add text matches first (for search results)
        if text_matches:
            response_parts.append("Here are the most relevant passages from your documents:")
            for match in text_matches:
                response_parts.append(f"• {match.description}")
        
        # Add statistical findings
        if stats:
            response_parts.append("\nHere are the key statistics:")
            for stat in stats:
                response_parts.append(f"• {stat.description}")
        
        # Add correlation findings
        if correlations:
            response_parts.append("\nI found these interesting relationships:")
            for corr in correlations:
                response_parts.append(f"• {corr.description}")
                
        # Combine all parts
        response = "\n".join(response_parts)
        
        return response

    def _analyze_data(self, safe_df: Any, query: str) -> Dict[str, Any]:
        """Analyze data using pandas operations."""
        insights = []
        charts = []
        
        try:
            # Basic statistics for numeric columns
            numeric_cols = safe_df.get_numeric_columns()
            for col in numeric_cols:
                mean_val = safe_df.mean(col)
                std_val = safe_df.std(col)
                insights.append({
                    'type': 'statistic',
                    'description': f'Average {col}: {mean_val:.2f} (std: {std_val:.2f})',
                    'confidence': 1.0
                })
            
            # Value distributions for categorical columns
            cat_cols = safe_df.get_categorical_columns()
            for col in cat_cols[:3]:  # Limit to first 3 categorical columns
                counts = safe_df.value_counts(col)
                charts.append({
                    'chart_type': 'bar',
                    'title': f'{col} Distribution',
                    'x_axis': col,
                    'y_axis': 'Count',
                    'data': [{'x': str(k), 'y': v} for k, v in counts.items()]
                })
            
            # Correlations between numeric columns
            for i, col1 in enumerate(numeric_cols[:-1]):
                for col2 in numeric_cols[i+1:]:
                    corr = safe_df.correlation(col1, col2)
                    if abs(corr) > 0.5:  # Only strong correlations
                        insights.append({
                            'type': 'correlation',
                            'description': f'Strong correlation ({corr:.2f}) between {col1} and {col2}',
                            'confidence': abs(corr)
                        })
        
        except Exception as e:
            logger.error(f"Error in data analysis: {e}")
            insights.append({
                'type': 'error',
                'description': 'Error analyzing data',
                'confidence': 0.0
            })
        
        return {
            'insights': insights,
            'charts': charts
        }
    
    def analyze_search_results(self, search_results: List[Dict[str, Any]], query: str) -> QueryResponse:
        """
        Analyze document chunks returned from database search.
        
        Args:
            search_results: List of document chunks from database search
            query: User's query string
            
        Returns:
            QueryResponse with insights from the search results
        """
        request_id = str(uuid.uuid4())  # Generate a temporary request ID
        try:
            logger.info(f"Analyzing {len(search_results)} search results for query: {query}")
            
            # Extract content and metadata from search results
            insights = []
            
            # Process each search result as a text match insight
            for i, result in enumerate(search_results[:5]):  # Limit to top 5 results
                content = result.get('content', '')
                doc_id = result.get('document_id', '')
                metadata = result.get('metadata', {})
                
                # Add this as a text match insight
                if content:
                    # Truncate long content for display
                    display_content = content[:200] + "..." if len(content) > 200 else content
                    
                    insights.append(NarrativeInsight(
                        type='text_match',
                        description=display_content,
                        confidence=0.9 - (i * 0.1)  # Decreasing confidence for later results
                    ))
            
            # Generate response text
            response_text = self._generate_response_text(query, insights)
            if not insights:
                response_text = "I couldn't find any specific information about that in your documents."
            
            # Create simple visualization if relevant
            visualizations = []
            if len(search_results) > 0:
                # Create a chart showing document distribution
                doc_counts = {}
                for result in search_results:
                    doc_id = result.get('document_id')
                    if doc_id not in doc_counts:
                        doc_counts[doc_id] = 0
                    doc_counts[doc_id] += 1
                
                if len(doc_counts) > 1:
                    # Only add visualization if we have multiple documents
                    visualizations.append(ChartData(
                        chart_type='bar',
                        title='Matches by Document',
                        x_axis='Document',
                        y_axis='Number of matches',
                        data=[{'x': f"Doc #{doc_id}", 'y': count} for doc_id, count in doc_counts.items()]
                    ))
            
            return QueryResponse(
                request_id=request_id,
                query=query,
                response=response_text,
                insights=insights,
                visualizations=visualizations
            )
            
        except Exception as e:
            logger.error("Error analyzing search results", extra={
                "error": str(e),
                "query": query
            })
            raise
        
    def analyze_csv(self, analysis_result: CSVAnalysisResult, query: str) -> QueryResponse:
        """
        Analyze CSV data using pandas operations.
        
        Args:
            analysis_result: Parsed CSV data and statistics
            query: User's analysis query
            
        Returns:
            QueryResponse with insights and visualizations
        """
        request_id = str(uuid.uuid4())  # Generate a temporary request ID
        try:
            # Create safe DataFrame wrapper
            safe_df = create_safe_dataframe(analysis_result.sample_rows)
            
            # Execute analysis
            result = self._analyze_data(safe_df, query)
            
            # Convert results to proper types
            insights = [
                NarrativeInsight(
                    type=insight['type'],
                    description=insight['description'],
                    confidence=insight['confidence']
                )
                for insight in result['insights']
            ]
            
            visualizations = [
                ChartData(
                    chart_type=chart['chart_type'],
                    title=chart['title'],
                    x_axis=chart['x_axis'],
                    y_axis=chart['y_axis'],
                    data=chart['data']
                )
                for chart in result['charts']
            ]
            
            # Generate a meaningful response based on insights
            response_text = self._generate_response_text(query, insights)
            
            return QueryResponse(
                request_id=request_id,
                query=query,
                response=response_text,
                insights=insights,
                visualizations=visualizations
            )
            
        except SecurityViolation as e:
            logger.error("Security violation in analysis", extra={
                "error": str(e),
                "query": query
            })
            raise
            
        except ResourceLimitExceeded as e:
            logger.error("Resource limit exceeded in analysis", extra={
                "error": str(e),
                "query": query
            })
            raise
            
        except Exception as e:
            logger.error("Error in analysis", extra={
                "error": str(e),
                "query": query
            })
            raise

# Create global service instance
analysis_service = AnalysisService()
