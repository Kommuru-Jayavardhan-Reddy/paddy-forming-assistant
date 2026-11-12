import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import select, text
from app.db.session import AsyncSessionLocal
from app.db.models.market import MarketPrice

async def main():
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text("SELECT id, market_name, commodity, variety, created_at FROM market_prices WHERE id IN (657, 658, 659, 660, 661)"))).all()
        for r in rows:
            print(r)

if __name__ == "__main__":
    asyncio.run(main())
