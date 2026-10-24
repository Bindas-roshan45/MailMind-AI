"""
User management API endpoints for MailMind AI.
Includes profile management, subscription tier usage limits,
GDPR data export, and full account deletion.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_session
from src.crud.user import user_crud
from src.crud.connected_account import connected_account_crud
from src.schemas import UserUpdate, APIResponse, UserPlan
from src.models import (
    AIReplyDraft,
    AuditLog,
    AutoReplyRule,
    CalendarEvent,
    ConnectedAccount,
    Email,
    EmailSignature,
    Notification,
    ProcessedMessageLog,
    Task,
    User,
    UserPreferences,
)

router = APIRouter()


class PlanChangeRequest(BaseModel):
    plan: UserPlan


PLAN_LIMITS = {
    UserPlan.FREE: {
        "max_connected_accounts": 1,
        "daily_auto_replies": 20,
        "features": ["Standard AI replies", "Single Gmail inbox", "Basic signatures"],
    },
    UserPlan.PRO: {
        "max_connected_accounts": 5,
        "daily_auto_replies": 150,
        "features": ["All AI tones & languages", "Multi-account sync", "Full automation engine", "Custom signatures"],
    },
    UserPlan.ENTERPRISE: {
        "max_connected_accounts": 999,
        "daily_auto_replies": 1000,
        "features": ["Unlimited inboxes", "Custom LLM rules", "Priority queue", "Dedicated audit logs"],
    },
}


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
                "last_sync": acc.last_sync.isoformat() if acc.last_sync else None,
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


@router.get("/me/usage", response_model=APIResponse, summary="Get Plan Usage & Quotas")
async def get_user_usage_and_quotas(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve subscription tier limits and current usage metrics."""
    plan_info = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[UserPlan.FREE])

    email_count = await db.scalar(
        select(func.count(Email.id)).where(Email.user_id == user.id)
    ) or 0

    acc_count = await db.scalar(
        select(func.count(ConnectedAccount.id)).where(ConnectedAccount.user_id == user.id)
    ) or 0

    # Auto-replies sent today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    replies_today = await db.scalar(
        select(func.count(ProcessedMessageLog.id)).where(
            ProcessedMessageLog.user_id == user.id,
            ProcessedMessageLog.action_taken == "auto_sent",
            ProcessedMessageLog.created_at >= today_start,
        )
    ) or 0

    return APIResponse(
        success=True,
        data={
            "plan": user.plan.value,
            "connected_accounts": acc_count,
            "max_connected_accounts": plan_info["max_connected_accounts"],
            "daily_auto_replies_used": replies_today,
            "daily_auto_replies_limit": plan_info["daily_auto_replies"],
            "total_emails_managed": email_count,
            "features": plan_info["features"],
        },
        message="Usage limits retrieved successfully",
    )


@router.patch("/me/plan", response_model=APIResponse, summary="Change Subscription Tier")
async def change_user_plan(
    payload: PlanChangeRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Upgrade or change user subscription plan."""
    user.plan = payload.plan
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return APIResponse(
        success=True,
        data={"id": user.id, "plan": user.plan.value},
        message=f"Plan successfully updated to {user.plan.value}",
    )


@router.get("/me/export", response_model=APIResponse, summary="Export Complete User Data (GDPR)")
async def export_user_data(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Export complete customer data bundle in structured JSON format."""
    emails_res = await db.execute(select(Email).where(Email.user_id == user.id))
    emails = emails_res.scalars().all()

    rules_res = await db.execute(select(AutoReplyRule).where(AutoReplyRule.user_id == user.id))
    rules = rules_res.scalars().all()

    sigs_res = await db.execute(select(EmailSignature).where(EmailSignature.user_id == user.id))
    sigs = sigs_res.scalars().all()

    tasks_res = await db.execute(select(Task).where(Task.user_id == user.id))
    tasks = tasks_res.scalars().all()

    pref_res = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))
    pref = pref_res.scalar_one_or_none()

    export_bundle = {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "plan": user.plan.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "preferences": {
            "reply_tone": pref.reply_tone if pref else "Professional",
            "automation_paused": pref.automation_paused if pref else False,
            "automation_mode": pref.automation_mode if pref else "draft_only",
            "daily_reply_limit": pref.daily_reply_limit if pref else 20,
        } if pref else {},
        "signatures": [
            {
                "id": s.id,
                "name": s.name,
                "sign_off": s.sign_off,
                "is_default_new": s.is_default_new,
                "is_default_reply": s.is_default_reply,
            }
            for s in sigs
        ],
        "automation_rules": [
            {
                "id": r.id,
                "name": r.name,
                "is_active": r.is_active,
                "auto_send": r.auto_send,
                "reply_template": r.reply_template,
            }
            for r in rules
        ],
        "emails_count": len(emails),
        "tasks_count": len(tasks),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    return APIResponse(
        success=True,
        data=export_bundle,
        message="User data package exported successfully",
    )


@router.delete("/me", response_model=APIResponse, summary="Delete User Account and All Data")
async def delete_user_account(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Permanently delete customer account and all associated tenant data:
    connected accounts, emails, drafts, signatures, rules, preferences, tasks, and audit logs.
    """
    user_id = user.id

    # Delete all tenant-associated tables
    await db.execute(Email.__table__.delete().where(Email.user_id == user_id))
    await db.execute(AIReplyDraft.__table__.delete().where(AIReplyDraft.user_id == user_id))
    await db.execute(ConnectedAccount.__table__.delete().where(ConnectedAccount.user_id == user_id))
    await db.execute(EmailSignature.__table__.delete().where(EmailSignature.user_id == user_id))
    await db.execute(AutoReplyRule.__table__.delete().where(AutoReplyRule.user_id == user_id))
    await db.execute(ProcessedMessageLog.__table__.delete().where(ProcessedMessageLog.user_id == user_id))
    await db.execute(Task.__table__.delete().where(Task.user_id == user_id))
    await db.execute(CalendarEvent.__table__.delete().where(CalendarEvent.user_id == user_id))
    await db.execute(Notification.__table__.delete().where(Notification.user_id == user_id))
    await db.execute(UserPreferences.__table__.delete().where(UserPreferences.user_id == user_id))
    await db.execute(AuditLog.__table__.delete().where(AuditLog.user_id == user_id))

    # Delete the user record
    await db.delete(user)
    await db.commit()

    return APIResponse(
        success=True,
        message="Account and all associated customer data permanently deleted.",
    )
