"""
Gmail Synchronization Service for MailMind AI.
Fetches real Gmail inbox messages, handles automated token refresh,
runs AI categorization and smart draft suggestions on inbound emails,
and populates the database with real user email threads.
"""
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.ai import ai_engine, _build_smart_draft
from src.core.gmail import GmailClient, GmailReconnectionRequiredError, GmailAuthError
from src.core.security import decrypt_secret, encrypt_secret
from src.crud.connected_account import connected_account_crud
from src.crud.email import email_crud
from src.models import (
    AIAnalysisSentiment,
    ConnectedAccount,
    Email,
    EmailCategory,
    EmailUrgency,
    User,
)

logger = logging.getLogger("mailmind-ai.gmail_sync")


async def get_gmail_client_for_user(
    db: AsyncSession, user_id: int
) -> Optional[Tuple[GmailClient, ConnectedAccount]]:
    """
    Retrieve active ConnectedAccount for user, decrypt OAuth tokens,
    verify/refresh if expired, and return authenticated GmailClient.
    """
    gmail_acc = await connected_account_crud.get_by_user_and_provider(db, user_id, "gmail")
    if not gmail_acc or gmail_acc.status != "connected" or not gmail_acc.access_token_encrypted:
        return None

    try:
        raw_access = decrypt_secret(gmail_acc.access_token_encrypted)
        raw_refresh = (
            decrypt_secret(gmail_acc.refresh_token_encrypted)
            if gmail_acc.refresh_token_encrypted
            else None
        )
    except Exception as exc:
        logger.error("Failed to decrypt Gmail tokens for user %s: %s", user_id, exc)
        return None

    def _sync_on_refresh(new_token: str, new_expiry: Optional[datetime]):
        try:
            gmail_acc.access_token_encrypted = encrypt_secret(new_token)
            if new_expiry:
                gmail_acc.token_expires_at = new_expiry
            db.add(gmail_acc)
        except Exception as cb_err:
            logger.error("Failed in on_token_refresh callback: %s", cb_err)

    client = GmailClient(
        access_token=raw_access,
        refresh_token=raw_refresh,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        token_expires_at=gmail_acc.token_expires_at,
        on_token_refresh=_sync_on_refresh,
    )

    # Check and handle automatic token refresh
    try:
        new_token = client.ensure_valid_token()
        if new_token:
            gmail_acc.access_token_encrypted = encrypt_secret(new_token)
            if client.creds.expiry:
                exp = client.creds.expiry
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                gmail_acc.token_expires_at = exp
            db.add(gmail_acc)
            await db.commit()
            await db.refresh(gmail_acc)
    except GmailReconnectionRequiredError as exc:
        logger.warning("Gmail refresh token invalid or revoked for user %s: %s", user_id, exc)
        gmail_acc.status = "error"
        db.add(gmail_acc)
        await db.commit()
        return None
    except Exception as exc:
        logger.warning("Error verifying token validity: %s", exc)

    return client, gmail_acc


def _heuristic_analyze_email(subject: str, body: str, sender_email: str) -> Dict[str, Any]:
    """Fast, reliable initial classification and key takeaways for synced messages."""
    subj_lower = (subject or "").lower()
    body_lower = (body or "").lower()
    sender_lower = (sender_email or "").lower()

    # Category determination
    category = EmailCategory.WORK
    if any(k in subj_lower or k in body_lower for k in ["invoice", "payment", "bank", "receipt", "transfer", "salary", "billing"]):
        category = EmailCategory.FINANCE
    elif any(k in subj_lower or k in body_lower for k in ["project", "client", "proposal", "contract", "quote", "inquiry"]):
        category = EmailCategory.CLIENT
    elif any(k in subj_lower or k in body_lower for k in ["college", "university", "assignment", "exam", "syllabus", "student"]):
        category = EmailCategory.COLLEGE
    elif any(k in subj_lower or k in body_lower for k in ["security", "password", "sign-in", "verification", "2fa", "alert"]):
        category = EmailCategory.SECURITY
    elif any(k in subj_lower or k in body_lower for k in ["job", "interview", "resume", "hiring", "career", "offer"]):
        category = EmailCategory.CAREER
    elif any(k in subj_lower or k in body_lower for k in ["meeting", "calendar", "reschedule", "zoom", "google meet"]):
        category = EmailCategory.MEETING
    elif any(k in subj_lower or k in body_lower for k in ["sale", "discount", "offer", "newsletter", "unsubscribe"]):
        category = EmailCategory.PROMOTIONS

    # Urgency determination
    urgency = EmailUrgency.LOW
    if any(k in subj_lower or k in body_lower for k in ["urgent", "asap", "immediate", "emergency", "deadline today"]):
        urgency = EmailUrgency.URGENT
    elif any(k in subj_lower for k in ["important", "action required", "priority", "deadline"]):
        urgency = EmailUrgency.HIGH
    elif "?" in body_lower or any(k in subj_lower for k in ["update", "review", "feedback"]):
        urgency = EmailUrgency.MEDIUM

    # Requires reply detection
    requires_reply = (
        ("?" in body_lower or any(k in body_lower for k in ["let me know", "please reply", "can you", "could you", "confirm", "available"]))
        and category not in (EmailCategory.PROMOTIONS, EmailCategory.SECURITY)
        and "no-reply" not in sender_lower
        and "noreply" not in sender_lower
    )

    # Key points extraction
    key_points = []
    lines = [l.strip() for l in body.splitlines() if len(l.strip()) > 15]
    if lines:
        key_points.append(lines[0][:120])
    if len(lines) > 1:
        key_points.append(lines[1][:120])
    if not key_points:
        key_points.append(f"Subject: {subject[:100]}")

    # Generate initial suggested reply preview
    suggested_reply = _build_smart_draft(subject, body, "professional") if requires_reply else None

    return {
        "category": category,
        "urgency": urgency,
        "requires_reply": requires_reply,
        "ai_confidence": 92 if requires_reply else 85,
        "ai_category": category.value,
        "ai_priority": "High" if urgency in (EmailUrgency.HIGH, EmailUrgency.URGENT) else "Normal",
        "ai_sentiment": AIAnalysisSentiment.NEUTRAL,
        "ai_key_points": key_points,
        "ai_suggested_reply": suggested_reply,
    }


