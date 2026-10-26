"""
Tests for real-time inbox synchronization, overlap prevention, duplicate prevention,
throttling, error handling, and multi-user isolation.
"""
import asyncio
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import encrypt_secret, create_access_token
from src.crud.connected_account import connected_account_crud
from src.crud.email import email_crud
from src.crud.user import user_crud
from src.models import (
    ConnectedAccount,
    Email,
    EmailCategory,
    EmailUrgency,
    User,
    UserPlan,
)
from src.core.gmail_sync import sync_user_gmail_inbox, _get_user_sync_lock
from src.core.gmail import GmailClient


@pytest.mark.asyncio
async def test_concurrent_sync_lock_prevents_overlap(client: AsyncClient, db_session: AsyncSession):
    """
    Test that concurrent sync attempts for the same user are protected by the per-user lock.
    If a sync is already running, the second request returns in_progress=True gracefully.
    """
    user = await user_crud.create(db_session, email="lock_test@gmail.com", name="Lock Test", plan=UserPlan.PRO)
    await connected_account_crud.create(
        db_session,
        user_id=user.id,
        email="lock_test@gmail.com",
        provider="gmail",
        status="connected",
        access_token_encrypted=encrypt_secret("test_tok"),
        refresh_token_encrypted=encrypt_secret("test_ref"),
    )

    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate a slow sync holding the user lock
    user_lock = await _get_user_sync_lock(user.id)
    await user_lock.acquire()

    try:
        # Call sync endpoint while lock is held
        res = await client.post("/api/v1/emails/sync?force=true", headers=headers)
        assert res.status_code == 200
        data = res.json().get("data", {})
        assert data.get("in_progress") is True
        assert "already in progress" in data.get("message", "").lower()
    finally:
        user_lock.release()


@pytest.mark.asyncio
async def test_non_forced_sync_throttles_within_interval(client: AsyncClient, db_session: AsyncSession):
    """
    Test that background polling with force=false respects the 45-second throttle.
    """
    user = await user_crud.create(db_session, email="throttle_test@gmail.com", name="Throttle Test", plan=UserPlan.PRO)
    acc = await connected_account_crud.create(
        db_session,
        user_id=user.id,
        email="throttle_test@gmail.com",
        provider="gmail",
        status="connected",
        access_token_encrypted=encrypt_secret("test_tok"),
        refresh_token_encrypted=encrypt_secret("test_ref"),
        last_sync=datetime.now(timezone.utc),  # Just synced
    )

    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Calling with force=false should return cached=True and not hit Gmail
    with patch("src.core.gmail_sync.GmailClient") as mock_client:
        res = await client.post("/api/v1/emails/sync?force=false", headers=headers)
        assert res.status_code == 200
        data = res.json().get("data", {})
        assert data.get("cached") is True
        mock_client.assert_not_called()

    # Calling with force=true bypasses the throttle
    mock_gmail_instance = MagicMock()
    mock_gmail_instance.ensure_valid_token.return_value = None
    mock_gmail_instance.list_messages.return_value = []

    with patch("src.core.gmail_sync.GmailClient", return_value=mock_gmail_instance):
        res_forced = await client.post("/api/v1/emails/sync?force=true", headers=headers)
        assert res_forced.status_code == 200
        data_forced = res_forced.json().get("data", {})
        assert data_forced.get("synced") is True
        assert data_forced.get("cached") is False


