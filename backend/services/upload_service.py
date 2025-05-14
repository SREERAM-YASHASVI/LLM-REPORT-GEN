from typing import Dict, Any, List
import os
import logging
import aiofiles
from fastapi import UploadFile
from pydantic import BaseModel
from services.database_service import database_service, DocumentMetadata

logger = logging.getLogger(__name__)

class UploadResponse(BaseModel):
    filename: str
    path: str
    status: str

class UploadService:
    def __init__(self, upload_dir: str = None):
        # Use absolute path for uploads directory
        self.upload_dir = upload_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        self.uploaded_documents = []
        self.unsynced_metadata = []  # Queue for metadata that failed to save
        self._ensure_upload_dir()
        # Initialize with empty list, will be populated when needed

    def _ensure_upload_dir(self):
        """Ensure upload directory exists with proper permissions"""
        try:
            os.makedirs(self.upload_dir, exist_ok=True)
            os.chmod(self.upload_dir, 0o755)
            logger.info(f"Upload directory ensured at: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create/configure upload directory: {str(e)}")
            raise

    async def _load_existing_files(self):
        """Load existing files from the database and local directory"""
        # First try to load from database
        if database_service.is_connected:
            try:
                db_documents = await database_service.get_all_documents()
                if db_documents:
                    self.uploaded_documents = []
                    for doc in db_documents:
                        # Verify file exists locally
                        if os.path.isfile(doc["upload_path"]):
                            self.uploaded_documents.append({
                                "id": doc["id"],
                                "name": doc["filename"],
                                "path": doc["upload_path"],
                                "type": doc.get("file_type"),
                                "size": doc.get("file_size"),
                                "uploaded_at": doc.get("uploaded_at")
                            })
                    logger.info(f"Loaded {len(self.uploaded_documents)} documents from database")
                    return
            except Exception as e:
                logger.error(f"Error loading documents from database: {e}")
        
        # Fallback to loading from filesystem
        logger.info("Loading documents from filesystem (database not available)")
        for filename in os.listdir(self.upload_dir):
            file_path = os.path.join(self.upload_dir, filename)
            if os.path.isfile(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    file_type = self._get_file_type(filename)
                    
                    doc_info = {
                        "name": filename,
                        "path": file_path,
                        "type": file_type,
                        "size": file_size
                    }
                    self.uploaded_documents.append(doc_info)
                    
                    # Try to add to database for future reference
                    if database_service.is_connected:
                        metadata = DocumentMetadata(
                            filename=filename,
                            upload_path=file_path,
                            file_type=file_type,
                            file_size=file_size
                        )
                        await database_service.store_document(metadata)
                        
                except Exception as e:
                    logger.error(f"Error processing existing file {filename}: {e}")

    def _get_file_type(self, filename: str) -> str:
        """Get file MIME type based on extension"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        mime_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }
        return mime_types.get(extension, 'application/octet-stream')

    async def upload_file(self, file: UploadFile, request_id: str) -> UploadResponse:
        """Handle file upload and storage"""
        try:
            # Store file in backend/uploads directory
            file_path = os.path.join(self.upload_dir, file.filename)
            # Store path for DB as 'backend/uploads/filename' (relative to project root)
            db_path = os.path.join("document-query-app/backend/uploads", file.filename)
            # Read file asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                contents = await file.read()
                await f.write(contents)
            os.chmod(file_path, 0o644)
            file_size = os.path.getsize(file_path)
            file_type = self._get_file_type(file.filename)
            metadata = DocumentMetadata(
                filename=file.filename,
                upload_path=db_path,  # Store backend-relative path in DB
                file_type=file_type,
                file_size=file_size
            )
            document_id = -1
            if database_service.is_connected:
                try:
                    document_id = await database_service.store_document(metadata)
                    if document_id <= 0:
                        raise Exception("Failed to store document metadata in DB")
                except Exception as e:
                    logger.error(f"[{request_id}] Error saving metadata to DB, queuing for retry: {str(e)}")
                    self.unsynced_metadata.append(metadata)
            else:
                logger.warning(f"[{request_id}] DB not connected, queuing metadata for retry")
                self.unsynced_metadata.append(metadata)
            doc_info = {
                "id": document_id if document_id > 0 else None,
                "name": file.filename,
                "path": file_path,
                "type": file_type,
                "size": file_size
            }
            self.uploaded_documents.append(doc_info)
            logger.info(f"[{request_id}] Successfully uploaded file: {file.filename} (path: {file_path}, id: {document_id})")
            # Validation: check file existence
            if not os.path.isfile(file_path):
                logger.error(f"[{request_id}] Uploaded file does not exist at expected path: {file_path}")
            else:
                logger.info(f"[{request_id}] File exists at: {file_path}")
            return UploadResponse(
                filename=file.filename,
                path=file_path,
                status="success"
            )
        except Exception as e:
            logger.error(f"[{request_id}] Error uploading file: {str(e)}")
            raise

    async def get_uploaded_documents(self) -> List[Dict[str, Any]]:
        """Get list of uploaded documents"""
        orphaned_documents = []
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if database_service.is_connected:
            try:
                db_documents = await database_service.get_all_documents()
                uploaded_documents = []
                for doc in db_documents:
                    # Join project root with DB path
                    file_path = os.path.join(project_root, doc["upload_path"]) if not os.path.isabs(doc["upload_path"]) else doc["upload_path"]
                    if os.path.isfile(file_path):
                        uploaded_documents.append({
                            "id": doc["id"],
                            "name": doc["filename"],
                            "path": file_path,
                            "type": doc.get("file_type"),
                            "size": doc.get("file_size"),
                            "uploaded_at": doc.get("uploaded_at")
                        })
                    else:
                        logger.warning(f"Orphaned document in DB but missing file: id={doc['id']}, name={doc['filename']}, path={file_path}")
                        orphaned_documents.append(doc)
                logger.info(f"Fetched {len(uploaded_documents)} documents from database. Orphaned: {len(orphaned_documents)}")
                return uploaded_documents
            except Exception as e:
                logger.error(f"Error fetching documents from database: {e}. Falling back to in-memory cache.")
        else:
            logger.warning("Database not connected. Using in-memory cache for uploaded documents.")
        return self.uploaded_documents

    async def cleanup_file(self, filename: str):
        """Remove a file and its entry from uploaded documents and database"""
        try:
            file_path = os.path.join(self.upload_dir, filename)
            
            # Find the document ID
            document_id = None
            for doc in self.uploaded_documents:
                if doc["name"] == filename:
                    document_id = doc.get("id")
                    break
            
            # Delete from database if ID exists
            if document_id and database_service.is_connected:
                await database_service.delete_document(document_id)
            
            # Delete file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Remove from local list
            self.uploaded_documents = [
                doc for doc in self.uploaded_documents 
                if doc["name"] != filename
            ]
            
            logger.info(f"Cleaned up file: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up file {filename}: {str(e)}")

    async def sync_unsynced_metadata(self):
        """Attempt to sync any unsaved file metadata to the database."""
        if not self.unsynced_metadata:
            logger.info("No unsynced metadata to sync.")
            return
        if not database_service.is_connected:
            logger.warning("Database not connected. Cannot sync unsynced metadata.")
            return
        logger.info(f"Attempting to sync {len(self.unsynced_metadata)} unsynced metadata entries.")
        still_unsynced = []
        for metadata in self.unsynced_metadata:
            try:
                document_id = await database_service.store_document(metadata)
                if document_id > 0:
                    logger.info(f"Successfully synced metadata for file: {metadata.filename}")
                else:
                    logger.error(f"Failed to sync metadata for file: {metadata.filename}")
                    still_unsynced.append(metadata)
            except Exception as e:
                logger.error(f"Error syncing metadata for file {metadata.filename}: {str(e)}")
                still_unsynced.append(metadata)
        self.unsynced_metadata = still_unsynced

# Create global upload service instance
upload_service = UploadService()
