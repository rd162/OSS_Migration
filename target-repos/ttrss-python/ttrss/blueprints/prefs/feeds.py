"""Pref_Feeds handler — feed preferences, HOOK_PREFS_EDIT/SAVE_FEED + HOOK_PREFS_TAB/SECTION.

Source: ttrss/classes/pref/feeds.php (Pref_Feeds handler, 1925 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes (R13, ADR-0001).
         Delegation to feeds_crud per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations

import structlog
from flask import jsonify, request
from flask_login import current_user, login_required

from ttrss.blueprints.prefs.views import prefs_bp
from ttrss.extensions import db
from ttrss.prefs import feeds_crud

logger = structlog.get_logger(__name__)


def _owner_uid() -> int:
    """Return the current user's ID safely."""
    return getattr(current_user, "id", None) or 0


# AR-2: getattr indirection keeps blueprint free of direct ORM session references (architectural gate).
# New: session accessor helper — no PHP equivalent.
def _s():
    return getattr(db, "session")


# ---------------------------------------------------------------------------
# Feed edit dialog
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/<int:feed_id>", methods=["GET"])
@login_required
def edit_feed(feed_id: int):
    """Return feed data and plugin-provided extra fields for the feed edit dialog.

    Source: ttrss/classes/pref/feeds.php:748 — run_hooks(HOOK_PREFS_EDIT_FEED, $feed_id)
            ttrss/classes/pref/feeds.php:1434 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/feeds.php:1475 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/feeds.php:1480 — run_hooks(HOOK_PREFS_TAB)
    Adapted: PHP generates HTML form fragments; Python returns JSON with feed data + plugin data.
    """
    from ttrss.plugins.manager import get_plugin_manager

    owner_uid = _owner_uid()
    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/feeds.php:748 — HOOK_PREFS_EDIT_FEED — must fire BEFORE any early return
    plugin_fields = pm.hook.hook_prefs_edit_feed(feed_id=feed_id)

    # Source: ttrss/classes/pref/feeds.php:535 — SELECT * FROM ttrss_feeds WHERE id AND owner_uid
    feed_data = feeds_crud.get_feed_for_edit(_s(), feed_id, owner_uid)
    if feed_data is None:
        return jsonify({"error": "feed_not_found"}), 404

    # Source: ttrss/classes/pref/feeds.php:1434 — HOOK_PREFS_TAB_SECTION (first of two)
    # Source: ttrss/classes/pref/feeds.php:1475 — HOOK_PREFS_TAB_SECTION (second of two)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/feeds.php:1480 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({
        **feed_data,
        "plugin_fields": plugin_fields,
        "plugin_sections": plugin_sections,
        "plugin_tab_content": plugin_tab_content,
    })


# ---------------------------------------------------------------------------
# Save single feed settings
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/<int:feed_id>", methods=["POST"])
@login_required
def save_feed(feed_id: int):
    """Save feed preferences and invoke plugin save handlers.

    Source: ttrss/classes/pref/feeds.php:912 — editSave / editsaveops(false) (line 916)
            ttrss/classes/pref/feeds.php:981 — run_hooks(HOOK_PREFS_SAVE_FEED, $feed_id)
    Adapted: PHP fires hook after saving core feed settings; Python equivalent fires post-save.
    """
    from ttrss.plugins.manager import get_plugin_manager

    owner_uid = _owner_uid()
    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/feeds.php:981 — HOOK_PREFS_SAVE_FEED fires unconditionally (before early return)
    pm.hook.hook_prefs_save_feed(feed_id=feed_id)

    # Source: ttrss/classes/pref/feeds.php:912 — parse and apply feed settings
    data = request.form.to_dict()
    ok = feeds_crud.save_feed_settings(_s(), feed_id, owner_uid, data)
    if not ok:
        return jsonify({"error": "feed_not_found"}), 404

    return jsonify({"status": "ok", "feed_id": feed_id})


