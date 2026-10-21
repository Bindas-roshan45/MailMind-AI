"""
AI Reply Draft Generation and Approval Endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field

from src.database import get_session
from src.api.deps import get_current_user
from src.core.ai import ai_engine
from src.models import AIReplyDraft, Email, User
from src.schemas import APIResponse

router = APIRouter()

class DraftGenerationRequest(BaseModel):
    email_id: int
    tone: str = Field(default="professional", description="Tone: professional, friendly, formal")
    language: str = Field(default="english")

class DraftApprovalRequest(BaseModel):
    is_approved: bool

@router.post("/generate-draft", response_model=APIResponse, status_code=status.HTTP_201_CREATED, summary="Generate AI Reply Draft")
async def generate_draft(
    payload: DraftGenerationRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Generate an AI reply draft for an email with a given tone (Professional, Friendly, Formal).
    Does NOT send the email automatically; requires user approval.
    """
    # 1. Fetch email
    email = await db.get(Email, payload.email_id)
    if not email or email.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    # 2. Generate reply content via AIEngine
    reply_content = await ai_engine.generate_reply(
        email_subject=email.subject,
        email_body=email.body or email.preview or "",
        tone=payload.tone
    )

    # 3. Save draft in database (is_approved=False by default)
    draft = AIReplyDraft(
        email_id=email.id,
        user_id=user.id,
        tone=payload.tone,
        language=payload.language,
        content=reply_content,
        is_approved=False,
        is_sent=False
    )
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data={
            "draft_id": draft.id,
            "email_id": draft.email_id,
            "tone": draft.tone,
            "content": draft.content,
            "is_approved": draft.is_approved,
            "is_sent": draft.is_sent,
        },
        message="AI reply draft generated successfully and saved for approval."
    )


@router.post("/drafts/{draft_id}/approve", response_model=APIResponse, summary="Approve AI Reply Draft")
async def approve_draft(
    draft_id: int,
    payload: DraftApprovalRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Approve or reject an AI reply draft.
    """
    draft = await db.get(AIReplyDraft, draft_id)
    if not draft or draft.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    draft.is_approved = payload.is_approved
    db.add(draft)
    await db.commit()
    await db.refresh(draft)

    return APIResponse(
        success=True,
        data={
            "draft_id": draft.id,
            "is_approved": draft.is_approved,
        },
        message=f"Draft {'approved' if draft.is_approved else 'unapproved'} successfully."
    )
