"""
Paddy Farming Assistant - Phase I: Final Database & Artifact Verification Script
Verifies:
1. Row counts of all seven application tables.
2. 58 fields and 580 satellite observations intact.
3. No duplicate field IDs or satellite observations.
4. No orphan satellite observations.
5. Alembic migration revision is 00ef7277e811.
6. Integrity of AI checkpoints and source data artifacts.
"""

import asyncio
import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import hashlib
from decimal import Decimal
from sqlalchemy import text
from app.db.session import AsyncSessionLocal, check_db_connectivity


async def run_phase_i_checks():
    print("=" * 70)
    print("STEP 11F.8 — PHASE I: FINAL DATABASE & ARTIFACT VERIFICATION")
    print("=" * 70)

    # 1. DB Connectivity Check
    conn_info = await check_db_connectivity()
    print("\n1. Database Connection:")
    print(f"   Status: {conn_info.get('status')}")
    print(f"   Database: {conn_info.get('database')}")
    print(f"   User: {conn_info.get('user')}")
    print(f"   Latency: {conn_info.get('latency_ms')} ms")
    assert conn_info.get("connected") is True, "Database must be connected"

    async with AsyncSessionLocal() as session:
        # 2. Table row counts
        tables = [
            "fields",
            "satellite_observations",
            "prediction_history",
            "weather_records",
            "market_prices",
            "buyers",
            "reports",
        ]
        print("\n2. Table Row Counts:")
        counts = {}
        for table in tables:
            res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            cnt = res.scalar()
            counts[table] = cnt
            print(f"   - {table:<24}: {cnt:>6} records")

        assert counts["fields"] == 58, f"Expected 58 fields, got {counts['fields']}"
        assert counts["satellite_observations"] == 580, f"Expected 580 satellite observations, got {counts['satellite_observations']}"
        assert counts["market_prices"] == 0, f"Expected 0 market prices, got {counts['market_prices']}"
        assert counts["buyers"] == 0, f"Expected 0 buyers, got {counts['buyers']}"
        assert counts["reports"] == 0, f"Expected 0 reports, got {counts['reports']}"

        # 3. Duplicate checks
        print("\n3. Duplicate Checks:")
        # Fields clean_field_id
        res = await session.execute(
            text("SELECT clean_field_id, COUNT(*) FROM fields GROUP BY clean_field_id HAVING COUNT(*) > 1")
        )
        dup_fields = res.fetchall()
        print(f"   Duplicate clean_field_id count: {len(dup_fields)}")
        assert len(dup_fields) == 0, f"Found duplicate fields: {dup_fields}"

        # Satellite duplicate observation: field_id + time_step
        res = await session.execute(
            text("SELECT field_id, time_step, COUNT(*) FROM satellite_observations GROUP BY field_id, time_step HAVING COUNT(*) > 1")
        )
        dup_sat = res.fetchall()
        print(f"   Duplicate satellite (field_id, time_step) count: {len(dup_sat)}")
        assert len(dup_sat) == 0, f"Found duplicate satellite observations: {dup_sat}"

        # 4. Orphan checks
        print("\n4. Orphan Satellite Observations Check:")
        res = await session.execute(
            text("""
                SELECT so.id, so.field_id
                FROM satellite_observations so
                LEFT JOIN fields f ON so.field_id = f.id
                WHERE f.id IS NULL
            """)
        )
        orphans = res.fetchall()
        print(f"   Orphan satellite observations: {len(orphans)}")
        assert len(orphans) == 0, f"Found orphan satellite observations: {orphans}"

        # 5. Alembic migration version
        print("\n5. Alembic Migration Revision:")
        res = await session.execute(text("SELECT version_num FROM alembic_version"))
        rev = res.scalar()
        print(f"   Current migration revision: {rev}")
        assert rev == "00ef7277e811", f"Unexpected alembic revision: {rev}"

        # 6. Verify observation values range for FIELD_01
        print("\n6. Sample Observations Check for FIELD_01:")
        res = await session.execute(
            text("""
                SELECT so.time_step, so.observation_date, so.ndvi, so.ndre, so.gndvi, so.data_source
                FROM satellite_observations so
                JOIN fields f ON so.field_id = f.id
                WHERE f.clean_field_id = 'CLEAN_FIELD_001'
                ORDER BY so.time_step ASC
            """)
        )
        obs_rows = res.fetchall()
        print(f"   Retrieved {len(obs_rows)} observations for CLEAN_FIELD_001 (FIELD_01)")
        assert len(obs_rows) == 10, f"Expected 10 observations, got {len(obs_rows)}"
        for row in obs_rows[:3]:
            print(f"     Step {row[0]}: date={row[1]}, NDVI={row[2]}, NDRE={row[3]}, GNDVI={row[4]}, src={row[5]}")

    # 7. AI Checkpoint and Source Data Files Integrity
    print("\n7. AI Checkpoints & Artifacts Integrity Check:")
    from app import config
    
    files_to_check = [
        ("EfficientNet-B4 Checkpoint", config.EFFICIENTNET_CHECKPOINT_PATH),
        ("Multimodal Checkpoint", config.MULTIMODAL_CHECKPOINT_PATH),
        ("Model Metadata", config.MODEL_METADATA_PATH),
        ("Satellite Sequences NPY", config.SATELLITE_SEQUENCES_PATH),
        ("Field Master Mapping CSV", config.FIELD_MASTER_MAPPING_PATH),
        ("Field Locations CSV", config.FIELD_LOCATIONS_PATH),
    ]

    for label, fpath in files_to_check:
        exists = fpath.is_file()
        rel_path = os.path.relpath(str(fpath), str(config.BASE_PROJECT_DIR))
        if exists:
            size_mb = fpath.stat().st_size / (1024 * 1024)
            print(f"   [FOUND] {label}: {rel_path} ({size_mb:.2f} MB)")
        else:
            print(f"   [MISSING] {label}: {rel_path}")
            assert exists, f"Critical artifact missing: {rel_path}"

    print("\n" + "=" * 70)
    print("PHASE I FINAL VERIFICATION: ALL CHECKS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_phase_i_checks())
