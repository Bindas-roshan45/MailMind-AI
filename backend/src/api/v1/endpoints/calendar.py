"""
Calendar endpoints for MailMind AI.
Manages meeting sync and events extracted from email correspondence.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.api.deps import get_current_user
from src.database import get_session
from src.crud.calendar_event import calendar_event_crud
from src.schemas import CalendarEventCreate, APIResponse
from src.models import EmailCategory, User

router = APIRouter()


@router.get("/events", response_model=APIResponse, summary="List Calendar Events")
async def list_calendar_events(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve all calendar events for the user."""
    now = datetime.now(timezone.utc)
    events = await calendar_event_crud.get_by_user_and_range(
        db,
        user_id=user.id,
        start_date=now - timedelta(days=30),
        end_date=now + timedelta(days=60),
    )

    if not events:
        # Populate demo events matching the frontend UI state
        demo_events = [
            {
                "title": "Team Meeting",
                "start_time": now + timedelta(days=1, hours=2),
                "end_time": now + timedelta(days=1, hours=3),
                "category": EmailCategory.WORK,
                "event_type": "Google Meet",
                "meeting_url": "https://meet.google.com/abc-defg-hij",
                "detected_from_email": True,
            },
            {
                "title": "Website Project Inquiry Sync",
                "start_time": now + timedelta(days=2, hours=1),
                "end_time": now + timedelta(days=2, hours=1, minutes=30),
                "category": EmailCategory.CLIENT,
                "event_type": "Google Meet",
                "meeting_url": "https://meet.google.com/xyz-uvwx-rst",
                "detected_from_email": True,
            },
            {
                "title": "Q3 Strategy & Performance Review",
                "start_time": now + timedelta(days=4, hours=5),
                "end_time": now + timedelta(days=4, hours=6),
                "category": EmailCategory.WORK,
                "event_type": "Conference Room B",
                "detected_from_email": False,
            },
        ]
        for de in demo_events:
            ev = await calendar_event_crud.create(db, user_id=user.id, **de)
            events.append(ev)

    items = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "category": e.category.value if e.category else "Work",
            "event_type": e.event_type,
            "meeting_url": e.meeting_url,
            "detected_from_email": e.detected_from_email,
        }
        for e in events
    ]

    return APIResponse(success=True, data=items, message="Calendar events retrieved successfully")


@router.post("/events", response_model=APIResponse, status_code=status.HTTP_201_CREATED, summary="Add Calendar Event")
async def create_calendar_event(
    event_in: CalendarEventCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add a new calendar event."""
    ev = await calendar_event_crud.create(
        db,
        user_id=user.id,
        title=event_in.title,
        description=event_in.description,
        start_time=event_in.start_time,
        end_time=event_in.end_time,
        all_day=event_in.all_day,
        category=event_in.category,
        event_type=event_in.event_type,
        meeting_url=event_in.meeting_url,
        email_id=event_in.email_id,
        detected_from_email=event_in.detected_from_email,
    )
    return APIResponse(
        success=True,
        data={"id": ev.id, "title": ev.title},
        message="Event added to calendar",
    )


@router.delete("/events/{event_id}", response_model=APIResponse, summary="Delete Calendar Event")
async def delete_calendar_event(
    event_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete a calendar event with user ownership check."""
    ev = await calendar_event_crud.get(db, event_id)
    if not ev or ev.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await calendar_event_crud.delete(db, event_id)
    await db.commit()
    return APIResponse(success=True, message="Event deleted successfully")
