"""Tests for JWT session architecture (no Gmail OAuth)."""
import pytest
from httpx import AsyncClient

from src.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_password,
)


def test_jwt_roundtrip():
    token = create_access_token(subject=1, extra_claims={"email": "roshan@gmail.com"})
    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["email"] == "roshan@gmail.com"


def test_password_hash_roundtrip():
    hashed = hash_password("phase1-test-password")
    assert hashed != "phase1-test-password"
    assert verify_password("phase1-test-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_secret_encryption_roundtrip():
    stored = encrypt_secret("oauth-refresh-token-example")
    assert stored != "oauth-refresh-token-example"
    assert decrypt_secret(stored) == "oauth-refresh-token-example"


@pytest.mark.asyncio
async def test_demo_token_and_auth_me(client: AsyncClient):
    token_res = await client.post("/api/v1/auth/demo-token")
    assert token_res.status_code == 200
    body = token_res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    data = me.json()
    assert data["success"] is True
    assert data["data"]["email"] == "roshan@gmail.com"


@pytest.mark.asyncio
async def test_invalid_bearer_is_rejected(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
