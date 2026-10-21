"""
Main API v1 Router for MailMind AI.
Aggregates all sub-routers under /api/v1 namespace.
"""
from fastapi import APIRouter

from src.api.v1.endpoints import (
    health,
    auth,
    users,
    emails,
    tasks,
    calendar,
    auto_reply,
    preferences,
    drafts,
)

api_router = APIRouter()

# Register sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(emails.router, prefix="/emails", tags=["Emails"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(auto_reply.router, prefix="/auto-reply", tags=["Auto Reply"])
api_router.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
api_router.include_router(drafts.router, prefix="/ai", tags=["AI Drafts"])
