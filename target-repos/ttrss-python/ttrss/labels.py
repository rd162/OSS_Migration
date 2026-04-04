"""Label management — per-user article label CRUD and label_cache maintenance.

Source: ttrss/include/labels.php (201 lines, 10 functions)
"""
from __future__ import annotations

import json
from typing import Any, Union

from sqlalchemy import delete as sa_delete
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ttrss.models.access_key import TtRssAccessKey
from ttrss.models.label import TtRssLabel2, TtRssUserLabel2
from ttrss.models.user_entry import TtRssUserEntry
from ttrss.utils.feeds import label_to_feed_id


def label_find_id(session: Session, caption: str, owner_uid: int) -> int:
    """Return label database ID for the given caption, or 0 if not found.
    Source: ttrss/include/labels.php:label_find_id (lines 2-12)
    """
    row = session.execute(
        select(TtRssLabel2.id)
        .where(TtRssLabel2.caption == caption)
        .where(TtRssLabel2.owner_uid == owner_uid)
        .limit(1)
    ).scalar_one_or_none()
    return row or 0


def label_find_caption(session: Session, label_id: int, owner_uid: int) -> str:
    """Return label caption for the given label ID, or empty string if not found.
    Source: ttrss/include/labels.php:label_find_caption (lines 60-70)
    """
    row = session.execute(
        select(TtRssLabel2.caption)
        .where(TtRssLabel2.id == label_id)
        .where(TtRssLabel2.owner_uid == owner_uid)
        .limit(1)
    ).scalar_one_or_none()
    return row or ""


def get_all_labels(session: Session, owner_uid: int) -> list[dict[str, Any]]:
    """Return all labels for a user as list of dicts.
    Source: ttrss/include/labels.php:get_all_labels (lines 72-82)
    """
    rows = session.execute(
        select(TtRssLabel2.fg_color, TtRssLabel2.bg_color, TtRssLabel2.caption)
        .where(TtRssLabel2.owner_uid == owner_uid)
    ).all()
    return [
        {"fg_color": r.fg_color, "bg_color": r.bg_color, "caption": r.caption}
        for r in rows
    ]


def get_article_labels(session: Session, article_id: int, owner_uid: int) -> list:
    """Return label list for an article, reading from cache or DB with write-back.

    Returns list of [virtual_feed_id, caption, fg_color, bg_color] arrays,
    or empty list when the article has no labels.
    Cache sentinel {"no-labels": 1} is stored when confirmed empty.

    Source: ttrss/include/labels.php:get_article_labels (lines 14-57)
    """
    # Try label_cache first.
    # Source: labels.php:19-33
    cached_str = session.execute(
        select(TtRssUserEntry.label_cache)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    ).scalar_one_or_none()

    if cached_str:
        try:
            cached = json.loads(cached_str)
        except (json.JSONDecodeError, ValueError):
            cached = None

        if cached is not None:
            if isinstance(cached, dict) and cached.get("no-labels") == 1:
                return []
            if isinstance(cached, list):
                return cached

    # Cache miss: query normalized tables.
    # Source: labels.php:36-49
    label_rows = session.execute(
        select(
            TtRssLabel2.id.label("label_id"),
            TtRssLabel2.caption,
            TtRssLabel2.fg_color,
            TtRssLabel2.bg_color,
        )
        .distinct()
        .join(TtRssUserLabel2, TtRssUserLabel2.label_id == TtRssLabel2.id)
        .where(TtRssUserLabel2.article_id == article_id)
        .where(TtRssLabel2.owner_uid == owner_uid)
        .order_by(TtRssLabel2.caption)
    ).all()

    rv = [
        [label_to_feed_id(r.label_id), r.caption, r.fg_color, r.bg_color]
        for r in label_rows
    ]

    # Write result back to cache.
    # Source: labels.php:51-54
    if rv:
        label_update_cache(session, owner_uid, article_id, rv)
    else:
        label_update_cache(session, owner_uid, article_id, {"no-labels": 1})

    return rv


