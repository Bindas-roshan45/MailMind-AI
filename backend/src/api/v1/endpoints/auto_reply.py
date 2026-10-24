"""
Auto-reply rules and AI draft endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.database import get_session
from src.api.deps import get_current_user
from src.schemas import (
    AutoReplyRuleCreate,
    AutoReplyRuleUpdate,
    AutoReplyRuleResponse,
    AIReplyDraftCreate,
    AIReplyDraftResponse,
    APIResponse,
)
from src.models import AutoReplyRule, AIReplyDraft, User, EmailCategory

router = APIRouter()


@router.get("/rules", response_model=APIResponse, summary="List Auto-Reply Rules")
async def list_rules(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List all auto-reply rules configured for current user."""
    result = await db.execute(
        select(AutoReplyRule).where(AutoReplyRule.user_id == user.id)
    )
    rules = list(result.scalars().all())

    if not rules:
        # Create default initial rules matching dashboard AI modes
        default_rule = AutoReplyRule(
            user_id=user.id,
            name="General Inquiries Confirmation",
            category=EmailCategory.CLIENT,
            keywords=["pricing", "quote", "services"],
            reply_template="Hi, thank you for reaching out! We received your inquiry and will follow up shortly.",
            is_active=True,
            auto_send=False,
        )
        db.add(default_rule)
        await db.commit()
        await db.refresh(default_rule)
        rules.append(default_rule)

    data = [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category.value if r.category else None,
            "keywords": r.keywords or [],
            "reply_template": r.reply_template,
            "is_active": r.is_active,
            "auto_send": r.auto_send,
        }
        for r in rules
    ]

    return APIResponse(success=True, data=data, message="Auto-reply rules retrieved")


@router.post("/rules", response_model=APIResponse, status_code=status.HTTP_201_CREATED, summary="Create Auto-Reply Rule")
async def create_rule(
    rule_in: AutoReplyRuleCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Create a new auto-reply rule."""
    rule = AutoReplyRule(
        user_id=user.id,
        name=rule_in.name,
        category=rule_in.category,
        sender_pattern=rule_in.sender_pattern,
        keywords=rule_in.keywords,
        reply_template=rule_in.reply_template,
        is_active=rule_in.is_active,
        auto_send=rule_in.auto_send,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return APIResponse(
        success=True,
        data={"id": rule.id, "name": rule.name, "is_active": rule.is_active},
        message="Auto-reply rule created",
    )


@router.patch("/rules/{rule_id}/toggle", response_model=APIResponse, summary="Toggle Auto-Reply Rule")
async def toggle_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Toggle an auto-reply rule on/off."""
    result = await db.execute(
        select(AutoReplyRule).where(
            AutoReplyRule.id == rule_id, AutoReplyRule.user_id == user.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    rule.is_active = not rule.is_active
    await db.commit()
    await db.refresh(rule)

    return APIResponse(
        success=True,
        data={"id": rule.id, "is_active": rule.is_active},
        message=f"Rule {'enabled' if rule.is_active else 'paused'}",
    )


@router.delete("/rules/{rule_id}", response_model=APIResponse, summary="Delete Auto-Reply Rule")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete an auto-reply rule."""
    result = await db.execute(
        select(AutoReplyRule).where(
            AutoReplyRule.id == rule_id, AutoReplyRule.user_id == user.id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    await db.delete(rule)
    await db.commit()
    return APIResponse(success=True, message="Rule deleted successfully")


from pydantic import BaseModel

class PauseTogglePayload(BaseModel):
    paused: bool


@router.post("/pause", response_model=APIResponse, summary="Global Automation Pause Switch")
async def toggle_global_pause(
    payload: PauseTogglePayload,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Immediate global pause switch for all auto-replies and automation."""
    from src.models import UserPreferences
    pref_res = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    pref = pref_res.scalar_one_or_none()
    if not pref:
        pref = UserPreferences(user_id=user.id, automation_paused=payload.paused)
        db.add(pref)
    else:
        pref.automation_paused = payload.paused
        db.add(pref)

    await db.commit()
    return APIResponse(
        success=True,
        message=f"Automation {'paused' if payload.paused else 'resumed'}",
        data={"automation_paused": payload.paused},
    )


@router.get("/logs", response_model=APIResponse, summary="Recent Automation Activity Logs")
async def get_automation_logs(
    limit: int = 30,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Retrieve processed message logs and automation decision history."""
    from src.models import ProcessedMessageLog
    from sqlalchemy import desc

    result = await db.execute(
        select(ProcessedMessageLog)
        .where(ProcessedMessageLog.user_id == user.id)
        .order_by(desc(ProcessedMessageLog.created_at))
        .limit(limit)
    )
    logs = result.scalars().all()
    items = [
        {
            "id": l.id,
            "message_id": l.message_id,
            "thread_id": l.thread_id,
            "action_taken": l.action_taken,
            "reason": l.reason,
            "rule_id": l.rule_id,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
    return APIResponse(success=True, data=items, message="Automation logs retrieved")


@router.post("/evaluate/{email_id}", response_model=APIResponse, summary="Evaluate/Preview Automation for Email")
async def evaluate_email_for_automation(
    email_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Preview what the automation engine would do on an email without sending or mutating."""
    from src.models import Email, UserPreferences
    from src.core.automation_engine import automation_engine

    email_res = await db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user.id)
    )
    email = email_res.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    pref_res = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user.id)
    )
    pref = pref_res.scalar_one_or_none()

    decision = await automation_engine.evaluate_email_for_automation(db, user, email, pref)
    return APIResponse(success=True, data=decision.to_dict(), message="Evaluation completed")
