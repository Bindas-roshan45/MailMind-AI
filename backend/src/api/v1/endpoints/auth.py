"""
Session token and Google OAuth 2.0 endpoints for MailMind AI.
Handles local JWT issuance, cryptographically signed OAuth state generation,
state replay prevention via AuditLog, browser redirect callback handling,
token encryption at rest, and Gmail connection status reporting.
"""
from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Optional
from urllib.parse import quote_plus, urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_or_create_demo_user
from src.config import settings
from src.core.gmail import GMAIL_SCOPES, GmailClient
from src.core.security import create_access_token, decrypt_secret, encrypt_secret
from src.crud.connected_account import connected_account_crud
from src.crud.user import user_crud
from src.database import get_session
from src.models import AuditLog, ConnectedAccount, User
from src.schemas import APIResponse, TokenResponse

logger = logging.getLogger("mailmind-ai.auth")

router = APIRouter()


class GoogleCallbackRequest(BaseModel):
    code: str
    state: str


def create_oauth_state(user_id: int) -> str:
    """
    Generate an unpredictable, short-lived (10 min), signed JWT state token
    containing user ID, cryptographic nonce, and unique token ID (jti).
    """
    payload = {
        "sub": str(user_id),
        "nonce": secrets.token_urlsafe(16),
        "jti": secrets.token_hex(16),
        "type": "google_oauth_state",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def verify_and_consume_oauth_state(db: AsyncSession, state: Optional[str]) -> int:
    """
    Validate the OAuth state token:
    1. Rejects missing or blank state.
    2. Validates cryptographic signature and expiration.
    3. Verifies token type is 'google_oauth_state'.
    4. Enforces one-time use by checking against consumed state records in AuditLog.
    5. Returns the bound user_id.
    Raises HTTPException(400) on any validation failure.
    """
    if not state or not state.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state parameter",
        )

    try:
        payload = jwt.decode(
            state.strip(),
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as exc:
        logger.warning("Invalid or expired OAuth state token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please initiate authorization again.",
        )

    if payload.get("type") != "google_oauth_state":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state type",
        )

    sub = payload.get("sub")
    if not sub or not str(sub).isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user identity in OAuth state",
        )
    user_id = int(sub)

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed OAuth state token (missing jti)",
        )

    # Replay protection: verify that state was not already used
    stmt = select(AuditLog).where(
        AuditLog.action == "OAUTH_STATE_CONSUMED",
        AuditLog.resource_id == str(jti),
    )
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        logger.warning("Replayed OAuth state token detected: jti=%s user_id=%s", jti, user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state token has already been used. Please initiate a new connection.",
        )

    # Mark state as consumed in AuditLog to enforce one-time usage
    consumption_log = AuditLog(
        user_id=user_id,
        action="OAUTH_STATE_CONSUMED",
        resource_type="oauth_state",
        resource_id=str(jti),
    )
    db.add(consumption_log)
    await db.flush()

    return user_id


async def _process_oauth_code(
    db: AsyncSession,
    user_id: int,
    code: str,
) -> ConnectedAccount:
    """
    Exchange authorization code for tokens, fetch Google profile,
    encrypt tokens at rest, and save ConnectedAccount.
    """
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    client_secret = (settings.GOOGLE_CLIENT_SECRET or "").strip()

    if not client_id or not client_secret or client_id.startswith("your_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth credentials not configured in environment",
        )

    target_user = await user_crud.get(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User bound to OAuth state not found",
        )

    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Encrypt tokens before storing in database
    enc_access = encrypt_secret(creds.token) if creds.token else None
    enc_refresh = encrypt_secret(creds.refresh_token) if creds.refresh_token else None
    expiry_utc = None
    raw_expiry = getattr(creds, "expiry", None)
    if isinstance(raw_expiry, datetime):
        expiry_utc = (
            raw_expiry.replace(tzinfo=timezone.utc)
            if raw_expiry.tzinfo is None
            else raw_expiry
        )

    # Fetch primary user profile from Google to get connected email
    client = GmailClient(
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_expires_at=expiry_utc,
    )
    profile = client.service.users().getProfile(userId="me").execute()
    gmail_address = profile.get("emailAddress", target_user.email)

    # Update or create ConnectedAccount
    gmail_acc = await connected_account_crud.get_by_user_and_provider(db, target_user.id, "gmail")
    if gmail_acc:
        gmail_acc.email = gmail_address
        gmail_acc.status = "connected"
        gmail_acc.access_token_encrypted = enc_access
        # Preserve existing refresh token if Google does not return a new one
        if enc_refresh:
            gmail_acc.refresh_token_encrypted = enc_refresh
        gmail_acc.token_expires_at = expiry_utc
        gmail_acc.last_sync = datetime.now(timezone.utc)
        db.add(gmail_acc)
    else:
        gmail_acc = ConnectedAccount(
            user_id=target_user.id,
            email=gmail_address,
            provider="gmail",
            status="connected",
            access_token_encrypted=enc_access,
            refresh_token_encrypted=enc_refresh,
            token_expires_at=expiry_utc,
            last_sync=datetime.now(timezone.utc),
        )
        db.add(gmail_acc)

    await db.commit()
    await db.refresh(gmail_acc)
    return gmail_acc


