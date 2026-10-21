"""
User CRUD operations.
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import User
from src.schemas import UserCreate, UserUpdate


class CRUDUser(CRUDBase):
    """CRUD for User model."""

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_multi_with_counts(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get users with connected accounts count."""
        # Note: For Phase 1, we just return users. In Phase 2+ we'll add counts.
        return await self.get_multi(db, skip=skip, limit=limit)


user_crud = CRUDUser()