"""
Health check endpoint for MailMind AI.
Verifies system health, configuration, and database connectivity.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_session

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="System Health & Database Status",
    description="Returns service health status, DB connection verify, and demo mode indicator.",
)
async def health_check(db: AsyncSession = Depends(get_session)):
    """Check system and database health."""
    db_status = "connected"
    db_error = None

    try:
        # Verify database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
    except Exception as exc:
        db_status = "disconnected"
        db_error = str(exc)

    is_healthy = db_status == "connected"

    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": db_status,
        "database_error": db_error,
        "demo_mode": settings.DEMO_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