def label_update_cache(
    session: Session,
    owner_uid: int,
    article_id: int,
    labels: Union[list, dict, None] = None,
    force: bool = False,
) -> None:
    """Write label list to the label_cache column.

    Source: ttrss/include/labels.php:label_update_cache (lines 84-97)
    """
    if force:
        label_clear_cache(session, article_id)

    if labels is None:
        labels = get_article_labels(session, article_id, owner_uid)

    cache_str = json.dumps(labels)
    session.execute(
        update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .values(label_cache=cache_str)
    )


def label_clear_cache(session: Session, article_id: int) -> None:
    """Reset label_cache to empty string for all user entries on this article.

    Source: ttrss/include/labels.php:label_clear_cache (lines 99-103)
    Note: PHP sets label_cache = '' (empty string), NOT NULL. Column is NOT NULL.
    """
    session.execute(
        update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == article_id)
        .values(label_cache="")
    )


def label_remove_article(
    session: Session, article_id: int, caption: str, owner_uid: int
) -> None:
    """Remove a label assignment from an article.
    Source: ttrss/include/labels.php:label_remove_article (lines 106-119)
    """
    label_id = label_find_id(session, caption, owner_uid)
    if not label_id:
        return
    session.execute(
        sa_delete(TtRssUserLabel2)
        .where(TtRssUserLabel2.label_id == label_id)
        .where(TtRssUserLabel2.article_id == article_id)
    )
    label_clear_cache(session, article_id)


def label_add_article(
    session: Session, article_id: int, caption: str, owner_uid: int
) -> None:
    """Assign a label to an article (idempotent — no-op if already assigned).
    Source: ttrss/include/labels.php:label_add_article (lines 121-143)
    """
    label_id = label_find_id(session, caption, owner_uid)
    if not label_id:
        return

    existing = session.execute(
        select(TtRssUserLabel2.article_id)
        .join(TtRssLabel2, TtRssLabel2.id == TtRssUserLabel2.label_id)
        .where(TtRssUserLabel2.label_id == label_id)
        .where(TtRssUserLabel2.article_id == article_id)
        .where(TtRssLabel2.owner_uid == owner_uid)
        .limit(1)
    ).scalar_one_or_none()

    if existing is None:
        session.add(TtRssUserLabel2(label_id=label_id, article_id=article_id))

    label_clear_cache(session, article_id)


def label_remove(session: Session, label_id: int, owner_uid: int) -> None:
    """Delete a label and clean up access keys and label_cache entries.
    Source: ttrss/include/labels.php:label_remove (lines 145-175)
    """
    # Fetch caption before deletion for cache invalidation.
    # Source: labels.php:150-153
    caption = session.execute(
        select(TtRssLabel2.caption).where(TtRssLabel2.id == label_id)
    ).scalar_one_or_none()

    result = session.execute(
        sa_delete(TtRssLabel2)
        .where(TtRssLabel2.id == label_id)
        .where(TtRssLabel2.owner_uid == owner_uid)
        .returning(TtRssLabel2.id)
    )
    deleted = result.scalar_one_or_none()

    if deleted is not None and caption:
        # Remove access key for the label's virtual feed ID.
        # Source: labels.php:162-165
        ext_id = str(label_to_feed_id(label_id))
        session.execute(
            sa_delete(TtRssAccessKey)
            .where(TtRssAccessKey.feed_id == ext_id)
            .where(TtRssAccessKey.owner_uid == owner_uid)
        )

        # Invalidate label_cache for any user entry that may reference this label caption.
        # Source: labels.php:168-170
        session.execute(
            update(TtRssUserEntry)
            .where(TtRssUserEntry.owner_uid == owner_uid)
            .where(TtRssUserEntry.label_cache.like(f"%{caption}%"))
            .values(label_cache="")
        )


def label_create(
    session: Session,
    caption: str,
    fg_color: str = "",
    bg_color: str = "",
    owner_uid: int = 0,
) -> bool:
    """Create a label if it doesn't already exist; return True if created.
    Source: ttrss/include/labels.php:label_create (lines 177-199)
    """
    existing = session.execute(
        select(TtRssLabel2.id)
        .where(TtRssLabel2.caption == caption)
        .where(TtRssLabel2.owner_uid == owner_uid)
    ).scalar_one_or_none()

    if existing is not None:
        return False

    session.add(
        TtRssLabel2(
            caption=caption,
            owner_uid=owner_uid,
            fg_color=fg_color,
            bg_color=bg_color,
        )
    )
    return True
