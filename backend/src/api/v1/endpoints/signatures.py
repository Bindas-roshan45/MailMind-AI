"""
Email Signatures Endpoints.
Supports multiple named signatures per user, default signature for new emails vs replies,
and personal sign-offs.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_session
from src.models import EmailSignature, User
from src.schemas import APIResponse

router = APIRouter()


class SignatureCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="e.g. Work Default, Mobile")
    sender_name: str = Field(..., min_length=1, max_length=255)
    job_title: Optional[str] = None
    company: Optional[str] = None
    sign_off: str = Field(default="Best regards")
    custom_sign_off: Optional[str] = None
    phone: Optional[str] = None
    content_html: Optional[str] = None
    content_text: str = Field(..., min_length=1)
    is_default_new: bool = False
    is_default_reply: bool = False


class SignatureUpdate(BaseModel):
    name: Optional[str] = None
    sender_name: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    sign_off: Optional[str] = None
    custom_sign_off: Optional[str] = None
    phone: Optional[str] = None
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    is_default_new: Optional[bool] = None
    is_default_reply: Optional[bool] = None


@router.get("", response_model=APIResponse)
async def list_signatures(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List all email signatures belonging to the authenticated user."""
    query = (
        select(EmailSignature)
        .where(EmailSignature.user_id == current_user.id)
        .order_by(EmailSignature.is_default_new.desc(), EmailSignature.id.desc())
    )
    result = await db.execute(query)
    signatures = result.scalars().all()

    items = [
        {
            "id": s.id,
            "name": s.name,
            "sender_name": s.sender_name,
            "job_title": s.job_title,
            "company": s.company,
            "sign_off": s.sign_off,
            "custom_sign_off": s.custom_sign_off,
            "phone": s.phone,
            "content_html": s.content_html,
            "content_text": s.content_text,
            "is_default_new": s.is_default_new,
            "is_default_reply": s.is_default_reply,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signatures
    ]
    return APIResponse(success=True, data=items)


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_signature(
    payload: SignatureCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new named email signature."""
    # If set as default, reset other defaults for this user
    if payload.is_default_new:
        existing_new = await db.execute(
            select(EmailSignature).where(EmailSignature.user_id == current_user.id, EmailSignature.is_default_new == True)
        )
        for s in existing_new.scalars().all():
            s.is_default_new = False
            db.add(s)

    if payload.is_default_reply:
        existing_reply = await db.execute(
            select(EmailSignature).where(EmailSignature.user_id == current_user.id, EmailSignature.is_default_reply == True)
        )
        for s in existing_reply.scalars().all():
            s.is_default_reply = False
            db.add(s)

    sig = EmailSignature(
        user_id=current_user.id,
        name=payload.name,
        sender_name=payload.sender_name,
        job_title=payload.job_title,
        company=payload.company,
        sign_off=payload.sign_off,
        custom_sign_off=payload.custom_sign_off,
        phone=payload.phone,
        content_html=payload.content_html,
        content_text=payload.content_text,
        is_default_new=payload.is_default_new,
        is_default_reply=payload.is_default_reply,
    )
    db.add(sig)
    await db.commit()
    await db.refresh(sig)

    return APIResponse(
        success=True,
        message="Signature created successfully",
        data={
            "id": sig.id,
            "name": sig.name,
            "sender_name": sig.sender_name,
            "is_default_new": sig.is_default_new,
            "is_default_reply": sig.is_default_reply,
            "content_text": sig.content_text,
        },
    )


@router.put("/{sig_id}", response_model=APIResponse)
async def update_signature(
    sig_id: int,
    payload: SignatureUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update an existing signature."""
    result = await db.execute(
        select(EmailSignature).where(EmailSignature.id == sig_id, EmailSignature.user_id == current_user.id)
    )
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signature not found")

    update_data = payload.model_dump(exclude_unset=True)

    if update_data.get("is_default_new"):
        existing_new = await db.execute(
            select(EmailSignature).where(
                EmailSignature.user_id == current_user.id,
                EmailSignature.id != sig_id,
                EmailSignature.is_default_new == True,
            )
        )
        for s in existing_new.scalars().all():
            s.is_default_new = False
            db.add(s)

    if update_data.get("is_default_reply"):
        existing_reply = await db.execute(
            select(EmailSignature).where(
                EmailSignature.user_id == current_user.id,
                EmailSignature.id != sig_id,
                EmailSignature.is_default_reply == True,
            )
        )
        for s in existing_reply.scalars().all():
            s.is_default_reply = False
            db.add(s)

    for field, val in update_data.items():
        setattr(sig, field, val)

    sig.updated_at = datetime.now(timezone.utc)
    db.add(sig)
    await db.commit()
    await db.refresh(sig)

    return APIResponse(
        success=True,
        message="Signature updated successfully",
        data={"id": sig.id, "name": sig.name, "is_default_new": sig.is_default_new, "is_default_reply": sig.is_default_reply},
    )


@router.delete("/{sig_id}", response_model=APIResponse)

async def delete_signature(
    sig_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete a signature."""
    result = await db.execute(
        select(EmailSignature).where(EmailSignature.id == sig_id, EmailSignature.user_id == current_user.id)
    )
    sig = result.scalar_one_or_none()
    if not sig:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signature not found")

    await db.delete(sig)
    await db.commit()
    return APIResponse(success=True, message="Signature deleted successfully")
