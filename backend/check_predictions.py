"""
Paddy Farming Assistant - Prediction Records Inspection Utility
Retrieves and displays prediction IDs and non-sensitive metadata from PostgreSQL.
Read-only script: does not modify or delete any records.
"""

import asyncio
import sys
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

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.prediction import PredictionHistory


async def check_predictions():
    """Queries and displays all prediction history records with identifying metadata."""
    try:
        async with AsyncSessionLocal() as session:
            # Query prediction records ordered by created_at DESC
            query = select(
                PredictionHistory.id,
                PredictionHistory.prediction_mode,
                PredictionHistory.predicted_disease,
                PredictionHistory.confidence,
                PredictionHistory.created_at,
                PredictionHistory.farmer_question,
                PredictionHistory.image_sha256,
            ).order_by(PredictionHistory.created_at.desc())

            result = await session.execute(query)
            records = result.fetchall()

            if not records:
                print("No prediction records found in 'prediction_history' table (table is empty).")
                return

            print("=" * 110)
            print(f"PREDICTION HISTORY RECORDS (Total: {len(records)})")
            print("=" * 110)
            print(f"{'#':<4} {'UUID (Prediction ID)':<38} {'Mode':<12} {'Disease':<24} {'Conf':<8} {'Created At (UTC)':<24}")
            print("-" * 110)

            for idx, r in enumerate(records, 1):
                pid = str(r.id)
                mode = str(r.prediction_mode or "unknown")
                disease = str(r.predicted_disease or "unknown")
                conf_val = f"{float(r.confidence):.2%}" if r.confidence is not None else "N/A"
                created = r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "N/A"
                print(f"{idx:<4} {pid:<38} {mode:<12} {disease:<24} {conf_val:<8} {created:<24}")
                if r.farmer_question:
                    print(f"     |-- Question: \"{r.farmer_question}\"")

            print("=" * 110)

    except Exception as exc:
        print(f"Error querying prediction history from database: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_predictions())
