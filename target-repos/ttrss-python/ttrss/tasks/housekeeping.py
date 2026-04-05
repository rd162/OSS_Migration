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

# Eliminated (ADR-0011): ttrss/include/rssfuncs.php::expire_lock_files — Celery Beat replaces file lock expiry.
# Eliminated (Docker): ttrss/include/functions.php::sanity_check — Docker healthchecks replace PHP startup validation.
"""
from __future__ import annotations

import structlog
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

logger = structlog.get_logger(__name__)

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

    # Aggregate: feeds with site_url + title, count subscriptions.
    # Source: rssfuncs.php — SELECT site_url, title, feed_url, count(*) AS subscribers
    #         FROM ttrss_feeds WHERE ... GROUP BY ... ORDER BY subscribers DESC LIMIT 1000
    # Source: rssfuncs.php lines 9-11 — exclude private feeds, feeds with credentials, and
    #         feeds with authentication in the URL (privacy filter for public browser).
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
        # Source: rssfuncs.php lines 9-11 — exclude private and credential-bearing feeds
        .where(TtRssFeed.private.is_(False))
        .where(TtRssFeed.auth_login == "")
        .where(TtRssFeed.auth_pass == "")
        # Source: rssfuncs.php line 11 — exclude URLs with embedded credentials (%:%@%)
        .where(~TtRssFeed.feed_url.contains("@"))
        .group_by(TtRssFeed.feed_url, TtRssFeed.title, TtRssFeed.site_url)
        .order_by(func.count(TtRssFeed.id).desc())
        .limit(1000)
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

    Source: ttrss/include/functions2.php:cleanup_tags (lines 2030-2069)
    Adapted: PHP single-query DELETE … LIMIT becomes subquery-based DELETE (PostgreSQL
    does not support DELETE … LIMIT directly).

    PHP deletes tags on entries older than `days` days (date-based, regardless of whether
    user_entry still exists). Python uses two complementary strategies:
    1. Orphaned tags (post_int_id no longer in ttrss_user_entries) — safety net for
       any tags missed by ON DELETE CASCADE on post_int_id → user_entries.int_id.
    2. Tags on old entries (entry date_updated older than `days`) whose article has not
       been starred/published (i.e., not kept intentionally) — matches PHP behavior.

    Returns number of rows deleted.
    """
    from ttrss.models.entry import TtRssEntry

    # Strategy 1: orphaned tags (CASCADE should handle these, but safety net)
    valid_int_ids_subq = select(TtRssUserEntry.int_id).scalar_subquery()
    orphan_candidate_ids_subq = (
        select(TtRssTag.id)
        .where(TtRssTag.post_int_id.not_in(valid_int_ids_subq))
        .limit(limit)
        .scalar_subquery()
    )
    r1 = session.execute(delete(TtRssTag).where(TtRssTag.id.in_(orphan_candidate_ids_subq)))

    # Strategy 2: Source: functions2.php:2043-2046 — tags on old entries (date_updated < cutoff)
    # whose user_entry is not starred or published (allows GC without removing intentionally-kept articles)
    cutoff_ts = datetime.now(timezone.utc) - timedelta(days=days)
    old_int_ids_subq = (
        select(TtRssUserEntry.int_id)
        .join(TtRssEntry, TtRssEntry.id == TtRssUserEntry.ref_id)
        .where(TtRssEntry.date_updated < cutoff_ts)
        .where(TtRssUserEntry.marked.is_(False))
        .where(TtRssUserEntry.published.is_(False))
        .scalar_subquery()
    )
    old_candidate_ids_subq = (
        select(TtRssTag.id)
        .where(TtRssTag.post_int_id.in_(old_int_ids_subq))
        .limit(limit)
        .scalar_subquery()
    )
    r2 = session.execute(delete(TtRssTag).where(TtRssTag.id.in_(old_candidate_ids_subq)))

    count = (r1.rowcount or 0) + (r2.rowcount or 0)
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

    Source: ttrss/classes/handler/public.php:Handler_Public::housekeepingTask (lines 414-416)
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
