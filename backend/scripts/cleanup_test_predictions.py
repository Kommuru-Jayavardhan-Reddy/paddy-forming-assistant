"""
Paddy Farming Assistant - Test Prediction Records Cleanup Utility
Safely removes only specified test prediction IDs from the database without touching genuine data.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text


async def cleanup_ids(ids_to_clean):
    if not ids_to_clean:
        print("No IDs provided to clean up.")
        return

    async with AsyncSessionLocal() as session:
        deleted_count = 0
        for pid in ids_to_clean:
            res = await session.execute(
                text("DELETE FROM prediction_history WHERE id = :id"),
                {"id": pid}
            )
            deleted_count += res.rowcount

        await session.commit()
        print(f"Successfully deleted {deleted_count} test prediction record(s).")

        res = await session.execute(text("SELECT count(*) FROM prediction_history"))
        print(f"Verified current prediction_history count: {res.scalar()}")


if __name__ == "__main__":
    target_ids = sys.argv[1:]
    asyncio.run(cleanup_ids(target_ids))
