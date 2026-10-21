"""
Notifications endpoints for MailMind AI.
Manages user notifications, unread counts, and read status updates.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.config import settings
from src.crud.notification import notification_crud
from src.database import get_session
from src.models import Notification, NotificationType, User
from src.schemas import APIResponse

router = APIRouter()


@router.get("", response_model=APIResponse, summary="List Notifications")
async def list_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve notifications for the current user."""
    items = await notification_crud.get_multi_by_user(
        db, user_id=user.id, unread_only=unread_only, skip=skip, limit=limit
    )

    # In DEMO_MODE, if user has no notifications, seed default demo notifications
    if not items and settings.DEMO_MODE and skip == 0 and not unread_only:
        demo_notifs = [
            {
                "title": "AI Draft Ready for Review",
                "body": "AI prepared a professional reply for John Smith (Website Project Inquiry).",
                "type": NotificationType.AI_DRAFT,
                "is_read": False,
            },
            {
                "title": "Meeting Reminder",
                "body": "Team Meeting starts in 30 minutes via Google Meet.",
                "type": NotificationType.REMINDER,
                "is_read": False,
            },
            {
                "title": "Project Submission Deadline",
                "body": "Project report deadline is approaching on Oct 20.",
                "type": NotificationType.REMINDER,
                "is_read": True,
            },
        ]
        created_items = []
        for dn in demo_notifs:
            notif = await notification_crud.create(db, user_id=user.id, **dn)
            created_items.append(notif)
        await db.commit()
        items = created_items

    unread_count = await notification_crud.get_unread_count(db, user_id=user.id)

    formatted = [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "type": n.type.value if n.type else "ai_draft",
            "email_id": n.email_id,
            "is_read": n.is_read,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in items
    ]

    return APIResponse(
        success=True,
        data={
            "items": formatted,
            "total": len(formatted),
            "unread_count": unread_count,
        },
        message="Notifications retrieved successfully",
    )


@router.get("/unread-count", response_model=APIResponse, summary="Get Unread Notification Count")
async def get_unread_count(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get the unread notification count for the current user."""
    count = await notification_crud.get_unread_count(db, user_id=user.id)
    return APIResponse(success=True, data={"unread_count": count})


@router.patch("/{notif_id}/read", response_model=APIResponse, summary="Mark Notification as Read")
async def mark_notification_read(
    notif_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Mark a notification as read (with user ownership verification)."""
    notif = await notification_crud.get(db, notif_id)
    if not notif or notif.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    updated = await notification_crud.mark_as_read(db, notif)
    await db.commit()
    return APIResponse(
        success=True,
        data={"id": updated.id, "is_read": updated.is_read},
        message="Notification marked as read",
    )


@router.post("/mark-all-read", response_model=APIResponse, summary="Mark All Notifications as Read")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Mark all notifications as read for current user."""
    count = await notification_crud.mark_all_as_read(db, user_id=user.id)
    return APIResponse(
        success=True,
        data={"marked_read": count},
        message=f"{count} notifications marked as read",
    )
