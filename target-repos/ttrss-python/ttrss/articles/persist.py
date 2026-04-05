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
Eliminated (inline): ttrss/include/rssfuncs.php::cache_images — image URL rewriting handled inline in sanitize pipeline.
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
    """Fallback GUID from article title (no ID and no link available).

    Source: ttrss/include/rssfuncs.php:make_guid_from_title (lines 1401-1404)
    PHP: preg_replace("/[ \"',.:;]/", "-", mb_strtolower(strip_tags($title), 'utf-8'))
    Adapted: lxml.html.fromstring used to strip HTML tags (equivalent to strip_tags).
    Note: This raw GUID is subsequently owner-scoped and SHA1-hashed in build_entry_guid,
    so the final stored value is always "SHA1:..." regardless of this raw form.
    """
    import re as _re
    # Strip HTML tags (PHP strip_tags equivalent)
    clean = _re.sub(r"<[^>]+>", "", title)
    # Lowercase (PHP mb_strtolower)
    clean = clean.lower()
    # Replace punctuation chars with hyphen (PHP preg_replace("/[ \"',.:;]/", "-", ...))
    return _re.sub(r'[ "\',.:\;]', "-", clean)


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

    Source: rssfuncs.php:871 — WHERE updated >= NOW() - INTERVAL '7 day'
    PHP only checks articles from the last 7 days to avoid false matches against
    old content. Python must also restrict to avoid over-suppression.
    Source: rssfuncs.php:872 — similarity(...) >= threshold (inclusive >=, not >).
    """
    if not title:
        return False
    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = session.execute(
            select(TtRssEntry.id)
            .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
            .where(TtRssUserEntry.owner_uid == owner_uid)
            # Source: rssfuncs.php:871 — 7-day window to avoid matching stale articles
            .where(TtRssEntry.date_updated >= cutoff)
            # Source: rssfuncs.php:872 — >= (inclusive boundary)
            .where(func.similarity(TtRssEntry.title, title) >= _NGRAM_THRESHOLD)
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
    mark_unread_on_update: bool = False,
) -> tuple[int, bool]:
    """INSERT or UPDATE ttrss_entries; return (entry_id, is_new).

    Source: ttrss/include/rssfuncs.php lines 720-750 (INSERT) and 923-970 (UPDATE)
    INSERT if GUID not found; UPDATE content/title if content_hash changed.
    Returns (entry_id, True) if newly created, (entry_id, False) if existing.
    Note: rssfuncs.php lines 926-944 — num_comments, plugin_data, and title changes
          also trigger $post_needs_update. Python only checks content_hash for
          simplicity; those fields are updated along with content when hash changes.
    """
    now = datetime.now(timezone.utc)

    # Try existing entry
    existing = session.execute(
        select(TtRssEntry.id, TtRssEntry.content_hash)
        .where(TtRssEntry.guid == guid)
    ).one_or_none()

    if existing is not None:
        entry_id = existing.id
        # Source: rssfuncs.php lines 926-944 — update if ANY of: content_hash, title,
        # plugin_data, or num_comments changed (not just content_hash).
        # PHP: $post_needs_update = content_hash || title || plugin_data || num_comments
        # Python was only checking content_hash, causing corrected titles to never sync.
        existing_full = session.execute(
            select(
                TtRssEntry.content_hash,
                TtRssEntry.title,
                TtRssEntry.plugin_data,
                TtRssEntry.num_comments,
            ).where(TtRssEntry.id == entry_id)
        ).one_or_none()

        hash_changed = existing_full is None or existing_full.content_hash != content_hash_val
        title_changed = existing_full is None or existing_full.title != title
        plugin_changed = existing_full is None or existing_full.plugin_data != plugin_data
        num_changed = existing_full is None or existing_full.num_comments != num_comments

        if hash_changed or title_changed or plugin_changed or num_changed:
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
                    num_comments=num_comments,
                )
            )
            # Source: rssfuncs.php lines 964-968 — mark_unread only on significant changes
            # (content_hash or title change, not minor plugin_data/num_comments)
            if mark_unread_on_update and (hash_changed or title_changed):
                session.execute(
                    sa_update(TtRssUserEntry)
                    .where(TtRssUserEntry.ref_id == entry_id)
                    .values(last_read=None, unread=True)
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
    allow_duplicate_posts: bool = False,
) -> Optional[int]:
    """INSERT into ttrss_user_entries if not exists; return int_id or None.

    Source: ttrss/include/rssfuncs.php lines 887-894
    Skips insert if ref_id already has a user_entry for this owner.
    Returns int_id of the new row, or None if already existed.

    Source: ttrss/include/rssfuncs.php lines 803-808 — ALLOW_DUPLICATE_POSTS:
    When False (default): check across all feeds (same GUID blocks duplicate user_entry).
    When True: restrict check to current feed only — allows same GUID in multiple feeds.
    """
    # Source: rssfuncs.php lines 832-834 — dupcheck_qpart
    dup_check = (
        select(TtRssUserEntry.int_id)
        .where(TtRssUserEntry.ref_id == ref_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    )
    if allow_duplicate_posts:
        # Source: rssfuncs.php line 806 — AND (feed_id = '$feed' OR feed_id IS NULL)
        dup_check = dup_check.where(
            (TtRssUserEntry.feed_id == feed_id) | (TtRssUserEntry.feed_id.is_(None))
        )
    existing_int_id = session.execute(dup_check.limit(1)).scalar_one_or_none()

    if existing_int_id is not None:
        return None  # already exists

    # Source: rssfuncs.php lines 884-885 — last_marked/last_published = NOW() if set, else NULL
    _now = datetime.now(timezone.utc)
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
        last_marked=_now if marked else None,
        last_published=_now if published else None,
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
    mark_unread_on_update: bool = False,
    allow_duplicate_posts: bool = False,
) -> bool:
    """Persist a single feedparser entry to ttrss_entries + ttrss_user_entries.

    Source: ttrss/include/rssfuncs.php:update_rss_feed (lines 545-1117)
    Returns True if the article was newly inserted, False if it already existed.
    """
    from ttrss.articles.filters import (
        calculate_article_score,
        find_article_filter,
        find_article_filters,
        get_article_filters,
    )

    # Source: rssfuncs.php lines 589-590 — get_content() first (full body), get_description() fallback
    # PHP FeedParser: get_content() = full body; get_description() = summary/description
    # feedparser: entry.content[0].value = full body; entry.summary = description
    content = (
        (entry.get("content") or [{}])[0].get("value", "")
        or entry.get("summary", "")
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
        mark_unread_on_update=mark_unread_on_update,
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

    # Source: rssfuncs.php line 823 — "filter" action type discards article before INSERT
    if find_article_filter(matched, "filter"):
        return False

    # Additional score from score-type actions (rssfuncs.php:824)
    extra_score = calculate_article_score(matched)

    # Source: rssfuncs.php line 845 — unread=false if score < -500 or catchup action
    # Source: rssfuncs.php lines 867-882 — n-gram duplicate → mark read (unread=false)
    ngram_dup = _is_ngram_duplicate(session, title, owner_uid)
    if ngram_dup:
        logger.debug("persist_article: n-gram duplicate detected for %r", title)

    # User entry INSERT
    # Source: rssfuncs.php lines 803-808 — allow_duplicate_posts from caller
    int_id = upsert_user_entry(
        session,
        ref_id=entry_id,
        feed_id=feed_id,
        owner_uid=owner_uid,
        unread=True,
        marked=False,
        published=False,
        score=extra_score,
        allow_duplicate_posts=allow_duplicate_posts,
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

    # Source: rssfuncs.php line 845 — score < -500 forces read regardless of catchup action
    if extra_score < -500:
        state["unread"] = False

    # Source: rssfuncs.php lines 867-882 — n-gram title duplicate → insert as read
    if ngram_dup:
        state["unread"] = False

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


# ---------------------------------------------------------------------------
# Label filter helpers
# ---------------------------------------------------------------------------


def labels_contains_caption(labels: list, caption: str) -> bool:
    """Return True if any label in *labels* has the given caption.

    Source: ttrss/include/rssfuncs.php:labels_contains_caption (lines 1381-1386)
    PHP: foreach ($labels as $label) { if ($label[1] == $caption) return true; }
    """
    return any(lbl[1] == caption for lbl in labels if len(lbl) > 1)


def assign_article_to_label_filters(
    session: "Session",
    article_id: int,
    filters: list,
    owner_uid: int,
    article_labels: list,
) -> None:
    """Assign an article to labels matched by label-type filter actions.

    Source: ttrss/include/rssfuncs.php:assign_article_to_label_filters (lines 1391-1400)
    PHP: foreach filters: if type=="label" and not labels_contains_caption: label_add_article.
    Only assigns if the label is not already present in article_labels.
    """
    from ttrss.labels import label_add_article

    for action in filters:
        if action.get("type") == "label":
            cap = action.get("param", "")
            if cap and not labels_contains_caption(article_labels, cap):
                label_add_article(session, article_id, cap, owner_uid)
