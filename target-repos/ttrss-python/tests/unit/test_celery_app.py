"""
Celery app unit tests (R13, R14, R18, R19, R20).

New: no PHP equivalent — PHP had no task queue; tests verify Celery configuration.
"""


def test_celery_app_importable_without_flask():
    """R18: celery_app.py must import and create Celery instance without Flask context."""
    from ttrss.celery_app import celery_app

    assert celery_app.main == "ttrss"


def test_tasks_registered():
    """R17 exit gate criterion 6: both tasks appear in task registry at import time."""
    from ttrss.celery_app import celery_app  # noqa: F401 — ensures include runs
    import ttrss.tasks.feed_tasks  # noqa: F401

    from ttrss.celery_app import celery_app as app

    assert "ttrss.tasks.feed_tasks.dispatch_feed_updates" in app.tasks
    assert "ttrss.tasks.feed_tasks.update_feed" in app.tasks


def test_prefork_pool_configured():
    """R14: prefork pool must be explicit (asyncio.run() incompatible with gevent/eventlet)."""
    from ttrss.celery_app import celery_app

    assert celery_app.conf.worker_pool == "prefork"


def test_http_timeout_values():
    """R19: connect=10, read=45, write=10, pool=5 per ADR-0015."""
    from ttrss.tasks.feed_tasks import HTTP_TIMEOUT

    assert HTTP_TIMEOUT.connect == 10.0
    assert HTTP_TIMEOUT.read == 45.0
    assert HTTP_TIMEOUT.write == 10.0
    assert HTTP_TIMEOUT.pool == 5.0


def test_update_feed_max_retries():
    """R20: update_feed has max_retries=3."""
    from ttrss.celery_app import celery_app  # noqa: F401
    import ttrss.tasks.feed_tasks  # noqa: F401

    from ttrss.celery_app import celery_app as app

    task = app.tasks["ttrss.tasks.feed_tasks.update_feed"]
    assert task.max_retries == 3


def test_beat_schedule_dispatch_feed_updates():
    """R1: Beat schedule entry for dispatch_feed_updates at 300s (Phase 5a: increased from 120s DAEMON_SLEEP_INTERVAL)."""
    from ttrss.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert "dispatch-feed-updates" in schedule
    entry = schedule["dispatch-feed-updates"]
    assert entry["task"] == "ttrss.tasks.feed_tasks.dispatch_feed_updates"
    assert float(entry["schedule"]) == 300.0
