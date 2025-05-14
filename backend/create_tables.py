import os
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
import json

# Load environment variables from the specific path
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lgowncnnkdxptuvnsrvw.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Function to execute SQL using direct REST API
def execute_sql(sql_query):
    """Execute SQL directly using REST API with service key authentication."""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY is not set in environment variables")
    
    # Endpoint for SQL execution
    url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
    
    # Headers for authentication
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # Data payload
    data = {
        "query": sql_query
    }
    
    try:
        # Make the POST request
        response = requests.post(url, headers=headers, json=data)
        
        # Check if successful
        if response.status_code in (200, 201, 204):
            print(f"Query executed successfully: {sql_query[:50]}...")
            try:
                return response.json()
            except:
                return {"success": True, "status_code": response.status_code}
        else:
            print(f"Error executing query: {response.status_code}")
            print(f"Response: {response.text}")
            return {"error": response.text, "status_code": response.status_code}
            
    except Exception as e:
        print(f"Exception occurred: {e}")
        return {"error": str(e)}

def create_tables():
    """Create all required tables for the application."""
    print("Creating database tables...")
    
    # SQL for creating uploads table
    uploads_sql = """
    CREATE TABLE IF NOT EXISTS public.uploads (
        id SERIAL PRIMARY KEY,
        filename TEXT NOT NULL,
        upload_path TEXT NOT NULL,
        uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        file_type TEXT,
        file_size INTEGER
    );
    """
    
    # SQL for creating document_chunks table
    document_chunks_sql = """
    CREATE TABLE IF NOT EXISTS public.document_chunks (
        id SERIAL PRIMARY KEY,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding VECTOR(1536),
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(document_id, chunk_index)
    );
    """
    
    # Create a regular Supabase client to check if tables exist
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Try to create tables using the REST API
    try:
        # Check if the uploads table exists
        try:
            response = supabase.table("uploads").select("id").limit(1).execute()
            print("Uploads table already exists.")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Table doesn't exist, create it
                print("Creating uploads table...")
                # Here, we would typically use the execute_sql function, but since it's not available by default,
                # we'll need to inform the user to create it manually
                print("To create the uploads table, please add the following SQL in the Supabase SQL Editor:")
                print(uploads_sql)
            else:
                print(f"Error checking uploads table: {e}")
        
        # Check if the document_chunks table exists
        try:
            response = supabase.table("document_chunks").select("id").limit(1).execute()
            print("Document chunks table already exists.")
        except Exception as e:
            if "relation" in str(e) and "does not exist" in str(e):
                # Table doesn't exist, create it
                print("Creating document_chunks table...")
                # Here, we would typically use the execute_sql function, but since it's not available by default,
                # we'll need to inform the user to create it manually
                print("To create the document_chunks table, please add the following SQL in the Supabase SQL Editor:")
                print(document_chunks_sql)
            else:
                print(f"Error checking document_chunks table: {e}")
        
        print("\nIMPORTANT: To create these tables, you'll need to:")
        print("1. Go to the Supabase dashboard at https://app.supabase.io")
        print("2. Select your project")
        print("3. Go to the SQL Editor")
        print("4. Create a new query and paste each SQL statement")
        print("5. Run the query to create the tables")
        
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_tables() 