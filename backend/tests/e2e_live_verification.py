"""
End-to-End Live Application Verification Script for MailMind AI.
Simulates all frontend UI workflows against http://127.0.0.1:8000.
"""
import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000/api/v1"

def req(endpoint, method="GET", data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            status = response.status
            content = response.read().decode("utf-8")
            return status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return e.code, parsed

def run_tests():
    results = []

    def check(name, success, info=""):
        results.append((name, success, info))
        status_str = "PASS" if success else "FAIL"
        print(f"[{status_str}] {name} {f'- {info}' if info else ''}")

    print("--- Starting End-to-End Live Workflow Verification ---")

    # 1. Health & Status
    status, data = req("/health")
    check("Health Check", status == 200 and data.get("status") == "healthy", f"status={status}")

    # 2. Demo Token & Authentication
    status, data = req("/auth/demo-token", method="POST")
    token = data.get("access_token")
    check("Auth: Demo Token Generation", status == 200 and bool(token), f"status={status}")

    status, me_resp = req("/auth/me", token=token)
    me = me_resp.get("data", {}) if isinstance(me_resp, dict) and "data" in me_resp else me_resp
    check("Auth: Get Current Profile (/auth/me)", status == 200 and ("roshan" in me.get("email", "") or "demo" in me.get("email", "")), f"user={me.get('email')}")

    # 3. Google Status Indicator
    status, gstatus = req("/auth/google/status", token=token)
    gdata = gstatus.get("data", {}) if "data" in gstatus else gstatus
    check("Auth: Google OAuth Status", status == 200, f"connected={gdata.get('connected')}")

    # 4. Email Inbox & Stats
    status, emails_resp = req("/emails?folder=inbox", token=token)
    emails = emails_resp.get("data", {}).get("items", [])
    check("Emails: List Inbox", status == 200 and len(emails) > 0, f"count={len(emails)}")

    status, stats_resp = req("/emails/stats", token=token)
    stats = stats_resp.get("data", {})
    check("Emails: Folder Stats", status == 200 and "total_received" in stats, f"total={stats.get('total_received')}")

    # 5. Email Actions (Star & Read)
    if emails:
        first_id = emails[0]["id"]
        status, star_resp = req(f"/emails/{first_id}/star", method="PATCH", token=token)
        check("Emails: Toggle Star", status == 200, f"email_id={first_id}")

        status, read_resp = req(f"/emails/{first_id}/read", method="PATCH", token=token)
        check("Emails: Toggle Read", status == 200, f"email_id={first_id}")

    # 6. AI Features
    if emails:
        first_id = emails[0]["id"]
        status, draft_resp = req("/ai/generate-draft", method="POST", data={
            "email_id": first_id,
            "tone": "professional",
            "language": "english"
        }, token=token)
        draft_data = draft_resp.get("data", {})
        draft_id = draft_data.get("draft_id")
        check("AI: Generate Reply Draft", status == 201 and draft_data.get("is_sent") is False, f"draft_id={draft_id}")

        # Safety Check: ensure is_sent is False
        check("Safety: Draft never auto-sent", draft_data.get("is_sent") is False and draft_data.get("is_approved") is False)

        if draft_id:
            # Approve draft
            status, app_resp = req(f"/ai/drafts/{draft_id}/approve", method="POST", data={"is_approved": True}, token=token)
            check("AI: Approve Draft", status == 200 and app_resp.get("data", {}).get("is_approved") is True)

            # Unapprove draft
            status, unapp_resp = req(f"/ai/drafts/{draft_id}/approve", method="POST", data={"is_approved": False}, token=token)
            check("AI: Unapprove Draft", status == 200 and unapp_resp.get("data", {}).get("is_approved") is False)

        # Standalone Compose Draft (no email_id)
        status, stand_resp = req("/ai/generate-draft", method="POST", data={
            "subject": "Partnership Proposal",
            "body": "Let's explore collaboration on AI solutions.",
            "prompt": "Offer an introductory call next Tuesday",
            "tone": "friendly"
        }, token=token)
        stand_data = stand_resp.get("data", {})
        check("AI: Standalone Compose Draft", status == 201 and bool(stand_data.get("content")), f"status={status}")

        # AI Summary
        email_body = emails[0].get("body") or emails[0].get("preview") or "Meeting update for project"
        status, sum_resp = req("/ai/summarize", method="POST", data={"text": email_body}, token=token)
        check("AI: Email Summary", status == 200 and "summary" in sum_resp.get("data", {}))

        # AI Extract Tasks
        status, ext_resp = req("/ai/extract-tasks", method="POST", data={"text": email_body}, token=token)
        check("AI: Extract Tasks", status == 200 and "tasks" in ext_resp.get("data", {}))

        # AI Rewrite (using content field matching frontend)
        status, rw_resp = req("/ai/rewrite", method="POST", data={"content": "Please confirm the project timeline.", "mode": "more_formal"}, token=token)
        check("AI: Rewrite Text", status == 200 and bool(rw_resp.get("data", {}).get("rewritten_content")))

    # 7. Tasks Lifecycle
    status, new_task = req("/tasks", method="POST", data={
        "title": "E2E QA Task Verification",
        "description": "Verify task creation, toggle, and persistence",
        "priority": "high"
    }, token=token)
    task_id = new_task.get("data", {}).get("id")
    check("Tasks: Create Task", status == 201 and bool(task_id), f"task_id={task_id}")

    if task_id:
        status, toggle_resp = req(f"/tasks/{task_id}/toggle", method="PATCH", token=token)
        check("Tasks: Toggle Completion", status == 200 and toggle_resp.get("data", {}).get("done") is True)

        # Persistence check
        status, task_list = req("/tasks?include_completed=true", token=token)
        persisted = any(t["id"] == task_id for t in task_list.get("data", []))
        check("Tasks: Persistence After State Change", status == 200 and persisted)

        status, del_resp = req(f"/tasks/{task_id}", method="DELETE", token=token)
        check("Tasks: Delete Task", status == 200)

    # 8. Calendar Events Lifecycle
    status, new_event = req("/calendar/events", method="POST", data={
        "title": "E2E QA Architecture Review",
        "description": "Live verification of calendar sync",
        "start_time": "2026-10-25T14:00:00Z",
        "end_time": "2026-10-25T15:00:00Z",
        "location": "Zoom Call"
    }, token=token)
    event_id = new_event.get("data", {}).get("id")
    check("Calendar: Create Event", status == 201 and bool(event_id), f"event_id={event_id}")

    if event_id:
        status, events_list = req("/calendar/events", token=token)
        persisted_event = any(e["id"] == event_id for e in events_list.get("data", []))
        check("Calendar: List & Persistence", status == 200 and persisted_event)

        status, del_ev = req(f"/calendar/events/{event_id}", method="DELETE", token=token)
        check("Calendar: Delete Event", status == 200)

    # 9. Notifications Lifecycle
    status, notifs = req("/notifications", token=token)
    check("Notifications: List Notifications", status == 200)

    status, unread = req("/notifications/unread-count", token=token)
    check("Notifications: Unread Count", status == 200 and "unread_count" in unread.get("data", {}))

    status, mark_all = req("/notifications/mark-all-read", method="POST", token=token)
    check("Notifications: Mark All Read", status == 200)

    # 10. Preferences
    status, prefs = req("/preferences", token=token)
    check("Preferences: Get User Preferences", status == 200 and "theme" in prefs.get("data", {}))

    status, updated_prefs = req("/preferences", method="PUT", data={"theme": "dark", "auto_draft_enabled": True}, token=token)
    check("Preferences: Update Preferences", status == 200 and updated_prefs.get("data", {}).get("theme") == "dark")

    # 11. Security & Token Verification
    status, invalid_token = req("/emails", token="invalid_jwt_token_payload")
    check("Security: Reject Malformed Token (401)", status == 401)

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n--- Verification Summary: {passed}/{total} Passed ---")
    if passed == total:
        print("ALL END-TO-END WORKFLOWS VERIFIED SUCCESSFULLY!")
    else:
        print(f"FAILED: {total - passed} tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
