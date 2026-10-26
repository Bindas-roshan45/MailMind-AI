"""
Production Bug Regression Test Suite for MailMind AI.

Verifies fixes for:
- Bug 1: Generic and robotic AI replies (financial assistance, ordinary business inquiries, empty bodies, provider fallback status)
- Bug 2: Wrong signature (saved user signature, missing signature, duplicate prevention, no 'MailMind AI User')
- Bug 3: Sensitive-email approval workflow (classification, safety intercept, human confirmation requirement)
- Bug 4: Auto-reply rules (Draft Only vs Auto-Send action toggle, worker status, safety guardrails, idempotency)
"""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import select

from src.core.ai import (
    _build_smart_draft,
    _format_signature,
    _attach_signature_once,
    _resolve_tone,
    AIEngine,
)
from src.models import (
    User,
    EmailSignature,
    AutoReplyRule,
)
from src.core.automation_engine import automation_engine
from src.core.security import create_access_token


# ==============================================================================
# BUG 1 REGRESSION TESTS: Generic and robotic AI replies
# ==============================================================================

def test_bug1_financial_assistance_no_robotic_ai_persona():
    """
    Regression: AI draft must NOT reply:
    'I have received your request for financial assistance. However, I am an artificial intelligence assistant and am unable to provide monetary funds.'
    Instead, it must draft on behalf of the recipient, acknowledge receipt, and route for human review.
    """
    draft = _build_smart_draft(
        subject="Urgent Request for Financial Assistance and Project Grant",
        body="Dear Roshan, We are requesting financial assistance of $5,000 for our non-profit event.",
        tone="professional",
        sender_name="Alex Smith",
        user_name="Roshan Kumar",
    )

    lower = draft.lower()
    # Must NOT claim to be an AI or state inability as an AI
    assert "artificial intelligence" not in lower
    assert "ai assistant" not in lower
    assert "unable to provide monetary funds" not in lower
    assert "as an ai" not in lower

    # Must politely acknowledge receipt and indicate review
    assert "received your request" in lower or "reviewing the details" in lower or "thank you" in lower
    # Must include user context / name
    assert "Roshan Kumar" in draft


def test_bug1_ordinary_business_inquiry_natural_draft():
    """
    Ordinary business inquiry should generate a direct, natural reply asking for
    available meeting times or addressing questions.
    """
    draft = _build_smart_draft(
        subject="Enterprise Pricing & Product Demo Inquiry",
        body="Hi team, I would like to schedule a 30-minute demo to review your SOC2 compliance and enterprise pricing.",
        tone="professional",
        sender_name="Sarah Connor",
        user_name="Roshan Kumar",
    )
    lower = draft.lower()
    assert "demo" in lower or "pricing" in lower or "schedule" in lower or "discuss" in lower
    assert "artificial intelligence" not in lower
    assert "Roshan Kumar" in draft


def test_bug1_empty_email_body_handles_gracefully():
    """Empty or whitespace-only bodies must ask for details instead of generic refusal or error."""
    draft = _build_smart_draft(
        subject="Quick Question",
        body="   ",
        tone="professional",
        sender_name="Jordan",
        user_name="Roshan Kumar",
    )
    lower = draft.lower()
    assert "details" in lower or "context" in lower
    assert "quick question" in lower
    assert "artificial intelligence" not in lower


@pytest.mark.asyncio
async def test_bug1_fallback_status_exposure_on_provider_error():
    """
    When Gemini or OpenAI fails, generate_reply_with_metadata must expose
    is_fallback=True and provider='smart_heuristic_fallback', without silently faking success.
    """
    engine = AIEngine()
    engine.gemini_key = "invalid-key"
    engine.gemini_model = "non-existent-model"

    # Simulate provider failure
    with patch.object(engine, "_generate_with_gemini", return_value=None):
        text, meta = await engine.generate_reply_with_metadata(
            email_subject="Partnership Discussion",
            email_body="Let's collaborate on the upcoming email AI integration.",
            tone="professional",
            sender_name="Partner Corp",
            user_name="Roshan Kumar",
        )

    assert meta["is_fallback"] is True
    assert meta["provider"] in ("smart_fallback", "smart_heuristic_fallback")
    assert "temporarily unavailable" in meta["notice"]
    assert "Roshan Kumar" in text
    assert "artificial intelligence" not in text.lower()


