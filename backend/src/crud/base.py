"""
Base CRUD operations for all models.
Provides standard create, read, update, delete operations.
"""
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import Base
from src.schemas import BaseSchema


class CRUDBase:
    """Base CRUD class with common operations."""

    def __init__(self, model: Type[Base]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[Base]:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None,
    ) -> List[Base]:
        """Get multiple records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        if order_by:
            query = query.order_by(order_by)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: Any = None, **kwargs) -> Base:
        """Create a new record from schema or kwargs."""
        data = {}
        if obj_in is not None:
            if hasattr(obj_in, 'model_dump'):
                data.update(obj_in.model_dump())
            elif hasattr(obj_in, 'dict'):
                data.update(obj_in.dict())
            elif isinstance(obj_in, dict):
                data.update(obj_in)
        data.update(kwargs)
        db_obj = self.model(**data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Base,
        obj_in: Any = None,
        **kwargs,
    ) -> Base:
        """Update an existing record from schema or kwargs."""
        update_data = {}
        if obj_in is not None:
            if hasattr(obj_in, 'model_dump'):
                update_data.update(obj_in.model_dump(exclude_unset=True))
            elif hasattr(obj_in, 'dict'):
                update_data.update(obj_in.dict(exclude_unset=True))
            elif isinstance(obj_in, dict):
                update_data.update(obj_in)
        update_data.update(kwargs)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, id: int) -> Optional[Base]:
        """Delete a record by ID."""
        db_obj = await self.get(db, id)
        if db_obj:
            await db.delete(db_obj)
            await db.flush()
        return db_obj

    async def delete(self, db: AsyncSession, id: int) -> Optional[Base]:
        """Alias for remove() used by API endpoints."""
        return await self.remove(db, id)