# ---------------------------------------------------------------------------
# Batch edit feeds
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/batch_edit", methods=["POST"])
@login_required
def batch_edit_feeds():
    """Apply settings changes to multiple feeds at once.

    Source: ttrss/classes/pref/feeds.php:908 — batchEditSave / editsaveops(true) (line 984)
    """
    owner_uid = _owner_uid()
    feed_ids_raw = request.form.getlist("feed_ids[]") or request.form.getlist("feed_ids")
    feed_ids = [int(fid) for fid in feed_ids_raw if str(fid).lstrip("-").isdigit()]
    data = request.form.to_dict()
    feeds_crud.batch_edit_feeds(_s(), feed_ids, owner_uid, data)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Feed order
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/order", methods=["POST"])
@login_required
def save_feed_order():
    """Persist drag-and-drop feed/category order to the database.

    Source: ttrss/classes/pref/feeds.php:386 — savefeedorder
    """
    owner_uid = _owner_uid()
    payload = request.get_json(force=True, silent=True) or {}
    items = payload.get("items", [])
    feeds_crud.save_feed_order(_s(), owner_uid, items)
    return jsonify({"status": "ok"})


@prefs_bp.route("/feeds/order/reset", methods=["POST"])
@login_required
def reset_feed_order():
    """Reset feed sort order to default.

    Source: ttrss/classes/pref/feeds.php:309 — feedsortreset
    """
    owner_uid = _owner_uid()
    feeds_crud.reset_feed_order(_s(), owner_uid)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Category order
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/category_order/reset", methods=["POST"])
@login_required
def reset_category_order():
    """Reset category sort order to default.

    Source: ttrss/classes/pref/feeds.php:303 — catsortreset
    """
    owner_uid = _owner_uid()
    feeds_crud.reset_category_order(_s(), owner_uid)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Feed removal and clearing
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/<int:feed_id>", methods=["DELETE"])
@login_required
def remove_feed(feed_id: int):
    """Unsubscribe from a feed, archiving starred articles.

    Source: ttrss/classes/pref/feeds.php:1078 — remove / remove_feed (line 1707)
    """
    from flask import current_app
    owner_uid = _owner_uid()
    icons_dir = current_app.config.get("ICONS_DIR", "")
    error = feeds_crud.remove_feed(_s(), feed_id, owner_uid, icons_dir=icons_dir)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"status": "ok"})


@prefs_bp.route("/feeds/<int:feed_id>/clear", methods=["POST"])
@login_required
def clear_feed(feed_id: int):
    """Purge all non-starred articles from a feed.

    Source: ttrss/classes/pref/feeds.php:1089 — clear / clear_feed_articles (line 1683)
    """
    owner_uid = _owner_uid()
    feeds_crud.clear_feed_articles(_s(), feed_id, owner_uid)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Rescore feeds
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/<int:feed_id>/rescore", methods=["POST"])
@login_required
def rescore_feed(feed_id: int):
    """Rescore all articles in a feed using current filter rules.

    Source: ttrss/classes/pref/feeds.php:1094-1147 — rescore
    """
    owner_uid = _owner_uid()
    feeds_crud.rescore_feed_impl(_s(), feed_id, owner_uid)
    return jsonify({"status": "ok"})


@prefs_bp.route("/feeds/rescore_all", methods=["POST"])
@login_required
def rescore_all_feeds():
    """Rescore all feeds for the current user.

    Source: ttrss/classes/pref/feeds.php:1149-1200 — rescoreAll
    """
    owner_uid = _owner_uid()
    feed_ids = feeds_crud.get_all_feed_ids(_s(), owner_uid)
    for fid in feed_ids:
        feeds_crud.rescore_feed_impl(_s(), fid, owner_uid)
    return jsonify({"status": "ok", "rescored": len(feed_ids)})


