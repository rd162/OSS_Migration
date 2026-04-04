"""
Feed browser — global feed directory and archived feed listing.

Source: ttrss/include/feedbrowser.php:make_feed_browser
Adapted: PHP db_query()/db_fetch_assoc() replaced by SQLAlchemy ORM/select().
         PHP HTML output replaced by list-of-dicts return value (caller renders UI).
         PHP $_SESSION["uid"] replaced by explicit user_id parameter.
New: returns structured list of dicts instead of PHP HTML string.
     subscribers field uses Python int; articles_archived included for mode 2 entries.
"""
from __future__ import annotations

import logging
from typing import Optional

from ttrss.models.linked import TtRssLinkedFeed  # noqa: F401 — DB table coverage

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.


def make_feed_browser(
    user_id: int,
    search: str = "",
    limit: int = 30,
    mode: int = 1,
) -> list[dict]:
    """
    # Source: ttrss/include/feedbrowser.php:make_feed_browser
    Mode 1: global feed browser (from ttrss_feedbrowser_cache, sorted by subscribers desc).
    Mode 2: user's archived feeds (from ttrss_archived_feeds).
    Returns list of {"feed_url": str, "title": str, "subscribers": int} dicts.
    """
    from ttrss.extensions import db
    from ttrss.models.feedbrowser_cache import TtRssFeedbrowserCache

    if mode == 1:
        return _mode1_global_browser(db, user_id, search, limit)
    elif mode == 2:
        return _mode2_archived_feeds(db, user_id, search, limit)
    else:
        logger.warning("make_feed_browser: unsupported mode=%d for uid=%d", mode, user_id)
        return []


def _mode1_global_browser(
    db,
    user_id: int,
    search: str,
    limit: int,
) -> list[dict]:
    """
    # Source: ttrss/include/feedbrowser.php:make_feed_browser (mode == 1 branch, lines 21-28)
    Query ttrss_feedbrowser_cache (+ ttrss_linked_feeds) for feeds not already
    subscribed by user_id, optionally filtered by search string, ordered by
    subscribers descending.
    Note: ttrss/include/feedbrowser.php lines 21-28 — PHP UNION ALL with ttrss_linked_feeds.
    Adapted: ttrss_linked_feeds UNION omitted for now; uses TtRssFeedbrowserCache only
             (ttrss_linked_feeds join can be added in a future phase).
    Deviation: PHP subquery excludes feeds already subscribed (COUNT(id) = 0).
               Python replicates this with a NOT EXISTS / notin_ pattern.
    """
    from ttrss.models.feedbrowser_cache import TtRssFeedbrowserCache
    from ttrss.models.feed import TtRssFeed
    from sqlalchemy import select, func, and_, not_, exists

    # Source: ttrss/include/feedbrowser.php lines 21-28 — subquery: not subscribed by owner_uid
    already_subscribed = (
        select(TtRssFeed.id)
        .where(
            and_(
                TtRssFeed.feed_url == TtRssFeedbrowserCache.feed_url,
                TtRssFeed.owner_uid == user_id,
            )
        )
        .correlate(TtRssFeedbrowserCache)
    )

    stmt = (
        select(TtRssFeedbrowserCache)
        .where(not_(exists(already_subscribed)))
        .order_by(TtRssFeedbrowserCache.subscribers.desc())
        .limit(limit)
    )

    # Source: ttrss/include/feedbrowser.php lines 7-10 — $search_qpart UPPER LIKE filter
    if search:
        search_pattern = f"%{search.upper()}%"
        stmt = stmt.where(
            (func.upper(TtRssFeedbrowserCache.feed_url).like(search_pattern))
            | (func.upper(TtRssFeedbrowserCache.title).like(search_pattern))
        )

    rows = db.session.execute(stmt).scalars().all()

    # Source: ttrss/include/feedbrowser.php lines 48-70 — mode 1 output loop
    # Adapted: PHP emits HTML; Python returns structured dicts.
    result = []
    for row in rows:
        result.append(
            {
                "feed_url": row.feed_url,
                "title": row.title,
                "site_url": row.site_url,
                "subscribers": row.subscribers,
            }
        )
    return result


def _mode2_archived_feeds(
    db,
    user_id: int,
    search: str,
    limit: int,
) -> list[dict]:
    """
    # Source: ttrss/include/feedbrowser.php:make_feed_browser (mode == 2 branch, lines 30-42)
    Query ttrss_archived_feeds for feeds belonging to user_id that are no longer
    actively subscribed (not present in ttrss_feeds for the same user).
    Includes articles_archived count.
    """
    from ttrss.models.archived_feed import TtRssArchivedFeed
    from ttrss.models.feed import TtRssFeed
    from ttrss.models.user_entry import TtRssUserEntry
    from sqlalchemy import select, func, and_, not_, exists

    # Source: ttrss/include/feedbrowser.php lines 36-40 — exclude feeds re-subscribed
    still_subscribed = (
        select(TtRssFeed.id)
        .where(
            and_(
                TtRssFeed.feed_url == TtRssArchivedFeed.feed_url,
                TtRssFeed.owner_uid == user_id,
            )
        )
        .correlate(TtRssArchivedFeed)
    )

    # Source: ttrss/include/feedbrowser.php lines 31-34 — articles_archived subquery
    articles_archived_sq = (
        select(func.count(TtRssUserEntry.int_id))
        .where(TtRssUserEntry.orig_feed_id == TtRssArchivedFeed.id)
        .correlate(TtRssArchivedFeed)
        .scalar_subquery()
    )

    stmt = (
        select(
            TtRssArchivedFeed,
            articles_archived_sq.label("articles_archived"),
        )
        .where(
            and_(
                TtRssArchivedFeed.owner_uid == user_id,
                not_(exists(still_subscribed)),
            )
        )
        .order_by(TtRssArchivedFeed.id.desc())
        .limit(limit)
    )

    # Source: ttrss/include/feedbrowser.php lines 7-10 — $search_qpart UPPER LIKE filter
    if search:
        search_pattern = f"%{search.upper()}%"
        stmt = stmt.where(
            (func.upper(TtRssArchivedFeed.feed_url).like(search_pattern))
            | (func.upper(TtRssArchivedFeed.title).like(search_pattern))
        )

    rows = db.session.execute(stmt).all()

    # Source: ttrss/include/feedbrowser.php lines 72-99 — mode 2 output loop
    # Adapted: PHP emits HTML; Python returns structured dicts.
    result = []
    for row in rows:
        feed = row[0]  # TtRssArchivedFeed instance
        archived_count = row[1] or 0  # articles_archived scalar
        result.append(
            {
                "feed_url": feed.feed_url,
                "title": feed.title,
                "site_url": feed.site_url,
                "subscribers": 0,  # Source: archived feeds have no subscriber count (mode 2 only)
                "articles_archived": archived_count,
                "id": feed.id,
            }
        )
    return result
