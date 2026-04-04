"""
Feed update tasks — Celery two-task fan-out (ADR-0011, ADR-0014, ADR-0015).

Source: ttrss/include/rssfuncs.php:update_daemon_common (lines 60-200) — dispatcher
        ttrss/include/rssfuncs.php:update_rss_feed (lines 203-900) — per-feed update
        Adapted: Celery tasks replace PHP pcntl_fork() daemon loop (ADR-0011).

Phase 1b: fetch → parse → sanitize skeleton.
Phase 2: HOOK_FETCH_FEED, HOOK_FEED_FETCHED, HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER wired.
         Article DB persistence deferred to Phase 3.
"""
from __future__ import annotations

import asyncio
import structlog
from typing import Any

import feedparser
import httpx

from ttrss.articles.sanitize import sanitize  # New: sanitize extracted to ttrss/articles/sanitize.py (Phase 2).
from ttrss.celery_app import celery_app

logger = structlog.get_logger(__name__)  # New: no PHP equivalent — Python logging setup.

# Source: ttrss/include/functions.php line 40 — define_default('FEED_FETCH_TIMEOUT', 45)
# Adapted: PHP FEED_FETCH_TIMEOUT (read-only) mapped to httpx.Timeout object (ADR-0015, R19).
# New: write=10.0 and pool=5.0 have no PHP cURL equivalent — added for httpx Timeout completeness.
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
    # New: no PHP equivalent — PHP dispatcher does not retry; max_retries added for Celery resilience.
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_feed_updates(self) -> dict[str, Any]:
    """
    Beat-triggered dispatcher: query due feeds, fan-out update_feed per feed.
    Source: ttrss/include/rssfuncs.php:update_daemon_common (lines 120-192)
    Note: ttrss/include/rssfuncs.php lines 93-94 — PHP checks last_updated = '1970-01-01 00:00:00'
          as a sentinel value for feeds that have never been updated.  Python uses IS NULL instead,
          relying on the ORM schema default; the 1970 sentinel is not reproduced.
    Note: ttrss/include/rssfuncs.php lines 72-80 — PHP applies DAEMON_UPDATE_LOGIN_LIMIT to cap
          the number of active users processed per cycle.  Python omits this per-login throttle;
          all due feeds up to DAEMON_FEED_LIMIT are dispatched unconditionally.
    Note: ttrss/include/rssfuncs.php lines 120-178 — PHP queries feed_url and deduplicates at the
          URL level before dispatching.  Python queries only ttrss_feeds.id and dispatches one task
          per feed row without URL-level deduplication — a structural redesign.
          Adapted: URL-level dedup omitted; ttrss_feeds.last_update_started guard prevents
          duplicate in-flight dispatches for the same feed row.
    """
    # Lazy Flask import — keeps celery_app.py independently importable (R18).
    # New: create_app() per task invocation — no PHP equivalent; required by Flask application
    #      factory pattern when running inside Celery workers (no shared app context).
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

        feed_ids = [r[0] for r in rows]  # New: no PHP equivalent — Python unpacks SQLAlchemy Row objects; PHP directly iterates query result arrays.

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

        from ttrss.plugins.manager import get_plugin_manager
        pm = get_plugin_manager()

        # Source: ttrss/update.php:161 — run_hooks(HOOK_UPDATE_TASK) before update cycle
        try:
            pm.hook.hook_update_task()
        except Exception:
            logger.debug("dispatch_feed_updates: hook_update_task (pre) failed — continuing", exc_info=True)

        # Source: rssfuncs.php lines 160-191 — fan-out one task per feed
        for fid in feed_ids:
            update_feed.delay(fid)

        # Source: ttrss/update.php:190 — run_hooks(HOOK_UPDATE_TASK) after update cycle
        try:
            pm.hook.hook_update_task()
        except Exception:
            logger.debug("dispatch_feed_updates: hook_update_task (post) failed — continuing", exc_info=True)

        logger.info("dispatch_feed_updates: dispatched %d feeds", len(feed_ids))
        return {"dispatched": len(feed_ids), "feed_ids": feed_ids}


# ---------------------------------------------------------------------------
# Async HTTP fetch helper
# ---------------------------------------------------------------------------

