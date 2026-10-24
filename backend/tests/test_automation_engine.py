"""
Unit and integration tests for the Automation Engine, sensitivity detection,
safety guardrails, loop prevention, and multi-signature endpoints.
"""
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.automation_engine import automation_engine
from src.crud.user import user_crud
from src.models import (
    AutoReplyRule,
    Email,
    EmailCategory,
    EmailSignature,
    EmailUrgency,
    ProcessedMessageLog,
    User,
    UserPlan,
    UserPreferences,
)


@pytest.mark.asyncio
async def test_sensitivity_financial_topics(db_session: AsyncSession):
    """Financial transfer, bank details, and invoice payments must be flagged sensitive."""
    is_sens, reason = automation_engine.assess_sensitivity(
        subject="Urgent wire transfer required",
        body="Please send the payment to our new routing number and bank account.",
    )
    assert is_sens is True
    assert "Financial matter" in reason


@pytest.mark.asyncio
async def test_sensitivity_legal_and_security(db_session: AsyncSession):
    """Legal threats and security/password resets must be flagged sensitive."""
    is_sens_legal, reason_legal = automation_engine.assess_sensitivity(
        subject="Notice of Lawsuit",
        body="This is an official legal notice regarding breach of contract.",
    )
    assert is_sens_legal is True
    assert "Legal topic" in reason_legal

    is_sens_sec, reason_sec = automation_engine.assess_sensitivity(
        subject="Security alert: Unauthorized login",
        body="Your password reset code and 2fa verification code are required.",
    )
    assert is_sens_sec is True
    assert "Security or credential" in reason_sec


@pytest.mark.asyncio
async def test_automated_sender_detection():
    """No-reply and mailer daemon addresses must be recognized as automated."""
    assert automation_engine.is_automated_sender("no-reply@github.com") is True
    assert automation_engine.is_automated_sender("mailer-daemon@googlemail.com") is True
    assert automation_engine.is_automated_sender("sarah.smith@acme.com") is False


@pytest.mark.asyncio
async def test_self_email_and_blocklist_skipped(db_session: AsyncSession):
    """Emails from the user's own address or on blocklist must be skipped."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan", plan=UserPlan.PRO)

    email_self = Email(
        user_id=user.id,
        from_email="roshan@gmail.com",
        from_name="Me",
        to="roshan@gmail.com",
        subject="Note to self",
        body="Remember to check the deployment",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.PERSONAL,
        urgency=EmailUrgency.LOW,
    )
    decision = await automation_engine.evaluate_email_for_automation(db_session, user, email_self)
    assert decision.action == "SKIP"
    assert "own email" in decision.reason

    # Blocklist test
    pref = UserPreferences(user_id=user.id, sender_blocklist=["spammer@spam.org"])
    email_blocked = Email(
        user_id=user.id,
        from_email="spammer@spam.org",
        from_name="Spam Bot",
        to="roshan@gmail.com",
        subject="Win cash now",
        body="Click here to win a car",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.PROMOTIONS,
        urgency=EmailUrgency.LOW,
    )
    decision_block = await automation_engine.evaluate_email_for_automation(
        db_session, user, email_blocked, preferences=pref
    )
    assert decision_block.action == "SKIP"
    assert "blocklist" in decision_block.reason


@pytest.mark.asyncio
async def test_duplicate_prevention_via_processed_log(db_session: AsyncSession):
    """If a message_id has already been processed, it must be skipped."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan", plan=UserPlan.PRO)

    log = ProcessedMessageLog(
        user_id=user.id,
        message_id="msg_unique_101",
        action_taken="DRAFT_CREATED",
        reason="First run",
    )
    db_session.add(log)
    await db_session.commit()

    email_dup = Email(
        user_id=user.id,
        message_id="msg_unique_101",
        from_email="client@partner.com",
        from_name="Client Partner",
        to="roshan@gmail.com",
        subject="Project Followup",
        body="Following up on our discussions",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.CLIENT,
        urgency=EmailUrgency.MEDIUM,
    )
    decision = await automation_engine.evaluate_email_for_automation(db_session, user, email_dup)
    assert decision.action == "SKIP"
    assert "already been processed" in decision.reason


