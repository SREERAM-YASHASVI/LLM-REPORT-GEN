from utils.admin_db_utils import get_admin_client, setup_database, insert_test_data
import json
import os
from dotenv import load_dotenv

# Load environment variables from the specific path
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

def test_admin_connection():
    """
    Test the connection to Supabase with admin privileges.
    """
    try:
        print("Testing Supabase admin connection...")
        
        # Get the admin client
        supabase = get_admin_client()
        print("Admin client created successfully!")
        
        # Verify we can access the Supabase API
        try:
            user = supabase.auth.get_user()
            print(f"Authentication successful: {user}")
            print("✅ Admin privileges verified!")
            return True
        except Exception as e:
            print(f"Error authenticating: {e}")
            print("❌ Admin privileges verification failed.")
            return False
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def test_setup_database():
    """
    Test database setup process.
    """
    print("\n=== Testing Database Setup ===")
    result = setup_database()
    if result:
        print("✅ Database setup completed!")
    else:
        print("❌ Database setup failed!")
    return result

def test_insert_data():
    """
    Test inserting data into the tables.
    """
    print("\n=== Testing Data Insertion ===")
    result = insert_test_data()
    if result:
        print("✅ Test data inserted successfully!")
    else:
        print("❌ Test data insertion failed!")
    return result

if __name__ == "__main__":
    print("=== Supabase Admin Database Test ===")
    
    # Test admin connection
    if test_admin_connection():
        print("\n✅ Admin connection successful!")
        
        # Test database setup
        test_setup_database()
        
        # Test data insertion
        test_insert_data()
        
        print("\n=== Database Testing Complete ===")
    else:
        print("\n❌ Admin connection failed. Please check your SUPABASE_SERVICE_KEY.") 