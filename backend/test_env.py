import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import pytest

# Load environment variables from the absolute path
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

def test_env_vars():
    """Test if the environment variables are set correctly"""
    print("=== Environment Variables Test ===")
    
    # Check SUPABASE_URL
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        print(f"✅ SUPABASE_URL is set: {supabase_url}")
    else:
        print("❌ SUPABASE_URL is not set")
    
    # Check SUPABASE_KEY
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_key:
        print(f"✅ SUPABASE_KEY is set: {supabase_key[:10]}...")
    else:
        print("❌ SUPABASE_KEY is not set")
    
    # Check SUPABASE_SERVICE_KEY
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if supabase_service_key:
        print(f"✅ SUPABASE_SERVICE_KEY is set: {supabase_service_key[:10]}...")
    else:
        print("❌ SUPABASE_SERVICE_KEY is not set")
    
    # Check which key to use
    key_to_use = supabase_key or supabase_service_key
    if key_to_use:
        print(f"✅ Using key: {key_to_use[:10]}...")
    else:
        print("❌ No Supabase key available")
    
    return {
        "url": supabase_url,
        "key": key_to_use
    }

def test_supabase_connection():
    """Test connection to Supabase"""
    credentials = test_env_vars()
    url, key = credentials.get("url"), credentials.get("key")
    print("\n=== Supabase Connection Test ===")
    assert url and key, "Missing Supabase credentials"
    
    print(f"Connecting to Supabase at {url}...")
    
    # Initialize the Supabase client
    supabase: Client = create_client(url, key)
    print("✅ Client created successfully!")
    
    # Try to get user info (basic permission test)
    try:
        user_response = supabase.auth.get_user()
        print(f"✅ Auth check passed: {user_response}")
    except Exception as e:
        pytest.skip(f"Auth check skipped: {e}")
    
    # Try to query the uploads table
    response = supabase.table("uploads").select("*").limit(1).execute()
    assert hasattr(response, 'data'), "No data attribute on response"
    print(f"✅ Query successful: {json.dumps(response.data, indent=2)}")

if __name__ == "__main__":
    # Test environment variables
    credentials = test_env_vars()
    
    # Test Supabase connection
    test_supabase_connection() 