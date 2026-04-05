"""
Celery application — standalone, independently importable without Flask (R18, ADR-0011).

This module must NOT import ttrss/__init__.py or call create_app() at module level.
Flask is imported lazily inside task functions only, so this file can be used as:
  celery -A ttrss.celery_app worker --pool=prefork

Source: ttrss/update_daemon2.php (pcntl_fork-based multi-process daemon supervisor)
        ttrss/update.php (daemon bootstrap + task dispatch)
        Adapted: Celery replaces PHP pcntl_fork() + SIGCHLD daemon architecture (ADR-0011).
New: no PHP equivalent — PHP used raw process forking; Celery provides task queue + Beat.
"""
import os

from celery import Celery

# Source: ttrss/include/rssfuncs.php (lines 3-4 — DAEMON_FEED_LIMIT / DAEMON_SLEEP_INTERVAL defines)
# New: Celery broker/backend via env var (PHP used no message broker — direct fork)
celery_app = Celery(
    "ttrss",
    broker=os.environ.get("CELERY_BROKER_URL", os.environ.get("REDIS_URL", "redis://localhost:6379/0")),
    backend=os.environ.get("CELERY_RESULT_BACKEND", os.environ.get("REDIS_URL", "redis://localhost:6379/0")),
    include=["ttrss.tasks.feed_tasks", "ttrss.tasks.housekeeping"],
)

celery_app.conf.update(
    # R14: prefork pool required — asyncio.run() inside tasks is incompatible with
    # gevent/eventlet pools (they patch the event loop, causing conflicts).
    # Each prefork worker process gets its own asyncio event loop via asyncio.run().
    worker_pool="prefork",
    worker_concurrency=int(os.environ.get("CELERY_CONCURRENCY", "2")),
    # Source: ttrss/include/rssfuncs.php line 3 — define_default('DAEMON_FEED_LIMIT', 500)
    # R20: task-level max_retries + backoff configured on the tasks themselves
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Source: ttrss/include/rssfuncs.php line 4 — define_default('DAEMON_SLEEP_INTERVAL', 120)
    # Phase 5a: increased dispatch interval to 300s (5 min); housekeeping added at 3600s (1 hr).
    beat_schedule={
        "dispatch-feed-updates": {
            "task": "ttrss.tasks.feed_tasks.dispatch_feed_updates",
            "schedule": float(os.environ.get("FEED_UPDATE_INTERVAL", "300")),  # R1 — 5 min default
        },
        "run-housekeeping": {
            # Source: ttrss/update.php — PHP calls housekeeping_common() periodically in daemon loop.
            # Adapted: Celery Beat replaces daemon loop cycle (ADR-0011).
            "task": "ttrss.tasks.housekeeping.run_housekeeping",
            "schedule": float(os.environ.get("HOUSEKEEPING_INTERVAL", "3600")),  # 1 hr default
        },
    },
    task_routes={
        "ttrss.tasks.feed_tasks.*": {"queue": "feeds"},
    },
)


# ---------------------------------------------------------------------------
# R03: Celery prefork worker DB pool safety (Phase 6 B3)
# ---------------------------------------------------------------------------
from celery.signals import worker_process_init, worker_process_shutdown  # noqa: E402


@worker_process_init.connect
def dispose_db_pool_on_fork(**kwargs):
    """
    R03: Celery prefork workers inherit the parent process's DB connection FD.
    dispose() before the first query ensures each worker opens its own fresh
    connections — prevents shared-FD silent data corruption.

    New: no PHP equivalent — PHP used pcntl_fork() with explicit resource cleanup.
    """
    try:
        from flask import current_app  # noqa: F401 — check for app context
        current_app._get_current_object()
        from ttrss.extensions import db
        db.engine.dispose()
    except RuntimeError:
        pass  # No app context during fork — safe to skip pool disposal


@worker_process_shutdown.connect
def close_db_pool_on_shutdown(**kwargs):
    """Close DB pool cleanly on Celery worker shutdown.

    New: no PHP equivalent — PHP daemon relied on OS cleanup on process exit.
    """
    from ttrss.extensions import db
    db.engine.dispose()


def init_app(app) -> None:
    """
    Bind Celery to a Flask app so tasks can use app context (DB, config).
    Called from Flask app factory. Does NOT affect standalone importability —
    celery_app is fully usable for task discovery and Beat without this.

    New: no PHP equivalent — Flask app context pattern (ADR-0011).
    """

    class ContextTask(celery_app.Task):
        # Inferred from: Flask + Celery integration pattern (ADR-0011)
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    app.extensions["celery"] = celery_app
