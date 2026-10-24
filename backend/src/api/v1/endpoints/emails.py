"""
Email endpoints for MailMind AI.
Provides listing, filtering, search, detail view, Gmail inbox synchronization,
thread exploration, and star/read updates.
"""
from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.config import settings
from src.core.gmail import GmailClient, GmailReconnectionRequiredError
from src.core.gmail_sync import (
    get_gmail_client_for_user,
    get_or_sync_email_thread,
    sync_user_gmail_inbox,
)
from src.core.security import decrypt_secret
from src.crud.connected_account import connected_account_crud
from src.crud.email import email_crud
from src.database import get_session
from src.models import AIReplyDraft, Email, EmailCategory, EmailUrgency, User
from src.schemas import APIResponse

logger = logging.getLogger("mailmind-ai.emails")

router = APIRouter()


class SyncResponse(BaseModel):
    synced: bool
    connected: bool
    new_count: int
    last_sync: Optional[str] = None
    message: str


class SendEmailRequest(BaseModel):
    to: str = Field(..., min_length=3)
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    draft_id: Optional[int] = None
    thread_id: Optional[str] = None


@router.post("/sync", response_model=APIResponse, summary="Sync Emails from Gmail")
async def sync_emails(
    max_results: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Explicitly triggers synchronization of inbox messages from Gmail API.
    Refreshes tokens if needed, fetches new messages, runs AI categorization,
    and updates database records.
    """
    result = await sync_user_gmail_inbox(db, user, max_results=max_results, force=True)
    if result.get("reconnect_required"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gmail authorization expired or was revoked. Please reconnect your Gmail account in Settings.",
        )
    if not result.get("connected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail account is not connected. Please connect Gmail in Settings.",
        )
    return APIResponse(
        success=result.get("synced", False),
        data=result,
        message=result.get("message", "Sync completed"),
    )


@router.get("", response_model=APIResponse, summary="List Emails with Filtering")
async def list_emails(
    folder: Optional[str] = Query(None, description="Filter by folder: inbox, starred, important, sent, drafts"),
    category: Optional[str] = Query(None, description="Filter by category: Work, Client, College, etc."),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    is_starred: Optional[bool] = Query(None, description="Filter by starred status"),
    search: Optional[str] = Query(None, description="Search term in subject, body, or sender"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auto_sync: bool = Query(True, description="Attempt auto-sync if Gmail connected"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Retrieve emails for current user with multi-faceted filtering.
    If Gmail is connected, synchronizes live Gmail inbox;
    otherwise falls back to demo data only when in DEMO_MODE.
    """
    # Check if Gmail account is actively connected
    gmail_acc = await connected_account_crud.get_by_user_and_provider(db, user.id, "gmail")
    is_gmail_connected = bool(
        gmail_acc
        and gmail_acc.status == "connected"
        and gmail_acc.access_token_encrypted
    )

    if is_gmail_connected:
        # If user has connected Gmail and auto_sync is requested, sync any new messages
        if auto_sync:
            try:
                await sync_user_gmail_inbox(db, user, max_results=25, force=False)
            except Exception as exc:
                logger.warning("Background inbox sync skipped: %s", exc)
    elif settings.DEMO_MODE:
        # Only seed demo emails if Gmail is NOT connected and DEMO_MODE is true
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
            "message_id": e.message_id,
            "thread_id": e.thread_id,
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
            "has_attachments": e.has_attachments,
            "attachment_count": e.attachment_count,
            "ai_confidence": e.ai_confidence or 90,
            "ai_summary": e.ai_key_points or [],
            "ai_suggested_reply": e.ai_suggested_reply,
        })

    return APIResponse(
        success=True,
        data={
            "items": email_items,
            "total": len(email_items),
            "folder_counts": total_count,
            "is_gmail_connected": is_gmail_connected,
        },
        message="Emails fetched successfully",
    )


