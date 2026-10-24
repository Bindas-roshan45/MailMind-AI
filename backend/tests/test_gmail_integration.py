"""
Comprehensive tests for real Gmail fetching, sync endpoints, threads,
token refresh, AI reply drafts, explicit user approval, and error handling.
"""
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.gmail import GmailClient, GmailReconnectionRequiredError, GmailAuthError
from src.core.security import encrypt_secret
from googleapiclient.errors import HttpError
from httpx import Response
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
    AIReplyDraft,
)


# =====================================================================
# Unit Tests for GmailClient
# =====================================================================

@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_ensure_valid_token_fresh(mock_creds_cls, mock_build):
    """If token is not expired, ensure_valid_token should return None (no refresh needed)."""
    mock_creds = MagicMock()
    mock_creds.expired = False
    mock_creds_cls.return_value = mock_creds

    client = GmailClient(
        access_token="valid_token",
        refresh_token="ref_token",
        client_id="cid",
        client_secret="csec",
    )
    token = client.ensure_valid_token()
    assert token is None
    mock_creds.refresh.assert_not_called()


@patch("google.auth.transport.requests.Request")
@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_ensure_valid_token_expired(mock_creds_cls, mock_build, mock_request_cls):
    """If token is expired, ensure_valid_token refreshes and returns the new token."""
    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.refresh_token = "ref_token"
    mock_creds.token = "refreshed_access_token"
    mock_creds_cls.return_value = mock_creds

    client = GmailClient(
        access_token="old_token",
        refresh_token="ref_token",
        client_id="cid",
        client_secret="csec",
    )
    token = client.ensure_valid_token()
    assert token == "refreshed_access_token"
    mock_creds.refresh.assert_called_once()


@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_list_and_parse_message(mock_creds_cls, mock_build):
    """GmailClient lists messages and parses headers, internalDate, and body."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    # Mock list
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg_001", "threadId": "th_001"}]
    }

    raw_msg = {
        "id": "msg_001",
        "threadId": "th_001",
        "internalDate": "1700000000000",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Here is the proposal preview...",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Project Proposal Q4"},
                {"name": "From", "value": "Alice Wonderland <alice@example.com>"},
                {"name": "To", "value": "roshan@gmail.com"},
                {"name": "Date", "value": "Fri, 15 Nov 2024 10:00:00 +0000"},
            ],
            "body": {
                "data": "SGVsbG8sIHBsZWFzZSByZXZpZXcgdGhlIHByb3Bvc2FsLg=="  # base64 "Hello, please review the proposal."
            },
        },
    }
    mock_service.users().messages().get().execute.return_value = raw_msg

    client = GmailClient(
        access_token="acc",
        refresh_token="ref",
        client_id="cid",
        client_secret="csec",
    )

    msgs = client.list_messages(max_results=5)
    assert len(msgs) == 1
    assert msgs[0]["id"] == "msg_001"

    msg_data = client.get_message("msg_001")
    assert msg_data["id"] == "msg_001"

    parsed = GmailClient.parse_message_headers_and_body(msg_data)
    assert parsed["subject"] == "Project Proposal Q4"
    assert parsed["from_email"] == "alice@example.com"
    assert parsed["from_name"] == "Alice Wonderland"
    assert "Hello, please review" in parsed["body"]
    assert parsed["is_read"] is False


@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_get_thread(mock_creds_cls, mock_build):
    """GmailClient get_thread retrieves raw thread payload."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    mock_service.users().threads().get().execute.return_value = {
        "id": "th_001",
        "messages": [
            {
                "id": "m1",
                "threadId": "th_001",
                "internalDate": "1700000000000",
                "snippet": "Initial question",
            },
            {
                "id": "m2",
                "threadId": "th_001",
                "internalDate": "1700000005000",
                "snippet": "Follow up reply",
            },
        ],
    }

    client = GmailClient(access_token="a", refresh_token="r", client_id="c", client_secret="s")
    raw_thread = client.get_thread("th_001")
    assert raw_thread["id"] == "th_001"
    assert len(raw_thread["messages"]) == 2


# =====================================================================
# Integration Tests: Endpoints & Live Sync
# =====================================================================

