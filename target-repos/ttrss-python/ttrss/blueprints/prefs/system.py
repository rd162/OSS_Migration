"""Pref_System handler — system preferences, HOOK_PREFS_TAB.

Source: ttrss/classes/pref/system.php (Pref_System handler, 91 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations
import structlog
from flask import jsonify
from flask_login import login_required

from ttrss.blueprints.prefs.views import prefs_bp

logger = structlog.get_logger(__name__)


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
