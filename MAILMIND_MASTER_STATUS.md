# MailMind AI — Master Project Audit & System Status

**Audit Date:** October 2026  
**Auditor:** Senior Full-Stack & AI Systems Auditor  
**Project:** MailMind AI  
**Repository State:** Audited (Read-Only Complete)

---

## 1. Executive Summary

MailMind AI has a **polished, high-fidelity React frontend** and a **well-structured FastAPI backend** with an async SQLAlchemy 2.0 database layer. However, **the frontend and backend are currently 100% disconnected**:
- The frontend operates entirely on static mock data (`src/data/mockData.js`) and simulated `setTimeout` timers.
- The backend has robust schemas, database models, and unit tests, but its database contains **zero rows** and lacks demo seeding for emails.
- Gemini integration uses the official `google-genai` SDK, but the model name configured in settings (`gemini-3.5-flash-lite`) is non-existent, and the default provider is set to `openai` (which is not installed).
- Gmail OAuth 2.0 and live email sending are not implemented; UI displays simulated connected badges.

---

## 2. Project Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Frontend: React 19 + Vite 8 + Tailwind CSS           │
│  - Dashboard, EmailDetail, EmailList, StatsBar, ComposeModal           │
│  - Pages: Inbox, Analytics, Tasks, Calendar, Reports, Settings         │
│  - State: AppContext.jsx (Currently bound only to mockData.js)         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │  (MISSING: API Client / Proxy)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Backend: FastAPI (Python 3.12)                       │
│  - Entry: main.py (CORS, Lifespan, Logging, Error Handlers)           │
│  - API Router: /api/v1                                                 │
│    ├── /auth         (demo-token, /me; Gmail OAuth deferred)          │
│    ├── /emails       (list, detail, stats, star, read)                 │
│    ├── /ai           (generate-draft, approve draft)                   │
│    ├── /tasks        (list, create, toggle, delete)                    │
│    ├── /calendar     (list events, add event)                          │
│    ├── /auto-reply   (rules list, create, toggle)                      │
│    ├── /preferences  (get, update user settings)                      │
│    └── /users        (me profile, update)                              │
│  - Core Services:                                                      │
│    ├── ai.py         (AIEngine: Gemini via google-genai + Fallback)    │
│    ├── gmail.py      (GmailClient stub: list/get messages only)        │
│    └── security.py   (JWT tokens, Fernet encryption, bcrypt)           │
│  - Persistence:                                                        │
│    ├── SQLite (local dev fallback: mailmind.db)                        │
│    └── PostgreSQL + asyncpg (production configuration)                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Feature Classification Matrix

| Feature / Subsystem | Status | Description & Actual State |
| :--- | :--- | :--- |
| **Frontend UI Shell** | `COMPLETE` | Clean, modern Tailwind dashboard, light/dark mode, responsive sidebar, detail pane, modal dialogues. |
| **Frontend Build & Linting** | `COMPLETE` | `vite build` passes (692ms). `oxlint` passes with 0 errors (16 unused import warnings in `ReportsPage.jsx`). |
| **Backend Core Architecture** | `COMPLETE` | FastAPI lifespan, CORS, Pydantic 2 schemas, SQLAlchemy 2 async engine, SQLite fallback. |
| **AI Reply Engine Core** | `PARTIAL` | `AIEngine` supports Gemini via `google-genai` and smart-draft fallback. However, model string is invalid (`gemini-3.5-flash-lite`), provider defaults to uninstalled `openai`, and API call is synchronous inside async handler. |
| **Frontend-Backend Integration** | `NOT IMPLEMENTED` | Frontend makes 0 HTTP calls (`fetch`/`axios`). All UI actions mutate in-memory state or use fake `setTimeout`. |
| **Inbox & Email Management API** | `PARTIAL` | Backend CRUD and endpoints exist, but zero emails are seeded in `mailmind.db`. Calling `/api/v1/emails` returns empty. |
| **Tasks Subsystem** | `PARTIAL` | Backend CRUD and endpoints work. Frontend has full Tasks page, but disconnected from backend API. |
| **Calendar Subsystem** | `PARTIAL` | Backend CRUD and demo seeding work. Frontend has full Calendar page, but disconnected from backend API. |
| **User Settings & Preferences** | `PARTIAL` | Backend preference CRUD works. Frontend Settings UI works visually but does not persist to backend. |
| **Notifications Subsystem** | `PARTIAL` | Models and CRUD exist in backend, but endpoint `/api/v1/notifications` is missing from `router.py`. Frontend uses static mock notifications. |
| **Analytics & Reports** | `PARTIAL` | High-fidelity UI charts via Recharts in `AnalyticsPage.jsx` and `ReportsPage.jsx`, but powered entirely by static fixtures. |
| **Gmail OAuth 2.0 Integration** | `NOT IMPLEMENTED` | No `/auth/google` flow implemented. Frontend displays hardcoded "Gmail: Connected" status. |
| **Live Email Sending** | `NOT IMPLEMENTED` | No SMTP or Gmail API `send_message` pipeline implemented. UI shows fake toast on send. |
| **AI Email Categorization / Ingestion Pipeline** | `NOT IMPLEMENTED` | No webhook or background worker extracting tasks/calendar events from incoming raw emails. |
| **Database Migrations (PostgreSQL)** | `BROKEN` | Migration `6f92c4c42425` contains `pass`. Tables were placed in initial migration, creating desync risks. |
| **API Endpoint Authorization (IDOR)** | `BROKEN` | `toggle_star`, `mark_read` (emails) and `toggle_task_done`, `delete_task` (tasks) lack user ownership checks. |

---

## 4. Test Results