@pytest.mark.asyncio
async def test_sync_disconnected_returns_400(client: AsyncClient, db_session: AsyncSession):
    """Calling POST /emails/sync when Gmail is disconnected returns 400 error."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan", plan=UserPlan.PRO)

    acc = await connected_account_crud.get_by_user_and_provider(db_session, user.id, "gmail")
    if acc:
        acc.status = "disconnected"
        acc.access_token_encrypted = None
        db_session.add(acc)
        await db_session.commit()

    res = await client.post("/api/v1/emails/sync")
    assert res.status_code == 400
    assert "not connected" in (res.json().get("message") or res.json().get("detail", "")).lower()


@pytest.mark.asyncio
async def test_sync_real_gmail_emails_and_verify_dashboard(client: AsyncClient, db_session: AsyncSession):
    """
    Simulates connected Gmail OAuth:
    1. Synchronizes inbox messages via Gmail API.
    2. Verifies emails stored in database.
    3. Confirms GET /api/v1/emails returns real data and skips demo emails.
    """
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan Kumar", plan=UserPlan.PRO)

    # Set up connected Gmail account with encrypted token
    acc = await connected_account_crud.get_by_user_and_provider(db_session, user.id, "gmail")
    if not acc:
        acc = await connected_account_crud.create(
            db_session,
            user_id=user.id,
            email="roshan@gmail.com",
            provider="gmail",
            status="connected",
            access_token_encrypted=encrypt_secret("fake_valid_token"),
            refresh_token_encrypted=encrypt_secret("fake_refresh_token"),
        )
    else:
        acc.status = "connected"
        acc.access_token_encrypted = encrypt_secret("fake_valid_token")
        acc.refresh_token_encrypted = encrypt_secret("fake_refresh_token")
        db_session.add(acc)
        await db_session.commit()

    # Mock Gmail client
    mock_client = MagicMock()
    mock_client.ensure_valid_token.return_value = "fake_valid_token"
    mock_client.parse_message_headers_and_body = GmailClient.parse_message_headers_and_body
    mock_client.list_messages.return_value = [
        {"id": "real_msg_101", "threadId": "real_th_101"},
        {"id": "real_msg_102", "threadId": "real_th_102"},
    ]
    mock_client.get_message.side_effect = [
        {
            "id": "real_msg_101",
            "threadId": "real_th_101",
            "internalDate": "1700000000000",
            "labelIds": ["INBOX", "UNREAD", "STARRED", "IMPORTANT"],
            "snippet": "Please deploy the patch before midnight.",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Urgent Security Patch Deployment"},
                    {"name": "From", "value": "Sarah Connor <sarah@cyberdyne.io>"},
                    {"name": "To", "value": "roshan@gmail.com"},
                    {"name": "Date", "value": "Wed, 20 Nov 2024 14:30:00 +0000"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": "SGVsbG8gUm9zaGFuLCBwbGVhc2UgZGVwbG95IHRoZSBwYXRjaC4="},
                    },
                    {
                        "filename": "patch.tar.gz",
                        "mimeType": "application/gzip",
                        "body": {"attachmentId": "att1"},
                    },
                ],
            },
        },
        {
            "id": "real_msg_102",
            "threadId": "real_th_102",
            "internalDate": "1699990000000",
            "labelIds": ["INBOX"],
            "snippet": "Explore the latest developments in async Python.",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Top Python Trends in 2024"},
                    {"name": "From", "value": "Dev Weekly <newsletter@devweekly.org>"},
                    {"name": "To", "value": "roshan@gmail.com"},
                    {"name": "Date", "value": "Wed, 20 Nov 2024 12:00:00 +0000"},
                ],
                "body": {
                    "data": "SGVyZSBhcmUgdGhpcyB3ZWVrJ3MgdG9wIFB5dGhvbiBhcnRpY2xlcy4="
                },
            },
        },
    ]

    with patch("src.core.gmail_sync.get_gmail_client_for_user", return_value=(mock_client, acc)):
        sync_res = await client.post("/api/v1/emails/sync?max_results=10")
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["success"] is True
        assert sync_data["data"]["new_count"] == 2

    # Fetch emails via GET /emails
    with patch("src.core.gmail_sync.get_gmail_client_for_user", return_value=(mock_client, acc)):
        get_res = await client.get("/api/v1/emails?auto_sync=false")
        assert get_res.status_code == 200
        list_data = get_res.json()
        assert list_data["success"] is True
        assert list_data["data"]["is_gmail_connected"] is True

        items = list_data["data"]["items"]
        assert len(items) == 2
        subjects = [e["subject"] for e in items]
        assert "Urgent Security Patch Deployment" in subjects
        assert "Top Python Trends in 2024" in subjects

        senders = [e["from_email"] for e in items]
        assert "sarah@cyberdyne.io" in senders
        assert "newsletter@devweekly.org" in senders


@pytest.mark.asyncio
async def test_get_thread_endpoint(client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/emails/threads/{thread_id} returns all emails in that thread."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan Kumar", plan=UserPlan.PRO)

    now = datetime.now(timezone.utc)
    e1 = Email(
        user_id=user.id,
        message_id="msg_thread_1",
        thread_id="thread_xyz",
        from_name="Partner A",
        from_email="partner@example.com",
        to="roshan@gmail.com",
        subject="Partnership Discussion",
        body="Let's collaborate on the project.",
        received_at=now,
        category=EmailCategory.WORK,
        urgency=EmailUrgency.MEDIUM,
        folder="inbox",
    )
    e2 = Email(
        user_id=user.id,
        message_id="msg_thread_2",
        thread_id="thread_xyz",
        from_name="Roshan Kumar",
        from_email="roshan@gmail.com",
        to="partner@example.com",
        subject="Re: Partnership Discussion",
        body="Sounds great, let's schedule a call.",
        received_at=now,
        category=EmailCategory.WORK,
        urgency=EmailUrgency.LOW,
        folder="sent",
    )
    db_session.add_all([e1, e2])
    await db_session.commit()

    res = await client.get("/api/v1/emails/threads/thread_xyz")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["thread_id"] == "thread_xyz"
    assert len(data["data"]["messages"]) == 2


@pytest.mark.asyncio
async def test_ai_reply_draft_lifecycle_requires_explicit_approval(client: AsyncClient, db_session: AsyncSession):
    """
    AI reply drafts must remain unapproved and unsent until the user approves
    and explicitly triggers send.
    """
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan Kumar", plan=UserPlan.PRO)

    now = datetime.now(timezone.utc)
    email_obj = Email(
        user_id=user.id,
        message_id="inbox_msg_999",
        thread_id="th_999",
        from_name="Client Bob",
        from_email="bob@acme.com",
        to="roshan@gmail.com",
        subject="Inquiry regarding consulting rates",
        body="Could you share your consulting rates and availability for next month?",
        received_at=now,
        category=EmailCategory.WORK,
        urgency=EmailUrgency.MEDIUM,
        folder="inbox",
    )
    db_session.add(email_obj)
    await db_session.commit()
    await db_session.refresh(email_obj)

    # 1. Generate AI draft
    gen_res = await client.post(
        "/api/v1/ai/generate-draft",
        json={
            "email_id": email_obj.id,
            "tone": "professional",
            "language": "english",
        },
    )
    assert gen_res.status_code == 201
    draft_data = gen_res.json()["data"]
    draft_id = draft_data["draft_id"]
    assert draft_id is not None
    # Draft is NOT approved and NOT sent
    assert draft_data["is_approved"] is False
    assert draft_data["is_sent"] is False

    # 2. Approve draft explicitly
    appr_res = await client.post(
        f"/api/v1/ai/drafts/{draft_id}/approve",
        json={"is_approved": True},
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["data"]["is_approved"] is True

    # 3. Explicitly send the email
    with patch("src.api.v1.endpoints.emails.get_gmail_client_for_user", return_value=None):
        send_res = await client.post(
            "/api/v1/emails/send",
            json={
                "to": "bob@acme.com",
                "subject": "Re: Inquiry regarding consulting rates",
                "body": draft_data["content"],
                "draft_id": draft_id,
                "thread_id": "th_999",
            },
        )
        assert send_res.status_code == 201
        assert send_res.json()["success"] is True

    # 4. Verify draft in DB is marked sent
    draft_in_db = await db_session.get(AIReplyDraft, draft_id)
    assert draft_in_db.is_sent is True


@pytest.mark.asyncio
async def test_gmail_api_error_handled_gracefully(client: AsyncClient, db_session: AsyncSession):
    """If Gmail API throws an exception during sync, it handles it gracefully without crashing."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan", plan=UserPlan.PRO)

    acc = await connected_account_crud.get_by_user_and_provider(db_session, user.id, "gmail")
    if not acc:
        acc = await connected_account_crud.create(
            db_session,
            user_id=user.id,
            email="roshan@gmail.com",
            provider="gmail",
            status="connected",
            access_token_encrypted=encrypt_secret("tok"),
            refresh_token_encrypted=encrypt_secret("ref"),
        )

    failing_client = MagicMock()
    failing_client.ensure_valid_token.return_value = "tok"
    failing_client.list_messages.side_effect = RuntimeError("Gmail API 429 Rate Limit Exceeded")

    with patch("src.core.gmail_sync.get_gmail_client_for_user", return_value=(failing_client, acc)):
        res = await client.post("/api/v1/emails/sync")
        assert res.status_code == 200
        assert res.json()["data"]["synced"] is False


