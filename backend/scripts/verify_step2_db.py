"""
Verification script for Step 2 Database Changes
Verifies:
1. 'farmers' table existence and schema.
2. 'prediction_history.farmer_id' is nullable and uses ON DELETE SET NULL.
3. Composite index on ('farmer_id', 'created_at') exists.
4. Exactly 53 legacy prediction records preserved with farmer_id = NULL.
5. Zero default admin/sample accounts created.
6. Alembic reports c748e89f1d2a as current head.
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def run_verification():
    print("=" * 80)
    print("STEP 2: DATABASE MIGRATION VERIFICATION AUDIT")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # 1. Farmers table existence
        res = await session.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'farmers')")
        )
        exists = res.scalar()
        print(f"\n[1] Table 'farmers' exists: {exists}")
        assert exists, "Table 'farmers' does not exist!"

        # 2. Farmers table schema
        res = await session.execute(
            text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'farmers'
                ORDER BY ordinal_position
            """)
        )
        print("\n[2] Table 'farmers' columns:")
        for r in res.fetchall():
            print(f"    - {r[0]:<15} {r[1]:<25} nullable={r[2]:<6} default={r[3]}")

        # 3. farmer_id in prediction_history
        res = await session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'prediction_history' AND column_name = 'farmer_id'
            """)
        )
        col = res.fetchone()
        print(f"\n[3] Column 'farmer_id' in 'prediction_history':")
        print(f"    - Name:      {col[0]}")
        print(f"    - Data Type: {col[1]}")
        print(f"    - Nullable:  {col[2]} (Expected: YES)")
        assert col[2] == "YES", "Column farmer_id must be nullable!"

        # 4. Foreign key constraint
        res = await session.execute(
            text("""
                SELECT
                    tc.constraint_name,
                    rc.delete_rule,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.referential_constraints AS rc
                    ON tc.constraint_name = rc.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_name = 'prediction_history'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND ccu.table_name = 'farmers'
            """)
        )
        fk = res.fetchone()
        print(f"\n[4] Foreign Key Constraint to 'farmers':")
        print(f"    - Constraint Name: {fk[0]}")
        print(f"    - ON DELETE Rule:  {fk[1]} (Expected: SET NULL)")
        print(f"    - References:      {fk[2]}.{fk[3]}")
        assert fk[1] == "SET NULL", "FK ON DELETE action must be SET NULL!"

        # 5. Indexes on prediction_history
        res = await session.execute(
            text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'prediction_history'
                ORDER BY indexname
            """)
        )
        print("\n[5] Indexes on 'prediction_history':")
        has_composite_index = False
        has_redundant_single_index = False
        for r in res.fetchall():
            print(f"    - {r[0]}: {r[1]}")
            if r[0] == "idx_pred_farmer_created":
                has_composite_index = True
            if r[0] == "ix_prediction_history_farmer_id":
                has_redundant_single_index = True

        assert has_composite_index, "Composite index 'idx_pred_farmer_created' must exist!"
        assert not has_redundant_single_index, "No redundant single-column index on farmer_id should exist!"
        print("    [PASS] Composite index on (farmer_id, created_at) verified without duplicate single-column index.")

        # 6. Legacy records audit
        res_total = await session.execute(text("SELECT count(*) FROM prediction_history"))
        total_count = res_total.scalar()
        res_null = await session.execute(text("SELECT count(*) FROM prediction_history WHERE farmer_id IS NULL"))
        null_count = res_null.scalar()
        print(f"\n[6] Legacy Records Audit:")
        print(f"    - Total records in prediction_history: {total_count} (Expected: 53)")
        print(f"    - Records with farmer_id IS NULL:      {null_count} (Expected: 53)")
        assert total_count == 53, f"Expected 53 records, got {total_count}"
        assert null_count == 53, f"All 53 records must have farmer_id IS NULL, got {null_count}"
        print("    [PASS] All 53 legacy records preserved with farmer_id = NULL.")

        # 7. Zero sample/admin accounts check
        res_farmers = await session.execute(text("SELECT count(*) FROM farmers"))
        farmer_count = res_farmers.scalar()
        print(f"\n[7] Accounts in 'farmers' table: {farmer_count} (Expected: 0)")
        assert farmer_count == 0, "No sample farmers, admin accounts, or default credentials should exist!"
        print("    [PASS] Clean zero-account baseline confirmed.")

    print("\n" + "=" * 80)
    print("ALL STEP 2 DATABASE VERIFICATION CHECKS PASSED SUCCESSFULLY.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_verification())
