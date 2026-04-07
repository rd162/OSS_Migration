"""Article tag CRUD — get_article_tags, setArticleTags, tag_is_valid, sanitize_tag.

Source: ttrss/include/functions2.php
    get_article_tags  (lines 1055-1099)
    tag_is_valid      (lines 1107-1115)
    sanitize_tag      (lines 1101-1105)
    (setArticleTags — from classes/article.php:Article::editArticleTags)

Eliminated (R13): format_tags_string — HTML output.
Adapted: tag_cache uses comma-separated string (no change from PHP).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import delete as sa_delete
from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import Session

from ttrss.models.tag import TtRssTag
from ttrss.models.user_entry import TtRssUserEntry

logger = logging.getLogger(__name__)

_MAX_TAG_LENGTH = 250


def sanitize_tag(tag: str) -> str:
    """Lowercase and strip whitespace from a tag, mirroring PHP sanitize_tag.

    # Source: ttrss/include/functions2.php:sanitize_tag (lines 1101-1105)
    PHP: strtolower(trim($tag)) — Python equivalent below.
    """
    return tag.strip().lower()


def tag_is_valid(tag: str) -> bool:
    """Return True if the tag name is non-empty, non-numeric, and within length.

    Source: ttrss/include/functions2.php:tag_is_valid (lines 1107-1115)
    """
    if not tag or not tag.strip():
        return False
    if tag.isdigit():
        return False
    if len(tag) > _MAX_TAG_LENGTH:
        return False
    return True


def get_article_tags(
    session: Session,
    article_id: int,
    owner_uid: int,
    tag_cache: Optional[str] = None,
) -> list[str]:
    """Return tag list for an article, using tag_cache if available.

    Source: ttrss/include/functions2.php:get_article_tags (lines 1055-1099)
    Cache hit: split tag_cache on comma and return.
    Cache miss: JOIN ttrss_tags via ttrss_user_entries.int_id, then write back cache.
    """
    # If caller didn't pass tag_cache, load it from the DB.
    if tag_cache is None:
        tag_cache = session.execute(
            select(TtRssUserEntry.tag_cache)
            .where(TtRssUserEntry.ref_id == article_id)
            .where(TtRssUserEntry.owner_uid == owner_uid)
        ).scalar_one_or_none()

    # Cache hit — return split list (filter empty strings from trailing commas)
    if tag_cache:
        return [t for t in tag_cache.split(",") if t]

    # Cache miss — query ttrss_tags via int_id subquery
    int_id_subq = (
        select(TtRssUserEntry.int_id)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .limit(1)
        .scalar_subquery()
    )
    tag_rows = session.execute(
        select(TtRssTag.tag_name)
        .where(TtRssTag.post_int_id == int_id_subq)
        .order_by(TtRssTag.tag_name)
        .distinct()
    ).scalars().all()
    tags = list(tag_rows)

    # Write back to cache
    tags_str = ",".join(tags)
    session.execute(
        sa_update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .values(tag_cache=tags_str)
    )

    return tags


def setArticleTags(
    session: Session,
    article_id: int,
    owner_uid: int,
    tags: list[str],
) -> None:
    """Replace all tags for an article and update the tag_cache.

    Source: ttrss/classes/article.php:Article::setArticleTags (lines 222-284)
    Source: ttrss/classes/article.php:Article::editArticleTags (tag write path)
    Validates each tag via tag_is_valid before inserting.
    """
    # Resolve int_id for this user/article
    int_id = session.execute(
        select(TtRssUserEntry.int_id)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .limit(1)
    ).scalar_one_or_none()

    if int_id is None:
        return

    # Delete existing tags
    session.execute(
        sa_delete(TtRssTag)
        .where(TtRssTag.post_int_id == int_id)
        .where(TtRssTag.owner_uid == owner_uid)
    )

    # Source: ttrss/classes/article.php:227 — array_unique(trim_array(explode(...))) deduplicates tags
    # sanitize_tag (strtolower+trim) applied to each tag before validation (functions2.php:1101-1105)
    # Python must also deduplicate to avoid inserting duplicate rows into ttrss_tags.
    seen_tags: set[str] = set()
    valid_tags = []
    for t in tags:
        ts = sanitize_tag(t)
        if tag_is_valid(ts) and ts not in seen_tags:
            valid_tags.append(ts)
            seen_tags.add(ts)
    for tag in valid_tags:
        session.add(TtRssTag(tag_name=tag, owner_uid=owner_uid, post_int_id=int_id))

    # Flush all tag inserts to database before updating cache
    # (session.add() marks as pending; flush() ensures they're written to DB)
    session.flush()

    # Source: ttrss/classes/article.php:265 — sort($tags_to_cache) before cache write
    # PHP sorts tag array alphabetically before joining; Python must match to keep cache consistent.
    valid_tags.sort()

    # Update cache
    session.execute(
        sa_update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == article_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .values(tag_cache=",".join(valid_tags))
    )
    session.flush()
