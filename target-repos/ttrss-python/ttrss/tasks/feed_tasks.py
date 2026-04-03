"""
Feed update tasks — Celery two-task fan-out (ADR-0011, ADR-0014, ADR-0015).

Source: ttrss/include/rssfuncs.php:update_daemon_common (lines 60-200) — dispatcher
        ttrss/include/rssfuncs.php:update_rss_feed (lines 203-700) — per-feed update
        Adapted: Celery tasks replace PHP pcntl_fork() daemon loop (ADR-0011).

Phase 1b scope: fetch → parse → sanitize. Article DB persistence is Phase 2.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import feedparser
import httpx
import lxml.html
import lxml.html.clean

from ttrss.celery_app import celery_app

logger = logging.getLogger(__name__)

# R19: HTTP timeouts per ADR-0015.
# read=45.0 matches PHP FEED_FETCH_TIMEOUT=45 (ttrss/include/functions.php line 40).
# Source: ttrss/include/functions.php:fetch_file_contents (lines 197-365, cURL timeout config)
HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=5.0)

# Source: ttrss/include/rssfuncs.php line 3 — define_default('DAEMON_FEED_LIMIT', 500)
DAEMON_FEED_LIMIT = 500


# ---------------------------------------------------------------------------
# dispatch_feed_updates — Beat-triggered dispatcher
# ---------------------------------------------------------------------------

# Source: ttrss/include/rssfuncs.php:update_daemon_common (lines 60-200)
# Queries feeds due for update; fans out update_feed.delay() per feed (ADR-0011 two-task pattern).
@celery_app.task(
    name="ttrss.tasks.feed_tasks.dispatch_feed_updates",
    bind=True,
    max_retries=3,  # R20
    default_retry_delay=60,
)
def dispatch_feed_updates(self) -> dict[str, Any]:
    """
    Beat-triggered dispatcher: query due feeds, fan-out update_feed per feed.
    Source: ttrss/include/rssfuncs.php:update_daemon_common (lines 120-192)
    """
    # Lazy Flask import — keeps celery_app.py independently importable (R18).
    from ttrss import create_app
    from ttrss.extensions import db

    app = create_app()
    with app.app_context():
        # Source: rssfuncs.php lines 120-131 — SQL for due feeds
        # update_interval=0 means "use user's DEFAULT_UPDATE_INTERVAL preference".
        # last_update_started guard prevents duplicate dispatch for in-flight feeds.
        from sqlalchemy import text

        rows = db.session.execute(
            text(
                """
                SELECT DISTINCT ttrss_feeds.id
                FROM ttrss_feeds
                JOIN ttrss_users ON ttrss_feeds.owner_uid = ttrss_users.id
                JOIN ttrss_user_prefs
                  ON ttrss_users.id = ttrss_user_prefs.owner_uid
                 AND ttrss_user_prefs.pref_name = 'DEFAULT_UPDATE_INTERVAL'
                 AND ttrss_user_prefs.profile IS NULL
                WHERE
                  (
                    (ttrss_feeds.update_interval = 0
                     AND ttrss_user_prefs.value != '-1'
                     AND (
                       ttrss_feeds.last_updated IS NULL
                       OR ttrss_feeds.last_updated
                          < NOW() - CAST((ttrss_user_prefs.value || ' minutes') AS INTERVAL)
                     ))
                    OR
                    (ttrss_feeds.update_interval > 0
                     AND (
                       ttrss_feeds.last_updated IS NULL
                       OR ttrss_feeds.last_updated
                          < NOW() - CAST((ttrss_feeds.update_interval || ' minutes') AS INTERVAL)
                     ))
                    OR ttrss_feeds.last_updated IS NULL
                  )
                  AND (
                    ttrss_feeds.last_update_started IS NULL
                    OR ttrss_feeds.last_update_started < NOW() - INTERVAL '10 minutes'
                  )
                ORDER BY ttrss_feeds.id
                LIMIT :limit
                """
            ),
            {"limit": DAEMON_FEED_LIMIT},
        ).fetchall()

        feed_ids = [r[0] for r in rows]

        # Source: rssfuncs.php lines 154-156 — mark feeds as in-progress
        if feed_ids:
            db.session.execute(
                text(
                    "UPDATE ttrss_feeds SET last_update_started = NOW()"
                    " WHERE id = ANY(:ids)"
                ),
                {"ids": feed_ids},
            )
            db.session.commit()

        # Source: rssfuncs.php lines 160-191 — fan-out one task per feed
        for fid in feed_ids:
            update_feed.delay(fid)

        logger.info("dispatch_feed_updates: dispatched %d feeds", len(feed_ids))
        return {"dispatched": len(feed_ids), "feed_ids": feed_ids}


# ---------------------------------------------------------------------------
# Async HTTP fetch helper
# ---------------------------------------------------------------------------

async def _fetch_feed_async(
    feed_url: str,
    last_etag: str | None,
    last_modified: str | None,
    auth_login: str | None,
    auth_pass: str | None,
) -> tuple[int, bytes, dict[str, str]]:
    """
    Async HTTP fetch with conditional GET (R4, R19, ADR-0015).

    Source: ttrss/include/functions.php:fetch_file_contents (lines 197-365)
            — cURL-based fetch replaced by httpx async (ADR-0015)
    New: ETag/Last-Modified conditional GET stores in ttrss_feeds.last_etag /
         last_modified (ADR-0015 schema extension, specs/02-database.md).
    """
    headers: dict[str, str] = {}
    # Source: ttrss/include/functions.php:fetch_file_contents — no conditional GET in PHP;
    # New: ADR-0015 adds conditional GET via last_etag / last_modified columns.
    if last_etag:
        headers["If-None-Match"] = last_etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    auth = None
    if auth_login and auth_pass:
        # Source: ttrss/include/functions.php:fetch_file_contents (lines 238-244, CURLOPT_USERPWD)
        auth = httpx.BasicAuth(auth_login, auth_pass)

    # AR2: new AsyncClient per task invocation — do NOT share across tasks (prefork fork safety).
    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,  # R19
        follow_redirects=True,
        max_redirects=20,  # Source: ttrss/include/functions.php (CURLOPT_MAXREDIRS default 20)
    ) as client:
        resp = await client.get(feed_url, headers=headers, auth=auth)
        resp_headers = {
            "etag": resp.headers.get("etag", ""),
            "last-modified": resp.headers.get("last-modified", ""),
        }
        return resp.status_code, resp.content, resp_headers


# ---------------------------------------------------------------------------
# HTML sanitization helper
# ---------------------------------------------------------------------------

def _sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content using lxml (ADR-0014).
    Source: ttrss/include/functions2.php:sanitize (lines 356-450)
            — PHP's strip_harmful_tags() + DOMDocument replaced by lxml Cleaner.
    """
    if not html_content:
        return ""
    cleaner = lxml.html.clean.Cleaner(
        scripts=True,
        javascript=True,
        embedded=True,
        meta=True,
        remove_unknown_tags=False,
        safe_attrs_only=True,
    )
    try:
        doc = lxml.html.fragment_fromstring(html_content, create_parent="div")
        cleaned = cleaner.clean_html(doc)
        return lxml.html.tostring(cleaned, encoding="unicode")
    except Exception:
        logger.warning("_sanitize_html: failed to sanitize, returning empty", exc_info=True)
        return ""


