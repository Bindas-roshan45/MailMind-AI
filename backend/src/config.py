"""
Configuration settings for MailMind AI backend.
Loads environment variables using Pydantic Settings.
"""
import base64
import hashlib
import secrets
from typing import List, Union

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "MailMind AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    DEMO_MODE: bool = True  # Set to False when real integrations are ready

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Union[str, None], info) -> str:
        if isinstance(v, str) and v.strip():
            url = v.strip()
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url

        # If user and db are configured, build postgres url
        user = info.data.get("POSTGRES_USER")
        password = info.data.get("POSTGRES_PASSWORD")
        server = info.data.get("POSTGRES_SERVER") or "localhost"
        port = str(info.data.get("POSTGRES_PORT") or "5432")
        db = info.data.get("POSTGRES_DB")

        if user and db:
            pwd_part = f":{password}" if password else ""
            return f"postgresql+asyncpg://{user}{pwd_part}@{server}:{port}/{db}"

        # Default development/test fallback when PostgreSQL is not configured
        return "sqlite+aiosqlite:///./mailmind.db"

    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str = ""

    # Google OAuth & Frontend
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:5173"

    # AI Provider (Future phases)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    AI_PROVIDER: str = "gemini"  # default to gemini

    # CORS (CORS_ORIGINS is accepted as an alias from .env.example)
    BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
        ],
        validation_alias=AliasChoices("BACKEND_CORS_ORIGINS", "CORS_ORIGINS"),
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Logging
    LOG_LEVEL: str = "info"

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """Ensure critical security credentials and databases are valid in production."""
        if not self.DEMO_MODE:
            insecure_placeholders = {
                "",
                "your_very_long_random_secret_key_here",
                "your_very_long_random_secret_key_here_change_this_in_production",
                "change_this_in_production",
                "secret",
                "password",
            }
            if self.SECRET_KEY in insecure_placeholders or len(self.SECRET_KEY) < 24:
                raise ValueError(
                    "Security Configuration Error: In production mode (DEMO_MODE=False), "
                    "SECRET_KEY must be an explicitly configured, persistent secret with at least 24 characters."
                )
        return self

    @property
    def fernet_key_bytes(self) -> bytes:
        """32-byte url-safe Fernet key derived from ENCRYPTION_KEY or SECRET_KEY."""
        raw = (self.ENCRYPTION_KEY or self.SECRET_KEY).encode("utf-8")
        digest = hashlib.sha256(raw).digest()
        return base64.urlsafe_b64encode(digest)


settings = Settings()