# =====================================================================
# Tests for Token Refresh, Revocation, and Auto-Retry on 401
# =====================================================================

@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_refresh_token_missing_raises_reconnect(mock_creds_cls, mock_build):
    """If refresh_token is missing when refresh is attempted, raise GmailReconnectionRequiredError."""
    mock_creds = MagicMock()
    mock_creds.refresh_token = None
    mock_creds_cls.return_value = mock_creds

    client = GmailClient(access_token="tok", refresh_token=None)
    with pytest.raises(GmailReconnectionRequiredError) as exc_info:
        client.refresh_token()
    assert "reconnect" in str(exc_info.value).lower()


@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_refresh_revoked_invalid_grant_raises_reconnect(mock_creds_cls, mock_build):
    """If Google OAuth returns invalid_grant / revoked, raise GmailReconnectionRequiredError."""
    from google.auth.exceptions import RefreshError
    mock_creds = MagicMock()
    mock_creds.refresh_token = "revoked_refresh_token"
    mock_creds.refresh.side_effect = RefreshError("invalid_grant: Token has been expired or revoked.")
    mock_creds_cls.return_value = mock_creds

    client = GmailClient(access_token="tok", refresh_token="revoked_refresh_token")
    with pytest.raises(GmailReconnectionRequiredError) as exc_info:
        client.refresh_token()
    assert "reconnect" in str(exc_info.value).lower()


