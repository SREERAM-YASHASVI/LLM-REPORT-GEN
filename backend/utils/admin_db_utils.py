import os
from dotenv import load_dotenv
from supabase import create_client, Client

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

def setup_database():
    """
    Set up the database with all required tables.
    This function uses Supabase's REST API for table operations.
    """
    try:
        # Get the admin client
        supabase = get_admin_client()
        
        # Test connection by getting user info
        user_response = supabase.auth.get_user()
        print(f"Connected as: {user_response}")
        
        # We can perform administrative operations via the Supabase REST API
        # For most operations, we'll need to use the Supabase Dashboard or SQL Editor
        
        # For now, we'll check if our tables exist by attempting to select from them
        # If they don't exist, we'll assume the tables need to be created via Supabase Dashboard
        
        try:
            # Try to select from uploads table
            uploads_response = supabase.table("uploads").select("*").limit(1).execute()
            print(f"Uploads table exists. Sample data: {uploads_response}")
        except Exception as e:
            print(f"Uploads table may not exist: {e}")
            print("Please create the uploads table in Supabase SQL Editor or Dashboard.")
            print("""
            -- SQL for creating uploads table:
            CREATE TABLE public.uploads (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_path TEXT NOT NULL,
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                file_type TEXT,
                file_size INTEGER
            );
            """)
        
        try:
            # Try to select from document_chunks table
            chunks_response = supabase.table("document_chunks").select("*").limit(1).execute()
            print(f"Document chunks table exists. Sample data: {chunks_response}")
        except Exception as e:
            print(f"Document chunks table may not exist: {e}")
            print("Please create the document_chunks table in Supabase SQL Editor or Dashboard.")
            print("""
            -- SQL for creating document_chunks table:
            CREATE TABLE public.document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding VECTOR(1536),
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(document_id, chunk_index)
            );
            """)
        
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

def insert_test_data():
    """
    Insert test data into the uploads table.
    """
    try:
        supabase = get_admin_client()
        
        # Insert a test record into uploads
        test_data = {
            "filename": "test_document.pdf",
            "upload_path": "/uploads/test_document.pdf",
            "file_type": "application/pdf",
            "file_size": 1024
        }
        
        response = supabase.table("uploads").insert(test_data).execute()
        print(f"Test data inserted into uploads: {response}")
        
        return True
    except Exception as e:
        print(f"Error inserting test data: {e}")
        return False 