from crewai import Agent, Task, Crew
from langchain_community.llms import Ollama
import httpx
import logging
import aiofiles

logger = logging.getLogger(__name__)

class DocumentAnalysisCrew:
    def __init__(self):
        self.llm = Ollama(
            model="deepseek-r1:1.5b",
            base_url="http://localhost:11434",
            temperature=0.7
        )

    async def check_ollama_health(self):
        """Check if Ollama server is running"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:11434/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
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

    def create_agents(self):
        # Document Analyzer Agent
        analyzer = Agent(
            role='Document Analyzer',
            goal='Analyze documents thoroughly and extract key information',
            backstory='You are an expert at analyzing documents and identifying key information. You carefully read through documents and understand their main points, key details, and relationships between concepts.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        # Query Specialist Agent
        specialist = Agent(
            role='Query Specialist',
            goal='Process user queries and provide accurate, detailed answers from analyzed documents',
            backstory='You are a specialist in understanding user queries and finding relevant information from analyzed documents. You provide comprehensive, accurate answers based on the document content.',
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

        return analyzer, specialist

    def create_tasks(self, query, document_contents):
        analyzer, specialist = self.create_agents()

        # Analysis Task
        analysis_task = Task(
            description=f"Analyze the following documents and extract key information:\n\n{document_contents}",
            agent=analyzer
        )

        # Query Task
        query_task = Task(
            description=f"Based on the analysis, answer the following query: {query}",
            agent=specialist
        )

        return [analysis_task, query_task]

    async def process_query(self, query, document_paths):
        # Check Ollama health first
        if not await self.check_ollama_health():
            raise Exception("Ollama server is not available")

        # Read all documents
        document_contents = []
        for path in document_paths:
            content = await self.read_document(path)
            if content:
                document_contents.append(f"Document: {path}\n{content}\n")

        if not document_contents:
            raise Exception("Failed to read any documents")

        # Create crew with tasks
        tasks = self.create_tasks(query, "\n\n".join(document_contents))
        crew = Crew(
            agents=[task.agent for task in tasks],
            tasks=tasks,
            verbose=True
        )

        # Get crew's response
        try:
            # Run crew.kickoff() in a separate thread since it's synchronous
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)
            return result
        except Exception as e:
            logger.error(f"Error during crew execution: {str(e)}")
            raise
