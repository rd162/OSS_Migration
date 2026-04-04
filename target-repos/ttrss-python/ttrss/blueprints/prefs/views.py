"""Prefs blueprint — preference UI data endpoints, wiring all HOOK_PREFS_* hooks.

Source: ttrss/prefs.php (main dispatcher)
        ttrss/classes/pref/feeds.php (feed-specific prefs)
        ttrss/classes/pref/filters.php
        ttrss/classes/pref/labels.php
        ttrss/classes/pref/system.php
        ttrss/classes/pref/users.php
Adapted: PHP handler class hierarchy replaced by Flask Blueprint.
         HTML output eliminated — all endpoints return JSON (R13).
         HOOK_PREFS_* hooks fire at the same lifecycle points as PHP run_hooks() calls.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)

prefs_bp = Blueprint("prefs", __name__, url_prefix="/prefs")


# ---------------------------------------------------------------------------
# /prefs/ — main preference tabs page
# Source: ttrss/prefs.php lines 139, 863 — HOOK_PREFS_TABS, HOOK_PREFS_TAB_SECTION, HOOK_PREFS_TAB
# ---------------------------------------------------------------------------


@prefs_bp.route("/", methods=["GET"])
@login_required
def index():
    """Return preference tab structure for the frontend.

    Source: ttrss/prefs.php:139 — run_hooks(HOOK_PREFS_TABS, ...)
            ttrss/prefs.php:863 — run_hooks(HOOK_PREFS_TAB_SECTION) ×3, run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML prefs page replaced by JSON endpoint; plugins extend via hooks.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/prefs.php:139 — HOOK_PREFS_TABS (fire-and-forget, collecting)
    plugin_tabs = pm.hook.hook_prefs_tabs(args={})

    # Source: ttrss/prefs.php:863 — HOOK_PREFS_TAB_SECTION (×3 sections) + HOOK_PREFS_TAB
    plugin_sections = pm.hook.hook_prefs_tab_section()
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify(
        {
            "plugin_tabs": plugin_tabs,
            "plugin_sections": plugin_sections,
            "plugin_tab_content": plugin_tab_content,
        }
    )


# ---------------------------------------------------------------------------
# /prefs/feeds/<feed_id> — feed preference editing
# Source: ttrss/classes/pref/feeds.php lines 748, 981 — HOOK_PREFS_EDIT_FEED, HOOK_PREFS_SAVE_FEED
# ---------------------------------------------------------------------------


@prefs_bp.route("/feeds/<int:feed_id>", methods=["GET"])
@login_required
def edit_feed(feed_id: int):
    """Return plugin-provided extra fields for the feed edit dialog.

    Source: ttrss/classes/pref/feeds.php:748 — run_hooks(HOOK_PREFS_EDIT_FEED, $feed_id)
            ttrss/classes/pref/feeds.php — run_hooks(HOOK_PREFS_TAB_SECTION), run_hooks(HOOK_PREFS_TAB)
    Adapted: PHP generates HTML form fragments; Python returns JSON with plugin data.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/feeds.php:748 — HOOK_PREFS_EDIT_FEED
    plugin_fields = pm.hook.hook_prefs_edit_feed(feed_id=feed_id)

    # Source: ttrss/classes/pref/feeds.php — HOOK_PREFS_TAB_SECTION (×2), HOOK_PREFS_TAB
    plugin_sections = pm.hook.hook_prefs_tab_section()
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify(
        {
            "feed_id": feed_id,
            "plugin_fields": plugin_fields,
            "plugin_sections": plugin_sections,
            "plugin_tab_content": plugin_tab_content,
        }
    )


@prefs_bp.route("/feeds/<int:feed_id>", methods=["POST"])
@login_required
def save_feed(feed_id: int):
    """Invoke plugin save handlers when feed preferences are saved.

    Source: ttrss/classes/pref/feeds.php:981 — run_hooks(HOOK_PREFS_SAVE_FEED, $feed_id)
    Adapted: PHP fires hook after saving core feed settings; Python equivalent fires after
             the save operation is complete.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/feeds.php:981 — HOOK_PREFS_SAVE_FEED (fire-and-forget)
    pm.hook.hook_prefs_save_feed(feed_id=feed_id)

    return jsonify({"status": "ok", "feed_id": feed_id})


# ---------------------------------------------------------------------------
# /prefs/filters — filter preferences tab
# Source: ttrss/classes/pref/filters.php:695 — HOOK_PREFS_TAB
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters", methods=["GET"])
@login_required
def filters():
    """Return plugin-provided content for the filters preferences tab.

    Source: ttrss/classes/pref/filters.php:695 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML tab content replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/filters.php:695 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({"plugin_tab_content": plugin_tab_content})


# ---------------------------------------------------------------------------
# /prefs/labels — label preferences tab
# Source: ttrss/classes/pref/labels.php:322 — HOOK_PREFS_TAB
# ---------------------------------------------------------------------------


@prefs_bp.route("/labels", methods=["GET"])
@login_required
def labels():
    """Return plugin-provided content for the labels preferences tab.

    Source: ttrss/classes/pref/labels.php:322 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML tab content replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/labels.php:322 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({"plugin_tab_content": plugin_tab_content})


# ---------------------------------------------------------------------------
# /prefs/system — system preferences tab
# Source: ttrss/classes/pref/system.php:83 — HOOK_PREFS_TAB
# ---------------------------------------------------------------------------


@prefs_bp.route("/system", methods=["GET"])
@login_required
def system():
    """Return plugin-provided content for the system preferences tab.

    Source: ttrss/classes/pref/system.php:83 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML tab content replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/system.php:83 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({"plugin_tab_content": plugin_tab_content})


# ---------------------------------------------------------------------------
# /prefs/users — user management preferences tab
# Source: ttrss/classes/pref/users.php:449 — HOOK_PREFS_TAB_SECTION, HOOK_PREFS_TAB
# ---------------------------------------------------------------------------


@prefs_bp.route("/users", methods=["GET"])
@login_required
def users():
    """Return plugin-provided content for the users preferences tab.

    Source: ttrss/classes/pref/users.php:449 — run_hooks(HOOK_PREFS_TAB_SECTION),
                                                run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML tab content replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/users.php:449 — HOOK_PREFS_TAB_SECTION (fire-and-forget, collecting)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/users.php:449 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify(
        {
            "plugin_sections": plugin_sections,
            "plugin_tab_content": plugin_tab_content,
        }
    )
