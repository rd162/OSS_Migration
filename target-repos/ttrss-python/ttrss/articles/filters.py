"""Article filter loading, matching, scoring, and SQL generation.

Source: ttrss/include/functions2.php
    load_filters        (lines 1491-1563)
    filter_to_sql       (lines 2082-2165)

        ttrss/include/rssfuncs.php
    get_article_filters (lines 1272-1348)
    calculate_article_score (lines 1370-1379)
    find_article_filter (lines 1350-1357)
    find_article_filters (lines 1359-1368)

Eliminated (R11): MySQL REGEXP branch — PostgreSQL ~ operator used.
Adapted: filter_to_sql returns SQLAlchemy clause element instead of SQL string.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from sqlalchemy import and_, func, not_, or_, select, true
from sqlalchemy.orm import Session

from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.filter import TtRssFilter2, TtRssFilter2Action, TtRssFilter2Rule
from ttrss.models.user_entry import TtRssUserEntry

logger = logging.getLogger(__name__)

# Type alias for a filter dict as returned by load_filters
FilterDict = dict[str, Any]


# ---------------------------------------------------------------------------
# load_filters
# ---------------------------------------------------------------------------


def load_filters(
    session: Session,
    feed_id: int,
    owner_uid: int,
    action_id: Optional[int] = None,
) -> list[FilterDict]:
    """Load all enabled filters applicable to a feed, with rules and actions.

    Source: ttrss/include/functions2.php:load_filters (lines 1491-1563)
    Each returned filter dict has keys: match_any_rule, inverse, rules, actions.
    Rules: [{reg_exp, type, inverse}]
    Actions: [{type, param}]
    """
    from ttrss.feeds.categories import getParentCategories
    from ttrss.models.category import TtRssFeedCategory
    from ttrss.models.filter import TtRssFilterAction, TtRssFilterType

    # Get cat_id for this feed
    cat_id_row = session.execute(
        select(TtRssFeed.cat_id).where(TtRssFeed.id == feed_id)
    ).scalar_one_or_none()
    cat_id = cat_id_row if cat_id_row is not None else 0

    # Build category scope: current cat + all parents
    parent_cats = getParentCategories(session, cat_id, owner_uid)
    check_cats = parent_cats + [cat_id]

    # Load enabled filters ordered by order_id, title
    filter_rows = session.execute(
        select(
            TtRssFilter2.id,
            TtRssFilter2.match_any_rule,
            TtRssFilter2.inverse,
        )
        .where(TtRssFilter2.owner_uid == owner_uid)
        .where(TtRssFilter2.enabled.is_(True))
        .order_by(TtRssFilter2.order_id, TtRssFilter2.title)
    ).all()

    filters: list[FilterDict] = []

    for f_row in filter_rows:
        filter_id = f_row.id

        # Build rule scope condition
        # Source: functions2.php:1516
        # (cat_id IS NULL AND cat_filter = false) OR cat_id IN (check_cats)
        # With null_cat_qpart added when current feed has no category (cat_id=0)
        base_cat_cond = and_(
            TtRssFilter2Rule.cat_id.is_(None),
            TtRssFilter2Rule.cat_filter.is_(False),
        )
        if cat_id == 0:
            # Feed has no category — also match rules that have cat_id IS NULL (regardless of cat_filter)
            cat_cond = TtRssFilter2Rule.cat_id.is_(None)
        else:
            cat_cond = or_(
                base_cat_cond,
                TtRssFilter2Rule.cat_id.in_(check_cats),
            )

        feed_cond = or_(
            TtRssFilter2Rule.feed_id.is_(None),
            TtRssFilter2Rule.feed_id == feed_id,
        )

        rule_rows = session.execute(
            select(
                TtRssFilter2Rule.reg_exp,
                TtRssFilter2Rule.inverse,
                TtRssFilterType.name.label("type_name"),
            )
            .join(TtRssFilterType, TtRssFilterType.id == TtRssFilter2Rule.filter_type)
            .where(TtRssFilter2Rule.filter_id == filter_id)
            .where(cat_cond)
            .where(feed_cond)
        ).all()

        rules = [
            {
                "reg_exp": r.reg_exp,
                "type": r.type_name,
                "inverse": bool(r.inverse),
            }
            for r in rule_rows
        ]

        action_q = (
            select(
                TtRssFilter2Action.action_param,
                TtRssFilterAction.name.label("type_name"),
            )
            .join(TtRssFilterAction, TtRssFilterAction.id == TtRssFilter2Action.action_id)
            .where(TtRssFilter2Action.filter_id == filter_id)
        )
        if action_id is not None:
            action_q = action_q.where(TtRssFilter2Action.action_id == action_id)

        action_rows = session.execute(action_q).all()

        actions = [
            {"type": a.type_name, "param": a.action_param}
            for a in action_rows
        ]

        if rules and actions:
            filters.append(
                {
                    "match_any_rule": bool(f_row.match_any_rule),
                    "inverse": bool(f_row.inverse),
                    "rules": rules,
                    "actions": actions,
                }
            )

    return filters


# ---------------------------------------------------------------------------
# get_article_filters — pure Python regex matching
# ---------------------------------------------------------------------------


def get_article_filters(
    filters: list[FilterDict],
    title: str,
    content: str,
    link: str,
    timestamp: Any,
    author: str,
    tags: list[str],
) -> list[dict[str, Any]]:
    """Apply filter list to an article; return list of matching action dicts.

    Source: ttrss/include/rssfuncs.php:get_article_filters (lines 1272-1348)
    Adapted: uses Python re.search with IGNORECASE instead of PHP preg_match.
    Stops processing after first 'stop' action (matching PHP behaviour).
    """
    matches: list[dict[str, Any]] = []

    # Strip newlines from content for matching (matches PHP's preg_replace)
    content_flat = re.sub(r"[\r\n\t]", "", content)

    for f in filters:
        match_any = f.get("match_any_rule", False)
        f_inverse = f.get("inverse", False)
        filter_match = False

        for rule in f.get("rules", []):
            reg_exp = rule.get("reg_exp", "")
            if not reg_exp:
                continue

            # PHP escapes '/' in the pattern; Python re doesn't need this
            rule_type = rule.get("type", "")
            rule_inverse = rule.get("inverse", False)

            try:
                match = False
                if rule_type == "title":
                    match = bool(re.search(reg_exp, title, re.IGNORECASE))
                elif rule_type == "content":
                    match = bool(re.search(reg_exp, content_flat, re.IGNORECASE))
                elif rule_type == "both":
                    match = bool(
                        re.search(reg_exp, title, re.IGNORECASE)
                        or re.search(reg_exp, content_flat, re.IGNORECASE)
                    )
                elif rule_type == "link":
                    match = bool(re.search(reg_exp, link, re.IGNORECASE))
                elif rule_type == "author":
                    match = bool(re.search(reg_exp, author, re.IGNORECASE))
                elif rule_type == "tag":
                    match = any(
                        re.search(reg_exp, tag, re.IGNORECASE) for tag in tags
                    )
            except re.error:
                # Invalid regex — skip rule (matches PHP @preg_match silent error)
                continue

            if rule_inverse:
                match = not match

            if match_any:
                if match:
                    filter_match = True
                    break
            else:
                filter_match = match
                if not match:
                    break

        if f_inverse:
            filter_match = not filter_match

        if filter_match:
            for action in f.get("actions", []):
                matches.append(action)
                if action.get("type") == "stop":
                    return matches

    return matches


# ---------------------------------------------------------------------------
# Helper: find actions by type
# ---------------------------------------------------------------------------


def find_article_filter(
    filters: list[dict[str, Any]], filter_name: str
) -> Optional[dict[str, Any]]:
    """Return first matching action dict by type name, or None.

    Source: ttrss/include/rssfuncs.php:find_article_filter (lines 1350-1357)
    """
    for f in filters:
        if f.get("type") == filter_name:
            return f
    return None


def find_article_filters(
    filters: list[dict[str, Any]], filter_name: str
) -> list[dict[str, Any]]:
    """Return all action dicts matching the given type name.

    Source: ttrss/include/rssfuncs.php:find_article_filters (lines 1359-1368)
    """
    return [f for f in filters if f.get("type") == filter_name]


# ---------------------------------------------------------------------------
# calculate_article_score
# ---------------------------------------------------------------------------


def calculate_article_score(filters: list[dict[str, Any]]) -> int:
    """Sum all 'score' action params from matched filters.

    Source: ttrss/include/rssfuncs.php:calculate_article_score (lines 1370-1379)
    """
    total = 0
    for f in filters:
        if f.get("type") == "score":
            try:
                total += int(f.get("param", 0))
            except (TypeError, ValueError):
                pass
    return total


# ---------------------------------------------------------------------------
# filter_to_sql — SQLAlchemy expression generator
# ---------------------------------------------------------------------------


def filter_to_sql(
    session: Session,
    filter_: FilterDict,
    owner_uid: int,
) -> Any:
    """Return a SQLAlchemy clause element for a filter dict.

    Source: ttrss/include/functions2.php:filter_to_sql (lines 2082-2165)
    Adapted: returns SQLAlchemy expression instead of raw SQL string.
    PostgreSQL `~*` (case-insensitive POSIX regex) used instead of PHP LOWER ~ LOWER.
    Eliminated: MySQL REGEXP branch (R11).
    """
    from ttrss.feeds.categories import getChildCategories

    rule_clauses = []

    for rule in filter_.get("rules", []):
        reg_exp = rule.get("reg_exp", "")
        if not reg_exp:
            continue

        # Validate regex
        try:
            re.compile(reg_exp)
        except re.error:
            continue

        rule_type = rule.get("type", "")

        # PostgreSQL ~* is case-insensitive POSIX regex (equivalent to PHP LOWER ~ LOWER)
        if rule_type == "title":
            qpart = TtRssEntry.title.op("~*")(reg_exp)
        elif rule_type == "content":
            qpart = TtRssEntry.content.op("~*")(reg_exp)
        elif rule_type == "both":
            qpart = or_(
                TtRssEntry.title.op("~*")(reg_exp),
                TtRssEntry.content.op("~*")(reg_exp),
            )
        elif rule_type == "tag":
            qpart = TtRssUserEntry.tag_cache.op("~*")(reg_exp)
        elif rule_type == "link":
            qpart = TtRssEntry.link.op("~*")(reg_exp)
        elif rule_type == "author":
            qpart = TtRssEntry.author.op("~*")(reg_exp)
        else:
            continue

        if rule.get("inverse"):
            qpart = not_(qpart)

        # Rule-level feed scope
        rule_feed_id = rule.get("feed_id")
        if rule_feed_id and int(rule_feed_id) > 0:
            qpart = and_(qpart, TtRssUserEntry.feed_id == int(rule_feed_id))

        # Rule-level category scope
        rule_cat_id = rule.get("cat_id")
        if rule_cat_id is not None:
            if int(rule_cat_id) > 0:
                children = getChildCategories(session, int(rule_cat_id), owner_uid)
                children.append(int(rule_cat_id))
                qpart = and_(qpart, TtRssFeed.cat_id.in_(children))
            else:
                qpart = and_(qpart, TtRssFeed.cat_id.is_(None))

        # Only applies to entries with a feed (not archived)
        qpart = and_(qpart, TtRssUserEntry.feed_id.isnot(None))

        rule_clauses.append(qpart)

    if not rule_clauses:
        return false_clause()

    match_any = filter_.get("match_any_rule", False)
    full_clause = or_(*rule_clauses) if match_any else and_(*rule_clauses)

    if filter_.get("inverse"):
        full_clause = not_(full_clause)

    return full_clause


def false_clause() -> Any:
    """Return a SQLAlchemy expression that is always false."""
    from sqlalchemy import literal
    return literal(False)
