import os
import json
import logging
import traceback
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from supabase import create_client
from pydantic import BaseModel
from dotenv import load_dotenv
import numpy as np
import voyageai

# Load environment variables
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

# Configure logging
logger = logging.getLogger(__name__)

# Supabase configuration
DEFAULT_SUPABASE_URL = "https://lgowncnnkdxptuvnsrvw.supabase.co"
SUPABASE_URL = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL)

# Try both keys, preferring service key
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Select which key to use (prefer service key for admin operations)
SUPABASE_API_KEY = SUPABASE_SERVICE_KEY or SUPABASE_KEY

# Detailed environment diagnostics
env_diagnostics = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_KEY_SET": bool(SUPABASE_SERVICE_KEY),
    "SUPABASE_KEY_SET": bool(SUPABASE_KEY), 
    "USING_KEY_TYPE": "SERVICE_KEY" if SUPABASE_SERVICE_KEY else ("KEY" if SUPABASE_KEY else "NONE")
}

# Log configuration details
if not SUPABASE_URL:
    logger.error(f"SUPABASE_URL not found in environment variables. Using default: {DEFAULT_SUPABASE_URL}")
else:
    logger.info(f"Using SUPABASE_URL: {SUPABASE_URL}")

if not SUPABASE_API_KEY:
    logger.error("No Supabase API key found. Checked both SUPABASE_SERVICE_KEY and SUPABASE_KEY.")
else:
    logger.info(f"Using Supabase key type: {env_diagnostics['USING_KEY_TYPE']}")

def generate_embedding(text: str) -> list:
    """
    Generate embedding for the given text using Voyage AI.
    Requires VOYAGE_API_KEY to be set in the environment.
    """
    try:
        voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if not voyage_api_key:
            raise RuntimeError("VOYAGE_API_KEY not set in environment.")
        vo = voyageai.Client(api_key=voyage_api_key)
        # Use 'voyage-3' as default model, input_type 'document' for doc, 'query' for queries
        # Here, we use 'document' for all, but you may want to distinguish in your app
        result = vo.embed([text], model="voyage-3", input_type="document")
        embedding = result.embeddings[0]
        return embedding
    except Exception as e:
        logging.error(f"Error generating embedding with Voyage AI: {e}")
        return []

class DocumentMetadata(BaseModel):
    """Model for document metadata"""
    filename: str
    upload_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_at: Optional[datetime] = None

class DocumentChunk(BaseModel):
    """Model for document chunk"""
    document_id: int
    chunk_index: int
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None

class ErrorDetails(BaseModel):
    """Model for storing detailed error information"""
    message: str
    error_type: str
    timestamp: datetime
    traceback: Optional[str] = None
    context: Dict[str, Any] = {}

class ConnectionStatus(BaseModel):
    """Model for database connection status"""
    is_connected: bool
    last_checked: datetime
    last_error: Optional[ErrorDetails] = None
    connection_attempts: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    env_diagnostics: Dict[str, Any] = {}

