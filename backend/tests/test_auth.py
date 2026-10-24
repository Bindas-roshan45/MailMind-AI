"""
Comprehensive tests for MailMind AI Authentication & Google OAuth 2.0.
Verifies JWT session lifecycle, password hashing, token encryption at rest,
OAuth state generation & validation, replay prevention, error handling,
mocked token exchange, status reporting, and disconnect.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient
from jose import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import (
    create_oauth_state,
    verify_and_consume_oauth_state,
)
from src.config import settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)
from src.crud.connected_account import connected_account_crud
from src.crud.user import user_crud
from src.models import ConnectedAccount, UserPlan


def test_jwt_roundtrip():
    token = create_access_token(subject=1, extra_claims={"email": "roshan@gmail.com"})
    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["email"] == "roshan@gmail.com"


def test_password_hash_roundtrip():
    hashed = hash_password("phase1-test-password")
    assert hashed != "phase1-test-password"
    assert verify_password("phase1-test-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_secret_encryption_roundtrip():
    stored = encrypt_secret("oauth-refresh-token-example")
    assert stored != "oauth-refresh-token-example"
    assert decrypt_secret(stored) == "oauth-refresh-token-example"


@pytest.mark.asyncio
async def test_demo_token_and_auth_me(client: AsyncClient):
    token_res = await client.post("/api/v1/auth/demo-token")
    assert token_res.status_code == 200
    body = token_res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    data = me.json()
    assert data["success"] is True
    assert data["data"]["email"] == "roshan@gmail.com"


@pytest.mark.asyncio
async def test_invalid_bearer_is_rejected(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_google_oauth_routes_registered(client: AsyncClient):
    """Verify that all canonical OAuth routes exist and do not 404."""
    # Status endpoint (GET)
    status_res = await client.get("/api/v1/auth/google/status")
    assert status_res.status_code == 200

    # Auth URL endpoint (GET)
    url_res = await client.get("/api/v1/auth/google/url")
    assert url_res.status_code == 200

    # Disconnect endpoint (POST)
    dc_res = await client.post("/api/v1/auth/google/disconnect")
    assert dc_res.status_code == 200

    # Legacy redirect route at /auth/google/callback
    legacy_res = await client.get("/auth/google/callback?code=test&state=test", follow_redirects=False)
    assert legacy_res.status_code == 307
    assert "/api/v1/auth/google/callback" in legacy_res.headers["location"]


@pytest.mark.asyncio
async def test_oauth_state_generation_and_validation(db_session: AsyncSession):
    """Test generating a secure signed state and consuming it successfully."""
    # Create test user
    user = await user_crud.create(
        db_session,
        email="teststate@gmail.com",
        name="State Test User",
        plan=UserPlan.PRO,
    )

    state = create_oauth_state(user.id)
    assert state
    assert len(state) > 30

    # Decode and verify claims
    decoded = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == str(user.id)
    assert decoded["type"] == "google_oauth_state"
    assert "nonce" in decoded
    assert "jti" in decoded

    # Consume state
    consumed_user_id = await verify_and_consume_oauth_state(db_session, state)
    assert consumed_user_id == user.id


@pytest.mark.asyncio
async def test_oauth_state_replay_rejected(db_session: AsyncSession):
    """Verify that reusing an already-consumed state token is strictly rejected."""
    user = await user_crud.create(
        db_session,
        email="replay@gmail.com",
        name="Replay User",
        plan=UserPlan.PRO,
    )
    state = create_oauth_state(user.id)

    # First consumption succeeds
    first_id = await verify_and_consume_oauth_state(db_session, state)
    assert first_id == user.id

    # Second consumption must be rejected with 400
    with pytest.raises(Exception) as excinfo:
        await verify_and_consume_oauth_state(db_session, state)
    assert "already been used" in str(excinfo.value)


@pytest.mark.asyncio
async def test_oauth_state_expired_rejected(db_session: AsyncSession):
    """Verify that expired state tokens are rejected."""
    expired_payload = {
        "sub": "1",
        "nonce": "testnonce",
        "jti": "expiredjti",
        "type": "google_oauth_state",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    expired_state = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(Exception) as excinfo:
        await verify_and_consume_oauth_state(db_session, expired_state)
    assert "Invalid or expired OAuth state" in str(excinfo.value)


@pytest.mark.asyncio
async def test_google_callback_error_handling(client: AsyncClient):
    """Verify that Google OAuth denial / cancel redirects cleanly to frontend with error."""
    res = await client.get(
        "/api/v1/auth/google/callback?error=access_denied&error_description=User+cancelled",
        follow_redirects=False,
    )
    assert res.status_code == 307
    location = res.headers["location"]
    assert "oauth=error" in location
    assert "access_denied" in location or "cancelled" in location


@pytest.mark.asyncio
async def test_google_callback_missing_state_handling(client: AsyncClient):
    """Verify that missing state redirects with error."""
    res = await client.get(
        "/api/v1/auth/google/callback?code=some_code",
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert "oauth=error" in res.headers["location"]


@pytest.mark.asyncio
async def test_google_callback_flow_mocked(client: AsyncClient, db_session: AsyncSession):
    """
    Test full mock OAuth code exchange:
    Generates state, exchanges code for credentials, encrypts tokens,
    updates ConnectedAccount, and redirects to /?oauth=success.
    """
    # Create user
    user = await user_crud.create(
        db_session,
        email="oauthuser@gmail.com",
        name="OAuth User",
        plan=UserPlan.PRO,
    )
    state = create_oauth_state(user.id)

    # Mock Google Flow credentials and Gmail profile
    mock_creds = MagicMock()
    mock_creds.token = "mock-google-access-token"
    mock_creds.refresh_token = "mock-google-refresh-token"

    mock_profile = {"emailAddress": "oauthuser@gmail.com"}

    with patch("google_auth_oauthlib.flow.Flow.from_client_config") as mock_flow_cls, \
         patch("src.api.v1.endpoints.auth.GmailClient") as mock_gmail_client_cls, \
         patch.object(settings, "GOOGLE_CLIENT_ID", "mock-client-id.apps.googleusercontent.com"), \
         patch.object(settings, "GOOGLE_CLIENT_SECRET", "mock-client-secret"):

        mock_flow_instance = MagicMock()
        mock_flow_instance.credentials = mock_creds
        mock_flow_cls.return_value = mock_flow_instance

        mock_gmail_instance = MagicMock()
        mock_gmail_instance.service.users().getProfile().execute.return_value = mock_profile
        mock_gmail_client_cls.return_value = mock_gmail_instance

        # Call GET callback
        res = await client.get(
            f"/api/v1/auth/google/callback?code=mock_code&state={state}",
            follow_redirects=False,
        )
        assert res.status_code == 307
        assert "oauth=success" in res.headers["location"]

        # Verify ConnectedAccount was saved and encrypted
        accounts = await connected_account_crud.get_by_user(db_session, user.id)
        gmail_acc = next((a for a in accounts if a.provider == "gmail"), None)
        assert gmail_acc is not None
        assert gmail_acc.status == "connected"
        assert gmail_acc.email == "oauthuser@gmail.com"
        assert gmail_acc.access_token_encrypted is not None
        assert decrypt_secret(gmail_acc.access_token_encrypted) == "mock-google-access-token"
        assert decrypt_secret(gmail_acc.refresh_token_encrypted) == "mock-google-refresh-token"


@pytest.mark.asyncio
async def test_google_disconnect_and_status(client: AsyncClient, db_session: AsyncSession):
    """
    Test that disconnect wipes encrypted tokens and marks status disconnected,
    and verify that get_google_status accurately reflects connection.
    """
    user = await user_crud.create(
        db_session,
        email="disconnect_test@gmail.com",
        name="Disconnect User",
        plan=UserPlan.PRO,
    )
    # Give user a token
    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Initially disconnected
    status_res = await client.get("/api/v1/auth/google/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["data"]["is_connected"] is False

    # Simulate connection with encrypted tokens
    enc_access = encrypt_secret("some-token")
    enc_refresh = encrypt_secret("some-refresh")
    acc = ConnectedAccount(
        user_id=user.id,
        email=user.email,
        provider="gmail",
        status="connected",
        access_token_encrypted=enc_access,
        refresh_token_encrypted=enc_refresh,
        last_sync=datetime.now(timezone.utc),
    )
    db_session.add(acc)
    await db_session.commit()

    # Now status should report is_connected == True
    status_res2 = await client.get("/api/v1/auth/google/status", headers=headers)
    assert status_res2.status_code == 200
    assert status_res2.json()["data"]["is_connected"] is True
    assert status_res2.json()["data"]["connected_email"] == user.email

    # Disconnect
    dc_res = await client.post("/api/v1/auth/google/disconnect", headers=headers)
    assert dc_res.status_code == 200
    assert dc_res.json()["success"] is True

    # Status should now be disconnected
    status_res3 = await client.get("/api/v1/auth/google/status", headers=headers)
    assert status_res3.status_code == 200
    assert status_res3.json()["data"]["is_connected"] is False
    assert status_res3.json()["data"]["connected_email"] is None
