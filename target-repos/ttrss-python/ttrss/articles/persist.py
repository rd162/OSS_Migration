"""Article persistence helpers — GUID, content hash, upsert, filter actions.

Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 545-1117)
    GUID construction:    lines 550-621
    Content hash:         line 707
    Entry upsert:         lines 720-750, 923-970
    User entry INSERT:    lines 887-894
    Filter actions:       lines 812-828, 845-863
    Tag extraction:       lines 634-648, 1062-1097
    Label assignment:     lines 1102-1113
    Enclosures:           lines 982-1020
    N-gram dedup:         lines 867-882
    Content update:       lines 923-970

Eliminated (R13): $debug parameter — Python logging used.
Eliminated (R11): MySQL-specific MATCH() AGAINST() — PostgreSQL similarity() used.
Adapted: SQLAlchemy ORM; pg_insert().on_conflict_do_nothing() for GUID uniqueness.
"""
from __future__ import annotations

import hashlib
import logging
import uuid as _uuid_mod
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from ttrss.articles.tags import setArticleTags, tag_is_valid
from ttrss.models.enclosure import TtRssEnclosure
from ttrss.models.entry import TtRssEntry
from ttrss.models.user_entry import TtRssUserEntry

logger = logging.getLogger(__name__)

# N-gram dedup threshold — rssfuncs.php:_NGRAM_TITLE_DUPLICATE_THRESHOLD
_NGRAM_THRESHOLD = 0.5

# Filter action type names (from ttrss_filter_actions table)
_ACTION_CATCHUP = "catchup"
_ACTION_MARK = "mark"
_ACTION_TAG = "tag"
_ACTION_SCORE = "score"
_ACTION_LABEL = "label"
_ACTION_STOP = "stop"
_ACTION_PUBLISH = "publish"
_ACTION_PLUGIN = "plugin"


# ---------------------------------------------------------------------------
# GUID construction
# ---------------------------------------------------------------------------


def _make_guid_from_title(title: str) -> str:
    """Fallback GUID from article title hash.

    Source: ttrss/include/rssfuncs.php (lines 550-560)
    """
    return "SHA1:" + hashlib.sha1(title.encode("utf-8", errors="replace")).hexdigest()


def build_entry_guid(
    entry: Any,
    owner_uid: int,
) -> str:
    """Build a stable, owner-scoped, SHA1-prefixed GUID for a feedparser entry.

    Source: ttrss/include/rssfuncs.php (lines 550-621)
    Fallback chain: entry.id → entry.link → title hash.
    Owner-scoped: f"{owner_uid},{entry_guid}"
    SHA1-prefixed: "SHA1:" + sha1(scoped).hexdigest()
    Truncated to 245 chars.
    """
    raw_guid = (
        entry.get("id")
        or entry.get("link")
        or _make_guid_from_title(entry.get("title", ""))
    )
    scoped = f"{owner_uid},{raw_guid}"
    guid = "SHA1:" + hashlib.sha1(scoped.encode("utf-8", errors="replace")).hexdigest()
    return guid[:245]


# ---------------------------------------------------------------------------
# Content hash
# ---------------------------------------------------------------------------


def content_hash(content: str) -> str:
    """Return SHA1-prefixed hash of article content.

    Source: ttrss/include/rssfuncs.php line 707
    """
    return "SHA1:" + hashlib.sha1(content.encode("utf-8", errors="replace")).hexdigest()


# ---------------------------------------------------------------------------
# N-gram duplicate detection
# ---------------------------------------------------------------------------


def _is_ngram_duplicate(session: Session, title: str, owner_uid: int) -> bool:
    """Check for an existing article with similar title using PostgreSQL similarity().

    Source: ttrss/include/rssfuncs.php lines 867-882
    Requires pg_trgm extension (CREATE EXTENSION IF NOT EXISTS pg_trgm).
    Returns True if a similar article already exists.
    """
    if not title:
        return False
    try:
        result = session.execute(
            select(TtRssEntry.id)
            .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
            .where(TtRssUserEntry.owner_uid == owner_uid)
            .where(func.similarity(TtRssEntry.title, title) > _NGRAM_THRESHOLD)
            .limit(1)
        ).scalar_one_or_none()
        return result is not None
    except Exception:
        # pg_trgm not installed or query failed — skip dedup silently
        return False


# ---------------------------------------------------------------------------
# Filter action processing
# ---------------------------------------------------------------------------


