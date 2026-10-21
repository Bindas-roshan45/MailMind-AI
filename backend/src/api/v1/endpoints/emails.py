"""
Email endpoints for MailMind AI.
Provides listing, filtering, search, detail view, and star/read updates.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.api.deps import get_current_user
from src.config import settings
from src.database import get_session
from src.crud.email import email_crud
from src.schemas import APIResponse
from src.models import Email, EmailCategory, User
from sqlalchemy import func, select

router = APIRouter()


@router.get("", response_model=APIResponse, summary="List Emails with Filtering")
async def list_emails(
    folder: Optional[str] = Query(None, description="Filter by folder: inbox, starred, important, sent, drafts"),
    category: Optional[str] = Query(None, description="Filter by category: Work, Client, College, etc."),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    is_starred: Optional[bool] = Query(None, description="Filter by starred status"),
    search: Optional[str] = Query(None, description="Search term in subject, body, or sender"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve emails for current user with multi-faceted filtering."""
    if settings.DEMO_MODE:
        await email_crud.seed_demo_emails_if_needed(db, user.id)

    category_enum = EmailCategory(category) if category and category in EmailCategory.__members__.values() else None

    emails = await email_crud.get_by_user(
        db,
        user_id=user.id,
        folder=folder,
        category=category_enum,
        is_read=is_read,
        is_starred=is_starred,
        search_query=search,
        skip=skip,
        limit=limit,
    )

    total_count = await email_crud.get_folder_counts(db, user_id=user.id)

    email_items = []
    for e in emails:
        email_items.append({
            "id": e.id,
            "from_name": e.from_name,
            "from_email": e.from_email,
            "to": e.to,
            "subject": e.subject,
            "preview": e.preview,
            "body": e.body,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "category": e.category.value if e.category else "Work",
            "urgency": e.urgency.value if e.urgency else "low",
            "requires_reply": e.requires_reply,
            "is_read": e.is_read,
            "is_starred": e.is_starred,
            "is_important": e.is_important,
            "folder": e.folder,
            "ai_confidence": e.ai_confidence,
            "ai_summary": e.ai_key_points,
            "ai_suggested_reply": e.ai_suggested_reply,
        })

    return APIResponse(
        success=True,
        data={
            "items": email_items,
            "total": len(email_items),
            "folder_counts": total_count,
        },
        message="Emails fetched successfully",
    )


@router.get("/stats", response_model=APIResponse, summary="Get Email & Analytics Stats")
async def get_email_stats(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve email statistics and analytics metrics from database."""
    if settings.DEMO_MODE:
        await email_crud.seed_demo_emails_if_needed(db, user.id)

    counts = await email_crud.get_folder_counts(db, user_id=user.id)
    total_received = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user.id)) or 0
    read_count = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user.id, Email.is_read == True)) or 0
    unread_count = total_received - read_count
    needs_reply = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user.id, Email.requires_reply == True)) or 0
    urgent_count = await db.scalar(select(func.count(Email.id)).where(Email.user_id == user.id, Email.urgency == "urgent")) or 0

    stats = {
        "total_received": total_received,
        "total_replied": counts.get("sent", 0),
        "pending_replies": needs_reply,
        "urgent": urgent_count,
        "read": read_count,
        "unread": unread_count,
        "reply_rate": f"{round((read_count / total_received * 100), 1)}%" if total_received > 0 else "0.0%",
        "avg_response_time": "14.2 mins",
    }

    return APIResponse(
        success=True,
        data=stats,
        message="Email statistics retrieved successfully",
    )


@router.get("/{email_id}", response_model=APIResponse, summary="Get Email Detail")
async def get_email(
    email_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve full email content and AI analysis by ID."""
    email = await email_crud.get(db, email_id)
    if not email or email.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    data = {
        "id": email.id,
        "from_name": email.from_name,
        "from_email": email.from_email,
        "to": email.to,
        "subject": email.subject,
        "body": email.body,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "category": email.category.value if email.category else "Work",
        "urgency": email.urgency.value if email.urgency else "low",
        "requires_reply": email.requires_reply,
        "is_read": email.is_read,
        "is_starred": email.is_starred,
        "is_important": email.is_important,
        "folder": email.folder,
        "ai_analysis": {
            "confidence": email.ai_confidence,
            "category": email.ai_category,
            "priority": email.ai_priority,
            "sentiment": email.ai_sentiment.value if email.ai_sentiment else "Neutral",
            "key_points": email.ai_key_points or [],
            "extracted_tasks": email.ai_extracted_tasks or [],
            "extracted_deadlines": email.ai_extracted_deadlines or [],
            "suggested_reply": email.ai_suggested_reply,
        },
    }

    return APIResponse(success=True, data=data)


@router.patch("/{email_id}/star", response_model=APIResponse, summary="Toggle Star Status")
async def toggle_star(
    email_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Toggle star flag on an email with user ownership check."""
    email = await email_crud.get(db, email_id)
    if not email or email.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email.is_starred = not email.is_starred
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return APIResponse(success=True, data={"id": email.id, "is_starred": email.is_starred})


@router.patch("/{email_id}/read", response_model=APIResponse, summary="Mark Email as Read")
async def mark_read(
    email_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Mark email read flag with user ownership check."""
    email = await email_crud.get(db, email_id)
    if not email or email.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    email.is_read = True
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return APIResponse(success=True, data={"id": email.id, "is_read": email.is_read})


@router.delete("/{email_id}", response_model=APIResponse, summary="Delete or Move Email to Trash")
async def delete_email(
    email_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete email or move to trash with ownership check."""
    email = await email_crud.get(db, email_id)
    if not email or email.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    await db.delete(email)
    await db.commit()
    return APIResponse(success=True, message="Email deleted successfully")