### Backend (`pytest` via `.venv/bin/pytest`)
- **Total Tests:** 51
- **Passed:** 47
- **Skipped:** 4 (`test_openai_*` skipped because `openai` package is not installed; `google-genai` is primary)
- **Failures:** 0

### Frontend
- **Linting (`oxlint`):** 0 errors, 16 warnings (unused imports in `ReportsPage.jsx`, 1 `setState` in effect in `PushNotificationToast.jsx`).
- **Production Build (`vite build`):** Success (0 errors, bundle generated in `dist/`).

---

## 5. Security & Risk Audit

1. **IDOR / Unauthorized Entity Manipulation (High Risk):**
   - In `backend/src/api/v1/endpoints/emails.py`:
     - `PATCH /api/v1/emails/{email_id}/star` does not check `user_id`.
     - `PATCH /api/v1/emails/{email_id}/read` does not check `user_id`.
   - In `backend/src/api/v1/endpoints/tasks.py`:
     - `PATCH /api/v1/tasks/{task_id}/toggle` does not verify `user_id` or authenticate.
     - `DELETE /api/v1/tasks/{task_id}` does not verify `user_id` or authenticate.
2. **Invalid Gemini Model & Fallback Behavior (Medium Risk):**
   - `GEMINI_MODEL="gemini-3.5-flash-lite"` is invalid. When a real API key is supplied, Google Gemini returns `404 Not Found` / `ClientError`, causing silent fallback to template strings instead of real AI generation.
3. **Misleading User Authentication & OAuth State (Medium Risk):**
   - The UI displays an active green pulse "Gmail: Connected" and "roshan@gmail.com OAuth 2.0 Connected" despite no live OAuth token existing. Users could believe emails are synchronizing.
4. **Secret Key & Env Verification (Good):**
   - `.env.example` is sanitized; secrets are not committed; Fernet encryption is wired up for stored credentials.

---

## 6. Exact Files Needing Modification

### Backend
1. `backend/src/config.py`:
   - Set default `AI_PROVIDER = "gemini"`.
   - Fix default `GEMINI_MODEL = "gemini-2.5-flash"` (or `gemini-1.5-flash`).
2. `backend/src/core/ai.py`:
   - Switch `_generate_with_gemini` to non-blocking async execution (`client.aio.models.generate_content`).
3. `backend/src/api/v1/endpoints/emails.py`:
   - Add `user: User = Depends(get_current_user)` to `toggle_star` and `mark_read`.
   - Add demo email seeding logic when `DEMO_MODE=True` and database is empty so frontend gets data.
4. `backend/src/api/v1/endpoints/tasks.py`:
   - Add `user: User = Depends(get_current_user)` and user ownership checks to `toggle_task_done` and `delete_task`.
5. `backend/src/api/v1/endpoints/notifications.py` *(New File)*:
   - Implement router for list notifications, mark read, mark all read.
6. `backend/src/api/v1/router.py`:
   - Register the `notifications` router.

### Frontend
1. `vite.config.js`:
   - Add proxy config for `/api` pointing to `http://127.0.0.1:8000`.
2. `src/services/api.js` *(New File)*:
   - Centralized API client for all backend endpoints (emails, AI drafts, tasks, calendar, preferences).
3. `src/context/AppContext.jsx`:
   - Replace purely static `mockData` with asynchronous fetching from `/api/v1/emails`, `/api/v1/tasks`, `/api/v1/preferences`.
   - Fall back smoothly to demo data if the backend server is offline.
4. `src/components/EmailDetail/EmailDetail.jsx`:
   - Connect `handleRegenerate` to `POST /api/v1/ai/generate-draft`.
5. `src/components/Pages/TasksPage.jsx` & `TasksWidget.jsx`:
   - Connect task creation, toggling, and deletion to `/api/v1/tasks`.
6. `src/components/Pages/CalendarPage.jsx`:
   - Connect events retrieval and creation to `/api/v1/calendar/events`.
7. `src/components/Pages/SettingsPage.jsx`:
   - Connect preferences fetch and update to `/api/v1/preferences`.

---

## 7. Prioritized Implementation Roadmap

### Phase 3.1: Critical Backend Fixes (Security & Gemini Configuration)
- **Task 1:** Fix Gemini model name in `config.py` (`gemini-2.5-flash`), default `AI_PROVIDER = "gemini"`, and ensure async execution in `ai.py`.
- **Task 2:** Fix IDOR vulnerabilities in `emails.py` and `tasks.py` by requiring current user authorization.
- **Task 3:** Add missing `notifications` endpoint router in backend.
- **Task 4:** Add demo email database seeder for `DEMO_MODE=True` in `backend/src/database.py` or `crud/email.py`.

### Phase 3.2: Frontend-Backend Integration Layer
- **Task 5:** Configure Vite dev proxy and create `src/services/api.js`.
- **Task 6:** Connect `AppContext.jsx` to load live emails, folder counts, and stats from backend API with offline fallback.
- **Task 7:** Wire up real AI reply draft generation in `EmailDetail.jsx` calling `/api/v1/ai/generate-draft`.

### Phase 3.3: Feature Completion & Data Sync
- **Task 8:** Wire up `TasksPage.jsx`, `CalendarPage.jsx`, and `SettingsPage.jsx` to their respective backend endpoints.
- **Task 9:** Clean up unused imports and ESLint warnings in `ReportsPage.jsx` and `PushNotificationToast.jsx`.

### Phase 3.4: Real Gmail OAuth & Sending (When Credentials Available)
- **Task 10:** Implement Google OAuth authorization URL generator and callback handler.
- **Task 11:** Implement safe, approved-only email sending service using Gmail API.
