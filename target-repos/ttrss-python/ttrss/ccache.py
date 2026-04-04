"""Counter cache management — per-feed unread count cache.

Source: ttrss/include/ccache.php (224 lines, 5 functions)
        ttrss/include/functions.php:getFeedArticles (lines 1401-1493, inlined as _count_feed_articles)
        ttrss/include/functions.php:getLabelUnread (lines 1388-1399, inlined in _count_feed_articles)

Dead code excluded (R12): $date_qpart TTL (ccache.php:72-76) is assigned but never included
in the SELECT query (lines 78-80 use only owner_uid + feed_id). Confirmed by PHP source inspection.

Circular import avoidance (R18): getFeedArticles logic is inlined here as _count_feed_articles
so that feeds/counters.py can import from ccache without ccache importing back from counters.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Union

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ttrss.models.counters_cache import TtRssCatCountersCache, TtRssCountersCache
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssUserLabel2
from ttrss.models.pref import TtRssPref, TtRssUserPref
from ttrss.models.tag import TtRssTag
from ttrss.models.user_entry import TtRssUserEntry
from ttrss.utils.feeds import LABEL_BASE_INDEX, feed_to_label_id

# ---------------------------------------------------------------------------
# Internal preference helpers
# ---------------------------------------------------------------------------


def _get_pref(session: Session, pref_name: str, owner_uid: int) -> str:
    """Read user preference with system-default fallback.
    Source: ttrss/include/db-prefs.php:get_pref
    """
    row = session.execute(
        select(TtRssUserPref.value)
        .where(TtRssUserPref.pref_name == pref_name)
        .where(TtRssUserPref.owner_uid == owner_uid)
        .where(TtRssUserPref.profile.is_(None))
    ).scalar_one_or_none()
    if row is not None:
        return row
    row = session.execute(
        select(TtRssPref.def_value).where(TtRssPref.pref_name == pref_name)
    ).scalar_one_or_none()
    return row or ""


def _pref_bool(session: Session, pref_name: str, owner_uid: int) -> bool:
    """Return a boolean preference value."""
    return _get_pref(session, pref_name, owner_uid).lower() == "true"


def _pref_int(session: Session, pref_name: str, owner_uid: int, default: int = 0) -> int:
    """Return an integer preference value."""
    try:
        return int(_get_pref(session, pref_name, owner_uid))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# _count_feed_articles — inlined getFeedArticles non-category logic (R18)
# ---------------------------------------------------------------------------


def _count_feed_articles(
    session: Session,
    feed_id: Union[int, str],
    owner_uid: int,
    unread_only: bool = True,
) -> int:
    """Count articles for a non-category feed.

    Inlines ttrss/include/functions.php:getFeedArticles (lines 1401-1493) and
    ttrss/include/functions.php:getLabelUnread (lines 1388-1399) to break the
    circular import that would arise if ccache imported feeds/counters.

    Source: ttrss/include/functions.php:getFeedArticles (lines 1401-1493)
    Source: ttrss/include/functions.php:getLabelUnread  (lines 1388-1399)
    Eliminated: MySQL DATE_SUB branch (functions.php:1441) — PostgreSQL INTERVAL only (R11).

    Note: is_cat=True is handled upstream in feeds/counters.py:getFeedArticles;
    this function is not called for category feeds from ccache_update.
    """
    unread_filter = TtRssUserEntry.unread.is_(True) if unread_only else None

    # Source: functions.php:1417 — feed_id == -6 (Recently Read) always returns 0.
    if feed_id == -6:
        return 0

    # Tag feed: string feed_id (non-numeric PHP string casts to 0 but feed != "0").
    # Source: functions.php:1419-1427
    if isinstance(feed_id, str):
        q = (
            select(func.count(TtRssUserEntry.int_id))
            .join(TtRssTag, TtRssTag.post_int_id == TtRssUserEntry.int_id)
            .where(TtRssTag.owner_uid == owner_uid)
            .where(TtRssTag.tag_name == feed_id)
        )
        if unread_filter is not None:
            q = q.where(unread_filter)
        return session.execute(q).scalar() or 0

    feed_id = int(feed_id)

    # Label feed: inline getLabelUnread (lines 1388-1399).
    # getLabelUnread always counts unread=true regardless of unread_only param.
    # Source: functions.php:1456-1461
    if feed_id < LABEL_BASE_INDEX:
        label_id = feed_to_label_id(feed_id)
        q = (
            select(func.count(TtRssUserEntry.ref_id))
            .join(TtRssUserLabel2, TtRssUserLabel2.article_id == TtRssUserEntry.ref_id)
            .where(TtRssUserEntry.owner_uid == owner_uid)
            .where(TtRssUserEntry.unread.is_(True))
            .where(TtRssUserLabel2.label_id == label_id)
        )
        return session.execute(q).scalar() or 0

    # Virtual and regular feeds.
    # Source: functions.php:1429-1454
    need_entries = False
    match = None

    if feed_id == -1:
        # Starred (marked).
        # Source: functions.php:1429-1430
        match = TtRssUserEntry.marked.is_(True)
    elif feed_id == -2:
        # Published.
        # Source: functions.php:1431-1432
        match = TtRssUserEntry.published.is_(True)
    elif feed_id == -3:
        # Fresh — unread, non-negative score, within FRESH_ARTICLE_MAX_AGE hours.
        # Source: functions.php:1433-1444 (MySQL DATE_SUB branch eliminated, R11)
        intl = _pref_int(session, "FRESH_ARTICLE_MAX_AGE", owner_uid, default=12)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=intl)
        match = (
            TtRssUserEntry.unread.is_(True)
            & (TtRssUserEntry.score >= 0)
            & (TtRssEntry.date_entered > cutoff)
        )
        need_entries = True
    elif feed_id == -4:
        # All articles — no additional match beyond owner_uid + unread_filter.
        # Source: functions.php:1446-1447
        match = None
    elif feed_id >= 0:
        # Regular feed; feed_id == 0 means NULL feed_id (orphan entries).
        # Source: functions.php:1448-1455
        match = TtRssUserEntry.feed_id == feed_id if feed_id != 0 else TtRssUserEntry.feed_id.is_(None)
    else:
        # Unhandled range (e.g. plugin feeds in -7 to -127).
        return 0

    # Build and execute count query.
    # Source: functions.php:1464-1487
    if need_entries:
        q = (
            select(func.count(TtRssUserEntry.int_id))
            .join(TtRssEntry, TtRssEntry.id == TtRssUserEntry.ref_id)
            .where(TtRssUserEntry.owner_uid == owner_uid)
        )
    else:
        q = select(func.count(TtRssUserEntry.int_id)).where(
            TtRssUserEntry.owner_uid == owner_uid
        )

    if unread_filter is not None:
        q = q.where(unread_filter)
    if match is not None:
        q = q.where(match)

    return session.execute(q).scalar() or 0


# ---------------------------------------------------------------------------
# Public API — matches ccache.php function signatures
# ---------------------------------------------------------------------------


def ccache_zero_all(session: Session, owner_uid: int) -> None:
    """Zero all cached unread counts for a user.
    Source: ttrss/include/ccache.php:ccache_zero_all (lines 8-13)
    """
    session.execute(
        update(TtRssCountersCache)
        .where(TtRssCountersCache.owner_uid == owner_uid)
        .values(value=0)
    )
    session.execute(
        update(TtRssCatCountersCache)
        .where(TtRssCatCountersCache.owner_uid == owner_uid)
        .values(value=0)
    )


def ccache_remove(
    session: Session,
    feed_id: int,
    owner_uid: int,
    is_cat: bool = False,
) -> None:
    """Delete a specific counter cache entry.
    Source: ttrss/include/ccache.php:ccache_remove (lines 16-27)
    """
    model = TtRssCatCountersCache if is_cat else TtRssCountersCache
    session.execute(
        sa_delete(model)
        .where(model.feed_id == feed_id)
        .where(model.owner_uid == owner_uid)
    )


def ccache_find(
    session: Session,
    feed_id: int,
    owner_uid: int,
    is_cat: bool = False,
    no_update: bool = False,
) -> int:
    """Return cached unread count; trigger ccache_update on cache miss.

    Source: ttrss/include/ccache.php:ccache_find (lines 56-91)
    Dead code excluded: $date_qpart TTL (lines 72-76) is computed but never included
    in the SELECT statement (lines 78-80 filter only on owner_uid + feed_id). Per R12.
    """
    model = TtRssCatCountersCache if is_cat else TtRssCountersCache
    row = session.execute(
        select(model.value)
        .where(model.owner_uid == owner_uid)
        .where(model.feed_id == feed_id)
        .limit(1)
    ).scalar_one_or_none()

    if row is not None:
        return int(row)
    if no_update:
        return -1
    return ccache_update(session, feed_id, owner_uid, is_cat)


def ccache_update_all(session: Session, owner_uid: int) -> None:
    """Rebuild all counter cache entries for a user.

    Source: ttrss/include/ccache.php:ccache_update_all (lines 29-53)
    Optimized (AR3): uses bulk GROUP BY + multi-row UPSERT instead of N+1 per-feed calls.
    """
    now = datetime.now(timezone.utc)

    # Bulk count unread articles per feed — used in both modes.
    feed_counts = session.execute(
        select(
            TtRssUserEntry.feed_id,
            func.count(TtRssUserEntry.int_id).label("value"),
        )
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .where(TtRssUserEntry.unread.is_(True))
        .where(TtRssUserEntry.feed_id.isnot(None))
        .group_by(TtRssUserEntry.feed_id)
    ).all()

    feeds_with_unread = {r.feed_id for r in feed_counts}

    # Feeds that are cached but now have 0 unread must be zeroed.
    # PHP loops over all cached feeds and recalculates each; the bulk GROUP BY only returns
    # feeds with unread > 0, so we must zero the remainder explicitly.
    session.execute(
        update(TtRssCountersCache)
        .where(TtRssCountersCache.owner_uid == owner_uid)
        .where(
            TtRssCountersCache.feed_id.not_in(feeds_with_unread)
            if feeds_with_unread
            else TtRssCountersCache.feed_id.isnot(None)
        )
        .values(value=0, updated=now)
    )

    if feed_counts:
        stmt = pg_insert(TtRssCountersCache).values(
            [
                {
                    "feed_id": r.feed_id,
                    "owner_uid": owner_uid,
                    "value": r.value,
                    "updated": now,
                }
                for r in feed_counts
            ]
        )
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=["feed_id", "owner_uid"],
            set_={"value": excluded.value, "updated": excluded.updated},
        )
        session.execute(stmt)

    if _pref_bool(session, "ENABLE_FEED_CATS", owner_uid):
        # Category mode: aggregate feed counters per category.
        # Source: ccache.php:33-42

        cat_counts = session.execute(
            select(
                func.coalesce(TtRssFeed.cat_id, 0).label("cat_id"),
                func.sum(TtRssCountersCache.value).label("value"),
            )
            .join(TtRssCountersCache, TtRssCountersCache.feed_id == TtRssFeed.id)
            .where(TtRssFeed.owner_uid == owner_uid)
            .group_by(func.coalesce(TtRssFeed.cat_id, 0))
        ).all()

        cat_ids_seen = {r.cat_id for r in cat_counts}
        rows = [
            {
                "feed_id": r.cat_id,
                "owner_uid": owner_uid,
                "value": int(r.value or 0),
                "updated": now,
            }
            for r in cat_counts
        ]
        # Always include category 0 (uncategorized).
        # Source: ccache.php:40-42
        if 0 not in cat_ids_seen:
            rows.append({"feed_id": 0, "owner_uid": owner_uid, "value": 0, "updated": now})

        if rows:
            stmt = pg_insert(TtRssCatCountersCache).values(rows)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=["feed_id", "owner_uid"],
                set_={"value": excluded.value, "updated": excluded.updated},
            )
            session.execute(stmt)


def ccache_update(
    session: Session,
    feed_id: int,
    owner_uid: int,
    is_cat: bool = False,
    update_pcat: bool = True,
    pcat_fast: bool = False,
) -> int:
    """Recalculate and persist the unread count for one feed or category.

    Source: ttrss/include/ccache.php:ccache_update (lines 94-191)
    """
    # Peek at previous value without triggering a recursive update.
    # Source: ccache.php:105
    prev_unread = ccache_find(session, feed_id, owner_uid, is_cat, no_update=True)

    # Negative feed_id = label: labels aren't individually cached; rebuild all.
    # Source: ccache.php:110-113
    if feed_id < 0:
        ccache_update_all(session, owner_uid)
        return 0

    now = datetime.now(timezone.utc)
    model = TtRssCatCountersCache if is_cat else TtRssCountersCache

    if is_cat and feed_id >= 0:
        # Category branch: optionally refresh child feed cache entries first,
        # then SUM them for this category.
        # Source: ccache.php:121-144
        cat_filter = (
            TtRssFeed.cat_id.is_(None) if feed_id == 0 else TtRssFeed.cat_id == feed_id
        )
        if not pcat_fast:
            child_ids = session.execute(
                select(TtRssFeed.id)
                .where(TtRssFeed.owner_uid == owner_uid)
                .where(cat_filter)
            ).scalars().all()
            for child_id in child_ids:
                ccache_update(session, child_id, owner_uid, is_cat=False, update_pcat=False)

        unread = int(
            session.execute(
                select(func.sum(TtRssCountersCache.value))
                .join(TtRssFeed, TtRssFeed.id == TtRssCountersCache.feed_id)
                .where(cat_filter)
                .where(TtRssFeed.owner_uid == owner_uid)
            ).scalar()
            or 0
        )
    else:
        # Regular or virtual feed.
        # Source: ccache.php:147
        unread = int(_count_feed_articles(session, feed_id, owner_uid, unread_only=True))

    # UPSERT the cached value.
    # Source: ccache.php:150-167
    stmt = pg_insert(model).values(
        feed_id=feed_id, owner_uid=owner_uid, value=unread, updated=now
    )
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=["feed_id", "owner_uid"],
        set_={"value": excluded.value, "updated": excluded.updated},
    )
    session.execute(stmt)

    # Cascade to parent category when the count changed.
    # Source: ccache.php:169-188
    if feed_id > 0 and prev_unread != unread and not is_cat and update_pcat:
        cat_id_val = session.execute(
            select(TtRssFeed.cat_id)
            .where(TtRssFeed.owner_uid == owner_uid)
            .where(TtRssFeed.id == feed_id)
        ).scalar_one_or_none()
        cat_id = cat_id_val if cat_id_val is not None else 0
        ccache_update(session, cat_id, owner_uid, is_cat=True, update_pcat=True, pcat_fast=True)

    return unread
