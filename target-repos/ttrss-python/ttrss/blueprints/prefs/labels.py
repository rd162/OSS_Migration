"""Pref_Labels handler — label preferences, HOOK_PREFS_TAB.

Source: ttrss/classes/pref/labels.php (Pref_Labels handler, 331 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations
import structlog
from flask import jsonify
from flask_login import login_required

from ttrss.blueprints.prefs.views import prefs_bp

logger = structlog.get_logger(__name__)


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
