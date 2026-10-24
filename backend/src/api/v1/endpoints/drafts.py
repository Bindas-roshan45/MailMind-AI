"""
AI Reply Draft Generation, Summarization, Extraction, and Approval Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.ai import ai_engine
from src.crud.task import task_crud
from src.database import get_session
from src.models import AIReplyDraft, Email, TaskPriority, User
from src.schemas import APIResponse

router = APIRouter()


from sqlalchemy import select, desc

class DraftGenerationRequest(BaseModel):
    email_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    prompt: Optional[str] = None
    sender: Optional[str] = None
    thread_id: Optional[str] = None
    tone: str = Field(default="professional", description="Tone: professional, friendly, formal, short, detailed")
    language: str = Field(default="english")


class SaveDraftRequest(BaseModel):
    email_id: Optional[int] = None
    draft_id: Optional[int] = None
    content: str = Field(..., min_length=1)
    tone: str = Field(default="professional")
    language: str = Field(default="english")


class DraftApprovalRequest(BaseModel):
    is_approved: bool


class SummarizeRequest(BaseModel):
    email_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class ExtractTasksRequest(BaseModel):
    email_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    auto_save_tasks: bool = False


class AnalyzeRequest(BaseModel):
    email_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    sender: Optional[str] = ""


class RewriteRequest(BaseModel):
    content: str = Field(..., min_length=1)
    mode: str = Field(default="improve", description="shorten, expand, improve, formal, friendly")


class SubjectRequest(BaseModel):
    body: str = Field(..., min_length=1)
    prompt: Optional[str] = None


@router.get("/provider-status", response_model=APIResponse, summary="Get AI Provider Configuration Status")
async def get_provider_status(
    user: User = Depends(get_current_user),
):
    """Return status of configured AI provider and whether API keys are loaded."""
    status_info = ai_engine.get_provider_status()
    return APIResponse(
        success=True,
        data=status_info,
        message=f"AI provider {status_info.get('configured_provider')} status retrieved.",
    )


@router.post("/generate-draft", response_model=APIResponse, status_code=status.HTTP_201_CREATED, summary="Generate AI Reply Draft")
async def generate_draft(
    payload: DraftGenerationRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Generate an AI reply draft for an email with a given tone and language based on actual email content and thread history.
    Does NOT send the email automatically; requires explicit user approval.
    """
    subject = payload.subject or "Message"
    body = payload.body or ""
    sender_name = payload.sender or ""
    thread_history = []
    email_id = payload.email_id

    if email_id is not None:
        email = await db.get(Email, email_id)
        if not email or email.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        subject = email.subject or subject
        body = email.body or email.preview or body
        sender_name = email.from_name or sender_name

        # If email belongs to a thread, retrieve recent context from the thread
        if email.thread_id:
            thread_stmt = (
                select(Email)
                .where(Email.thread_id == email.thread_id, Email.user_id == user.id)
                .order_by(desc(Email.received_at))
                .limit(5)
            )
            result = await db.execute(thread_stmt)
            thread_emails = list(result.scalars().all())
            # Put in chronological order
            thread_emails.reverse()
            for te in thread_emails:
                sender_label = te.from_name or te.from_email
                snippet = (te.body or te.preview or "")[:300].strip()
                thread_history.append(f"{sender_label}: {snippet}")

    if payload.prompt:
        body = f"{body}\n\nAdditional user prompt/instructions: {payload.prompt}"

    # Generate reply content and metadata via AIEngine
    reply_content, metadata = await ai_engine.generate_reply_with_metadata(
        email_subject=subject,
        email_body=body,
        tone=payload.tone,
        language=payload.language,
        sender_name=sender_name,
        thread_history=thread_history,
    )

    # Save draft in database if associated with an email (is_approved=False by default)
    if email_id is not None:
        draft = AIReplyDraft(
            email_id=email_id,
            user_id=user.id,
            tone=payload.tone,
            language=payload.language,
            content=reply_content,
            is_approved=False,
            is_sent=False,
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
                "language": draft.language,
                "content": draft.content,
                "is_approved": draft.is_approved,
                "is_sent": draft.is_sent,
                "ai_metadata": metadata,
            },
            message="AI reply draft generated successfully and saved for approval.",
        )

    # Standalone draft (e.g., composing a new message)
    return APIResponse(
        success=True,
        data={
            "draft_id": None,
            "email_id": None,
            "tone": payload.tone,
            "language": payload.language,
            "content": reply_content,
            "is_approved": False,
            "is_sent": False,
            "ai_metadata": metadata,
        },
        message="AI email draft generated successfully.",
    )


