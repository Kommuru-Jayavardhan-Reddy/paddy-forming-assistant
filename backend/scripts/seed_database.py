"""
Paddy Farming Assistant - Controlled Database Seeding (STEP 11F.7)
Safely seeds authentic field metadata and Sentinel-2 satellite observations
into PostgreSQL using SQLAlchemy ORM and Alembic-migrated schema.

Supports:
  python scripts/seed_database.py --dry-run   (Inspect, validate, and report with 0 DB writes)
  python scripts/seed_database.py --apply     (Execute safe, idempotent transactional seeding)
"""

import sys
import argparse
import asyncio
import csv
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
import uuid

# Adjust path to import backend modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app import config
from app.db.session import AsyncSessionLocal, check_db_connectivity, close_db_engine
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation


async def load_and_validate_sources() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Reads and validates source CSV files:
    - Master field embedding mapping (58 fields)
    - Raw Sentinel-2 acquisition metadata (cloud coverage, image IDs)
    - Sentinel-2 regularized 10-timestep time-series (580 observations)
    """
    stats = {
        "fields_read": 0,
        "fields_valid": 0,
        "fields_invalid": 0,
        "observations_read": 0,
        "observations_valid": 0,
        "observations_invalid": 0,
        "raw_acquisitions_loaded": 0,
        "validation_errors": [],
    }

    # 1. Master Field Mapping
    master_csv = config.FIELD_MASTER_MAPPING_PATH
    if not master_csv.exists():
        raise FileNotFoundError(f"Authoritative field mapping not found at: {master_csv}")

    fields_data: List[Dict[str, Any]] = []
    seen_field_ids: Set[str] = set()

    with open(master_csv, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            stats["fields_read"] += 1
            fid = row.get("field_id", "").strip()
            cid = row.get("clean_field_id", "").strip()
            lat_str = row.get("latitude", "").strip()
            lon_str = row.get("longitude", "").strip()

            if not fid:
                stats["fields_invalid"] += 1
                stats["validation_errors"].append(f"Row {row_num}: missing field_id")
                continue

            if fid in seen_field_ids:
                stats["fields_invalid"] += 1
                stats["validation_errors"].append(f"Row {row_num}: duplicate field_id '{fid}'")
                continue
            seen_field_ids.add(fid)

            try:
                lat = float(lat_str)
                lon = float(lon_str)
                if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                    raise ValueError(f"Coordinates out of bounds: ({lat}, {lon})")
            except Exception as e:
                stats["fields_invalid"] += 1
                stats["validation_errors"].append(f"Row {row_num} ({fid}): invalid coordinates: {e}")
                continue

            fields_data.append({
                "external_field_id": fid,
                "clean_field_id": cid or None,
                "field_name": f"Paddy Field {fid.replace('FIELD_', '')}",
                "latitude": Decimal(str(round(lat, 6))),
                "longitude": Decimal(str(round(lon, 6))),
                "sentinel2_image_count": int(row.get("sentinel2_image_count", 0)),
                "sequence_index": int(row.get("sequence_index", -1)),
            })
            stats["fields_valid"] += 1

    # 2. Raw Acquisitions (for cloud cover & image ID lookup)
    raw_csv = config.BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 5" / "text_and_csv_files_5" / "sentinel2_timeseries_raw.csv"
    raw_metadata: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if raw_csv.exists():
        with open(raw_csv, mode="r", encoding="utf-8", errors="replace") as f:
            for row in csv.DictReader(f):
                stats["raw_acquisitions_loaded"] += 1
                key = (row.get("field_id", "").strip(), row.get("date", "").strip())
                raw_metadata[key] = {
                    "cloud_percentage": row.get("cloud_percentage"),
                    "image_id": row.get("image_id"),
                }

    # 3. Sentinel-2 Regularized Timeseries (580 observations)
    ts_csv = config.SENTINEL2_TIMESERIES_CSV_PATH
    if not ts_csv.exists():
        raise FileNotFoundError(f"Authoritative satellite timeseries not found at: {ts_csv}")

    obs_data: List[Dict[str, Any]] = []
    seen_obs_keys: Set[Tuple[str, date, str]] = set()

    with open(ts_csv, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            stats["observations_read"] += 1
            fid = row.get("field_id", "").strip()
            step_str = row.get("time_step", "").strip()
            date_str = row.get("date", "").strip()
            ndvi_str = row.get("NDVI", "").strip()
            ndre_str = row.get("NDRE", "").strip()
            gndvi_str = row.get("GNDVI", "").strip()

            if fid not in seen_field_ids:
                stats["observations_invalid"] += 1
                stats["validation_errors"].append(f"TS Row {row_num}: unknown field_id '{fid}'")
                continue

            try:
                obs_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception as e:
                stats["observations_invalid"] += 1
                stats["validation_errors"].append(f"TS Row {row_num} ({fid}): invalid date '{date_str}': {e}")
                continue

            try:
                time_step = int(step_str)
                if not (1 <= time_step <= 10):
                    raise ValueError(f"time_step {time_step} not in [1, 10]")
            except Exception as e:
                stats["observations_invalid"] += 1
                stats["validation_errors"].append(f"TS Row {row_num} ({fid}): invalid time_step '{step_str}': {e}")
                continue

            try:
                ndvi = float(ndvi_str)
                ndre = float(ndre_str)
                gndvi = float(gndvi_str)
                if not (-1.0 <= ndvi <= 1.0) or not (-1.0 <= ndre <= 1.0) or not (-1.0 <= gndvi <= 1.0):
                    raise ValueError(f"Indices out of [-1, 1] range: ({ndvi}, {ndre}, {gndvi})")
            except Exception as e:
                stats["observations_invalid"] += 1
                stats["validation_errors"].append(f"TS Row {row_num} ({fid}): invalid index values: {e}")
                continue

            obs_key = (fid, obs_date, "Sentinel-2 L2A")
            if obs_key in seen_obs_keys:
                stats["observations_invalid"] += 1
                stats["validation_errors"].append(f"TS Row {row_num} ({fid}): duplicate observation date '{obs_date}'")
                continue
            seen_obs_keys.add(obs_key)

            # Check if this date was an exact raw acquisition or interpolated
            raw_info = raw_metadata.get((fid, date_str))
            is_interp = raw_info is None
            cloud_pct = None
            raw_meta = {
                "source_file": "sentinel2_timeseries.csv",
                "time_step": time_step,
                "regularization": "linear_temporal_interpolation_step5g",
            }
            if raw_info:
                try:
                    cloud_pct = Decimal(str(round(float(raw_info["cloud_percentage"]), 2)))
                except Exception:
                    cloud_pct = None
                raw_meta["scene_image_id"] = raw_info.get("image_id")

            obs_data.append({
                "external_field_id": fid,
                "time_step": time_step,
                "observation_date": obs_date,
                "ndvi": Decimal(str(round(ndvi, 6))),
                "ndre": Decimal(str(round(ndre, 6))),
                "gndvi": Decimal(str(round(gndvi, 6))),
                "cloud_coverage_pct": cloud_pct,
                "is_interpolated": is_interp,
                "data_source": "Sentinel-2 L2A",
                "raw_metadata": raw_meta,
            })
            stats["observations_valid"] += 1

    return fields_data, obs_data, stats


async def run_seeding(apply_changes: bool = False):
    print("=" * 70)
    mode_str = "APPLY (TRANSACTIONAL WRITE)" if apply_changes else "DRY-RUN (VALIDATION & AUDIT ONLY, ZERO WRITES)"
    print(f"STEP 11F.7 — DATABASE DATA SEEDING: {mode_str}")
    print("=" * 70)

    # 1. Verify DB Connection
    db_health = await check_db_connectivity()
    if db_health.get("status") != "healthy" and not db_health.get("connected"):
        print(f"[FAIL] Database connection check failed: {db_health}")
        return False
    print(f"[OK] Connected to PostgreSQL: database='{db_health.get('database')}', user='{db_health.get('user')}', latency={db_health.get('latency_ms')}ms")

    # 2. Source Loading & Validation
    print("\n[Phase 1] Discovering and validating source data files...")
    fields_data, obs_data, stats = await load_and_validate_sources()

    print(f"  Fields Read:        {stats['fields_read']}")
    print(f"  Fields Valid:       {stats['fields_valid']}")
    print(f"  Fields Invalid:     {stats['fields_invalid']}")
    print(f"  Observations Read:  {stats['observations_read']}")
    print(f"  Observations Valid: {stats['observations_valid']}")
    print(f"  Observations Invalid: {stats['observations_invalid']}")
    print(f"  Raw Scenes Indexed: {stats['raw_acquisitions_loaded']}")

    if stats["validation_errors"]:
        print(f"\n[WARNING] Found {len(stats['validation_errors'])} validation issues:")
        for err in stats["validation_errors"][:10]:
            print(f"    - {err}")
        if not apply_changes:
            print("  (Review validation issues before applying)")

    try:
        # 3. Inspect Current Database State
        print("\n[Phase 2] Inspecting current database state...")
        async with AsyncSessionLocal() as session:
            # Check existing fields
            res_fields = await session.execute(select(Field.id, Field.external_field_id))
            existing_fields_map: Dict[str, uuid.UUID] = {row[1]: row[0] for row in res_fields.all()}
            
            # Check existing observations count
            res_obs_count = await session.execute(select(func.count(SatelliteObservation.id)))
            existing_obs_count = res_obs_count.scalar() or 0

        print(f"  Existing fields in DB:       {len(existing_fields_map)}")
        print(f"  Existing observations in DB: {existing_obs_count}")

        # 4. Calculate proposed operations
        fields_to_insert = [f for f in fields_data if f["external_field_id"] not in existing_fields_map]
        fields_to_skip = [f for f in fields_data if f["external_field_id"] in existing_fields_map]

        print(f"\n[Phase 3] Action Plan:")
        print(f"  Fields to INSERT:  {len(fields_to_insert)}")
        print(f"  Fields to SKIP:    {len(fields_to_skip)}")
        print(f"  Observations plan: {len(obs_data)} candidate records mapped to 58 field IDs")

        if not apply_changes:
            print("\n" + "=" * 70)
            print("DRY-RUN COMPLETE: ZERO WRITES PERFORMED.")
            print("Run with '--apply' to execute transactional seeding.")
            print("=" * 70)
            return True

        # 5. Execute Transactional Seeding
        print("\n[Phase 4] Executing Transactional Seeding...")
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # A. Insert Fields
                inserted_field_entities: Dict[str, Field] = {}
                for f_dict in fields_to_insert:
                    field_obj = Field(
                        external_field_id=f_dict["external_field_id"],
                        clean_field_id=f_dict["clean_field_id"],
                        field_name=f_dict["field_name"],
                        latitude=f_dict["latitude"],
                        longitude=f_dict["longitude"],
                        is_active=True,
                    )
                    session.add(field_obj)
                    inserted_field_entities[f_dict["external_field_id"]] = field_obj

                # Flush to generate UUIDs
                if inserted_field_entities:
                    await session.flush()
                    for fid, entity in inserted_field_entities.items():
                        existing_fields_map[fid] = entity.id

                print(f"  [OK] Successfully persisted {len(inserted_field_entities)} new fields.")

                # B. Query existing observation signatures to guarantee idempotency
                res_obs_sig = await session.execute(
                    select(SatelliteObservation.field_id, SatelliteObservation.observation_date, SatelliteObservation.data_source)
                )
                existing_obs_sigs = set(res_obs_sig.all())

                # C. Insert Satellite Observations
                obs_to_insert = []
                obs_skipped = 0

                for o_dict in obs_data:
                    parent_field_id = existing_fields_map.get(o_dict["external_field_id"])
                    if not parent_field_id:
                        raise ValueError(f"Could not resolve UUID for field {o_dict['external_field_id']}")

                    sig = (parent_field_id, o_dict["observation_date"], o_dict["data_source"])
                    if sig in existing_obs_sigs:
                        obs_skipped += 1
                        continue

                    obs_obj = SatelliteObservation(
                        field_id=parent_field_id,
                        time_step=o_dict["time_step"],
                        observation_date=o_dict["observation_date"],
                        ndvi=o_dict["ndvi"],
                        ndre=o_dict["ndre"],
                        gndvi=o_dict["gndvi"],
                        cloud_coverage_pct=o_dict["cloud_coverage_pct"],
                        is_interpolated=o_dict["is_interpolated"],
                        data_source=o_dict["data_source"],
                        raw_metadata=o_dict["raw_metadata"],
                    )
                    session.add(obs_obj)
                    existing_obs_sigs.add(sig)
                    obs_to_insert.append(obs_obj)

                if obs_to_insert:
                    await session.flush()
                print(f"  [OK] Successfully persisted {len(obs_to_insert)} satellite observations (skipped {obs_skipped} existing).")

        print("\n[Phase 5] Post-Seed Immediate Catalog Audit:")
        async with AsyncSessionLocal() as session:
            f_count = (await session.execute(select(func.count(Field.id)))).scalar()
            o_count = (await session.execute(select(func.count(SatelliteObservation.id)))).scalar()
            
            # Verify min/max bounds in DB
            min_max_indices = (await session.execute(
                select(
                    func.min(SatelliteObservation.ndvi),
                    func.max(SatelliteObservation.ndvi),
                    func.min(SatelliteObservation.ndre),
                    func.max(SatelliteObservation.ndre),
                    func.min(SatelliteObservation.gndvi),
                    func.max(SatelliteObservation.gndvi),
                )
            )).first()

        print(f"  Total fields in database:              {f_count}")
        print(f"  Total observations in database:        {o_count}")
        print(f"  NDVI Range in database:                [{min_max_indices[0]}, {min_max_indices[1]}]")
        print(f"  NDRE Range in database:                [{min_max_indices[2]}, {min_max_indices[3]}]")
        print(f"  GNDVI Range in database:               [{min_max_indices[4]}, {min_max_indices[5]}]")

        print("\n" + "=" * 70)
        print("CONTROLLED SEEDING COMPLETED SUCCESSFULLY (PASS)")
        print("=" * 70)
        return True
    finally:
        await close_db_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paddy Farming Assistant Database Seeder")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--dry-run", action="store_true", help="Perform validation and dry run without writing to DB")
    group.add_argument("--apply", action="store_true", help="Apply seeding changes to PostgreSQL database")

    args = parser.parse_args()
    apply = args.apply

    success = asyncio.run(run_seeding(apply_changes=apply))
    if not success:
        sys.exit(1)
