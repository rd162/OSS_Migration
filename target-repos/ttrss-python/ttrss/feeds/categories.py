"""Feed category CRUD, hierarchy traversal, and title resolution.

Source: ttrss/include/functions.php  (getCategoryTitle, getFeedCatTitle, getFeedTitle, lines 1250-1997)
        ttrss/include/functions2.php (getParentCategories, getChildCategories, lines 364-390;
                                      get_feed_category, add_feed_category, lines 1634-1686;
                                      getArticleFeed, lines 1688-1697)

Eliminated (R13 / AR9): print_feed_cat_select(), print_feed_select() — server-rendered HTML.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ttrss.models.category import TtRssFeedCategory
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2
from ttrss.models.user_entry import TtRssUserEntry
from ttrss.utils.feeds import LABEL_BASE_INDEX, feed_to_label_id

# Depth guard for recursive category traversal — prevents infinite recursion on
# circular parent_cat references in the DB.
MAX_CATEGORY_DEPTH = 20


def getCategoryTitle(session: Session, cat_id: int, owner_uid: Optional[int] = None) -> str:
    """Return the display title for a category ID.

    Source: ttrss/include/functions.php:getCategoryTitle (lines 1250-1268)
    Note: PHP has no owner_uid parameter; owner_uid is optional here for consistency
    but is not used in the DB query (category IDs are globally unique).
    """
    if cat_id == -1:
        return "Special"
    if cat_id == -2:
        return "Labels"
    row = session.execute(
        select(TtRssFeedCategory.title).where(TtRssFeedCategory.id == cat_id)
    ).scalar_one_or_none()
    return row if row is not None else "Uncategorized"


def getFeedCatTitle(session: Session, feed_id: int) -> str:
    """Return the category title for a given feed ID.

    Source: ttrss/include/functions.php:getFeedCatTitle (lines 1911-1927)
    """
    if feed_id == -1:
        return "Special"
    if feed_id < LABEL_BASE_INDEX:
        return "Labels"
    if feed_id > 0:
        row = session.execute(
            select(TtRssFeedCategory.title)
            .join(TtRssFeed, TtRssFeed.cat_id == TtRssFeedCategory.id)
            .where(TtRssFeed.id == feed_id)
        ).scalar_one_or_none()
        return row if row is not None else "Uncategorized"
    return f"getFeedCatTitle({feed_id}) failed"


def getFeedTitle(
    session: Session, feed_id: int | str, cat: bool = False
) -> str:
    """Return display title for a feed ID (including virtual/label feeds).

    Source: ttrss/include/functions.php:getFeedTitle (lines 1964-1997)
    """
    if cat:
        return getCategoryTitle(session, int(feed_id))

    feed_id = int(feed_id) if str(feed_id).lstrip("-").isdigit() else feed_id

    if feed_id == -1:
        return "Starred articles"
    if feed_id == -2:
        return "Published articles"
    if feed_id == -3:
        return "Fresh articles"
    if feed_id == -4:
        return "All articles"
    if feed_id == 0 or feed_id == "0":
        return "Archived articles"
    if feed_id == -6:
        return "Recently read"
    if isinstance(feed_id, int) and feed_id < LABEL_BASE_INDEX:
        label_id = feed_to_label_id(feed_id)
        row = session.execute(
            select(TtRssLabel2.caption).where(TtRssLabel2.id == label_id)
        ).scalar_one_or_none()
        return row if row is not None else f"Unknown label ({label_id})"
    if isinstance(feed_id, int) and feed_id > 0:
        row = session.execute(
            select(TtRssFeed.title).where(TtRssFeed.id == feed_id)
        ).scalar_one_or_none()
        return row if row is not None else f"Unknown feed ({feed_id})"
    return str(feed_id)


def getArticleFeed(session: Session, article_id: int, owner_uid: int) -> int:
    """Return the feed_id for an article (by its entry ID).

    Source: ttrss/include/functions2.php:getArticleFeed (lines 1688-1697)
    """
    row = session.execute(
        select(TtRssUserEntry.feed_id)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    ).scalar_one_or_none()
    return row or 0


def get_feed_category(
    session: Session,
    cat_title: str,
    owner_uid: int,
    parent_cat_id: Optional[int] = None,
) -> Optional[int]:
    """Return the category ID for a given title and parent, or None if not found.

    Source: ttrss/include/functions2.php:get_feed_category (lines 1634-1651)
    """
    q = (
        select(TtRssFeedCategory.id)
        .where(TtRssFeedCategory.title == cat_title)
        .where(TtRssFeedCategory.owner_uid == owner_uid)
    )
    if parent_cat_id is not None:
        q = q.where(TtRssFeedCategory.parent_cat == parent_cat_id)
    else:
        q = q.where(TtRssFeedCategory.parent_cat.is_(None))
    return session.execute(q).scalar_one_or_none()


def add_feed_category(
    session: Session,
    cat_title: str,
    owner_uid: int,
    parent_cat_id: Optional[int] = None,
) -> bool:
    """Create a feed category if it doesn't exist; return True if created.

    Source: ttrss/include/functions2.php:add_feed_category (lines 1654-1686)
    """
    if not cat_title:
        return False

    cat_title = cat_title[:250]

    existing = get_feed_category(session, cat_title, owner_uid, parent_cat_id)
    if existing is not None:
        return False

    session.add(
        TtRssFeedCategory(
            owner_uid=owner_uid,
            title=cat_title,
            parent_cat=parent_cat_id,
        )
    )
    return True


def getParentCategories(
    session: Session,
    cat_id: int,
    owner_uid: int,
    _depth: int = 0,
) -> list[int]:
    """Return all ancestor category IDs for a category (recursive, depth-limited).

    Source: ttrss/include/functions2.php:getParentCategories (lines 364-376)
    Note: MAX_CATEGORY_DEPTH=20 guard added — PHP has no guard but relies on DB integrity.
    """
    if _depth >= MAX_CATEGORY_DEPTH:
        return []

    rows = session.execute(
        select(TtRssFeedCategory.parent_cat)
        .where(TtRssFeedCategory.id == cat_id)
        .where(TtRssFeedCategory.owner_uid == owner_uid)
        .where(TtRssFeedCategory.parent_cat.isnot(None))
    ).scalars().all()

    rv: list[int] = []
    for parent_id in rows:
        rv.append(parent_id)
        rv.extend(getParentCategories(session, parent_id, owner_uid, _depth + 1))
    return rv


def getChildCategories(
    session: Session,
    cat_id: int,
    owner_uid: int,
    _depth: int = 0,
) -> list[int]:
    """Return all descendant category IDs for a category (recursive, depth-limited).

    Source: ttrss/include/functions2.php:getChildCategories (lines 378-390)
    Note: cat_id=0 returns [] — PHP queries parent_cat='0' which never matches
    since top-level categories use parent_cat IS NULL, not parent_cat=0.
    Note: MAX_CATEGORY_DEPTH=20 guard added.
    """
    if _depth >= MAX_CATEGORY_DEPTH or cat_id == 0:
        return []

    child_ids = session.execute(
        select(TtRssFeedCategory.id)
        .where(TtRssFeedCategory.parent_cat == cat_id)
        .where(TtRssFeedCategory.owner_uid == owner_uid)
    ).scalars().all()

    rv: list[int] = []
    for child_id in child_ids:
        rv.append(child_id)
        rv.extend(getChildCategories(session, child_id, owner_uid, _depth + 1))
    return rv
