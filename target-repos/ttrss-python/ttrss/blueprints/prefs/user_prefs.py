"""Pref_Prefs handler — user preferences, HOOK_PREFS_TAB_SECTION ×3 + HOOK_PREFS_TAB.

Source: ttrss/classes/pref/prefs.php (Pref_Prefs handler, 1129 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         Delegation to prefs.ops per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations
import structlog
from flask import jsonify
from flask_login import current_user, login_required

from ttrss.blueprints.prefs.views import prefs_bp

logger = structlog.get_logger(__name__)


@prefs_bp.route("/user", methods=["GET"])
@login_required
def user_prefs():
    """Return current user preferences with plugin-added sections.

    Source: ttrss/classes/pref/prefs.php:435 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/prefs.php:661 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/prefs.php:697 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/prefs.php:863 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML preference form replaced by JSON payload; AR-2 delegates to prefs.ops.
    """
    from ttrss.plugins.manager import get_plugin_manager
    from ttrss.prefs.ops import get_user_pref
    pm = get_plugin_manager()
    owner_uid: int = current_user.get_id()  # type: ignore[assignment]
    # Source: ttrss/classes/pref/prefs.php:435 — HOOK_PREFS_TAB_SECTION (section 1 of 3)
    # Source: ttrss/classes/pref/prefs.php:661 — HOOK_PREFS_TAB_SECTION (section 2 of 3)
    # Source: ttrss/classes/pref/prefs.php:697 — HOOK_PREFS_TAB_SECTION (section 3 of 3)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/prefs.php:863 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()
    return jsonify({
        "plugin_sections": plugin_sections,
        "plugin_tab_content": plugin_tab_content,
    })
