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
