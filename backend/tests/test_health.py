"""
Tests for health check and root endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Verify GET /api/health returns 200 OK and database status connected."""
    response = await client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "demo_mode" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Verify root GET / returns service information."""
    response = await client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "MailMind AI"
    assert data["status"] == "online"
    assert data["health_check"] == "/api/health"
    assert data["docs_url"] == "/docs"
