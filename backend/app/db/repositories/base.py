"""
Paddy Farming Assistant - Base Database Repository (STEP 11F.8)
Provides abstract base methods for asynchronous SQLAlchemy 2.x CRUD operations.
"""

import logging
from typing import Generic, TypeVar, Type, Optional, List, Any, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType]):
    """
    Base generic repository encapsulating common asynchronous CRUD operations
    with parameterized queries, safe pagination, and non-blocking execution.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id_val: Any) -> Optional[ModelType]:
        """
        Retrieves a single record by primary key.
        """
        stmt = select(self.model).where(self.model.id == id_val)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        """
        Lists records with safe pagination limits.
        """
        safe_limit = min(max(1, limit), 500)
        safe_skip = max(0, skip)
        stmt = select(self.model).offset(safe_skip).limit(safe_limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """
        Returns total record count for the model table.
        """
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
