"""Feed preferences CRUD operations — all DB/ORM logic extracted from the prefs blueprint.

Source: ttrss/classes/pref/feeds.php (Pref_Feeds handler, 1925 lines)
Adapted: Per AR-2 all db.session calls live here; the blueprint delegates entirely to
         these functions and never touches db.session directly.

Each public function:
  - accepts a SQLAlchemy Session as its first argument (``session``)
  - contains all SQL/ORM logic for that operation
  - returns plain Python dicts or lists (never Flask responses)
  - carries a ``# Source:`` traceability comment
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ttrss.models.access_key import TtRssAccessKey
from ttrss.models.archived_feed import TtRssArchivedFeed
from ttrss.models.category import TtRssFeedCategory
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.label import TtRssLabel2
from ttrss.models.user_entry import TtRssUserEntry


# ---------------------------------------------------------------------------
# Feed edit dialog data
# ---------------------------------------------------------------------------


def get_feed_for_edit(session: Session, feed_id: int, owner_uid: int) -> Optional[dict]:
    """Return feed data dict for the edit dialog, or None if not found.

    # Source: ttrss/classes/pref/feeds.php:editfeed (line 529)
    #         SELECT * FROM ttrss_feeds WHERE id AND owner_uid (line 535)
    """
    feed = session.execute(
        select(TtRssFeed).where(TtRssFeed.id == feed_id, TtRssFeed.owner_uid == owner_uid)
    ).scalar_one_or_none()
    if feed is None:
        return None
    return {
        "feed_id": feed.id,
        "title": feed.title,
        "feed_url": feed.feed_url,
        "site_url": feed.site_url,
        "cat_id": feed.cat_id,
        "update_interval": feed.update_interval,
        "purge_interval": feed.purge_interval,
        "auth_login": feed.auth_login,
        "private": feed.private,
        "include_in_digest": feed.include_in_digest,
        "always_display_enclosures": feed.always_display_enclosures,
        "hide_images": feed.hide_images,
        "cache_images": feed.cache_images,
        "mark_unread_on_update": feed.mark_unread_on_update,
        "last_error": feed.last_error,
    }


# ---------------------------------------------------------------------------
# Save single feed settings
# ---------------------------------------------------------------------------


def save_feed_settings(
    session: Session,
    feed_id: int,
    owner_uid: int,
    data: dict,
) -> bool:
    """Apply posted form data to a single feed.  Returns False if feed not found.

    # Source: ttrss/classes/pref/feeds.php:editsaveops (line 916) / editSave (line 912)
    #         ttrss/classes/pref/feeds.php:918 — feed_title = trim($_POST["title"])
    #         ttrss/classes/pref/feeds.php:927-938 — boolean checkbox fields
    """
    feed = session.execute(
        select(TtRssFeed).where(TtRssFeed.id == feed_id, TtRssFeed.owner_uid == owner_uid)
    ).scalar_one_or_none()
    if feed is None:
        return False

    if "title" in data:
        feed.title = data["title"].strip()
    if "feed_url" in data:
        feed.feed_url = data["feed_url"].strip()
    if "update_interval" in data:
        feed.update_interval = int(data["update_interval"])
    if "purge_interval" in data:
        feed.purge_interval = int(data["purge_interval"])
    if "auth_login" in data:
        feed.auth_login = data["auth_login"].strip()
    if "auth_pass" in data:
        feed.auth_pass = data["auth_pass"].strip()
    if "cat_id" in data:
        cat_id = int(data["cat_id"])
        feed.cat_id = cat_id if cat_id != 0 else None

    feed.private = _checkbox_bool(data.get("private"))
    feed.include_in_digest = _checkbox_bool(data.get("include_in_digest"))
    feed.cache_images = _checkbox_bool(data.get("cache_images"))
    feed.hide_images = _checkbox_bool(data.get("hide_images"))
    feed.always_display_enclosures = _checkbox_bool(data.get("always_display_enclosures"))
    feed.mark_unread_on_update = _checkbox_bool(data.get("mark_unread_on_update"))

    session.commit()
    return True


# ---------------------------------------------------------------------------
# Batch edit save
# ---------------------------------------------------------------------------


def batch_edit_feeds(
    session: Session,
    feed_ids: list[int],
    owner_uid: int,
    data: dict,
) -> None:
    """Apply settings changes to multiple feeds at once.

    # Source: ttrss/classes/pref/feeds.php:batchEditSave (line 908) / editsaveops(true) (line 984)
    #         ttrss/classes/pref/feeds.php:984-1064 — iterate posted keys and update matching feeds
    """
    update_values: dict = {}
    field_map = {
        "title": "title",
        "feed_url": "feed_url",
        "update_interval": "update_interval",
        "purge_interval": "purge_interval",
        "auth_login": "auth_login",
    }
    for form_key, col_name in field_map.items():
        if form_key in data:
            val = data[form_key]
            if col_name in ("update_interval", "purge_interval"):
                val = int(val)
            else:
                val = val.strip()
            update_values[col_name] = val

    bool_fields = [
        "private", "include_in_digest", "always_display_enclosures",
        "mark_unread_on_update", "cache_images", "hide_images",
    ]
    for bf in bool_fields:
        if bf in data:
            update_values[bf] = _checkbox_bool(data.get(bf))

    if "cat_id" in data:
        cat_id = int(data["cat_id"])
        update_values["cat_id"] = cat_id if cat_id != 0 else None

    if update_values:
        session.execute(
            update(TtRssFeed)
            .where(TtRssFeed.id.in_(feed_ids), TtRssFeed.owner_uid == owner_uid)
            .values(**update_values)
        )

    # Handle auth_pass separately (needs per-feed Fernet encryption via property setter)
    if "auth_pass" in data:
        auth_pass_val = data["auth_pass"].strip()
        feeds = session.execute(
            select(TtRssFeed).where(TtRssFeed.id.in_(feed_ids), TtRssFeed.owner_uid == owner_uid)
        ).scalars().all()
        for f in feeds:
            f.auth_pass = auth_pass_val

    session.commit()


# ---------------------------------------------------------------------------
# Feed order
# ---------------------------------------------------------------------------


def save_feed_order(session: Session, owner_uid: int, items: list) -> None:
    """Persist drag-and-drop feed/category order to the database.

    # Source: ttrss/classes/pref/feeds.php:savefeedorder (line 386)
    #         ttrss/classes/pref/feeds.php:400-418 — build data_map and process
    """
    data_map: dict = {}
    root_item = None
    for item in items:
        item_id = item.get("id")
        if isinstance(item.get("items"), list):
            if len(item["items"]) == 1 and "_reference" in (item["items"][0] if isinstance(item["items"][0], dict) else {}):
                data_map[item_id] = [item["items"][0]]
            else:
                data_map[item_id] = item["items"]
        if item_id == "root":
            root_item = item_id

    if root_item:
        _process_category_order(session, data_map, root_item, parent_id=None, owner_uid=owner_uid)

    session.commit()


def _process_category_order(
    session: Session,
    data_map: dict,
    item_id: str,
    parent_id: Any,
    owner_uid: int,
    nest_level: int = 0,
) -> None:
    """Recursively process category/feed ordering from the tree data.

    # Source: ttrss/classes/pref/feeds.php:process_category_order (line 315)
    #         ttrss/classes/pref/feeds.php:326-337 — update parent_cat for categories
    #         ttrss/classes/pref/feeds.php:354-364 — update feed order_id / cat_id
    #         ttrss/classes/pref/feeds.php:365-378 — recurse into sub-categories
    """
    if nest_level > 20:
        return

    bare_item_id = item_id.split(":")[-1] if ":" in item_id else item_id

    if item_id != "root":
        if parent_id and parent_id != "root":
            parent_bare_id = int(parent_id.split(":")[-1])
        else:
            parent_bare_id = None

        if bare_item_id.isdigit():
            session.execute(
                update(TtRssFeedCategory)
                .where(TtRssFeedCategory.id == int(bare_item_id), TtRssFeedCategory.owner_uid == owner_uid)
                .values(parent_cat=parent_bare_id)
            )

    cat = data_map.get(item_id, [])
    order_id = 0

    for child in cat:
        ref = child.get("_reference") if isinstance(child, dict) else None
        if not ref:
            continue
        bare_id = ref.split(":")[-1]

        if ref.startswith("FEED") and bare_id.isdigit():
            cat_id_val = int(bare_item_id) if item_id != "root" and bare_item_id.isdigit() else None
            session.execute(
                update(TtRssFeed)
                .where(TtRssFeed.id == int(bare_id), TtRssFeed.owner_uid == owner_uid)
                .values(order_id=order_id, cat_id=cat_id_val)
            )
        elif ref.startswith("CAT:") and bare_id.isdigit():
            _process_category_order(session, data_map, ref, item_id, owner_uid, nest_level + 1)
            session.execute(
                update(TtRssFeedCategory)
                .where(TtRssFeedCategory.id == int(bare_id), TtRssFeedCategory.owner_uid == owner_uid)
                .values(order_id=order_id)
            )

        order_id += 1


# ---------------------------------------------------------------------------
# Icon operations
# ---------------------------------------------------------------------------


def verify_feed_ownership(session: Session, feed_id: int, owner_uid: int) -> bool:
    """Return True if the feed exists and belongs to owner_uid.

    # Source: ttrss/classes/pref/feeds.php:uploadicon / removeicon — ownership check
    """
    result = session.execute(
        select(TtRssFeed.id).where(TtRssFeed.id == feed_id, TtRssFeed.owner_uid == owner_uid)
    ).scalar_one_or_none()
    return result is not None


def reset_favicon_color(session: Session, feed_id: int, value: Optional[str] = "") -> None:
    """Reset favicon_avg_color after icon upload or removal.

    # Source: ttrss/classes/pref/feeds.php:505-507 — reset favicon_avg_color on upload
    #         ttrss/classes/pref/feeds.php:468-469 — reset favicon_avg_color on remove
    """
    session.execute(
        update(TtRssFeed).where(TtRssFeed.id == feed_id).values(favicon_avg_color=value)
    )
    session.commit()


# ---------------------------------------------------------------------------
# Remove feed (unsubscribe)
# ---------------------------------------------------------------------------


def remove_feed(
    session: Session,
    feed_id: int,
    owner_uid: int,
    icons_dir: str = "",
) -> Optional[str]:
    """Unsubscribe from a feed, archiving starred articles.  Returns error string or None.

    # Source: ttrss/classes/pref/feeds.php:remove (line 1078) / remove_feed (line 1707)
    #         ttrss/classes/pref/feeds.php:1709-1764 — archive starred, then delete
    """
    import pathlib

    if feed_id > 0:
        feed_row = session.execute(
            select(TtRssFeed).where(TtRssFeed.id == feed_id, TtRssFeed.owner_uid == owner_uid)
        ).scalar_one_or_none()
        if feed_row is None:
            return "Feed not found"

        # Source: ttrss/classes/pref/feeds.php:1726-1735 — create archived feed if missing
        existing_archive = session.execute(
            select(TtRssArchivedFeed.id)
            .where(TtRssArchivedFeed.feed_url == feed_row.feed_url,
                   TtRssArchivedFeed.owner_uid == owner_uid)
        ).scalar_one_or_none()

        if existing_archive is None:
            max_id = session.execute(
                select(func.coalesce(func.max(TtRssArchivedFeed.id), 0))
            ).scalar() or 0
            new_archive_id = max_id + 1
            session.add(TtRssArchivedFeed(
                id=new_archive_id,
                owner_uid=owner_uid,
                title=feed_row.title,
                feed_url=feed_row.feed_url,
                site_url=feed_row.site_url,
            ))
            archive_id = new_archive_id
        else:
            archive_id = existing_archive

        # Source: ttrss/classes/pref/feeds.php:1739-1741 — move starred entries to archive
        session.execute(
            update(TtRssUserEntry)
            .where(TtRssUserEntry.feed_id == feed_id,
                   TtRssUserEntry.marked.is_(True),
                   TtRssUserEntry.owner_uid == owner_uid)
            .values(feed_id=None, orig_feed_id=archive_id)
        )

        # Source: ttrss/classes/pref/feeds.php:1745-1746 — remove access key
        session.execute(
            sa_delete(TtRssAccessKey)
            .where(TtRssAccessKey.feed_id == str(feed_id),
                   TtRssAccessKey.owner_uid == owner_uid)
        )

        # Source: ttrss/classes/pref/feeds.php:1750-1751 — delete the feed
        session.execute(
            sa_delete(TtRssFeed)
            .where(TtRssFeed.id == feed_id, TtRssFeed.owner_uid == owner_uid)
        )

        if icons_dir:
            icon_path = pathlib.Path(icons_dir) / f"{feed_id}.ico"
            if icon_path.exists():
                icon_path.unlink()

        # Source: ttrss/classes/pref/feeds.php:1759 — ccache_remove($id, $owner_uid)
        # Invalidate counter cache after feed deletion to prevent stale counts.
        from ttrss.ccache import ccache_remove
        ccache_remove(session, feed_id, owner_uid)

        session.commit()
    else:
        # Source: ttrss/classes/pref/feeds.php:1762 — label_remove for negative feed IDs
        from ttrss.labels import label_remove
        from ttrss.utils.feeds import feed_to_label_id
        label_remove(session, feed_to_label_id(feed_id), owner_uid)
        session.commit()

    return None


# ---------------------------------------------------------------------------
# Clear feed articles
# ---------------------------------------------------------------------------


def clear_feed_articles(session: Session, feed_id: int, owner_uid: int) -> None:
    """Purge all non-starred articles from a feed.

    # Source: ttrss/classes/pref/feeds.php:clear_feed_articles (line 1683) / clear (line 1089)
    #         ttrss/classes/pref/feeds.php:1685-1694 — delete user_entries, purge orphans, ccache
    """
    from ttrss.ccache import ccache_update

    if feed_id != 0:
        session.execute(
            sa_delete(TtRssUserEntry)
            .where(TtRssUserEntry.feed_id == feed_id,
                   TtRssUserEntry.marked.is_(False),
                   TtRssUserEntry.owner_uid == owner_uid)
        )
    else:
        session.execute(
            sa_delete(TtRssUserEntry)
            .where(TtRssUserEntry.feed_id.is_(None),
                   TtRssUserEntry.marked.is_(False),
                   TtRssUserEntry.owner_uid == owner_uid)
        )

    # Source: ttrss/classes/pref/feeds.php:1693-1694 — purge orphaned entries
    orphan_subq = (
        select(func.count(TtRssUserEntry.int_id))
        .where(TtRssUserEntry.ref_id == TtRssEntry.id)
        .correlate(TtRssEntry)
        .scalar_subquery()
    )
    session.execute(sa_delete(TtRssEntry).where(orphan_subq == 0))

    # Source: ttrss/classes/pref/feeds.php:1696 — ccache_update
    ccache_update(session, feed_id, owner_uid)
    session.commit()


# ---------------------------------------------------------------------------
# Rescore feeds
# ---------------------------------------------------------------------------


def rescore_feed_impl(session: Session, feed_id: int, owner_uid: int) -> None:
    """Rescore all articles in a feed using current filter rules.

    # Source: ttrss/classes/pref/feeds.php:rescore (lines 1094-1147)
    # Source: ttrss/classes/pref/feeds.php:rescoreAll delegated here for single-feed case
    #         action_id=6 is score action
    """
    from ttrss.articles.filters import (
        calculate_article_score,
        get_article_filters,
        load_filters,
    )
    from ttrss.articles.tags import get_article_tags

    filters = load_filters(session, feed_id, owner_uid, action_id=6)

    rows = session.execute(
        select(
            TtRssEntry.title,
            TtRssEntry.content,
            TtRssEntry.link,
            TtRssUserEntry.ref_id,
            TtRssUserEntry.tag_cache,
            TtRssEntry.author,
            TtRssEntry.updated,
        )
        .join(TtRssEntry, TtRssEntry.id == TtRssUserEntry.ref_id)
        .where(TtRssUserEntry.feed_id == feed_id, TtRssUserEntry.owner_uid == owner_uid)
    ).all()

    scores: dict[int, list[int]] = {}
    for row in rows:
        # Source: ttrss/classes/pref/feeds.php:1116 — get_article_tags($line["ref_id"])
        # PHP fetches actual tags before calling get_article_filters; passing [] silently
        # breaks tag-based filter rules during rescoring.
        article_tags = get_article_tags(session, row.ref_id, owner_uid, tag_cache=row.tag_cache)
        article_filters = get_article_filters(
            filters, row.title or "", row.content or "", row.link or "",
            row.updated, row.author or "", article_tags,
        )
        new_score = calculate_article_score(article_filters)
        scores.setdefault(new_score, []).append(row.ref_id)

    # Source: ttrss/classes/pref/feeds.php:1129-1142
    for s, ref_ids in scores.items():
        vals: dict = {"score": s}
        if s > 1000:
            vals["marked"] = True
        elif s < -500:
            vals["unread"] = False
        session.execute(
            update(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(ref_ids))
            .values(**vals)
        )


def get_all_feed_ids(session: Session, owner_uid: int) -> list[int]:
    """Return all feed IDs for a user.

    # Source: ttrss/classes/pref/feeds.php:1151-1152 — SELECT id FROM ttrss_feeds
    """
    return list(session.execute(
        select(TtRssFeed.id).where(TtRssFeed.owner_uid == owner_uid)
    ).scalars().all())


# ---------------------------------------------------------------------------
# Categorize feeds
# ---------------------------------------------------------------------------


def categorize_feeds(
    session: Session,
    feed_ids: list[int],
    owner_uid: int,
    cat_id: int,
) -> None:
    """Move feeds to a specified category.

    # Source: ttrss/classes/pref/feeds.php:categorize (line 1202)
    #         ttrss/classes/pref/feeds.php:1215-1221 — iterate and update cat_id
    """
    cat_id_val = cat_id if cat_id != 0 else None
    for fid in feed_ids:
        session.execute(
            update(TtRssFeed)
            .where(TtRssFeed.id == fid, TtRssFeed.owner_uid == owner_uid)
            .values(cat_id=cat_id_val)
        )
    session.commit()


# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------


def remove_category(session: Session, cat_id: int, owner_uid: int) -> None:
    """Remove a feed category.

    Source: ttrss/classes/pref/feeds.php:remove_feed_category (lines 1699-1705)
    Source: ttrss/classes/pref/feeds.php:removeCat (line 1226)
    PHP line 1702: DELETE FROM ttrss_feed_categories WHERE id AND owner_uid.
    PHP line 1704: ccache_remove($id, $owner_uid, true) — invalidate category cache entry.
    """
    from ttrss.ccache import ccache_remove

    session.execute(
        sa_delete(TtRssFeedCategory)
        .where(TtRssFeedCategory.id == cat_id, TtRssFeedCategory.owner_uid == owner_uid)
    )
    ccache_remove(session, cat_id, owner_uid, is_cat=True)
    session.commit()


def rename_category(session: Session, cat_id: int, owner_uid: int, title: str) -> None:
    """Rename a feed category.

    # Source: ttrss/classes/pref/feeds.php:renamecat (line 17)
    #         ttrss/classes/pref/feeds.php:22-23 — UPDATE ttrss_feed_categories SET title
    """
    session.execute(
        update(TtRssFeedCategory)
        .where(TtRssFeedCategory.id == cat_id, TtRssFeedCategory.owner_uid == owner_uid)
        .values(title=title)
    )
    session.commit()


def reset_category_order(session: Session, owner_uid: int) -> None:
    """Reset category sort order to default.

    # Source: ttrss/classes/pref/feeds.php:catsortreset (line 303)
    """
    session.execute(
        update(TtRssFeedCategory)
        .where(TtRssFeedCategory.owner_uid == owner_uid)
        .values(order_id=0)
    )
    session.commit()


def reset_feed_order(session: Session, owner_uid: int) -> None:
    """Reset feed sort order to default.

    # Source: ttrss/classes/pref/feeds.php:feedsortreset (line 309)
    """
    session.execute(
        update(TtRssFeed)
        .where(TtRssFeed.owner_uid == owner_uid)
        .values(order_id=0)
    )
    session.commit()


# ---------------------------------------------------------------------------
# Inactive feeds
# ---------------------------------------------------------------------------


def get_inactive_feeds(session: Session, owner_uid: int) -> list[dict]:
    """Return feeds with no new articles for 3 months.

    # Source: ttrss/classes/pref/feeds.php:inactiveFeeds (line 1529)
    #         ttrss/classes/pref/feeds.php:1537-1547 — correlated subquery for max(updated)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    max_updated_subq = (
        select(func.max(TtRssEntry.updated))
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .where(TtRssUserEntry.feed_id == TtRssFeed.id)
        .correlate(TtRssFeed)
        .scalar_subquery()
    )

    rows = session.execute(
        select(
            TtRssFeed.id,
            TtRssFeed.title,
            TtRssFeed.site_url,
            TtRssFeed.feed_url,
            func.max(TtRssEntry.updated).label("last_article"),
        )
        .join(TtRssUserEntry, TtRssUserEntry.feed_id == TtRssFeed.id)
        .join(TtRssEntry, TtRssEntry.id == TtRssUserEntry.ref_id)
        .where(TtRssFeed.owner_uid == owner_uid)
        .where(max_updated_subq < cutoff)
        .group_by(TtRssFeed.id, TtRssFeed.title, TtRssFeed.site_url, TtRssFeed.feed_url)
        .order_by(func.max(TtRssEntry.updated))
    ).all()

    return [
        {
            "id": r.id,
            "title": r.title,
            "site_url": r.site_url,
            "feed_url": r.feed_url,
            "last_article": r.last_article.isoformat() if r.last_article else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Feeds with errors
# ---------------------------------------------------------------------------


def get_feeds_with_errors(session: Session, owner_uid: int) -> list[dict]:
    """Return feeds that have last_error set.

    # Source: ttrss/classes/pref/feeds.php:feedsWithErrors (line 1611)
    """
    rows = session.execute(
        select(TtRssFeed.id, TtRssFeed.title, TtRssFeed.feed_url,
               TtRssFeed.last_error, TtRssFeed.site_url)
        .where(TtRssFeed.last_error != "", TtRssFeed.owner_uid == owner_uid)
    ).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "feed_url": r.feed_url,
            "last_error": r.last_error,
            "site_url": r.site_url,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Batch subscribe
# ---------------------------------------------------------------------------


def batch_subscribe_feeds(
    session: Session,
    owner_uid: int,
    feeds_text: str,
    cat_id: Optional[int],
    login: str,
    password: str,
) -> list[dict]:
    """Subscribe to multiple feeds at once (one URL per line).

    Source: ttrss/classes/pref/feeds.php:batchSubscribe (lines 1767-1860)
    Source: ttrss/classes/pref/feeds.php:batchAddFeeds (line 1815)
    PHP: subscribe each URL in a newline-separated list.
    """
    from ttrss.http.client import validate_feed_url

    results = []
    for line in feeds_text.split("\n"):
        feed_url = line.strip()
        if not feed_url:
            continue

        # Source: ttrss/classes/pref/feeds.php:1820 — validate_feed_url() check before subscribe
        if not validate_feed_url(feed_url):
            results.append({"url": feed_url, "status": "invalid_url"})
            continue

        existing = session.execute(
            select(TtRssFeed.id)
            .where(TtRssFeed.feed_url == feed_url, TtRssFeed.owner_uid == owner_uid)
        ).scalar_one_or_none()

        if existing is not None:
            results.append({"url": feed_url, "status": "already_subscribed"})
            continue

        new_feed = TtRssFeed(
            owner_uid=owner_uid,
            feed_url=feed_url,
            title="[Unknown]",
            cat_id=cat_id,
            auth_login=login,
            update_method=0,
        )
        if password:
            new_feed.auth_pass = password
        session.add(new_feed)
        results.append({"url": feed_url, "status": "subscribed"})

    session.commit()
    return results


# ---------------------------------------------------------------------------
# Access key management
# ---------------------------------------------------------------------------


def update_feed_access_key(
    session: Session,
    feed_id_str: str,
    is_cat: bool,
    owner_uid: int,
) -> str:
    """Regenerate or create an access key for a feed/OPML.

    # Source: ttrss/classes/pref/feeds.php:update_feed_access_key (line 1880)
    """
    existing = session.execute(
        select(TtRssAccessKey)
        .where(TtRssAccessKey.feed_id == feed_id_str,
               TtRssAccessKey.is_cat == is_cat,
               TtRssAccessKey.owner_uid == owner_uid)
    ).scalar_one_or_none()

    new_key = secrets.token_urlsafe(16)[:24]

    if existing is not None:
        existing.access_key = new_key
    else:
        session.add(TtRssAccessKey(
            access_key=new_key,
            feed_id=feed_id_str,
            is_cat=is_cat,
            owner_uid=owner_uid,
        ))

    session.commit()
    return new_key


# ---------------------------------------------------------------------------
# Feed tree
# ---------------------------------------------------------------------------


def get_feed_tree(
    session: Session,
    owner_uid: int,
    mode: int = 0,
    search: str = "",
    force_show_empty: bool = False,
) -> dict:
    """Return the full feed/category tree structure.

    # Source: ttrss/classes/pref/feeds.php:getfeedtree (line 94) / makefeedtree (line 98)
    #         ttrss/classes/pref/feeds.php:115-300 — build tree with categories, labels, feeds
    """
    from ttrss.feeds.categories import getCategoryTitle, getFeedTitle
    from ttrss.prefs.ops import get_user_pref

    show_empty_cats = force_show_empty or (mode != 2 and not search)
    enable_cats = get_user_pref(owner_uid, "ENABLE_FEED_CATS") == "true"

    root: dict = {
        "id": "root",
        "name": "Feeds",
        "items": [],
        "type": "category",
        "param": 0,
    }

    search_filter = f"%{search.lower()}%" if search else None

    if mode == 2:
        # Source: ttrss/classes/pref/feeds.php:115-187 — special feeds and labels
        if enable_cats:
            cat = _init_cat_node(session, -1)
        else:
            cat = {"items": []}

        for i in [-4, -3, -1, -2, 0, -6]:
            cat["items"].append(_init_feed_node(session, i))

        if enable_cats:
            root["items"].append(cat)
        else:
            root["items"].extend(cat["items"])

        label_rows = session.execute(
            select(TtRssLabel2)
            .where(TtRssLabel2.owner_uid == owner_uid)
            .order_by(TtRssLabel2.caption)
        ).scalars().all()

        if label_rows:
            if enable_cats:
                label_cat = _init_cat_node(session, -2)
            else:
                label_cat = {"items": []}

            from ttrss.utils.feeds import label_to_feed_id
            for lbl in label_rows:
                label_feed_id = label_to_feed_id(lbl.id)
                feed_item = _init_feed_node(session, label_feed_id)
                feed_item["fg_color"] = lbl.fg_color
                feed_item["bg_color"] = lbl.bg_color
                label_cat["items"].append(feed_item)

            if enable_cats:
                root["items"].append(label_cat)
            else:
                root["items"].extend(label_cat["items"])

    if enable_cats:
        # Source: ttrss/classes/pref/feeds.php:189-261 — categorized feeds
        top_cats = session.execute(
            select(TtRssFeedCategory)
            .where(TtRssFeedCategory.owner_uid == owner_uid,
                   TtRssFeedCategory.parent_cat.is_(None))
            .order_by(TtRssFeedCategory.order_id, TtRssFeedCategory.title)
        ).scalars().all()

        for tc in top_cats:
            cat_item = {
                "id": f"CAT:{tc.id}",
                "bare_id": tc.id,
                "auxcounter": 0,
                "name": tc.title,
                "items": [],
                "checkbox": False,
                "type": "category",
                "unread": 0,
                "child_unread": 0,
            }
            cat_item["items"] = _get_category_items(session, tc.id, owner_uid, search_filter, show_empty_cats)
            num_children = _calculate_children_count(cat_item)
            cat_item["param"] = f"({num_children} feed{'s' if num_children != 1 else ''})"
            if num_children > 0 or show_empty_cats:
                root["items"].append(cat_item)

        # Source: ttrss/classes/pref/feeds.php:221-258 — uncategorized feeds
        uncat: dict = {
            "id": "CAT:0",
            "bare_id": 0,
            "auxcounter": 0,
            "name": "Uncategorized",
            "items": [],
            "type": "category",
            "checkbox": False,
            "unread": 0,
            "child_unread": 0,
        }

        q = (
            select(TtRssFeed)
            .where(TtRssFeed.cat_id.is_(None), TtRssFeed.owner_uid == owner_uid)
            .order_by(TtRssFeed.order_id, TtRssFeed.title)
        )
        if search_filter:
            q = q.where(func.lower(TtRssFeed.title).like(search_filter))

        uncat_feeds = session.execute(q).scalars().all()
        for uf in uncat_feeds:
            uncat["items"].append(_feed_to_item(uf))

        n = len(uncat["items"])
        uncat["param"] = f"({n} feed{'s' if n != 1 else ''})"
        if n > 0 or show_empty_cats:
            root["items"].append(uncat)

        total = _calculate_children_count(root)
        root["param"] = f"({total} feed{'s' if total != 1 else ''})"
    else:
        # Source: ttrss/classes/pref/feeds.php:263-288 — flat feed list
        q = (
            select(TtRssFeed)
            .where(TtRssFeed.owner_uid == owner_uid)
            .order_by(TtRssFeed.order_id, TtRssFeed.title)
        )
        if search_filter:
            q = q.where(func.lower(TtRssFeed.title).like(search_filter))

        flat_feeds = session.execute(q).scalars().all()
        for ff in flat_feeds:
            root["items"].append(_feed_to_item(ff))

        n = len(root["items"])
        root["param"] = f"({n} feed{'s' if n != 1 else ''})"

    # Source: ttrss/classes/pref/feeds.php:290-300
    fl: dict = {"identifier": "id", "label": "name"}
    if mode != 2:
        fl["items"] = [root]
    else:
        fl["items"] = root["items"]

    return fl


# ---------------------------------------------------------------------------
# Tree helper functions (private)
# ---------------------------------------------------------------------------


def _get_category_items(
    session: Session,
    cat_id: int,
    owner_uid: int,
    search_filter: Optional[str],
    show_empty_cats: bool,
) -> list:
    """Recursively build category items for the feed tree.

    # Source: ttrss/classes/pref/feeds.php:get_category_items (line 28)
    """
    items = []

    sub_cats = session.execute(
        select(TtRssFeedCategory)
        .where(TtRssFeedCategory.owner_uid == owner_uid,
               TtRssFeedCategory.parent_cat == cat_id)
        .order_by(TtRssFeedCategory.order_id, TtRssFeedCategory.title)
    ).scalars().all()

    for sc in sub_cats:
        cat_item = {
            "id": f"CAT:{sc.id}",
            "bare_id": sc.id,
            "name": sc.title,
            "items": [],
            "checkbox": False,
            "type": "category",
            "unread": 0,
            "child_unread": 0,
            "auxcounter": 0,
        }
        cat_item["items"] = _get_category_items(session, sc.id, owner_uid, search_filter, show_empty_cats)
        num_children = _calculate_children_count(cat_item)
        cat_item["param"] = f"({num_children} feed{'s' if num_children != 1 else ''})"
        if num_children > 0 or show_empty_cats:
            items.append(cat_item)

    q = (
        select(TtRssFeed)
        .where(TtRssFeed.cat_id == cat_id, TtRssFeed.owner_uid == owner_uid)
        .order_by(TtRssFeed.order_id, TtRssFeed.title)
    )
    if search_filter:
        q = q.where(func.lower(TtRssFeed.title).like(search_filter))

    feeds = session.execute(q).scalars().all()
    for f in feeds:
        items.append(_feed_to_item(f))

    return items


def _feed_to_item(feed: TtRssFeed) -> dict:
    """Convert a feed ORM object to tree item dict."""
    return {
        "id": f"FEED:{feed.id}",
        "bare_id": feed.id,
        "auxcounter": 0,
        "name": feed.title,
        "checkbox": False,
        "unread": 0,
        "error": feed.last_error,
        "icon": f"{feed.id}.ico",
        "param": feed.last_updated.isoformat() if feed.last_updated else "",
        "type": "feed",
    }


def _init_cat_node(session: Session, cat_id: int) -> dict:
    """Initialize a virtual category node.

    # Source: ttrss/classes/pref/feeds.php:feedlist_init_cat (line 1486)
    """
    from ttrss.feeds.categories import getCategoryTitle
    return {
        "id": f"CAT:{cat_id}",
        "items": [],
        "name": getCategoryTitle(session, cat_id),
        "type": "category",
        "unread": 0,
        "bare_id": cat_id,
        "auxcounter": 0,
    }


def _init_feed_node(session: Session, feed_id: int) -> dict:
    """Initialize a virtual feed node.

    # Source: ttrss/classes/pref/feeds.php:feedlist_init_feed (line 1506)
    """
    from ttrss.feeds.categories import getFeedTitle
    return {
        "id": f"FEED:{feed_id}",
        "name": getFeedTitle(session, feed_id),
        "unread": 0,
        "type": "feed",
        "error": "",
        "updated": "",
        "icon": f"{feed_id}.ico" if feed_id > 0 else "",
        "bare_id": feed_id,
        "auxcounter": 0,
    }


def _calculate_children_count(cat: dict) -> int:
    """Count leaf feeds in a category tree.

    # Source: ttrss/classes/pref/feeds.php:calculate_children_count (line 1909)
    """
    c = 0
    for child in cat.get("items", []):
        if child.get("type") == "category":
            c += _calculate_children_count(child)
        else:
            c += 1
    return c


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _checkbox_bool(value: Any) -> bool:
    """Convert a checkbox form value to boolean, matching PHP checkbox_to_sql_bool."""
    if value is None:
        return False
    return str(value).lower() in ("1", "true", "on", "yes")


# ---------------------------------------------------------------------------
# Icon / PubSub / Access key helpers
# ---------------------------------------------------------------------------


def remove_feed_icon(session: Session, feed_id: int, owner_uid: int) -> bool:
    """Clear favicon colour data for a feed.

    Source: ttrss/classes/pref/feeds.php:Pref_Feeds::removeicon (lines 459-470)
    PHP: UPDATE ttrss_feeds SET favicon_avg_color = NULL WHERE id = feed_id AND owner_uid = uid.
    Returns False if feed not owned by user.
    """
    result = session.execute(
        update(TtRssFeed)
        .where(TtRssFeed.id == feed_id, TtRssFeed.owner_uid == owner_uid)
        .values(favicon_avg_color=None)
    )
    session.commit()
    return result.rowcount > 0


def reset_pubsub(session: Session, feed_ids: list, owner_uid: int) -> int:
    """Reset PubSubHubbub subscription state to 0 for a set of feeds.

    Source: ttrss/classes/pref/feeds.php:Pref_Feeds::resetPubSub (lines 1068-1077)
    PHP: UPDATE ttrss_feeds SET pubsub_state = 0 WHERE id IN (ids) AND owner_uid = uid.
    """
    if not feed_ids:
        return 0
    result = session.execute(
        update(TtRssFeed)
        .where(TtRssFeed.id.in_(feed_ids), TtRssFeed.owner_uid == owner_uid)
        .values(pubsub_state=0)
    )
    session.commit()
    return result.rowcount


def regen_opml_key(session: Session, owner_uid: int) -> str:
    """Regenerate the OPML publish access key for a user.

    Source: ttrss/classes/pref/feeds.php:Pref_Feeds::regenOPMLKey (lines 1861-1867)
    PHP: calls update_feed_access_key('OPML:Publish', false, uid), returns new link.
    """
    return update_feed_access_key(session, "OPML:Publish", False, owner_uid)


def regen_feed_key(session: Session, feed_id: int, is_cat: bool, owner_uid: int) -> str:
    """Regenerate the per-feed access key.

    Source: ttrss/classes/pref/feeds.php:Pref_Feeds::regenFeedKey (lines 1870-1878)
    PHP: regenerates key via update_feed_access_key for the given feed_id/is_cat.
    """
    return update_feed_access_key(session, str(feed_id), is_cat, owner_uid)


def clear_access_keys(session: Session, owner_uid: int) -> None:
    """Delete all access keys for a user.

    Source: ttrss/classes/pref/feeds.php:Pref_Feeds::clearKeys (lines 1904-1906)
    PHP: DELETE FROM ttrss_access_keys WHERE owner_uid = uid.
    """
    session.execute(
        sa_delete(TtRssAccessKey).where(TtRssAccessKey.owner_uid == owner_uid)
    )
    session.commit()
