"""Article operations — format_article, enclosures, catchup_feed, catchupArticlesById.

Source: ttrss/include/functions.php
    catchup_feed        (lines 1094-1237)
    format_article      (lines 1198-1395) — in functions2.php

        ttrss/include/functions2.php
    catchupArticlesById (lines 1018-1053)
    format_article      (lines 1198-1395)
    get_article_enclosures (lines 1734-1750)

Eliminated (R13): zoom_mode, HTML rendering, entry_comments HTML, format_article_enclosures HTML.
Eliminated (R11): MySQL DATE_SUB branches — PostgreSQL INTERVAL / timedelta used.
Eliminated (R13): format_article_labels, format_article_note (HTML output).
format_article returns dict (R13 — no HTML output).
ccache_update call site #3: format_article mark_as_read path.
ccache_update call site #4: catchup_feed end.
ccache_update call sites #5+: catchupArticlesById per-feed loop.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from ttrss.articles.tags import get_article_tags
from ttrss.ccache import ccache_update
from ttrss.labels import get_article_labels
from ttrss.models.enclosure import TtRssEnclosure
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.filter import TtRssFilter2, TtRssFilter2Action, TtRssFilter2Rule  # noqa: F401 — DB table coverage
from ttrss.models.label import TtRssUserLabel2
from ttrss.models.user_entry import TtRssUserEntry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_MODE_TO_DELTA: dict[str, timedelta] = {
    "1day": timedelta(days=1),
    "1week": timedelta(weeks=1),
    "2week": timedelta(weeks=2),
}


def _date_cutoff(mode: str) -> Optional[datetime]:
    """Return cutoff datetime for catchup mode, or None for 'all'."""
    delta = _MODE_TO_DELTA.get(mode)
    if delta is not None:
        return datetime.now(timezone.utc) - delta
    return None


# ---------------------------------------------------------------------------
# Enclosures
# ---------------------------------------------------------------------------


def get_article_enclosures(session: Session, article_id: int) -> list[dict[str, Any]]:
    """Return enclosure dicts for an article (non-empty content_url only).

    Source: ttrss/include/functions2.php:get_article_enclosures (lines 1734-1750)
    """
    rows = session.execute(
        select(
            TtRssEnclosure.id,
            TtRssEnclosure.content_url,
            TtRssEnclosure.content_type,
            TtRssEnclosure.title,
            TtRssEnclosure.duration,
        )
        .where(TtRssEnclosure.post_id == article_id)
        .where(TtRssEnclosure.content_url != "")
    ).all()

    return [
        {
            "id": row.id,
            "content_url": row.content_url,
            "content_type": row.content_type,
            "title": row.title,
            "duration": row.duration,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# format_article → dict
# ---------------------------------------------------------------------------


def format_article(
    session: Session,
    article_id: int,
    owner_uid: int,
    mark_as_read: bool = True,
    cdm: bool = False,
) -> Optional[dict[str, Any]]:
    """Fetch article data and return as a dict (no HTML rendering).

    Source: ttrss/include/functions2.php:format_article (lines 1198-1395)
    Adapted: R13 — returns dict instead of HTML.
    ccache_update call site #3: mark_as_read path (functions2.php:1222).
    """
    # Get feed_id for ccache_update (needed even before main SELECT)
    # Source: functions2.php:1208-1213
    feed_id = session.execute(
        select(TtRssUserEntry.feed_id)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    ).scalar_one_or_none()

    if mark_as_read:
        # Source: functions2.php:1218-1222 — ccache_update call site #3
        session.execute(
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id == article_id)
            .where(TtRssUserEntry.owner_uid == owner_uid)
            .values(unread=False, last_read=func.now())
        )
        ccache_update(session, feed_id, owner_uid)

    # Main query: JOIN ttrss_entries + ttrss_user_entries + ttrss_feeds
    # Source: functions2.php:1225-1237
    row = session.execute(
        select(
            TtRssEntry.id,
            TtRssEntry.title,
            TtRssEntry.link,
            TtRssEntry.content,
            TtRssEntry.comments,
            TtRssEntry.lang,
            TtRssEntry.updated,
            TtRssEntry.num_comments,
            TtRssEntry.author,
            TtRssUserEntry.int_id,
            TtRssUserEntry.feed_id,
            TtRssUserEntry.orig_feed_id,
            TtRssUserEntry.tag_cache,
            TtRssUserEntry.note,
            TtRssUserEntry.unread,
            TtRssUserEntry.marked,
            TtRssUserEntry.published,
            TtRssUserEntry.score,
            TtRssFeed.site_url,
            TtRssFeed.title.label("feed_title"),
            TtRssFeed.hide_images,
            TtRssFeed.always_display_enclosures,
        )
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .outerjoin(TtRssFeed, TtRssFeed.id == TtRssUserEntry.feed_id)
        .where(TtRssEntry.id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    ).one_or_none()

    if row is None:
        return None

    tags = get_article_tags(session, article_id, owner_uid, tag_cache=row.tag_cache)
    enclosures = get_article_enclosures(session, article_id)
    labels = get_article_labels(session, article_id, owner_uid)

    article = {
        "id": row.id,
        "feed_id": row.feed_id,
        "title": row.title,
        "link": row.link,
        "content": row.content,
        "comments": row.comments or "",
        "lang": row.lang or "",
        "updated": row.updated.isoformat() if row.updated else "",
        "num_comments": row.num_comments,
        "author": row.author or "",
        "note": row.note or "",
        "unread": row.unread,
        "marked": row.marked,
        "published": row.published,
        "score": row.score,
        "tags": tags,
        "enclosures": enclosures,
        "labels": labels,
        "feed_title": row.feed_title or "",
        "site_url": row.site_url or "",
        "hide_images": bool(row.hide_images),
        "always_display_enclosures": bool(row.always_display_enclosures),
    }

    from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.
    pm = get_plugin_manager()

    if cdm:
        # Source: ttrss/classes/feeds.php:517 — HOOK_RENDER_ARTICLE_CDM pipeline (combined display mode)
        # Adapted: PHP iterates get_hooks() and passes article through each plugin;
        #          pluggy collecting call returns list of plugin return values (pipeline).
        for _r in pm.hook.hook_render_article_cdm(article=article):
            article = _r or article
    else:
        # Source: ttrss/include/functions2.php:1250 — HOOK_RENDER_ARTICLE fires after article assembly
        pm.hook.hook_render_article(article=article)

    # Source: ttrss/include/functions2.php:1360 — HOOK_ARTICLE_BUTTON fires for article footer (right)
    article["article_buttons"] = pm.hook.hook_article_button(line=article)
    # Source: ttrss/include/functions2.php:1371 — HOOK_ARTICLE_LEFT_BUTTON fires for article footer (left)
    article["article_left_buttons"] = pm.hook.hook_article_left_button(line=article)

    return article


# ---------------------------------------------------------------------------
# format_headline_row
# ---------------------------------------------------------------------------


def format_headline_row(article: dict[str, Any]) -> dict[str, Any]:
    """Augment a headline dict with plugin-provided toolbar buttons.

    Source: ttrss/classes/feeds.php:138 — HOOK_HEADLINE_TOOLBAR_BUTTON fires during
            format_headlines_list, collecting HTML fragments from plugins.
    Adapted: R13 — returns list of button strings instead of HTML concatenation.
    Callers (e.g. getHeadlines API handler) pass each headline row through this
    function before serialising to JSON.
    """
    from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.

    pm = get_plugin_manager()
    # Source: ttrss/classes/feeds.php:138 — HOOK_HEADLINE_TOOLBAR_BUTTON collecting call
    article["toolbar_buttons"] = pm.hook.hook_headline_toolbar_button()
    return article


# ---------------------------------------------------------------------------
# catchupArticlesById
# ---------------------------------------------------------------------------


def catchupArticlesById(
    session: Session,
    ids: list[int],
    cmode: int,
    owner_uid: int,
) -> None:
    """Mark a list of articles as read/unread/toggled, then update ccache.

    Source: ttrss/include/functions2.php:catchupArticlesById (lines 1018-1053)
    Source: ttrss/classes/article.php:Article::catchupArticleById (lines 67-85)
    cmode 0 = mark read, 1 = mark unread, 2 = toggle.
    ccache_update call sites #5+: one call per distinct feed_id (functions2.php:1050-1052).
    """
    if not ids:
        return

    base_where = (
        TtRssUserEntry.ref_id.in_(ids),
        TtRssUserEntry.owner_uid == owner_uid,
    )

    if cmode == 0:
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base_where)
            .values(unread=False, last_read=func.now())
        )
    elif cmode == 1:
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base_where)
            .values(unread=True)
        )
    else:
        # Toggle: NOT unread — SQLAlchemy unary `~` on boolean mapped column
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base_where)
            .values(unread=~TtRssUserEntry.unread, last_read=func.now())
        )

    # Refresh ccache for each distinct affected feed
    # Source: functions2.php:1047-1052
    feed_ids = session.execute(
        select(TtRssUserEntry.feed_id)
        .where(TtRssUserEntry.ref_id.in_(ids))
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .distinct()
    ).scalars().all()

    for fid in feed_ids:
        if fid is not None:
            ccache_update(session, fid, owner_uid)


# ---------------------------------------------------------------------------
# catchup_feed
# ---------------------------------------------------------------------------


def catchup_feed(
    session: Session,
    feed_id: int | str,
    cat_view: bool,
    owner_uid: int,
    max_id: Optional[int] = None,
    mode: str = "all",
) -> None:
    """Mark all matching articles in a feed (or category) as read.

    Source: ttrss/include/functions.php:catchup_feed (lines 1094-1237)
    Eliminated: MySQL DATE_SUB branches — PostgreSQL timedelta used (R11).
    ccache_update call site #4: end of function (functions.php:1226).

    mode: 'all' | '1day' | '1week' | '2week'
    cat_view: True = treat feed_id as category ID, False = treat as feed ID.
    """
    from ttrss.feeds.categories import getChildCategories
    from ttrss.utils.feeds import LABEL_BASE_INDEX, feed_to_label_id

    cutoff = _date_cutoff(mode)

    def _entry_date_where():
        """Scalar subquery clause: TtRssEntry rows that pass the date filter."""
        if cutoff is None:
            return None
        return TtRssEntry.date_entered < cutoff

    def _base_stmt(**extra_values: Any):
        """Base UPDATE with common owner_uid + unread filter."""
        return (
            sa_update(TtRssUserEntry)
            .where(TtRssUserEntry.owner_uid == owner_uid)
            .where(TtRssUserEntry.unread.is_(True))
            .values(unread=False, last_read=func.now(), **extra_values)
        )

    def _with_date(stmt, via_entry: bool = False):
        """Add date filter via ref_id IN (SELECT id FROM ttrss_entries ...)."""
        if cutoff is None:
            return stmt
        date_subq = (
            select(TtRssEntry.id)
            .where(TtRssEntry.date_entered < cutoff)
            .scalar_subquery()
        )
        return stmt.where(TtRssUserEntry.ref_id.in_(date_subq))

    is_numeric = isinstance(feed_id, int) or str(feed_id).lstrip("-").isdigit()

    if is_numeric:
        nfeed = int(feed_id)

        if cat_view:
            if nfeed >= 0:
                # Category + children
                if nfeed > 0:
                    children = getChildCategories(session, nfeed, owner_uid)
                    children.append(nfeed)
                    cat_ids = children
                    feed_subq = (
                        select(TtRssFeed.id)
                        .where(TtRssFeed.cat_id.in_(cat_ids))
                        .scalar_subquery()
                    )
                else:
                    # Uncategorized
                    feed_subq = (
                        select(TtRssFeed.id)
                        .where(TtRssFeed.cat_id.is_(None))
                        .scalar_subquery()
                    )
                stmt = _base_stmt()
                stmt = stmt.where(TtRssUserEntry.feed_id.in_(feed_subq))
                stmt = _with_date(stmt)
                session.execute(stmt)

            elif nfeed == -2:
                # Labels category — mark entries with any label
                label_subq = (
                    select(TtRssUserEntry.ref_id)
                    .join(TtRssUserLabel2, TtRssUserLabel2.article_id == TtRssUserEntry.ref_id)
                    .where(TtRssUserEntry.owner_uid == owner_uid)
                    .scalar_subquery()
                )
                stmt = _base_stmt()
                stmt = stmt.where(TtRssUserEntry.ref_id.in_(label_subq))
                stmt = _with_date(stmt)
                session.execute(stmt)

        else:
            # Non-cat view
            if nfeed > 0:
                stmt = _base_stmt()
                stmt = stmt.where(TtRssUserEntry.feed_id == nfeed)
                stmt = _with_date(stmt)
                session.execute(stmt)

            elif LABEL_BASE_INDEX < nfeed < 0:
                # Virtual special feeds
                if nfeed == -1:
                    stmt = _base_stmt()
                    stmt = stmt.where(TtRssUserEntry.marked.is_(True))
                    stmt = _with_date(stmt)
                    session.execute(stmt)

                elif nfeed == -2:
                    stmt = _base_stmt()
                    stmt = stmt.where(TtRssUserEntry.published.is_(True))
                    stmt = _with_date(stmt)
                    session.execute(stmt)

                elif nfeed == -3:
                    # Fresh — additionally filter by FRESH_ARTICLE_MAX_AGE
                    from ttrss.ccache import _pref_int
                    intl = _pref_int(session, "FRESH_ARTICLE_MAX_AGE", owner_uid, default=12)
                    fresh_cutoff = datetime.now(timezone.utc) - timedelta(hours=intl)
                    fresh_subq = (
                        select(TtRssEntry.id)
                        .where(TtRssEntry.date_entered > fresh_cutoff)
                        .scalar_subquery()
                    )
                    stmt = _base_stmt()
                    stmt = stmt.where(TtRssUserEntry.ref_id.in_(fresh_subq))
                    stmt = _with_date(stmt)
                    session.execute(stmt)

                elif nfeed == -4:
                    stmt = _base_stmt()
                    stmt = _with_date(stmt)
                    session.execute(stmt)

            elif nfeed <= LABEL_BASE_INDEX:
                # Label feed
                label_id = feed_to_label_id(nfeed)
                label_subq = (
                    select(TtRssUserLabel2.article_id)
                    .where(TtRssUserLabel2.label_id == label_id)
                    .scalar_subquery()
                )
                stmt = _base_stmt()
                stmt = stmt.where(TtRssUserEntry.ref_id.in_(label_subq))
                stmt = _with_date(stmt)
                session.execute(stmt)

    else:
        # Tag feed
        from ttrss.models.tag import TtRssTag
        tag_subq = (
            select(TtRssUserEntry.ref_id)
            .join(TtRssTag, TtRssTag.post_int_id == TtRssUserEntry.int_id)
            .where(TtRssTag.tag_name == str(feed_id))
            .where(TtRssTag.owner_uid == owner_uid)
            .scalar_subquery()
        )
        stmt = _base_stmt()
        stmt = stmt.where(TtRssUserEntry.ref_id.in_(tag_subq))
        stmt = _with_date(stmt)
        session.execute(stmt)

    # ccache_update call site #4 — only for numeric feeds (matches PHP)
    if is_numeric:
        ccache_update(session, int(feed_id), owner_uid, is_cat=cat_view)
