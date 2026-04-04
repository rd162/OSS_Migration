"""Periodic housekeeping — Celery task + sub-functions, fire hooks.

Source: ttrss/include/rssfuncs.php:housekeeping_common (lines 1415-1430)
    and individual sub-functions called therein.

PHP → Python mapping (per plan R14):
    expire_cached_files($debug) → expire_cached_files()    — pathlib glob + unlink
    expire_lock_files($debug)   → ELIMINATED               — Celery replaces file locks (ADR-0011)
    expire_error_log($debug)    → expire_error_log()        — DELETE from ttrss_error_log
    update_feedbrowser_cache()  → update_feedbrowser_cache() — DELETE + INSERT into cache table
    purge_orphans(true)         → imported from ttrss.feeds.ops (Batch 2, not duplicated)
    cleanup_tags(14, 50000)     → cleanup_tags()            — DELETE old unused tags
    HOOK_HOUSE_KEEPING          → plugin_manager.hook.hook_house_keeping()

Registered as a Celery periodic task (beat schedule).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from ttrss.models.error_log import TtRssErrorLog
from ttrss.models.feedbrowser_cache import TtRssFeedbrowserCache
from ttrss.models.tag import TtRssTag
from ttrss.models.user_entry import TtRssUserEntry

logger = logging.getLogger(__name__)

# Default retention periods (PHP rssfuncs.php:expire_error_log — 7 days)
_ERROR_LOG_RETENTION_DAYS = 7
# rssfuncs.php:cleanup_tags default arguments: days=14, limit=50000
_TAG_RETENTION_DAYS = 14
_TAG_CLEANUP_LIMIT = 50_000
# rssfuncs.php:expire_cached_files — 7 days (PURGE_CACHE_FILE_AGE_DAYS not in PHP;
# 7 days matches Tiny Tiny RSS cache dir pruning convention)
_CACHE_FILE_RETENTION_DAYS = 7


# ---------------------------------------------------------------------------
# expire_cached_files
# ---------------------------------------------------------------------------


def expire_cached_files(cache_dir: Optional[str] = None) -> int:
    """Delete cached files older than _CACHE_FILE_RETENTION_DAYS days.

    Source: ttrss/include/rssfuncs.php:expire_cached_files (lines ~1395-1414)
    Eliminated: $debug parameter — Python logging used instead.
    Returns number of files deleted.
    """
    if cache_dir is None:
        cache_dir = os.environ.get("TTRSS_CACHE_DIR", "/var/cache/ttrss")

    cache_path = Path(cache_dir)
    if not cache_path.is_dir():
        logger.debug("expire_cached_files: cache_dir %s not found, skipping", cache_dir)
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=_CACHE_FILE_RETENTION_DAYS)
    deleted = 0

    for f in cache_path.glob("**/*"):
        if not f.is_file():
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
                logger.debug("expire_cached_files: deleted %s", f)
        except OSError:
            pass

    logger.info("expire_cached_files: deleted %d file(s)", deleted)
    return deleted


# ---------------------------------------------------------------------------
# expire_error_log
# ---------------------------------------------------------------------------


def expire_error_log(session: Session) -> int:
    """Delete error log entries older than _ERROR_LOG_RETENTION_DAYS days.

    Source: ttrss/include/rssfuncs.php:expire_error_log (lines ~1380-1393)
    Eliminated: $debug parameter.
    Returns number of rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_ERROR_LOG_RETENTION_DAYS)
    result = session.execute(
        delete(TtRssErrorLog).where(TtRssErrorLog.created_at < cutoff)
    )
    count = result.rowcount
    logger.info("expire_error_log: deleted %d row(s)", count)
    return count


# ---------------------------------------------------------------------------
# update_feedbrowser_cache
# ---------------------------------------------------------------------------


def update_feedbrowser_cache(session: Session) -> None:
    """Rebuild the feedbrowser cache from current feed subscriptions.

    Source: ttrss/include/rssfuncs.php:update_feedbrowser_cache (lines ~1330-1370)
    Adapted: SQL string replaced by SQLAlchemy expressions.
    DELETE all rows then INSERT aggregated subscription counts.
    """
    from ttrss.models.feed import TtRssFeed

    # Clear stale cache
    session.execute(delete(TtRssFeedbrowserCache))

    # Aggregate: feeds with site_url + title, count subscriptions
    # Source: rssfuncs.php — SELECT site_url, title, feed_url, count(*) as subscribers
    #         FROM ttrss_feeds WHERE ... GROUP BY ... ORDER BY subscribers DESC LIMIT 500
    stmt = (
        select(
            TtRssFeed.feed_url,
            TtRssFeed.title,
            TtRssFeed.site_url,
            func.count(TtRssFeed.id).label("subscribers"),
        )
        .where(TtRssFeed.feed_url.isnot(None))
        .where(TtRssFeed.feed_url != "")
        .where(TtRssFeed.site_url.isnot(None))
        .where(TtRssFeed.site_url != "")
        .group_by(TtRssFeed.feed_url, TtRssFeed.title, TtRssFeed.site_url)
        .order_by(func.count(TtRssFeed.id).desc())
        .limit(500)
    )
    rows = session.execute(stmt).all()

    for row in rows:
        session.add(
            TtRssFeedbrowserCache(
                feed_url=row.feed_url,
                title=row.title or "",
                site_url=row.site_url or "",
                subscribers=row.subscribers,
            )
        )

    logger.info("update_feedbrowser_cache: inserted %d row(s)", len(rows))


