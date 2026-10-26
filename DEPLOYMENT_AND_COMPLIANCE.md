# MailMind AI — Production SaaS Deployment & Compliance Guide

This document is the definitive deployment, infrastructure hardening, and regulatory compliance guide for **MailMind AI**.

---

## 1. Production Architecture Overview

MailMind AI is structured as a decoupled modern SaaS application:
- **Frontend**: React 18 SPA built with Vite, Tailwind CSS, Lucide icons, and Recharts. Split into optimized cacheable chunks (`vendor-react`, `vendor-charts`, `index`).
- **Backend API**: Python 3.12+ FastAPI application with async SQLAlchemy 2.0, Pydantic v2 validation, and Fernet encryption for OAuth tokens.
- **Database**: PostgreSQL 15+ using asyncpg with connection pooling (`pool_pre_ping=True`, `pool_recycle=300`, `pool_size=10`, `max_overflow=20`).
- **AI Intelligence**: Google Gemini 2.5 Flash / Flash Lite with fallback and automatic context synthesis.
- **Integration**: Google Cloud OAuth 2.0 with Gmail REST API integration.

```
                  ┌──────────────────────┐
                  │ HTTPS Reverse Proxy  │
                  │   (Nginx / Caddy)    │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   ┌─────────────────┐               ┌─────────────────┐
   │ React 18 SPA    │               │ FastAPI API     │
   │ (Static / CDN)  │               │ (Port 8000)     │
   └─────────────────┘               └────────┬────────┘
                                              │
                      ┌───────────────────────┼──────────────────────┐
                      ▼                       ▼                      ▼
             ┌─────────────────┐     ┌─────────────────┐    ┌─────────────────┐
             │ PostgreSQL 16   │     │ Google Gemini   │    │ Gmail API       │
             │ (Asyncpg Pool)  │     │ (REST API)      │    │ (OAuth 2.0)     │
             └─────────────────┘     └─────────────────┘    └─────────────────┘
```

---

## 2. Environment Configuration

### Required Production Secrets Generation

Never use development keys in production. Generate high-entropy cryptographic keys:

```bash
# 1. Generate JWT SECRET_KEY (minimum 32 bytes hex)
openssl rand -hex 32

# 2. Generate Fernet ENCRYPTION_KEY (for OAuth token encryption)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> [!CAUTION]
> **Encryption Key Stability**: The `ENCRYPTION_KEY` is used to encrypt customer OAuth refresh tokens stored in the database. If this key is lost or changed, all previously connected users will be forced to re-authenticate with Google. Store this key in your cloud secret manager (AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault).

### Production Environment Template

Create `backend/.env.production` (or inject as container environment variables):

```bash
# Mode
DEMO_MODE=false
ENVIRONMENT=production
LOG_LEVEL=INFO

# Security
SECRET_KEY=<32+_character_openssl_hex>
ENCRYPTION_KEY=<fernet_base64_key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=postgresql+asyncpg://mailmind_app:SECURE_DB_PASSWORD@postgres.internal:5432/mailmind_production

# Google OAuth 2.0
GOOGLE_CLIENT_ID=<your-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-secret>
GOOGLE_REDIRECT_URI=https://app.mailmind.ai/api/v1/auth/google/callback

# Frontend & CORS
FRONTEND_URL=https://app.mailmind.ai
CORS_ORIGINS=https://app.mailmind.ai

# AI Intelligence
AI_PROVIDER=gemini
GEMINI_API_KEY=<your-production-gemini-key>
GEMINI_MODEL=gemini-2.5-flash
```

---

## 3. PostgreSQL Database Setup & Migrations

### Initial PostgreSQL Setup

Connect to your PostgreSQL cluster as superuser:

```sql
CREATE DATABASE mailmind_production;
CREATE USER mailmind_app WITH ENCRYPTED PASSWORD 'SECURE_DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE mailmind_production TO mailmind_app;
\c mailmind_production
GRANT ALL ON SCHEMA public TO mailmind_app;
```

### Running Alembic Migrations

Run migrations from the `backend/` directory:

```bash
cd backend
source .venv/bin/activate

# Execute forward migrations to head
alembic upgrade head
```

### Verifying Migration Status

```bash
alembic current
alembic history --verbose
```

### Safe Rollback Procedure

If a release must be rolled back:

```bash
# Downgrade one revision
alembic downgrade -1

# Or downgrade to specific revision
alembic downgrade <revision_id>
```

> [!NOTE]
> All Alembic migrations in MailMind AI (`a1b2c3d4e5f6` and `b2c3d4e5f6a7`) are strictly idempotent with table reflection checks. They can safely be run on empty databases or existing databases without data loss.

### Automated Backups (pg_dump)

Configure an automated backup cron job or use managed cloud point-in-time recovery (PITR):

```bash
#!/usr/bin/env bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/mailmind"
mkdir -p "$BACKUP_DIR"

