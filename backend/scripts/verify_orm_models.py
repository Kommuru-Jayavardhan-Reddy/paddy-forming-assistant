"""
Paddy Farming Assistant - SQLAlchemy ORM Models Validation (STEP 11F.5)
Validates all seven ORM model definitions, mapper configurations,
relationships, foreign keys, constraints, and verifies AI model import integrity.
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    print("=" * 80)
    print("STEP 11F.5 — SQLALCHEMY ORM MODELS & DECLARATIVE BASE VALIDATION")
    print("=" * 80)

    # 1. AI Model Import Preservation
    print("\n[1/6] Verifying existing AI model imports are not broken...")
    try:
        from app.models import ModelLoader, TemporalCrossAttentionModel, MultimodalModelLoader
        from app.models.model_loader import ModelLoader as MLDirect
        from app.models.multimodal_model import MultimodalModelLoader as MMLDirect
        print("  [PASS] Existing AI model imports verified with zero namespace conflicts.")
    except Exception as exc:
        print(f"  [FAIL] Failed to import existing AI models: {exc}")
        return 1

    # 2. ORM Models Import
    print("\n[2/6] Importing SQLAlchemy Declarative Base and all 7 ORM models...")
    try:
        from app.db.base import Base, TimestampMixin
        from app.db.models import (
            Field,
            PredictionHistory,
            SatelliteObservation,
            WeatherRecord,
            MarketPrice,
            Buyer,
            Report,
        )
        from app.models.orm import (
            Field as FieldORM,
            PredictionHistory as PredORM,
            SatelliteObservation as SatORM,
            WeatherRecord as WeatherORM,
            MarketPrice as MarketORM,
            Buyer as BuyerORM,
            Report as ReportORM,
        )
        print("  [PASS] Successfully imported all 7 ORM models from app.db.models and app.models.orm.")
    except Exception as exc:
        print(f"  [FAIL] Failed to import ORM models: {exc}")
        return 1

    # 3. SQLAlchemy Mapper Configuration
    print("\n[3/6] Running sqlalchemy.orm.configure_mappers()...")
    try:
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        print("  [PASS] All model mappers, relationships, and back_populates configured successfully.")
    except Exception as exc:
        print(f"  [FAIL] Mapper configuration failed: {exc}")
        return 1

    # 4. Table Count and Names in Metadata
    print("\n[4/6] Verifying Metadata Table Registry...")
    expected_tables = {
        "fields",
        "prediction_history",
        "satellite_observations",
        "weather_records",
        "market_prices",
        "buyers",
        "reports",
    }
    actual_tables = set(Base.metadata.tables.keys())
    print(f"  Actual tables registered: {sorted(list(actual_tables))}")
    if actual_tables != expected_tables:
        diff = expected_tables.symmetric_difference(actual_tables)
        print(f"  [FAIL] Table mismatch in metadata! Difference: {diff}")
        return 1
    print(f"  [PASS] Exactly the intended 7 tables registered in Base.metadata.")

    # 5. Foreign Keys and Cascade Policies
    print("\n[5/6] Verifying Foreign Keys and Deletion Policies...")
    fk_checks = [
        ("prediction_history", "field_id", "fields.id", "SET NULL"),
        ("satellite_observations", "field_id", "fields.id", "CASCADE"),
        ("weather_records", "field_id", "fields.id", "SET NULL"),
        ("reports", "field_id", "fields.id", "SET NULL"),
        ("reports", "prediction_id", "prediction_history.id", "SET NULL"),
    ]

    for table_name, col_name, target, ondelete in fk_checks:
        tbl = Base.metadata.tables[table_name]
        matching_fks = [fk for fk in tbl.foreign_keys if fk.parent.name == col_name]
        if not matching_fks:
            print(f"  [FAIL] Missing FK on {table_name}.{col_name}")
            return 1
        fk = matching_fks[0]
        actual_target = f"{fk.column.table.name}.{fk.column.name}"
        if actual_target != target:
            print(f"  [FAIL] {table_name}.{col_name} targets {actual_target}, expected {target}")
            return 1
        if fk.ondelete != ondelete:
            print(f"  [FAIL] {table_name}.{col_name} ondelete is '{fk.ondelete}', expected '{ondelete}'")
            return 1
        print(f"  [PASS] {table_name}.{col_name} -> {target} (ON DELETE {ondelete})")

    # 6. Check Constraints & Unique Constraints
    print("\n[6/6] Verifying Constraints and Schema Safety...")
    pred_tbl = Base.metadata.tables["prediction_history"]
    pred_ck_names = [ck.name for ck in pred_tbl.constraints if hasattr(ck, "sqltext")]
    print(f"  PredictionHistory check constraints: {pred_ck_names}")
    assert any("mode_class_index" in name or "ck_pred_mode_class_index" in name for name in pred_ck_names), \
        "Missing dual 13-class/11-class mode check constraint on PredictionHistory!"

    sat_tbl = Base.metadata.tables["satellite_observations"]
    sat_uqs = [c.name for c in sat_tbl.constraints if hasattr(c, "columns") and c.__class__.__name__ == "UniqueConstraint"]
    print(f"  SatelliteObservation unique constraints: {sat_uqs}")
    assert "uq_sat_field_date_source" in sat_uqs, "Missing uq_sat_field_date_source on SatelliteObservation!"

    market_tbl = Base.metadata.tables["market_prices"]
    market_uqs = [c.name for c in market_tbl.constraints if hasattr(c, "columns") and c.__class__.__name__ == "UniqueConstraint"]
    print(f"  MarketPrice unique constraints: {market_uqs}")
    assert "uq_market_quote" in market_uqs, "Missing uq_market_quote on MarketPrice!"

    print("  [PASS] All required CheckConstraints and UniqueConstraints verified.")

    # 7. Database State Check: Confirm all 7 tables exist in the database
    print("\n[7/7] Confirming all 7 tables are present in the PostgreSQL database...")
    import asyncio
    from sqlalchemy import text
    from app.db.session import get_async_engine, close_db_engine

    async def _check_db():
        engine = get_async_engine()
        try:
            async with engine.connect() as conn:
                stmt = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
                res = await conn.execute(stmt)
                tables = set(res.scalars().all())
                print(f"  Public tables currently in PostgreSQL database: {sorted(list(tables))}")
                missing = expected_tables.difference(tables)
                if missing:
                    print(f"  [FAIL] Missing tables in database! Missing: {missing}")
                    return False
                print(f"  [PASS] Confirmed: All 7 application tables successfully provisioned in PostgreSQL.")
                return True
        finally:
            await close_db_engine()

    clean = asyncio.run(_check_db())
    if not clean:
        return 1

    print("\n" + "=" * 80)
    print("ORM MODELS VALIDATION: ALL CHECKS PASSED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
