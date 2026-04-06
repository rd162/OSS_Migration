"""Top-level prefs dispatcher — /prefs/ route, HOOK_PREFS_TABS.

Source: ttrss/prefs.php (main prefs dispatcher, lines 1-159)
Adapted: PHP Prefs class replaced by Flask Blueprint (R13, ADR-0001).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations
import structlog
from flask import Blueprint, jsonify
from flask_login import login_required

from ttrss.extensions import csrf

logger = structlog.get_logger(__name__)

prefs_bp = Blueprint("prefs", __name__, url_prefix="/prefs")

# New: csrf.exempt required because the JS prefsRequest() helper does not send a CSRF token.
# The endpoint is protected by @login_required + SameSite=Lax cookie (spec/06-security.md, R13).
csrf.exempt(prefs_bp)

# Import sub-handler routes to register them on prefs_bp
import ttrss.blueprints.prefs.feeds  # noqa: F401, E402
import ttrss.blueprints.prefs.filters  # noqa: F401, E402
import ttrss.blueprints.prefs.labels  # noqa: F401, E402
import ttrss.blueprints.prefs.system  # noqa: F401, E402
import ttrss.blueprints.prefs.user_prefs  # noqa: F401, E402
import ttrss.blueprints.prefs.users  # noqa: F401, E402


@prefs_bp.route("/", methods=["GET"])
@login_required
def index():
    """Return preference tab structure including plugin-added tabs.

    Source: ttrss/prefs.php:139 — run_hooks(HOOK_PREFS_TABS, $args)
    Adapted: HTML prefs page replaced by JSON endpoint; plugins extend via hooks.
    """
    from ttrss.plugins.manager import get_plugin_manager
    pm = get_plugin_manager()
    # Source: ttrss/prefs.php:139 — HOOK_PREFS_TABS (fire-and-forget, collecting)
    plugin_tabs = pm.hook.hook_prefs_tabs(args={})
    return jsonify({"plugin_tabs": plugin_tabs})