@patch("src.core.gmail.build")
@patch("src.core.gmail.Credentials")
def test_gmail_client_401_triggers_auto_refresh_and_retries(mock_creds_cls, mock_build):
    """When a Gmail API call returns HTTP 401, automatically refresh access token and retry."""
    mock_creds = MagicMock()
    mock_creds.refresh_token = "valid_refresh_token"
    mock_creds.token = "initial_token"
    mock_creds_cls.return_value = mock_creds

    # Setup 401 HttpError mock response
    resp_401 = MagicMock()
    resp_401.status = 401
    resp_401.reason = "Unauthorized"
    error_401 = HttpError(resp_401, b'{"error": "Invalid Credentials"}')

    # Mock service calls: 1st execute raises 401, 2nd execute succeeds
    mock_service_1 = MagicMock()
    mock_req_1 = MagicMock()
    mock_req_1.execute.side_effect = error_401
    mock_service_1.users().messages().list.return_value = mock_req_1

    mock_service_2 = MagicMock()
    mock_req_2 = MagicMock()
    mock_req_2.execute.return_value = {"messages": [{"id": "retried_msg_001"}]}
    mock_service_2.users().messages().list.return_value = mock_req_2

    # build() returns service_1 initially, then service_2 after refresh
    mock_build.side_effect = [mock_service_1, mock_service_2]

    refreshed_tokens = []
    def on_refresh(new_token, new_expiry):
        refreshed_tokens.append(new_token)

    client = GmailClient(
        access_token="expired_tok",
        refresh_token="valid_refresh_token",
        on_token_refresh=on_refresh,
    )

    # When refreshing, update creds.token
    def fake_refresh(request):
        mock_creds.token = "refreshed_token_abc"
    mock_creds.refresh.side_effect = fake_refresh

    # List messages should catch the 401, refresh, and return messages from service_2
    messages = client.list_messages()
    assert len(messages) == 1
    assert messages[0]["id"] == "retried_msg_001"
    mock_creds.refresh.assert_called_once()
    assert "refreshed_token_abc" in refreshed_tokens


