"""Article search and headline queries — search_to_sql, queryFeedHeadlines.

Source: ttrss/include/functions2.php
    search_to_sql      (lines 260-362)
    queryFeedHeadlines (lines 392-841) — ~200 lines, 16 parameters

Eliminated (R11): MySQL DATE_SUB/REGEXP branches — PostgreSQL INTERVAL used.
Eliminated (R13): Sphinx search, PHP debug printing.
Adapted: search_to_sql returns SQLAlchemy clauses instead of SQL strings.
Adapted: queryFeedHeadlines returns QueryHeadlinesResult (list subclass with search_words attribute)
         instead of PHP 6-tuple.  Callers that iterate or compare against list continue to work.
"""
from __future__ import annotations

import logging
import shlex
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, false, func, not_, or_, select, true
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from ttrss.ccache import _pref_int
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2, TtRssUserLabel2
from ttrss.models.tag import TtRssTag
from ttrss.models.user_entry import TtRssUserEntry
from ttrss.utils.feeds import LABEL_BASE_INDEX, feed_to_label_id

logger = logging.getLogger(__name__)


class QueryHeadlinesResult(list):
    """list subclass returned by queryFeedHeadlines.

    Source: ttrss/include/functions2.php:queryFeedHeadlines line 827
    PHP returns array($result, $feed_title, $feed_site_url, $last_error, $last_updated, $search_words).
    Python: rows are the list body; search_words attached as an attribute.
    Inheriting list ensures isinstance(result, list) and equality comparisons remain compatible.
    """

    search_words: list[str]

    def __new__(cls, rows: list, search_words: list[str]) -> "QueryHeadlinesResult":
        obj = super().__new__(cls, rows)
        return obj

    def __init__(self, rows: list, search_words: list[str]) -> None:
        super().__init__(rows)
        self.search_words = search_words


# Default ORDER BY when no override is provided
_DEFAULT_ORDER = [
    TtRssUserEntry.score.desc(),
    TtRssEntry.date_entered.desc(),
    TtRssEntry.updated.desc(),
]


# ---------------------------------------------------------------------------
# search_to_sql
# ---------------------------------------------------------------------------


