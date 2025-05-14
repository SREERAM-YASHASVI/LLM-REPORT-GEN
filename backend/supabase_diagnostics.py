import os
import sys
import json
import time
import traceback
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
from rich.console import Console
from rich.table import Table

# Load environment variables from the absolute path
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')

# Initialize console for pretty output
console = Console()

def check_env_vars():
    """Test if the environment variables are set correctly"""
    console.print("\n[bold blue]== Environment Variables Check ==[/bold blue]")
    
    env_status = {}
    
    # Check SUPABASE_URL
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        console.print(f"✅ SUPABASE_URL is set: {supabase_url}")
        env_status["SUPABASE_URL"] = {"status": "ok", "value": supabase_url}
    else:
        console.print("❌ [bold red]SUPABASE_URL is not set[/bold red]")
        env_status["SUPABASE_URL"] = {"status": "missing"}
    
    # Check SUPABASE_KEY
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_key:
        masked_key = f"{supabase_key[:10]}..."
        console.print(f"✅ SUPABASE_KEY is set: {masked_key}")
        env_status["SUPABASE_KEY"] = {"status": "ok", "value_prefix": supabase_key[:10]}
    else:
        console.print("❌ [bold yellow]SUPABASE_KEY is not set[/bold yellow]")
        env_status["SUPABASE_KEY"] = {"status": "missing"}
    
    # Check SUPABASE_SERVICE_KEY
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if supabase_service_key:
        masked_key = f"{supabase_service_key[:10]}..."
        console.print(f"✅ SUPABASE_SERVICE_KEY is set: {masked_key}")
        env_status["SUPABASE_SERVICE_KEY"] = {"status": "ok", "value_prefix": supabase_service_key[:10]}
    else:
        console.print("❌ [bold red]SUPABASE_SERVICE_KEY is not set[/bold red]")
        env_status["SUPABASE_SERVICE_KEY"] = {"status": "missing"}
    
    # Determine which key to use
    key_to_use = supabase_service_key or supabase_key
    if key_to_use:
        masked_key = f"{key_to_use[:10]}..."
        console.print(f"✅ Using key: {masked_key}")
        env_status["key_to_use"] = {"status": "ok", "type": "SERVICE_KEY" if supabase_service_key else "KEY"}
    else:
        console.print("❌ [bold red]No Supabase key available[/bold red]")
        env_status["key_to_use"] = {"status": "missing"}
    
    return {
        "url": supabase_url,
        "key": key_to_use,
        "status": env_status
    }

def test_basic_connection(url, key):
    """Test basic connection to Supabase"""
    console.print("\n[bold blue]== Basic Connection Test ==[/bold blue]")
    
    if not url or not key:
        console.print("❌ [bold red]Missing Supabase credentials, skipping connection test[/bold red]")
        return False
    
    console.print(f"Connecting to Supabase at {url}...")
    
    try:
        # Initialize the Supabase client
        start_time = time.time()
        supabase: Client = create_client(url, key)
        init_time = time.time() - start_time
        console.print(f"✅ Client created successfully (took {init_time:.3f}s)")
        
        # Try to get user info (basic permission test)
        try:
            start_time = time.time()
            user_response = supabase.auth.get_user()
            auth_time = time.time() - start_time
            console.print(f"✅ Auth check passed (took {auth_time:.3f}s)")
        except Exception as e:
            console.print(f"⚠️ [bold yellow]Auth check failed: {e}[/bold yellow]")
            console.print("This may be expected with anon key or if auth is not set up")
        
        return supabase
    except Exception as e:
        console.print(f"❌ [bold red]Connection failed: {e}[/bold red]")
        console.print("[dim]Traceback:[/dim]")
        console.print_exception()
        return False

