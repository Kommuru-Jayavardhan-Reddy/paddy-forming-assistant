"""
Paddy Farming Assistant - Buyer GPS Coordinates Safe Importer (STEP 11H.7)
Provides a safe, validated, idempotent import pipeline for authentic buyer GPS coordinates.

Strict Integrity Rules:
1. Never fabricates or estimates coordinates. Centroids and approximations are strictly forbidden.
2. Coordinate completeness: Requires both latitude and longitude together. Rejects partial pairs.
3. Coordinate bounds: Enforces WGS-84 ranges [-90.0, 90.0] and [-180.0, 180.0].
4. Provenance enforcement: Requires coordinate_source, source_reference, and evidence_notes.
5. Only rows with coordinate_verification_status == 'accepted' can update database coordinates.
6. Identity matching: Strict match by business_name and district against the buyers table.
7. Preserves existing records: Does NOT delete any buyer, does NOT change buyer verification_status
   (pending buyers remain pending), and does NOT touch other tables.
8. Supports --dry-run for pre-commit verification.
"""

import sys
import os
import csv
import argparse
import asyncio
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func, text
from app.db.session import AsyncSessionLocal
from app.db.models.buyer import Buyer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("buyer_coordinate_importer")

REQUIRED_CSV_COLUMNS = [
    "business_name",
    "district",
    "latitude",
    "longitude",
    "coordinate_source",
    "source_reference",
    "evidence_notes",
    "coordinate_verification_status",
]

ALLOWED_COORDINATE_STATUSES = {"accepted", "rejected", "unresolved", "pending"}


def parse_and_validate_coordinate_row(row: Dict[str, str], line_num: int) -> Dict[str, Any]:
    """
    Validates a single row from the buyer coordinate CSV.
    Returns cleaned row dictionary or raises ValueError if validation fails.
    """
    # 1. Check required columns present
    for col in REQUIRED_CSV_COLUMNS:
        if col not in row:
            raise ValueError(f"Line {line_num}: Missing required CSV column '{col}'")

    b_name = (row.get("business_name") or "").strip()
    if not b_name:
        raise ValueError(f"Line {line_num}: 'business_name' cannot be blank")

    district = (row.get("district") or "").strip()
    if not district:
        raise ValueError(f"Line {line_num}: 'district' cannot be blank")

    status = (row.get("coordinate_verification_status") or "").strip().lower()
    if status not in ALLOWED_COORDINATE_STATUSES:
        raise ValueError(
            f"Line {line_num}: Invalid coordinate_verification_status '{status}'. "
            f"Must be one of {sorted(ALLOWED_COORDINATE_STATUSES)}"
        )

    raw_lat = (row.get("latitude") or "").strip()
    raw_lon = (row.get("longitude") or "").strip()

    has_lat = bool(raw_lat)
    has_lon = bool(raw_lon)

    # 2. Enforce pair completeness: both or neither
    if has_lat != has_lon:
        raise ValueError(
            f"Line {line_num}: Partial coordinate pair for '{b_name}'. "
            f"Both latitude and longitude must be provided together, or both must be empty."
        )

    lat: Optional[Decimal] = None
    lon: Optional[Decimal] = None

    if has_lat and has_lon:
        # 3. Numeric parsing and range validation
        try:
            lat = Decimal(raw_lat)
        except (InvalidOperation, TypeError):
            raise ValueError(f"Line {line_num}: Invalid latitude '{raw_lat}' for '{b_name}'")

        try:
            lon = Decimal(raw_lon)
        except (InvalidOperation, TypeError):
            raise ValueError(f"Line {line_num}: Invalid longitude '{raw_lon}' for '{b_name}'")

        if not (Decimal("-90.0") <= lat <= Decimal("90.0")):
            raise ValueError(f"Line {line_num}: Latitude out of range [-90, +90]: {lat}")

        if not (Decimal("-180.0") <= lon <= Decimal("180.0")):
            raise ValueError(f"Line {line_num}: Longitude out of range [-180, +180]: {lon}")

        # 4. Non-empty coordinates require status 'accepted'
        if status != "accepted":
            raise ValueError(
                f"Line {line_num}: Coordinates provided for '{b_name}', but status is '{status}'. "
                f"Only 'accepted' coordinates can be ingested into production."
            )

        # 5. Provenance validation
        coord_source = (row.get("coordinate_source") or "").strip()
        if len(coord_source) < 3:
            raise ValueError(
                f"Line {line_num}: 'coordinate_source' required when coordinates are provided (got '{coord_source}')"
            )

        source_ref = (row.get("source_reference") or "").strip()
        if len(source_ref) < 3:
            raise ValueError(
                f"Line {line_num}: 'source_reference' required when coordinates are provided (got '{source_ref}')"
            )

        evidence = (row.get("evidence_notes") or "").strip()
        if len(evidence) < 5:
            raise ValueError(
                f"Line {line_num}: Detailed 'evidence_notes' required when coordinates are provided"
            )
    else:
        # Both are empty - coordinates remain None
        coord_source = (row.get("coordinate_source") or "").strip() or None
        source_ref = (row.get("source_reference") or "").strip() or None
        evidence = (row.get("evidence_notes") or "").strip() or None

    return {
        "line_num": line_num,
        "business_name": b_name,
        "district": district,
        "latitude": lat,
        "longitude": lon,
        "coordinate_source": coord_source,
        "source_reference": source_ref,
        "evidence_notes": evidence,
        "coordinate_verification_status": status,
        "has_coordinates": bool(lat is not None and lon is not None),
    }