pg_dump -U mailmind_app -h postgres.internal -d mailmind_production -F c -b -v -f "$BACKUP_DIR/mailmind_$TIMESTAMP.dump"

# Upload to secure encrypted object storage (S3/GCS with KMS encryption)
aws s3 cp "$BACKUP_DIR/mailmind_$TIMESTAMP.dump" "s3://mailmind-backups-production/db/mailmind_$TIMESTAMP.dump" --sse aws:kms

# Delete backups older than 14 days locally
find "$BACKUP_DIR" -type f -name "*.dump" -mtime +14 -delete
```

---

## 4. Deployment Instructions

### Option A: Staging Deployment via Docker Compose

1. **Prepare Environment File**:
   Copy `.env.staging.example` to `backend/.env.staging` (or project root `.env.staging`):
   ```bash
   cp backend/.env.staging.example backend/.env.staging
   ```
   Generate random keys and populate credentials:
   ```bash
   # Generate SECRET_KEY
   openssl rand -hex 32
   # Generate ENCRYPTION_KEY
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Configure Staging Domain & OAuth**:
   - Set `FRONTEND_URL=https://staging.yourdomain.com` (or `http://localhost`)
   - Set `GOOGLE_REDIRECT_URI=https://staging.yourdomain.com/api/v1/auth/google/callback`
   - In Google Cloud Console, ensure this redirect URI is listed under authorized URIs.

3. **Launch Staging Stack**:
   ```bash
   # Preferred (Compose v2 / v5 standard):
   docker compose --env-file backend/.env.staging -f docker-compose.production.yml up -d --build

   # Or using shell environment variable:
   ENV_FILE=./backend/.env.staging docker compose -f docker-compose.production.yml up -d --build
   ```

4. **Verify Health and Auto-Migration**:
   ```bash
   # Check running containers
   docker compose -f docker-compose.production.yml ps

   # Check backend health & worker status
   curl -f http://localhost:8000/api/v1/health

   # Check Nginx frontend and API reverse proxy
   curl -f http://localhost/healthz
   curl -f http://localhost/api/v1/health
   ```

### Option B: Production Deployment via Docker Compose (Single Host / VPS / EC2)

1. Ensure Docker and Docker Compose v2 are installed.
2. Clone repository and switch to `feat/production-saas-upgrade` branch.
3. Configure `backend/.env.production`.
4. Launch containers:
   ```bash
   docker compose -f docker-compose.production.yml up -d --build
   ```
5. Check service health:
   ```bash
   docker compose -f docker-compose.production.yml ps
   curl -I http://localhost:8000/api/v1/health
   ```

### Option B: Cloud-Native Deployment (AWS / GCP / Render)

- **Database**: Provision Amazon RDS PostgreSQL or GCP Cloud SQL (PostgreSQL 16).
- **Backend API**: Deploy `backend/Dockerfile` to AWS ECS (Fargate) or GCP Cloud Run.
  - Set minimum instances = 1 (or 2 for high availability).
  - Configure container health check path: `/api/v1/health`.
  - Pass all environment variables from Cloud Secret Manager.
- **Frontend SPA**:
  - Deploy `dist/` directly to AWS CloudFront + S3, Cloudflare Pages, or Vercel.
  - Set build command: `npm run build`.
  - Set output directory: `dist`.
  - Configure single-page application rewrite: all routes `/*` -> `/index.html`.

---

## 5. Security & Infrastructure Hardening

### Automatic HTTP Security Headers

The FastAPI middleware automatically enforces the following security headers on all responses:

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevents clickjacking in iframes |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Protects sensitive tokens in URLs from leaking |
| `X-XSS-Protection` | `1; mode=block` | Enables browser reflected XSS filtering |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS transport (when served over TLS) |

### OAuth Token Storage Security

1. **At-Rest Encryption**: OAuth access tokens and refresh tokens are encrypted using Fernet (AES-128 in CBC mode with HMAC-SHA256 authentication) before writing to the database.
2. **Replay Protection**: The OAuth `state` parameter contains a signed, time-limited token with a cryptographic nonce. State reuse is strictly rejected (`test_oauth_state_replay_rejected`).
3. **Draft-Only Safeguard**: Automated email replies default to **Draft Only**. Automatic sending is never enabled without explicit user opt-in and rule configuration. Sensitive topics (financial, legal, security) are hardcoded to require human approval.

---

## 6. Monitoring, Logging & Background Workers

### Health Check Endpoints

- `GET /api/v1/health`
  - Returns `200 OK` with database connection status and background worker status.
  - Used by load balancers and container orchestrators.