@router.post("/save-draft", response_model=APIResponse, summary="Save or Update AI Reply Draft")
async def save_draft(
    payload: SaveDraftRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Explicitly save or update user-edited draft.
    Does NOT send the email automatically.
    """
    draft = None
    if payload.draft_id:
        draft = await db.get(AIReplyDraft, payload.draft_id)
        if not draft or draft.user_id != user.id:
            draft = None

    if draft:
        draft.content = payload.content
        draft.tone = payload.tone
        draft.language = payload.language
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
    elif payload.email_id:
        email = await db.get(Email, payload.email_id)
        if not email or email.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        draft = AIReplyDraft(
            email_id=payload.email_id,
            user_id=user.id,
            tone=payload.tone,
            language=payload.language,
            content=payload.content,
            is_approved=False,
            is_sent=False,
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email_id or draft_id is required to save a draft",
        )

    return APIResponse(
        success=True,
        data={
            "draft_id": draft.id,
            "email_id": draft.email_id,
            "tone": draft.tone,
            "language": draft.language,
            "content": draft.content,
            "is_approved": draft.is_approved,
            "is_sent": draft.is_sent,
        },
        message="Draft saved successfully.",
    )


@router.post("/drafts/{draft_id}/approve", response_model=APIResponse, summary="Approve AI Reply Draft")
async def approve_draft(
    draft_id: int,
    payload: DraftApprovalRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Approve or reject an AI reply draft."""
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
        message=f"Draft {'approved' if draft.is_approved else 'unapproved'} successfully.",
    )


@router.post("/summarize", response_model=APIResponse, summary="Summarize Email")
async def summarize_email_endpoint(
    payload: SummarizeRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Summarize an email using AI."""
    subject = payload.subject or ""
    body = payload.body or ""

    if payload.email_id:
        email = await db.get(Email, payload.email_id)
        if not email or email.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        subject = email.subject
        body = email.body or email.preview or ""

    result = await ai_engine.summarize_email(subject, body)
    return APIResponse(success=True, data=result, message="Summary generated successfully")


@router.post("/extract-tasks", response_model=APIResponse, summary="Extract Action Items & Deadlines")
async def extract_tasks_endpoint(
    payload: ExtractTasksRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Extract actionable tasks from an email, optionally saving to user tasks."""
    subject = payload.subject or ""
    body = payload.body or ""
    email_id = payload.email_id

    if email_id:
        email = await db.get(Email, email_id)
        if not email or email.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        subject = email.subject
        body = email.body or email.preview or ""

    result = await ai_engine.extract_tasks_and_deadlines(subject, body)

    # Optionally persist extracted tasks directly into the user's task list
    saved_tasks = []
    if payload.auto_save_tasks and result.get("tasks"):
        for item in result["tasks"]:
            p = TaskPriority.MEDIUM
            if item.get("priority") == "high":
                p = TaskPriority.HIGH
            elif item.get("priority") == "low":
                p = TaskPriority.LOW
            created = await task_crud.create(
                db,
                user_id=user.id,
                email_id=email_id,
                title=item.get("title", "Email follow-up task"),
                priority=p,
            )
            saved_tasks.append(created.id)
        await db.commit()

    return APIResponse(
        success=True,
        data={**result, "saved_task_ids": saved_tasks},
        message="Tasks and deadlines extracted",
    )


@router.post("/analyze", response_model=APIResponse, summary="Analyze Email & Phishing Shield")
async def analyze_email_endpoint(
    payload: AnalyzeRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Perform full AI classification, priority assessment, sentiment, and phishing check."""
    subject = payload.subject or ""
    body = payload.body or ""
    sender = payload.sender or ""

    if payload.email_id:
        email = await db.get(Email, payload.email_id)
        if not email or email.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        subject = email.subject
        body = email.body or email.preview or ""
        sender = f"{email.from_name} <{email.from_email}>"

    analysis = await ai_engine.analyze_email(subject, body, sender)
    return APIResponse(success=True, data=analysis, message="Analysis complete")


@router.post("/rewrite", response_model=APIResponse, summary="Rewrite Email Draft")
async def rewrite_draft_endpoint(
    payload: RewriteRequest,
    user: User = Depends(get_current_user),
):
    """Rewrite, shorten, expand, or polish an email draft."""
    result = await ai_engine.rewrite_draft(payload.content, payload.mode)
    return APIResponse(success=True, data=result, message=f"Draft rewritten ({payload.mode})")


@router.post("/subject", response_model=APIResponse, summary="Generate Email Subject")
async def generate_subject_endpoint(
    payload: SubjectRequest,
    user: User = Depends(get_current_user),
):
    """Generate an email subject line based on body content."""
    result = await ai_engine.generate_subject(payload.body, payload.prompt)
    return APIResponse(success=True, data=result, message="Subject generated")
