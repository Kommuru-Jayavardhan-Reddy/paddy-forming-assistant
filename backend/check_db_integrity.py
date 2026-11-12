import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
import json

async def check():
    async with AsyncSessionLocal() as session:
        tables = [
            'buyers',
            'market_prices',
            'fields',
            'satellite_observations',
            'prediction_history',
            'weather_records',
            'reports'
        ]
        counts = {}
        for t in tables:
            res = await session.execute(text(f'SELECT count(*) FROM {t}'))
            counts[t] = res.scalar()
        print('DB_COUNTS:' + json.dumps(counts))

if __name__ == '__main__':
    asyncio.run(check())
