import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import select, func, text
from app.db.session import AsyncSessionLocal
from app.db.models.market import MarketPrice

async def main():
    async with AsyncSessionLocal() as s:
        cnt = (await s.execute(select(func.count(MarketPrice.id)))).scalar()
        print(f"Total market_prices: {cnt}")
        rows = (await s.execute(text("SELECT price_date, count(*) FROM market_prices GROUP BY price_date ORDER BY price_date DESC"))).all()
        for r in rows:
            print(f"  price_date: {r[0]} -> {r[1]} records")
        # Check newly created records
        newest = (await s.execute(select(MarketPrice).order_by(MarketPrice.created_at.desc()).limit(10))).scalars().all()
        print("Newest created:")
        for n in newest:
            print(f"  {n.id}: {n.market_name} | {n.commodity} | {n.variety} | {n.price_date} | created_at={n.created_at}")

if __name__ == "__main__":
    asyncio.run(main())
