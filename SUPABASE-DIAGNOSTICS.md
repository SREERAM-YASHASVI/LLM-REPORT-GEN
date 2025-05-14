# Supabase Integration Diagnostics

This document explains the enhanced Supabase integration, diagnostic tools, and troubleshooting steps for the Document Query App.

## Overview

The application uses Supabase as its database backend. The integration has been enhanced with:

1. Improved error handling and detailed diagnostics
2. Connection retry logic
3. Comprehensive troubleshooting tools
4. Better error reporting in API responses

## Environment Setup

To use Supabase, you need to set the following environment variables in your `.env` file:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
```

- `SUPABASE_URL`: Your Supabase project URL (e.g., https://yourproject.supabase.co)
- `SUPABASE_KEY`: The public/anon key (for client-side operations)
- `SUPABASE_SERVICE_KEY`: The service key for admin operations (has higher privileges)

## Required Database Tables

The application requires two tables in your Supabase project:

### uploads Table

```sql
CREATE TABLE IF NOT EXISTS public.uploads (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_path TEXT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_type TEXT,
    file_size INTEGER
);
```

### document_chunks Table

```sql
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
```

## Diagnostic Tools

### Diagnostic Endpoints

The application now includes detailed diagnostic endpoints:

1. **Health Check**: `/health` - Provides basic service status information
2. **Database Diagnostics**: `/diagnostics/database` - Provides detailed information about Supabase connection, tables, and configuration

### Standalone Diagnostic Script

A dedicated diagnostic script is available to check the Supabase integration:

```bash
cd backend
python supabase_diagnostics.py
```

This script performs:

1. Environment variable checks
2. Connection tests
3. Table existence verification
4. Data operation tests (INSERT, SELECT, DELETE)
5. Performance benchmarks

The script provides clear, color-coded output and suggestions for fixing issues.

## Startup Script

The application now includes a `start.sh` script that:

1. Checks environment setup
2. Runs diagnostics before starting
3. Starts both backend and frontend servers

To use it:

```bash
./start.sh
```

## Common Issues and Solutions

### Connection Issues

1. **Cannot connect to Supabase**:
   - Verify that `SUPABASE_URL` is correct
   - Check that either `SUPABASE_KEY` or `SUPABASE_SERVICE_KEY` is set
   - Verify your internet connection
   - Check Supabase service status: https://status.supabase.com

2. **Authentication failures**:
   - Ensure your Supabase keys are valid and not expired
   - Try regenerating the keys in the Supabase dashboard

### Table Issues

1. **Tables don't exist**:
   - Run the SQL queries provided above in the Supabase SQL Editor
   - Check for typos in table names

2. **Permission denied**:
   - Ensure you're using the service key for admin operations
   - Check table permissions in Supabase dashboard

### Data Operation Issues

1. **Insert/Update failures**:
   - Check for foreign key constraints
   - Verify field names and types match the schema
   - Look for unique constraint violations

## Enhanced Error Reporting

API endpoints now provide detailed error information including:

1. Error message
2. Stack trace (in development mode)
3. Contextual information

Example error response:
```json
{
  "error": "Failed to connect to database",
  "details": [
    "Traceback (most recent call last):",
    "  File \"main.py\", line 123, in get_documents",
    "    documents = await database_service.get_all_documents()",
    "  File \"services/database_service.py\", line 245, in get_all_documents",
    "    success, result, error = self._handle_db_operation(\"get_all_documents\", _execute_query)",
    "ConnectionError: Cannot connect to host supabase.co"
  ]
}
```

## Performance Considerations

For optimal performance with Supabase:

1. Keep connection pool sizes appropriate for your workload
2. Use indexes for frequently queried columns
3. Consider using Supabase's edge functions for heavy processing
4. Monitor query performance in the Supabase dashboard

## Support and Further Information

For more information about Supabase, visit:
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase GitHub](https://github.com/supabase/supabase)
- [Supabase Community](https://github.com/supabase/supabase/discussions) 