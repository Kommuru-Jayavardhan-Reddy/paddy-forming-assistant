import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text("DELETE FROM market_prices WHERE id IN (657, 658, 659, 660, 661)"))
        await s.commit()
        print(f"Deleted rows: {res.rowcount}")

if __name__ == "__main__":
    asyncio.run(main())
