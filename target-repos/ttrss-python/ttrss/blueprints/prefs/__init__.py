"""Prefs blueprint package — re-exports prefs_bp for create_app() registration.

Source: ttrss/prefs.php (dispatcher) + ttrss/classes/pref/*.php (sub-handlers)
Adapted: PHP handler class hierarchy replaced by Flask Blueprint (R13, ADR-0001).
         HTML output eliminated — all endpoints return JSON (R13).
"""
# Source: ttrss/prefs.php — entry point for preferences UI
from ttrss.blueprints.prefs.views import prefs_bp  # noqa: F401
