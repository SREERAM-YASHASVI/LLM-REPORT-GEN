"""Service for processing documents into searchable chunks with embeddings."""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2
import docx
import json
from services.database_service import database_service, DocumentChunk, generate_embedding
from utils.logging_utils import setup_json_logging

# Configure logging
logger = setup_json_logging("document_processor")

class DocumentProcessorService:
    """Service to process documents into searchable chunks with embeddings (Voyage AI)"""
    
    def __init__(self, chunk_size: int = 1000):
        """
        Initialize document processor
        Args:
            chunk_size: Target size for text chunks in characters (for embedding)
        """
        self.chunk_size = chunk_size
    
    async def process_document(self, document_id: int, file_path: str, file_type: str) -> bool:
        """
        Process a document into chunks with embeddings (using Voyage AI),
        but SKIP chunking/embedding for CSV files (handled directly by LLM).
        Args:
            document_id: ID of the document in database
            file_path: Path to the document file
            file_type: MIME type of the document
        Returns:
            bool: True if processing successful
        """
        try:
            # Extract text based on file type
            text = self._extract_text(file_path, file_type)
            if not text:
                logger.warning(f"No text extracted from document {document_id}")
                return False

            # SKIP chunking/embedding for CSV files; handled directly by LLM
            if file_type == 'text/csv':
                logger.info(f"Skipping chunking/embedding for CSV document {document_id}; will be sent directly to LLM for analysis.")
                return True

            # Create chunks (for embedding)
            chunks = self._create_chunks(text)
            logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            
            # Store chunks with embeddings (Voyage AI)
            for i, chunk_text in enumerate(chunks):
                # Generate embedding (Voyage AI)
                embedding = generate_embedding(chunk_text)
                
                # Create chunk object
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=embedding,
                    metadata={
                        "type": file_type,
                        "chunk_number": i,
                        "total_chunks": len(chunks)
                    }
                )
                
                # Store in database
                success = await database_service.store_document_chunk(chunk)
                if not success:
                    logger.error(f"Failed to store chunk {i} for document {document_id}")
                    return False
                    
            logger.info(f"Successfully processed document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            return False
    
    def _extract_text(self, file_path: str, file_type: str) -> Optional[str]:
        """Extract text content from document based on type"""
        try:
            if file_type in ['text/plain', 'text/markdown', 'application/json']:
                # Text files
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
            elif file_type == 'application/pdf':
                # PDF files
                text = []
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    for page in pdf.pages:
                        text.append(page.extract_text())
                return '\n'.join(text)
                
            elif file_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # Word documents
                doc = docx.Document(file_path)
                return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                
            elif file_type == 'text/csv':
                # CSV files - read as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
            else:
                logger.warning(f"Unsupported file type: {file_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None
    
    def _create_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks of approximately target size for embedding.
        This is only for preparing text for embedding with Voyage AI.
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Split into paragraphs first
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # Skip empty paragraphs
            if not paragraph.strip():
                continue
                
            # If paragraph is too long, split into sentences
            if len(paragraph) > self.chunk_size:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if not sentence.strip():
                        continue
                        
                    # If adding this sentence exceeds chunk size, start new chunk
                    if current_size + len(sentence) > self.chunk_size:
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                            current_chunk = []
                            current_size = 0
                    
                    current_chunk.append(sentence)
                    current_size += len(sentence)
                    
            else:
                # If adding this paragraph exceeds chunk size, start new chunk
                if current_size + len(paragraph) > self.chunk_size:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                
                current_chunk.append(paragraph)
                current_size += len(paragraph)
        
        # Add final chunk if any
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

# Create global service instance
document_processor = DocumentProcessorService()