# New: _fetch_feed_async is a Python-only structural addition — PHP has no equivalent async
#      helper function; cURL is called inline inside update_rss_feed via fetch_file_contents().
#      Extracted here to allow asyncio.run() isolation inside the synchronous Celery task (R14).
async def _fetch_feed_async(
    feed_url: str,
    last_etag: str | None,
    last_modified: str | None,
    auth_login: str | None,
    auth_pass: str | None,
) -> tuple[int, bytes, dict[str, str]]:
    """
    Async HTTP fetch with conditional GET (R4, R19, ADR-0015).

    Source: ttrss/include/functions.php:fetch_file_contents (lines 343-495)
            — cURL-based fetch replaced by httpx async (ADR-0015)
    New: ETag/Last-Modified conditional GET stores in ttrss_feeds.last_etag /
         last_modified (ADR-0015 schema extension, specs/02-database.md).
         No PHP equivalent — PHP does not perform conditional GET.
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
        # Source: ttrss/include/functions.php lines 374-376 — CURLOPT_FOLLOWLOCATION (conditional on safe_mode).
        # Adapted: Python always enables follow_redirects=True; safe_mode path not reproduced.
        follow_redirects=True,
        max_redirects=20,  # Source: ttrss/include/functions.php — CURLOPT_MAXREDIRS default 20
    ) as client:
        resp = await client.get(feed_url, headers=headers, auth=auth)
        resp_headers = {
            "etag": resp.headers.get("etag", ""),
            "last-modified": resp.headers.get("last-modified", ""),
        }
        return resp.status_code, resp.content, resp_headers


# ---------------------------------------------------------------------------
# update_feed — per-feed worker
# ---------------------------------------------------------------------------

# Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 203-900)
# R20: max_retries=3, exponential backoff via retry_backoff=True.
# R14: asyncio.run() inside prefork worker — each process has its own event loop.
@celery_app.task(
    name="ttrss.tasks.feed_tasks.update_feed",
    bind=True,
    max_retries=3,  # R20
    autoretry_for=(httpx.HTTPError, ConnectionError),
    retry_backoff=True,    # R20: exponential — base 60s, doubles per retry, cap 600s
    retry_backoff_max=600,
    retry_jitter=True,     # Phase 5a: add jitter to spread retries across workers (ADR-0011)
    default_retry_delay=60,
)
def update_feed(self, feed_id: int) -> dict[str, Any]:
    """
    Per-feed update task: fetch → 304 check → feedparser → lxml sanitize.
    Article DB persistence deferred to Phase 3.

    Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 203-900)
    ADR-0011 (Celery), ADR-0014 (feedparser+lxml), ADR-0015 (httpx async).
    Note: ttrss/include/rssfuncs.php lines 235-236 — PHP stamps last_update_started at task
          start.  Python stamps last_update_started in dispatch_feed_updates before fan-out;
          not re-stamped at task entry here.
    Note: ttrss/include/rssfuncs.php lines 424-457 — PHP fetches and updates favicon.
          Favicon handling not reproduced.
    Note: ttrss/include/rssfuncs.php lines 459-474 — PHP updates feed title and site_url from
          parsed feed metadata.  Feed metadata update not reproduced.
    Note: ttrss/include/rssfuncs.php lines 494-541 — PHP handles PubSubHubbub subscription.
          PubSubHubbub not reproduced.
    Note: ttrss/include/rssfuncs.php lines 702-703 — PHP triggers cache_images() per entry.
          Image caching not reproduced.
    Note: ttrss/include/rssfuncs.php — entry fields entry_timestamp, entry_language,
          entry_comments, num_comments, entry_tags are parsed and stored by PHP but are not
          included in the Python article dict; omitted pending Phase 3 DB persistence.
    Note: ttrss/include/rssfuncs.php — PHP computes SHA1-prefixed GUID for entries without a
          stable guid.  GUID hashing not reproduced; feedparser's entry.id used as-is.
    """
    # Lazy Flask import — keeps celery_app.py independently importable (R18).
    # New: create_app() per task invocation — no PHP equivalent; required by Flask application
    #      factory pattern when running inside Celery workers (no shared app context).
    from ttrss import create_app
    from ttrss.extensions import db

    app = create_app()
    with app.app_context():
        from ttrss.models.feed import TtRssFeed

        feed = db.session.get(TtRssFeed, feed_id)
        if feed is None:  # New: no PHP equivalent — PHP passes feed_id from a trusted dispatch loop; Python guards against race-condition deletes between dispatch and execution.
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

        from ttrss.plugins.manager import get_plugin_manager
        pm = get_plugin_manager()

        # Source: ttrss/include/rssfuncs.php lines 270-272 — HOOK_FETCH_FEED pipeline
        # Each plugin receives feed_data (None initially) and may return alternative feed bytes,
        # bypassing the HTTP fetch.  Collecting hook; last non-None result wins.
        _hook_feed_data_results = pm.hook.hook_fetch_feed(
            feed_data=None,
            fetch_url=feed.feed_url,
            owner_uid=feed.owner_uid,
            feed=feed_id,
        )
        _plugin_feed_data = next(  # New: no PHP equivalent — Python aggregates pipeline results.
            (r for r in reversed(_hook_feed_data_results) if r is not None), None
        )

        # R14: asyncio.run() wraps async httpx — safe in prefork (AR9: NOT get_event_loop())
        if _plugin_feed_data is not None:
            # Source: ttrss/include/rssfuncs.php lines 270-272 — plugin-provided data bypasses HTTP fetch.
            # Note: PHP's local file-cache path (lines 274-291) is a different mechanism; Python's
            #       plugin-bypass is structurally analogous but not identical to PHP's cache path.
            body = _plugin_feed_data
            status_code = 200  # New: synthetic status; plugin bypassed HTTP entirely.
            resp_headers: dict[str, str] = {}  # New: no PHP equivalent — empty headers dict satisfies the conditional-GET update path below; plugin-provided data has no HTTP response headers.
        else:
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
            except httpx.HTTPError as exc:  # Source: ttrss/include/rssfuncs.php lines 317-323 — PHP catches cURL errors; Python raises for autoretry (R20).
                feed.last_error = str(exc)[:250]
                db.session.commit()
                raise  # triggers autoretry

        # Source: rssfuncs.php lines 352-364 — 304 Not Modified handling
        if status_code == 304:  # Source: rssfuncs.php line 352 — if ($res_code == 304) — skip update, stamp last_updated.
            from sqlalchemy import func as sqlfunc
            feed.last_updated = sqlfunc.now()
            db.session.commit()
            logger.debug("update_feed: feed %d 304 Not Modified", feed_id)
            return {"feed_id": feed_id, "status": "not_modified"}

        if status_code >= 400:  # Source: rssfuncs.php lines 357-364 — if ($res_code == 0 || $res_code >= 400) — record HTTP error, stamp last_updated.
            feed.last_error = f"HTTP {status_code}"
            from sqlalchemy import func as sqlfunc
            feed.last_updated = sqlfunc.now()
            db.session.commit()
            logger.warning("update_feed: feed %d HTTP %d", feed_id, status_code)
            return {"feed_id": feed_id, "status": "http_error", "code": status_code}

        # New: no PHP equivalent — ADR-0015 stores ETag/Last-Modified for conditional GET on next fetch.
        feed.last_etag = resp_headers.get("etag") or None
        feed.last_modified = resp_headers.get("last-modified") or None

        # Source: ttrss/include/rssfuncs.php line 367 — HOOK_FEED_FETCHED pipeline
        # Plugins may transform raw feed bytes (e.g., apply encoding fixes, inject content).
        # Collecting hook; last non-None result replaces body.
        _hook_fetched_results = pm.hook.hook_feed_fetched(
            feed_data=body,
            fetch_url=feed.feed_url,
            owner_uid=feed.owner_uid,
            feed=feed_id,
        )
        for _r in _hook_fetched_results:  # New: no PHP equivalent — Python collects all results; pipeline takes last non-None.
            if _r is not None:
                body = _r

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

        # Source: ttrss/include/rssfuncs.php line 394 — HOOK_FEED_PARSED fire-and-forget
        # run_hooks() in PHP; pluggy collecting call here (results ignored).
        pm.hook.hook_feed_parsed(rss=parsed)

        # Source: rssfuncs.php lines 440-500 — per-entry processing loop
        # Phase 3: load filters once per feed update (rssfuncs.php lines 806-812)
        from ttrss.articles.filters import load_filters
        from ttrss.articles.persist import persist_article

        feed_filters = load_filters(db.session, feed_id=feed_id, owner_uid=feed.owner_uid)
        sanitized_count = 0
        persisted_count = 0
        for entry in parsed.entries:
            # Source: ttrss/include/rssfuncs.php lines 580-600 — extract entry content/summary
            # Adapted: PHP extracts content from SimplePie entry object; feedparser uses dict-like API.
            content = (
                entry.get("summary")
                or (entry.get("content") or [{}])[0].get("value", "")
            )

            # Source: ttrss/include/rssfuncs.php lines 673-689 — build article dict + HOOK_ARTICLE_FILTER
            # Adapted: PHP builds $article array from local vars; Python builds from feedparser entry.
            article: dict = {
                "owner_uid": feed.owner_uid,  # Source: rssfuncs.php line 673 — "owner_uid" => $owner_uid
                "guid": entry.get("id", ""),  # Source: rssfuncs.php line 674 — "guid" => $entry_guid
                "title": entry.get("title", ""),  # Source: rssfuncs.php line 675 — "title" => $entry_title
                "content": content,  # Source: rssfuncs.php line 676 — "content" => $entry_content
                "link": entry.get("link", ""),  # Source: rssfuncs.php line 677 — "link" => $entry_link
                "tags": [],  # Source: rssfuncs.php line 678 — "tags" => $entry_tags
                "plugin_data": "",  # Source: rssfuncs.php line 679 — "plugin_data" => $entry_plugin_data
                "author": entry.get("author", ""),  # Source: rssfuncs.php line 680 — "author" => $entry_author
            }

            # Source: ttrss/include/rssfuncs.php lines 687-689 — HOOK_ARTICLE_FILTER pipeline
            _hook_filter_results = pm.hook.hook_article_filter(article=article)
            for _r in _hook_filter_results:  # New: no PHP equivalent — Python collects results; pipeline takes last non-None.
                if _r is not None:
                    article = _r
            content = article.get("content", content)  # Source: rssfuncs.php line 697 — $entry_content = $article["content"]

            sanitize(content, owner_uid=feed.owner_uid)  # Source: ttrss/include/rssfuncs.php lines 694-697 — sanitize($entry_content, ...) call per entry.
            sanitized_count += 1  # New: no PHP equivalent — Python tracks sanitized count for task return value; PHP has no equivalent counter.

            # Phase 3: persist entry (rssfuncs.php lines 720-1117)
            # Propagate plugin_data from HOOK_ARTICLE_FILTER back into feedparser entry dict.
            entry_copy = dict(entry)
            entry_copy["plugin_data"] = article.get("plugin_data", "")
            # Extract enclosures from feedparser entry (rssfuncs.php lines 982-1020)
            enc_list = [
                {
                    "content_url": e.get("href", ""),
                    "content_type": e.get("type", ""),
                    "title": e.get("title", ""),
                    "duration": e.get("length", "") or "",
                }
                for e in (entry.get("enclosures") or [])
            ]
            is_new = persist_article(
                db.session,
                entry=entry_copy,
                feed_id=feed_id,
                owner_uid=feed.owner_uid,
                filters=feed_filters,
                enclosures=enc_list,
            )
            if is_new:
                persisted_count += 1

        # Source: rssfuncs.php lines 488-490 — update feed last_updated and clear last_error after successful parse
        feed.last_error = ""
        from sqlalchemy import func as sqlfunc
        feed.last_updated = sqlfunc.now()
        db.session.commit()

        logger.info(
            "update_feed: feed %d ok — %d entries, %d sanitized, %d new",
            feed_id,
            len(parsed.entries),
            sanitized_count,
            persisted_count,
        )
        return {
            "feed_id": feed_id,
            "status": "ok",
            "entries": len(parsed.entries),
            "sanitized": sanitized_count,
            "new": persisted_count,
        }