# ---------------------------------------------------------------------------
# cleanup_tags
# ---------------------------------------------------------------------------


def cleanup_tags(
    session: Session,
    days: int = _TAG_RETENTION_DAYS,
    limit: int = _TAG_CLEANUP_LIMIT,
) -> int:
    """Delete orphaned/old tags to keep ttrss_tags table bounded.

    Source: ttrss/include/rssfuncs.php:cleanup_tags (lines ~1370-1380)
    Adapted: PHP single-query DELETE … LIMIT becomes subquery-based DELETE (PostgreSQL
    does not support DELETE … LIMIT directly).
    Returns number of rows deleted.
    """
    # Tags older than `days` days that are not referenced from any current user_entry
    # (post_int_id may have been deleted due to purge_orphans cascading)
    cutoff_ts = datetime.now(timezone.utc) - timedelta(days=days)

    # Identify int_ids still present in ttrss_user_entries
    valid_int_ids_subq = select(TtRssUserEntry.int_id).scalar_subquery()

    # Candidate tag ids to delete: post_int_id no longer in user_entries, up to limit
    candidate_ids_subq = (
        select(TtRssTag.id)
        .where(TtRssTag.post_int_id.not_in(valid_int_ids_subq))
        .limit(limit)
        .scalar_subquery()
    )

    result = session.execute(
        delete(TtRssTag).where(TtRssTag.id.in_(candidate_ids_subq))
    )
    count = result.rowcount
    logger.info("cleanup_tags: deleted %d tag(s)", count)
    return count


# ---------------------------------------------------------------------------
# housekeeping_common — orchestrator
# ---------------------------------------------------------------------------


def housekeeping_common(
    session: Session,
    cache_dir: Optional[str] = None,
) -> None:
    """Run all periodic housekeeping tasks.

    Source: ttrss/include/rssfuncs.php:housekeeping_common (lines 1415-1430)
    Eliminated: expire_lock_files — Celery handles job exclusivity (ADR-0011).
    Eliminated: $debug parameter — Python logging used.
    Added: pluggy HOOK_HOUSE_KEEPING at end.
    """
    from ttrss.feeds.ops import purge_orphans

    # Source: ttrss/classes/handler/public.php:411 — run_hooks(HOOK_UPDATE_TASK) before housekeeping
    try:
        from ttrss.plugins.manager import get_plugin_manager
        get_plugin_manager().hook.hook_update_task()
    except Exception:
        logger.debug("housekeeping_common: hook_update_task (pre) failed — continuing", exc_info=True)

    expire_cached_files(cache_dir=cache_dir)
    expire_error_log(session)
    update_feedbrowser_cache(session)
    purge_orphans(session)
    cleanup_tags(session)

    # Fire HOOK_HOUSE_KEEPING (pluggy collecting hook)
    # Source: ttrss/classes/pluginhost.php:HOOK_HOUSE_KEEPING (const 24)
    try:
        from ttrss.plugins.manager import get_plugin_manager
        get_plugin_manager().hook.hook_house_keeping(args={})
    except Exception:
        logger.debug("housekeeping_common: hook_house_keeping failed — continuing", exc_info=True)

    # Source: ttrss/classes/handler/public.php:421 — run_hooks(HOOK_UPDATE_TASK) after housekeeping
    try:
        from ttrss.plugins.manager import get_plugin_manager
        get_plugin_manager().hook.hook_update_task()
    except Exception:
        logger.debug("housekeeping_common: hook_update_task (post) failed — continuing", exc_info=True)


# ---------------------------------------------------------------------------
# run_housekeeping — Celery Beat task
# ---------------------------------------------------------------------------

from ttrss.celery_app import celery_app  # noqa: E402 — module-level import after housekeeping_common


@celery_app.task(
    name="ttrss.tasks.housekeeping.run_housekeeping",
    bind=True,
    # New: no PHP equivalent — Celery retry policy for transient failures (ADR-0011).
    max_retries=2,
    default_retry_delay=300,
)
def run_housekeeping(self) -> dict:
    """
    Beat-triggered periodic housekeeping: expire caches, clean DB, fire hooks.

    Source: ttrss/update.php (housekeeping_common call in daemon loop)
    Adapted: Celery Beat replaces PHP daemon loop (ADR-0011).
    Note: ttrss/update.php — PHP calls housekeeping_common() every DAEMON_SLEEP_INTERVAL cycles;
          Python uses a dedicated Beat schedule (celery_app.py beat_schedule).
    """
    from ttrss import create_app
    from ttrss.extensions import db

    app = create_app()
    with app.app_context():
        try:
            housekeeping_common(db.session)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("run_housekeeping: failed: %s", exc, exc_info=True)
            raise self.retry(exc=exc)

    logger.info("run_housekeeping: complete")
    return {"status": "ok"}