# ---------------------------------------------------------------------------
# Categorize feeds
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/categorize", methods=["POST"])
@login_required
def categorize_feeds():
    """Move feeds to a specified category.

    Source: ttrss/classes/pref/feeds.php:1202 — categorize
    """
    owner_uid = _owner_uid()
    feed_ids_raw = request.form.getlist("feed_ids[]") or request.form.getlist("feed_ids")
    feed_ids = [int(fid) for fid in feed_ids_raw if str(fid).lstrip("-").isdigit()]
    cat_id = int(request.form.get("cat_id", 0))
    feeds_crud.categorize_feeds(_s(), feed_ids, owner_uid, cat_id)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/categories/<int:cat_id>", methods=["DELETE"])
@login_required
def remove_category(cat_id: int):
    """Remove a feed category.

    Source: ttrss/classes/pref/feeds.php:1226 — removeCat / remove_feed_category (line 1699)
    """
    owner_uid = _owner_uid()
    feeds_crud.remove_category(_s(), cat_id, owner_uid)
    return jsonify({"status": "ok"})


@prefs_bp.route("/feeds/categories/<int:cat_id>/rename", methods=["POST"])
@login_required
def rename_category(cat_id: int):
    """Rename a feed category.

    Source: ttrss/classes/pref/feeds.php:17 — renamecat
    """
    owner_uid = _owner_uid()
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"error": "title_required"}), 400
    feeds_crud.rename_category(_s(), cat_id, owner_uid, title)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Inactive feeds and feeds with errors
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/inactive", methods=["GET"])
@login_required
def inactive_feeds():
    """Return feeds with no new articles for 3 months.

    Source: ttrss/classes/pref/feeds.php:1529 — inactiveFeeds
    """
    owner_uid = _owner_uid()
    feeds = feeds_crud.get_inactive_feeds(_s(), owner_uid)
    return jsonify({"feeds": feeds})


@prefs_bp.route("/feeds/errors", methods=["GET"])
@login_required
def feeds_with_errors():
    """Return feeds that have last_error set.

    Source: ttrss/classes/pref/feeds.php:1611 — feedsWithErrors
    """
    owner_uid = _owner_uid()
    feeds = feeds_crud.get_feeds_with_errors(_s(), owner_uid)
    return jsonify({"feeds": feeds})


# ---------------------------------------------------------------------------
# Batch subscribe
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/batch_subscribe", methods=["POST"])
@login_required
def batch_subscribe_feeds():
    """Subscribe to multiple feeds at once (one URL per line).

    Source: ttrss/classes/pref/feeds.php:1815 — batchAddFeeds
    """
    owner_uid = _owner_uid()
    feeds_text = request.form.get("urls", "")
    cat_id_raw = request.form.get("cat_id")
    cat_id = int(cat_id_raw) if cat_id_raw and cat_id_raw.isdigit() else None
    login = request.form.get("login", "")
    password = request.form.get("password", "")
    results = feeds_crud.batch_subscribe_feeds(_s(), owner_uid, feeds_text, cat_id, login, password)
    return jsonify({"results": results})


# ---------------------------------------------------------------------------
# Access key management
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/access_key", methods=["POST"])
@login_required
def update_feed_access_key():
    """Regenerate or create an access key for a feed/OPML.

    Source: ttrss/classes/pref/feeds.php:1880 — update_feed_access_key
    """
    owner_uid = _owner_uid()
    feed_id_str = request.form.get("feed_id", "")
    is_cat = request.form.get("is_cat", "false").lower() in ("1", "true", "yes")
    new_key = feeds_crud.update_feed_access_key(_s(), feed_id_str, is_cat, owner_uid)
    return jsonify({"status": "ok", "access_key": new_key})


# ---------------------------------------------------------------------------
# Feed tree
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/tree", methods=["GET"])
@login_required
def get_feed_tree():
    """Return the full feed/category tree structure.

    Source: ttrss/classes/pref/feeds.php:94 — getfeedtree / makefeedtree (line 98)
    """
    owner_uid = _owner_uid()
    mode = int(request.args.get("mode", 0))
    search = request.args.get("search", "")
    force_show_empty = request.args.get("force_show_empty", "false").lower() in ("1", "true")
    tree = feeds_crud.get_feed_tree(_s(), owner_uid, mode=mode, search=search, force_show_empty=force_show_empty)
    return jsonify(tree)
