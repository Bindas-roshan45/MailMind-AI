"""
Security, Multi-Tenant Isolation, and Productivity Integration Tests for MailMind AI.
Validates tenant boundaries, account lifecycle, background worker health, and email productivity features.
"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.background_worker import automation_worker, worker_state
from src.core.security import create_access_token, hash_password
from src.models import (
    Email,
    EmailCategory,
    EmailSignature,
    EmailUrgency,
    User,
    UserPlan,
)


async def create_test_user(db: AsyncSession, email: str, name: str) -> User:
    """Helper to create and persist an active test user."""
    user = User(
        email=email,
        name=name,
        hashed_password=hash_password("SecurePassword123!"),
        is_active=True,
        plan=UserPlan.FREE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_cross_tenant_isolation_rejected(client: AsyncClient, db_session: AsyncSession):
    """
    Ensure User B cannot read, star, move, or delete an email owned by User A.
    Must strictly return 404 Not Found to prevent data leakage.
    """
    user_a = await create_test_user(db_session, "user_a@example.com", "User Alpha")
    user_b = await create_test_user(db_session, "user_b@example.com", "User Beta")

    # Seed email for User A
    email_a = Email(
        user_id=user_a.id,
        message_id="msg-alpha-1",
        from_name="Client Corp",
        from_email="client@corp.com",
        to="user_a@example.com",
        subject="Confidential Strategy Alpha",
        body="Secret business data for User A only.",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.WORK,
        urgency=EmailUrgency.HIGH,
        folder="inbox",
    )
    db_session.add(email_a)
    await db_session.commit()
    await db_session.refresh(email_a)

    token_b = create_access_token(subject=user_b.id, extra_claims={"email": user_b.email})
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B attempts to read User A's email
    res_get = await client.get(f"/api/v1/emails/{email_a.id}", headers=headers_b)
    assert res_get.status_code == 404

    # User B attempts to star User A's email
    res_star = await client.patch(f"/api/v1/emails/{email_a.id}/star", headers=headers_b)
    assert res_star.status_code == 404

    # User B attempts to move User A's email to trash
    res_folder = await client.patch(
        f"/api/v1/emails/{email_a.id}/folder",
        headers=headers_b,
        json={"folder": "trash"},
    )
    assert res_folder.status_code == 404

    # User B attempts to delete User A's email
    res_del = await client.delete(f"/api/v1/emails/{email_a.id}", headers=headers_b)
    assert res_del.status_code == 404


@pytest.mark.asyncio
async def test_email_productivity_folder_and_snooze(client: AsyncClient, db_session: AsyncSession):
    """Test folder movement (archive/trash) and email snoozing with ownership validation."""
    user = await create_test_user(db_session, "prod_user@example.com", "Productive User")
    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    email = Email(
        user_id=user.id,
        message_id="msg-prod-101",
        from_name="Newsletter",
        from_email="news@daily.com",
        to="prod_user@example.com",
        subject="Daily Briefing",
        body="Here is your morning digest.",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.WORK,
        urgency=EmailUrgency.LOW,
        folder="inbox",
    )
    db_session.add(email)
    await db_session.commit()
    await db_session.refresh(email)

    # 1. Move to Archive
    res_archive = await client.patch(
        f"/api/v1/emails/{email.id}/folder",
        headers=headers,
        json={"folder": "archive"},
    )
    assert res_archive.status_code == 200
    assert res_archive.json()["data"]["folder"] == "archive"

    # 2. Snooze Email
    res_snooze = await client.patch(
        f"/api/v1/emails/{email.id}/snooze",
        headers=headers,
        json={"snooze_until": datetime.now(timezone.utc).isoformat()},
    )
    assert res_snooze.status_code == 200
    assert res_snooze.json()["data"]["folder"] == "snoozed"


@pytest.mark.asyncio
async def test_email_draft_creation_and_updating(client: AsyncClient, db_session: AsyncSession):
    """Test saving new drafts and updating existing drafts."""
    user = await create_test_user(db_session, "drafter@example.com", "Drafter User")
    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Save new draft
    res_create = await client.post(
        "/api/v1/emails/draft",
        headers=headers,
        json={
            "to": "partner@example.com",
            "subject": "Proposal Outline",
            "body": "Drafting initial partnership terms...",
        },
    )
    assert res_create.status_code == 200
    draft_id = res_create.json()["data"]["id"]
    assert draft_id is not None

    # Verify saved in drafts folder
    saved = await db_session.get(Email, draft_id)
    assert saved.folder == "drafts"
    assert saved.user_id == user.id

    # 2. Update existing draft
    res_update = await client.post(
        "/api/v1/emails/draft",
        headers=headers,
        json={
            "id": draft_id,
            "to": "partner@example.com",
            "subject": "Updated Proposal Outline",
            "body": "Finalized partnership terms ready for review.",
        },
    )
    assert res_update.status_code == 200
    await db_session.refresh(saved)
    assert saved.subject == "Updated Proposal Outline"
    assert "Finalized" in saved.body


@pytest.mark.asyncio
async def test_user_usage_quotas_and_plan_upgrade(client: AsyncClient, db_session: AsyncSession):
    """Verify subscription plan quotas and user tier upgrade."""
    user = await create_test_user(db_session, "saas_user@example.com", "SaaS Customer")
    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Check default Free tier limits
    res_usage = await client.get("/api/v1/users/me/usage", headers=headers)
    assert res_usage.status_code == 200
    data = res_usage.json()["data"]
    assert data["plan"] == "Free"
    assert data["daily_auto_replies_limit"] == 20
    assert data["max_connected_accounts"] == 1

    # Upgrade to Pro Plan
    res_plan = await client.patch(
        "/api/v1/users/me/plan",
        headers=headers,
        json={"plan": "Pro Plan"},
    )
    assert res_plan.status_code == 200
    assert res_plan.json()["data"]["plan"] == "Pro Plan"

    # Re-verify upgraded limits
    res_usage_pro = await client.get("/api/v1/users/me/usage", headers=headers)
    pro_data = res_usage_pro.json()["data"]
    assert pro_data["plan"] == "Pro Plan"
    assert pro_data["daily_auto_replies_limit"] == 150
    assert pro_data["max_connected_accounts"] == 5


@pytest.mark.asyncio
async def test_user_data_export_and_cascade_account_deletion(client: AsyncClient, db_session: AsyncSession):
    """Verify GDPR data export and cascade deletion of all tenant data."""
    user = await create_test_user(db_session, "export_user@example.com", "Export Customer")
    token = create_access_token(subject=user.id, extra_claims={"email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Add a signature and an email
    sig = EmailSignature(
        user_id=user.id,
        name="Official",
        sender_name="Export Customer",
        sign_off="Best regards",
        content_text="Best regards,\nExport Customer",
        is_default_new=True,
    )
    email = Email(
        user_id=user.id,
        message_id="msg-export-1",
        from_name="Sender",
        from_email="sender@ex.com",
        to=user.email,
        subject="Important Notice",
        body="Body text for export",
        received_at=datetime.now(timezone.utc),
        category=EmailCategory.WORK,
        urgency=EmailUrgency.LOW,
    )
    db_session.add_all([sig, email])
    await db_session.commit()

    # 1. Export Data
    res_export = await client.get("/api/v1/users/me/export", headers=headers)
    assert res_export.status_code == 200
    export_json = res_export.json()["data"]
    assert export_json["user"]["email"] == "export_user@example.com"
    assert export_json["emails_count"] == 1
    assert len(export_json["signatures"]) == 1

    # 2. Delete Account (Cascade deletion)
    res_del = await client.delete("/api/v1/users/me", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Confirm user and emails are eradicated from DB
    deleted_user = await db_session.get(User, user.id)
    assert deleted_user is None

    remaining_emails = await db_session.execute(select(Email).where(Email.user_id == user.id))
    assert len(remaining_emails.scalars().all()) == 0


@pytest.mark.asyncio
async def test_health_includes_background_worker(client: AsyncClient):
    """Ensure /api/v1/health returns background worker monitoring status."""
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert "worker" in data
    assert "is_running" in data["worker"]
    assert "total_cycles" in data["worker"]
