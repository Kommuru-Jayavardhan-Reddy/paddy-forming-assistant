"""
Paddy Farming Assistant - Weather Repository (STEP 11F.8)
Handles asynchronous database operations and caching for Open-Meteo weather data.
"""

import logging
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Sequence
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.weather import WeatherRecord
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class WeatherRepository(BaseRepository[WeatherRecord]):
    """
    Asynchronous repository for real-time and forecasted atmospheric records.
    Provides optional non-intrusive database caching for genuine Open-Meteo observations.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(WeatherRecord, session)

    async def get_cached_current_weather(
        self,
        latitude: float,
        longitude: float,
        max_age_minutes: int = 30,
        coord_tolerance: float = 0.01,
    ) -> Optional[WeatherRecord]:
        """
        Retrieves recent cached 'current' weather observation for coordinates
        within the specified maximum age threshold and coordinate bounding box.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=max_age_minutes)

        lat_min = Decimal(str(round(latitude - coord_tolerance, 4)))
        lat_max = Decimal(str(round(latitude + coord_tolerance, 4)))
        lon_min = Decimal(str(round(longitude - coord_tolerance, 4)))
        lon_max = Decimal(str(round(longitude + coord_tolerance, 4)))

        stmt = (
            select(WeatherRecord)
            .where(
                and_(
                    WeatherRecord.record_type == "current",
                    WeatherRecord.latitude >= lat_min,
                    WeatherRecord.latitude <= lat_max,
                    WeatherRecord.longitude >= lon_min,
                    WeatherRecord.longitude <= lon_max,
                    WeatherRecord.retrieval_time >= cutoff,
                    WeatherRecord.temperature_c.isnot(None),
                    WeatherRecord.weather_code.isnot(None),
                )
            )
            .order_by(desc(WeatherRecord.retrieval_time))
            .limit(1)
        )

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_cached_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 7,
        max_age_hours: int = 3,
        coord_tolerance: float = 0.01,
    ) -> Sequence[WeatherRecord]:
        """
        Retrieves recent cached daily forecast records for coordinates
        within the specified maximum age threshold.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_age_hours)
        today = now.date()

        lat_min = Decimal(str(round(latitude - coord_tolerance, 4)))
        lat_max = Decimal(str(round(latitude + coord_tolerance, 4)))
        lon_min = Decimal(str(round(longitude - coord_tolerance, 4)))
        lon_max = Decimal(str(round(longitude + coord_tolerance, 4)))

        stmt = (
            select(WeatherRecord)
            .where(
                and_(
                    WeatherRecord.record_type == "forecast",
                    WeatherRecord.latitude >= lat_min,
                    WeatherRecord.latitude <= lat_max,
                    WeatherRecord.longitude >= lon_min,
                    WeatherRecord.longitude <= lon_max,
                    WeatherRecord.retrieval_time >= cutoff,
                    WeatherRecord.forecast_date >= today,
                )
            )
            .order_by(WeatherRecord.forecast_date.asc())
            .limit(forecast_days)
        )

        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def record_current_weather(
        self,
        latitude: float,
        longitude: float,
        temperature_c: Optional[float],
        relative_humidity_pct: Optional[float],
        precipitation_mm: Optional[float],
        rain_mm: Optional[float],
        wind_speed_kmh: Optional[float],
        weather_code: Optional[int],
        weather_condition: Optional[str],
        observation_time: Optional[datetime] = None,
        field_id: Optional[uuid.UUID] = None,
        provider: str = "Open-Meteo",
        timezone_str: str = "Asia/Kolkata",
    ) -> WeatherRecord:
        """
        Caches a genuine real-time current weather observation into PostgreSQL.
        """
        record = WeatherRecord(
            field_id=field_id,
            latitude=Decimal(str(round(latitude, 6))),
            longitude=Decimal(str(round(longitude, 6))),
            record_type="current",
            observation_time=observation_time or datetime.now(timezone.utc),
            retrieval_time=datetime.now(timezone.utc),
            temperature_c=Decimal(str(round(temperature_c, 2))) if temperature_c is not None else None,
            relative_humidity_pct=Decimal(str(round(relative_humidity_pct, 2))) if relative_humidity_pct is not None else None,
            precipitation_mm=Decimal(str(round(precipitation_mm, 2))) if precipitation_mm is not None else None,
            rain_mm=Decimal(str(round(rain_mm, 2))) if rain_mm is not None else None,
            wind_speed_kmh=Decimal(str(round(wind_speed_kmh, 2))) if wind_speed_kmh is not None else None,
            weather_code=weather_code,
            weather_condition=weather_condition,
            provider=provider,
            timezone=timezone_str,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def record_forecast_days(
        self,
        latitude: float,
        longitude: float,
        forecast_items: List[dict],
        field_id: Optional[uuid.UUID] = None,
        provider: str = "Open-Meteo",
        timezone_str: str = "Asia/Kolkata",
    ) -> List[WeatherRecord]:
        """
        Caches multi-day forecast daily summaries into PostgreSQL.
        """
        records = []
        retrieval_now = datetime.now(timezone.utc)
        lat_dec = Decimal(str(round(latitude, 6)))
        lon_dec = Decimal(str(round(longitude, 6)))

        for item in forecast_items:
            f_date = item.get("date")
            if isinstance(f_date, str):
                f_date = datetime.strptime(f_date, "%Y-%m-%d").date()

            temp_max = item.get("temperature_max")
            temp_min = item.get("temperature_min")
            precip = item.get("precipitation_sum")
            rain = item.get("rain_sum")
            wind_max = item.get("wind_speed_max")

            rec = WeatherRecord(
                field_id=field_id,
                latitude=lat_dec,
                longitude=lon_dec,
                record_type="forecast",
                forecast_date=f_date,
                retrieval_time=retrieval_now,
                temperature_max_c=Decimal(str(round(temp_max, 2))) if temp_max is not None else None,
                temperature_min_c=Decimal(str(round(temp_min, 2))) if temp_min is not None else None,
                precipitation_mm=Decimal(str(round(precip, 2))) if precip is not None else None,
                rain_mm=Decimal(str(round(rain, 2))) if rain is not None else None,
                wind_speed_max_kmh=Decimal(str(round(wind_max, 2))) if wind_max is not None else None,
                weather_code=item.get("weather_code"),
                weather_condition=item.get("weather_condition"),
                provider=provider,
                timezone=timezone_str,
            )
            self.session.add(rec)
            records.append(rec)

        await self.session.flush()
        return records
