"""
Paddy Farming Assistant - Auxiliary Repositories (STEP 11F.8)
Provides CRUD/lookup methods for MarketPrice, Buyer, and Report ORM entities.
"""

import logging
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Sequence, Tuple, Dict, Any
from sqlalchemy import select, func, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.market import MarketPrice
from app.db.models.buyer import Buyer
from app.db.models.report import Report
from app.db.repositories.base import BaseRepository
from app.services.geo_service import haversine_distance_km

logger = logging.getLogger(__name__)


def _match_commodity(commodity_val: str):
    """
    Matches commodity names flexibly, allowing standard 'Paddy (Dhan)' query defaults
    to match official Agmarknet 'Paddy(Common)' and 'Paddy(Basmati)' records.
    """
    clean = commodity_val.lower().strip()
    if clean in ("paddy (dhan)", "paddy(dhan)", "paddy"):
        return func.lower(MarketPrice.commodity).like("paddy%")
    return func.lower(MarketPrice.commodity) == clean


class MarketPriceRepository(BaseRepository[MarketPrice]):
    """
    Repository for wholesale agricultural mandi prices.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(MarketPrice, session)

    async def upsert_prices(self, prices: List[Dict[str, Any]]) -> int:
        """
        Atomically and idempotently upserts a list of market price dictionaries into PostgreSQL.
        Matches on UniqueConstraint 'uq_market_quote' (market_name, commodity, variety, price_date).
        Deduplicates in-memory preserving the latest quote per unique key.
        """
        if not prices:
            return 0

        deduped: Dict[Tuple[str, str, str, date], Dict[str, Any]] = {}
        for p in prices:
            key = (p["market_name"], p["commodity"], p["variety"], p["price_date"])
            deduped[key] = p

        upserted_count = 0
        now_utc = datetime.now(timezone.utc)
        for item in deduped.values():
            stmt = pg_insert(MarketPrice).values(**item)
            stmt = stmt.on_conflict_do_update(
                index_elements=["market_name", "commodity", "variety", "price_date"],
                set_={
                    "min_price": item["min_price"],
                    "max_price": item["max_price"],
                    "modal_price": item["modal_price"],
                    "grade": item.get("grade", "FAQ"),
                    "unit": item.get("unit", "Quintal"),
                    "currency": item.get("currency", "INR"),
                    "source": item.get("source", "Agmarknet via Data.gov.in"),
                    "retrieval_timestamp": now_utc,
                },
            )
            await self.session.execute(stmt)
            upserted_count += 1

        await self.session.flush()
        logger.info("Upserted %d market price quotations into database.", upserted_count)
        return upserted_count

    async def list_latest_prices(
        self,
        district: Optional[str] = None,
        commodity: Optional[str] = None,
        variety: Optional[str] = None,
        state: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[MarketPrice], int]:
        safe_limit = min(max(1, limit), 200)
        safe_skip = max(0, skip)

        query = select(MarketPrice)
        count_query = select(func.count(MarketPrice.id))

        if state:
            query = query.where(func.lower(MarketPrice.state) == state.lower().strip())
            count_query = count_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if district:
            query = query.where(func.lower(MarketPrice.district) == district.lower().strip())
            count_query = count_query.where(func.lower(MarketPrice.district) == district.lower().strip())
        if commodity:
            query = query.where(_match_commodity(commodity))
            count_query = count_query.where(_match_commodity(commodity))
        if variety:
            query = query.where(func.lower(MarketPrice.variety) == variety.lower().strip())
            count_query = count_query.where(func.lower(MarketPrice.variety) == variety.lower().strip())

        query = query.order_by(desc(MarketPrice.price_date), desc(MarketPrice.id)).offset(safe_skip).limit(safe_limit)

        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar() or 0

        res = await self.session.execute(query)
        records = res.scalars().all()

        return records, total_count

    async def get_market_summary(
        self,
        state: Optional[str] = None,
        district: Optional[str] = None,
        commodity: Optional[str] = None,
        variety: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes aggregate summary metrics across matching mandi records in PostgreSQL.
        Distinguishes missing data from calculated zero.
        """
        query = select(
            func.count(MarketPrice.id).label("total_observations"),
            func.count(func.distinct(MarketPrice.market_name)).label("distinct_markets"),
            func.count(func.distinct(MarketPrice.district)).label("distinct_districts"),
            func.count(func.distinct(MarketPrice.variety)).label("distinct_varieties"),
            func.avg(MarketPrice.modal_price).label("avg_modal_price"),
            func.min(MarketPrice.modal_price).label("min_modal_price"),
            func.max(MarketPrice.modal_price).label("max_modal_price"),
            func.min(MarketPrice.min_price).label("min_transaction_price"),
            func.max(MarketPrice.max_price).label("max_transaction_price"),
            func.min(MarketPrice.price_date).label("earliest_price_date"),
            func.max(MarketPrice.price_date).label("latest_price_date"),
        )
        if state:
            query = query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if district:
            query = query.where(func.lower(MarketPrice.district) == district.lower().strip())
        if commodity:
            query = query.where(_match_commodity(commodity))
        if variety:
            query = query.where(func.lower(MarketPrice.variety) == variety.lower().strip())

        res = await self.session.execute(query)
        row = res.one()

        total = row.total_observations or 0
        has_data = total > 0

        return {
            "state": state,
            "district": district,
            "commodity": commodity or "Paddy (Dhan)",
            "variety": variety,
            "has_data": has_data,
            "total_observations": total,
            "distinct_markets": row.distinct_markets or 0,
            "distinct_districts": row.distinct_districts or 0,
            "distinct_varieties": row.distinct_varieties or 0,
            "avg_modal_price": float(round(row.avg_modal_price, 2)) if row.avg_modal_price is not None else None,
            "min_modal_price": float(row.min_modal_price) if row.min_modal_price is not None else None,
            "max_modal_price": float(row.max_modal_price) if row.max_modal_price is not None else None,
            "min_transaction_price": float(row.min_transaction_price) if row.min_transaction_price is not None else None,
            "max_transaction_price": float(row.max_transaction_price) if row.max_transaction_price is not None else None,
            "earliest_price_date": row.earliest_price_date,
            "latest_price_date": row.latest_price_date,
            "currency": "INR",
            "unit": "Quintal",
        }

    async def get_daily_trends(
        self,
        days: int = 7,
        state: Optional[str] = None,
        district: Optional[str] = None,
        commodity: Optional[str] = None,
        variety: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes historical daily price movements and net price trend direction.
        Strictly returns trend_direction='insufficient_data' if fewer than 2 distinct observation dates exist.
        """
        # Determine latest price date in matching records
        max_date_query = select(func.max(MarketPrice.price_date))
        if state:
            max_date_query = max_date_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if district:
            max_date_query = max_date_query.where(func.lower(MarketPrice.district) == district.lower().strip())
        if commodity:
            max_date_query = max_date_query.where(_match_commodity(commodity))
        if variety:
            max_date_query = max_date_query.where(func.lower(MarketPrice.variety) == variety.lower().strip())

        max_date_res = await self.session.execute(max_date_query)
        latest_date = max_date_res.scalar()

        if not latest_date:
            return {
                "state": state,
                "district": district,
                "commodity": commodity or "Paddy (Dhan)",
                "variety": variety,
                "days_requested": days,
                "days_with_data": 0,
                "start_date": None,
                "end_date": None,
                "total_observations": 0,
                "start_modal_price": None,
                "end_modal_price": None,
                "absolute_change": None,
                "percentage_change": None,
                "trend_direction": "insufficient_data",
                "currency": "INR",
                "unit": "Quintal",
                "daily_trends": [],
            }

        start_boundary = latest_date - timedelta(days=days)

        trend_query = (
            select(
                MarketPrice.price_date.label("date"),
                func.avg(MarketPrice.modal_price).label("avg_modal_price"),
                func.min(MarketPrice.modal_price).label("min_modal_price"),
                func.max(MarketPrice.modal_price).label("max_modal_price"),
                func.count(MarketPrice.id).label("observation_count"),
            )
            .where(MarketPrice.price_date >= start_boundary)
        )
        if state:
            trend_query = trend_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if district:
            trend_query = trend_query.where(func.lower(MarketPrice.district) == district.lower().strip())
        if commodity:
            trend_query = trend_query.where(_match_commodity(commodity))
        if variety:
            trend_query = trend_query.where(func.lower(MarketPrice.variety) == variety.lower().strip())

        trend_query = trend_query.group_by(MarketPrice.price_date).order_by(MarketPrice.price_date.asc())
        trend_res = await self.session.execute(trend_query)
        rows = trend_res.all()

        daily_points = [
            {
                "date": r.date,
                "avg_modal_price": float(round(r.avg_modal_price, 2)),
                "min_modal_price": float(r.min_modal_price),
                "max_modal_price": float(r.max_modal_price),
                "observation_count": r.observation_count,
                "currency": "INR",
                "unit": "Quintal",
            }
            for r in rows
        ]

        total_obs = sum(p["observation_count"] for p in daily_points)
        days_with_data = len(daily_points)

        if days_with_data >= 2:
            start_price = daily_points[0]["avg_modal_price"]
            end_price = daily_points[-1]["avg_modal_price"]
            abs_change = round(end_price - start_price, 2)
            pct_change = round((abs_change / start_price) * 100, 2) if start_price > 0 else 0.0

            if abs_change > 10.0:
                trend_dir = "up"
            elif abs_change < -10.0:
                trend_dir = "down"
            else:
                trend_dir = "stable"
        elif days_with_data == 1:
            start_price = daily_points[0]["avg_modal_price"]
            end_price = start_price
            abs_change = None
            pct_change = None
            trend_dir = "insufficient_data"
        else:
            start_price = None
            end_price = None
            abs_change = None
            pct_change = None
            trend_dir = "insufficient_data"

        return {
            "state": state,
            "district": district,
            "commodity": commodity or "Paddy (Dhan)",
            "variety": variety,
            "days_requested": days,
            "days_with_data": days_with_data,
            "start_date": daily_points[0]["date"] if daily_points else None,
            "end_date": daily_points[-1]["date"] if daily_points else None,
            "total_observations": total_obs,
            "start_modal_price": start_price,
            "end_modal_price": end_price,
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "trend_direction": trend_dir,
            "currency": "INR",
            "unit": "Quintal",
            "daily_trends": daily_points,
        }

    async def get_district_benchmarks(
        self,
        days: int = 30,
        state: Optional[str] = None,
        commodity: Optional[str] = None,
        variety: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes district-level price benchmarks and differentials relative to overall state average.
        """
        max_date_query = select(func.max(MarketPrice.price_date))
        if state:
            max_date_query = max_date_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if commodity:
            max_date_query = max_date_query.where(_match_commodity(commodity))
        if variety:
            max_date_query = max_date_query.where(func.lower(MarketPrice.variety) == variety.lower().strip())

        max_date_res = await self.session.execute(max_date_query)
        latest_date = max_date_res.scalar()

        if not latest_date:
            return {
                "state": state,
                "commodity": commodity or "Paddy (Dhan)",
                "days_analyzed": days,
                "state_avg_modal_price": None,
                "highest_price_district": None,
                "lowest_price_district": None,
                "price_spread": None,
                "districts": [],
            }

        start_boundary = latest_date - timedelta(days=days)

        # Overall state average
        state_avg_q = select(func.avg(MarketPrice.modal_price)).where(MarketPrice.price_date >= start_boundary)
        if state:
            state_avg_q = state_avg_q.where(func.lower(MarketPrice.state) == state.lower().strip())
        if commodity:
            state_avg_q = state_avg_q.where(_match_commodity(commodity))
        if variety:
            state_avg_q = state_avg_q.where(func.lower(MarketPrice.variety) == variety.lower().strip())
        state_avg_val = (await self.session.execute(state_avg_q)).scalar()
        state_avg = float(round(state_avg_val, 2)) if state_avg_val is not None else None

        # District breakdown
        d_query = (
            select(
                MarketPrice.district.label("district"),
                func.avg(MarketPrice.modal_price).label("avg_modal_price"),
                func.min(MarketPrice.modal_price).label("min_modal_price"),
                func.max(MarketPrice.modal_price).label("max_modal_price"),
                func.count(MarketPrice.id).label("observation_count"),
                func.count(func.distinct(MarketPrice.market_name)).label("market_count"),
                func.max(MarketPrice.price_date).label("latest_price_date"),
            )
            .where(MarketPrice.price_date >= start_boundary)
        )
        if state:
            d_query = d_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if commodity:
            d_query = d_query.where(_match_commodity(commodity))
        if variety:
            d_query = d_query.where(func.lower(MarketPrice.variety) == variety.lower().strip())

        d_query = d_query.group_by(MarketPrice.district).order_by(desc("avg_modal_price"))
        d_rows = (await self.session.execute(d_query)).all()

        benchmarks = []
        for r in d_rows:
            avg_m = float(round(r.avg_modal_price, 2))
            diff = round(avg_m - state_avg, 2) if state_avg is not None else None
            pct_diff = round((diff / state_avg) * 100, 2) if state_avg and state_avg > 0 else None
            benchmarks.append({
                "district": r.district,
                "avg_modal_price": avg_m,
                "min_modal_price": float(r.min_modal_price),
                "max_modal_price": float(r.max_modal_price),
                "difference_from_state_avg": diff,
                "percentage_diff_from_state_avg": pct_diff,
                "observation_count": r.observation_count,
                "market_count": r.market_count,
                "latest_price_date": r.latest_price_date,
                "currency": "INR",
                "unit": "Quintal",
            })

        highest_dist = benchmarks[0]["district"] if benchmarks else None
        lowest_dist = benchmarks[-1]["district"] if benchmarks else None
        spread = round(benchmarks[0]["avg_modal_price"] - benchmarks[-1]["avg_modal_price"], 2) if len(benchmarks) >= 2 else 0.0

        return {
            "state": state,
            "commodity": commodity or "Paddy (Dhan)",
            "days_analyzed": days,
            "state_avg_modal_price": state_avg,
            "highest_price_district": highest_dist,
            "lowest_price_district": lowest_dist,
            "price_spread": spread,
            "districts": benchmarks,
        }

    async def get_variety_benchmarks(
        self,
        days: int = 30,
        state: Optional[str] = None,
        district: Optional[str] = None,
        commodity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes variety-level modal price benchmarks, identifying premium and standard cultivar brackets.
        """
        max_date_query = select(func.max(MarketPrice.price_date))
        if state:
            max_date_query = max_date_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if district:
            max_date_query = max_date_query.where(func.lower(MarketPrice.district) == district.lower().strip())
        if commodity:
            max_date_query = max_date_query.where(_match_commodity(commodity))

        max_date_res = await self.session.execute(max_date_query)
        latest_date = max_date_res.scalar()

        if not latest_date:
            return {
                "state": state,
                "commodity": commodity or "Paddy (Dhan)",
                "district": district,
                "days_analyzed": days,
                "premium_variety": None,
                "standard_variety": None,
                "varieties": [],
            }

        start_boundary = latest_date - timedelta(days=days)

        v_query = (
            select(
                MarketPrice.variety.label("variety"),
                func.avg(MarketPrice.modal_price).label("avg_modal_price"),
                func.min(MarketPrice.modal_price).label("min_modal_price"),
                func.max(MarketPrice.modal_price).label("max_modal_price"),
                func.count(MarketPrice.id).label("observation_count"),
                func.count(func.distinct(MarketPrice.district)).label("district_count"),
                func.max(MarketPrice.price_date).label("latest_price_date"),
            )
            .where(MarketPrice.price_date >= start_boundary)
        )
        if state:
            v_query = v_query.where(func.lower(MarketPrice.state) == state.lower().strip())
        if district:
            v_query = v_query.where(func.lower(MarketPrice.district) == district.lower().strip())
        if commodity:
            v_query = v_query.where(_match_commodity(commodity))

        v_query = v_query.group_by(MarketPrice.variety).order_by(desc("avg_modal_price"))
        v_rows = (await self.session.execute(v_query)).all()

        benchmarks = [
            {
                "variety": r.variety,
                "avg_modal_price": float(round(r.avg_modal_price, 2)),
                "min_modal_price": float(r.min_modal_price),
                "max_modal_price": float(r.max_modal_price),
                "observation_count": r.observation_count,
                "district_count": r.district_count,
                "latest_price_date": r.latest_price_date,
                "currency": "INR",
                "unit": "Quintal",
            }
            for r in v_rows
        ]

        premium = benchmarks[0]["variety"] if benchmarks else None

        # Standard variety: "Common" if present, else cultivar with highest observation volume
        common_found = next((b["variety"] for b in benchmarks if b["variety"].strip().lower() == "common"), None)
        if common_found:
            standard = common_found
        elif benchmarks:
            most_observed = max(benchmarks, key=lambda x: x["observation_count"])
            standard = most_observed["variety"]
        else:
            standard = None

        return {
            "state": state,
            "commodity": commodity or "Paddy (Dhan)",
            "district": district,
            "days_analyzed": days,
            "premium_variety": premium,
            "standard_variety": standard,
            "varieties": benchmarks,
        }



class BuyerRepository(BaseRepository[Buyer]):
    """
    Repository for verified wholesale grain buyers, millers, and procurement agencies.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Buyer, session)

    async def list_buyers(
        self,
        district: Optional[str] = None,
        buyer_type: Optional[str] = None,
        state: Optional[str] = None,
        verification_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[Buyer], int]:
        safe_limit = min(max(1, limit), 200)
        safe_skip = max(0, skip)

        query = select(Buyer).where(Buyer.is_active.is_(True))
        count_query = select(func.count(Buyer.id)).where(Buyer.is_active.is_(True))

        if state:
            query = query.where(func.lower(Buyer.state) == state.lower().strip())
            count_query = count_query.where(func.lower(Buyer.state) == state.lower().strip())
        if district:
            query = query.where(func.lower(Buyer.district) == district.lower().strip())
            count_query = count_query.where(func.lower(Buyer.district) == district.lower().strip())
        if buyer_type:
            query = query.where(Buyer.buyer_type == buyer_type.strip().lower())
            count_query = count_query.where(Buyer.buyer_type == buyer_type.strip().lower())
        if verification_status:
            query = query.where(Buyer.verification_status == verification_status.strip().lower())
            count_query = count_query.where(Buyer.verification_status == verification_status.strip().lower())

        query = query.order_by(Buyer.business_name.asc(), Buyer.id.asc()).offset(safe_skip).limit(safe_limit)

        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar() or 0

        res = await self.session.execute(query)
        records = res.scalars().all()

        return records, total_count

    async def list_nearby_buyers(
        self,
        farmer_lat: float,
        farmer_lon: float,
        radius_km: Optional[float] = None,
        district: Optional[str] = None,
        buyer_type: Optional[str] = None,
        state: Optional[str] = None,
        verification_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Tuple[Buyer, float]], int]:
        """
        Retrieves active buyers with verified non-null GPS coordinates, calculates great-circle
        distances using the Haversine formula, filters by search radius (if specified),
        and returns results ranked by distance ascending with deterministic tie-breaking.
        """
        safe_limit = min(max(1, limit), 200)
        safe_skip = max(0, skip)

        query = (
            select(Buyer)
            .where(
                Buyer.is_active.is_(True),
                Buyer.latitude.is_not(None),
                Buyer.longitude.is_not(None),
            )
        )

        if state:
            query = query.where(func.lower(Buyer.state) == state.lower().strip())
        if district:
            query = query.where(func.lower(Buyer.district) == district.lower().strip())
        if buyer_type:
            query = query.where(Buyer.buyer_type == buyer_type.strip().lower())
        if verification_status:
            query = query.where(Buyer.verification_status == verification_status.strip().lower())

        res = await self.session.execute(query)
        candidates = res.scalars().all()

        scored_buyers: List[Tuple[Buyer, float]] = []
        for b in candidates:
            if b.latitude is None or b.longitude is None:
                continue
            try:
                b_lat = float(b.latitude)
                b_lon = float(b.longitude)
                if not (-90.0 <= b_lat <= 90.0 and -180.0 <= b_lon <= 180.0):
                    continue
                dist = haversine_distance_km(farmer_lat, farmer_lon, b_lat, b_lon)
                if radius_km is not None and dist > radius_km:
                    continue
                scored_buyers.append((b, dist))
            except (ValueError, TypeError):
                continue

        # Sort by distance ascending, then business_name ascending, then ID ascending as deterministic tie-breaker
        scored_buyers.sort(key=lambda item: (item[1], item[0].business_name.lower(), str(item[0].id)))

        total_count = len(scored_buyers)
        paginated_items = scored_buyers[safe_skip : safe_skip + safe_limit]

        return paginated_items, total_count


