import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("c:/paddy project/backend/.env")

async def fix_staging_privileges():
    pwd = os.getenv("POSTGRES_PASSWORD", "postgres")
    conn = await asyncpg.connect(database="paddy_farming_staging", user="postgres", password=pwd, host="127.0.0.1", port=5432)
    
    await conn.execute("ALTER DATABASE paddy_farming_staging OWNER TO paddy_app;")
    await conn.execute("GRANT ALL ON SCHEMA public TO paddy_app;")
    await conn.execute("ALTER SCHEMA public OWNER TO paddy_app;")
    await conn.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO paddy_app;")
    await conn.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO paddy_app;")
    print("Staging database and public schema ownership set to paddy_app successfully.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_staging_privileges())

