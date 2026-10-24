"""
Database layer for MailMind AI backend.
Handles SQLAlchemy engine, session management, and model base.
"""
import os
from typing import AsyncGenerator, Optional

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 base class for all models."""
    pass


# Create async engine
# echo=False in production; set to True for debugging SQL queries
engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    future=True,
)

# Create session maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)
AsyncSessionLocal = async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async DB session and commits on success."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables in the database (for development)."""
    import src.models  # noqa: F401 — register models on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def sync_sqlite_columns(connection):
            try:
                # Direct check on raw SQLite connection
                raw_conn = connection.connection.dbapi_connection
                cursor = raw_conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                cols = {row[1] for row in cursor.fetchall()}
                if cols and "hashed_password" not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)")

                # Check user_preferences table
                cursor.execute("PRAGMA table_info(user_preferences)")
                pref_cols = {row[1] for row in cursor.fetchall()}
                if pref_cols:
                    new_cols = {
                        "automation_paused": "BOOLEAN DEFAULT 0",
                        "automation_mode": "VARCHAR(50) DEFAULT 'draft_only'",
                        "daily_reply_limit": "INTEGER DEFAULT 20",
                        "min_confidence_score": "INTEGER DEFAULT 85",
                        "sender_allowlist": "JSON",
                        "sender_blocklist": "JSON",
                        "job_title": "VARCHAR(255)",
                        "company": "VARCHAR(255)",
                        "timezone": "VARCHAR(100) DEFAULT 'UTC'",
                        "custom_instructions": "TEXT",
                    }
                    for col_name, col_type in new_cols.items():
                        if col_name not in pref_cols:
                            try:
                                cursor.execute(f"ALTER TABLE user_preferences ADD COLUMN {col_name} {col_type}")
                            except Exception:
                                pass
                raw_conn.commit()
            except Exception:
                pass

        if "sqlite" in str(settings.DATABASE_URL):
            await conn.run_sync(sync_sqlite_columns)


async def close_db() -> None:
    """Dispose of the engine pool."""
    await engine.dispose()