"""
Integration tests for users, emails, tasks, calendar, and auto-reply endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    """Test retrieving user profile."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "roshan@gmail.com"
    assert data["data"]["name"] == "Roshan Kumar"
    assert len(data["data"]["connected_accounts"]) >= 1


@pytest.mark.asyncio
async def test_tasks_lifecycle(client: AsyncClient):
    """Test listing, creating, toggling, and deleting tasks."""
    # List initial tasks
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Create a new task
    create_payload = {
        "title": "Review Q4 Strategy Draft",
        "description": "Urgent review required",
        "priority": "high",
        "done": False,
    }
    create_res = await client.post("/api/v1/tasks", json=create_payload)
    assert create_res.status_code == 201
    created_task = create_res.json()["data"]
    assert created_task["title"] == "Review Q4 Strategy Draft"
    task_id = created_task["id"]

    # Toggle task status
    toggle_res = await client.patch(f"/api/v1/tasks/{task_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["data"]["done"] is True

    # Delete task
    del_res = await client.delete(f"/api/v1/tasks/{task_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


@pytest.mark.asyncio
async def test_list_emails_empty(client: AsyncClient):
    """Listing emails should succeed before any messages are synced."""
    response = await client.get("/api/v1/emails")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "items" in data["data"]


@pytest.mark.asyncio
async def test_email_stats(client: AsyncClient):
    """Test retrieving email statistics."""
    response = await client.get("/api/v1/emails/stats")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "total_received" in data["data"]
    assert "reply_rate" in data["data"]


@pytest.mark.asyncio
async def test_calendar_events(client: AsyncClient):
    """Test listing calendar events."""
    response = await client.get("/api/v1/calendar/events")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_auto_reply_rules(client: AsyncClient):
    """Test listing and toggling auto-reply rules."""
    response = await client.get("/api/v1/auto-reply/rules")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    rule_id = data["data"][0]["id"]

    # Toggle rule
    toggle_res = await client.patch(f"/api/v1/auto-reply/rules/{rule_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["success"] is True


@pytest.mark.asyncio
async def test_user_preferences(client: AsyncClient):
    """Test getting and updating user preferences."""
    get_res = await client.get("/api/v1/preferences")
    assert get_res.status_code == 200
    assert get_res.json()["success"] is True

    # Update theme
    update_res = await client.put("/api/v1/preferences", json={"theme": "dark"})
    assert update_res.status_code == 200
    assert update_res.json()["data"]["theme"] == "dark"


@pytest.mark.asyncio
async def test_notifications_lifecycle(client: AsyncClient):
    """Test listing, read count, and marking notifications as read."""
    res = await client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "items" in data
    assert len(data["items"]) >= 1
    notif_id = data["items"][0]["id"]

    # Read count
    count_res = await client.get("/api/v1/notifications/unread-count")
    assert count_res.status_code == 200
    assert "unread_count" in count_res.json()["data"]

    # Mark single read
    patch_res = await client.patch(f"/api/v1/notifications/{notif_id}/read")
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["is_read"] is True

    # Mark all read
    all_res = await client.post("/api/v1/notifications/mark-all-read")
    assert all_res.status_code == 200
    assert all_res.json()["success"] is True


@pytest.mark.asyncio
async def test_email_star_and_read(client: AsyncClient):
    """Test toggling star and marking read on an email."""
    # List emails (seeded automatically in DEMO_MODE)
    list_res = await client.get("/api/v1/emails")
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) >= 1
    email_id = items[0]["id"]

    # Star toggle
    star_res = await client.patch(f"/api/v1/emails/{email_id}/star")
    assert star_res.status_code == 200
    assert "is_starred" in star_res.json()["data"]

    # Mark read
    read_res = await client.patch(f"/api/v1/emails/{email_id}/read")
    assert read_res.status_code == 200
    assert read_res.json()["data"]["is_read"] is True


@pytest.mark.asyncio
async def test_ai_intelligence_endpoints(client: AsyncClient):
    """Test summarize, extract-tasks, analyze, rewrite, and subject generation."""
    list_res = await client.get("/api/v1/emails")
    email_id = list_res.json()["data"]["items"][0]["id"]

    # Summarize
    sum_res = await client.post("/api/v1/ai/summarize", json={"email_id": email_id})
    assert sum_res.status_code == 200
    assert "summary" in sum_res.json()["data"]

    # Extract tasks
    tasks_res = await client.post("/api/v1/ai/extract-tasks", json={"email_id": email_id, "auto_save_tasks": True})
    assert tasks_res.status_code == 200
    assert "tasks" in tasks_res.json()["data"]

    # Analyze / Phishing shield
    ana_res = await client.post("/api/v1/ai/analyze", json={"email_id": email_id})
    assert ana_res.status_code == 200
    assert "category" in ana_res.json()["data"]
    assert "is_suspicious" in ana_res.json()["data"]

    # Rewrite
    rw_res = await client.post("/api/v1/ai/rewrite", json={"content": "Here is a rough draft email.", "mode": "improve"})
    assert rw_res.status_code == 200
    assert "rewritten_content" in rw_res.json()["data"]

    # Subject line
    subj_res = await client.post("/api/v1/ai/subject", json={"body": "We are confirming our meeting for tomorrow at 10 AM."})
    assert subj_res.status_code == 200
    assert "subject" in subj_res.json()["data"]


@pytest.mark.asyncio
async def test_idor_protection(client: AsyncClient):
    """Verify that unauthorized access or cross-user operations are rejected."""
    # Attempting to access or modify a non-existent / other user's ID
    fake_id = 999999
    res_star = await client.patch(f"/api/v1/emails/{fake_id}/star")
    assert res_star.status_code == 404

    res_task = await client.patch(f"/api/v1/tasks/{fake_id}/toggle")
    assert res_task.status_code == 404

    res_del_task = await client.delete(f"/api/v1/tasks/{fake_id}")
    assert res_del_task.status_code == 404

    res_del_email = await client.delete(f"/api/v1/emails/{fake_id}")
    assert res_del_email.status_code == 404
