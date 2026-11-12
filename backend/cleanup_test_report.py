import sys
import asyncio
import uuid
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def cleanup_report(report_id_str):
    try:
        report_uuid = uuid.UUID(report_id_str)
    except Exception as e:
        print(f"INVALID_UUID:{e}")
        return

    async with AsyncSessionLocal() as session:
        # Only delete this specific report ID
        res = await session.execute(
            text("DELETE FROM reports WHERE id = :rid"),
            {"rid": report_uuid}
        )
        await session.commit()
        print(f"DELETED_REPORT:{report_id_str}:{res.rowcount}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(cleanup_report(sys.argv[1]))
    else:
        print("NO_REPORT_ID_PROVIDED")