class DatabaseService:
    """Service to interact with Supabase database"""
    
    def __init__(self, max_retries=3, retry_delay=2):
        """
        Initialize Supabase client with retry logic
        
        Args:
            max_retries: Maximum number of connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = None
        self.is_connected = False
        self.status = ConnectionStatus(
            is_connected=False,
            last_checked=datetime.now(),
            env_diagnostics=env_diagnostics
        )
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self) -> bool:
        """
        Initialize Supabase client with retry logic
        Returns success status
        """
        if not SUPABASE_URL or not SUPABASE_API_KEY:
            error_msg = "Supabase credentials missing:"
            details = []
            if not SUPABASE_URL:
                details.append("SUPABASE_URL not set")
            if not SUPABASE_API_KEY:
                details.append("No API key found (checked SUPABASE_SERVICE_KEY and SUPABASE_KEY)")
            
            error_details = ErrorDetails(
                message=f"{error_msg} {', '.join(details)}",
                error_type="ConfigurationError",
                timestamp=datetime.now(),
                context=env_diagnostics
            )
            
            logger.error(f"{error_details.message}")
            self.status.last_error = error_details
            self.client = None
            self.is_connected = False
            return False
            
        # Attempt connection with retry
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Connecting to Supabase (attempt {attempt}/{self.max_retries})...")
                self.client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
                
                # Test connection with a simple query
                test_response = self.client.table("uploads").select("id").limit(1).execute()
                
                self.is_connected = True
                self.status.is_connected = True
                self.status.last_checked = datetime.now()
                self.status.connection_attempts += 1
                logger.info(f"Connected to Supabase successfully (attempt {attempt})")
                return True
                
            except Exception as e:
                error_details = ErrorDetails(
                    message=str(e),
                    error_type=type(e).__name__,
                    timestamp=datetime.now(),
                    traceback=traceback.format_exc(),
                    context={
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "supabase_url": SUPABASE_URL,
                        "key_type": env_diagnostics["USING_KEY_TYPE"]
                    }
                )
                
                logger.error(f"Failed to connect to Supabase (attempt {attempt}/{self.max_retries}): {e}")
                logger.debug(f"Connection error traceback: {error_details.traceback}")
                
                self.status.last_error = error_details
                self.status.connection_attempts += 1
                
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
        
        self.is_connected = False
        self.status.is_connected = False
        return False
    
    def check_connection(self) -> bool:
        """Check if database connection is alive with detailed diagnostics"""
        self.status.last_checked = datetime.now()
        
        if not self.is_connected or not self.client:
            logger.warning("Connection check failed: Client not initialized")
            return False
            
        try:
            # Simple query to check connection
            start_time = time.time()
            response = self.client.table("uploads").select("id").limit(1).execute()
            query_time = time.time() - start_time
            
            logger.info(f"Connection check successful (query time: {query_time:.3f}s)")
            self.status.successful_queries += 1
            self.is_connected = True
            self.status.is_connected = True
            return True
            
        except Exception as e:
            error_details = ErrorDetails(
                message=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(),
                traceback=traceback.format_exc()
            )
            
            logger.error(f"Database connection check failed: {e}")
            logger.debug(f"Connection error traceback: {error_details.traceback}")
            
            self.status.last_error = error_details
            self.status.failed_queries += 1
            self.is_connected = False
            self.status.is_connected = False
            
            # Attempt to reconnect
            logger.info("Attempting to reconnect...")
            reconnected = self._initialize_connection()
            if reconnected:
                logger.info("Successfully reconnected to database")
                return True
            else:
                logger.error("Failed to reconnect to database")
                return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status and diagnostics
        Returns a dictionary with connection information
        """
        # Update connection status before returning
        self.check_connection()
        
        # Convert to dict for easy serialization
        status_dict = self.status.model_dump()
        
        # Add any additional runtime diagnostics
        if self.client:
            status_dict["client_initialized"] = True
        else:
            status_dict["client_initialized"] = False
            
        return status_dict
    
    def _handle_db_operation(self, operation_name: str, func, *args, **kwargs) -> Tuple[bool, Any, Optional[ErrorDetails]]:
        """
        Generic handler for database operations with error handling
        
        Args:
            operation_name: Name of the operation for logging
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Tuple containing (success status, result data, error details if any)
        """
        if not self.is_connected:
            # Try to reconnect
            logger.warning(f"Not connected for {operation_name}, attempting to reconnect")
            if not self._initialize_connection():
                error_details = ErrorDetails(
                    message=f"Cannot {operation_name}: No database connection",
                    error_type="ConnectionError",
                    timestamp=datetime.now()
                )
                logger.error(error_details.message)
                return False, None, error_details
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            query_time = time.time() - start_time
            
            logger.debug(f"{operation_name} completed in {query_time:.3f}s")
            self.status.successful_queries += 1
            return True, result, None
            
        except Exception as e:
            error_details = ErrorDetails(
                message=str(e),
                error_type=type(e).__name__,
                timestamp=datetime.now(),
                traceback=traceback.format_exc(),
                context={"operation": operation_name}
            )
            
            logger.error(f"Error in {operation_name}: {e}")
            logger.debug(f"Error traceback: {error_details.traceback}")
            
            self.status.last_error = error_details
            self.status.failed_queries += 1
            
            # Check if we should attempt reconnection
            if "not connected" in str(e).lower() or "connection" in str(e).lower():
                logger.info(f"Connection issue detected, attempting to reconnect...")
                self._initialize_connection()
            
            return False, None, error_details
    
    async def store_document(self, metadata: DocumentMetadata) -> int:
        """
        Store document metadata in the uploads table
        Returns the document ID
        """
        doc_data = {
            "filename": metadata.filename,
            "upload_path": metadata.upload_path,
            "file_type": metadata.file_type,
            "file_size": metadata.file_size
            # uploaded_at will be set automatically by the database
        }
        
        def _execute_store():
            response = self.client.table("uploads").insert(doc_data).execute()
            if hasattr(response, 'data') and response.data:
                return response.data[0]['id']
            else:
                raise ValueError(f"Store document response has no data: {response}")
        
        success, result, error = self._handle_db_operation("store_document", _execute_store)
        
        if success:
            document_id = result
            logger.info(f"Document stored with ID: {document_id}")
            return document_id
        else:
            logger.error(f"Failed to store document: {error.message if error else 'Unknown error'}")
            return -1
    
    async def store_document_chunk(self, chunk: DocumentChunk) -> bool:
        """
        Store a document chunk in the document_chunks table
        Returns True if successful
        """
        chunk_data = {
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "embedding": chunk.embedding,
            "metadata": chunk.metadata
        }
        
        def _execute_store():
            response = self.client.table("document_chunks").insert(chunk_data).execute()
            if hasattr(response, 'data') and response.data:
                return True
            else:
                raise ValueError(f"Store chunk response has no data: {response}")
        
        success, result, error = self._handle_db_operation("store_document_chunk", _execute_store)
        
        if success:
            logger.info(f"Chunk stored for document ID: {chunk.document_id}, index: {chunk.chunk_index}")
            return True
        else:
            logger.error(f"Failed to store document chunk: {error.message if error else 'Unknown error'}")
            return False
    
    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents from the uploads table"""
        def _execute_query():
            response = self.client.table("uploads").select("*").order("uploaded_at", desc=True).execute()
            if hasattr(response, 'data'):
                return response.data
            else:
                return []
        
        success, result, error = self._handle_db_operation("get_all_documents", _execute_query)
        
        if success:
            return result
        else:
            logger.error(f"Error getting documents: {error.message if error else 'Unknown error'}")
            return []
    
    async def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document"""
        def _execute_query():
            response = self.client.table("document_chunks").select("*").eq("document_id", document_id).order("chunk_index").execute()
            if hasattr(response, 'data'):
                return response.data
            else:
                return []
        
        success, result, error = self._handle_db_operation("get_document_chunks", _execute_query)
        
        if success:
            return result
        else:
            logger.error(f"Error getting document chunks: {error.message if error else 'Unknown error'}")
            return []
    
    async def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Search documents based on content (simple text search)
        In a real implementation, this would use vector similarity search
        """
        def _execute_query():
            response = self.client.table("document_chunks").select("*").textSearch("content", query).execute()
            if hasattr(response, 'data'):
                return response.data
            else:
                return []
        
        success, result, error = self._handle_db_operation("search_documents", _execute_query)
        
        if success:
            return result
        else:
            logger.error(f"Error searching documents: {error.message if error else 'Unknown error'}")
            return []
    
    async def delete_document(self, document_id: int) -> bool:
        """Delete a document and all its chunks"""
        def _execute_delete():
            # Delete associated chunks first (foreign key constraint)
            chunks_response = self.client.table("document_chunks").delete().eq("document_id", document_id).execute()
            
            # Delete the document
            doc_response = self.client.table("uploads").delete().eq("id", document_id).execute()
            return True
        
        success, result, error = self._handle_db_operation("delete_document", _execute_delete)
        
        if success:
            logger.info(f"Deleted document ID: {document_id} and its chunks")
            return True
        else:
            logger.error(f"Error deleting document: {error.message if error else 'Unknown error'}")
            return False

    async def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags"""
        def _execute_query():
            response = self.client.table("tags").select("*").order("name").execute()
            if hasattr(response, 'data'):
                return response.data
            else:
                return []
        success, result, error = self._handle_db_operation("get_tags", _execute_query)
        return result if success else []

    async def add_tag(self, name: str, color: str = None) -> Optional[int]:
        """Add a new tag and return its ID"""
        def _execute_insert():
            tag_data = {"name": name}
            if color:
                tag_data["color"] = color
            response = self.client.table("tags").insert(tag_data).execute()
            if hasattr(response, 'data') and response.data:
                return response.data[0]['id']
            else:
                return None
        success, result, error = self._handle_db_operation("add_tag", _execute_insert)
        return result if success else None

    async def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag by ID"""
        def _execute_delete():
            response = self.client.table("tags").delete().eq("id", tag_id).execute()
            return True
        success, result, error = self._handle_db_operation("delete_tag", _execute_delete)
        return success

    async def get_document_tags(self, document_id: int) -> List[Dict[str, Any]]:
        """Get tags for a specific document"""
        def _execute_query():
            response = self.client.table("document_tags").select("tag_id, tags(name, color)").eq("document_id", document_id).execute()
            if hasattr(response, 'data'):
                return response.data
            else:
                return []
        success, result, error = self._handle_db_operation("get_document_tags", _execute_query)
        return result if success else []

    async def add_tag_to_document(self, document_id: int, tag_id: int) -> bool:
        """Associate a tag with a document"""
        def _execute_insert():
            response = self.client.table("document_tags").insert({"document_id": document_id, "tag_id": tag_id}).execute()
            return True
        success, result, error = self._handle_db_operation("add_tag_to_document", _execute_insert)
        return success

    async def remove_tag_from_document(self, document_id: int, tag_id: int) -> bool:
        """Remove a tag from a document"""
        def _execute_delete():
            response = self.client.table("document_tags").delete().eq("document_id", document_id).eq("tag_id", tag_id).execute()
            return True
        success, result, error = self._handle_db_operation("remove_tag_from_document", _execute_delete)
        return success

    async def vector_search_documents(self, query: str, top_k: int = 5) -> list:
        """
        Perform vector similarity search for the query using local embeddings and Supabase vector search.
        Returns top_k most similar document chunks.
        """
        # Generate embedding for the query
        query_embedding = generate_embedding(query)
        def _execute_query():
            # Supabase vector search: use .select().match() or .vectorSearch() depending on SDK
            # Here we use .match() for demonstration; adjust as needed for your SDK
            response = self.client.table("document_chunks") \
                .select("*") \
                .vector_search("embedding", query_embedding, match_threshold=0.7, top_k=top_k) \
                .execute()
            if hasattr(response, 'data'):
                return response.data
            else:
                return []
        success, result, error = self._handle_db_operation("vector_search_documents", _execute_query)
        if success:
            return result
        else:
            logger.error(f"Error in vector search: {error.message if error else 'Unknown error'}")
            return []

# Create global instance
database_service = DatabaseService() 