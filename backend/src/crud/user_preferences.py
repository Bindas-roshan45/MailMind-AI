"""
User Preferences CRUD operations.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import UserPreferences
from src.schemas import UserPreferencesCreate, UserPreferencesUpdate


class CRUDUserPreferences(CRUDBase):
    """CRUD for UserPreferences model."""

    def __init__(self):
        super().__init__(UserPreferences)

    async def get_by_user_id(
        self, db: AsyncSession, user_id: int
    ) -> Optional[UserPreferences]:
        """Get preferences by user ID."""
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()

    get_by_user = get_by_user_id

    async def create_or_update(
        self, db: AsyncSession, user_id: int, obj_in: UserPreferencesUpdate
    ) -> UserPreferences:
        """Create or update user preferences."""
        existing = await self.get_by_user_id(db, user_id)
        if existing:
            return await self.update(db, existing, obj_in)
        else:
            create_data = UserPreferencesCreate(user_id=user_id, **obj_in.model_dump())
            return await self.create(db, create_data)


user_preferences_crud = CRUDUserPreferences()