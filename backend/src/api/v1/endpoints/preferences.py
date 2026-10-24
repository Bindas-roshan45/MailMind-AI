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
        "auto_sync_enabled": pref.auto_sync_enabled,
        "sync_interval_minutes": pref.sync_interval_minutes,
        "push_notifications_enabled": pref.push_notifications_enabled,
        "email_notifications_enabled": pref.email_notifications_enabled,
        "automation_paused": pref.automation_paused,
        "automation_mode": pref.automation_mode,
        "daily_reply_limit": pref.daily_reply_limit,
        "min_confidence_score": pref.min_confidence_score,
        "sender_allowlist": pref.sender_allowlist or [],
        "sender_blocklist": pref.sender_blocklist or [],
        "job_title": pref.job_title,
        "company": pref.company,
        "timezone": pref.timezone,
        "custom_instructions": pref.custom_instructions,
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

    data = {
        "theme": updated.theme,
        "layout_density": updated.layout_density,
        "ai_model": updated.ai_model,
        "default_reply_tone": updated.default_reply_tone,
        "auto_draft_enabled": updated.auto_draft_enabled,
        "phishing_shield_enabled": updated.phishing_shield_enabled,
        "ai_confidence_threshold": updated.ai_confidence_threshold,
        "auto_sync_enabled": updated.auto_sync_enabled,
        "sync_interval_minutes": updated.sync_interval_minutes,
        "push_notifications_enabled": updated.push_notifications_enabled,
        "email_notifications_enabled": updated.email_notifications_enabled,
        "automation_paused": updated.automation_paused,
        "automation_mode": updated.automation_mode,
        "daily_reply_limit": updated.daily_reply_limit,
        "min_confidence_score": updated.min_confidence_score,
        "sender_allowlist": updated.sender_allowlist or [],
        "sender_blocklist": updated.sender_blocklist or [],
        "job_title": updated.job_title,
        "company": updated.company,
        "timezone": updated.timezone,
        "custom_instructions": updated.custom_instructions,
    }

    return APIResponse(
        success=True,
        data=data,
        message="Preferences updated successfully",
    )