@router.post("/demo-token", response_model=TokenResponse, summary="Issue demo JWT")
async def issue_demo_token(db: AsyncSession = Depends(get_session)):
    """Issue a JWT for the local demo user. Disabled when DEMO_MODE is false."""
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo tokens are disabled when DEMO_MODE is false",
        )
    user = await get_or_create_demo_user(db)
    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=APIResponse, summary="Current token identity")
async def auth_me(current_user: User = Depends(get_current_user)):
    """Return the user bound to the current session (JWT or demo fallback)."""
    return APIResponse(
        success=True,
        data={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "plan": current_user.plan.value if current_user.plan else None,
            "is_active": current_user.is_active,
        },
        message="Authenticated",
        demo_mode=settings.DEMO_MODE,
    )


@router.get("/google/url", response_model=APIResponse, summary="Get Google OAuth Authorization URL")
async def get_google_oauth_url(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Generate Google OAuth 2.0 authorization URL with cryptographically signed,
    unpredictable state bound to the authenticated user.
    """
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    client_secret = (settings.GOOGLE_CLIENT_SECRET or "").strip()

    is_configured = bool(
        client_id
        and not client_id.startswith("your_")
        and client_secret
        and not client_secret.startswith("your_")
    )

    if not is_configured:
        return APIResponse(
            success=False,
            data={
                "is_configured": False,
                "auth_url": None,
                "setup_instructions": (
                    "To enable real Gmail sync: Create OAuth 2.0 credentials in Google Cloud Console "
                    "(https://console.cloud.google.com/apis/credentials), set Authorized Redirect URI "
                    f"to {settings.GOOGLE_REDIRECT_URI}, and set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env."
                ),
            },
            message="Google OAuth credentials not configured in environment.",
        )

    # Generate cryptographically signed, short-lived, one-time state
    state = create_oauth_state(user.id)

    params = {
        "client_id": client_id,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return APIResponse(
        success=True,
        data={
            "is_configured": True,
            "auth_url": auth_url,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        },
        message="Google OAuth authorization URL generated",
    )


@router.get("/google/callback", summary="Handle Google OAuth Browser Redirect")
async def google_oauth_callback_get(
    request: Request,
    db: AsyncSession = Depends(get_session),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """
    Handles standard browser GET redirect from Google OAuth.
    Validates state, exchanges authorization code, stores encrypted credentials,
    and redirects the user back to the frontend with outcome query parameters.
    """
    frontend_base = settings.FRONTEND_URL.rstrip("/")

    # Check for Google authorization error (e.g., user clicked cancel/deny)
    if error:
        err_msg = error_description or error
        logger.warning("Google OAuth error redirect: %s", err_msg)
        return RedirectResponse(
            url=f"{frontend_base}/?oauth=error&message={quote_plus(f'Google authorization error: {err_msg}')}"
        )

    if not code:
        return RedirectResponse(
            url=f"{frontend_base}/?oauth=error&message={quote_plus('Missing authorization code from Google.')}"
        )

    # Validate and consume state (one-time use, replay protection)
    try:
        user_id = await verify_and_consume_oauth_state(db, state)
    except HTTPException as exc:
        return RedirectResponse(
            url=f"{frontend_base}/?oauth=error&message={quote_plus(str(exc.detail))}"
        )

    # Exchange code and update account
    try:
        gmail_acc = await _process_oauth_code(db, user_id=user_id, code=code)
        logger.info("Gmail OAuth connected successfully for user %s", user_id)
        # Issue fresh application session token to prevent "Invalid or expired access token" in frontend
        app_token = create_access_token(
            subject=user_id,
            extra_claims={"email": gmail_acc.email},
        )
        return RedirectResponse(url=f"{frontend_base}/?oauth=success&token={app_token}")
    except Exception as exc:
        logger.error("OAuth token exchange failure: %s", exc)
        return RedirectResponse(
            url=f"{frontend_base}/?oauth=error&message={quote_plus('Failed to exchange authorization code with Google.')}"
        )


@router.post("/google/callback", response_model=APIResponse, summary="Handle Google OAuth Programmatic Callback")
async def google_oauth_callback_post(
    payload: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Handles programmatic token exchange via POST with code and state payload.
    """
    user_id = await verify_and_consume_oauth_state(db, payload.state)
    try:
        account = await _process_oauth_code(db, user_id=user_id, code=payload.code)
        app_token = create_access_token(
            subject=user_id,
            extra_claims={"email": account.email},
        )
        return APIResponse(
            success=True,
            data={
                "id": account.id,
                "email": account.email,
                "provider": account.provider,
                "status": account.status,
                "access_token": app_token,
                "token_type": "bearer",
            },
            message="Google Gmail account connected successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("OAuth token exchange error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with Google",
        )


@router.get("/google/status", response_model=APIResponse, summary="Get Gmail Connection Status")
async def get_google_status(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Return genuine Gmail integration connection and sync status.
    Never fabricates a live OAuth connection when credentials/tokens are absent.
    """
    gmail_acc = await connected_account_crud.get_by_user_and_provider(db, user.id, "gmail")

    is_error_status = bool(gmail_acc and gmail_acc.status == "error")
    has_real_tokens = bool(
        gmail_acc
        and gmail_acc.access_token_encrypted
        and gmail_acc.status == "connected"
    )

    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    is_oauth_configured = bool(client_id and not client_id.startswith("your_"))

    account_status = (
        "error"
        if is_error_status
        else ("connected" if has_real_tokens else "disconnected")
    )
    message = (
        "Gmail authorization expired or was revoked. Please reconnect your Gmail account in Settings."
        if is_error_status
        else (
            "Real Gmail integration active"
            if has_real_tokens
            else (
                "Running in Simulated Demo Mode. Connect Google OAuth for real inbox sync."
                if settings.DEMO_MODE
                else "Gmail not connected. Please connect your Google account."
            )
        )
    )

    return APIResponse(
        success=True,
        data={
            "is_connected": has_real_tokens,
            "is_demo_mode": settings.DEMO_MODE,
            "is_oauth_configured": is_oauth_configured,
            "connected_email": gmail_acc.email if (gmail_acc and has_real_tokens) else None,
            "account_status": account_status,
            "last_sync": gmail_acc.last_sync.isoformat() if (gmail_acc and has_real_tokens and gmail_acc.last_sync) else None,
            "message": message,
        },
        message="Integration status retrieved",
    )


@router.post("/google/disconnect", response_model=APIResponse, summary="Disconnect Gmail Account")
async def disconnect_google(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Disconnect and revoke stored Gmail OAuth tokens."""
    gmail_acc = await connected_account_crud.get_by_user_and_provider(db, user.id, "gmail")
    if gmail_acc:
        gmail_acc.status = "disconnected"
        gmail_acc.access_token_encrypted = None
        gmail_acc.refresh_token_encrypted = None
        db.add(gmail_acc)
        await db.commit()

    return APIResponse(
        success=True,
        message="Gmail account disconnected successfully",
    )
