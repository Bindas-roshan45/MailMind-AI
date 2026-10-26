"""
MailMind AI — Modular FastAPI Backend Application.
Provides RESTful APIs for email management, AI reply automation, tasks, and scheduling.
"""
from contextlib import asynccontextmanager
import logging
import os
import sys
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config import settings
from src.database import init_db, close_db, engine
from src.api.v1.router import api_router
from src.api.v1.endpoints import health

# ─── Logging Setup ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if settings.LOG_LEVEL.lower() == "info" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("mailmind-ai")


from src.core.background_worker import automation_worker


# ─── Lifespan Context Manager ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown hooks."""
    logger.info("==================================================")
    logger.info(f" Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f" Mode: {'DEMO MODE (Simulated Data)' if settings.DEMO_MODE else 'PRODUCTION'}")
    logger.info(f" Database URL: {str(settings.DATABASE_URL).split('@')[-1] if '@' in str(settings.DATABASE_URL) else settings.DATABASE_URL}")
    logger.info("==================================================")

    # Initialize tables if running on local SQLite
    if "sqlite" in str(settings.DATABASE_URL):
        try:
            await init_db()
            logger.info(" SQLite database tables verified/created.")
        except Exception as e:
            logger.warning(f" Could not auto-create tables: {e}")

    # Launch reliable background automation worker (skip thread spawn during pytest runs)
    if not os.getenv("PYTEST_CURRENT_TEST"):
        automation_worker.start()

    yield

    # Gracefully stop background worker
    if not os.getenv("PYTEST_CURRENT_TEST"):
        await automation_worker.stop()

    # Cleanup database connection pool
    logger.info(" Shutting down MailMind AI backend...")
    await close_db()
    logger.info(" Database connections closed.")


# ─── FastAPI Application ────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent Email Agent Backend — FastAPI & PostgreSQL/SQLAlchemy 2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ─── CORS Middleware ────────────────────────────────────────────────
origins = settings.BACKEND_CORS_ORIGINS if isinstance(settings.BACKEND_CORS_ORIGINS, list) else [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Timing, Logging & Security Headers Middleware ─────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration * 1000:.1f}ms)"
    )
    response.headers["X-Process-Time"] = f"{duration:.4f}"

    # Production Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# ─── Exception Handlers ─────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle 422 validation errors with a clean JSON response."""
    errors = []
    for error in exc.errors():
        loc = " -> ".join([str(l) for l in error.get("loc", [])])
        msg = error.get("msg", "Invalid field")
        errors.append({"field": loc, "message": msg})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation Error",
            "errors": errors,
            "demo_mode": settings.DEMO_MODE,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "status_code": exc.status_code,
            "demo_mode": settings.DEMO_MODE,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled server errors."""
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected internal server error occurred.",
            "demo_mode": settings.DEMO_MODE,
        },
    )


# ─── Health Check Endpoints ─────────────────────────────────────────
# Direct mount at /api/health as explicitly requested by specification
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(health.router, tags=["Health"])


# ─── Root Endpoint ──────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint with API discovery information."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "demo_mode": settings.DEMO_MODE,
        "docs_url": "/docs",
        "health_check": "/api/health",
        "api_v1": settings.API_V1_STR,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Mount API v1 Router ────────────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)


# ─── Legacy/Compatibility Route for Google OAuth Callback ───────────
@app.get("/auth/google/callback", include_in_schema=False)
async def legacy_google_oauth_callback(request: Request):
    """
    Compatibility redirect for Google OAuth credentials configured with
    Authorized Redirect URI: http://localhost:8000/auth/google/callback
    Redirects to canonical /api/v1/auth/google/callback endpoint with all query params.
    """
    from fastapi.responses import RedirectResponse
    target_url = f"{settings.API_V1_STR}/auth/google/callback"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"
    return RedirectResponse(url=target_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
