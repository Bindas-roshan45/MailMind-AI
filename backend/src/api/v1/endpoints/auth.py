"""
Session token endpoints.

Gmail OAuth is deferred until the backend foundation is stable.
DEMO_MODE can issue a local JWT for the demo user.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_or_create_demo_user
from src.config import settings
from src.core.security import create_access_token
from src.database import get_session
from src.models import User
from src.schemas import APIResponse, TokenResponse

router = APIRouter()


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