async def sync_user_gmail_inbox(
    db: AsyncSession,
    user: User,
    max_results: int = 25,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Synchronize inbox messages from Google Gmail API into local database.
    Does not duplicate existing messages by message_id.
    """
    client_tuple = await get_gmail_client_for_user(db, user.id)
    if not client_tuple:
        gmail_acc = await connected_account_crud.get_by_user_and_provider(db, user.id, "gmail")
        if gmail_acc and gmail_acc.status == "error":
            return {
                "synced": False,
                "connected": False,
                "reconnect_required": True,
                "new_count": 0,
                "error": "reconnect_required",
                "message": "Gmail authorization expired or was revoked. Please reconnect your Gmail account in Settings.",
            }
        return {
            "synced": False,
            "connected": False,
            "reconnect_required": False,
            "new_count": 0,
            "message": "Gmail is not connected.",
        }

    client, account = client_tuple

    # Throttle non-forced syncs if synced within the last 45 seconds
    if not force and account.last_sync:
        elapsed = (datetime.now(timezone.utc) - account.last_sync.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < 45:
            return {
                "synced": True,
                "connected": True,
                "new_count": 0,
                "last_sync": account.last_sync.isoformat(),
                "message": "Inbox is up to date.",
            }

    try:
        messages = client.list_messages(user_id="me", max_results=max_results)
    except GmailReconnectionRequiredError as exc:
        logger.warning("Gmail reconnection required for user %s: %s", user.id, exc)
        account.status = "error"
        db.add(account)
        await db.commit()
        return {
            "synced": False,
            "connected": False,
            "reconnect_required": True,
            "new_count": 0,
            "error": "reconnect_required",
            "message": "Gmail authorization expired or was revoked. Please reconnect your Gmail account in Settings.",
        }
    except Exception as exc:
        logger.error("Failed to list Gmail messages for user %s: %s", user.id, exc)
        return {
            "synced": False,
            "connected": True,
            "new_count": 0,
            "error": str(exc),
            "message": f"Gmail API error: {str(exc)}",
        }

    new_messages_count = 0
    newly_added_emails = []

    for msg_meta in messages:
        msg_id = msg_meta.get("id")
        if not msg_id:
            continue

        # Check if already synced in database
        existing = await email_crud.get_by_message_id(db, msg_id)
        if existing:
            continue

        # Fetch message payload
        raw_msg = client.get_message(msg_id)
        if not raw_msg:
            continue

        parsed = client.parse_message_headers_and_body(raw_msg)
        analysis = _heuristic_analyze_email(
            parsed["subject"], parsed["body"], parsed["from_email"]
        )

        email_row = Email(
            user_id=user.id,
            message_id=parsed["message_id"],
            thread_id=parsed["thread_id"],
            from_name=parsed["from_name"],
            from_email=parsed["from_email"],
            to=parsed["to"],
            subject=parsed["subject"],
            preview=parsed["preview"],
            body=parsed["body"],
            received_at=parsed["received_at"],
            date=parsed["received_at"].date(),
            category=analysis["category"],
            urgency=analysis["urgency"],
            requires_reply=analysis["requires_reply"],
            is_read=parsed["is_read"],
            is_starred=parsed["is_starred"],
            is_important=parsed["is_important"],
            folder=parsed["folder"],
            has_attachments=parsed["has_attachments"],
            attachment_count=parsed["attachment_count"],
            ai_confidence=analysis["ai_confidence"],
            ai_category=analysis["ai_category"],
            ai_priority=analysis["ai_priority"],
            ai_sentiment=analysis["ai_sentiment"],
            ai_requires_reply=analysis["requires_reply"],
            ai_key_points=analysis["ai_key_points"],
            ai_suggested_reply=analysis["ai_suggested_reply"],
        )
        db.add(email_row)
        newly_added_emails.append(email_row)
        new_messages_count += 1

    account.last_sync = datetime.now(timezone.utc)
    db.add(account)
    await db.commit()

    # Run automated decision engine for newly synced emails if enabled
    if newly_added_emails:
        from src.core.automation_engine import automation_engine
        from src.models import UserPreferences
        pref_res = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user.id)
        )
        user_pref = pref_res.scalar_one_or_none()
        if user_pref and not user_pref.automation_paused:
            for new_em in newly_added_emails:
                try:
                    await automation_engine.process_and_record(
                        db=db,
                        user=user,
                        email=new_em,
                        gmail_client=client,
                        preferences=user_pref,
                    )
                except Exception as auto_err:
                    logger.warning("Automation error on email %s: %s", new_em.id, auto_err)

    logger.info("Synced %d new Gmail messages for user %s", new_messages_count, user.id)
    return {
        "synced": True,
        "connected": True,
        "new_count": new_messages_count,
        "last_sync": account.last_sync.isoformat(),
        "message": f"Synced {new_messages_count} new messages from Gmail.",
    }


async def get_or_sync_email_thread(
    db: AsyncSession, user: User, thread_id: str
) -> List[Email]:
    """Retrieve all messages belonging to a thread, syncing missing messages from Gmail if available."""
    # First, query local database
    stmt = (
        select(Email)
        .where(Email.user_id == user.id, Email.thread_id == thread_id)
        .order_by(Email.received_at.asc())
    )
    res = await db.execute(stmt)
    local_emails = list(res.scalars().all())

    # If thread is missing or has only 1 message, check if Gmail has more in this thread
    client_tuple = await get_gmail_client_for_user(db, user.id)
    if client_tuple:
        client, _ = client_tuple
        try:
            raw_thread = client.get_thread(thread_id)
            if raw_thread and "messages" in raw_thread:
                existing_ids = {e.message_id for e in local_emails if e.message_id}
                added_any = False
                for raw_msg in raw_thread["messages"]:
                    msg_id = raw_msg.get("id")
                    if msg_id and msg_id not in existing_ids:
                        parsed = client.parse_message_headers_and_body(raw_msg)
                        analysis = _heuristic_analyze_email(parsed["subject"], parsed["body"], parsed["from_email"])
                        email_row = Email(
                            user_id=user.id,
                            message_id=parsed["message_id"],
                            thread_id=parsed["thread_id"],
                            from_name=parsed["from_name"],
                            from_email=parsed["from_email"],
                            to=parsed["to"],
                            subject=parsed["subject"],
                            preview=parsed["preview"],
                            body=parsed["body"],
                            received_at=parsed["received_at"],
                            date=parsed["received_at"].date(),
                            category=analysis["category"],
                            urgency=analysis["urgency"],
                            requires_reply=analysis["requires_reply"],
                            is_read=parsed["is_read"],
                            is_starred=parsed["is_starred"],
                            is_important=parsed["is_important"],
                            folder=parsed["folder"],
                            has_attachments=parsed["has_attachments"],
                            attachment_count=parsed["attachment_count"],
                            ai_confidence=analysis["ai_confidence"],
                            ai_category=analysis["ai_category"],
                            ai_priority=analysis["ai_priority"],
                            ai_sentiment=analysis["ai_sentiment"],
                            ai_requires_reply=analysis["requires_reply"],
                            ai_key_points=analysis["ai_key_points"],
                            ai_suggested_reply=analysis["ai_suggested_reply"],
                        )
                        db.add(email_row)
                        added_any = True

                if added_any:
                    await db.commit()
                    # Re-query all emails in the thread
                    res2 = await db.execute(stmt)
                    local_emails = list(res2.scalars().all())
        except Exception as exc:
            logger.warning("Could not sync extra thread messages: %s", exc)

    return local_emails
