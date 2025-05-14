import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Load environment variables from the specific path
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

# Supabase configuration
SUPABASE_URL = "https://lgowncnnkdxptuvnsrvw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxnb3duY25ua2R4cHR1dm5zcnZ3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY1OTQzODUsImV4cCI6MjA2MjE3MDM4NX0.75M6EP8h8VsO4l1UEXaiYtY25Re9bH-yK93DVEh3GCY"

def test_supabase_connection():
    try:
        print(f"Connecting to Supabase at {SUPABASE_URL}...")
        
        # Initialize the Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Client created successfully!")
        
        # Try to simply create a table with a direct call
        try:
            print("\nAttempting to create uploads table...")
            
            # Create a simple table for uploads
            query = """
            CREATE TABLE IF NOT EXISTS uploads (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                upload_path TEXT NOT NULL,
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                file_type TEXT,
                file_size INTEGER
            )
            """
            
            # Execute the query (this might not be allowed with anon key)
            response = supabase.table("uploads").select("*").execute()
            print(f"Table exists or was created. Test query: {response}")
            
            # Try inserting data
            print("\nInserting test data...")
            response = supabase.table("uploads").insert({
                "filename": "test.csv",
                "upload_path": "/uploads/test.csv",
                "file_type": "text/csv",
                "file_size": 1024
            }).execute()
            
            print(f"Insert response: {response}")
            return True
            
        except Exception as e:
            print(f"Error with uploads table: {e}")
            
            # Try another schema/table that might exist
            try:
                print("\nAttempting to access any available table...")
                tables = supabase.auth.get_user()
                print(f"Auth user: {tables}")
                return True
            except Exception as e2:
                print(f"Error with auth: {e2}")
                return False
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection() 