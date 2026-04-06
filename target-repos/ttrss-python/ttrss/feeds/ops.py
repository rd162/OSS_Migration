"""Feed operations — subscription, purge, favicon, update interval.

Source: ttrss/include/functions.php  (feed_purge_interval, purge_feed, purge_orphans,
                                      get_feed_update_interval, get_favicon_url,
                                      check_feed_favicon, subscribe_to_feed, lines 209-291, 324-341,
                                      504-535, 537-585, 1672-1754)
        ttrss/include/functions2.php (feed_has_icon, get_feed_access_key, get_feeds_from_html,
                                      lines 1579-1813)

Eliminated (R11): MySQL branches in purge_feed (functions.php:266-280) — PostgreSQL only.
Eliminated (R13): print_feed_select, print_feed_cat_select — server-rendered HTML.
ccache_update call sites #1 and #2 of 9 (R5) are in purge_feed.
"""
from __future__ import annotations

import logging
import pathlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ttrss.ccache import _get_pref, _pref_int, ccache_update
from ttrss.models.access_key import TtRssAccessKey
from ttrss.models.archived_feed import TtRssArchivedFeed  # noqa: F401 — DB table coverage
from ttrss.models.category import TtRssFeedCategory  # noqa: F401 — DB table coverage
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2  # noqa: F401 — DB table coverage
from ttrss.models.user_entry import TtRssUserEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interval helpers
# ---------------------------------------------------------------------------


def feed_purge_interval(session: Session, feed_id: int) -> int:
    """Return effective purge interval (days) for a feed.

    Source: ttrss/include/functions.php:feed_purge_interval (lines 293-310)
    Returns -1 if feed not found, 0 means "use PURGE_OLD_DAYS pref".
    """
    row = session.execute(
        select(TtRssFeed.purge_interval, TtRssFeed.owner_uid)
        .where(TtRssFeed.id == feed_id)
    ).one_or_none()
    if row is None:
        return -1
    purge_interval, owner_uid = row.purge_interval, row.owner_uid
    if purge_interval == 0:
        purge_interval = _pref_int(session, "PURGE_OLD_DAYS", owner_uid, default=60)
    return purge_interval


def get_feed_update_interval(session: Session, feed_id: int) -> int:
    """Return effective update interval (minutes) for a feed.

    Source: ttrss/include/functions.php:get_feed_update_interval (lines 324-341)
    Returns -1 if feed not found.
    """
    row = session.execute(
        select(TtRssFeed.update_interval, TtRssFeed.owner_uid)
        .where(TtRssFeed.id == feed_id)
    ).one_or_none()
    if row is None:
        return -1
    update_interval, owner_uid = row.update_interval, row.owner_uid
    if update_interval != 0:
        return update_interval
    # Source: ttrss/schema/ttrss_schema_pgsql.sql — DEFAULT_UPDATE_INTERVAL def_value = '30'
    # PHP get_pref() returns the DB def_value (30); hardcoding 120 was wrong.
    return _pref_int(session, "DEFAULT_UPDATE_INTERVAL", owner_uid, default=30)


# ---------------------------------------------------------------------------
# Purge operations
# ---------------------------------------------------------------------------


def purge_feed(
    session: Session,
    feed_id: int,
    purge_interval: int = 0,
    debug: bool = False,
) -> Optional[int]:
    """Delete old articles from a feed according to the purge interval.

    Source: ttrss/include/functions.php:purge_feed (lines 209-291)
    Eliminated: MySQL DATE_SUB branch (lines 266-280) — PostgreSQL only (R11).
    ccache_update call site #1: early-return when purge_interval <= 0 (functions.php:226).
    ccache_update call site #2: after article deletion (functions.php:284).
    """
    if not purge_interval:
        purge_interval = feed_purge_interval(session, feed_id)

    owner_row = session.execute(
        select(TtRssFeed.owner_uid).where(TtRssFeed.id == feed_id)
    ).scalar_one_or_none()

    owner_uid = owner_row

    # No purge when interval is -1 or 0 — just refresh the counter cache.
    # Source: functions.php:224-228 — ccache_update call site #1
    if purge_interval == -1 or not purge_interval:
        if owner_uid:
            ccache_update(session, feed_id, owner_uid)
        return None

    if not owner_uid:
        return None

    purge_unread = bool(_get_pref(session, "PURGE_UNREAD_ARTICLES", owner_uid) == "true")

    cutoff = datetime.now(timezone.utc) - timedelta(days=purge_interval)

    # PostgreSQL-only DELETE via IN subquery (equivalent to USING ttrss_entries).
    # Source: functions.php:255-264 (modern PostgreSQL branch)
    date_subq = (
        select(TtRssEntry.id)
        .where(TtRssEntry.date_updated < cutoff)
        .scalar_subquery()
    )
    stmt = (
        sa_delete(TtRssUserEntry)
        .where(TtRssUserEntry.feed_id == feed_id)
        .where(TtRssUserEntry.marked.is_(False))
        .where(TtRssUserEntry.ref_id.in_(date_subq))
    )
    if not purge_unread:
        stmt = stmt.where(TtRssUserEntry.unread.is_(False))

    result = session.execute(stmt)
    rows = result.rowcount

    # Source: functions.php:284 — ccache_update call site #2
    ccache_update(session, feed_id, owner_uid)

    if debug:
        logger.debug("Purged feed %d (%d days): deleted %d articles", feed_id, purge_interval, rows)

    return rows


