"""
Paddy Farming Assistant - Market Prices & Buyers CSV Importer (STEP 11F.10)
Provides a safe, verified, idempotent ingestion pipeline for authentic
Andhra Pradesh agricultural mandi prices and verified buyers/rice mills.

Strict Integrity Rules:
- Never fabricates data.
- Enforces database check constraints and validation rules prior to SQL execution.
- Supports dry-run mode for pre-commit verification.
- Completely idempotent using PostgreSQL ON CONFLICT handling.
- Does not modify existing fields, satellite observations, predictions, or weather records.
"""

import sys
import os
import csv
import json
import uuid
import argparse
import asyncio
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

VALID_BUYER_TYPES = {"mill", "fpo", "government_agency", "wholesaler", "trader"}
VALID_VERIFICATION_STATUSES = {"verified", "pending", "unverified"}


def validate_market_price_row(row: Dict[str, str], line_num: int) -> Dict[str, Any]:
    """Validates and casts a market_prices CSV row against schema and check constraints."""
    required = ["market_name", "district", "state", "commodity", "variety", "grade",
                "min_price", "max_price", "modal_price", "currency", "unit", "price_date", "source"]
    for col in required:
        if not row.get(col) or not row[col].strip():
            raise ValueError(f"Line {line_num}: Missing required column '{col}'")

    try:
        min_p = Decimal(row["min_price"].strip())
        max_p = Decimal(row["max_price"].strip())
        modal_p = Decimal(row["modal_price"].strip())
    except (InvalidOperation, TypeError) as e:
        raise ValueError(f"Line {line_num}: Invalid numeric price value: {e}")

    if min_p < 0:
        raise ValueError(f"Line {line_num}: min_price must be >= 0 (got {min_p})")
    if max_p < min_p:
        raise ValueError(f"Line {line_num}: max_price ({max_p}) must be >= min_price ({min_p})")
    if modal_p < min_p or modal_p > max_p:
        raise ValueError(f"Line {line_num}: modal_price ({modal_p}) must be between min_price ({min_p}) and max_price ({max_p})")

    try:
        p_date = date.fromisoformat(row["price_date"].strip())
    except ValueError:
        raise ValueError(f"Line {line_num}: Invalid price_date format. Must be YYYY-MM-DD (got '{row['price_date']}')")

    return {
        "market_name": row["market_name"].strip()[:150],
        "district": row["district"].strip()[:100],
        "state": row["state"].strip()[:100],
        "commodity": row["commodity"].strip()[:100],
        "variety": row["variety"].strip()[:100],
        "grade": row["grade"].strip()[:50],
        "min_price": min_p,
        "max_price": max_p,
        "modal_price": modal_p,
        "currency": row["currency"].strip()[:10],
        "unit": row["unit"].strip()[:30],
        "price_date": p_date,
        "source": row["source"].strip()[:100],
    }


def validate_buyer_row(row: Dict[str, str], line_num: int) -> Dict[str, Any]:
    """Validates and casts a buyers CSV row against schema and check constraints."""
    required = ["business_name", "buyer_type", "district", "state"]
    for col in required:
        if not row.get(col) or not row[col].strip():
            raise ValueError(f"Line {line_num}: Missing required column '{col}'")

    b_type = row["buyer_type"].strip().lower()
    if b_type not in VALID_BUYER_TYPES:
        raise ValueError(f"Line {line_num}: Invalid buyer_type '{b_type}'. Must be one of {sorted(VALID_BUYER_TYPES)}")

    v_status = row.get("verification_status", "pending").strip().lower() or "pending"
    if v_status not in VALID_VERIFICATION_STATUSES:
        raise ValueError(f"Line {line_num}: Invalid verification_status '{v_status}'. Must be one of {sorted(VALID_VERIFICATION_STATUSES)}")

    pref_varieties = []
    if row.get("preferred_varieties") and row["preferred_varieties"].strip():
        raw_val = row["preferred_varieties"].strip()
        try:
            parsed = json.loads(raw_val)
            if isinstance(parsed, list):
                pref_varieties = [str(x).strip() for x in parsed if str(x).strip()]
            else:
                pref_varieties = [str(parsed).strip()]
        except json.JSONDecodeError:
            # Fallback to comma-separated list
            pref_varieties = [v.strip() for v in raw_val.split(",") if v.strip()]

    min_proc = None
    if row.get("min_procurement_quintals") and row["min_procurement_quintals"].strip():
        try:
            min_proc = Decimal(row["min_procurement_quintals"].strip())
            if min_proc < 0:
                raise ValueError(f"Line {line_num}: min_procurement_quintals must be >= 0")
        except (InvalidOperation, TypeError):
            raise ValueError(f"Line {line_num}: Invalid min_procurement_quintals: '{row['min_procurement_quintals']}'")

    is_active = True
    if row.get("is_active") and row["is_active"].strip().lower() in {"false", "0", "no"}:
        is_active = False

    lat = None
    if row.get("latitude") and row["latitude"].strip():
        try:
            lat = Decimal(row["latitude"].strip())
            if not (-90 <= lat <= 90):
                raise ValueError(f"Line {line_num}: latitude must be between -90 and 90 (got {lat})")
        except (InvalidOperation, TypeError):
            raise ValueError(f"Line {line_num}: Invalid latitude: '{row['latitude']}'")

    lon = None
    if row.get("longitude") and row["longitude"].strip():
        try:
            lon = Decimal(row["longitude"].strip())
            if not (-180 <= lon <= 180):
                raise ValueError(f"Line {line_num}: longitude must be between -180 and 180 (got {lon})")
        except (InvalidOperation, TypeError):
            raise ValueError(f"Line {line_num}: Invalid longitude: '{row['longitude']}'")

    coord_src = (row.get("coordinate_source") or "").strip()[:100] or None

    return {
        "business_name": row["business_name"].strip()[:200],
        "buyer_type": b_type,
        "district": row["district"].strip()[:100],
        "state": row["state"].strip()[:100],
        "address_summary": (row.get("address_summary") or "").strip()[:255] or None,
        "contact_person": (row.get("contact_person") or "").strip()[:100] or None,
        "contact_phone": (row.get("contact_phone") or "").strip()[:20] or None,
        "contact_email": (row.get("contact_email") or "").strip()[:150] or None,
        "preferred_varieties": pref_varieties,
        "min_procurement_quintals": min_proc,
        "verification_status": v_status,
        "verification_notes": (row.get("verification_notes") or "").strip() or None,
        "is_active": is_active,
        "latitude": lat,
        "longitude": lon,
        "coordinate_source": coord_src,
    }


