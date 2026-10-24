# MailMind AI — Production SaaS Platform

MailMind AI is a production-grade, multi-tenant AI email management SaaS inspired by Microsoft Outlook's productivity capabilities, powered by FastAPI, React 19, Tailwind CSS, Google Gemini GenAI SDK, and the Gmail API with Google OAuth 2.0.

---

## 🌟 Key Architecture & Capabilities

### 1. Security & Safety Guardrails (Zero Unintended Sends)
- **Draft Only by Default**: AI generated replies are always created as drafts and stored safely in the database.
- **Explicit Auto-Send Rules**: Automatic email dispatch ONLY occurs when a user explicitly configures an automation rule with `auto_send: true` for that specific category/sender pattern.
- **Sensitive Email Interception**: Emails touching financial matters (wires, banking, refunds), legal risks, security/credential topics, customer complaints, or uncertain classifications **always require manual human approval** via the `SensitiveApprovalModal`.
- **Emergency Global Pause Switch**: Instant tenant-wide pause switch (`/api/v1/auto-reply/pause`) that immediately halts all automated sends regardless of rules.
- **Loop & Rate Limit Protection**: Enforces daily reply limits (e.g. 20 for Free, 150 for Pro) and thread rate-limiting (max 1 auto-reply per thread per 24 hours).
- **Automated Sender Filtering**: Auto-filters bounces, no-reply addresses, delivery notifications, mailing lists, newsletters, and the user's own outgoing messages.
- **Encrypted Credential Storage**: All OAuth refresh and access tokens are encrypted at rest using AES-256 Fernet symmetric cryptography (`backend/src/core/security.py`). Secrets are never logged or exposed to the frontend.

### 2. Outlook-Inspired Productivity
- **Compose & Actions**: Rich compose modal supporting **Reply**, **Reply All**, **Forward**, CC, BCC, and in-reply-to threading headers.
- **Undo Send**: Configurable 5-second countdown timer before message dispatch with an instant "Undo Send" restore option.
- **Attachment Validation**: File picker supporting multiple attachments with rigorous 25 MB total size validation (matching Gmail limits) and visual removal chips.
- **Reusable Templates**: Quick-insert preset templates (Meeting Follow-up, Inquiry Acknowledgment, Schedule Coordination, Status Update).
- **Folder Navigation**: Complete folder hierarchy including **Inbox**, **Starred**, **Important**, **Snoozed**, **Sent**, **Drafts**, **Archive**, **Spam**, and **Trash**.
- **Snoozing**: Temporarily snooze emails for 4 hours, until tomorrow, or next week.
- **Draft Continuity**: View and continue editing unsent drafts seamlessly from the Drafts folder.

### 3. Personalization & Multi-Signature Management
- **Multiple Named Signatures**: Configure multiple signatures per user (e.g., "Work Default", "Direct Mobile", "Formal Executive").
- **Signature Defaults**: Separate default signature assignment for new outgoing emails vs. replies/forwards.
- **Rich Personalization**: Custom sign-offs (*Best regards*, *Kind regards*, *Thanks*, or custom sign-offs), full designations, company names, and direct phone lines.
- **Draft Independence**: Auto-inserted into new drafts with real-time selection dropdown to switch or remove.
- **AI Tone Calibration**: Professional, Friendly, Formal, Concise, and Custom tones with multilingual support (English, Hindi, Hinglish) and AI transformations (Improve, Shorten, Expand).

### 4. Background Automation & Reliability
- **Dedicated Async Worker**: Self-contained background runner (`backend/src/core/background_worker.py`) monitoring inboxes periodically (default: 60s).
- **Concurrency Locks**: Per-user mutex locks prevent race conditions and duplicate worker execution.
- **Idempotent Ingestion**: `ProcessedMessageLog` table ensures messages are never evaluated or replied to twice.
- **Exponential Backoff**: Automated retries with exponential backoff on transient Google API rate limits (HTTP 429) or network timeouts.
- **Health Checks & Monitoring**: Worker status, cycle count, uptime, and error history exposed under `/api/v1/health`.

### 5. Multi-Tenant SaaS Architecture
- **Tenant Isolation**: Strict `user_id` filtering enforced across all database queries, background sync tasks, and API endpoints.
- **Subscription Tiers & Quotas**: Built-in `Free`, `Pro Plan`, and `Enterprise` tiers tracking connected account allowances and daily reply quotas.
- **GDPR Data Export**: One-click complete tenant data export (`GET /api/v1/users/me/export`) packaging user profile, preferences, signatures, automation rules, and emails.
- **Full Account Deletion**: Cascade account deletion (`DELETE /api/v1/users/me`) permanently wiping all tenant emails, drafts, credentials, logs, and settings.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 8, Tailwind CSS, Lucide React, React Hot Toast |
| **Backend** | Python 3.12, FastAPI, Pydantic 2.0, Uvicorn |
| **Database** | SQLite + aiosqlite (Local Dev), PostgreSQL + asyncpg (Production) |
| **ORM** | SQLAlchemy 2.0 (Async Engine & Declarative Models) |
| **Authentication**| JWT (HS256) + Google OAuth 2.0 (Authorization Code Flow) |
| **Security** | AES-256 Fernet token encryption, Passlib bcrypt |
| **AI Engine** | Google Gemini (Google GenAI SDK) with offline fallback heuristics |
| **Email Protocol**| Google Gmail REST API v1 |

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

