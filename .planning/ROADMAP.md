# MailMind AI — Production SaaS Upgrade Roadmap

## Milestones & Phases

### Phase 1: Foundation Verification (COMPLETED IN CHECKPOINT)
- [x] Verify Google token refresh & reconnection handling (`GmailClient.ensure_valid_token`).
- [x] Verify real Gmail inbox synchronization & thread parsing (`gmail_sync.py`).
- [x] Distinguish Application JWT expiration from Google OAuth token failures.
- [x] Remove mock data from real accounts; keep demo mode explicitly isolated.
- [x] Verify backend tests (78 passed) & Vite build (0 errors).

### Phase 2: Intelligent Auto-Reply Engine
- [ ] Implement enhanced email classification (Routine, Client, Work, Finance, Legal, Security, Complaint, Personal, Unknown).
- [ ] Add sensitivity assessment & confidence scoring.
- [ ] Build `AutomationEngine` supporting allowlists, blocklists, per-user rate limits, daily quotas, duplicate prevention, and a global pause switch.
- [ ] Ensure Draft Only is the default; auto-send occurs ONLY if user explicitly enabled a matching safe rule.
- [ ] Block auto-reply on phishing, spam, bounces, mailing lists, and self-addressed messages.
- [ ] Record audit events for all classification and automation actions.

### Phase 3: Sensitive Email Approval Modal & Safety Controls
- [ ] Build `SensitiveApprovalModal.jsx` displaying sender, subject, sensitivity reason, and proposed reply.
- [ ] Provide interactive editable draft editor with explicit "Edit" and "Send" confirmation buttons.
- [ ] Prevent duplicate submissions and show instant feedback toasts.
- [ ] Enforce user confirmation before sending; record approved draft changes in DB and audit log.

### Phase 4: Personalization, Signatures & AI Tone Preferences
- [ ] Database model `EmailSignature` (multiple named signatures, rich-text / sanitized text, defaults for new emails vs replies).
- [ ] Backend CRUD API for user signatures (`/api/v1/signatures`).
- [ ] User Settings UI for profile details (display name, job title, company, timezone) and signature preview.
- [ ] AI Tone Preferences: Professional, Friendly, Formal, Concise, Custom tones, reply length, custom brand voice.

### Phase 5: Outlook-Inspired Productivity Features
- [ ] Reply, Reply All, Forward, and Compose with recipient auto-suggestions.
- [ ] Safe rich-text editing with clean HTML sanitization.
- [ ] Undo Send delay queue (configurable 5s–30s delay before Gmail API dispatch).
- [ ] Attachment validation (file size and MIME types).
- [ ] Search, multi-label folder navigation (Inbox, Sent, Drafts, Archive, Spam, Trash), star/unstar, read/unread.

### Phase 6: Background Automation Runner & Reliability
- [ ] Background polling task runner with idempotency keys and synchronization checkpoints.
- [ ] Retry with exponential backoff for transient Gmail/network failures.
- [ ] Worker duplicate guard ensuring multiple processes never double-send replies.
- [ ] System health monitoring and error logging without leaking email contents or tokens.

### Phase 7: Multi-Tenant SaaS & Customer Onboarding
- [ ] Secure tenant isolation audit across all models, endpoints, and background workers.
- [ ] Customer onboarding flow: account setup -> Google OAuth -> signature setup -> reply mode choice.
- [ ] Plan-based usage tracking (Free, Pro, Enterprise tiers).
- [ ] Account deletion, export, retention, and privacy documentation for Google OAuth verification.

### Phase 8: Database Migrations, Security Hardening & Extended Test Suite
- [ ] Clean database migration script for new models (`EmailSignature`, `ProcessedMessageLog`, `AutomationAuditRecord`).
- [ ] Automated tests covering token refresh, approval flow, auto-send rule constraints, cross-user isolation, and Undo Send.

### Phase 9: UI Polish & Production Delivery
- [ ] Verify responsive design, theme consistency, and accessibility.
- [ ] Run full test suites, linter, production build, and generate deployment documentation.