def test_tables(supabase):
    """Test if required tables exist and have correct structure"""
    console.print("\n[bold blue]== Database Tables Check ==[/bold blue]")
    
    if not supabase:
        console.print("❌ [bold red]No Supabase connection, skipping tables test[/bold red]")
        return False
    
    tables_status = {}
    
    # Check uploads table
    console.print("Testing 'uploads' table...")
    try:
        start_time = time.time()
        response = supabase.table("uploads").select("*").limit(1).execute()
        query_time = time.time() - start_time
        
        if hasattr(response, 'data'):
            if response.data:
                console.print(f"✅ 'uploads' table exists and contains data (query: {query_time:.3f}s)")
                console.print(f"   First record: {json.dumps(response.data[0], indent=2)}")
                tables_status["uploads"] = {"status": "ok", "count": len(response.data), "sample": response.data[0]}
            else:
                console.print(f"✅ 'uploads' table exists but is empty (query: {query_time:.3f}s)")
                tables_status["uploads"] = {"status": "empty"}
        else:
            console.print("⚠️ [bold yellow]'uploads' table check returned unexpected response format[/bold yellow]")
            tables_status["uploads"] = {"status": "unknown"}
    except Exception as e:
        console.print(f"❌ [bold red]'uploads' table error: {e}[/bold red]")
        if "does not exist" in str(e):
            tables_status["uploads"] = {"status": "missing"}
            
            # Show the SQL to create the table
            console.print("\n[italic]To create the uploads table, run this SQL in Supabase SQL Editor:[/italic]")
            console.print("""
CREATE TABLE IF NOT EXISTS public.uploads (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_path TEXT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_type TEXT,
    file_size INTEGER
);
            """)
        else:
            tables_status["uploads"] = {"status": "error", "error": str(e)}
    
    # Check document_chunks table
    console.print("\nTesting 'document_chunks' table...")
    try:
        start_time = time.time()
        response = supabase.table("document_chunks").select("*").limit(1).execute()
        query_time = time.time() - start_time
        
        if hasattr(response, 'data'):
            if response.data:
                console.print(f"✅ 'document_chunks' table exists and contains data (query: {query_time:.3f}s)")
                console.print(f"   First record: {json.dumps(response.data[0], indent=2)}")
                tables_status["document_chunks"] = {"status": "ok", "count": len(response.data), "sample": response.data[0]}
            else:
                console.print(f"✅ 'document_chunks' table exists but is empty (query: {query_time:.3f}s)")
                tables_status["document_chunks"] = {"status": "empty"}
        else:
            console.print("⚠️ [bold yellow]'document_chunks' table check returned unexpected response format[/bold yellow]")
            tables_status["document_chunks"] = {"status": "unknown"}
    except Exception as e:
        console.print(f"❌ [bold red]'document_chunks' table error: {e}[/bold red]")
        if "does not exist" in str(e):
            tables_status["document_chunks"] = {"status": "missing"}
            
            # Show the SQL to create the table
            console.print("\n[italic]To create the document_chunks table, run this SQL in Supabase SQL Editor:[/italic]")
            console.print("""
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
            """)
        else:
            tables_status["document_chunks"] = {"status": "error", "error": str(e)}
    
    return tables_status

def test_data_operations(supabase):
    """Test data operations (insert, select, delete)"""
    console.print("\n[bold blue]== Data Operations Test ==[/bold blue]")
    
    if not supabase:
        console.print("❌ [bold red]No Supabase connection, skipping data operations test[/bold red]")
        return False
    
    operations_status = {}
    test_id = None
    
    # Test INSERT operation
    console.print("Testing INSERT operation...")
    try:
        # Create test data
        test_data = {
            "filename": f"test_file_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt",
            "upload_path": "/uploads/test_file.txt",
            "file_type": "text/plain",
            "file_size": 1024
        }
        
        start_time = time.time()
        response = supabase.table("uploads").insert(test_data).execute()
        insert_time = time.time() - start_time
        
        if hasattr(response, 'data') and response.data:
            test_id = response.data[0]['id']
            console.print(f"✅ INSERT successful (took {insert_time:.3f}s)")
            console.print(f"   Record ID: {test_id}")
            operations_status["insert"] = {"status": "ok", "time": f"{insert_time:.3f}s", "record_id": test_id}
        else:
            console.print("❌ [bold red]INSERT returned unexpected response format[/bold red]")
            operations_status["insert"] = {"status": "error", "response": str(response)}
    except Exception as e:
        console.print(f"❌ [bold red]INSERT error: {e}[/bold red]")
        operations_status["insert"] = {"status": "error", "error": str(e)}
    
    # Test SELECT operation if insert was successful
    if test_id:
        console.print("\nTesting SELECT operation...")
        try:
            start_time = time.time()
            response = supabase.table("uploads").select("*").eq("id", test_id).execute()
            select_time = time.time() - start_time
            
            if hasattr(response, 'data') and response.data and len(response.data) == 1:
                console.print(f"✅ SELECT successful (took {select_time:.3f}s)")
                console.print(f"   Record: {json.dumps(response.data[0], indent=2)}")
                operations_status["select"] = {"status": "ok", "time": f"{select_time:.3f}s"}
            else:
                console.print("❌ [bold red]SELECT returned unexpected response format[/bold red]")
                operations_status["select"] = {"status": "error", "response": str(response)}
        except Exception as e:
            console.print(f"❌ [bold red]SELECT error: {e}[/bold red]")
            operations_status["select"] = {"status": "error", "error": str(e)}
        
        # Test DELETE operation if we have a test ID
        console.print("\nTesting DELETE operation...")
        try:
            start_time = time.time()
            response = supabase.table("uploads").delete().eq("id", test_id).execute()
            delete_time = time.time() - start_time
            
            if hasattr(response, 'data'):
                console.print(f"✅ DELETE successful (took {delete_time:.3f}s)")
                operations_status["delete"] = {"status": "ok", "time": f"{delete_time:.3f}s"}
            else:
                console.print("❌ [bold red]DELETE returned unexpected response format[/bold red]")
                operations_status["delete"] = {"status": "error", "response": str(response)}
        except Exception as e:
            console.print(f"❌ [bold red]DELETE error: {e}[/bold red]")
            operations_status["delete"] = {"status": "error", "error": str(e)}
    
    return operations_status