- `GET /api/v1/auto-reply/worker/status`
  - Returns worker activity, interval, last execution timestamp, and active user count.

### Structured Logging & PII Protection

- Application logs use Python `logging` with timestamps and log levels.
- **Zero PII Policy**: Email body contents, OAuth secrets, authorization headers, and user passwords are never output to logs.
- In production, log level is set to `INFO`.

---

## 7. Google OAuth Verification & CASA Tier 2 Compliance

Because MailMind AI accesses Gmail user data, Google requires **OAuth API Verification** before granting access to unverified external users.

### Applicable Gmail Scopes

MailMind AI requests the following scopes:
1. `https://www.googleapis.com/auth/gmail.readonly` — View email messages and settings (Restricted).
2. `https://www.googleapis.com/auth/gmail.compose` — Create email drafts (Sensitive).
3. `https://www.googleapis.com/auth/gmail.modify` — Read, compose, and send email (Restricted).
4. `https://www.googleapis.com/auth/userinfo.email` — Identify authenticated Google user.
5. `https://www.googleapis.com/auth/userinfo.profile` — User display name and avatar.

### Pre-Submission Checklist

Before submitting the verification request in the Google Cloud Console:

- [ ] **Custom Domain**: App must be hosted on an active, verified domain (e.g., `https://app.mailmind.ai`).
- [ ] **HTTPS Enforced**: All OAuth redirect URIs and application endpoints must enforce TLS 1.3 / 1.2.
- [ ] **Public Privacy Policy**: Host a publicly accessible privacy policy clearly stating:
  - What data is accessed (Gmail messages, profile).
  - How data is stored (encrypted at rest).
  - Explicit statement of compliance with the **Google API Services User Data Policy**, including the **Limited Use** requirements.
  - Statement that customer email data is NOT used for generalized AI model training.
- [ ] **Public Terms of Service**: Host terms of service on the domain.
- [ ] **YouTube Demo Video**: Create an unlisted YouTube video showing:
  - The client ID clearly visible in the browser address bar during OAuth consent.
  - The user signing in and granting Gmail permissions.
  - How MailMind AI syncs messages and creates drafts in the user's Gmail inbox.
- [ ] **Google Search Console**: Verify ownership of the root domain in Google Search Console.

### CASA (Cloud Application Security Assessment) Tier 2

Because MailMind AI uses **Restricted Gmail Scopes**, Google requires an annual independent third-party security assessment under the **Cloud Application Security Assessment (CASA)** framework (based on OWASP ASVS).

1. **Select an Authorized CASA Assessor**:
   Google partners with accredited labs (e.g., Bishop Fox, Leviathan Security Group, NCC Group, TAC Security).
2. **Scan Requirements**:
   - Static Application Security Testing (SAST) on the codebase.
   - Dynamic Application Security Testing (DAST) on the deployed API.
3. **Validation Areas**:
   - Proper token storage encryption (satisfied by Fernet implementation).
   - Insecure direct object reference (IDOR) protection (verified in `test_idor_protection`).
   - Tenant isolation (verified in `test_cross_tenant_isolation_rejected`).
   - Cryptographic key management.
4. **Letter of Validation (LOV)**:
   Upon passing, the assessor submits the LOV directly to Google trust & safety.

---

## 8. Summary of Pre-Flight Verification

Before turning on production traffic, ensure the following commands pass:

```bash
# 1. Run migrations on staging/production PostgreSQL
cd backend && alembic upgrade head

# 2. Run backend test suite
pytest tests/ -v

# 3. Verify frontend code splitting & type integrity
cd .. && npm run lint && npm run build
```

---

## 9. Authentication Hardening & Staging Verification

### Production & Staging Authentication Mode
- When `DEMO_MODE=false` (configured in `backend/.env.staging` and `backend/.env.production`), the backend requires genuine authentication for all protected endpoints (`/auth/me`, `/preferences`, `/emails`, `/notifications`, `/signatures`, `/tasks`, `/auto-reply`).
- `POST /api/v1/auth/demo-token` strictly returns `403 Forbidden` in this mode.
- Users authenticate via standard password credentials or Google OAuth:
  - `POST /api/v1/auth/register`: Validates email uniqueness and min-8-character password, creates `users` record with bcrypt hash, initializes default `user_preferences`, and issues a JWT token.
  - `POST /api/v1/auth/login`: Validates credentials with `verify_password`, confirms `is_active`, and issues a JWT session token.
- The frontend `AuthModal` renders on load if no token exists, preventing unauthenticated calls to protected API routes.
- Once authenticated, all protected endpoints receive the `Authorization: Bearer <token>` header and return `200 OK`.

