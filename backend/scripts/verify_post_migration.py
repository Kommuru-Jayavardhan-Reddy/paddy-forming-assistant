"""
Paddy Farming Assistant - Post-Migration Database Verification (STEP 11F.6)
Validates created tables, constraints, foreign keys, indexes, alembic version,
and user permissions directly against PostgreSQL system catalogs.
"""

import sys
import asyncio
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app import config
from app.db.session import get_async_engine, close_db_engine


async def verify_post_migration() -> int:
    print("=" * 80)
    print("STEP 11F.6 — POST-MIGRATION POSTGRESQL CATALOG VERIFICATION")
    print("=" * 80)

    engine = get_async_engine()

    try:
        async with engine.connect() as conn:
            # 1. Database and Session Identity
            id_query = text("SELECT current_database() AS dbname, current_user AS username, version() AS ver;")
            id_row = (await conn.execute(id_query)).mappings().one()
            print(f"\n[1/7] Connected Database: {id_row['dbname']} | Active User: {id_row['username']}")
            assert id_row['dbname'] == "paddy_farming_db", "Target database mismatch!"
            assert id_row['username'] == "paddy_app", "Session user mismatch!"

            # 2. Table Inventory in 'public' Schema
            print("\n[2/7] Verifying Table Inventory...")
            tbl_query = text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' ORDER BY table_name;"
            )
            tables = (await conn.execute(tbl_query)).scalars().all()
            print(f"  Public Tables Found ({len(tables)}): {tables}")

            expected_tables = [
                "alembic_version",
                "buyers",
                "fields",
                "market_prices",
                "prediction_history",
                "reports",
                "satellite_observations",
                "weather_records",
            ]
            if sorted(tables) != sorted(expected_tables):
                print(f"  [FAIL] Unexpected table list: expected {expected_tables}, got {tables}")
                return 1
            print("  [PASS] Exactly the 7 planned application tables plus alembic_version exist.")

            # 3. Alembic Version Verification
            print("\n[3/7] Verifying Alembic Migration Version...")
            rev_query = text("SELECT version_num FROM alembic_version;")
            revisions = (await conn.execute(rev_query)).scalars().all()
            print(f"  Alembic recorded revisions: {revisions}")
            if not revisions or revisions[0] != "00ef7277e811":
                print(f"  [FAIL] Expected revision '00ef7277e811', found {revisions}")
                return 1
            print("  [PASS] Migration 00ef7277e811 is recorded as current revision.")

            # 4. Primary Key Verification
            print("\n[4/7] Verifying Primary Keys...")
            pk_query = text("""
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                  AND tc.table_name != 'alembic_version'
                ORDER BY tc.table_name;
            """)
            pks = (await conn.execute(pk_query)).all()
            for tbl, col in pks:
                print(f"  PK -> {tbl}.{col}")
            assert len(pks) == 7, f"Expected 7 primary keys, found {len(pks)}"
            print("  [PASS] All 7 tables have primary keys.")

            # 5. Foreign Key Verification & Deletion Actions
            print("\n[5/7] Verifying Foreign Keys & On-Delete Behaviors...")
            fk_query = text("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                JOIN information_schema.referential_constraints AS rc
                    ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name;
            """)
            fks = (await conn.execute(fk_query)).all()
            for src_tbl, src_col, tgt_tbl, tgt_col, del_rule in fks:
                print(f"  FK: {src_tbl}.{src_col} -> {tgt_tbl}.{tgt_col} (ON DELETE {del_rule})")

            expected_fk_rules = {
                ("prediction_history", "field_id"): ("fields", "id", "SET NULL"),
                ("satellite_observations", "field_id"): ("fields", "id", "CASCADE"),
                ("weather_records", "field_id"): ("fields", "id", "SET NULL"),
                ("reports", "field_id"): ("fields", "id", "SET NULL"),
                ("reports", "prediction_id"): ("prediction_history", "id", "SET NULL"),
            }

            for (src_tbl, src_col), (exp_tgt, exp_col, exp_rule) in expected_fk_rules.items():
                match = [
                    f for f in fks
                    if f[0] == src_tbl and f[1] == src_col and f[2] == exp_tgt and f[3] == exp_col and f[4] == exp_rule
                ]
                if not match:
                    print(f"  [FAIL] Missing/mismatched FK on {src_tbl}.{src_col}")
                    return 1
            print("  [PASS] All 5 foreign keys and cascade/set-null policies verified.")

            # 6. Check Constraints & Unique Constraints
            print("\n[6/7] Verifying Unique & Check Constraints...")
            ck_query = text("""
                SELECT tc.table_name, tc.constraint_name, tc.constraint_type
                FROM information_schema.table_constraints tc
                WHERE tc.table_schema = 'public'
                  AND tc.constraint_type IN ('CHECK', 'UNIQUE')
                  AND tc.table_name != 'alembic_version'
                ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;
            """)
            constraints = (await conn.execute(ck_query)).all()
            for tbl, cname, ctype in constraints:
                print(f"  {ctype}: {tbl}.{cname}")

            cnames = [c[1] for c in constraints]
            assert any("ck_pred_mode_class_index" in n for n in cnames), "Missing mode/class index constraint!"
            assert "uq_sat_field_date_source" in cnames, "Missing uq_sat_field_date_source!"
            assert "uq_market_quote" in cnames, "Missing uq_market_quote!"
            print("  [PASS] All critical domain constraints verified in catalog.")

            # 7. Database Privileges for paddy_app
            print("\n[7/7] Verifying Table & Sequence Privileges for paddy_app...")
            app_tables = [
                "fields",
                "prediction_history",
                "satellite_observations",
                "weather_records",
                "market_prices",
                "buyers",
                "reports",
            ]
            for tbl in app_tables:
                for priv in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                    priv_query = text(f"SELECT has_table_privilege('paddy_app', '{tbl}', '{priv}');")
                    has_priv = (await conn.execute(priv_query)).scalar()
                    if not has_priv:
                        print(f"  [FAIL] paddy_app lacks {priv} on {tbl}!")
                        return 1
                print(f"  Privileges on {tbl}: SELECT, INSERT, UPDATE, DELETE (PASS)")

            # Check sequences for BIGINT IDENTITY tables
            seq_query = text("""
                SELECT sequence_name FROM information_schema.sequences
                WHERE sequence_schema = 'public';
            """)
            sequences = (await conn.execute(seq_query)).scalars().all()
            print(f"  Sequences Found: {sequences}")
            for seq in sequences:
                priv_seq = (await conn.execute(text(f"SELECT has_sequence_privilege('paddy_app', '{seq}', 'USAGE, SELECT');"))).scalar()
                print(f"  Sequence {seq}: USAGE/SELECT = {priv_seq}")
                if not priv_seq:
                    print(f"  [FAIL] paddy_app lacks USAGE on sequence {seq}!")
                    return 1

            print("  [PASS] All necessary operational privileges verified for paddy_app.")

    finally:
        await close_db_engine()

    print("\n" + "=" * 80)
    print("STEP 11F.6 POST-MIGRATION VERIFICATION: ALL CHECKS PASSED (100%)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(verify_post_migration())
    sys.exit(exit_code)
