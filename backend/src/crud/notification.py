"""
Notification CRUD operations.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import Notification, NotificationType
from src.schemas import NotificationCreate, NotificationUpdate


class CRUDNotification(CRUDBase):
    """CRUD for Notification model."""

    def __init__(self):
        super().__init__(Notification)

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_unread_count(self, db: AsyncSession, user_id: int) -> int:
        """Get count of unread notifications."""
        result = await db.execute(
            select(func.count()).where(
                Notification.user_id == user_id, Notification.is_read == False
            )
        )
        return result.scalar_one()

    async def mark_as_read(self, db: AsyncSession, db_obj: Notification) -> Notification:
        """Mark notification as read."""
        db_obj.is_read = True
        db_obj.read_at = datetime.now(timezone.utc)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def mark_all_as_read(self, db: AsyncSession, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        result = await db.execute(
            select(Notification).where(Notification.user_id == user_id)
        )
        notifications = result.scalars().all()
        for notif in notifications:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
        await db.flush()
        await db.commit()
        return len(notifications)


notification_crud = CRUDNotification()