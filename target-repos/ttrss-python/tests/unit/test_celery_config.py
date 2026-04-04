"""Tests for Celery app configuration — beat_schedule entries and retry policy attributes.

Source: ttrss/include/rssfuncs.php:DAEMON_SLEEP_INTERVAL (beat timing)
        ttrss/classes/handler/public.php (housekeeping trigger)
New: Python test suite (A5 gate).
"""
from __future__ import annotations

import pytest


class TestBeatSchedule:
    """celery_app.conf.beat_schedule contains both required tasks at correct intervals."""

    def test_dispatch_feed_updates_in_schedule(self):
        """dispatch_feed_updates is in beat_schedule.

        Source: ttrss/include/rssfuncs.php:DAEMON_SLEEP_INTERVAL — PHP 120s default
                Phase 5a: increased to 300s (5 min) for Python implementation.
        """
        from ttrss.celery_app import celery_app
        assert "dispatch-feed-updates" in celery_app.conf.beat_schedule

    def test_dispatch_feed_updates_interval_300s(self):
        """dispatch_feed_updates schedule is 300s (Phase 5a — increased from 120s).

        Source: ttrss/include/rssfuncs.php line 4 — define_default('DAEMON_SLEEP_INTERVAL', 120)
        Adapted: increased to 300s; env FEED_UPDATE_INTERVAL overrides.
        """
        from ttrss.celery_app import celery_app
        entry = celery_app.conf.beat_schedule["dispatch-feed-updates"]
        assert float(entry["schedule"]) == 300.0

    def test_dispatch_feed_updates_task_name(self):
        from ttrss.celery_app import celery_app
        entry = celery_app.conf.beat_schedule["dispatch-feed-updates"]
        assert entry["task"] == "ttrss.tasks.feed_tasks.dispatch_feed_updates"

    def test_run_housekeeping_in_schedule(self):
        """run_housekeeping is in beat_schedule.

        Source: ttrss/classes/handler/public.php — housekeeping trigger in daemon loop
        New: no PHP equivalent for separate housekeeping schedule (ADR-0011).
        """
        from ttrss.celery_app import celery_app
        assert "run-housekeeping" in celery_app.conf.beat_schedule

    def test_run_housekeeping_interval_3600s(self):
        """run_housekeeping schedule is 3600s (1 hour).

        New: no PHP equivalent — Celery Beat replaces daemon loop cycle (ADR-0011).
        """
        from ttrss.celery_app import celery_app
        entry = celery_app.conf.beat_schedule["run-housekeeping"]
        assert float(entry["schedule"]) == 3600.0

    def test_run_housekeeping_task_name(self):
        from ttrss.celery_app import celery_app
        entry = celery_app.conf.beat_schedule["run-housekeeping"]
        assert entry["task"] == "ttrss.tasks.housekeeping.run_housekeeping"


class TestUpdateFeedRetryPolicy:
    """update_feed task has correct retry policy attributes (R20, ADR-0011)."""

    @pytest.fixture(autouse=True)
    def _import_tasks(self):
        """Force task module import so @celery_app.task decorators register the tasks."""
        import ttrss.tasks.feed_tasks  # noqa: F401
        import ttrss.tasks.housekeeping  # noqa: F401

    def test_update_feed_max_retries(self):
        """update_feed max_retries == 3.

        Source: Phase 5 plan R20 — max_retries=3 for transient HTTP failures.
        """
        from ttrss.celery_app import celery_app
        task = celery_app.tasks["ttrss.tasks.feed_tasks.update_feed"]
        assert task.max_retries == 3

    def test_update_feed_retry_backoff(self):
        """update_feed retry_backoff == True (exponential backoff).

        Source: Phase 5 plan R20 — exponential backoff, base 60s, cap 600s.
        """
        from ttrss.celery_app import celery_app
        task = celery_app.tasks["ttrss.tasks.feed_tasks.update_feed"]
        assert task.retry_backoff is True

    def test_update_feed_retry_backoff_max(self):
        """update_feed retry_backoff_max == 600s.

        Source: Phase 5 plan R20 — cap at 600s to prevent excessive wait.
        """
        from ttrss.celery_app import celery_app
        task = celery_app.tasks["ttrss.tasks.feed_tasks.update_feed"]
        assert task.retry_backoff_max == 600

    def test_update_feed_retry_jitter(self):
        """update_feed retry_jitter == True.

        New: Phase 5a — jitter spreads retries across workers (ADR-0011).
        """
        from ttrss.celery_app import celery_app
        task = celery_app.tasks["ttrss.tasks.feed_tasks.update_feed"]
        assert task.retry_jitter is True

    def test_run_housekeeping_max_retries(self):
        """run_housekeeping max_retries == 2.

        New: no PHP equivalent — Celery retry policy for transient failures (ADR-0011).
        """
        from ttrss.celery_app import celery_app
        task = celery_app.tasks["ttrss.tasks.housekeeping.run_housekeeping"]
        assert task.max_retries == 2