def performance_test(supabase):
    """Test performance of Supabase operations"""
    console.print("\n[bold blue]== Performance Test ==[/bold blue]")
    
    if not supabase:
        console.print("❌ [bold red]No Supabase connection, skipping performance test[/bold red]")
        return False
    
    # Test different operations with timing
    results = {}
    
    # Test simple query performance
    console.print("Testing query performance...")
    operations = [
        ("Simple SELECT", lambda: supabase.table("uploads").select("id").limit(5).execute()),
        ("COUNT query", lambda: supabase.table("uploads").select("id", count="exact").execute()),
        ("ORDER BY query", lambda: supabase.table("uploads").select("*").order("uploaded_at", desc=True).limit(5).execute())
    ]
    
    # Create a table for results
    table = Table(title="Supabase Query Performance")
    table.add_column("Operation", style="cyan")
    table.add_column("Attempt 1", style="green")
    table.add_column("Attempt 2", style="green")
    table.add_column("Attempt 3", style="green")
    table.add_column("Average", style="yellow")
    
    for name, operation in operations:
        times = []
        for i in range(3):
            try:
                start_time = time.time()
                operation()
                elapsed = time.time() - start_time
                times.append(elapsed)
            except Exception as e:
                console.print(f"❌ Error in {name}: {e}")
                times.append(None)
        
        # Calculate average (excluding None values)
        valid_times = [t for t in times if t is not None]
        avg = sum(valid_times) / len(valid_times) if valid_times else None
        
        # Format times for display
        time_strs = [f"{t:.4f}s" if t is not None else "failed" for t in times]
        avg_str = f"{avg:.4f}s" if avg is not None else "N/A"
        
        table.add_row(name, *time_strs, avg_str)
        results[name] = {"times": times, "average": avg}
    
    console.print(table)
    return results

def generate_report(env_info, tables_info, operations_info, performance_info):
    """Generate a summary report"""
    console.print("\n[bold blue]== Diagnostic Summary Report ==[/bold blue]")
    
    # Environment status
    env_status = "✅ OK" if env_info["key"] else "❌ FAIL"
    console.print(f"Environment Variables: {env_status}")
    
    # Tables status
    if not tables_info:
        tables_status = "❌ FAIL (No connection)"
    else:
        uploads_ok = tables_info.get("uploads", {}).get("status") in ["ok", "empty"]
        chunks_ok = tables_info.get("document_chunks", {}).get("status") in ["ok", "empty"]
        
        if uploads_ok and chunks_ok:
            tables_status = "✅ OK"
        elif uploads_ok or chunks_ok:
            tables_status = "⚠️ PARTIAL"
        else:
            tables_status = "❌ FAIL"
    
    console.print(f"Database Tables: {tables_status}")
    
    # Operations status
    if not operations_info:
        operations_status = "❌ FAIL (No connection)"
    else:
        all_ok = all(op.get("status") == "ok" for op in operations_info.values())
        operations_status = "✅ OK" if all_ok else "❌ FAIL"
    
    console.print(f"Data Operations: {operations_status}")
    
    # Generate recommendations
    console.print("\n[bold]Recommendations:[/bold]")
    
    if not env_info["key"]:
        console.print("- Set up SUPABASE_URL, SUPABASE_KEY, and SUPABASE_SERVICE_KEY in .env file")
    
    if tables_info:
        if tables_info.get("uploads", {}).get("status") == "missing":
            console.print("- Create the 'uploads' table using the SQL provided above")
        if tables_info.get("document_chunks", {}).get("status") == "missing":
            console.print("- Create the 'document_chunks' table using the SQL provided above")
    
    if operations_info and any(op.get("status") != "ok" for op in operations_info.values()):
        console.print("- Check Supabase permissions for the key being used")
        console.print("- Verify that the tables have the correct structure")
    
    # Overall status
    if (env_status == "✅ OK" and tables_status == "✅ OK" and operations_status == "✅ OK"):
        console.print("\n[bold green]🎉 Supabase integration is working correctly![/bold green]")
    elif (env_status == "✅ OK" and (tables_status == "✅ OK" or tables_status == "⚠️ PARTIAL")):
        console.print("\n[bold yellow]⚠️ Supabase integration is partially working, see recommendations above.[/bold yellow]")
    else:
        console.print("\n[bold red]❌ Supabase integration is not working correctly. Follow the recommendations above.[/bold red]")

def run_diagnostics():
    """Run all diagnostic tests"""
    console.print("[bold]===== Supabase Integration Diagnostic Tool =====[/bold]")
    console.print("Running tests, please wait...\n")
    
    try:
        # Check environment variables
        env_info = check_env_vars()
        
        # Test connection
        supabase = test_basic_connection(env_info["url"], env_info["key"])
        
        # Test tables if connection was successful
        tables_info = test_tables(supabase) if supabase else None
        
        # Test data operations if connection was successful
        operations_info = test_data_operations(supabase) if supabase else None
        
        # Test performance if connection was successful
        performance_info = performance_test(supabase) if supabase else None
        
        # Generate report
        generate_report(env_info, tables_info, operations_info, performance_info)
        
    except Exception as e:
        console.print(f"[bold red]Error running diagnostics: {e}[/bold red]")
        console.print_exception()

if __name__ == "__main__":
    run_diagnostics() 