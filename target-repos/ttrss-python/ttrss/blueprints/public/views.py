"""
Public endpoints (/public.php equivalent — no auth required).
Phase 1a: index health-check stub only.
Full implementation (RSS feed output, OPML export, shared articles) in Phase 1b.
"""
from flask import Blueprint, jsonify

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
def index():
    """Health-check / app root. Phase 1a stub."""
    return jsonify({"status": "ok", "app": "ttrss-python", "phase": "1a"})