# ==============================================================================
# BUG 2 REGRESSION TESTS: Wrong signature
# ==============================================================================

def test_bug2_custom_signature_used_and_no_mailmind_ai_user():
    """
    When a custom signature is configured (e.g. Roshan Kumar, Founder | Frame & Function),
    it must be attached to the draft, and 'MailMind AI User' must NEVER appear.
    """
    custom_sig = (
        "Best regards,\n"
        "Roshan Kumar\n"
        "Founder | Frame & Function\n"
        "6203487580"
    )
    draft = _build_smart_draft(
        subject="Design Review",
        body="The Figma files are ready for your review.",
        tone="professional",
        signature_text=custom_sig,
        user_name="Roshan Kumar",
    )

    assert "Founder | Frame & Function" in draft
    assert "6203487580" in draft
    assert "Roshan Kumar" in draft
    assert "MailMind AI User" not in draft


def test_bug2_missing_signature_falls_back_to_user_name_only():
    """
    If no custom signature exists, the sign-off should use the authenticated user's name
    and NEVER 'MailMind AI User'.
    """
    sig = _format_signature(
        sign_off="Best regards",
        signature_text=None,
        user_name="Alice Wonderland",
    )
    assert sig == "Best regards,\nAlice Wonderland"
    assert "MailMind AI User" not in sig


def test_bug2_duplicate_signature_prevention():
    """
    _attach_signature_once must not append a duplicate signature if the body
    already contains it.
    """
    custom_sig = "Best regards,\nRoshan Kumar\nFounder | Frame & Function"
    body = (
        "Hi Alex,\n\n"
        "I have received your proposal and will review it shortly.\n\n"
        "Best regards,\n"
        "Roshan Kumar\n"
        "Founder | Frame & Function"
    )

    result = _attach_signature_once(body, custom_sig)
    # The signature should only appear once
    assert result.count("Founder | Frame & Function") == 1
    assert result.count("Roshan Kumar") == 1


@pytest.mark.asyncio
async def test_bug2_get_user_signature_text_from_db(db_session):
    """
    Verify get_user_signature_text loads the configured signature from DB.
    """
    # Create user
    user = User(
        email="roshan@frameandfunction.com",
        hashed_password="hashed_pw_test",
        name="Roshan Kumar",
    )
    db_session.add(user)
    await db_session.flush()

    # Create email signature
    sig = EmailSignature(
        user_id=user.id,
        name="Business Default",
        sender_name="Roshan Kumar",
        content_text="Best regards,\nRoshan Kumar\nFounder | Frame & Function\n6203487580",
        is_default_reply=True,
    )
    db_session.add(sig)
    await db_session.commit()

    loaded_sig = await automation_engine.get_user_signature_text(db_session, user.id)
    assert loaded_sig is not None
    assert "Founder | Frame & Function" in loaded_sig
    assert "6203487580" in loaded_sig
    assert "MailMind AI User" not in loaded_sig


# ==============================================================================
# BUG 3 REGRESSION TESTS: Sensitive-email approval workflow
# ==============================================================================