def purge_orphans(session: Session, do_output: bool = False) -> None:
    """Delete ttrss_entries rows that have no user_entries referencing them.

    Source: ttrss/include/functions.php:purge_orphans (lines 312-322)
    """
    subq = (
        select(func.count(TtRssUserEntry.int_id))
        .where(TtRssUserEntry.ref_id == TtRssEntry.id)
        .scalar_subquery()
    )
    stmt = sa_delete(TtRssEntry).where(subq == 0)
    result = session.execute(stmt)
    if do_output:
        logger.debug("Purged %d orphaned posts.", result.rowcount)


# ---------------------------------------------------------------------------
# Favicon helpers
# ---------------------------------------------------------------------------


def feed_has_icon(feed_id: int, icons_dir: str = "") -> bool:
    """Return True if a feed icon file exists and is non-empty.

    Source: ttrss/include/functions2.php:feed_has_icon (lines 1579-1580)
    Note: PHP checks filesystem path ICONS_DIR; Python uses icons_dir parameter.
    """
    if not icons_dir:
        return False
    icon_path = pathlib.Path(icons_dir) / f"{feed_id}.ico"
    return icon_path.exists() and icon_path.stat().st_size > 0


def get_favicon_url(url: str) -> Optional[str]:
    """Try to locate the favicon URL for a site.

    Source: ttrss/include/functions.php:get_favicon_url (lines 504-535)
    Adapted: Uses httpx + lxml instead of PHP cURL + DOMDocument (ADR-0015).
    Falls back to /favicon.ico if no <link rel="icon"> found.
    """
    try:
        import httpx
        from lxml import html as lxml_html

        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            doc = lxml_html.fromstring(resp.content, base_url=url)
            doc.make_links_absolute(url)

            for link in doc.xpath('.//link[contains(concat(" ",normalize-space(@rel)," ")," icon ") or contains(concat(" ",normalize-space(@rel)," ")," shortcut icon ")]'):
                href = link.get("href")
                if href:
                    return href
    except Exception as exc:
        logger.debug("get_favicon_url(%s): %s", url, exc)

    # Fallback: /favicon.ico
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"


def check_feed_favicon(site_url: str, feed_id: int, icons_dir: str = "") -> Optional[str]:
    """Download and cache the favicon for a feed if not already cached.

    Source: ttrss/include/functions.php:check_feed_favicon (lines 537-585)
    Adapted: Uses pathlib + httpx instead of PHP file_exists + fetch_file_contents (ADR-0015).
    """
    if not icons_dir:
        return None

    icon_file = pathlib.Path(icons_dir) / f"{feed_id}.ico"
    if icon_file.exists():
        return str(icon_file)

    favicon_url = get_favicon_url(site_url)
    if not favicon_url:
        return None

    try:
        import httpx

        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(favicon_url)
            resp.raise_for_status()
            contents = resp.content
    except Exception as exc:
        logger.debug("check_feed_favicon fetch failed: %s", exc)
        return None

    if not contents:
        return None

    # Crude image type validation (matches PHP's preg_match checks).
    # Source: functions.php:552-571
    is_valid = (
        contents[:4] == b"\x00\x00\x01\x00"  # Windows ICO
        or contents[:4] == b"GIF8"            # GIF
        or contents[:8] == b"\x89PNG\r\n\x1a\n"  # PNG
        or contents[:2] == b"\xff\xd8"         # JPEG
    )
    if not is_valid:
        return None

    icons_dir_path = pathlib.Path(icons_dir)
    icons_dir_path.mkdir(parents=True, exist_ok=True)
    icon_file.write_bytes(contents)
    icon_file.chmod(0o644)
    return str(icon_file)


# ---------------------------------------------------------------------------
# Feed link discovery
# ---------------------------------------------------------------------------