@pytest.mark.asyncio
async def test_get_gmail_client_for_user_marks_error_on_reconnect_required(db_session: AsyncSession):
    """If ensure_valid_token raises GmailReconnectionRequiredError, account status is set to error."""
    from src.core.gmail_sync import get_gmail_client_for_user

    user = await user_crud.create(db_session, email="revoke_test@gmail.com", name="Revoke Test", plan=UserPlan.PRO)
    acc = await connected_account_crud.create(
        db_session,
        user_id=user.id,
        email="revoke_test@gmail.com",
        provider="gmail",
        status="connected",
        access_token_encrypted=encrypt_secret("old_tok"),
        refresh_token_encrypted=encrypt_secret("revoked_refresh"),
    )

    with patch("src.core.gmail_sync.GmailClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.ensure_valid_token.side_effect = GmailReconnectionRequiredError("Token revoked")
        mock_client_cls.return_value = mock_client

        result = await get_gmail_client_for_user(db_session, user.id)
        assert result is None

        # Verify DB account status updated to error
        await db_session.refresh(acc)
        assert acc.status == "error"


@pytest.mark.asyncio
async def test_sync_emails_returns_401_on_reconnect_required(client: AsyncClient, db_session: AsyncSession):
    """POST /api/v1/emails/sync returns 401 when account has status=error and needs reconnection."""
    user = await user_crud.create(db_session, email="sync_reconn@gmail.com", name="Sync Reconnect", plan=UserPlan.PRO)
    await connected_account_crud.create(
        db_session,
        user_id=user.id,
        email="sync_reconn@gmail.com",
        provider="gmail",
        status="error",
        access_token_encrypted=encrypt_secret("tok"),
        refresh_token_encrypted=encrypt_secret("revoked"),
    )

    from src.core.security import create_access_token
    app_token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {app_token}"}

    res = await client.post("/api/v1/emails/sync", headers=headers)
    assert res.status_code == 401
    err_text = res.json().get("message") or res.json().get("detail", "")
    assert "reconnect" in err_text.lower()


@pytest.mark.asyncio
async def test_gmail_fetch_and_ai_reply_generation_after_token_refresh(client: AsyncClient, db_session: AsyncSession):
    """Test that after a token refresh occurs, real Gmail message is synced and AI reply draft is generated."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan Kumar", plan=UserPlan.PRO)

    acc = await connected_account_crud.get_by_user_and_provider(db_session, user.id, "gmail")
    if not acc:
        acc = await connected_account_crud.create(
            db_session,
            user_id=user.id,
            email="roshan@gmail.com",
            provider="gmail",
            status="connected",
            access_token_encrypted=encrypt_secret("old_tok"),
            refresh_token_encrypted=encrypt_secret("ref_tok"),
        )
    else:
        acc.status = "connected"
        acc.access_token_encrypted = encrypt_secret("old_tok")
        acc.refresh_token_encrypted = encrypt_secret("ref_tok")
        db_session.add(acc)
        await db_session.commit()

    # Simulate GmailClient that refreshes token then returns a real message
    mock_client = MagicMock()
    mock_client.ensure_valid_token.return_value = "new_refreshed_access_token"
    mock_client.creds.expiry = None
    mock_client.list_messages.return_value = [{"id": "post_refresh_msg_101"}]
    mock_client.get_message.return_value = {
        "id": "post_refresh_msg_101",
        "threadId": "th_post_ref_101",
        "internalDate": "1700000000000",
        "labelIds": ["INBOX"],
        "snippet": "Can we confirm the contract pricing for Q1?",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "Contract Pricing Confirmation Q1"},
                {"name": "From", "value": "David Miller <david.miller@enterprise.org>"},
                {"name": "To", "value": "roshan@gmail.com"},
                {"name": "Date", "value": "Thu, 21 Nov 2024 14:00:00 +0000"},
            ],
            "body": {
                "data": "Q2FuIHdlIGNvbmZpcm0gdGhlIGNvbnRyYWN0IHByaWNpbmcgZm9yIFExPyBQbGVhc2Ugc2VuZCB0aGUgZmluYWwgZmlndXJlcy4="
            },
        },
    }
    mock_client.parse_message_headers_and_body.return_value = {
        "message_id": "post_refresh_msg_101",
        "thread_id": "th_post_ref_101",
        "subject": "Contract Pricing Confirmation Q1",
        "from_name": "David Miller",
        "from_email": "david.miller@enterprise.org",
        "to": "roshan@gmail.com",
        "received_at": datetime.now(timezone.utc),
        "body": "Can we confirm the contract pricing for Q1? Please send the final figures.",
        "preview": "Can we confirm the contract pricing for Q1?",
        "is_read": False,
        "is_starred": False,
        "is_important": True,
        "folder": "inbox",
        "has_attachments": False,
        "attachment_count": 0,
    }

    with patch("src.core.gmail_sync.get_gmail_client_for_user", return_value=(mock_client, acc)):
        sync_res = await client.post("/api/v1/emails/sync?max_results=5")
        assert sync_res.status_code == 200
        sync_data = sync_res.json()
        assert sync_data["success"] is True

        # Check that message was created in DB
        email_record = await email_crud.get_by_message_id(db_session, "post_refresh_msg_101")
        assert email_record is not None
        assert email_record.subject == "Contract Pricing Confirmation Q1"

        # Generate AI reply draft for this synced email
        draft_res = await client.post(
            "/api/v1/ai/generate-draft",
            json={
                "email_id": email_record.id,
                "tone": "professional",
                "language": "english",
            },
        )
        assert draft_res.status_code == 201
        draft_body = draft_res.json()["data"]
        assert draft_body["content"]
        assert draft_body["is_approved"] is False
        assert draft_body["is_sent"] is False