def search_to_sql(
    search: str,
) -> tuple[list[Any], list[str]]:
    """Parse a search query into SQLAlchemy clause elements and search words.

    Source: ttrss/include/functions2.php:search_to_sql (lines 260-362)
    Returns: (clause_list, search_words)
    clause_list should be AND-combined in the caller.
    search_words are plain text keywords (for highlighting).

    Adapted: shlex.split used instead of PHP str_getcsv with space separator.
    Eliminated: @date timezone conversion — UTC parse used directly.
    """
    clauses: list[Any] = []
    search_words: list[str] = []

    try:
        keywords = shlex.split(search)
    except ValueError:
        keywords = search.split()

    for k in keywords:
        negated = k.startswith("-")
        if negated:
            k = k[1:]
            if not k:
                continue

        parts = k.lower().split(":", 1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        def _like(col: Any, term: str) -> Any:
            return func.upper(col).like(f"%{term.upper()}%")

        def _ilike_both(term: str) -> Any:
            return or_(_like(TtRssEntry.title, term), _like(TtRssEntry.content, term))

        def _maybe_not(clause: Any) -> Any:
            return not_(clause) if negated else clause

        if cmd == "title" and arg:
            clause = _like(TtRssEntry.title, arg)
            clauses.append(_maybe_not(clause))
        elif cmd == "author" and arg:
            clause = _like(TtRssEntry.author, arg)
            clauses.append(_maybe_not(clause))
        elif cmd == "note":
            if arg == "true":
                clause = and_(
                    TtRssUserEntry.note.isnot(None),
                    TtRssUserEntry.note != "",
                )
            elif arg == "false":
                clause = or_(
                    TtRssUserEntry.note.is_(None),
                    TtRssUserEntry.note == "",
                )
            elif arg:
                clause = _like(TtRssUserEntry.note, arg)
            else:
                clause = _ilike_both(k)
                if not negated:
                    search_words.append(k)
            clauses.append(_maybe_not(clause))
        elif cmd == "star":
            if arg == "true":
                clause = TtRssUserEntry.marked.is_(True)
            else:
                clause = TtRssUserEntry.marked.is_(False)
            clauses.append(_maybe_not(clause))
        elif cmd == "pub":
            if arg == "true":
                clause = TtRssUserEntry.published.is_(True)
            else:
                clause = TtRssUserEntry.published.is_(False)
            clauses.append(_maybe_not(clause))
        else:
            # @date shorthand — parse date from the keyword (strip @)
            if k.startswith("@"):
                date_str = k[1:]
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    clause = func.date(TtRssEntry.updated) == dt.date()
                    clauses.append(_maybe_not(clause))
                    continue
                except ValueError:
                    pass

            clause = _ilike_both(k)
            clauses.append(_maybe_not(clause))
            if not negated:
                search_words.append(k)

    return clauses, search_words


# ---------------------------------------------------------------------------
# queryFeedHeadlines
# ---------------------------------------------------------------------------


def queryFeedHeadlines(
    session: Session,
    feed: int | str,
    limit: int,
    view_mode: str,
    cat_view: bool,
    search: str = "",
    search_mode: str = "",
    override_order: Optional[str] = None,
    offset: int = 0,
    owner_uid: int = 0,
    filter_: Optional[Any] = None,
    since_id: int = 0,
    include_children: bool = False,
    ignore_vfeed_group: bool = False,
    override_strategy: Optional[Any] = None,
    override_vfeed: bool = False,
    start_ts: Optional[str] = None,
) -> "QueryHeadlinesResult":
    """Return headline rows for a feed, category, virtual feed, label, or tag.

    Source: ttrss/include/functions2.php:queryFeedHeadlines (lines 392-841)
    Eliminated: Sphinx search, PHP debug printing, MySQL DATE_SUB (R11).
    Adapted: returns list[Row] (SQLAlchemy NamedTuples).

    Parameters mirror the PHP function signature.
    """
    from ttrss.articles.filters import filter_to_sql
    from ttrss.feeds.categories import getChildCategories
    from ttrss.feeds.counters import _feed_unread, getCategoryChildrenUnread

    is_numeric_feed = isinstance(feed, int) or str(feed).lstrip("-").isdigit()
    nfeed = int(feed) if is_numeric_feed else 0

    # -----------------------------------------------------------------------
    # Search clause
    # -----------------------------------------------------------------------
    search_clauses: list[Any] = []
    search_words: list[str] = []
    if search:
        # Source: functions2.php line 827 — $search_words returned for frontend highlighting
        search_clauses, search_words = search_to_sql(search)

    # -----------------------------------------------------------------------
    # Filter clause + date window (functions2.php:418-451)
    # -----------------------------------------------------------------------
    filter_clause: Optional[Any] = None
    if filter_ is not None:
        filter_clause = filter_to_sql(session, filter_, owner_uid)
        # 14-day recency window when filter is active (functions2.php:421)
        window_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        filter_window = TtRssEntry.updated > window_cutoff

    # -----------------------------------------------------------------------
    # since_id
    # -----------------------------------------------------------------------
    since_id_clause: Optional[Any] = None
    if since_id:
        since_id_clause = TtRssEntry.id > since_id

    # -----------------------------------------------------------------------
    # view_mode → additional WHERE
    # -----------------------------------------------------------------------
    view_clause: Optional[Any] = None

    if view_mode == "adaptive" and not search:
        if nfeed != -1:
            unread = _feed_unread(session, nfeed if not cat_view else 0, owner_uid)
            if cat_view and nfeed > 0 and include_children:
                unread += getCategoryChildrenUnread(session, nfeed, owner_uid)
            if unread > 0:
                view_clause = TtRssUserEntry.unread.is_(True)
    elif view_mode == "marked":
        view_clause = TtRssUserEntry.marked.is_(True)
    elif view_mode == "has_note":
        view_clause = and_(
            TtRssUserEntry.note.isnot(None),
            TtRssUserEntry.note != "",
        )
    elif view_mode == "published":
        view_clause = TtRssUserEntry.published.is_(True)
    elif view_mode == "unread" and nfeed != -6:
        view_clause = TtRssUserEntry.unread.is_(True)

    # -----------------------------------------------------------------------
    # start_ts filter
    # -----------------------------------------------------------------------
    start_ts_clause: Optional[Any] = None
    if start_ts:
        try:
            ts = datetime.fromisoformat(start_ts)
            start_ts_clause = TtRssEntry.date_entered >= ts
        except ValueError:
            pass

    # -----------------------------------------------------------------------
    # Query strategy: determine JOIN type, strategy clause, extra tables
    # -----------------------------------------------------------------------
    allow_archived = False
    include_feed_title = override_vfeed  # whether to include feed title in SELECT
    strategy_clause: Any = true()
    needs_label_join = False
    extra_order_cols: list[Any] = []

    if search and search_mode == "all_feeds":
        strategy_clause = true()
        include_feed_title = True
    elif not is_numeric_feed:
        # Tag feed
        strategy_clause = true()
        include_feed_title = True
    elif search and search_mode == "this_cat":
        include_feed_title = True
        if nfeed > 0:
            if include_children:
                subcats = getChildCategories(session, nfeed, owner_uid)
                subcats.append(nfeed)
                strategy_clause = TtRssFeed.cat_id.in_(subcats)
            else:
                strategy_clause = TtRssFeed.cat_id == nfeed
        else:
            strategy_clause = TtRssFeed.cat_id.is_(None)
    elif nfeed > 0:
        if cat_view:
            include_feed_title = True
            if include_children:
                subcats = getChildCategories(session, nfeed, owner_uid)
                subcats.append(nfeed)
                strategy_clause = TtRssFeed.cat_id.in_(subcats)
            else:
                strategy_clause = TtRssFeed.cat_id == nfeed
        else:
            strategy_clause = TtRssUserEntry.feed_id == nfeed
    elif nfeed == 0 and not cat_view:
        # Archive virtual feed
        strategy_clause = TtRssUserEntry.feed_id.is_(None)
        allow_archived = True
    elif nfeed == 0 and cat_view:
        # Uncategorized
        strategy_clause = and_(
            TtRssFeed.cat_id.is_(None),
            TtRssUserEntry.feed_id.isnot(None),
        )
        include_feed_title = True
    elif nfeed == -1:
        # Starred
        strategy_clause = TtRssUserEntry.marked.is_(True)
        include_feed_title = True
        allow_archived = True
        if not override_order:
            extra_order_cols = [
                TtRssUserEntry.last_marked.desc(),
                TtRssEntry.date_entered.desc(),
                TtRssEntry.updated.desc(),
            ]
    elif nfeed == -2 and not cat_view:
        # Published
        strategy_clause = TtRssUserEntry.published.is_(True)
        include_feed_title = True
        allow_archived = True
        if not override_order:
            extra_order_cols = [
                TtRssUserEntry.last_published.desc(),
                TtRssEntry.date_entered.desc(),
                TtRssEntry.updated.desc(),
            ]
    elif nfeed == -2 and cat_view:
        # Labels category
        strategy_clause = and_(
            TtRssLabel2.id == TtRssUserLabel2.label_id,
            TtRssUserLabel2.article_id == TtRssUserEntry.ref_id,
        )
        include_feed_title = True
        needs_label_join = True
    elif nfeed == -6:
        # Recently read
        strategy_clause = and_(
            TtRssUserEntry.unread.is_(False),
            TtRssUserEntry.last_read.isnot(None),
        )
        include_feed_title = True
        allow_archived = True
        ignore_vfeed_group = True
        if not override_order:
            extra_order_cols = [TtRssUserEntry.last_read.desc()]
    elif nfeed == -3:
        # Fresh
        intl = _pref_int(session, "FRESH_ARTICLE_MAX_AGE", owner_uid, default=12)
        fresh_cutoff = datetime.now(timezone.utc) - timedelta(hours=intl)
        strategy_clause = and_(
            TtRssUserEntry.unread.is_(True),
            TtRssUserEntry.score >= 0,
            TtRssEntry.date_entered > fresh_cutoff,
        )
        include_feed_title = True
    elif nfeed == -4:
        # All articles
        strategy_clause = true()
        include_feed_title = True
        allow_archived = True
    elif nfeed < LABEL_BASE_INDEX:
        # Source: ttrss/include/functions.php:catchup_feed line 1213 — strict less-than (not <=)
        # Label virtual feed
        label_id = feed_to_label_id(nfeed)
        strategy_clause = and_(
            TtRssLabel2.id == label_id,
            TtRssLabel2.id == TtRssUserLabel2.label_id,
            TtRssUserLabel2.article_id == TtRssUserEntry.ref_id,
        )
        include_feed_title = True
        needs_label_join = True
        allow_archived = True
    else:
        strategy_clause = true()

    # Override strategy from caller
    if override_strategy is not None:
        strategy_clause = override_strategy

    # -----------------------------------------------------------------------
    # ORDER BY
    # -----------------------------------------------------------------------
    if override_order:
        # Parse simple column name override — use sa_text for raw SQL column spec
        order_clauses = [sa_text(override_order)]
    elif extra_order_cols:
        order_clauses = extra_order_cols
    else:
        order_clauses = _DEFAULT_ORDER[:]

    if view_mode == "unread_first" and not override_order:
        order_clauses = [TtRssUserEntry.unread.desc()] + order_clauses

    # Source: ttrss/include/functions2.php lines 689-695 — VFEED_GROUP_BY_FEED:
    # When viewing a virtual/multi-feed and pref is set, prepend feed title to ORDER BY.
    if include_feed_title and not ignore_vfeed_group:
        try:
            from ttrss.prefs.ops import get_user_pref as _gup
            _vfg = _gup(owner_uid, "VFEED_GROUP_BY_FEED") or "false"
            if _vfg.lower() not in {"false", "0", ""}:
                # Prepend feed title to order_clauses (override_order or default)
                order_clauses = [TtRssFeed.title] + order_clauses
        except Exception:
            pass  # No app context (e.g., unit tests) — skip pref lookup

    # -----------------------------------------------------------------------
    # SELECT columns
    # -----------------------------------------------------------------------
    select_cols = [
        TtRssEntry.date_entered,
        TtRssEntry.guid,
        TtRssEntry.id,
        TtRssEntry.title,
        TtRssEntry.updated,
        TtRssUserEntry.label_cache,
        TtRssUserEntry.tag_cache,
        TtRssFeed.always_display_enclosures,
        TtRssFeed.site_url,
        TtRssUserEntry.note,
        TtRssEntry.num_comments,
        TtRssEntry.comments,
        TtRssUserEntry.int_id,
        TtRssUserEntry.uuid,
        TtRssEntry.lang,
        TtRssFeed.hide_images,
        TtRssUserEntry.unread,
        TtRssUserEntry.feed_id,
        TtRssUserEntry.marked,
        TtRssUserEntry.published,
        TtRssEntry.link,
        TtRssUserEntry.last_read,
        TtRssUserEntry.orig_feed_id,
        TtRssUserEntry.last_marked,
        TtRssUserEntry.last_published,
        TtRssEntry.content,
        TtRssEntry.author,
        TtRssUserEntry.score,
    ]

    if include_feed_title:
        select_cols.append(TtRssFeed.title.label("feed_title"))
        # Source: functions2.php lines 706-707 — favicon_avg_color added when vfeed_query_part set
        select_cols.append(TtRssFeed.favicon_avg_color)

    # -----------------------------------------------------------------------
    # Build FROM / JOIN
    # -----------------------------------------------------------------------
    if is_numeric_feed:
        stmt = select(*select_cols).distinct().select_from(TtRssEntry)
        stmt = stmt.join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)

        if allow_archived:
            # LEFT OUTER JOIN feeds — archived articles may have no feed
            stmt = stmt.outerjoin(TtRssFeed, TtRssFeed.id == TtRssUserEntry.feed_id)
        else:
            # INNER JOIN feeds — only articles in a feed
            stmt = stmt.join(TtRssFeed, TtRssFeed.id == TtRssUserEntry.feed_id)

        if needs_label_join:
            stmt = stmt.join(
                TtRssUserLabel2, TtRssUserLabel2.article_id == TtRssUserEntry.ref_id
            ).join(TtRssLabel2, TtRssLabel2.id == TtRssUserLabel2.label_id)

    else:
        # Tag feed: join via TtRssTag
        all_tags = str(feed).split(",")
        stmt = select(*select_cols).distinct().select_from(TtRssEntry)
        stmt = stmt.join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        stmt = stmt.outerjoin(TtRssFeed, TtRssFeed.id == TtRssUserEntry.feed_id)

        if search_mode == "any":
            # Source: functions2.php:796-800 — "any" mode: single IN across all tags
            # owner_uid filter on TtRssTag prevents cross-user tag matches (functions2.php:803)
            stmt = stmt.join(
                TtRssTag,
                and_(
                    TtRssTag.post_int_id == TtRssUserEntry.int_id,
                    TtRssTag.owner_uid == owner_uid,
                ),
            )
            stmt = stmt.where(TtRssTag.tag_name.in_(all_tags))
        else:
            # Source: functions2.php:801-818 — "all" (default) mode:
            # each tag in the list must be present — correlated EXISTS per tag.
            # owner_uid scopes each EXISTS to the current user's tags.
            for tag in all_tags:
                tag_sq = (
                    select(TtRssTag.post_int_id)
                    .where(TtRssTag.tag_name == tag)
                    .where(TtRssTag.owner_uid == owner_uid)
                    .where(TtRssTag.post_int_id == TtRssUserEntry.int_id)
                    .correlate(TtRssUserEntry)
                )
                stmt = stmt.where(tag_sq.exists())

    # -----------------------------------------------------------------------
    # Apply WHERE clauses
    # -----------------------------------------------------------------------
    stmt = stmt.where(TtRssUserEntry.owner_uid == owner_uid)
    stmt = stmt.where(strategy_clause)

    if search_clauses:
        stmt = stmt.where(and_(*search_clauses))

    if since_id_clause is not None:
        stmt = stmt.where(since_id_clause)

    if filter_clause is not None:
        stmt = stmt.where(filter_clause)
        stmt = stmt.where(filter_window)

    if view_clause is not None:
        stmt = stmt.where(view_clause)

    if start_ts_clause is not None:
        stmt = stmt.where(start_ts_clause)

    # -----------------------------------------------------------------------
    # ORDER BY, LIMIT, OFFSET
    # -----------------------------------------------------------------------
    stmt = stmt.order_by(*order_clauses)

    if limit > 0:
        stmt = stmt.limit(limit).offset(offset)

    # Source: ttrss/include/functions2.php:queryFeedHeadlines — HOOK_QUERY_HEADLINES
    # Source: ttrss/classes/feeds.php:298 — get_hooks(PluginHost::HOOK_QUERY_HEADLINES)
    # Fires after query construction, before execution. Plugins may modify the result set.
    from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.
    pm = get_plugin_manager()
    qfh_ret = {
        "stmt": stmt, "feed": feed, "limit": limit, "view_mode": view_mode,
        "cat_view": cat_view, "search": search, "search_mode": search_mode,
        "override_order": override_order, "offset": offset, "owner_uid": owner_uid,
        "filter": filter_, "since_id": since_id, "include_children": include_children,
    }
    pm.hook.hook_query_headlines(
        qfh_ret=qfh_ret, feed=feed, limit=limit, view_mode=view_mode,
        cat_view=cat_view, search=search, search_mode=search_mode,
        override_order=override_order, offset=offset, owner_uid=owner_uid,
        filter_results=filter_, since_id=since_id, include_children=include_children,
    )
    stmt = qfh_ret.get("stmt", stmt)

    # Source: functions2.php line 827 — return array($result, $feed_title, $feed_site_url,
    #   $last_error, $last_updated, $search_words). Python: rows are the list, search_words
    #   attached as QueryHeadlinesResult.search_words attribute.
    rows = list(session.execute(stmt).all())
    return QueryHeadlinesResult(rows, search_words)