@pytest.mark.asyncio
async def test_duplicate_email_prevention_on_repeated_sync(client: AsyncClient, db_session: AsyncSession):
    """
    Test that syncing multiple times with overlapping Gmail messages does NOT
    produce duplicate emails in the database or trigger duplicate automations.
    """
    user = await user_crud.create(db_session, email="dedup_test@gmail.com", name="Dedup Test", plan=UserPlan.PRO)
    from src.models import UserPreferences
    pref = UserPreferences(user_id=user.id, automation_paused=False)
    db_session.add(pref)
    await db_session.commit()

    await connected_account_crud.create(
        db_session,
        user_id=user.id,
        email="dedup_test@gmail.com",
        provider="gmail",
        status="connected",
        access_token_encrypted=encrypt_secret("test_tok"),
        refresh_token_encrypted=encrypt_secret("test_ref"),
    )

    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    raw_msg1 = {
        "id": "gmail_msg_001",
        "threadId": "gmail_th_001",
        "internalDate": "1700000000000",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Here is invoice #1001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Invoice #1001"},
                {"name": "From", "value": "billing@vendor.com"},
                {"name": "To", "value": "dedup_test@gmail.com"},
                {"name": "Date", "value": "Mon, 26 Oct 2026 10:00:00 +0000"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": "SGVyZSBpcyBpbnZvaWNlICMxMDAx"}}
            ]
        }
    }

    raw_msg2 = {
        "id": "gmail_msg_002",
        "threadId": "gmail_th_002",
        "internalDate": "1700001000000",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Project Status Update",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Project Status Update"},
                {"name": "From", "value": "manager@company.com"},
                {"name": "To", "value": "dedup_test@gmail.com"},
                {"name": "Date", "value": "Mon, 26 Oct 2026 10:30:00 +0000"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": "UHJvamVjdCBzdGF0dXMgdXBkYXRl"}}
            ]
        }
    }

    mock_client = MagicMock()
    mock_client.ensure_valid_token.return_value = None
    mock_client.parse_message_headers_and_body = GmailClient.parse_message_headers_and_body

    # First sync returns msg1
    mock_client.list_messages.return_value = [{"id": "gmail_msg_001", "threadId": "gmail_th_001"}]
    mock_client.get_message.side_effect = lambda mid: raw_msg1 if mid == "gmail_msg_001" else raw_msg2

    with patch("src.core.gmail_sync.GmailClient", return_value=mock_client), \
         patch("src.core.automation_engine.automation_engine.process_and_record", new_callable=AsyncMock) as mock_auto:

        res1 = await client.post("/api/v1/emails/sync?force=true", headers=headers)
        assert res1.status_code == 200
        assert res1.json().get("data", {}).get("new_count") == 1
        assert mock_auto.call_count == 1

        # Second sync returns msg1 AND msg2
        mock_client.list_messages.return_value = [
            {"id": "gmail_msg_001", "threadId": "gmail_th_001"},
            {"id": "gmail_msg_002", "threadId": "gmail_th_002"},
        ]

        res2 = await client.post("/api/v1/emails/sync?force=true", headers=headers)
        assert res2.status_code == 200
        # Only 1 new message should have been added
        assert res2.json().get("data", {}).get("new_count") == 1
        # Automated decision engine should only run once for msg2, total calls = 2 (not 3)
        assert mock_auto.call_count == 2

    # Verify total emails in DB for user
    emails_in_db = await email_crud.get_multi_by_user(db_session, user_id=user.id, folder="inbox")
    assert len(emails_in_db) == 2
    msg_ids = [e.message_id for e in emails_in_db]
    assert "gmail_msg_001" in msg_ids
    assert "gmail_msg_002" in msg_ids