def apply_filter_actions(
    session: Session,
    article_id: int,
    owner_uid: int,
    feed_id: int,
    matched_actions: list[dict[str, Any]],
    tag_list: list[str],
) -> dict[str, Any]:
    """Apply filter action dicts to a newly inserted article.

    Source: ttrss/include/rssfuncs.php lines 812-828, 845-863
    Returns updated state dict: {unread, marked, published, score, tags}.
    """
    from ttrss.labels import label_add_article

    unread = True
    marked = False
    published = False
    score = 0

    for action in matched_actions:
        action_type = action.get("type", "")
        param = action.get("param", "")

        if action_type == _ACTION_CATCHUP:
            # Source: rssfuncs.php line 815 — if ($type == "catchup") unread = false
            unread = False

        elif action_type == _ACTION_MARK:
            # Source: rssfuncs.php line 818 — if ($type == "mark") marked = true
            marked = True

        elif action_type == _ACTION_PUBLISH:
            # Source: rssfuncs.php line 821 — if ($type == "publish") published = true
            published = True

        elif action_type == _ACTION_SCORE:
            # Source: rssfuncs.php line 824 — score += (int) param
            try:
                score += int(param)
            except (TypeError, ValueError):
                pass

        elif action_type == _ACTION_TAG:
            # Source: rssfuncs.php line 845 — add tag to tag list
            if param and tag_is_valid(param):
                tag_list.append(param)

        elif action_type == _ACTION_LABEL:
            # Source: rssfuncs.php line 851 — assign article to label by caption
            if param:
                label_add_article(session, article_id, param, owner_uid)

        elif action_type == _ACTION_STOP:
            # Source: rssfuncs.php line 828 — break out of filter loop
            break

        # _ACTION_PLUGIN: not wired here (handled by HOOK_ARTICLE_FILTER upstream)

    return {
        "unread": unread,
        "marked": marked,
        "published": published,
        "score": score,
        "tags": tag_list,
    }


# ---------------------------------------------------------------------------
# Enclosure persistence
# ---------------------------------------------------------------------------


def persist_enclosures(
    session: Session,
    article_id: int,
    enclosures: list[dict[str, Any]],
) -> None:
    """Insert enclosures for an article, deduplicated by content_url + post_id.

    Source: ttrss/include/rssfuncs.php lines 982-1020
    Skips enclosures with empty content_url.
    """
    # Load existing URLs to deduplicate
    existing_urls = set(
        session.execute(
            select(TtRssEnclosure.content_url)
            .where(TtRssEnclosure.post_id == article_id)
        ).scalars().all()
    )

    for enc in enclosures:
        url = enc.get("content_url", "").strip()
        if not url or url in existing_urls:
            continue
        session.add(
            TtRssEnclosure(
                post_id=article_id,
                content_url=url,
                content_type=enc.get("content_type", "") or "",
                title=enc.get("title", "") or "",
                duration=enc.get("duration", "") or "",
            )
        )
        existing_urls.add(url)


# ---------------------------------------------------------------------------
# Entry upsert
# ---------------------------------------------------------------------------


def upsert_entry(
    session: Session,
    guid: str,
    title: str,
    link: str,
    content: str,
    content_hash_val: str,
    author: str,
    updated: datetime,
    plugin_data: Optional[str] = None,
    lang: Optional[str] = None,
    num_comments: int = 0,
    comments: str = "",
) -> tuple[int, bool]:
    """INSERT or UPDATE ttrss_entries; return (entry_id, is_new).

    Source: ttrss/include/rssfuncs.php lines 720-750 (INSERT) and 923-970 (UPDATE)
    INSERT if GUID not found; UPDATE content/title if content_hash changed.
    Returns (entry_id, True) if newly created, (entry_id, False) if existing.
    """
    now = datetime.now(timezone.utc)

    # Try existing entry
    existing = session.execute(
        select(TtRssEntry.id, TtRssEntry.content_hash)
        .where(TtRssEntry.guid == guid)
    ).one_or_none()

    if existing is not None:
        entry_id = existing.id
        # Content update detection (rssfuncs.php:923-970)
        if existing.content_hash != content_hash_val:
            session.execute(
                sa_update(TtRssEntry)
                .where(TtRssEntry.id == entry_id)
                .values(
                    title=title,
                    content=content,
                    content_hash=content_hash_val,
                    link=link,
                    author=author,
                    updated=updated,
                    date_updated=now,
                    plugin_data=plugin_data,
                )
            )
        return entry_id, False

    # New entry
    entry = TtRssEntry(
        guid=guid,
        title=title,
        link=link,
        content=content,
        content_hash=content_hash_val,
        author=author,
        updated=updated,
        date_entered=now,
        date_updated=now,
        no_orig_date=False,
        num_comments=num_comments,
        comments=comments,
        plugin_data=plugin_data,
        lang=lang,
    )
    session.add(entry)
    session.flush()  # populate entry.id
    return entry.id, True


# ---------------------------------------------------------------------------
# User entry upsert
# ---------------------------------------------------------------------------


