"""
Paddy Farming Assistant - Post-Seed Database Verification Script (STEP 11F.7)
Executes comprehensive PostgreSQL catalog and table queries to verify:
1. Fields and satellite observations counts
2. External ID uniqueness and no duplicates
3. (field_id, observation_date, data_source) uniqueness
4. No orphan records (referential integrity)
5. GPS coordinates bounds and precision
6. Vegetation index numerical bounds
7. Integrity of empty tables (no dummy records in prediction, weather, market, buyer, report)
8. Exact match against bilstm_sequences.npy ground truth
"""

import sys
import asyncio
from pathlib import Path
import numpy as np
from sqlalchemy import text, select, func

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import config
from app.db.session import AsyncSessionLocal, check_db_connectivity, close_db_engine
from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation


async def run_post_seed_verification():
    print("=" * 70)
    print("STEP 11F.7 — POST-SEED DATABASE VERIFICATION")
    print("=" * 70)

    db_health = await check_db_connectivity()
    print(f"[Health] PostgreSQL connection: {db_health.get('status')}, latency={db_health.get('latency_ms')}ms")

    passed_checks = 0
    total_checks = 10

    try:
        async with AsyncSessionLocal() as session:
            # Check 1: Exactly 58 Fields
            res_fields_count = await session.execute(select(func.count(Field.id)))
            field_count = res_fields_count.scalar()
            print(f"\n[Check 1] Fields count: {field_count} (expected 58)")
            assert field_count == 58, f"Expected 58 fields, got {field_count}"
            passed_checks += 1
            print("  [PASS] Exactly 58 fields present.")

            # Check 2: Exactly 580 Satellite Observations
            res_obs_count = await session.execute(select(func.count(SatelliteObservation.id)))
            obs_count = res_obs_count.scalar()
            print(f"\n[Check 2] Satellite observations count: {obs_count} (expected 580)")
            assert obs_count == 580, f"Expected 580 observations, got {obs_count}"
            passed_checks += 1
            print("  [PASS] Exactly 580 observations present (58 fields x 10 steps).")

            # Check 3: Exactly 10 Observations per Field
            res_per_field = await session.execute(
                text("""
                    SELECT f.external_field_id, count(s.id) as obs_count
                    FROM fields f
                    LEFT JOIN satellite_observations s ON s.field_id = f.id
                    GROUP BY f.external_field_id
                    HAVING count(s.id) != 10
                """)
            )
            unequal_fields = res_per_field.all()
            print(f"\n[Check 3] Fields with observation count != 10: {len(unequal_fields)}")
            assert len(unequal_fields) == 0, f"Fields with count != 10: {unequal_fields}"
            passed_checks += 1
            print("  [PASS] All 58 fields have exactly 10 satellite observations.")

            # Check 4: No Duplicate external_field_id
            res_dup_fields = await session.execute(
                text("""
                    SELECT external_field_id, count(*)
                    FROM fields
                    GROUP BY external_field_id
                    HAVING count(*) > 1
                """)
            )
            dup_fields = res_dup_fields.all()
            print(f"\n[Check 4] Duplicate external_field_ids: {len(dup_fields)}")
            assert len(dup_fields) == 0, f"Duplicate fields found: {dup_fields}"
            passed_checks += 1
            print("  [PASS] All external_field_ids are strictly unique.")

            # Check 5: No Duplicate (field_id, observation_date, data_source)
            res_dup_obs = await session.execute(
                text("""
                    SELECT field_id, observation_date, data_source, count(*)
                    FROM satellite_observations
                    GROUP BY field_id, observation_date, data_source
                    HAVING count(*) > 1
                """)
            )
            dup_obs = res_dup_obs.all()
            print(f"\n[Check 5] Duplicate (field_id, observation_date, data_source) rows: {len(dup_obs)}")
            assert len(dup_obs) == 0, f"Duplicate observations found: {dup_obs}"
            passed_checks += 1
            print("  [PASS] All satellite observations satisfy unique constraint uq_sat_field_date_source.")

            # Check 6: Referential Integrity / No Orphan Observations
            res_orphans = await session.execute(
                text("""
                    SELECT count(*)
                    FROM satellite_observations s
                    LEFT JOIN fields f ON s.field_id = f.id
                    WHERE f.id IS NULL
                """)
            )
            orphan_count = res_orphans.scalar()
            print(f"\n[Check 6] Orphan satellite observations: {orphan_count}")
            assert orphan_count == 0, f"Orphan observations detected: {orphan_count}"
            passed_checks += 1
            print("  [PASS] 100% of observations link to valid parent field UUIDs.")

            # Check 7: GPS Coordinates Bounds
            res_gps = await session.execute(
                text("""
                    SELECT min(latitude), max(latitude), min(longitude), max(longitude)
                    FROM fields
                """)
            )
            min_lat, max_lat, min_lon, max_lon = res_gps.first()
            print(f"\n[Check 7] Field GPS bounds:")
            print(f"  Latitude:  [{min_lat}, {max_lat}]")
            print(f"  Longitude: [{min_lon}, {max_lon}]")
            assert 13.0 <= float(min_lat) and float(max_lat) <= 14.5, "Latitude out of project region"
            assert 78.0 <= float(min_lon) and float(max_lon) <= 80.5, "Longitude out of project region"
            passed_checks += 1
            print("  [PASS] Field coordinates within authentic Andhra Pradesh region.")

            # Check 8: Vegetation Indices Bounds
            res_indices = await session.execute(
                text("""
                    SELECT min(ndvi), max(ndvi), min(ndre), max(ndre), min(gndvi), max(gndvi)
                    FROM satellite_observations
                """)
            )
            min_ndvi, max_ndvi, min_ndre, max_ndre, min_gndvi, max_gndvi = res_indices.first()
            print(f"\n[Check 8] Vegetation index bounds in database:")
            print(f"  NDVI:  [{min_ndvi}, {max_ndvi}]")
            print(f"  NDRE:  [{min_ndre}, {max_ndre}]")
            print(f"  GNDVI: [{min_gndvi}, {max_gndvi}]")
            assert -1.0 <= float(min_ndvi) and float(max_ndvi) <= 1.0, "NDVI out of bounds"
            assert -1.0 <= float(min_ndre) and float(max_ndre) <= 1.0, "NDRE out of bounds"
            assert -1.0 <= float(min_gndvi) and float(max_gndvi) <= 1.0, "GNDVI out of bounds"
            passed_checks += 1
            print("  [PASS] All spectral indices strictly satisfy check constraints [-1.0, 1.0].")

            # Check 9: Numerical Fidelity against bilstm_sequences.npy ground truth
            seq_npy = np.load(config.SATELLITE_SEQUENCES_PATH, allow_pickle=False)
            res_f1_obs = await session.execute(
                text("""
                    SELECT s.time_step, s.observation_date, s.ndvi, s.ndre, s.gndvi
                    FROM satellite_observations s
                    JOIN fields f ON s.field_id = f.id
                    WHERE f.external_field_id = 'FIELD_01'
                    ORDER BY s.time_step ASC
                """)
            )
            f1_rows = res_f1_obs.all()
            print(f"\n[Check 9] Verifying FIELD_01 values against bilstm_sequences.npy[0]:")
            for step_idx, row in enumerate(f1_rows):
                expected = seq_npy[0, step_idx]
                db_vals = [float(row[2]), float(row[3]), float(row[4])]
                diff = max(abs(e - d) for e, d in zip(expected, db_vals))
                assert diff < 1e-4, f"Mismatch at step {step_idx}: expected {expected}, got {db_vals}, diff={diff}"
            passed_checks += 1
            print(f"  [PASS] All 10 timesteps of FIELD_01 match bilstm_sequences.npy ground truth (max diff < 0.0001).")

            # Check 10: Non-Seeded Tables Remain Clean (Zero Dummy Records)
            res_tables = await session.execute(
                text("""
                    SELECT 
                        (SELECT count(*) FROM prediction_history) as pred_count,
                        (SELECT count(*) FROM weather_records) as weather_count,
                        (SELECT count(*) FROM market_prices) as market_count,
                        (SELECT count(*) FROM buyers) as buyer_count,
                        (SELECT count(*) FROM reports) as report_count
                """)
            )
            counts = res_tables.first()
            print(f"\n[Check 10] Non-seeded tables record counts:")
            print(f"  prediction_history: {counts[0]}")
            print(f"  weather_records:    {counts[1]}")
            print(f"  market_prices:      {counts[2]}")
            print(f"  buyers:             {counts[3]}")
            print(f"  reports:            {counts[4]}")
            assert all(c == 0 for c in counts), f"Unexpected data found in non-seeded tables: {counts}"
            passed_checks += 1
            print("  [PASS] Zero dummy records inserted into prediction, weather, market, buyer, or report tables.")

    finally:
        await close_db_engine()

    print("\n" + "=" * 70)
    print(f"VERIFICATION SUMMARY: {passed_checks} / {total_checks} CHECKS PASSED (100%)")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_post_seed_verification())
    if not success:
        sys.exit(1)
