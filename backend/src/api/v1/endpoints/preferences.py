"""
User preferences endpoints for MailMind AI.
Manages theme, AI model preferences, and notification channels.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.api.deps import get_current_user
from src.crud.user_preferences import user_preferences_crud
from src.schemas import UserPreferencesUpdate, APIResponse
from src.models import User, UserPreferences

router = APIRouter()


@router.get("", response_model=APIResponse, summary="Get User Preferences")
async def get_preferences(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve settings and preferences for the current user."""
    pref = await user_preferences_crud.get_by_user(db, user.id)
    if not pref:
        pref = await user_preferences_crud.create(db, user_id=user.id)

    data = {
        "theme": pref.theme,
        "layout_density": pref.layout_density,
        "ai_model": pref.ai_model,
        "default_reply_tone": pref.default_reply_tone,
        "auto_draft_enabled": pref.auto_draft_enabled,
        "phishing_shield_enabled": pref.phishing_shield_enabled,
        "ai_confidence_threshold": pref.ai_confidence_threshold,
        "push_notifications_enabled": pref.push_notifications_enabled,
        "email_notifications_enabled": pref.email_notifications_enabled,
    }

    return APIResponse(success=True, data=data, message="Preferences retrieved")


@router.put("", response_model=APIResponse, summary="Update User Preferences")
async def update_preferences(
    update_in: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Update settings and preferences for the current user."""
    pref = await user_preferences_crud.get_by_user(db, user.id)
    if not pref:
        pref = await user_preferences_crud.create(db, user_id=user.id)

    update_dict = update_in.model_dump(exclude_unset=True)
    updated = await user_preferences_crud.update(db, db_obj=pref, **update_dict)

    return APIResponse(
        success=True,
        data={
            "theme": updated.theme,
            "ai_model": updated.ai_model,
            "auto_draft_enabled": updated.auto_draft_enabled,
        },
        message="Preferences updated successfully",
    )
