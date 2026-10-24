# MailMind AI — Production SaaS Upgrade

## Project Overview
MailMind AI is a production-ready, multi-tenant AI email management SaaS inspired by Microsoft Outlook's productivity capabilities. It features intelligent email automation, user-controlled AI replies, customizable signatures, safe Gmail integration, and multi-tenant SaaS architecture.

## Stack
- **Frontend**: React 19, Vite 8, Tailwind CSS, Lucide icons, Sonner notifications
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (asyncio)
- **Database**: SQLite (`aiosqlite`) for local development; PostgreSQL (`asyncpg`) for production
- **AI Engine**: Google GenAI SDK (`gemini-3.5-flash-lite`, `gemini-3.8-flash`) with smart heuristic fallback
- **Authentication**: Application JWT + Google OAuth 2.0 with Fernet AES-256 token encryption at rest
- **Testing**: Pytest (82 items: 78 passed, 4 skipped fallback), Playwright/Vite build validation

## Core Principles
1. **Never auto-send emails** without an explicitly enabled, matching user automation rule.
2. **Draft Only is the default** mode. Sensitive, financial, legal, security, credential, and uncertain emails always require human review.
3. **No credentials or secrets in logs or client-side code**.
4. **Tenant isolation**: Every query and mutation enforces `resource.user_id == user.id`.
5. **Truthful UI**: Real Gmail data is separated from demo accounts; no mock simulations in connected accounts.
