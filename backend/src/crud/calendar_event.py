"""
Calendar Event CRUD operations.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.base import CRUDBase
from src.models import CalendarEvent, EmailCategory
from src.schemas import CalendarEventCreate, CalendarEventUpdate


class CRUDCalendarEvent(CRUDBase):
    """CRUD for CalendarEvent model."""

    def __init__(self):
        super().__init__(CalendarEvent)

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CalendarEvent]:
        """Get calendar events for a user."""
        query = select(CalendarEvent).where(CalendarEvent.user_id == user_id).offset(
            skip
        ).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_user_and_range(
        self,
        db: AsyncSession,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """Get calendar events for user within date range."""
        query = select(CalendarEvent).where(CalendarEvent.user_id == user_id)
        if start_date:
            query = query.where(CalendarEvent.start_time >= start_date)
        if end_date:
            query = query.where(CalendarEvent.start_time <= end_date)
        query = query.order_by(CalendarEvent.start_time.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create_from_email(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        email_id: int,
        title: str,
        start_time: datetime,
        end_time: datetime,
        event_type: Optional[str] = None,
        location: Optional[str] = None,
    ) -> CalendarEvent:
        """Create calendar event from an email."""
        db_obj = CalendarEvent(
            user_id=user_id,
            email_id=email_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type or "Meeting",
            location=location,
            category=EmailCategory.MEETING,
            detected_from_email=True,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: CalendarEvent,
        obj_in=None,
        **kwargs,
    ) -> CalendarEvent:
        """Update calendar event from schema and/or kwargs."""
        return await super().update(db, db_obj, obj_in=obj_in, **kwargs)


calendar_event_crud = CRUDCalendarEvent()