"""Pref_Users handler — user management (admin), HOOK_PREFS_TAB_SECTION + HOOK_PREFS_TAB.

Source: ttrss/classes/pref/users.php (Pref_Users handler, 458 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations
import structlog
from flask import jsonify
from flask_login import login_required

from ttrss.blueprints.prefs.views import prefs_bp

logger = structlog.get_logger(__name__)


@prefs_bp.route("/users", methods=["GET"])
@login_required
def users():
    """Return user management data with plugin-added sections (admin only).

    Source: ttrss/classes/pref/users.php:354 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/users.php:449 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML admin panel replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager
    pm = get_plugin_manager()
    # Source: ttrss/classes/pref/users.php:354 — HOOK_PREFS_TAB_SECTION (fire-and-forget, collecting)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/users.php:449 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()
    return jsonify({
        "plugin_sections": plugin_sections,
        "plugin_tab_content": plugin_tab_content,
    })
