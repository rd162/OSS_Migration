"""Feed counter queries — getAllCounters, per-feed/category/label/virtual counters.

Source: ttrss/include/functions.php
    getAllCounters        (line 1239-1248)
    getCategoryCounters  (line 1270-1311)
    getCategoryChildrenUnread (line 1314-1328)
    getCategoryUnread    (line 1330-1382)
    getFeedUnread        (line 1384-1386) — inlined as _feed_unread helper
    getLabelUnread       (line 1388-1399) — inlined in ccache._count_feed_articles (R18)
    getFeedArticles      (line 1401-1493) — public wrapper delegates to ccache
    getGlobalUnread      (line 1495-1507)
    getGlobalCounters    (line 1509-1532)
    getVirtCounters      (line 1534-1572)
    getLabelCounters     (line 1574-1602)
    getFeedCounters      (line 1604-1651)

Eliminated (R13): active_feed title truncation kept as data, no HTML rendering.
Eliminated (R11): MySQL DATE_SUB branches — PostgreSQL INTERVAL used.
Eliminated (R13/plugin): PluginHost.get_feeds(-1) virtual feeds — no pluggy hook yet.
ccache_update call sites #3-#9 are in task/housekeeping layers (not here).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from ttrss.ccache import _count_feed_articles, ccache_find
from ttrss.models.category import TtRssFeedCategory
from ttrss.models.counters_cache import TtRssCatCountersCache, TtRssCountersCache
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2, TtRssUserLabel2
from ttrss.models.user_entry import TtRssUserEntry
from ttrss.utils.feeds import LABEL_BASE_INDEX, label_to_feed_id

logger = logging.getLogger(__name__)

# Maximum year gap before last_updated is considered too stale to display.
_MAX_UPDATED_AGE_YEARS = 2


# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------


def getGlobalUnread(session: Session, owner_uid: int) -> int:
    """Return total cached unread count across all real feeds for a user.

    Source: ttrss/include/functions.php:getGlobalUnread (lines 1495-1507)
    Uses ttrss_counters_cache WHERE feed_id > 0 (excludes virtual feeds).
    """
    result = session.execute(
        select(func.sum(TtRssCountersCache.value))
        .where(TtRssCountersCache.owner_uid == owner_uid)
        .where(TtRssCountersCache.feed_id > 0)
    ).scalar()
    return int(result) if result is not None else 0


def getGlobalCounters(session: Session, owner_uid: int) -> list[dict[str, Any]]:
    """Return global-unread and subscribed-feeds counter dicts.

    Source: ttrss/include/functions.php:getGlobalCounters (lines 1509-1532)
    """
    global_unread = getGlobalUnread(session, owner_uid)
    subscribed = session.execute(
        select(func.count(TtRssFeed.id)).where(TtRssFeed.owner_uid == owner_uid)
    ).scalar() or 0

    return [
        {"id": "global-unread", "counter": global_unread},
        {"id": "subscribed-feeds", "counter": int(subscribed)},
    ]


# ---------------------------------------------------------------------------
# Category counters
# ---------------------------------------------------------------------------


def getCategoryUnread(session: Session, cat_id: int, owner_uid: int) -> int:
    """Return unread count for a category (by summing its feed user_entries).

    Source: ttrss/include/functions.php:getCategoryUnread (lines 1330-1382)
    cat_id >= 0: sum unread from ttrss_user_entries for feeds in that category.
    cat_id == -1: Special — sum of starred/published/fresh/archived unread.
    cat_id == -2: Labels — count unread entries that have any label.
    """
    if cat_id >= 0:
        if cat_id != 0:
            feed_subq = (
                select(TtRssFeed.id)
                .where(TtRssFeed.cat_id == cat_id)
                .where(TtRssFeed.owner_uid == owner_uid)
                .scalar_subquery()
            )
        else:
            # cat_id == 0 means uncategorized (cat_id IS NULL)
            feed_subq = (
                select(TtRssFeed.id)
                .where(TtRssFeed.cat_id.is_(None))
                .where(TtRssFeed.owner_uid == owner_uid)
                .scalar_subquery()
            )

        result = session.execute(
            select(func.count(TtRssUserEntry.int_id))
            .where(TtRssUserEntry.unread.is_(True))
            .where(TtRssUserEntry.feed_id.in_(feed_subq))
            .where(TtRssUserEntry.owner_uid == owner_uid)
        ).scalar()
        return int(result) if result is not None else 0

    if cat_id == -1:
        # Special: starred + published + fresh + archived (feed 0)
        # Source: functions.php:1368
        return sum(
            _feed_unread(session, fid, owner_uid)
            for fid in (-1, -2, -3, 0)
        )

    if cat_id == -2:
        # Labels: count unread entries that have any label assignment
        # Source: functions.php:1369-1379
        result = session.execute(
            select(func.count(TtRssUserEntry.int_id))
            .join(TtRssUserLabel2, TtRssUserLabel2.article_id == TtRssUserEntry.ref_id)
            .where(TtRssUserEntry.unread.is_(True))
            .where(TtRssUserEntry.owner_uid == owner_uid)
        ).scalar()
        return int(result) if result is not None else 0

    return 0


def getCategoryChildrenUnread(session: Session, cat_id: int, owner_uid: int) -> int:
    """Return sum of unread counts for all child categories (recursive).

    Source: ttrss/include/functions.php:getCategoryChildrenUnread (lines 1314-1328)
    Note: no depth guard in PHP (assumes DB integrity); Python matches PHP behaviour.
    """
    child_ids = session.execute(
        select(TtRssFeedCategory.id)
        .where(TtRssFeedCategory.parent_cat == cat_id)
        .where(TtRssFeedCategory.owner_uid == owner_uid)
    ).scalars().all()

    unread = 0
    for child_id in child_ids:
        unread += getCategoryUnread(session, child_id, owner_uid)
        unread += getCategoryChildrenUnread(session, child_id, owner_uid)
    return unread


def getCategoryCounters(session: Session, owner_uid: int) -> list[dict[str, Any]]:
    """Return counter dicts for all categories + Labels (-2) + Uncategorized (0).

    Source: ttrss/include/functions.php:getCategoryCounters (lines 1270-1311)
    """
    ret: list[dict[str, Any]] = []

    # Labels virtual category (-2)
    ret.append({"id": -2, "kind": "cat", "counter": getCategoryUnread(session, -2, owner_uid)})

    # Real categories from DB joined with ttrss_cat_counters_cache
    # Alias for the self-referential child-count subquery.
    c2 = aliased(TtRssFeedCategory, flat=True)
    child_count_subq = (
        select(func.count(c2.id))
        .where(c2.parent_cat == TtRssFeedCategory.id)
        .correlate(TtRssFeedCategory)
        .scalar_subquery()
    )

    rows = session.execute(
        select(
            TtRssFeedCategory.id.label("cat_id"),
            TtRssCatCountersCache.value.label("unread"),
            child_count_subq.label("num_children"),
        )
        .join(
            TtRssCatCountersCache,
            (TtRssCatCountersCache.feed_id == TtRssFeedCategory.id)
            & (TtRssCatCountersCache.owner_uid == TtRssFeedCategory.owner_uid),
        )
        .where(TtRssFeedCategory.owner_uid == owner_uid)
    ).all()

    for row in rows:
        cat_id = int(row.cat_id)
        child_counter = (
            getCategoryChildrenUnread(session, cat_id, owner_uid)
            if row.num_children > 0
            else 0
        )
        ret.append({"id": cat_id, "kind": "cat", "counter": int(row.unread) + child_counter})

    # Uncategorized (cat_id=0, no real DB row) via ccache_find
    # Source: functions.php:1305-1308
    uncategorized_count = ccache_find(session, feed_id=0, owner_uid=owner_uid, is_cat=True)
    ret.append({"id": 0, "kind": "cat", "counter": int(uncategorized_count)})

    return ret


# ---------------------------------------------------------------------------
# Virtual feed counters (feed IDs -1 to -4)
# ---------------------------------------------------------------------------


def _feed_unread(session: Session, feed_id: int, owner_uid: int) -> int:
    """Return unread count for a single virtual feed (non-category path).

    Source: ttrss/include/functions.php:getFeedUnread (line 1384-1386)
    Delegates to ccache._count_feed_articles (inlined, avoids circular import R18).
    """
    return _count_feed_articles(session, feed_id, owner_uid, unread_only=True)


def getVirtCounters(session: Session, owner_uid: int) -> list[dict[str, Any]]:
    """Return counter dicts for virtual feeds 0, -1, -2, -3, -4.

    Source: ttrss/include/functions.php:getVirtCounters (lines 1534-1572)
    Eliminated: PluginHost.get_feeds(-1) plugin virtual feeds (no pluggy hook yet).
    auxcounter is the total article count (all, not just unread) for feeds 0/-1/-2.
    """
    ret: list[dict[str, Any]] = []
    for i in range(0, -5, -1):
        count = _feed_unread(session, i, owner_uid)
        # Total count (unread=False) only for feeds 0, -1, -2
        # Source: functions.php:1542-1545
        auxctr: int = 0
        if i in (0, -1, -2):
            auxctr = int(
                _count_feed_articles(session, i, owner_uid, unread_only=False) or 0
            )
        ret.append({"id": i, "counter": int(count), "auxcounter": auxctr})
    return ret


# ---------------------------------------------------------------------------
# Label counters
# ---------------------------------------------------------------------------


def getLabelCounters(
    session: Session, owner_uid: int, descriptions: bool = False
) -> list[dict[str, Any]]:
    """Return counter dicts for all labels (virtual feed IDs).

    Source: ttrss/include/functions.php:getLabelCounters (lines 1574-1602)
    Counter = unread count, auxcounter = total count across all labelled entries.
    """
    rows = session.execute(
        select(
            TtRssLabel2.id,
            TtRssLabel2.caption,
            func.sum(
                case((TtRssUserEntry.unread.is_(True), 1), else_=0)
            ).label("unread"),
            func.count(TtRssUserEntry.int_id).label("total"),
        )
        .outerjoin(TtRssUserLabel2, TtRssLabel2.id == TtRssUserLabel2.label_id)
        .outerjoin(
            TtRssUserEntry,
            # Source: functions.php:1584 — u1.ref_id = article_id
            # D01 fix: also restrict to owner_uid to prevent cross-user label counts
            (TtRssUserEntry.ref_id == TtRssUserLabel2.article_id)
            & (TtRssUserEntry.owner_uid == owner_uid),
        )
        .where(TtRssLabel2.owner_uid == owner_uid)
        .group_by(TtRssLabel2.id, TtRssLabel2.caption)
    ).all()

    ret: list[dict[str, Any]] = []
    for row in rows:
        vfid = label_to_feed_id(row.id)
        cv: dict[str, Any] = {
            "id": vfid,
            "counter": int(row.unread or 0),
            "auxcounter": int(row.total or 0),
        }
        if descriptions:
            cv["description"] = row.caption
        ret.append(cv)
    return ret


# ---------------------------------------------------------------------------
# Feed counters (real feeds)
# ---------------------------------------------------------------------------


def getFeedCounters(
    session: Session,
    owner_uid: int,
    active_feed: Optional[int] = None,
    icons_dir: str = "",
) -> list[dict[str, Any]]:
    """Return counter dicts for all real feeds from ttrss_counters_cache.

    Source: ttrss/include/functions.php:getFeedCounters (lines 1604-1651)
    Adapted: feed_has_icon requires icons_dir (filesystem path).
    Adapted: last_updated returned as ISO string; cleared if > 2 years old.
    Eliminated: EXTENDED_FEEDLIST xmsg (commented out in PHP).
    Eliminated: make_local_datetime — UTC ISO used instead.
    """
    from ttrss.feeds.ops import feed_has_icon  # local import to avoid circular (R18)

    rows = session.execute(
        select(
            TtRssFeed.id,
            TtRssFeed.title,
            TtRssFeed.last_updated,
            TtRssFeed.last_error,
            TtRssCountersCache.value.label("count"),
        )
        .join(
            TtRssCountersCache,
            (TtRssCountersCache.feed_id == TtRssFeed.id)
            & (TtRssCountersCache.owner_uid == TtRssFeed.owner_uid),
        )
        .where(TtRssFeed.owner_uid == owner_uid)
    ).all()

    now_year = datetime.now(timezone.utc).year
    ret: list[dict[str, Any]] = []
    for row in rows:
        feed_id = int(row.id)

        # Stale last_updated: blank if > 2 years old (matches PHP logic)
        last_updated = ""
        if row.last_updated is not None:
            lu = row.last_updated
            if hasattr(lu, "year"):
                if now_year - lu.year <= _MAX_UPDATED_AGE_YEARS:
                    last_updated = lu.isoformat()
            else:
                last_updated = str(lu)[:19]

        has_img = feed_has_icon(feed_id, icons_dir)
        last_error = (row.last_error or "").strip()

        cv: dict[str, Any] = {
            "id": feed_id,
            "updated": last_updated,
            "counter": int(row.count or 0),
            "has_img": int(has_img),
        }
        if last_error:
            cv["error"] = last_error

        # active_feed: include title (truncated to 30 chars, matching PHP)
        if active_feed is not None and feed_id == active_feed:
            cv["title"] = (row.title or "")[:30]

        ret.append(cv)
    return ret


# ---------------------------------------------------------------------------
# Top-level aggregator
# ---------------------------------------------------------------------------


def getAllCounters(session: Session, owner_uid: int, icons_dir: str = "") -> list[dict[str, Any]]:
    """Return all counters: global + virtual + label + feed + category.

    Source: ttrss/include/functions.php:getAllCounters (lines 1239-1248)
    """
    data: list[dict[str, Any]] = []
    data.extend(getGlobalCounters(session, owner_uid))
    data.extend(getVirtCounters(session, owner_uid))
    data.extend(getLabelCounters(session, owner_uid))
    data.extend(getFeedCounters(session, owner_uid, icons_dir=icons_dir))
    data.extend(getCategoryCounters(session, owner_uid))
    return data


# ---------------------------------------------------------------------------
# Public getFeedArticles wrapper
# ---------------------------------------------------------------------------


def getFeedArticles(
    session: Session,
    feed_id: int | str,
    owner_uid: int,
    is_cat: bool = False,
    unread_only: bool = True,
) -> int:
    """Return article count for a feed or category.

    Source: ttrss/include/functions.php:getFeedArticles (lines 1401-1493)
    Category path delegates to getCategoryUnread.
    Non-category path delegates to ccache._count_feed_articles.
    """
    if is_cat:
        return getCategoryUnread(session, int(feed_id), owner_uid)
    return int(_count_feed_articles(session, feed_id, owner_uid, unread_only=unread_only) or 0)
