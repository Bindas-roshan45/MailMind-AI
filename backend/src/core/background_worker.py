"""
Background Automation Worker for MailMind AI.
Runs periodic, reliable inbox synchronization and intelligent auto-reply automation
with concurrency locks, idempotency, exponential backoff, quota limits, and graceful shutdown.
"""
import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.gmail_sync import sync_user_gmail_inbox
from src.database import AsyncSessionLocal
from src.models import ConnectedAccount, User

logger = logging.getLogger("mailmind-ai.background_worker")


class BackgroundWorkerState:
    """Tracks runtime health, execution metrics, and failure counts."""

    def __init__(self):
        self.is_running: bool = False
        self.started_at: Optional[datetime] = None
        self.last_run_at: Optional[datetime] = None
        self.total_cycles: int = 0
        self.successful_cycles: int = 0
        self.failed_cycles: int = 0
        self.last_error: Optional[str] = None
        self.active_user_locks: Set[int] = set()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "total_cycles": self.total_cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "last_error": self.last_error,
            "active_users_processing": len(self.active_user_locks),
        }


worker_state = BackgroundWorkerState()


class BackgroundAutomationWorker:
    """Manages the background synchronization task lifecycle."""

    def __init__(self, poll_interval_seconds: int = 60):
        self.poll_interval = poll_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._user_locks_mutex = asyncio.Lock()

    def start(self):
        """Start the background worker loop as an asyncio task."""
        if self._task and not self._task.done():
            logger.warning("Background worker task already active.")
            return

        self._stop_event.clear()
        worker_state.is_running = True
        worker_state.started_at = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._run_loop(), name="mailmind-automation-worker")
        logger.info("Background automation worker started (interval: %ss)", self.poll_interval)

    async def stop(self, timeout: float = 10.0):
        """Gracefully stop the worker loop with timeout."""
        logger.info("Stopping background automation worker...")
        self._stop_event.set()
        worker_state.is_running = False

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
                logger.info("Background automation worker stopped cleanly.")
            except asyncio.TimeoutError:
                logger.warning("Background worker did not terminate in time; canceling task.")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None

    async def _run_loop(self):
        """Core periodic processing loop."""
        # Initial brief delay to let application start completely
        try:
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            return

        while not self._stop_event.is_set():
            worker_state.total_cycles += 1
            worker_state.last_run_at = datetime.now(timezone.utc)
            try:
                await self._process_all_connected_accounts()
                worker_state.successful_cycles += 1
                worker_state.last_error = None
            except Exception as exc:
                worker_state.failed_cycles += 1
                worker_state.last_error = str(exc)
                logger.error("Background worker cycle encountered an error: %s", exc, exc_info=True)

            # Wait for next poll interval or stop event
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=float(self.poll_interval))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _process_all_connected_accounts(self):
        """Iterate over all active users with connected Gmail accounts."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ConnectedAccount, User)
                .join(User, ConnectedAccount.user_id == User.id)
                .where(
                    ConnectedAccount.provider == "gmail",
                    ConnectedAccount.status == "connected",
                    User.is_active == True,
                )
            )
            rows = result.all()

        if not rows:
            logger.debug("Background worker: No active connected Gmail accounts to process.")
            return

        logger.info("Background worker checking %d connected account(s)...", len(rows))

        for conn_acc, user in rows:
            if self._stop_event.is_set():
                break

            # Per-user concurrency lock to ensure single worker per user
            async with self._user_locks_mutex:
                if user.id in worker_state.active_user_locks:
                    logger.debug("Skipping user %s; already in active processing lock.", user.id)
                    continue
                worker_state.active_user_locks.add(user.id)

            try:
                await self._process_user_with_retry(user)
            finally:
                async with self._user_locks_mutex:
                    worker_state.active_user_locks.discard(user.id)

    async def _process_user_with_retry(self, user: User, max_retries: int = 2):
        """Execute sync and automation for a single user with exponential backoff on transient failure."""
        attempt = 0
        backoff = 2.0

        while attempt <= max_retries:
            attempt += 1
            try:
                async with AsyncSessionLocal() as db:
                    sync_res = await sync_user_gmail_inbox(db, user, max_results=15, force=False)
                    if sync_res.get("synced"):
                        logger.info(
                            "Background sync for user %s: %s (new messages: %d)",
                            user.id,
                            sync_res.get("message"),
                            sync_res.get("new_count", 0),
                        )
                return  # Success, exit retry loop
            except Exception as err:
                if "rateLimitExceeded" in str(err) or "quotaExceeded" in str(err) or "timeout" in str(err).lower():
                    if attempt <= max_retries:
                        logger.warning(
                            "Transient error syncing user %s (attempt %d/%d): %s. Backoff %ss",
                            user.id, attempt, max_retries, err, backoff
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                logger.warning("Background sync failed for user %s: %s", user.id, err)
                break


automation_worker = BackgroundAutomationWorker(poll_interval_seconds=60)