@pytest.mark.asyncio
async def test_multi_user_sync_isolation(client: AsyncClient, db_session: AsyncSession):
    """
    Test that sync locks and email datasets are completely isolated across different users.
    User A's sync does not block User B's sync lock, and User A's emails never appear for User B.
    """
    user1 = await user_crud.create(db_session, email="tenant_a@gmail.com", name="Tenant A", plan=UserPlan.PRO)
    user2 = await user_crud.create(db_session, email="tenant_b@gmail.com", name="Tenant B", plan=UserPlan.PRO)

    await connected_account_crud.create(
        db_session, user_id=user1.id, email="tenant_a@gmail.com", provider="gmail",
        status="connected", access_token_encrypted=encrypt_secret("tok1"),
        refresh_token_encrypted=encrypt_secret("ref1"),
    )
    await connected_account_crud.create(
        db_session, user_id=user2.id, email="tenant_b@gmail.com", provider="gmail",
        status="connected", access_token_encrypted=encrypt_secret("tok2"),
        refresh_token_encrypted=encrypt_secret("ref2"),
    )

    lock1 = await _get_user_sync_lock(user1.id)
    lock2 = await _get_user_sync_lock(user2.id)

    # Locks must be distinct objects
    assert lock1 is not lock2

    token1 = create_access_token(subject=user1.id, extra_claims={"email": user1.email})
    token2 = create_access_token(subject=user2.id, extra_claims={"email": user2.email})

    # Holding lock for user 1 does NOT block user 2
    await lock1.acquire()
    try:
        mock_client2 = MagicMock()
        mock_client2.ensure_valid_token.return_value = None
        mock_client2.parse_message_headers_and_body = GmailClient.parse_message_headers_and_body
        mock_client2.list_messages.return_value = [{"id": "user2_msg_001", "threadId": "user2_th_001"}]
        mock_client2.get_message.return_value = {
            "id": "user2_msg_001",
            "threadId": "user2_th_001",
            "internalDate": "1700000000000",
            "labelIds": ["INBOX"],
            "snippet": "User 2 confidential message",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "User 2 Confidential"},
                    {"name": "From", "value": "boss@tenantb.com"},
                    {"name": "To", "value": "tenant_b@gmail.com"},
                    {"name": "Date", "value": "Mon, 26 Oct 2026 11:00:00 +0000"},
                ],
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": "VXNlciAyIGNvbmZpZGVudGlhbA=="}}
                ]
            }
        }

        with patch("src.core.gmail_sync.GmailClient", return_value=mock_client2):
            res2 = await client.post("/api/v1/emails/sync?force=true", headers={"Authorization": f"Bearer {token2}"})
            assert res2.status_code == 200
            assert res2.json().get("data", {}).get("in_progress") is not True
            assert res2.json().get("data", {}).get("new_count") == 1
    finally:
        lock1.release()

    # Verify user 1 cannot see user 2's email
    u1_emails = await email_crud.get_multi_by_user(db_session, user_id=user1.id, folder="inbox")
    assert len(u1_emails) == 0

    u2_emails = await email_crud.get_multi_by_user(db_session, user_id=user2.id, folder="inbox")
    assert len(u2_emails) == 1
    assert u2_emails[0].message_id == "user2_msg_001"


@pytest.mark.asyncio
async def test_reconnection_required_marks_account_error(client: AsyncClient, db_session: AsyncSession):
    """
    Test that when Gmail raises a ReconnectionRequired error (e.g. invalid grant / revoked token),
    the account status is updated to 'error' and a 401 response is returned.
    """
    from src.core.gmail import GmailReconnectionRequiredError

    user = await user_crud.create(db_session, email="revoked_user@gmail.com", name="Revoked", plan=UserPlan.PRO)
    await connected_account_crud.create(
        db_session,
        user_id=user.id,
        email="revoked_user@gmail.com",
        provider="gmail",
        status="connected",
        access_token_encrypted=encrypt_secret("expired_tok"),
        refresh_token_encrypted=encrypt_secret("revoked_ref"),
    )

    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    with patch("src.core.gmail_sync.GmailClient") as mock_cls:
        mock_inst = MagicMock()
        mock_inst.ensure_valid_token.side_effect = GmailReconnectionRequiredError("Token revoked by Google")
        mock_cls.return_value = mock_inst

        res = await client.post("/api/v1/emails/sync?force=true", headers=headers)
        assert res.status_code == 401
        assert "reconnect" in (res.json().get("message") or res.json().get("detail", "")).lower()

    # Verify account status in DB was updated to error
    acc = await connected_account_crud.get_by_user_and_provider(db_session, user.id, "gmail")
    assert acc.status == "error"