```env
# Application
PROJECT_NAME="MailMind AI"
VERSION="1.0.0"
ENVIRONMENT="production"        # "development" | "production"
LOG_LEVEL="INFO"
DEMO_MODE="false"               # Set "false" for real Gmail API usage

# Security & Cryptography
# Generate via: openssl rand -hex 32
SECRET_KEY="your-random-32-byte-hex-jwt-secret"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="1440"

# Generate Fernet key via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY="your-base64-encoded-fernet-key=="

# Database (PostgreSQL for Production, SQLite for Local)
DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/mailmind"
# Local development fallback:
# DATABASE_URL="sqlite+aiosqlite:///./mailmind.db"

# Google Gemini AI
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-2.0-flash"

# Google Gmail OAuth 2.0
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback"
FRONTEND_REDIRECT_URL="http://localhost:5173"

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### Frontend (`.env`)

```env
VITE_API_URL="http://localhost:8000"
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ & npm

### 2. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start backend dev server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at `http://localhost:8000/docs`.

### 3. Frontend Setup
```bash
# In repository root
npm install
npm run dev
```
Access the application at `http://localhost:5173`.

---

## 🧪 Verification & Testing

MailMind AI features a 54+ test suite spanning unit, integration, and security boundaries.

### Run Backend Tests
```bash
cd backend
.venv/bin/pytest tests/test_saas_security_and_productivity.py tests/test_automation_engine.py tests/test_auth.py tests/test_health.py tests/test_drafts.py tests/test_endpoints.py -v
```

### Run Frontend Linting & Production Build
```bash
# In repository root
npm run lint      # oxlint validation
npm run build     # vite production bundle
```

---

## 🔐 Google OAuth 2.0 Setup & Consent Verification

To connect real Gmail inboxes:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project and configure the **OAuth consent screen**:
   - User Type: **External**
   - App Name: `MailMind AI`
   - Scopes required:
     - `https://www.googleapis.com/auth/gmail.readonly` (Read incoming inbox)
     - `https://www.googleapis.com/auth/gmail.send` (Send authorized replies)
     - `https://www.googleapis.com/auth/gmail.compose` (Create drafts)
     - `https://www.googleapis.com/auth/gmail.modify` (Label and archive management)
3. Under **Credentials**, create an **OAuth 2.0 Client ID** (Web Application):
   - Authorized Javascript Origins: `http://localhost:5173`
   - Authorized Redirect URIs: `http://localhost:8000/api/v1/auth/google/callback`
4. Copy Client ID and Secret into `backend/.env`.

---

## 🗄 Production Deployment & PostgreSQL Migration

### 1. Database Setup
```bash
# PostgreSQL CLI
CREATE DATABASE mailmind;
CREATE USER mailmind_user WITH ENCRYPTED PASSWORD 'secure_pass';
GRANT ALL PRIVILEGES ON DATABASE mailmind TO mailmind_user;
```

Update `backend/.env`:
```env
DATABASE_URL="postgresql+asyncpg://mailmind_user:secure_pass@db-host:5432/mailmind"
```

The database tables, constraints, and indexes auto-initialize on startup via SQLAlchemy 2.0 models.

### 2. Backup & Disaster Recovery
```bash
# Backup PostgreSQL Database
pg_dump -U mailmind_user -h localhost -d mailmind -Fc -f "mailmind_backup_$(date +%Y%m%d).dump"

# Restore Database
pg_restore -U mailmind_user -h localhost -d mailmind -c "mailmind_backup_20261024.dump"
```

---

## 📋 End-to-End Manual Testing Checklist

| Test Case | Steps | Expected Result |
|---|---|---|
| **1. Google OAuth Connect** | Navigate to Settings -> Integrations -> Click "Connect Gmail" | Completes Google consent flow, redirects with success toast, displays connected email address. |
| **2. Multi-Signature Creation** | Go to Settings -> Signatures -> Create "Executive" signature with custom sign-off | Appears in signatures list; can be set as default for new or replies. |
| **3. New Compose & Undo Send** | Click "New Email" -> Select template -> Click "Send" | 5-second countdown banner appears with "Undo Send". Clicking Undo cancels send and keeps draft. |
| **4. Reply / Reply All** | Open an email -> Click "Reply All" | Opens compose modal pre-filled with sender, CC recipients, `Re:` subject, and quoted history. |
| **5. Sensitive Email Guard** | Open email mentioning wire/invoice/legal -> Click "Send Reply" | `SensitiveApprovalModal` appears with sensitivity reason; mandates review before dispatch. |
| **6. Emergency Pause** | Go to Settings -> Auto-Reply -> Toggle "Global Pause" | All automation is immediately paused. Audit log records pause state. |
| **7. Archive & Snooze** | Open email -> Click "Archive" or "Snooze" | Email disappears from inbox and appears in Archive / Snoozed mailbox. |
| **8. GDPR Export & Deletion**| Go to Settings -> Account -> Click "Export Data" | Downloads complete JSON archive. Deletion cascades and purges all tenant records. |
