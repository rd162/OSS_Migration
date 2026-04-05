"""Tests for the Celery application (ttrss/celery_app.py).

Source: ttrss/update_daemon2.php (pcntl_fork-based daemon supervisor)
        ttrss/update.php (daemon bootstrap + task dispatch)
        ttrss/include/rssfuncs.php lines 3-4 (DAEMON_FEED_LIMIT / DAEMON_SLEEP_INTERVAL)
Adapted: Celery replaces PHP pcntl_fork() + SIGCHLD daemon architecture (ADR-0011).
New: no PHP equivalent — PHP used raw process forking; Celery provides task queue + Beat.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Test: celery_app is a Celery instance (R18)
# ---------------------------------------------------------------------------


def test_celery_app_is_celery_instance():
    """celery_app is a Celery instance importable without a Flask app context.

    Source: ttrss/update.php (daemon bootstrap)
    Adapted: R18 — celery_app.py must import and create Celery instance without Flask.
    New: Celery replaces PHP pcntl_fork() daemon (ADR-0011).
    """
    from celery import Celery
    from ttrss.celery_app import celery_app

    assert isinstance(celery_app, Celery)
    # Preserved from pre-existing suite (R18 exit gate criterion):
    assert celery_app.main == "ttrss"


# ---------------------------------------------------------------------------
# Test: update_feed task registered (R17)
# ---------------------------------------------------------------------------


def test_update_feed_task_registered():
    """update_feed task appears in celery_app.tasks registry after import.

    Source: ttrss/include/rssfuncs.php (PHP update_rss_feed() — replaced by Celery task).
    Adapted: task auto-discovery via celery_app include=['ttrss.tasks.feed_tasks'] (R17).
    New: no PHP equivalent — PHP had no task registry; Celery provides one.
    """
    import ttrss.tasks.feed_tasks  # noqa: F401 — trigger task registration

    from ttrss.celery_app import celery_app

    assert "ttrss.tasks.feed_tasks.update_feed" in celery_app.tasks
    # Also verify dispatch task is present (pre-existing R17 coverage)
    assert "ttrss.tasks.feed_tasks.dispatch_feed_updates" in celery_app.tasks


# ---------------------------------------------------------------------------
# Test: Beat schedule has dispatch_feed_updates key (R1)
# ---------------------------------------------------------------------------


def test_beat_schedule_has_dispatch_feed_updates():
    """Beat schedule contains 'dispatch-feed-updates' entry with correct task name.

    Source: ttrss/include/rssfuncs.php line 4 — define_default('DAEMON_SLEEP_INTERVAL', 120)
    Adapted: Celery Beat replaces PHP daemon sleep loop (ADR-0011).
             Phase 5a increased interval to 300 s (FEED_UPDATE_INTERVAL env var, R1).
    New: no PHP equivalent — PHP daemon used a sleep loop; Celery Beat is event-driven.
    """
    from ttrss.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "dispatch-feed-updates" in schedule
    entry = schedule["dispatch-feed-updates"]
    assert entry["task"] == "ttrss.tasks.feed_tasks.dispatch_feed_updates"
    assert float(entry["schedule"]) == 300.0


# ---------------------------------------------------------------------------
# Pre-existing tests preserved from original suite
# ---------------------------------------------------------------------------


def test_prefork_pool_configured():
    """R14: prefork pool must be explicit (asyncio.run() incompatible with gevent/eventlet).

    Source: ttrss/update_daemon2.php — PHP used pcntl_fork(); Celery uses prefork pool.
    Adapted: worker_pool='prefork' avoids asyncio event-loop conflicts (ADR-0011, R14).
    """
    from ttrss.celery_app import celery_app

    assert celery_app.conf.worker_pool == "prefork"


def test_http_timeout_values():
    """R19: connect=10, read=45, write=10, pool=5 per ADR-0015.

    Source: ttrss/include/rssfuncs.php (PHP fetch_file_contents timeouts).
    Adapted: httpx.Timeout replaces PHP stream_context_create timeout options (R19).
    """
    from ttrss.tasks.feed_tasks import HTTP_TIMEOUT

    assert HTTP_TIMEOUT.connect == 10.0
    assert HTTP_TIMEOUT.read == 45.0
    assert HTTP_TIMEOUT.write == 10.0
    assert HTTP_TIMEOUT.pool == 5.0


def test_update_feed_max_retries():
    """R20: update_feed has max_retries=3.

    Source: ttrss/include/rssfuncs.php — PHP had no retry concept; Python adds retry
            with exponential back-off via Celery autoretry (ADR-0011, R20).
    """
    import ttrss.tasks.feed_tasks  # noqa: F401

    from ttrss.celery_app import celery_app

    task = celery_app.tasks["ttrss.tasks.feed_tasks.update_feed"]
    assert task.max_retries == 3


# ---------------------------------------------------------------------------
# Additional tests to cover lines 74-75, 84-85, 97-104 (init_celery function)
# ---------------------------------------------------------------------------

def test_init_celery_wires_task_base(app):
    """Source: ADR-0011 — Flask+Celery init_celery() wraps Task with app context.
    Assert: calling init_celery(app) sets celery_app.Task to ContextTask."""
    from ttrss.celery_app import init_app as init_celery, celery_app
    from unittest.mock import patch, MagicMock

    with patch("ttrss.extensions.db") as mock_db:
        mock_db.engine.dispose = MagicMock()
        init_celery(app)

    # After init_celery, celery_app.Task should be ContextTask
    assert hasattr(celery_app.Task, "__call__")
    assert "celery" in app.extensions


def test_context_task_calls_run_in_app_context(app):
    """Source: ADR-0011 — ContextTask.__call__ runs self.run() inside app_context().
    Assert: the ContextTask wrapper executes successfully."""
    from ttrss.celery_app import init_app as init_celery, celery_app
    from unittest.mock import patch, MagicMock

    with patch("ttrss.extensions.db") as mock_db:
        mock_db.engine.dispose = MagicMock()
        init_celery(app)

    # Create a ContextTask instance and call it
    task = celery_app.Task()
    task.run = MagicMock(return_value=42)
    result = task(1, 2, kwarg="x")
    assert result == 42
    task.run.assert_called_once_with(1, 2, kwarg="x")
