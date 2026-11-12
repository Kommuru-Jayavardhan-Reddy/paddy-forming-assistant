import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def cleanup():
    async with AsyncSessionLocal() as session:
        # Delete any records added beyond the baseline seed of 98 records (id > 117)
        res = await session.execute(text("DELETE FROM weather_records WHERE id > 117"))
        await session.commit()
        print(f"DELETED_COUNT:{res.rowcount}")

if __name__ == '__main__':
    asyncio.run(cleanup())