@pytest.mark.asyncio
async def test_bug3_sensitive_emails_never_auto_sent(db_session):
    """
    Safety rule: Emails containing wire transfers, banking, payroll, or passwords
    must NEVER be auto-sent, even if a matching rule has auto_send=True.
    """
    from src.models import Email, EmailCategory, EmailUrgency, UserPreferences
    from datetime import datetime, timezone

    user = User(
        email="test_sensitive@mailmind.test",
        hashed_password="hashed_pw_test",
        name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    rule = AutoReplyRule(
        user_id=user.id,
        name="Auto-Confirm Inquiries",
        category="Finance",
        reply_template="Confirmed received.",
        auto_send=True,  # User explicitly turned on auto_send
        is_active=True,
    )
    db_session.add(rule)

    pref = UserPreferences(
        user_id=user.id,
        automation_mode="auto_reply",
        automation_paused=False,
    )
    db_session.add(pref)
    await db_session.commit()

    email_sensitive = Email(
        user_id=user.id,
        message_id="msg_wire_123",
        from_email="external@unknown.com",
        from_name="External",
        to=user.email,
        subject="Urgent: Wire Transfer & Bank Details Update",
        body="Please wire $15,000 to the following routing number immediately.",
        category=EmailCategory.FINANCE,
        urgency=EmailUrgency.HIGH,
        received_at=datetime.now(timezone.utc),
    )

    decision = await automation_engine.evaluate_email_for_automation(
        db_session, user, email_sensitive, preferences=pref
    )

    # Must be APPROVAL_REQUIRED, BLOCKED_SENSITIVE, or DRAFT_ONLY, NEVER AUTO_REPLIED
    assert decision.action in ("APPROVAL_REQUIRED", "BLOCKED_SENSITIVE", "DRAFT_ONLY", "DRAFT_CREATED", "SKIP")
    assert decision.action != "AUTO_REPLIED"
    assert "sensitive" in decision.reason.lower() or "financial" in decision.reason.lower() or "blocked" in decision.reason.lower()


# ==============================================================================
# BUG 4 REGRESSION TESTS: Auto-reply rules (Draft Only vs Auto-Send)
# ==============================================================================

@pytest.mark.asyncio
async def test_bug4_toggle_rule_action_endpoint(client, db_session):
    """
    PATCH /api/v1/automation/rules/{id}/action allows users to toggle
    between Draft Only (auto_send=False) and Auto-Send (auto_send=True).
    """
    user = User(
        email="rule_test@mailmind.test",
        hashed_password="hashed_pw_test",
        name="Rule Tester",
    )
    db_session.add(user)
    await db_session.flush()

    rule = AutoReplyRule(
        user_id=user.id,
        name="General Inquiries Confirmation",
        reply_template="Thank you for reaching out.",
        auto_send=False,  # Default: Draft Only
        is_active=True,
    )
    db_session.add(rule)
    await db_session.commit()

    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Toggle to Auto-Send
    res = await client.patch(
        f"/api/v1/auto-reply/rules/{rule.id}/action",
        json={"auto_send": True},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["auto_send"] is True
    assert "Auto-Send" in data["message"]

    # Toggle back to Draft Only
    res2 = await client.patch(
        f"/api/v1/auto-reply/rules/{rule.id}/action",
        json={"auto_send": False},
        headers=headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["data"]["auto_send"] is False
    assert "Draft Only" in data2["message"]


@pytest.mark.asyncio
async def test_bug4_worker_status_endpoint(client, db_session):
    """
    GET /api/v1/auto-reply/worker-status returns operational status,
    cycles, and Gmail connection state.
    """
    user = User(
        email="worker_check@mailmind.test",
        hashed_password="hashed_pw_test",
        name="Worker Checker",
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(subject=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/auto-reply/worker-status", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "operational_state" in data
    assert "is_gmail_connected" in data
    assert "is_operational" in data


@pytest.mark.asyncio
async def test_bug4_draft_only_rule_never_auto_replies(db_session):
    """
    When a rule has auto_send=False (Draft Only), matching emails MUST create
    a draft and NEVER auto-send.
    """
    from src.models import Email, EmailCategory, EmailUrgency, UserPreferences
    from datetime import datetime, timezone

    user = User(
        email="draft_rule_user@mailmind.test",
        hashed_password="hashed_pw_test",
        name="Draft Only Tester",
    )
    db_session.add(user)
    await db_session.flush()

    rule = AutoReplyRule(
        user_id=user.id,
        name="General Inquiries Confirmation",
        category="Client",
        reply_template="We have received your inquiry and will respond soon.",
        auto_send=False,  # Draft Only
        is_active=True,
    )
    db_session.add(rule)

    pref = UserPreferences(
        user_id=user.id,
        automation_mode="auto_reply",  # Even if global mode is auto_reply
        automation_paused=False,
    )
    db_session.add(pref)
    await db_session.commit()

    email_inquiry = Email(
        user_id=user.id,
        message_id="msg_draft_only_456",
        from_email="client@example.com",
        from_name="Inquiring Client",
        to=user.email,
        subject="General Inquiry about Services",
        body="Hello, what services does your consultancy offer?",
        category=EmailCategory.CLIENT,
        urgency=EmailUrgency.MEDIUM,
        received_at=datetime.now(timezone.utc),
    )

    decision = await automation_engine.evaluate_email_for_automation(
        db_session, user, email_inquiry, preferences=pref
    )

    # Must be DRAFT_ONLY or DRAFT_CREATED, NOT AUTO_REPLIED
    assert decision.action in ("DRAFT_ONLY", "DRAFT_CREATED")
    assert decision.action != "AUTO_REPLIED"
    assert "draft" in decision.reason.lower()
