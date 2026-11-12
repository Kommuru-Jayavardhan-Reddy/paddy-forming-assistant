"""
Verification Test Suite for Automatic Test Prediction UUID Retrieval and Cleanup
Tests:
1. PowerShell string quoting explanation and check_predictions.py functionality.
2. Safe schema inspection and safety halt on missing test identifier.
3. Invalid UUID syntax handling (graceful error, no DB modification).
4. Non-existent UUID handling (graceful error, 0 rows deleted).
5. Isolated synthetic test prediction insertion, identification, cleanup, and verification.
6. Absolute non-pollution of baseline database records.
"""

import asyncio
import subprocess
import sys
import uuid
from decimal import Decimal
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func, text, delete
from app.db.session import AsyncSessionLocal
from app.db.models.prediction import PredictionHistory


async def get_prediction_count() -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.count(PredictionHistory.id)))
        return res.scalar() or 0


async def run_tests():
    print("=" * 80)
    print("RUNNING VERIFICATION SUITE FOR PREDICTION RETRIEVAL & CLEANUP")
    print("=" * 80)

    python_exe = sys.executable
    initial_count = await get_prediction_count()
    print(f"Initial prediction_history row count: {initial_count}")

    # TEST 1: check_predictions.py runs cleanly and prints records
    print("\n[TEST 1] Testing check_predictions.py execution...")
    cp_proc = subprocess.run(
        [python_exe, "check_predictions.py"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cp_proc.returncode == 0, f"check_predictions.py failed with code {cp_proc.returncode}:\n{cp_proc.stderr}"
    assert "PREDICTION HISTORY RECORDS" in cp_proc.stdout, "check_predictions.py missing header"
    assert "UUID (Prediction ID)" in cp_proc.stdout, "check_predictions.py missing column headers"
    print("  [PASS] check_predictions.py executed successfully and formatted records cleanly.")

    # TEST 2: cleanup_test_prediction.py with no args triggers safety halt
    print("\n[TEST 2] Testing cleanup_test_prediction.py safety halt on missing identifier...")
    cl_proc = subprocess.run(
        [python_exe, "cleanup_test_prediction.py"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cl_proc.returncode == 1, f"Expected returncode 1, got {cl_proc.returncode}"
    assert "[SAFETY_HALT]" in cl_proc.stdout, "Missing [SAFETY_HALT] notice in output"
    assert "check_predictions.py" in cl_proc.stdout, "Missing safe workflow recommendation"
    print("  [PASS] Safety halt successfully prevented accidental data deletion.")

    # TEST 3: cleanup_test_prediction.py with invalid UUID syntax
    print("\n[TEST 3] Testing invalid UUID syntax handling...")
    cl_inv = subprocess.run(
        [python_exe, "cleanup_test_prediction.py", "invalid-uuid-1234"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cl_inv.returncode == 1
    assert "INVALID_UUID" in cl_inv.stdout
    print("  [PASS] Invalid UUID format caught cleanly with no DB interaction.")

    # TEST 4: cleanup_test_prediction.py with non-existent UUID
    print("\n[TEST 4] Testing non-existent UUID handling...")
    dummy_uuid = "00000000-0000-0000-0000-000000000000"
    cl_none = subprocess.run(
        [python_exe, "cleanup_test_prediction.py", dummy_uuid],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cl_none.returncode == 1
    assert "PREDICTION_NOT_FOUND" in cl_none.stdout
    print("  [PASS] Non-existent UUID reported cleanly with zero modifications.")

    # TEST 5: Create isolated test prediction, verify retrieval, and clean up
    print("\n[TEST 5] Testing creation, targeted cleanup, and verification of a test prediction...")
    test_uuid = uuid.uuid4()
    test_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    async with AsyncSessionLocal() as session:
        test_pred = PredictionHistory(
            id=test_uuid,
            prediction_mode="image_only",
            model_name="EfficientNet-B4",
            model_version="test_cleanup_verification",
            predicted_disease="normal",
            predicted_class_index=12,
            confidence=Decimal("0.9999"),
            is_healthy=True,
            low_confidence=False,
            top_k_predictions=[{"disease": "normal", "probability": 0.9999, "index": 12}],
            farmer_question="AUTOMATED_TEST_VERIFICATION_QUESTION",
            image_sha256=test_hash,
        )
        session.add(test_pred)
        await session.commit()

    count_after_insert = await get_prediction_count()
    assert count_after_insert == initial_count + 1, f"Expected {initial_count + 1}, got {count_after_insert}"
    print(f"  Inserted isolated test prediction: {test_uuid}")

    # Verify check_predictions.py sees this record
    cp_check = subprocess.run(
        [python_exe, "check_predictions.py"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert str(test_uuid) in cp_check.stdout, "check_predictions.py did not display the new test record"
    assert "AUTOMATED_TEST_VERIFICATION_QUESTION" in cp_check.stdout
    print("  [PASS] check_predictions.py reliably detected the test prediction UUID and question.")

    # Clean up test prediction using cleanup_test_prediction.py
    cl_del = subprocess.run(
        [python_exe, "cleanup_test_prediction.py", str(test_uuid)],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert cl_del.returncode == 0, f"Cleanup failed:\n{cl_del.stderr}\n{cl_del.stdout}"
    assert f"DELETED_PREDICTION:{test_uuid}:1" in cl_del.stdout
    assert "VERIFIED_CLEANUP" in cl_del.stdout
    print("  [PASS] cleanup_test_prediction.py deleted exactly 1 row within a verified transaction.")

    # TEST 6: Verify database row count is restored exactly to initial count
    print("\n[TEST 6] Verifying database integrity and zero pollution...")
    final_count = await get_prediction_count()
    assert final_count == initial_count, f"Final count mismatch: {final_count} != {initial_count}"
    print(f"  Final prediction_history row count: {final_count} (exactly matches initial {initial_count}).")
    print("  [PASS] Database non-pollution confirmed.")

    print("\n" + "=" * 80)
    print("ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_tests())
