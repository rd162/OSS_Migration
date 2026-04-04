"""Pref_Feeds handler — feed preferences, HOOK_PREFS_EDIT/SAVE_FEED + HOOK_PREFS_TAB/SECTION.

Source: ttrss/classes/pref/feeds.php (Pref_Feeds handler, 1925 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes (R13, ADR-0001).
         Delegation to feeds.ops and feeds.categories per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations
import structlog
from flask import jsonify
from flask_login import login_required

from ttrss.blueprints.prefs.views import prefs_bp

logger = structlog.get_logger(__name__)


@prefs_bp.route("/feeds/<int:feed_id>", methods=["GET"])
@login_required
def edit_feed(feed_id: int):
    """Return plugin-provided extra fields for the feed edit dialog.

    Source: ttrss/classes/pref/feeds.php:748 — run_hooks(HOOK_PREFS_EDIT_FEED, $feed_id)
            ttrss/classes/pref/feeds.php:1434 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/feeds.php:1475 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/feeds.php:1480 — run_hooks(HOOK_PREFS_TAB)
    Adapted: PHP generates HTML form fragments; Python returns JSON with plugin data.
    """
    from ttrss.plugins.manager import get_plugin_manager
    pm = get_plugin_manager()
    # Source: ttrss/classes/pref/feeds.php:748 — HOOK_PREFS_EDIT_FEED (fire-and-forget, collecting)
    plugin_fields = pm.hook.hook_prefs_edit_feed(feed_id=feed_id)
    # Source: ttrss/classes/pref/feeds.php:1434 — HOOK_PREFS_TAB_SECTION (first of two)
    # Source: ttrss/classes/pref/feeds.php:1475 — HOOK_PREFS_TAB_SECTION (second of two)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/feeds.php:1480 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()
    return jsonify({
        "feed_id": feed_id,
        "plugin_fields": plugin_fields,
        "plugin_sections": plugin_sections,
        "plugin_tab_content": plugin_tab_content,
    })


@prefs_bp.route("/feeds/<int:feed_id>", methods=["POST"])
@login_required
def save_feed(feed_id: int):
    """Invoke plugin save handlers when feed preferences are saved.

    Source: ttrss/classes/pref/feeds.php:981 — run_hooks(HOOK_PREFS_SAVE_FEED, $feed_id)
    Adapted: PHP fires hook after saving core feed settings; Python equivalent fires post-save.
    """
    from ttrss.plugins.manager import get_plugin_manager
    pm = get_plugin_manager()
    # Source: ttrss/classes/pref/feeds.php:981 — HOOK_PREFS_SAVE_FEED (fire-and-forget, collecting)
    pm.hook.hook_prefs_save_feed(feed_id=feed_id)
    return jsonify({"status": "ok", "feed_id": feed_id})