class ReportRepository(BaseRepository[Report]):
    """
    Repository for compiled advisory dossiers and field diagnostic reports.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Report, session)

    async def get_by_prediction_id(
        self,
        prediction_id: uuid.UUID,
    ) -> Optional[Report]:
        """
        Retrieves the most recent report associated with a specific prediction ID.
        """
        stmt = (
            select(Report)
            .where(Report.prediction_id == prediction_id)
            .order_by(desc(Report.created_at), desc(Report.id))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_report(
        self,
        report_type: str,
        title: str,
        prediction_id: Optional[uuid.UUID] = None,
        field_id: Optional[uuid.UUID] = None,
        summary: Optional[str] = None,
        status: str = "completed",
        file_path: Optional[str] = None,
        file_format: str = "json",
        file_size_bytes: Optional[int] = None,
        report_metadata: Optional[Dict[str, Any]] = None,
        generated_by: str = "system",
        report_id: Optional[uuid.UUID] = None,
    ) -> Report:
        """
        Creates, validates, and persists a new compiled diagnostic report record.
        """
        valid_types = (
            "disease_diagnostic",
            "field_health_summary",
            "seasonal_advisory",
            "market_intelligence",
        )
        if report_type not in valid_types:
            raise ValueError(f"Invalid report_type '{report_type}': must be one of {valid_types}")

        valid_statuses = ("generating", "completed", "failed")
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}': must be one of {valid_statuses}")

        report = Report(
            id=report_id or uuid.uuid4(),
            field_id=field_id,
            prediction_id=prediction_id,
            report_type=report_type,
            title=title,
            summary=summary,
            status=status,
            file_path=file_path,
            file_format=file_format,
            file_size_bytes=file_size_bytes,
            report_metadata=report_metadata,
            generated_by=generated_by,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def list_reports(
        self,
        prediction_id: Optional[uuid.UUID] = None,
        field_id: Optional[uuid.UUID] = None,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[Report], int]:
        """
        Lists reports with safe pagination and optional filtering by prediction_id, field_id, report_type, and status.
        Ordered by created_at DESC.
        """
        safe_limit = min(max(1, limit), 200)
        safe_skip = max(0, skip)

        query = select(Report)
        count_query = select(func.count(Report.id))

        if prediction_id is not None:
            query = query.where(Report.prediction_id == prediction_id)
            count_query = count_query.where(Report.prediction_id == prediction_id)

        if field_id is not None:
            query = query.where(Report.field_id == field_id)
            count_query = count_query.where(Report.field_id == field_id)

        if report_type is not None and report_type.strip():
            query = query.where(Report.report_type == report_type.strip())
            count_query = count_query.where(Report.report_type == report_type.strip())

        if status is not None and status.strip():
            query = query.where(Report.status == status.strip())
            count_query = count_query.where(Report.status == status.strip())

        query = query.order_by(desc(Report.created_at), desc(Report.id)).offset(safe_skip).limit(safe_limit)

        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar() or 0

        res = await self.session.execute(query)
        records = res.scalars().all()

        return records, total_count

    async def list_reports_for_field(
        self,
        field_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[Report], int]:
        """Backward-compatible helper to list reports for a field."""
        return await self.list_reports(field_id=field_id, skip=skip, limit=limit)