@pytest.mark.asyncio
async def test_global_pause_forces_draft_only(db_session: AsyncSession):
    """When automation is paused globally, all automation is downgraded to draft only."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan", plan=UserPlan.PRO)

    pref = UserPreferences(user_id=user.id, automation_paused=True, automation_mode="auto_reply")
    email = Email(
        user_id=user.id,
        message_id="msg_paused_test",
        from_email="inquiry@startup.io",
        from_name="Startup Founder",
        to="roshan@gmail.com",
        subject="API Integration",
        body="Can we schedule a call to discuss API integration?",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.WORK,
        urgency=EmailUrgency.MEDIUM,
        ai_confidence=95,
    )
    decision = await automation_engine.evaluate_email_for_automation(db_session, user, email, preferences=pref)
    assert decision.action == "DRAFT_ONLY"
    assert "globally paused" in decision.reason


@pytest.mark.asyncio
async def test_auto_send_only_with_explicit_matching_rule(db_session: AsyncSession):
    """Auto-send triggers ONLY when user configured an active rule with auto_send=True and mode is auto_reply."""
    user = await user_crud.get_by_email(db_session, "roshan@gmail.com")
    if not user:
        user = await user_crud.create(db_session, email="roshan@gmail.com", name="Roshan", plan=UserPlan.PRO)

    pref = UserPreferences(
        user_id=user.id,
        automation_paused=False,
        automation_mode="auto_reply",
        min_confidence_score=80,
    )

    rule = AutoReplyRule(
        user_id=user.id,
        name="Auto-Acknowledge Inquiries",
        category=EmailCategory.CLIENT,
        keywords=["demo", "meeting"],
        reply_template="Thanks! I will gladly set up a meeting for this demo.",
        is_active=True,
        auto_send=True,
    )
    db_session.add(rule)
    await db_session.commit()

    email_matching = Email(
        user_id=user.id,
        message_id="msg_rule_match_99",
        from_email="lead@customer.com",
        from_name="Prospective Customer",
        to="roshan@gmail.com",
        subject="Request for product demo",
        body="We would love to book a meeting for a product demo this week.",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.CLIENT,
        urgency=EmailUrgency.HIGH,
        ai_confidence=92,
    )

    decision = await automation_engine.evaluate_email_for_automation(
        db_session, user, email_matching, preferences=pref
    )
    assert decision.action == "AUTO_SEND"
    assert decision.rule_id == rule.id
    assert decision.reply_content == rule.reply_template


@pytest.mark.asyncio
async def test_signatures_lifecycle_api(client: AsyncClient):
    """Test creating, listing, updating, and deleting email signatures."""
    # 1. Create a signature
    sig_payload = {
        "name": "Work Pro",
        "sender_name": "Roshan Kumar",
        "job_title": "Founder & Lead Architect",
        "company": "MailMind AI",
        "sign_off": "Best regards",
        "phone": "+1 (555) 019-2831",
        "content_text": "Roshan Kumar\nFounder & Lead Architect | MailMind AI",
        "is_default_new": True,
        "is_default_reply": True,
    }
    create_res = await client.post("/api/v1/signatures", json=sig_payload)
    assert create_res.status_code == 201
    sig_id = create_res.json()["data"]["id"]

    # 2. List signatures
    list_res = await client.get("/api/v1/signatures")
    assert list_res.status_code == 200
    items = list_res.json()["data"]
    assert any(s["id"] == sig_id for s in items)

    # 3. Update signature
    update_res = await client.put(f"/api/v1/signatures/{sig_id}", json={"company": "MailMind Inc."})
    assert update_res.status_code == 200

    # 4. Delete signature
    del_res = await client.delete(f"/api/v1/signatures/{sig_id}")
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_automation_rules_and_pause_api(client: AsyncClient):
    """Test auto-reply rules CRUD, pause toggle, and logs via API."""
    # Create rule
    rule_res = await client.post("/api/v1/auto-reply/rules", json={
        "name": "Support Acknowledgment",
        "category": "Work",
        "reply_template": "Your ticket has been received.",
        "auto_send": False,
    })
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["data"]["id"]

    # Toggle pause
    pause_res = await client.post("/api/v1/auto-reply/pause", json={"paused": True})
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["automation_paused"] is True

    # Resume
    resume_res = await client.post("/api/v1/auto-reply/pause", json={"paused": False})
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["automation_paused"] is False

    # Get logs
    logs_res = await client.get("/api/v1/auto-reply/logs")
    assert logs_res.status_code == 200
    assert isinstance(logs_res.json()["data"], list)

    # Delete rule
    del_res = await client.delete(f"/api/v1/auto-reply/rules/{rule_id}")
    assert del_res.status_code == 200
