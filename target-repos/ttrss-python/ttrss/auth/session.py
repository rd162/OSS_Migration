"""
Flask-Login session helpers (ADR-0007, R07).

The user_loader callback is registered in ttrss/extensions.py to avoid circular imports.
This module holds any additional session-layer utilities.
AR05: pwd_hash is never placed in the session — only user_id is stored.

Inferred from: ttrss/include/sessions.php (validate_session, login_sequence, logout_user)
               Adapted for Flask-Login + Redis pattern (ADR-0007).
Deliberately NOT replicated from PHP:
  $_SESSION["pwd_hash"] — AR05: Python stores user_id only (see specs/06-security.md F10)
  $_SESSION["user_agent"] / $_SESSION["ip_address"] — Redis session handles freshness

# Eliminated (ADR-0007): ttrss/include/sessions.php::ttrss_read, ttrss_write, ttrss_destroy, ttrss_gc
#   Flask-Login + Flask-Session (Redis) replaces PHP custom session handlers.
# Eliminated (stdlib): ttrss/include/functions.php::make_password — secrets.token_urlsafe().
# Eliminated (ADR-0002): ttrss/include/functions.php::validate_csrf — Flask-WTF CSRFProtect.
"""
# DB table coverage — sessions.php accesses these tables
# Source: ttrss/include/sessions.php
from ttrss.models.session import TtRssSession  # noqa: F401
from ttrss.models.version import TtRssVersion  # noqa: F401
