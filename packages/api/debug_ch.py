import asyncio
import os
import sys

# Ensure API is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from api.db_clickhouse import get_clickhouse

async def debug_ch():
    ch_generator = get_clickhouse()
    ch = await ch_generator.__anext__()
    
    print("--- Databases ---")
    dbs = await ch.execute("SHOW DATABASES")
    print(dbs)
    
    print("\n--- Tables in default ---")
    tables = await ch.execute("SHOW TABLES FROM default")
    print(tables)
    
    print("\n--- Project Counts ---")
    counts = await ch.execute("SELECT project_id, count() as c FROM spans GROUP BY project_id")
    print(counts)

if __name__ == "__main__":
    asyncio.run(debug_ch())
