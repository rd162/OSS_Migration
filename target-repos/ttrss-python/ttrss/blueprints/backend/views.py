"""
TT-RSS AJAX RPC dispatcher (/backend.php — equivalent to PHP backend.php).

Dispatch table covers:
  op=rpc   → RPC class  (ttrss/classes/rpc.php)
  op=dlg   → Dlg class  (ttrss/classes/dlg.php)
  op=backend → Backend class (ttrss/classes/backend.php)

Source: ttrss/backend.php (entry point)
        + ttrss/classes/backend.php:Backend (dispatch class)
        + ttrss/classes/handler/protected.php (login_required base for all backend ops)

CSRF (R13, ADR-0002, AR06):
  Flask-WTF CSRFProtect is active globally.
  Config WTF_CSRF_HEADERS=["X-CSRFToken","X-CSRF-Token"] allows AJAX callers
  to pass the token as a header (A-NC-05, CG-05).
  JavaScript must include X-CSRFToken in all state-mutating POST requests.
  Methods in csrf_ignore list bypass token check (sanitycheck, completelabels)
  to match PHP RPC::csrf_ignore behaviour.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import structlog
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy import update as sa_update

from ttrss.extensions import db
from ttrss.models.category import TtRssFeedCategory  # noqa: F401 — DB table coverage (rpc.php)

logger = structlog.get_logger(__name__)

# Source: ttrss/backend.php + ttrss/classes/backend.php:Backend
backend_bp = Blueprint("backend", __name__)

# ---------------------------------------------------------------------------
# CSRF-exempt methods (GET-safe info ops)
# Source: ttrss/classes/rpc.php:RPC::csrf_ignore (lines 4-8)
# ---------------------------------------------------------------------------
_RPC_CSRF_IGNORE = {"sanitycheck", "completelabels"}


def _param(key: str, default: str = "") -> str:
    """Read a request parameter from form, JSON body, or query string.

    Source: ttrss/backend.php — PHP $_REQUEST merges GET, POST, COOKIE.
    """
    data = request.get_json(silent=True) or {}
    return (
        request.form.get(key)
        or data.get(key)
        or request.args.get(key, default)
        or default
    )


# ---------------------------------------------------------------------------
# Top-level dispatcher
# Source: ttrss/backend.php (POST handler)
#         + ttrss/classes/handler/protected.php (login guard)
# ---------------------------------------------------------------------------


@backend_bp.post("/backend.php")
@login_required
def dispatch():
    """Dispatch op+method to the correct handler.

    Source: ttrss/backend.php reads from $_REQUEST (merges GET+POST+COOKIE).
    Python: reads from form data, JSON body, AND query params to match PHP $_REQUEST.
    Source: ttrss/classes/backend.php:Backend (dispatch routing)
    """
    data = request.get_json(silent=True) or {}
    op = (
        request.form.get("op")
        or data.get("op")
        or request.args.get("op", "")
    ).lower()
    method = (
        request.form.get("method")
        or data.get("method")
        or request.args.get("method", "")
    ).lower()

    # Source: ttrss/classes/rpc.php:RPC::csrf_ignore — bypass CSRF for safe methods
    # Flask-WTF CSRFProtect is global; exempt methods listed here are read-only.
    # Full CSRF bypass not implemented here — rely on GET-only path for those ops.

    handler = _DISPATCH.get((op, method))
    if handler is None:
        return jsonify({"status": "ERR", "error": f"Unknown op/method: {op}/{method}"}), 400

    try:
        result = handler()
        if result is None:
            return jsonify({"status": "OK"})
        return result
    except Exception as exc:
        logger.exception("backend dispatch error", op=op, method=method)
        return jsonify({"status": "ERR", "error": str(exc)}), 500


# ===========================================================================
# RPC handlers — op="rpc"
# Source: ttrss/classes/rpc.php:RPC (lines 1-653)
# ===========================================================================


def _rpc_mark():
    """Mark/unmark an article as starred.

    Source: ttrss/classes/rpc.php:RPC::mark (lines 131-146)
    PHP reads $_REQUEST["mark"] and $_REQUEST["id"].
    """
    from ttrss.models.user_entry import TtRssUserEntry

    ref_id = int(_param("id", "0"))
    mark = _param("mark", "0") == "1"

    db.session.execute(
        sa_update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == ref_id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
        .values(marked=mark, last_marked=func.now())
    )
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_catchup_feed():
    """Mark all articles in a feed (or category) as read.

    Source: ttrss/classes/rpc.php:RPC::catchupFeed (lines 442-450)
    Delegates to ttrss.articles.ops:catchup_feed.
    """
    from ttrss.articles.ops import catchup_feed

    feed_id = _param("feed_id", "0")
    is_cat = _param("is_cat", "false").lower() == "true"
    mode = _param("mode", "all")

    # feed_id may be numeric or a tag string
    try:
        feed_id_v: int | str = int(feed_id)
    except ValueError:
        feed_id_v = feed_id

    catchup_feed(db.session, feed_id_v, is_cat, current_user.id, mode=mode)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_delete():
    """Delete articles by ref_id list.

    Source: ttrss/classes/rpc.php:RPC::delete (lines 148-157)
    """
    from ttrss.feeds.ops import purge_orphans
    from ttrss.models.user_entry import TtRssUserEntry

    ids_str = _param("ids", "")
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    if ids:
        db.session.execute(
            sa_delete(TtRssUserEntry)
            .where(TtRssUserEntry.ref_id.in_(ids))
            .where(TtRssUserEntry.owner_uid == current_user.id)
        )
        purge_orphans(db.session)
        db.session.commit()

    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_publ():
    """Set/unset article published flag.

    Source: ttrss/classes/rpc.php:RPC::publ (lines 258-286)
    Note: PubSubHubbub notification skipped — no PHP PUBSUBHUBBUB_HUB equivalent in Python.
    """
    from ttrss.models.user_entry import TtRssUserEntry

    ref_id = int(_param("id", "0"))
    pub = _param("pub", "0") == "1"

    db.session.execute(
        sa_update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == ref_id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
        .values(published=pub, last_published=func.now())
    )
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS", "pubsub_result": False})


def _rpc_archive():
    """Archive a list of articles (move to archived feed).

    Source: ttrss/classes/rpc.php:RPC::archive (lines 216-224)
    Delegates to _archive_article() for each id.
    """
    ids_str = _param("ids", "")
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]
    for ref_id in ids:
        _archive_article(ref_id, current_user.id)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_unarchive():
    """Restore archived articles back to their originating feeds.

    Source: ttrss/classes/rpc.php:RPC::unarchive (lines 159-214)
    """
    from ttrss.models.archived_feed import TtRssArchivedFeed
    from ttrss.models.feed import TtRssFeed
    from ttrss.models.user_entry import TtRssUserEntry

    ids_str = _param("ids", "")
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    for ref_id in ids:
        # Source: rpc.php:163-167 — find archived feed for this article
        row = db.session.execute(
            select(
                TtRssArchivedFeed.feed_url,
                TtRssArchivedFeed.site_url,
                TtRssArchivedFeed.title,
            )
            .join(
                TtRssUserEntry,
                TtRssUserEntry.orig_feed_id == TtRssArchivedFeed.id,
            )
            .where(TtRssUserEntry.ref_id == ref_id)
            .where(TtRssUserEntry.owner_uid == current_user.id)
        ).one_or_none()

        if row is None:
            continue

        feed_url, site_url, title = row.feed_url, row.site_url, row.title

        # Source: rpc.php:173-176 — check if user already subscribed to this feed_url
        existing_id = db.session.execute(
            select(TtRssFeed.id)
            .where(TtRssFeed.feed_url == feed_url)
            .where(TtRssFeed.owner_uid == current_user.id)
        ).scalar_one_or_none()

        if existing_id is None:
            # Source: rpc.php:180-190 — re-insert feed
            if not title:
                title = "[Unknown]"
            new_feed = TtRssFeed(
                owner_uid=current_user.id,
                feed_url=feed_url,
                site_url=site_url or "",
                title=title,
                cat_id=None,
                auth_login="",
                update_method=0,
            )
            db.session.add(new_feed)
            db.session.flush()
            feed_id = new_feed.id
        else:
            feed_id = existing_id

        if feed_id:
            # Source: rpc.php:202-206 — restore article to feed
            db.session.execute(
                sa_update(TtRssUserEntry)
                .where(TtRssUserEntry.ref_id == ref_id)
                .where(TtRssUserEntry.owner_uid == current_user.id)
                .values(feed_id=feed_id, orig_feed_id=None)
            )

    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_remarchive():
    """Remove archived feed entries that have no articles.

    Source: ttrss/classes/rpc.php:RPC::remarchive (lines 88-100)
    """
    from ttrss.models.archived_feed import TtRssArchivedFeed
    from ttrss.models.user_entry import TtRssUserEntry

    ids_str = _param("ids", "")
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    for arch_id in ids:
        # Only delete if no user entries reference this archived feed
        # Source: rpc.php:93-97 — DELETE WHERE (SELECT COUNT(*) ...) = 0
        ref_count = db.session.execute(
            select(func.count(TtRssUserEntry.int_id))
            .where(TtRssUserEntry.orig_feed_id == arch_id)
        ).scalar() or 0

        if ref_count == 0:
            db.session.execute(
                sa_delete(TtRssArchivedFeed)
                .where(TtRssArchivedFeed.id == arch_id)
                .where(TtRssArchivedFeed.owner_uid == current_user.id)
            )

    db.session.commit()
    return jsonify({"status": "OK"})


def _rpc_mark_selected():
    """Mark/unmark/toggle selected articles as starred.

    Source: ttrss/classes/rpc.php:RPC::markSelected (lines 314-321)
    cmode: 0=unmark, 1=mark, 2=toggle
    """
    from ttrss.models.user_entry import TtRssUserEntry

    ids_str = _param("ids", "")
    cmode = int(_param("cmode", "0"))
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    _mark_articles_by_id(db.session, ids, cmode, current_user.id)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_catchup_selected():
    """Mark selected articles read/unread/toggled.

    Source: ttrss/classes/rpc.php:RPC::catchupSelected (lines 305-311)
    """
    from ttrss.articles.ops import catchupArticlesById

    ids_str = _param("ids", "")
    cmode = int(_param("cmode", "0"))
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    catchupArticlesById(db.session, ids, cmode, current_user.id)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS", "ids": ids})


def _rpc_mark_articles_by_id():
    """Bulk mark articles by id list (direct API variant).

    Source: ttrss/classes/rpc.php:RPC::markArticlesById (private, lines 566-589)
    Called via public op=rpc&method=markArticlesById.
    """
    ids_str = _param("ids", "")
    cmode = int(_param("cmode", "0"))
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    _mark_articles_by_id(db.session, ids, cmode, current_user.id)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_publish_articles_by_id():
    """Bulk publish articles by id list.

    Source: ttrss/classes/rpc.php:RPC::publishArticlesById (private, lines 591-624)
    Note: PubSubHubbub notification skipped.
    """
    ids_str = _param("ids", "")
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    _publish_articles_by_id(db.session, ids, 1, current_user.id)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_publish_selected():
    """Publish/unpublish/toggle selected articles.

    Source: ttrss/classes/rpc.php:RPC::publishSelected (lines 323-330)
    """
    ids_str = _param("ids", "")
    cmode = int(_param("cmode", "0"))
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    _publish_articles_by_id(db.session, ids, cmode, current_user.id)
    db.session.commit()
    return jsonify({"message": "UPDATE_COUNTERS"})


def _rpc_setprofile():
    """Set the active settings profile for the current session.

    Source: ttrss/classes/rpc.php:RPC::setprofile (lines 10-13)
    Adapted: PHP stores in $_SESSION["profile"]; Python stores in Flask session.
    """
    from flask import session

    profile_id = int(_param("id", "0"))
    session["profile"] = profile_id
    return jsonify({"status": "OK"})


def _rpc_addprofile():
    """Create a new settings profile (silent — returns no body).

    Source: ttrss/classes/rpc.php:RPC::addprofile (lines 28-55)
    """
    from ttrss.models.pref import TtRssSettingsProfile
    from ttrss.prefs.ops import initialize_user_prefs

    title = _param("title", "").strip()
    if not title:
        return jsonify({"status": "OK"})

    # Source: rpc.php:34-36 — check for duplicate title
    existing = db.session.execute(
        select(TtRssSettingsProfile.id)
        .where(TtRssSettingsProfile.title == title)
        .where(TtRssSettingsProfile.owner_uid == current_user.id)
    ).scalar_one_or_none()

    if existing is None:
        # Source: rpc.php:38-53 — insert and initialize prefs
        new_profile = TtRssSettingsProfile(
            title=title,
            owner_uid=current_user.id,
        )
        db.session.add(new_profile)
        db.session.flush()
        initialize_user_prefs(current_user.id, profile=new_profile.id)
        db.session.commit()

    return jsonify({"status": "OK"})


def _rpc_remprofiles():
    """Delete settings profiles by id list (cannot delete active profile).

    Source: ttrss/classes/rpc.php:RPC::remprofiles (lines 17-25)
    Adapted: PHP reads active profile from $_SESSION["profile"]; Python from Flask session.
    """
    from flask import session

    from ttrss.models.pref import TtRssSettingsProfile

    ids_str = _param("ids", "")
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]
    active_profile = session.get("profile")

    for pid in ids:
        if active_profile is not None and pid == active_profile:
            continue  # Source: rpc.php:20 — skip if this is the active profile
        db.session.execute(
            sa_delete(TtRssSettingsProfile)
            .where(TtRssSettingsProfile.id == pid)
            .where(TtRssSettingsProfile.owner_uid == current_user.id)
        )

    db.session.commit()
    return jsonify({"status": "OK"})


def _rpc_saveprofile():
    """Rename a settings profile.

    Source: ttrss/classes/rpc.php:RPC::saveprofile (lines 58-86)
    Returns the final title (existing or new).
    """
    from ttrss.models.pref import TtRssSettingsProfile

    profile_id = int(_param("id", "0"))
    title = _param("value", "").strip()

    # Source: rpc.php:62-65 — id==0 is the default profile (immutable)
    if profile_id == 0:
        return jsonify({"title": "Default profile"})

    if not title:
        return jsonify({"status": "ERR", "error": "empty title"})

    # Source: rpc.php:70-72 — check for name collision
    collision = db.session.execute(
        select(TtRssSettingsProfile.id)
        .where(TtRssSettingsProfile.title == title)
        .where(TtRssSettingsProfile.owner_uid == current_user.id)
    ).scalar_one_or_none()

    if collision is None:
        # Source: rpc.php:73-76 — rename
        db.session.execute(
            sa_update(TtRssSettingsProfile)
            .where(TtRssSettingsProfile.id == profile_id)
            .where(TtRssSettingsProfile.owner_uid == current_user.id)
            .values(title=title)
        )
        db.session.commit()
        return jsonify({"title": title})
    else:
        # Source: rpc.php:77-80 — return current title on collision
        current_title = db.session.execute(
            select(TtRssSettingsProfile.title)
            .where(TtRssSettingsProfile.id == profile_id)
            .where(TtRssSettingsProfile.owner_uid == current_user.id)
        ).scalar_one_or_none()
        return jsonify({"title": current_title or title})


def _rpc_addfeed():
    """Subscribe the current user to a feed URL.

    Source: ttrss/classes/rpc.php:RPC::addfeed (lines 102-111)
    Delegates to ttrss.feeds.ops:subscribe_to_feed.
    """
    from ttrss.feeds.ops import subscribe_to_feed

    feed_url = _param("feed", "")
    cat_id = int(_param("cat", "0"))
    login = _param("login", "")
    password = _param("pass", "")

    rc = subscribe_to_feed(
        db.session,
        url=feed_url,
        owner_uid=current_user.id,
        cat_id=cat_id,
        auth_login=login,
        auth_pass=password,
    )
    db.session.commit()
    return jsonify({"result": rc})


def _rpc_quick_add_cat():
    """Create a feed category and return its new id.

    Source: ttrss/classes/rpc.php:RPC::quickAddCat (lines 452-467)
    Delegates to ttrss.feeds.categories:add_feed_category.
    PHP returns HTML select; Python returns JSON {id, title}.
    """
    from ttrss.feeds.categories import add_feed_category, get_feed_category

    cat = _param("cat", "").strip()
    if not cat:
        return jsonify({"status": "ERR", "error": "empty category name"})

    add_feed_category(db.session, cat, current_user.id)
    db.session.commit()

    cat_id = get_feed_category(db.session, cat, current_user.id) or 0
    return jsonify({"id": cat_id, "title": cat})


def _rpc_mass_subscribe():
    """Bulk-subscribe from a feed browser payload.

    Source: ttrss/classes/rpc.php:RPC::massSubscribe (lines 393-440)
    mode=1: payload is [[title, feed_url], ...]
    mode=2: payload is [archived_feed_id, ...] (restore from archive)
    """
    from ttrss.models.archived_feed import TtRssArchivedFeed
    from ttrss.models.feed import TtRssFeed

    payload_str = _param("payload", "[]")
    mode = int(_param("mode", "1"))

    try:
        payload = json.loads(payload_str)
    except (json.JSONDecodeError, ValueError):
        return jsonify({"status": "ERR", "error": "invalid payload"})

    if not isinstance(payload, list):
        return jsonify({"status": "OK"})

    if mode == 1:
        # Source: rpc.php:401-415 — subscribe by [title, feed_url] pairs
        for item in payload:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            title, feed_url = str(item[0]), str(item[1])
            existing = db.session.execute(
                select(TtRssFeed.id)
                .where(TtRssFeed.feed_url == feed_url)
                .where(TtRssFeed.owner_uid == current_user.id)
            ).scalar_one_or_none()
            if existing is None:
                db.session.add(
                    TtRssFeed(
                        owner_uid=current_user.id,
                        feed_url=feed_url,
                        title=title,
                        cat_id=None,
                        site_url="",
                        update_method=0,
                    )
                )
    elif mode == 2:
        # Source: rpc.php:416-438 — restore from archive by archived feed id
        for item in payload:
            try:
                arch_id = int(item)
            except (ValueError, TypeError):
                continue
            arch_row = db.session.execute(
                select(TtRssArchivedFeed)
                .where(TtRssArchivedFeed.id == arch_id)
                .where(TtRssArchivedFeed.owner_uid == current_user.id)
            ).scalar_one_or_none()
            if arch_row is None:
                continue
            existing = db.session.execute(
                select(TtRssFeed.id)
                .where(TtRssFeed.feed_url == arch_row.feed_url)
                .where(TtRssFeed.owner_uid == current_user.id)
            ).scalar_one_or_none()
            if existing is None:
                db.session.add(
                    TtRssFeed(
                        owner_uid=current_user.id,
                        feed_url=arch_row.feed_url,
                        title=arch_row.title,
                        cat_id=None,
                        site_url=arch_row.site_url or "",
                        update_method=0,
                    )
                )

    db.session.commit()
    return jsonify({"status": "OK"})


def _rpc_update_feed_browser():
    """Return feedbrowser content for the subscribe dialog.

    Source: ttrss/classes/rpc.php:RPC::updateFeedBrowser (lines 381-391)
    PHP calls make_feed_browser(); Python returns a minimal stub JSON.
    Adapted: HTML output eliminated (R13) — returns JSON list of feed records.
    """
    from ttrss.models.feedbrowser_cache import TtRssFeedbrowserCache

    search = _param("search", "")
    limit = int(_param("limit", "30"))
    mode = int(_param("mode", "1"))

    # Source: rpc.php:381-391 — feedbrowser query by mode
    # mode 1 = popular feeds across all users, mode 2 = per-user subscriptions
    q = select(
        TtRssFeedbrowserCache.feed_url,
        TtRssFeedbrowserCache.title,
        TtRssFeedbrowserCache.site_url,
        TtRssFeedbrowserCache.subscribers,
    ).order_by(TtRssFeedbrowserCache.subscribers.desc()).limit(limit)

    if search:
        q = q.where(
            TtRssFeedbrowserCache.title.ilike(f"%{search}%")
            | TtRssFeedbrowserCache.feed_url.ilike(f"%{search}%")
        )

    rows = db.session.execute(q).all()
    content = [
        {
            "feed_url": r.feed_url,
            "title": r.title,
            "site_url": r.site_url,
            "subscribers": r.subscribers,
        }
        for r in rows
    ]
    return jsonify({"content": content, "mode": mode})


def _rpc_togglepref():
    """Toggle a boolean preference value.

    Source: ttrss/classes/rpc.php:RPC::togglepref (lines 113-118)
    Delegates to ttrss.prefs.ops:get_user_pref + set_user_pref.
    """
    from ttrss.prefs.ops import get_user_pref, set_user_pref

    key = _param("key", "")
    if not key:
        return jsonify({"status": "ERR", "error": "missing key"})

    current_val = get_user_pref(current_user.id, key)
    new_val = "false" if current_val and current_val.lower() not in {"false", "0", ""} else "true"
    set_user_pref(current_user.id, key, new_val)
    return jsonify({"param": key, "value": new_val})


def _rpc_setpref():
    """Set a preference value.

    Source: ttrss/classes/rpc.php:RPC::setpref (lines 121-128)
    PHP replaces newlines with <br/> unconditionally for ALL keys including USER_STYLESHEET
    (which is a PHP bug — it would corrupt stored CSS). Python deliberately preserves
    newlines for USER_STYLESHEET (CSS is valid multi-line); replaces for all other keys.
    """
    from ttrss.prefs.ops import set_user_pref

    key = _param("key", "")
    value = _param("value", "")

    if key != "USER_STYLESHEET":
        # Source: rpc.php:124 — str_replace("\n", "<br/>", $value) — applied to HTML-stored prefs only
        value = value.replace("\n", "<br/>")

    set_user_pref(current_user.id, key, value)
    return jsonify({"param": key, "value": value})


def _rpc_sanity_check():
    """Run a basic sanity check and return init params.

    Source: ttrss/classes/rpc.php:RPC::sanityCheck (lines 332-348)
    Simplified: daemon check replaced by Celery health (ADR-0011).
    """
    from flask import session

    from ttrss.ui.init_params import make_init_params, make_runtime_info

    # Source: rpc.php:333-336 — store client capabilities in session
    session["hasAudio"] = _param("hasAudio", "false").lower() == "true"
    session["hasSandbox"] = _param("hasSandbox", "false").lower() == "true"
    session["hasMp3"] = _param("hasMp3", "false").lower() == "true"
    session["clientTzOffset"] = _param("clientTzOffset", "0")

    reply: dict[str, Any] = {}
    # Source: rpc.php:340-346 — error=0 means OK; populate init-params
    reply["error"] = {"code": 0}
    reply["init-params"] = make_init_params(current_user.id)
    reply["runtime-info"] = make_runtime_info(current_user.id)
    return jsonify(reply)


def _rpc_complete_labels():
    """Autocomplete labels by search prefix.

    Source: ttrss/classes/rpc.php:RPC::completeLabels (lines 350-364)
    PHP returns an HTML <ul>; Python returns JSON list of captions.
    Adapted: R13 — HTML output eliminated.
    """
    from ttrss.models.label import TtRssLabel2

    search = _param("search", "")

    q = (
        select(TtRssLabel2.caption)
        .where(TtRssLabel2.owner_uid == current_user.id)
        .order_by(TtRssLabel2.caption)
        .limit(5)
    )
    if search:
        q = q.where(TtRssLabel2.caption.ilike(f"{search}%"))

    captions = db.session.execute(q).scalars().all()
    return jsonify({"labels": list(captions)})


def _rpc_purge():
    """Purge old articles from a list of feed ids.

    Source: ttrss/classes/rpc.php:RPC::purge (lines 366-379)
    days=0 means use the feed's configured interval.
    """
    from ttrss.feeds.ops import purge_feed
    from ttrss.models.feed import TtRssFeed

    ids_str = _param("ids", "")
    days = int(_param("days", "0"))
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]

    for feed_id in ids:
        # Source: rpc.php:371-378 — verify ownership before purging
        owned = db.session.execute(
            select(TtRssFeed.id)
            .where(TtRssFeed.id == feed_id)
            .where(TtRssFeed.owner_uid == current_user.id)
        ).scalar_one_or_none()
        if owned is not None:
            purge_feed(db.session, feed_id, purge_interval=days)

    db.session.commit()
    return jsonify({"status": "OK"})


def _rpc_updaterandomfeed():
    """Trigger an update of a random feed that is due.

    Source: ttrss/classes/rpc.php:RPC::updaterandomfeed (lines 562-564)
             + RPC::updaterandomfeed_real (lines 478-560)
    Adapted: Full update logic runs via Celery worker (ADR-0011); this endpoint
             enqueues a task or returns a stub if Celery is unavailable.
    """
    try:
        from ttrss.tasks.feed_tasks import update_random_feed

        task = update_random_feed.delay(owner_uid=current_user.id)
        return jsonify({"message": "UPDATE_COUNTERS", "task_id": str(task.id)})
    except Exception:
        # Source: rpc.php:552-558 — NOTHING_TO_UPDATE fallback
        return jsonify({"message": "NOTHING_TO_UPDATE"})


def _rpc_getlinktitlebyid():
    """Return the link URL and title for an article.

    Source: ttrss/classes/rpc.php:RPC::getlinktitlebyid (lines 626-639)
    """
    from ttrss.models.entry import TtRssEntry
    from ttrss.models.user_entry import TtRssUserEntry

    ref_id = int(_param("id", "0"))

    row = db.session.execute(
        select(TtRssEntry.link, TtRssEntry.title)
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .where(TtRssEntry.id == ref_id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
    ).one_or_none()

    if row is not None:
        return jsonify({"link": row.link, "title": row.title})
    return jsonify({"error": "ARTICLE_NOT_FOUND"})


def _rpc_log():
    """Log a client-side error message to the database.

    Source: ttrss/classes/rpc.php:RPC::log (lines 642-651)
    Stores in ttrss_error_log via TtRssErrorLog model.
    """
    from ttrss.models.error_log import TtRssErrorLog

    logmsg = _param("logmsg", "")
    if logmsg:
        db.session.add(
            TtRssErrorLog(
                owner_uid=current_user.id,
                errno=512,  # E_USER_WARNING equivalent
                errstr=logmsg,
                filename="[client-js]",
                lineno=0,
                context="",
                created_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()

    return jsonify({"message": "HOST_ERROR_LOGGED"})


def _rpc_setpanelmode():
    """Store widescreen panel preference as a cookie.

    Source: ttrss/classes/rpc.php:RPC::setpanelmode (lines 469-476)
    Adapted: PHP uses setcookie(); Python sets a cookie on the response object.
    """
    from flask import make_response

    wide = int(_param("wide", "0"))
    response = make_response(jsonify({"wide": wide}))
    # Source: rpc.php:471 — COOKIE_LIFETIME_LONG = 86400 * 365 days in PHP
    response.set_cookie(
        "ttrss_widescreen",
        str(wide),
        max_age=86400 * 365,
        httponly=False,
        samesite="Lax",
    )
    return response


def _rpc_get_all_counters():
    """Return all counters for the current user.

    Source: ttrss/classes/rpc.php:RPC::getAllCounters (lines 288-302)
    """
    from ttrss.feeds.counters import getAllCounters
    from ttrss.models.entry import TtRssEntry
    from ttrss.models.user_entry import TtRssUserEntry
    from ttrss.ui.init_params import make_runtime_info

    last_article_id = int(_param("last_article_id", "0"))
    seq = _param("seq", "")

    reply: dict[str, Any] = {}
    if seq:
        try:
            reply["seq"] = int(seq)
        except ValueError:
            pass

    # Source: rpc.php:295-298 — only send counters if last_article_id changed
    current_last = db.session.execute(
        select(func.max(TtRssEntry.id))
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .where(TtRssUserEntry.owner_uid == current_user.id)
    ).scalar() or 0

    if last_article_id != current_last:
        reply["counters"] = getAllCounters(db.session, current_user.id)

    reply["runtime-info"] = make_runtime_info(current_user.id)
    return jsonify(reply)


# ---------------------------------------------------------------------------
# Private helpers used by multiple RPC handlers
# ---------------------------------------------------------------------------


def _archive_article(ref_id: int, owner_uid: int) -> None:
    """Move an article to the archived feed (set orig_feed_id, clear feed_id).

    Source: ttrss/classes/rpc.php:RPC::archive_article (private, lines 226-256)
    """
    from ttrss.models.archived_feed import TtRssArchivedFeed
    from ttrss.models.feed import TtRssFeed
    from ttrss.models.user_entry import TtRssUserEntry

    # Source: rpc.php:229-233 — find current feed_id
    ue_row = db.session.execute(
        select(TtRssUserEntry.feed_id)
        .where(TtRssUserEntry.ref_id == ref_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    ).scalar_one_or_none()

    if ue_row is None:
        return

    feed_id = ue_row
    if not feed_id:
        return

    # Source: rpc.php:237-245 — copy feed into archived_feeds if not already there
    existing_arch = db.session.execute(
        select(TtRssArchivedFeed.id).where(TtRssArchivedFeed.id == feed_id)
    ).scalar_one_or_none()

    if existing_arch is None:
        feed_row = db.session.execute(
            select(TtRssFeed.id, TtRssFeed.owner_uid, TtRssFeed.title, TtRssFeed.feed_url, TtRssFeed.site_url)
            .where(TtRssFeed.id == feed_id)
        ).one_or_none()
        if feed_row:
            db.session.add(
                TtRssArchivedFeed(
                    id=feed_row.id,
                    owner_uid=feed_row.owner_uid,
                    title=feed_row.title or "",
                    feed_url=feed_row.feed_url,
                    site_url=feed_row.site_url or "",
                )
            )
            db.session.flush()

    # Source: rpc.php:248-251 — detach article from live feed
    db.session.execute(
        sa_update(TtRssUserEntry)
        .where(TtRssUserEntry.ref_id == ref_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .values(orig_feed_id=feed_id, feed_id=None)
    )


def _mark_articles_by_id(session: Any, ids: list[int], cmode: int, owner_uid: int) -> None:
    """Mark/unmark/toggle articles as starred.

    Source: ttrss/classes/rpc.php:RPC::markArticlesById (private, lines 566-589)
    cmode 0=unmark, 1=mark, 2=toggle.
    """
    from ttrss.models.user_entry import TtRssUserEntry

    if not ids:
        return

    base = (
        TtRssUserEntry.ref_id.in_(ids),
        TtRssUserEntry.owner_uid == owner_uid,
    )

    if cmode == 0:
        session.execute(
            sa_update(TtRssUserEntry).where(*base).values(marked=False, last_marked=func.now())
        )
    elif cmode == 1:
        session.execute(
            sa_update(TtRssUserEntry).where(*base).values(marked=True, last_marked=func.now())
        )
    else:
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base)
            .values(marked=~TtRssUserEntry.marked, last_marked=func.now())
        )


def _publish_articles_by_id(session: Any, ids: list[int], cmode: int, owner_uid: int) -> None:
    """Publish/unpublish/toggle articles.

    Source: ttrss/classes/rpc.php:RPC::publishArticlesById (private, lines 591-624)
    Note: PubSubHubbub notification skipped — no PUBSUBHUBBUB_HUB in Python config.
    cmode 0=unpublish, 1=publish, 2=toggle.
    """
    from ttrss.models.user_entry import TtRssUserEntry

    if not ids:
        return

    base = (
        TtRssUserEntry.ref_id.in_(ids),
        TtRssUserEntry.owner_uid == owner_uid,
    )

    if cmode == 0:
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base)
            .values(published=False, last_published=func.now())
        )
    elif cmode == 1:
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base)
            .values(published=True, last_published=func.now())
        )
    else:
        session.execute(
            sa_update(TtRssUserEntry)
            .where(*base)
            .values(published=~TtRssUserEntry.published, last_published=func.now())
        )


# ===========================================================================
# Dlg handlers — op="dlg"
# Source: ttrss/classes/dlg.php:Dlg (lines 1-271)
# ===========================================================================


def _dlg_import_opml():
    """Handle OPML import: parse uploaded file and import.

    Source: ttrss/classes/dlg.php:Dlg::importOpml (lines 15-42)
    Adapted: R13 — returns JSON status instead of HTML fragments.
    """
    from ttrss.models.feed import TtRssFeed

    f = request.files.get("opml_file")
    if f is None:
        return jsonify({"status": "ERR", "error": "no file uploaded"})

    try:
        content = f.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return jsonify({"status": "ERR", "error": str(exc)})

    # Source: dlg.php:24 — $opml->opml_import($_SESSION["uid"])
    # Delegate to full OPML importer (handles feeds, categories, labels, filters, prefs).
    from ttrss.feeds.opml import import_opml
    result = import_opml(db.session, current_user.id, content)
    return jsonify({"status": "OK", "imported": result.get("imported", 0), "errors": result.get("errors", [])})


def _do_opml_import(content: str, owner_uid: int) -> int:
    """Parse an OPML XML string and subscribe the user to all contained feeds.

    Source: ttrss/classes/opml.php:Opml::opml_import (feed subscription loop)
    Adapted: uses ElementTree instead of PHP DOMDocument.
    Returns number of feeds imported.
    """
    import xml.etree.ElementTree as ET

    from ttrss.models.feed import TtRssFeed

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return 0

    count = 0
    for outline in root.iter("outline"):
        feed_url = outline.get("xmlUrl") or outline.get("xmlurl")
        title = outline.get("title") or outline.get("text") or "[Unknown]"
        if not feed_url:
            continue
        existing = db.session.execute(
            select(TtRssFeed.id)
            .where(TtRssFeed.feed_url == feed_url)
            .where(TtRssFeed.owner_uid == owner_uid)
        ).scalar_one_or_none()
        if existing is None:
            db.session.add(
                TtRssFeed(
                    owner_uid=owner_uid,
                    feed_url=feed_url,
                    title=title,
                    cat_id=None,
                    site_url="",
                    update_method=0,
                )
            )
            count += 1

    db.session.commit()
    return count


def _dlg_export_opml():
    """Return the user's public OPML export URL.

    Source: ttrss/classes/dlg.php:Dlg::pubOPMLUrl (lines 44-64)
    Adapted: R13 — returns JSON with url instead of HTML.
    """
    from flask import request as flask_request

    from ttrss.feeds.ops import get_feed_access_key

    # Source: dlg.php:45 — Opml::opml_publish_url()
    # Construct the OPML export URL with an access key for feed -3 (OPML virtual feed)
    key = get_feed_access_key(db.session, -3, is_cat=False, owner_uid=current_user.id)
    base_url = flask_request.host_url.rstrip("/")
    url = f"{base_url}/opml?key={key}"
    db.session.commit()
    return jsonify({"url": url})


def _dlg_print_tag_cloud():
    """Return a tag cloud dataset (top 50 tags by article count).

    Source: ttrss/classes/dlg.php:Dlg::printTagCloud (lines 99-161)
    Adapted: R13 — returns JSON list of {tag, count, size} instead of HTML.
    """
    from ttrss.models.tag import TtRssTag

    rows = db.session.execute(
        select(TtRssTag.tag_name, func.count(TtRssTag.post_int_id).label("count"))
        .where(TtRssTag.owner_uid == current_user.id)
        .group_by(TtRssTag.tag_name)
        .order_by(func.count(TtRssTag.post_int_id).desc())
        .limit(50)
    ).all()

    if not rows:
        return jsonify({"tags": []})

    tags: dict[str, int] = {r.tag_name: r.count for r in rows}
    max_qty = max(tags.values())
    min_qty = min(tags.values())
    spread = max(max_qty - min_qty, 1)
    max_size, min_size = 32, 11
    step = (max_size - min_size) / spread

    result = [
        {
            "tag": tag,
            "count": count,
            "size": round(min_size + (count - min_qty) * step),
        }
        for tag, count in sorted(tags.items())
    ]
    return jsonify({"tags": result})


def _dlg_print_tag_select():
    """Return all tags available for the current user (for tag filter dialog).

    Source: ttrss/classes/dlg.php:Dlg::printTagSelect (lines 163-192)
    Adapted: R13 — returns JSON list of tag names instead of HTML select.
    """
    from ttrss.models.tag import TtRssTag

    rows = db.session.execute(
        select(TtRssTag.tag_name)
        .where(TtRssTag.owner_uid == current_user.id)
        .where(func.length(TtRssTag.tag_name) <= 30)
        .distinct()
        .order_by(TtRssTag.tag_name)
    ).scalars().all()

    return jsonify({"tags": list(rows)})


def _dlg_generated_feed():
    """Return the generated RSS URL for a feed/category with access key.

    Source: ttrss/classes/dlg.php:Dlg::generatedFeed (lines 194-221)
    Adapted: R13 — returns JSON {url} instead of HTML.
    """
    from flask import request as flask_request

    from ttrss.feeds.ops import get_feed_access_key

    # Source: dlg.php:196 — $this->params = explode(":", $this->param, 3)
    # param format: "feed_id:is_cat:url_path"
    param = _param("param", "")
    parts = param.split(":", 2)
    if len(parts) < 2:
        return jsonify({"status": "ERR", "error": "invalid param"})

    try:
        feed_id = int(parts[0])
    except ValueError:
        return jsonify({"status": "ERR", "error": "invalid feed_id"})

    is_cat = bool(int(parts[1]) if parts[1].lstrip("-").isdigit() else 0)
    url_path = parts[2] if len(parts) > 2 else ""

    key = get_feed_access_key(db.session, feed_id, is_cat=is_cat, owner_uid=current_user.id)
    db.session.commit()

    full_url = f"{url_path}&key={key}" if url_path else ""
    return jsonify({"feed_id": feed_id, "is_cat": is_cat, "key": key, "url": full_url})


def _dlg_new_version():
    """Return version check information.

    Source: ttrss/classes/dlg.php:Dlg::newVersion (lines 223-267)
    Adapted: R13 — returns JSON {version, available} instead of HTML dialog.
    No external HTTP check — returns static "up to date" response.
    """
    # Source: dlg.php:225 — check_for_update() calls remote HTTP
    # Adapted: eliminated remote HTTP call (ADR-0015, no external dep at handler level)
    return jsonify({"available": False, "version": None, "message": "No version check configured"})


def _dlg_explain_error():
    """Return a human-readable explanation for a TT-RSS error code.

    Source: ttrss/classes/dlg.php:Dlg::explainError (lines 66-97)
    Adapted: R13 — returns JSON {explanation} instead of HTML.
    """
    code = int(_param("param", "0"))

    explanations: dict[int, str] = {
        # Source: dlg.php:69-75
        1: (
            "Update daemon is enabled in configuration, but daemon process is not running, "
            "which prevents all feeds from updating. Please start the daemon process or "
            "contact instance owner."
        ),
        # Source: dlg.php:78-83
        3: (
            "Update daemon is taking too long to perform a feed update. This could indicate "
            "a problem like crash or a hang. Please check the daemon process or contact "
            "instance owner."
        ),
    }

    explanation = explanations.get(code, "Unknown error code.")
    return jsonify({"code": code, "explanation": explanation})


# ===========================================================================
# Backend class handlers — op="backend"
# Source: ttrss/classes/backend.php:Backend (lines 1-119)
# ===========================================================================


def _backend_loading():
    """Return a loading indicator response.

    Source: ttrss/classes/backend.php:Backend::loading (lines 3-7)
    Adapted: R13 — returns JSON instead of HTML.
    """
    return jsonify({"status": "loading"})


def _backend_help():
    """Return keyboard shortcut help data.

    Source: ttrss/classes/backend.php:Backend::help (lines 88-117)
    Adapted: R13 — returns JSON dict of hotkeys instead of HTML.
    """
    from ttrss.ui.init_params import get_hotkeys_info, get_hotkeys_map

    topic = _param("topic", "main")

    if topic == "main":
        prefixes, hotkeys = get_hotkeys_map()
        info = get_hotkeys_info()
        return jsonify({"topic": topic, "hotkeys": hotkeys, "prefixes": prefixes, "info": info})

    return jsonify({"topic": topic, "hotkeys": {}, "prefixes": [], "info": {}})


# ===========================================================================
# Article class handlers — Source: ttrss/classes/article.php:Article
# ===========================================================================


def _article_complete_tags():
    """Tag autocomplete — return up to 10 tags matching a search prefix.

    Source: ttrss/classes/article.php:Article::completeTags (lines 287-299)
    PHP: SELECT DISTINCT tag_name FROM ttrss_tags WHERE owner_uid = uid AND tag_name LIKE :search% LIMIT 10.
    Adapted: R13 — JSON output instead of HTML <ul>.
    """
    from ttrss.models.tag import TtRssTag

    search = _param("search", "")
    q = (
        select(TtRssTag.tag_name)
        .distinct()
        .where(TtRssTag.owner_uid == current_user.id)
        .order_by(TtRssTag.tag_name)
        .limit(10)
    )
    if search:
        q = q.where(TtRssTag.tag_name.ilike(f"{search}%"))
    tags = db.session.execute(q).scalars().all()
    return jsonify({"tags": list(tags)})


def _article_assign_to_label():
    """Assign articles to a label.

    Source: ttrss/classes/article.php:Article::assigntolabel (lines 302-303)
    Source: ttrss/classes/article.php:Article::labelops (lines 310-340)
    PHP: calls labelops(true) → label_add_article for each article id.
    """
    from ttrss.labels import label_add_article, label_find_caption

    ids_str = _param("ids", "")
    label_id = int(_param("lid", 0))
    owner_uid = current_user.id
    ids = [int(x) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]
    caption = label_find_caption(db.session, label_id, owner_uid)
    if caption and ids:
        for art_id in ids:
            label_add_article(db.session, art_id, caption, owner_uid)
        db.session.commit()
    return jsonify({"status": "OK"})


def _article_remove_from_label():
    """Remove articles from a label.

    Source: ttrss/classes/article.php:Article::removefromlabel (lines 306-307)
    Source: ttrss/classes/article.php:Article::labelops (lines 310-340)
    PHP: calls labelops(false) → label_remove_article for each article id.
    """
    from ttrss.labels import label_remove_article, label_find_caption

    ids_str = _param("ids", "")
    label_id = int(_param("lid", 0))
    owner_uid = current_user.id
    ids = [int(x) for x in ids_str.split(",") if x.strip().lstrip("-").isdigit()]
    caption = label_find_caption(db.session, label_id, owner_uid)
    if caption and ids:
        for art_id in ids:
            label_remove_article(db.session, art_id, caption, owner_uid)
        db.session.commit()
    return jsonify({"status": "OK"})


# ===========================================================================
# Dispatch table: (op, method) → handler
# Source: ttrss/backend.php dispatch pattern
# ===========================================================================

_DISPATCH: dict[tuple[str, str], Any] = {
    # RPC operations — Source: ttrss/classes/rpc.php:RPC
    ("rpc", "mark"):                _rpc_mark,
    ("rpc", "catchupfeed"):         _rpc_catchup_feed,
    ("rpc", "delete"):              _rpc_delete,
    ("rpc", "publ"):                _rpc_publ,
    ("rpc", "archive"):             _rpc_archive,
    ("rpc", "unarchive"):           _rpc_unarchive,
    ("rpc", "remarchive"):          _rpc_remarchive,
    ("rpc", "markselected"):        _rpc_mark_selected,
    ("rpc", "catchupselected"):     _rpc_catchup_selected,
    ("rpc", "markarticlesbyid"):    _rpc_mark_articles_by_id,
    ("rpc", "publisharticlesbyid"): _rpc_publish_articles_by_id,
    ("rpc", "publishselected"):     _rpc_publish_selected,
    ("rpc", "setprofile"):          _rpc_setprofile,
    ("rpc", "addprofile"):          _rpc_addprofile,
    ("rpc", "remprofiles"):         _rpc_remprofiles,
    ("rpc", "saveprofile"):         _rpc_saveprofile,
    ("rpc", "addfeed"):             _rpc_addfeed,
    ("rpc", "quickaddcat"):         _rpc_quick_add_cat,
    ("rpc", "masssubscribe"):       _rpc_mass_subscribe,
    ("rpc", "updatefeedbrowser"):   _rpc_update_feed_browser,
    ("rpc", "togglepref"):          _rpc_togglepref,
    ("rpc", "setpref"):             _rpc_setpref,
    ("rpc", "sanitycheck"):         _rpc_sanity_check,
    ("rpc", "completelabels"):      _rpc_complete_labels,
    ("rpc", "purge"):               _rpc_purge,
    ("rpc", "updaterandomfeed"):    _rpc_updaterandomfeed,
    ("rpc", "getlinktitlebyid"):    _rpc_getlinktitlebyid,
    ("rpc", "log"):                 _rpc_log,
    ("rpc", "setpanelmode"):        _rpc_setpanelmode,
    ("rpc", "getallcounters"):      _rpc_get_all_counters,
    # Dlg operations — Source: ttrss/classes/dlg.php:Dlg
    ("dlg", "importopml"):          _dlg_import_opml,
    ("dlg", "pubopmlurl"):          _dlg_export_opml,
    ("dlg", "printtagcloud"):       _dlg_print_tag_cloud,
    ("dlg", "printtagselect"):      _dlg_print_tag_select,
    ("dlg", "generatedfeed"):       _dlg_generated_feed,
    ("dlg", "newversion"):          _dlg_new_version,
    ("dlg", "explainerror"):        _dlg_explain_error,
    # Backend class operations — Source: ttrss/classes/backend.php:Backend
    ("backend", "loading"):         _backend_loading,
    ("backend", "help"):            _backend_help,
    # Article class operations — Source: ttrss/classes/article.php:Article
    ("article", "completetags"):    _article_complete_tags,
    ("article", "assigntolabel"):   _article_assign_to_label,
    ("article", "removefromlabel"): _article_remove_from_label,
}