# ---------------------------------------------------------------------------
# update_feed — per-feed worker
# ---------------------------------------------------------------------------

# Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 203-700)
# R20: max_retries=3, exponential backoff via retry_backoff=True.
# R14: asyncio.run() inside prefork worker — each process has its own event loop.
@celery_app.task(
    name="ttrss.tasks.feed_tasks.update_feed",
    bind=True,
    max_retries=3,  # R20
    autoretry_for=(httpx.HTTPError, ConnectionError),
    retry_backoff=True,   # R20: exponential — base 60s, doubles per retry, cap 600s
    retry_backoff_max=600,
    default_retry_delay=60,
)
def update_feed(self, feed_id: int) -> dict[str, Any]:
    """
    Per-feed update task: fetch → 304 check → feedparser → lxml sanitize.
    Article DB persistence deferred to Phase 2 (marked TODO below).

    Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 203-700)
    ADR-0011 (Celery), ADR-0014 (feedparser+lxml), ADR-0015 (httpx async).
    """
    # Lazy Flask import — keeps celery_app.py independently importable (R18).
    from ttrss import create_app
    from ttrss.extensions import db

    app = create_app()
    with app.app_context():
        from ttrss.models.feed import TtRssFeed

        feed = db.session.get(TtRssFeed, feed_id)
        if feed is None:
            logger.warning("update_feed: feed %d not found, skipping", feed_id)
            return {"feed_id": feed_id, "status": "not_found"}

        # Source: rssfuncs.php lines 238-244 — auth credentials
        # ADR-0009: auth_pass property decrypts via Fernet if auth_pass_encrypted is set.
        auth_login = feed.auth_login or None
        raw_pass = feed._auth_pass  # read encrypted value directly
        auth_pass: str | None = None
        if feed.auth_pass_encrypted and raw_pass:
            # auth_pass property calls fernet_decrypt; skip if no FERNET key configured
            try:
                auth_pass = feed.auth_pass
            except Exception:
                logger.warning("update_feed: failed to decrypt auth_pass for feed %d", feed_id)
        elif raw_pass:
            auth_pass = raw_pass

        # R14: asyncio.run() wraps async httpx — safe in prefork (AR9: NOT get_event_loop())
        try:
            status_code, body, resp_headers = asyncio.run(
                _fetch_feed_async(
                    feed.feed_url,
                    feed.last_etag,
                    feed.last_modified,
                    auth_login,
                    auth_pass,
                )
            )
        except httpx.HTTPError as exc:
            feed.last_error = str(exc)[:250]
            db.session.commit()
            raise  # triggers autoretry

        # Source: rssfuncs.php lines 352-364 — 304 Not Modified handling
        if status_code == 304:
            from sqlalchemy import func as sqlfunc
            feed.last_updated = sqlfunc.now()
            db.session.commit()
            logger.debug("update_feed: feed %d 304 Not Modified", feed_id)
            return {"feed_id": feed_id, "status": "not_modified"}

        if status_code >= 400:
            feed.last_error = f"HTTP {status_code}"
            from sqlalchemy import func as sqlfunc
            feed.last_updated = sqlfunc.now()
            db.session.commit()
            logger.warning("update_feed: feed %d HTTP %d", feed_id, status_code)
            return {"feed_id": feed_id, "status": "http_error", "code": status_code}

        # New: ADR-0015 — store conditional GET response headers for next request
        feed.last_etag = resp_headers.get("etag") or None
        feed.last_modified = resp_headers.get("last-modified") or None

        # Source: rssfuncs.php lines 375-378 — parse feed content (ADR-0014)
        parsed = feedparser.parse(body)

        if parsed.bozo and not parsed.entries:
            # Source: rssfuncs.php lines 385-390 — bozo error handling
            feed.last_error = str(parsed.bozo_exception)[:250]
            from sqlalchemy import func as sqlfunc
            feed.last_updated = sqlfunc.now()
            db.session.commit()
            logger.warning(
                "update_feed: feed %d parse error: %s", feed_id, parsed.bozo_exception
            )
            return {"feed_id": feed_id, "status": "parse_error"}

        # Source: rssfuncs.php lines 391-394 — HOOK_FEED_PARSED (collecting, not firstresult)
        # TODO Phase 2: pm.hook.hook_feed_parsed(rss=parsed) via get_plugin_manager()

        # Source: rssfuncs.php lines 440-500 — per-entry processing loop
        sanitized_count = 0
        for entry in parsed.entries:
            content = (
                entry.get("summary")
                or (entry.get("content") or [{}])[0].get("value", "")
            )
            _sanitize_html(content)
            sanitized_count += 1
            # TODO Phase 2: upsert entry into ttrss_entries + ttrss_user_entries

        # Source: rssfuncs.php lines 680-690 — update feed metadata
        feed.last_error = ""
        from sqlalchemy import func as sqlfunc
        feed.last_updated = sqlfunc.now()
        db.session.commit()

        logger.info(
            "update_feed: feed %d ok — %d entries, %d sanitized",
            feed_id,
            len(parsed.entries),
            sanitized_count,
        )
        return {
            "feed_id": feed_id,
            "status": "ok",
            "entries": len(parsed.entries),
            "sanitized": sanitized_count,
        }