def upsert_user_entry(
    session: Session,
    ref_id: int,
    feed_id: int,
    owner_uid: int,
    unread: bool = True,
    marked: bool = False,
    published: bool = False,
    score: int = 0,
) -> Optional[int]:
    """INSERT into ttrss_user_entries if not exists; return int_id or None.

    Source: ttrss/include/rssfuncs.php lines 887-894
    Skips insert if ref_id already has a user_entry for this owner.
    Returns int_id of the new row, or None if already existed.
    """
    existing_int_id = session.execute(
        select(TtRssUserEntry.int_id)
        .where(TtRssUserEntry.ref_id == ref_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .limit(1)
    ).scalar_one_or_none()

    if existing_int_id is not None:
        return None  # already exists

    user_entry = TtRssUserEntry(
        ref_id=ref_id,
        feed_id=feed_id,
        owner_uid=owner_uid,
        unread=unread,
        marked=marked,
        published=published,
        score=score,
        uuid=str(_uuid_mod.uuid4()),
        tag_cache="",
        label_cache="",
    )
    session.add(user_entry)
    session.flush()
    return user_entry.int_id


# ---------------------------------------------------------------------------
# Top-level persist_article
# ---------------------------------------------------------------------------


def persist_article(
    session: Session,
    entry: Any,
    feed_id: int,
    owner_uid: int,
    filters: list[dict[str, Any]],
    enclosures: Optional[list[dict[str, Any]]] = None,
) -> bool:
    """Persist a single feedparser entry to ttrss_entries + ttrss_user_entries.

    Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 545-1117)
    Returns True if the article was newly inserted, False if it already existed.
    """
    from ttrss.articles.filters import (
        calculate_article_score,
        find_article_filters,
        get_article_filters,
    )

    content = (
        entry.get("summary")
        or (entry.get("content") or [{}])[0].get("value", "")
        or ""
    )
    title = entry.get("title", "") or ""
    link = entry.get("link", "") or ""
    author = entry.get("author", "") or ""

    # Source: rssfuncs.php lines 636-648 — extract tags from <category> elements
    raw_tags = [
        t.get("term", "")
        for t in (entry.get("tags") or [])
        if t.get("term")
    ]
    tag_list = [t for t in raw_tags if tag_is_valid(t)]

    # Source: rssfuncs.php line 650 — parse updated timestamp
    updated_parsed = entry.get("updated_parsed") or entry.get("published_parsed")
    if updated_parsed:
        updated = datetime(*updated_parsed[:6], tzinfo=timezone.utc)
    else:
        updated = datetime.now(timezone.utc)

    # GUID + content hash
    guid = build_entry_guid(entry, owner_uid)
    ch = content_hash(content)

    # N-gram dedup check (rssfuncs.php:867-882)
    if _is_ngram_duplicate(session, title, owner_uid):
        logger.debug("persist_article: n-gram duplicate detected for %r", title)

    # Entry upsert
    entry_id, is_new = upsert_entry(
        session,
        guid=guid,
        title=title,
        link=link,
        content=content,
        content_hash_val=ch,
        author=author,
        updated=updated,
        plugin_data=entry.get("plugin_data"),
        lang=entry.get("language"),
    )

    if not is_new:
        # Existing entry — no need to apply filters or create user_entry again
        return False

    # Filter matching
    matched = get_article_filters(
        filters,
        title=title,
        content=content,
        link=link,
        timestamp=None,
        author=author,
        tags=tag_list,
    )

    # Additional score from score-type actions (rssfuncs.php:824)
    extra_score = calculate_article_score(matched)

    # User entry INSERT
    int_id = upsert_user_entry(
        session,
        ref_id=entry_id,
        feed_id=feed_id,
        owner_uid=owner_uid,
        unread=True,
        marked=False,
        published=False,
        score=extra_score,
    )

    if int_id is None:
        return False  # already had a user entry

    # Apply filter actions (may add tags, assign labels, change unread/marked/published)
    state = apply_filter_actions(
        session,
        article_id=entry_id,
        owner_uid=owner_uid,
        feed_id=feed_id,
        matched_actions=matched,
        tag_list=tag_list,
    )

    # Update user_entry with filter-determined state
    session.execute(
        sa_update(TtRssUserEntry)
        .where(TtRssUserEntry.int_id == int_id)
        .values(
            unread=state["unread"],
            marked=state["marked"],
            published=state["published"],
            score=state["score"],
        )
    )

    # Persist tags
    if state["tags"]:
        setArticleTags(session, entry_id, owner_uid, state["tags"])

    # Persist enclosures
    if enclosures:
        persist_enclosures(session, entry_id, enclosures)

    return True
