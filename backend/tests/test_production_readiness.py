"""
Regression and verification tests for production hardening:
1. Security headers on all HTTP responses.
2. Insecure SECRET_KEY rejection when DEMO_MODE is False.
3. Database pooling and migration schema completeness.
4. Ephemeral key stability across session decryptions.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.core.security import encrypt_secret, decrypt_secret


@pytest.mark.asyncio
async def test_production_security_headers_present(client: AsyncClient):
    """Verify standard security headers are attached to all API responses."""
    res = await client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("X-XSS-Protection") == "1; mode=block"


def test_production_config_rejects_insecure_secret_key():
    """Verify that in production mode (DEMO_MODE=False), weak or default SECRET_KEY is rejected."""
    # When DEMO_MODE is False and SECRET_KEY is too short or insecure placeholder
    with pytest.raises(ValueError, match="Security Configuration Error"):
        Settings(
            DEMO_MODE=False,
            SECRET_KEY="short",
        )

    with pytest.raises(ValueError, match="Security Configuration Error"):
        Settings(
            DEMO_MODE=False,
            SECRET_KEY="your_very_long_random_secret_key_here_change_this_in_production",
        )

    # Valid secret in production passes
    valid_settings = Settings(
        DEMO_MODE=False,
        SECRET_KEY="a_very_secure_and_cryptographically_sound_persistent_production_key_123",
    )
    assert valid_settings.DEMO_MODE is False
    assert len(valid_settings.SECRET_KEY) >= 24


def test_fernet_encryption_key_stability():
    """Verify token encryption and decryption remain stable with a consistent key."""
    secret_text = "ya29.a0ARrdaM8SampleGoogleOAuthToken12345"
    enc = encrypt_secret(secret_text)
    assert enc != secret_text

    dec = decrypt_secret(enc)
    assert dec == secret_text


@pytest.mark.asyncio
async def test_health_check_reports_production_readiness(client: AsyncClient):
    """Verify health endpoint reports correct database and worker status."""
    res = await client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "healthy"
    assert body.get("database") == "connected"
    assert "worker" in body


def test_alembic_migrations_postgresql_boolean_defaults():
    """Verify that all Alembic migrations generate valid PostgreSQL boolean defaults without integer 0/1."""
    import io
    from contextlib import redirect_stdout
    import alembic.command
    import alembic.config

    cfg = alembic.config.Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", "postgresql+asyncpg://user:pass@localhost:5432/testdb")

    stdout_buf = io.StringIO()
    with redirect_stdout(stdout_buf):
        alembic.command.upgrade(cfg, "head", sql=True)
    generated_sql = stdout_buf.getvalue()

    # PostgreSQL strict boolean check: defaults must be 'false' or 'true', not integer 0/1
    assert "BOOLEAN DEFAULT 0" not in generated_sql, "Alembic DDL generated invalid 'BOOLEAN DEFAULT 0' for PostgreSQL"
    assert "BOOLEAN DEFAULT 1" not in generated_sql, "Alembic DDL generated invalid 'BOOLEAN DEFAULT 1' for PostgreSQL"
    assert "is_default_new BOOLEAN DEFAULT false NOT NULL" in generated_sql
    assert "is_default_reply BOOLEAN DEFAULT false NOT NULL" in generated_sql
    assert "automation_paused BOOLEAN DEFAULT false NOT NULL" in generated_sql

