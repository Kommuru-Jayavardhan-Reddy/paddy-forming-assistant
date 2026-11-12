"""
Paddy Farming Assistant - Satellite Observation Repository (STEP 11F.8)
Handles asynchronous CRUD operations for Sentinel-2 satellite time-series records.
"""

import logging
import uuid
from datetime import date
from typing import Optional, List, Sequence, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.field import Field
from app.db.models.satellite import SatelliteObservation
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SatelliteRepository(BaseRepository[SatelliteObservation]):
    """
    Asynchronous repository for field satellite observations (NDVI, NDRE, GNDVI).
    """

    def __init__(self, session: AsyncSession):
        super().__init__(SatelliteObservation, session)

    async def get_observations_by_field_uuid(
        self,
        field_uuid: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        order_asc: bool = True,
    ) -> Sequence[SatelliteObservation]:
        """
        Retrieves satellite observations for a specific field UUID.
        Orders by time_step ASC and observation_date ASC.
        """
        stmt = select(SatelliteObservation).where(SatelliteObservation.field_id == field_uuid)

        if start_date:
            stmt = stmt.where(SatelliteObservation.observation_date >= start_date)
        if end_date:
            stmt = stmt.where(SatelliteObservation.observation_date <= end_date)

        if order_asc:
            stmt = stmt.order_by(
                SatelliteObservation.time_step.asc().nulls_last(),
                SatelliteObservation.observation_date.asc(),
            )
        else:
            stmt = stmt.order_by(
                SatelliteObservation.time_step.desc().nulls_last(),
                SatelliteObservation.observation_date.desc(),
            )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_observations_by_external_id(
        self,
        external_field_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        field_id: Optional[str] = None,
    ) -> Tuple[Optional[Field], Sequence[SatelliteObservation]]:
        """
        Resolves external field identifier (e.g. 'FIELD_01') to internal field entity
        and retrieves its chronological satellite observations.
        Returns (None, []) if the field does not exist.
        """
        target_id = external_field_id or field_id
        if not target_id:
            return None, []

        norm_id = target_id.strip()
        field_stmt = select(Field).where(func.upper(Field.external_field_id) == norm_id.upper())
        field_res = await self.session.execute(field_stmt)
        field = field_res.scalar_one_or_none()

        if not field:
            return None, []

        observations = await self.get_observations_by_field_uuid(
            field.id,
            start_date=start_date,
            end_date=end_date,
            order_asc=True,
        )
        return field, observations

    async def create_observation(
        self,
        field_id: uuid.UUID,
        observation_date: date,
        ndvi: float,
        ndre: float,
        gndvi: float,
        time_step: Optional[int] = None,
        cloud_coverage_pct: Optional[float] = None,
        is_interpolated: bool = False,
        data_source: str = "Sentinel-2 L2A",
        raw_metadata: Optional[dict] = None,
    ) -> SatelliteObservation:
        """
        Inserts and flushes a new satellite observation record within an async transaction.
        """
        obs = SatelliteObservation(
            field_id=field_id,
            time_step=time_step,
            observation_date=observation_date,
            ndvi=ndvi,
            ndre=ndre,
            gndvi=gndvi,
            cloud_coverage_pct=cloud_coverage_pct,
            is_interpolated=is_interpolated,
            data_source=data_source,
            raw_metadata=raw_metadata,
        )
        self.session.add(obs)
        await self.session.flush()
        return obs
