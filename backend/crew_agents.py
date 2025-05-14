import logging
import os
from crewai import Agent, Task, Crew
from langchain.callbacks.base import BaseCallbackHandler
from utils.crewai_llm_adapter import CrewAILLMAdapter
import aiofiles
from typing import Dict, Any, List
import pandas as pd
import io
import math
import httpx
import time

logger = logging.getLogger(__name__)

class ThinkingCallback(BaseCallbackHandler):
    """Callback handler to capture thinking steps with improved filtering"""
    
    def __init__(self) -> None:
        BaseCallbackHandler.__init__(self)
        self.thinking_steps = []
        self.seen_prompts = set()  # Track seen prompts to avoid duplicates
        self.max_thinking_steps = 5  # Limit thinking steps to prevent overwhelming UI
        self.prompt_min_length = 50  # Minimum length to consider a prompt significant
        self.last_thinking_time = 0  # Track time between thinking steps
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called when LLM starts processing with improved filtering"""
        if not prompts or len(self.thinking_steps) >= self.max_thinking_steps:
            return
            
        # Extract meaningful content from the prompt (often buried in instruction text)
        content = prompts[0]
        
        # Simple heuristic - extract just the query part if it's a long prompt
        if len(content) > 500:
            # Try to find the actual query/task in the prompt
            lines = content.split('\n')
            for line in lines:
                if 'query' in line.lower() or 'question' in line.lower() or 'task' in line.lower():
                    content = line.strip()
                    break
            else:
                # If we can't find a specific query line, use a shortened version
                content = f"Analyzing data to answer the query..." 
        
        # Check if this is a duplicate or trivial prompt
        prompt_hash = hash(content)
        current_time = time.time()
        
        if (prompt_hash not in self.seen_prompts and 
            len(content) >= self.prompt_min_length and
            current_time - self.last_thinking_time >= 0.5):  # Rate limit thinking steps
            
            self.seen_prompts.add(prompt_hash)
            self.last_thinking_time = current_time
            
            self.thinking_steps.append({
                "type": "thinking",
                "content": content
            })

    def on_llm_end(self, response: Dict[str, Any], **kwargs: Any) -> None:
        """Called when LLM finishes processing, capturing only final results"""
        if response and "generations" in response:
            # Only capture the last conclusion to avoid overwhelming the UI
            if len(self.thinking_steps) < self.max_thinking_steps:
                for gen in response["generations"]:
                    if gen and gen[0].text:
                        # We care more about final conclusions 
                        self.thinking_steps.append({
                            "type": "conclusion",
                            "content": gen[0].text[:1000]  # Limit length
                        })
                        break  # Only take the first conclusion

class DocumentAnalysisCrew:
    def __init__(self):
        self.thinking_callback = ThinkingCallback()
        self.llm = CrewAILLMAdapter(
            model="claude-3-opus-20240229",
            temperature=0.7,
            callbacks=[self.thinking_callback]
        )

    async def check_api_health(self):
        """Check if Anthropic API key is configured"""
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not found in environment variables")
                return False
            return True
        except Exception as e:
            logger.error(f"API health check failed: {str(e)}")
            return False

    async def read_document(self, file_path):
        """Read document content asynchronously"""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return ""

    def dataframe_to_chartdata(self, df):
        """Convert a DataFrame to chartData for recharts (list of dicts with 'name' and 'value'), ensuring JSON serializability."""
        chart_data = []
        # Use the first two columns for a simple line chart if possible
        if len(df.columns) >= 2:
            x_col, y_col = df.columns[:2]
            for _, row in df.iterrows():
                x = str(row[x_col])
                y = row[y_col]
                # Convert to float or int, handle NaN/inf
                if isinstance(y, (float, int)):
                    if isinstance(y, float) and (math.isnan(y) or math.isinf(y)):
                        y = None
                else:
                    try:
                        y = float(y)
                        if math.isnan(y) or math.isinf(y):
                            y = None
                    except Exception:
                        y = None
                chart_data.append({"name": x, "value": y})
        elif len(df.columns) == 1:
            x_col = df.columns[0]
            for idx, val in enumerate(df[x_col]):
                y = val
                if isinstance(y, (float, int)):
                    if isinstance(y, float) and (math.isnan(y) or math.isinf(y)):
                        y = None
                else:
                    try:
                        y = float(y)
                        if math.isnan(y) or math.isinf(y):
                            y = None
                    except Exception:
                        y = None
                chart_data.append({"name": str(idx), "value": y})
        return chart_data

    async def read_csv_document(self, file_path):
        """Read and parse CSV content asynchronously using pandas, return summary and chartData."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            try:
                df = pd.read_csv(io.StringIO(content))
                preview = df.head(10).to_markdown(index=False)
                summary = f"CSV Preview (first 10 rows):\n{preview}\n\nColumns: {list(df.columns)}\nRows: {len(df)}"
                chart_data = self.dataframe_to_chartdata(df.head(100))  # Limit for frontend
                return {"summary": summary, "chartData": chart_data}
            except Exception as e:
                return {"summary": f"[CSV PARSE ERROR] {str(e)}", "chartData": []}
        except Exception as e:
            logger.error(f"Error reading CSV file {file_path}: {str(e)}")
            return {"summary": f"[FILE READ ERROR] {str(e)}", "chartData": []}

    def create_agents(self):
        # Document Analyzer Agent
        analyzer = Agent(
            role='CSV & Document Analyzer',
            goal='Analyze documents and CSVs, extract key information, summary statistics, trends, and anomalies',
            backstory='You are an expert at analyzing both unstructured documents and tabular CSV data. For CSVs, you provide summary statistics (mean, min, max, missing values), detect trends, and highlight anomalies. For text, you extract main points and relationships.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # Query Specialist Agent
        specialist = Agent(
            role='Query Specialist',
            goal='Process user queries and provide accurate, detailed answers from analyzed documents or CSVs',
            backstory='You are a specialist in understanding user queries and finding relevant information from analyzed documents or CSVs. You provide comprehensive, accurate answers based on the content, including tabular insights if available.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        return analyzer, specialist

    def create_tasks(self, query, document_contents):
        analyzer, specialist = self.create_agents()

        # Analysis Task
        analysis_task = Task(
            description=(
                "Analyze the following documents.\n"
                "For CSVs, provide: summary statistics (mean, min, max, missing values), trends, and anomalies. "
                "For text, extract key information.\n\n"
                f"{document_contents}"
            ),
            agent=analyzer
        )

        # Query Task
        query_task = Task(
            description=f"Based on the analysis, answer the following query: {query}",
            agent=specialist
        )

        return [analysis_task, query_task]

    async def process_query(self, query: str, document_paths: List[str]) -> Dict[str, Any]:
        self.thinking_callback.thinking_steps = []
        if not await self.check_api_health():
            raise Exception("Anthropic API is not properly configured")
        document_contents = []
        chart_data = None
        for path in document_paths:
            if path.lower().endswith('.csv'):
                csv_result = await self.read_csv_document(path)
                content = csv_result["summary"]
                chart_data = csv_result["chartData"]
            else:
                content = await self.read_document(path)
            if content:
                document_contents.append(f"Document: {path}\n{content}\n")
        if not document_contents:
            raise Exception("Failed to read any documents")
        tasks = self.create_tasks(query, "\n\n".join(document_contents))
        crew = Crew(
            agents=[task.agent for task in tasks],
            tasks=tasks,
            verbose=True
        )
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)
            response = {
                "result": result,
                "thinking_steps": self.thinking_callback.thinking_steps
            }
            if chart_data is not None:
                response["chartData"] = chart_data
            return response
        except Exception as e:
            logger.error(f"Error during crew execution: {str(e)}")
            raise
