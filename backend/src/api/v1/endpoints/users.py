"""
User management API endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_session
from src.crud.user import user_crud
from src.crud.connected_account import connected_account_crud
from src.schemas import UserUpdate, APIResponse
from src.models import User

router = APIRouter()


@router.get("/me", response_model=APIResponse, summary="Get Current User Profile")
async def get_current_user_profile(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Fetch current authenticated user profile."""
    accounts = await connected_account_crud.get_by_user(db, user.id)

    profile_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "plan": user.plan.value,
        "is_active": user.is_active,
        "connected_accounts": [
            {
                "id": acc.id,
                "email": acc.email,
                "provider": acc.provider,
                "status": acc.status,
                "last_sync": acc.last_sync.isoformat() if acc.last_sync else "2 min ago",
            }
            for acc in accounts
        ],
    }

    return APIResponse(
        success=True,
        data=profile_data,
        message="User profile retrieved successfully",
    )


@router.put("/me", response_model=APIResponse, summary="Update User Profile")
async def update_current_user_profile(
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Update profile details for current user. Existing fields are preserved when omitted."""
    updated_user = await user_crud.update(
        db,
        db_obj=user,
        name=update_data.name if update_data.name is not None else user.name,
        avatar_url=update_data.avatar_url if update_data.avatar_url is not None else user.avatar_url,
        plan=update_data.plan if update_data.plan is not None else user.plan,
    )

    return APIResponse(
        success=True,
        data={
            "id": updated_user.id,
            "email": updated_user.email,
            "name": updated_user.name,
            "plan": updated_user.plan.value,
        },
        message="Profile updated successfully",
    )