async def import_market_prices(csv_path: Path, dry_run: bool = False) -> int:
    """Reads and imports market_prices CSV idempotently."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    valid_rows: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader((line for line in f if not line.strip().startswith("#")))
        for line_num, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue
            cleaned = validate_market_price_row(row, line_num)
            valid_rows.append(cleaned)

    logger.info(f"Parsed and validated {len(valid_rows)} market price records from {csv_path.name}")
    if dry_run or not valid_rows:
        logger.info(f"[DRY-RUN] No records written to database. Validation: PASS")
        return len(valid_rows)

    inserted_count = 0
    async with AsyncSessionLocal() as session:
        for item in valid_rows:
            stmt = pg_insert(MarketPrice).values(**item)
            stmt = stmt.on_conflict_do_update(
                index_elements=["market_name", "commodity", "variety", "price_date"],
                set_={
                    "min_price": item["min_price"],
                    "max_price": item["max_price"],
                    "modal_price": item["modal_price"],
                    "grade": item["grade"],
                    "unit": item["unit"],
                    "currency": item["currency"],
                    "source": item["source"],
                    "retrieval_timestamp": datetime.now(timezone.utc),
                }
            )
            await session.execute(stmt)
            inserted_count += 1
        await session.commit()

    logger.info(f"Successfully upserted {inserted_count} market price records into database.")
    return inserted_count


async def import_buyers(csv_path: Path, dry_run: bool = False) -> int:
    """Reads and imports buyers CSV idempotently."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    valid_rows: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader((line for line in f if not line.strip().startswith("#")))
        for line_num, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue
            cleaned = validate_buyer_row(row, line_num)
            valid_rows.append(cleaned)

    logger.info(f"Parsed and validated {len(valid_rows)} buyer records from {csv_path.name}")
    if dry_run or not valid_rows:
        logger.info(f"[DRY-RUN] No records written to database. Validation: PASS")
        return len(valid_rows)

    inserted_count = 0
    async with AsyncSessionLocal() as session:
        for item in valid_rows:
            # Check for existing business_name + district match to avoid duplicate entries
            existing = await session.execute(
                select(Buyer).where(
                    func.lower(Buyer.business_name) == item["business_name"].lower(),
                    func.lower(Buyer.district) == item["district"].lower(),
                )
            )
            b = existing.scalar_one_or_none()
            if b:
                # Update existing
                for k, v in item.items():
                    setattr(b, k, v)
            else:
                session.add(Buyer(**item))
            inserted_count += 1
        await session.commit()

    logger.info(f"Successfully upserted {inserted_count} buyer records into database.")
    return inserted_count


async def main():
    parser = argparse.ArgumentParser(description="Import authentic agricultural market prices or buyers from CSV")
    parser.add_argument("--type", choices=["market", "buyer"], required=True, help="Entity type to import")
    parser.add_argument("--csv-path", type=str, required=True, help="Path to CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV without writing to PostgreSQL")
    args = parser.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if args.type == "market":
        count = await import_market_prices(csv_path, dry_run=args.dry_run)
    else:
        count = await import_buyers(csv_path, dry_run=args.dry_run)

    print(f"COMPLETE: Processed {count} records (dry_run={args.dry_run})")


if __name__ == "__main__":
    asyncio.run(main())
