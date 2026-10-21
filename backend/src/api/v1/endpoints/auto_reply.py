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
