"""
Paddy Farming Assistant - Test Prediction Records Cleanup Utility
Safely removes specifically identified test prediction records from PostgreSQL.
Strict safety rules:
- Never deletes all records.
- Never assumes the newest record is a test record.
- Never guesses without a reliable test identifier.
- Uses transactions and validates exactly 1 record was deleted.
"""

import sys
import argparse
import asyncio
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Ensure safe encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from sqlalchemy import select, delete, text
from app.db.session import AsyncSessionLocal
from app.db.models.prediction import PredictionHistory
from app.db.models.report import Report


async def delete_prediction_by_uuid(pred_uuid: uuid.UUID) -> bool:
    """
    Deletes a single prediction record by verified UUID within a strict transaction.
    Verifies that the record exists and that exactly 1 row was affected.
    """
    async with AsyncSessionLocal() as session:
        # 1. Fetch record first to verify existence and inspect metadata
        query = select(PredictionHistory).where(PredictionHistory.id == pred_uuid)
        res = await session.execute(query)
        record = res.scalar_one_or_none()

        if record is None:
            print(f"PREDICTION_NOT_FOUND: Record '{pred_uuid}' does not exist in 'prediction_history'.")
            return False

        # 2. Check for foreign key references in reports table
        report_check = await session.execute(
            select(Report.id, Report.title).where(Report.prediction_id == pred_uuid)
        )
        linked_reports = report_check.fetchall()
        if linked_reports:
            print(f"WARNING: Prediction '{pred_uuid}' has {len(linked_reports)} linked report(s):")
            for rep in linked_reports:
                print(f"   - Report ID: {rep.id} ({rep.title})")
            print("To maintain relational integrity, delete linked reports first or proceed with caution.")

        print(f"IDENTIFIED_RECORD: UUID={record.id} | Disease={record.predicted_disease} | Conf={record.confidence} | Created={record.created_at}")

        # 3. Perform atomic deletion in transaction
        try:
            del_stmt = delete(PredictionHistory).where(PredictionHistory.id == pred_uuid)
            del_res = await session.execute(del_stmt)

            if del_res.rowcount != 1:
                await session.rollback()
                print(f"TRANSACTION_ABORTED: Expected to delete 1 row, but matched {del_res.rowcount} rows. Rolled back.", file=sys.stderr)
                return False

            await session.commit()
            print(f"DELETED_PREDICTION:{pred_uuid}:{del_res.rowcount}")

            # 4. Post-deletion verification
            verify_res = await session.execute(
                select(PredictionHistory.id).where(PredictionHistory.id == pred_uuid)
            )
            if verify_res.scalar_one_or_none() is not None:
                print(f"ERROR: Record {pred_uuid} still present after commit!", file=sys.stderr)
                return False

            print(f"VERIFIED_CLEANUP: Record '{pred_uuid}' successfully removed from PostgreSQL.")
            return True

        except Exception as exc:
            await session.rollback()
            print(f"DATABASE_ERROR during deletion of '{pred_uuid}': {exc}", file=sys.stderr)
            return False


async def delete_prediction_by_image_hash(image_sha256: str) -> bool:
    """Deletes a test prediction identified by its explicit image SHA-256 hash."""
    sha = image_sha256.strip().lower()
    if len(sha) != 64:
        print(f"INVALID_HASH: SHA-256 hash must be 64 hexadecimal characters.")
        return False

    async with AsyncSessionLocal() as session:
        query = select(PredictionHistory).where(PredictionHistory.image_sha256 == sha)
        records = (await session.execute(query)).scalars().all()

        if not records:
            print(f"NO_RECORD_FOUND: No prediction matched image hash '{sha}'.")
            return False

        if len(records) > 1:
            print(f"SAFETY_STOP: Multiple records ({len(records)}) match image hash '{sha}'.")
            print("Specify the target UUID directly to avoid deleting unintended records:")
            for r in records:
                print(f"   - UUID: {r.id} | Created: {r.created_at} | Disease: {r.predicted_disease}")
            return False

        target_uuid = records[0].id

    return await delete_prediction_by_uuid(target_uuid)


async def check_schema_test_identifiers() -> bool:
    """
    Inspects the schema of 'prediction_history' to determine if an authoritative
    test identifier column (e.g. 'is_test', 'test_id', 'environment') exists.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'prediction_history' "
            "AND column_name IN ('is_test', 'test_id', 'environment', 'source')"
        ))
        matching_columns = [row[0] for row in res.fetchall()]
        return len(matching_columns) > 0


async def handle_auto_cleanup():
    """
    Strict safety handler when automatic cleanup is requested without an explicit ID.
    Per project safety rules:
    - Never assume that the newest prediction is a test prediction.
    - Never delete a record based only on its UUID existing in the database.
    - If the schema does not contain a reliable test identifier, stop safely.
    """
    has_test_column = await check_schema_test_identifiers()

    print("=" * 80)
    print("TEST PREDICTION AUTOMATIC RETRIEVAL & SAFETY AUDIT")
    print("=" * 80)

    if not has_test_column:
        print("[SAFETY_HALT] Automatic test prediction cleanup cannot proceed safely.")
        print()
        print("EXPLANATION:")
        print("  Database schema inspection shows table 'prediction_history' does NOT contain")
        print("  a dedicated test identifier column (such as 'is_test', 'test_id', or 'environment').")
        print("  Both live AI test inferences and authentic farmer predictions share the same")
        print("  model_name ('EfficientNet-B4') and version ('phaseC_best').")
        print()
        print("SAFETY RULES ENFORCED:")
        print("  1. The script will NOT guess or assume the newest prediction is a test record.")
        print("  2. The script will NOT delete any record without verified explicit identification.")
        print()
        print("SAFE WORKFLOW:")
        print("  Step 1. Inspect stored predictions using the safe reader script:")
        print("          ..\\venv\\Scripts\\python.exe .\\check_predictions.py")
        print()
        print("  Step 2. Delete the specifically verified test prediction by UUID:")
        print("          ..\\venv\\Scripts\\python.exe .\\cleanup_test_prediction.py <PREDICTION_UUID>")
        print()
        print("  Step 3. Or delete by known test image hash:")
        print("          ..\\venv\\Scripts\\python.exe .\\cleanup_test_prediction.py --image-hash <SHA256>")
        print("=" * 80)
        return False

    print("Schema has test identifier column. Automated lookup active.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Safely removes specifically identified test prediction records from PostgreSQL."
    )
    parser.add_argument(
        "prediction_id",
        nargs="?",
        default=None,
        help="Optional prediction UUID string to delete directly.",
    )
    parser.add_argument(
        "--id",
        dest="flag_id",
        default=None,
        help="Explicit prediction UUID to delete.",
    )
    parser.add_argument(
        "--image-hash",
        dest="image_hash",
        default=None,
        help="Target test prediction by exact input image SHA-256 hash.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Attempt automatic test prediction retrieval with schema safety audit.",
    )

    args = parser.parse_args()

    # Determine targeted ID
    target_id_str = args.flag_id or args.prediction_id

    if target_id_str:
        try:
            target_uuid = uuid.UUID(target_id_str.strip())
        except Exception as e:
            print(f"INVALID_UUID: '{target_id_str}' is not a valid UUID format ({e}).")
            sys.exit(1)

        success = asyncio.run(delete_prediction_by_uuid(target_uuid))
        sys.exit(0 if success else 1)

    if args.image_hash:
        success = asyncio.run(delete_prediction_by_image_hash(args.image_hash))
        sys.exit(0 if success else 1)

    # If neither UUID nor hash is provided, execute safe auto check
    success = asyncio.run(handle_auto_cleanup())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