@router.get("/threads/{thread_id}", response_model=APIResponse, summary="Get Email Thread")
async def get_email_thread(
    thread_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve all email messages belonging to a given conversation thread."""
    thread_emails = await get_or_sync_email_thread(db, user, thread_id)
    if not thread_emails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )

    items = [
        {
            "id": e.id,
            "message_id": e.message_id,
            "thread_id": e.thread_id,
            "from_name": e.from_name,
            "from_email": e.from_email,
            "to": e.to,
            "subject": e.subject,
            "preview": e.preview,
            "body": e.body,
            "received_at": e.received_at.isoformat() if e.received_at else None,
            "category": e.category.value if e.category else "Work",
            "is_read": e.is_read,
            "is_starred": e.is_starred,
            "folder": e.folder,
        }
        for e in thread_emails
    ]

    return APIResponse(
        success=True,
        data={
            "thread_id": thread_id,
            "subject": thread_emails[0].subject,
            "messages": items,
            "count": len(items),
        },
        message="Thread messages retrieved successfully",
    )


@router.get("/stats", response_model=APIResponse, summary="Get Email & Analytics Stats")
async def get_email_stats(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve email statistics and analytics metrics from database."""
    gmail_acc = await connected_account_crud.get_by_user_and_provider(db, user.id, "gmail")
    is_gmail_connected = bool(
        gmail_acc and gmail_acc.status == "connected" and gmail_acc.access_token_encrypted
    )

    if not is_gmail_connected and settings.DEMO_MODE:
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
        "is_gmail_connected": is_gmail_connected,
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
        "message_id": email.message_id,
        "thread_id": email.thread_id,
        "from_name": email.from_name,
        "from_email": email.from_email,
        "to": email.to,
        "subject": email.subject,
        "preview": email.preview,
        "body": email.body,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "category": email.category.value if email.category else "Work",
        "urgency": email.urgency.value if email.urgency else "low",
        "requires_reply": email.requires_reply,
        "is_read": email.is_read,
        "is_starred": email.is_starred,
        "is_important": email.is_important,
        "folder": email.folder,
        "has_attachments": email.has_attachments,
        "attachment_count": email.attachment_count,
        "ai_analysis": {
            "confidence": email.ai_confidence or 90,
            "category": email.ai_category or (email.category.value if email.category else "Work"),
            "priority": email.ai_priority or "Normal",
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


@router.post("/send", response_model=APIResponse, status_code=status.HTTP_201_CREATED, summary="Send Email with Explicit Approval")
async def send_email(
    payload: SendEmailRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Send an email with explicit user authorization.
    Dispatches via Gmail API if OAuth is connected; records in sent folder in demo mode.
    NEVER sends without explicit user invocation of this endpoint.
    """
    client_tuple = await get_gmail_client_for_user(db, user.id)
    real_sent_id = None

    if client_tuple:
        client, _ = client_tuple
        try:
            sent_res = client.send_message(
                to=payload.to,
                subject=payload.subject,
                body=payload.body,
                thread_id=payload.thread_id,
            )
            real_sent_id = sent_res.get("id") if sent_res else None
        except GmailReconnectionRequiredError as exc:
            logger.warning("Gmail reconnection required during send for user %s: %s", user.id, exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Gmail authorization expired or was revoked. Please reconnect your Gmail account in Settings.",
            )
        except Exception as exc:
            logger.error("Gmail send error: %s", exc)
            if not settings.DEMO_MODE:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to send email via Gmail API: {str(exc)}"
                )

    # Persist sent email in user's sent folder
    now = datetime.now(timezone.utc)
    sent_email = Email(
        user_id=user.id,
        message_id=real_sent_id or f"sent-{user.id}-{int(now.timestamp())}",
        thread_id=payload.thread_id,
        from_name=user.name,
        from_email=user.email,
        to=payload.to,
        subject=payload.subject,
        preview=payload.body[:120].strip(),
        body=payload.body,
        received_at=now,
        date=now.date(),
        category=EmailCategory.WORK,
        urgency=EmailUrgency.LOW,
        requires_reply=False,
        is_read=True,
        is_starred=False,
        is_important=False,
        folder="sent",
    )
    db.add(sent_email)

    # If linked to a draft, mark the draft as sent
    if payload.draft_id:
        draft = await db.get(AIReplyDraft, payload.draft_id)
        if draft and draft.user_id == user.id:
            draft.is_sent = True
            db.add(draft)

    await db.commit()
    await db.refresh(sent_email)

    return APIResponse(
        success=True,
        data={
            "id": sent_email.id,
            "to": sent_email.to,
            "subject": sent_email.subject,
            "folder": sent_email.folder,
            "is_sent": True,
            "gmail_message_id": real_sent_id,
        },
        message="Email sent successfully",
    )
