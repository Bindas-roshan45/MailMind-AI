"""
Session token and Google OAuth 2.0 endpoints for MailMind AI.
Handles local JWT issuance, Google OAuth authorization flow, callback,
token encryption, and connection status reporting.
"""
from datetime import datetime, timezone
import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_or_create_demo_user
from src.config import settings
from src.core.gmail import GMAIL_SCOPES, GmailClient
from src.core.security import create_access_token, decrypt_secret, encrypt_secret
from src.crud.connected_account import connected_account_crud
from src.database import get_session
from src.models import ConnectedAccount, User
from src.schemas import APIResponse, TokenResponse

logger = logging.getLogger("mailmind-ai.auth")

router = APIRouter()


class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


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
    Generate Google OAuth 2.0 authorization URL.
    Returns clear instructions if Google Cloud credentials are not configured in .env.
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

    # Build standard Google OAuth 2.0 authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": f"uid_{user.id}",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return APIResponse(
        success=True,
        data={
            "is_configured": True,
            "auth_url": auth_url,
        },
        message="Google OAuth authorization URL generated",
    )


@router.post("/google/callback", response_model=APIResponse, summary="Handle Google OAuth Callback")
async def google_oauth_callback(
    payload: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Exchange authorization code for tokens, encrypt with Fernet, and save ConnectedAccount.
    """
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    client_secret = (settings.GOOGLE_CLIENT_SECRET or "").strip()

    if not client_id or not client_secret or client_id.startswith("your_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth credentials not configured in environment",
        )

    try:
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
        flow.fetch_token(code=payload.code)
        creds = flow.credentials

        # Encrypt tokens before storing in database
        enc_access = encrypt_secret(creds.token) if creds.token else None
        enc_refresh = encrypt_secret(creds.refresh_token) if creds.refresh_token else None

        # Fetch primary user profile from Google to get connected email
        client = GmailClient(
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
        profile = client.service.users().getProfile(userId="me").execute()
        gmail_address = profile.get("emailAddress", user.email)

        # Update or create ConnectedAccount
        accounts = await connected_account_crud.get_by_user(db, user.id)
        gmail_acc = next((a for a in accounts if a.provider == "gmail"), None)

        if gmail_acc:
            gmail_acc.email = gmail_address
            gmail_acc.status = "connected"
            gmail_acc.access_token_encrypted = enc_access
            gmail_acc.refresh_token_encrypted = enc_refresh or gmail_acc.refresh_token_encrypted
            gmail_acc.last_sync = datetime.now(timezone.utc)
            db.add(gmail_acc)
        else:
            gmail_acc = ConnectedAccount(
                user_id=user.id,
                email=gmail_address,
                provider="gmail",
                status="connected",
                access_token_encrypted=enc_access,
                refresh_token_encrypted=enc_refresh,
                last_sync=datetime.now(timezone.utc),
            )
            db.add(gmail_acc)

        await db.commit()
        await db.refresh(gmail_acc)

        return APIResponse(
            success=True,
            data={
                "id": gmail_acc.id,
                "email": gmail_acc.email,
                "provider": gmail_acc.provider,
                "status": gmail_acc.status,
            },
            message="Google Gmail account connected successfully",
        )
    except Exception as exc:
        logger.error("OAuth token exchange error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with Google: {str(exc)}",
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
    accounts = await connected_account_crud.get_by_user(db, user.id)
    gmail_acc = next((a for a in accounts if a.provider == "gmail"), None)

    has_real_tokens = bool(
        gmail_acc and gmail_acc.access_token_encrypted and gmail_acc.status == "connected"
    )

    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    is_oauth_configured = bool(client_id and not client_id.startswith("your_"))

    return APIResponse(
        success=True,
        data={
            "is_connected": has_real_tokens,
            "is_demo_mode": settings.DEMO_MODE,
            "is_oauth_configured": is_oauth_configured,
            "connected_email": gmail_acc.email if (gmail_acc and has_real_tokens) else None,
            "account_status": gmail_acc.status if gmail_acc else "disconnected",
            "last_sync": gmail_acc.last_sync.isoformat() if (gmail_acc and gmail_acc.last_sync) else None,
            "message": (
                "Real Gmail integration active"
                if has_real_tokens
                else (
                    "Running in Simulated Demo Mode. Connect Google OAuth for real inbox sync."
                    if settings.DEMO_MODE
                    else "Gmail not connected. Please connect your Google account."
                )
            ),
        },
        message="Integration status retrieved",
    )


@router.post("/google/disconnect", response_model=APIResponse, summary="Disconnect Gmail Account")
async def disconnect_google(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Disconnect and revoke stored Gmail OAuth tokens."""
    accounts = await connected_account_crud.get_by_user(db, user.id)
    gmail_acc = next((a for a in accounts if a.provider == "gmail"), None)
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
