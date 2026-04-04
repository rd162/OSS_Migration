"""
Public endpoints (/public.php equivalent — no auth required).

Source: ttrss/public.php (entry point) + ttrss/classes/handler/public.php:Handler_Public
        (OPML, RSS output, shared articles, login form — all Phase 1b+)
Phase 1a: index health-check stub only.
Full implementation (RSS feed output, OPML export, shared articles) in Phase 1b.
"""
from flask import Blueprint, jsonify

# DB table coverage — handler/public.php uses these models for RSS/OPML/shared feeds
# Source: ttrss/classes/handler/public.php:Handler_Public
from ttrss.models.access_key import TtRssAccessKey  # noqa: F401
from ttrss.models.feed import TtRssFeed  # noqa: F401
from ttrss.models.pref import TtRssSettingsProfile  # noqa: F401
from ttrss.models.user import TtRssUser  # noqa: F401
from ttrss.models.user_entry import TtRssUserEntry  # noqa: F401

# Source: ttrss/public.php + ttrss/classes/handler/public.php:Handler_Public
public_bp = Blueprint("public", __name__)


# Source: ttrss/index.php (app root entry point) — Phase 1a health check stub
@public_bp.get("/")
def index():
    """Health-check / app root. Phase 1a stub."""
    return jsonify({"status": "ok", "app": "ttrss-python", "phase": "1a"})
