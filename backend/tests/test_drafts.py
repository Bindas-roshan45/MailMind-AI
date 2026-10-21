"""
Integration tests for AI draft generation and approval endpoints.

Tests go through the full FastAPI stack with an in-memory SQLite DB.
The AI providers are NOT called — the engine falls back to the smart
draft because no API keys are set in the test environment.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Email, EmailCategory, EmailUrgency
from datetime import datetime, timezone


# ─── Helpers ────────────────────────────────────────────────────────────────

async def _create_email(db: AsyncSession, **overrides) -> Email:
    defaults = dict(
        user_id=1,
        from_name="Test Sender",
        from_email="sender@example.com",
        to="roshan@gmail.com",
        subject="Test Subject",
        body="This is the email body for testing.",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.WORK,
        urgency=EmailUrgency.MEDIUM,
        folder="inbox",
    )
    defaults.update(overrides)
    email = Email(**defaults)
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return email


# ─── Original test (preserved) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_draft_generation_and_approval(client: AsyncClient, db_session: AsyncSession):
    """Test generating a friendly-tone draft then approving it (original test, preserved)."""
    email = await _create_email(
        db_session,
        from_name="Alice Smith",
        from_email="alice@example.com",
        subject="Project Proposal & Pricing",
        body="Hi Roshan, we would like to get a quote for the upcoming integration project.",
        category=EmailCategory.CLIENT,
    )

    # Generate friendly draft
    gen_res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": email.id,
        "tone": "friendly",
        "language": "english",
    })
    assert gen_res.status_code == 201
    gen_data = gen_res.json()
    assert gen_data["success"] is True
    draft_id = gen_data["data"]["draft_id"]
    assert "Hi there," in gen_data["data"]["content"]
    assert gen_data["data"]["is_approved"] is False
    assert gen_data["data"]["is_sent"] is False      # NEVER auto-sent

    # Approve the draft
    approve_res = await client.post(f"/api/v1/ai/drafts/{draft_id}/approve", json={
        "is_approved": True
    })
    assert approve_res.status_code == 200
    approve_data = approve_res.json()
    assert approve_data["success"] is True
    assert approve_data["data"]["is_approved"] is True


# ─── Tone-specific tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_draft_professional_tone(client: AsyncClient, db_session: AsyncSession):
    """Professional tone → Dear Sender / Best regards."""
    email = await _create_email(
        db_session,
        subject="Budget Review Q4",
        body="Please review the Q4 budget proposal.",
        urgency=EmailUrgency.HIGH,
    )

    res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": email.id, "tone": "professional", "language": "english",
    })
    assert res.status_code == 201
    content = res.json()["data"]["content"]
    assert "Dear Sender," in content
    assert "Best regards" in content
    assert res.json()["data"]["is_sent"] is False


@pytest.mark.asyncio
async def test_draft_friendly_tone(client: AsyncClient, db_session: AsyncSession):
    """Friendly tone → Hi there / Cheers."""
    email = await _create_email(
        db_session,
        subject="Weekend Meetup",
        body="Want to grab coffee this weekend?",
        category=EmailCategory.PERSONAL,
        urgency=EmailUrgency.LOW,
    )

    res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": email.id, "tone": "friendly", "language": "english",
    })
    assert res.status_code == 201
    content = res.json()["data"]["content"]
    assert "Hi there," in content
    assert "Cheers" in content
    assert res.json()["data"]["is_sent"] is False


@pytest.mark.asyncio
async def test_draft_formal_tone(client: AsyncClient, db_session: AsyncSession):
    """Formal tone → Dear Sir/Madam / Sincerely."""
    email = await _create_email(
        db_session,
        subject="Contract Amendment Notice",
        body="This is to formally notify you of the contract amendment.",
        urgency=EmailUrgency.URGENT,
    )

    res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": email.id, "tone": "formal", "language": "english",
    })
    assert res.status_code == 201
    content = res.json()["data"]["content"]
    assert "Dear Sir/Madam," in content
    assert "Sincerely" in content
    assert res.json()["data"]["is_sent"] is False


# ─── DB persistence ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_draft_saved_in_database(client: AsyncClient, db_session: AsyncSession):
    """Generated draft must be persisted in the database with correct fields."""
    from src.models import AIReplyDraft
    from sqlalchemy import select

    email = await _create_email(db_session, subject="DB Persistence Test")

    res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": email.id, "tone": "professional", "language": "english",
    })
    assert res.status_code == 201
    draft_id = res.json()["data"]["draft_id"]

    # Verify it's in the DB
    result = await db_session.execute(
        select(AIReplyDraft).where(AIReplyDraft.id == draft_id)
    )
    db_draft = result.scalar_one_or_none()
    assert db_draft is not None
    assert db_draft.tone == "professional"
    assert db_draft.language == "english"
    assert db_draft.is_sent is False
    assert db_draft.is_approved is False
    assert len(db_draft.content) > 0


# ─── Error cases ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_draft_404_for_nonexistent_email(client: AsyncClient, db_session: AsyncSession):
    """Non-existent email_id → 404."""
    res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": 999999, "tone": "professional", "language": "english",
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_draft_approval_404_for_nonexistent_draft(client: AsyncClient, db_session: AsyncSession):
    """Non-existent draft_id approve → 404."""
    res = await client.post("/api/v1/ai/drafts/999999/approve", json={"is_approved": True})
    assert res.status_code == 404


# ─── Contract: never auto-sends ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_tones_never_auto_sent(client: AsyncClient, db_session: AsyncSession):
    """
    Contract test: drafts for all three tones must always have
    is_sent=False and is_approved=False immediately after creation.
    The system must NEVER send emails automatically.
    """
    email = await _create_email(db_session, subject="Auto-Send Safety Test")

    for tone in ["professional", "friendly", "formal"]:
        res = await client.post("/api/v1/ai/generate-draft", json={
            "email_id": email.id, "tone": tone, "language": "english",
        })
        assert res.status_code == 201, f"Failed for tone={tone}"
        data = res.json()["data"]
        assert data["is_sent"] is False,    f"Draft auto-sent for tone={tone}!"
        assert data["is_approved"] is False, f"Draft auto-approved for tone={tone}!"


@pytest.mark.asyncio
async def test_unapprove_then_reapprove_draft(client: AsyncClient, db_session: AsyncSession):
    """Draft can be toggled: approved → unapproved → approved again."""
    email = await _create_email(db_session, subject="Approval Toggle Test")

    gen_res = await client.post("/api/v1/ai/generate-draft", json={
        "email_id": email.id, "tone": "professional", "language": "english",
    })
    draft_id = gen_res.json()["data"]["draft_id"]

    # Approve
    r = await client.post(f"/api/v1/ai/drafts/{draft_id}/approve", json={"is_approved": True})
    assert r.json()["data"]["is_approved"] is True

    # Unapprove
    r = await client.post(f"/api/v1/ai/drafts/{draft_id}/approve", json={"is_approved": False})
    assert r.json()["data"]["is_approved"] is False

    # Re-approve
    r = await client.post(f"/api/v1/ai/drafts/{draft_id}/approve", json={"is_approved": True})
    assert r.json()["data"]["is_approved"] is True


@pytest.mark.asyncio
async def test_generate_draft_standalone_without_email_id(client: AsyncClient):
    """Regression test: generating a draft without email_id (ComposeModal) succeeds without 500."""
    res = await client.post("/api/v1/ai/generate-draft", json={
        "subject": "Website Project Inquiry",
        "body": "Hi, I want a quote for a website.",
        "prompt": "Offer a 2-4 week timeline",
        "tone": "professional",
    })
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["draft_id"] is None
    assert data["email_id"] is None
    assert "content" in data and len(data["content"]) > 0
    assert data["is_approved"] is False
    assert data["is_sent"] is False


@pytest.mark.asyncio
async def test_demo_token_issue_and_user_creation(client: AsyncClient):
    """Regression test: demo token endpoint succeeds and user timestamps/passwords are valid."""
    res = await client.post("/api/v1/auth/demo-token")
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data

    # Use token to call /me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "roshan@gmail.com"