async def import_buyer_coordinates(
    csv_path: Path,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Executes coordinate validation and ingestion.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Coordinate CSV file not found: {csv_path}")

    # Read and parse CSV
    validated_rows: List[Dict[str, Any]] = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            # Skip completely empty rows
            if not any(row.values()):
                continue
            v_row = parse_and_validate_coordinate_row(row, line_num=i)
            validated_rows.append(v_row)

    logger.info("Parsed and validated %d CSV rows from %s", len(validated_rows), csv_path.name)

    stats = {
        "total_csv_rows": len(validated_rows),
        "rows_with_coordinates": sum(1 for r in validated_rows if r["has_coordinates"]),
        "rows_unresolved": sum(1 for r in validated_rows if r["coordinate_verification_status"] == "unresolved"),
        "rows_rejected": sum(1 for r in validated_rows if r["coordinate_verification_status"] == "rejected"),
        "rows_pending": sum(1 for r in validated_rows if r["coordinate_verification_status"] == "pending"),
        "matched_buyers": 0,
        "unmatched_buyers": 0,
        "updated_coordinates": 0,
        "preserved_null": 0,
        "dry_run": dry_run,
        "errors": [],
    }

    async with AsyncSessionLocal() as session:
        try:
            for item in validated_rows:
                # Identity matching: match against buyers by business_name and district (case-insensitive)
                stmt = select(Buyer).where(
                    func.lower(Buyer.business_name) == item["business_name"].lower(),
                    func.lower(Buyer.district) == item["district"].lower(),
                )
                res = await session.execute(stmt)
                buyers = res.scalars().all()

                if len(buyers) == 0:
                    err_msg = f"No database buyer match for '{item['business_name']}' in district '{item['district']}'"
                    stats["errors"].append(err_msg)
                    stats["unmatched_buyers"] += 1
                    logger.warning("Unmatched: %s", err_msg)
                    continue

                if len(buyers) > 1:
                    err_msg = f"Ambiguous database match: {len(buyers)} buyers match '{item['business_name']}' in district '{item['district']}'"
                    stats["errors"].append(err_msg)
                    logger.error("Ambiguous: %s", err_msg)
                    continue

                buyer = buyers[0]
                stats["matched_buyers"] += 1

                if item["has_coordinates"]:
                    # Update coordinates and source provenance
                    buyer.latitude = item["latitude"]
                    buyer.longitude = item["longitude"]
                    buyer.coordinate_source = item["coordinate_source"]
                    stats["updated_coordinates"] += 1
                    logger.info(
                        "Updating buyer '%s' (ID %s) with coordinates (%s, %s) from %s",
                        buyer.business_name,
                        buyer.id,
                        buyer.latitude,
                        buyer.longitude,
                        buyer.coordinate_source,
                    )
                else:
                    # No coordinates provided: keep NULL, do NOT invent coordinates
                    stats["preserved_null"] += 1
                    logger.debug(
                        "Buyer '%s' (ID %s) remains with NULL coordinates (status: %s)",
                        buyer.business_name,
                        buyer.id,
                        item["coordinate_verification_status"],
                    )

            if stats["errors"]:
                logger.error("Encountered %d errors during identity matching. Rolling back.", len(stats["errors"]))
                await session.rollback()
                stats["committed"] = False
                return stats

            if dry_run:
                logger.info("[DRY RUN] All validations and identity matches succeeded. Rolling back transaction.")
                await session.rollback()
                stats["committed"] = False
            else:
                logger.info("Committing coordinate changes to database.")
                await session.commit()
                stats["committed"] = True

        except Exception as e:
            await session.rollback()
            logger.error("Import failed with exception: %s", e, exc_info=True)
            stats["errors"].append(str(e))
            stats["committed"] = False
            raise

    return stats


def main():
    parser = argparse.ArgumentParser(description="Safely import verified buyer GPS coordinates into PostgreSQL.")
    parser.add_argument(
        "--csv",
        type=str,
        default=str(BACKEND_DIR / "data" / "curated_buyer_coordinates.csv"),
        help="Path to buyer coordinates CSV file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Perform validation and matching without committing changes",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes to database (overrides default dry-run)",
    )

    args = parser.parse_args()
    csv_path = Path(args.csv)

    is_dry_run = True
    if args.apply:
        is_dry_run = False
    elif not args.dry_run:
        # Default safety: dry-run unless --apply is explicitly specified
        print("Notice: Running in --dry-run mode by default for safety. Pass --apply to commit.")
        is_dry_run = True

    print("================================================================================")
    print(" PADDY FARMING ASSISTANT — SAFE BUYER GPS COORDINATE IMPORTER")
    print(f" CSV Target: {csv_path}")
    print(f" Execution Mode: {'DRY RUN (no DB modifications)' if is_dry_run else 'APPLY (live commit)'}")
    print("================================================================================")

    try:
        results = asyncio.run(import_buyer_coordinates(csv_path, dry_run=is_dry_run))
        print("\n--- IMPORT SUMMARY RESULTS ---")
        print(f"  Total CSV Rows Processed:       {results['total_csv_rows']}")
        print(f"  Matched Production Buyers:      {results['matched_buyers']}")
        print(f"  Unmatched Buyers:               {results['unmatched_buyers']}")
        print(f"  Rows with Verified Coordinates: {results['rows_with_coordinates']}")
        print(f"  Rows Unresolved (Address only): {results['rows_unresolved']}")
        print(f"  Rows Rejected (Approximation):  {results['rows_rejected']}")
        print(f"  Updated Buyer Coordinates:      {results['updated_coordinates']}")
        print(f"  Preserved NULL Coordinates:     {results['preserved_null']}")
        print(f"  Committed to PostgreSQL:        {results['committed']}")
        print(f"  Validation Errors:              {len(results['errors'])}")
        print("================================================================================")
        if results["errors"]:
            print("Errors encountered:")
            for err in results["errors"]:
                print(f"  - {err}")
            sys.exit(1)
        sys.exit(0)
    except Exception as exc:
        print(f"\nFATAL ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
