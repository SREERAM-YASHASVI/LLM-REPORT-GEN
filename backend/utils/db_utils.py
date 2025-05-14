import os
from dotenv import load_dotenv
load_dotenv('/Users/sreeramyashasviv/projects/MISC./AGENTIC-PLAYGROUND/.env')
import asyncpg

_SUPABASE_DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL")

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        if not _SUPABASE_DATABASE_URL:
            raise RuntimeError("SUPABASE_DATABASE_URL is not set in environment variables.")
        _pool = await asyncpg.create_pool(_SUPABASE_DATABASE_URL)
    return _pool

async def test_connection():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1;")
        return result 