"""
Paddy Farming Assistant - Field Repository (STEP 11F.8)
Handles asynchronous CRUD operations for agricultural fields.
"""

import logging
import uuid
from typing import Optional, List, Tuple, Sequence, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.field import Field
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FieldRepository(BaseRepository[Field]):
    """
    Asynchronous repository for agricultural fields and parcels.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Field, session)

    async def get_by_external_id(self, external_field_id: str) -> Optional[Field]:
        """
        Retrieves a field by its external business identifier (e.g. 'FIELD_01').
        Performs case-insensitive lookup (e.g., 'field_01' matches 'FIELD_01').
        """
        if not external_field_id:
            return None
        norm_id = external_field_id.strip()
        stmt = select(Field).where(func.upper(Field.external_field_id) == norm_id.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, field_uuid: uuid.UUID) -> Optional[Field]:
        """
        Retrieves a field by its internal PostgreSQL UUID primary key.
        """
        return await self.get_by_id(field_uuid)

    async def list_fields(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        user_only: Optional[bool] = None,
    ) -> Tuple[Sequence[Field], int]:
        """
        Lists fields with pagination and total count.
        Optionally filters strictly by user_only (True for user-entered fields, False for catalog fields).
        """
        safe_limit = min(max(1, limit), 500)
        safe_skip = max(0, skip)

        query = select(Field)
        count_query = select(func.count(Field.id))

        if active_only:
            query = query.where(Field.is_active.is_(True))
            count_query = count_query.where(Field.is_active.is_(True))

        if user_only is True:
            query = query.where(Field.is_user_created.is_(True))
            count_query = count_query.where(Field.is_user_created.is_(True))
        elif user_only is False:
            query = query.where(Field.is_user_created.is_(False))
            count_query = count_query.where(Field.is_user_created.is_(False))

        query = query.order_by(Field.external_field_id.asc()).offset(safe_skip).limit(safe_limit)

        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar() or 0

        fields_res = await self.session.execute(query)
        fields = fields_res.scalars().all()

        return fields, total_count

    async def create_field(
        self,
        external_field_id: str,
        latitude: float,
        longitude: float,
        clean_field_id: Optional[str] = None,
        field_name: Optional[str] = None,
        area_hectares: Optional[float] = None,
        crop_variety: Optional[str] = None,
        is_active: bool = True,
        is_user_created: bool = True,
    ) -> Field:
        """
        Creates and persists a new Field entity within a transaction.
        """
        field = Field(
            external_field_id=external_field_id.strip(),
            clean_field_id=clean_field_id.strip() if clean_field_id else None,
            field_name=field_name.strip() if field_name else f"Paddy Field {external_field_id.replace('FIELD_', '')}",
            latitude=latitude,
            longitude=longitude,
            area_hectares=area_hectares,
            crop_variety=crop_variety,
            is_active=is_active,
            is_user_created=is_user_created,
        )
        self.session.add(field)
        await self.session.flush()
        return field
