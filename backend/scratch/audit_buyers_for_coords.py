import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.buyer import Buyer

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Buyer).order_by(Buyer.business_name.asc(), Buyer.id.asc()))
        buyers = res.scalars().all()
        print(f"Total buyers found in PostgreSQL: {len(buyers)}")
        records = []
        for i, b in enumerate(buyers, start=1):
            records.append({
                "num": i,
                "id": str(b.id),
                "business_name": b.business_name,
                "buyer_type": b.buyer_type,
                "district": b.district,
                "state": b.state,
                "address_summary": b.address_summary,
                "contact_person": b.contact_person,
                "verification_status": b.verification_status,
                "verification_notes": b.verification_notes,
                "latitude": float(b.latitude) if b.latitude is not None else None,
                "longitude": float(b.longitude) if b.longitude is not None else None,
                "coordinate_source": b.coordinate_source,
            })
        print(json.dumps(records, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
