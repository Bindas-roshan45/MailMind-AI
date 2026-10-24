"""
Shared FastAPI dependencies: database session, current user, demo fallback.
"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.security import decode_access_token
from src.crud.connected_account import connected_account_crud
from src.crud.user import user_crud
from src.database import get_session
from src.models import User, UserPlan

logger = logging.getLogger("mailmind-ai.deps")

optional_bearer = HTTPBearer(auto_error=False)

DEMO_USER_EMAIL = "roshan@gmail.com"
DEMO_USER_NAME = "Roshan Kumar"


async def get_or_create_demo_user(db: AsyncSession) -> User:
    """Ensure the Phase 1 demo user exists. Does not overwrite existing rows."""
    user = await user_crud.get_by_email(db, DEMO_USER_EMAIL)
    if user:
        return user

    user = await user_crud.create(
        db,
        email=DEMO_USER_EMAIL,
        name=DEMO_USER_NAME,
        plan=UserPlan.PRO,
    )
    existing_accounts = await connected_account_crud.get_by_user(db, user.id)
    if not existing_accounts:
        await connected_account_crud.create(
            db,
            user_id=user.id,
            email=DEMO_USER_EMAIL,
            provider="gmail",
            status="disconnected",
        )
    return user


async def get_current_user(
    db: AsyncSession = Depends(get_session),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
) -> User:
    """
    Resolve the authenticated user from a Bearer JWT.

    In DEMO_MODE, missing credentials fall back to the demo user so the React
    UI and existing tests keep working without Gmail OAuth.
    """
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            subject = payload.get("sub")
        except JWTError as jwt_err:
            logger.info("Application JWT session expired or invalid: %s", jwt_err)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user: Optional[User] = None
        if subject:
            if str(subject).isdigit():
                user = await user_crud.get(db, int(subject))
            if user is None:
                user = await user_crud.get_by_email(db, str(subject))

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    if settings.DEMO_MODE:
        return await get_or_create_demo_user(db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
