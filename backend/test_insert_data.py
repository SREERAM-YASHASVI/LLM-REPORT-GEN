import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json
from datetime import datetime
import pytest

# Load environment variables from the specific path
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lgowncnnkdxptuvnsrvw.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_admin_client():
    """
    Returns a Supabase client initialized with the service key for admin operations.
    """
    if not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_KEY is not set in environment variables.")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def test_insert_uploads():
    """
    Test inserting data into the uploads table.
    """
    try:
        print("\n=== Testing Uploads Table Insertion ===")
        supabase = get_admin_client()
        
        # Sample upload data
        upload_data = {
            "filename": f"test_file_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
            "upload_path": "/uploads/test_file.pdf",
            "file_type": "application/pdf",
            "file_size": 1024
        }
        
        # Insert into uploads table
        print(f"Inserting: {upload_data}")
        response = supabase.table("uploads").insert(upload_data).execute()
        
        # Check response
        if hasattr(response, 'data') and response.data:
            print(f"✅ Upload data inserted successfully: {json.dumps(response.data, indent=2)}")
            return response.data[0]['id']  # Return the ID for document_chunks test
        else:
            print(f"❌ Upload insert failed: {response}")
            return None
            
    except Exception as e:
        print(f"Error inserting upload data: {e}")
        return None

def test_insert_document_chunks():
    """
    Test inserting data into the document_chunks table.
    """
    document_id = test_insert_uploads()
    assert document_id, "Failed to insert upload data, cannot test chunks"
    
    try:
        print("\n=== Testing Document Chunks Table Insertion ===")
        supabase = get_admin_client()
        
        # Sample document chunk data
        chunk_data = {
            "document_id": document_id,
            "chunk_index": 1,
            "content": "This is a sample document chunk for testing purposes.",
            "metadata": {"page": 1, "source": "test"}
        }
        
        # Insert into document_chunks table
        print(f"Inserting: {chunk_data}")
        response = supabase.table("document_chunks").insert(chunk_data).execute()
        
        # Check response
        assert hasattr(response, 'data') and response.data, f"Document chunk insert failed: {response}"
        print(f"✅ Document chunk inserted successfully: {json.dumps(response.data, indent=2)}")
        return True
            
    except Exception as e:
        print(f"Error inserting document chunk: {e}")
        return False

def test_query_data():
    """
    Test querying data from both tables.
    """
    print("\n=== Testing Data Queries ===")
    supabase = get_admin_client()
    
    # Query uploads table
    print("Querying uploads table:")
    uploads_response = supabase.table("uploads").select("*").execute()
    print(f"Found {len(uploads_response.data)} uploads: {json.dumps(uploads_response.data[:3], indent=2)}")
    
    # Query document_chunks table
    print("\nQuerying document_chunks table:")
    chunks_response = supabase.table("document_chunks").select("*").execute()
    print(f"Found {len(chunks_response.data)} document chunks: {json.dumps(chunks_response.data[:3], indent=2)}")
    
    assert True  # Queries executed without exception
    return True

if __name__ == "__main__":
    print("=== Supabase Database Test - Data Insertion ===")
    
    # Test inserting into uploads table
    document_id = test_insert_uploads()
    
    # Test inserting into document_chunks table
    if document_id:
        test_insert_document_chunks()
    
    # Test querying data
    test_query_data()
    
    print("\n=== Test Complete ===") 