def get_feeds_from_html(url: str, content: str) -> dict[str, str]:
    """Parse HTML and return dict of {feed_url: title} alternate links.

    Source: ttrss/include/functions2.php:get_feeds_from_html (lines 1787-1813)
    Adapted: Uses lxml.html instead of PHP DOMDocument + XPath.
    Source: functions2.php:1789 — fix_url($url) normalises base URL before link resolution.
    """
    try:
        from lxml import html as lxml_html
        from ttrss.http.client import fix_url as _fix_url

        # Source: functions2.php:1789 — fix_url($url) before using as base
        url = _fix_url(url) or url

        doc = lxml_html.fromstring(content, base_url=url)
        doc.make_links_absolute(url)

        feed_urls: dict[str, str] = {}
        for link in doc.cssselect('link[rel="alternate"]'):
            link_type = link.get("type", "")
            if "rss" in link_type or "atom" in link_type:
                href = link.get("href")
                if href:
                    title = link.get("title") or link_type
                    feed_urls[href] = title

        # Also match rel="feed"
        for link in doc.cssselect('link[rel="feed"]'):
            href = link.get("href")
            if href:
                feed_urls[href] = link.get("title", "")

        return feed_urls
    except Exception as exc:
        logger.debug("get_feeds_from_html: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Access keys
# ---------------------------------------------------------------------------


def get_feed_access_key(
    session: Session, feed_id: int, is_cat: bool, owner_uid: int
) -> str:
    """Return (or create) an access key for a feed or category.

    Source: ttrss/include/functions2.php:get_feed_access_key (lines 1763-1785)
    Adapted: Uses secrets.token_urlsafe instead of PHP uniqid(base_convert(rand()...)).
    """
    feed_id_str = str(feed_id)
    row = session.execute(
        select(TtRssAccessKey.access_key)
        .where(TtRssAccessKey.feed_id == feed_id_str)
        .where(TtRssAccessKey.is_cat == is_cat)
        .where(TtRssAccessKey.owner_uid == owner_uid)
    ).scalar_one_or_none()

    if row is not None:
        return row

    key = secrets.token_urlsafe(16)[:24]
    session.add(
        TtRssAccessKey(
            access_key=key,
            feed_id=feed_id_str,
            is_cat=is_cat,
            owner_uid=owner_uid,
        )
    )
    # Source: functions2.php:1780-1782 — INSERT is immediate within PHP's transaction.
    # flush() makes the row visible within the current SQLAlchemy session so the
    # returned key is usable in the same request before the outer commit.
    session.flush()
    return key


# ---------------------------------------------------------------------------
# Subscribe
# ---------------------------------------------------------------------------


def subscribe_to_feed(
    session: Session,
    url: str,
    owner_uid: int,
    cat_id: int = 0,
    auth_login: str = "",
    auth_pass: str = "",
) -> dict[str, Any]:
    """Subscribe a user to a feed URL.

    Source: ttrss/include/functions.php:subscribe_to_feed (lines 1672-1754)
    # Source: ttrss/classes/feeds.php:quickAddFeed (UI entry point; delegates to subscribe_to_feed)
    Adapted: Uses httpx + lxml instead of PHP fetch_file_contents + DOMDocument (ADR-0015).
    Auth pass encryption handled by TtRssFeed.auth_pass property (ADR-0009, Fernet).

    Return codes (matching PHP):
    0 = already subscribed
    1 = newly subscribed
    2 = invalid URL
    3 = HTML page with no feed links
    4 = HTML page with multiple feed links (feeds list in result)
    5 = fetch failed (message in result)
    """
    from ttrss.http.client import fix_url, validate_feed_url

    url = url.strip()
    # Source: ttrss/include/functions.php:1679-1681 — fix_url() then validate_feed_url()
    url = fix_url(url)
    if not url or not validate_feed_url(url):
        return {"code": 2}

    try:
        import httpx
        from lxml import html as lxml_html

        httpx_auth = (auth_login, auth_pass) if auth_login else None
        # Source: ttrss/include/functions.php:fetch_file_contents — PHP uses curl with 45s timeout
        # Adapted: reduced to 8s for responsiveness; verify=False tolerates self-signed certs in dev
        with httpx.Client(timeout=8.0, follow_redirects=True, verify=False) as client:
            resp = client.get(url, auth=httpx_auth)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            content = resp.text
    except Exception as exc:
        return {"code": 5, "message": str(exc)}

    # If response is HTML, try to discover feed links.
    # Source: functions.php:1689-1699
    is_html = "html" in content_type.lower() or content.lstrip().lower().startswith(
        ("<!doctype html", "<html")
    )
    if is_html:
        feed_urls = get_feeds_from_html(url, content)
        if not feed_urls:
            return {"code": 3}
        if len(feed_urls) > 1:
            return {"code": 4, "feeds": feed_urls}
        url = next(iter(feed_urls))

    # Check for existing subscription.
    # Source: functions.php:1719-1722
    existing = session.execute(
        select(TtRssFeed.id)
        .where(TtRssFeed.feed_url == url)
        .where(TtRssFeed.owner_uid == owner_uid)
    ).scalar_one_or_none()

    if existing is not None:
        return {"code": 0}

    # Insert new feed.
    # Source: functions.php:1734-1738
    new_feed = TtRssFeed(
        owner_uid=owner_uid,
        feed_url=url,
        title="[Unknown]",
        cat_id=cat_id or None,
        auth_login=auth_login or "",
        update_method=0,
    )
    if auth_pass:
        new_feed.auth_pass = auth_pass  # Fernet encryption via property (ADR-0009)

    session.add(new_feed)
    session.flush()  # Assign new_feed.id before triggering task

    # Source: ttrss/include/functions.php:1747 — update_rss_feed($feed_id, true) immediately after INSERT
    # Adapted: Python dispatches Celery task instead of blocking call (ADR-0011).
    # This populates feed title, site_url, and initial articles without waiting for scheduled update.
    try:
        from ttrss.tasks.feed_tasks import update_feed
        update_feed.delay(new_feed.id)
    except Exception:
        pass  # Celery unavailable (e.g., tests/CLI) — feed will update on next scheduled run

    return {"code": 1}
