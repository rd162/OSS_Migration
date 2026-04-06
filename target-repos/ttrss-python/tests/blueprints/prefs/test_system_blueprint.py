"""Tests for /prefs/system* HTTP handlers (admin system preferences).

Source: ttrss/classes/pref/system.php (Pref_System, 91 lines)
New: Python test suite — handler-level HTTP tests via Flask test client.

All system endpoints require access_level=10.  Non-admin requests are blocked
by _require_admin() which mirrors PHP's before() check on access_level < 10.
Source: ttrss/classes/pref/system.php:before() — blocks access_level < 10.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_admin(uid: int = 1) -> MagicMock:
    u = MagicMock()
    u.id = uid
    u.access_level = 10
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


def _make_regular_user(uid: int = 2) -> MagicMock:
    u = MagicMock()
    u.id = uid
    u.access_level = 0
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


# ---------------------------------------------------------------------------
# GET /prefs/system
# ---------------------------------------------------------------------------


class TestSystemTab:
    """Source: ttrss/classes/pref/system.php:83 — run_hooks(HOOK_PREFS_TAB)"""

    def test_admin_gets_200(self, client):
        """Admin user receives the system tab content.

        Source: ttrss/classes/pref/system.php:83 — HOOK_PREFS_TAB only accessible
                to admin users (access_level >= 10).
        """
        mock_admin = _make_admin()
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab.return_value = []

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.system.current_user", mock_admin), \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
            resp = client.get("/prefs/system")

        assert resp.status_code == 200
        data = resp.get_json()
        assert "plugin_tab_content" in data

    def test_non_admin_gets_403(self, client):
        """Non-admin is blocked by _require_admin() → 403 insufficient_access_level.

        Source: ttrss/classes/pref/system.php:before() — access_level < 10 → blocked.
        """
        mock_user = _make_regular_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.system.current_user", mock_user):
            resp = client.get("/prefs/system")

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "insufficient_access_level"


# ---------------------------------------------------------------------------
# POST /prefs/system/clear_log
# ---------------------------------------------------------------------------


class TestClearLog:
    """Source: ttrss/classes/pref/system.php:22 — clearLog"""

    def test_admin_can_clear_log(self, client):
        """Admin successfully clears the error log → 200 ok.

        Source: ttrss/classes/pref/system.php:22-23 — DELETE FROM ttrss_error_log.
        """
        mock_admin = _make_admin()

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.system.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.system.system_crud") as mock_crud:
            resp = client.post("/prefs/system/clear_log")

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.clear_error_log.assert_called_once()

    def test_non_admin_clear_log_gets_403(self, client):
        """Non-admin cannot clear error log → 403 insufficient_access_level.

        Source: ttrss/classes/pref/system.php:before() — access_level < 10 → blocked.
        """
        mock_user = _make_regular_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.system.current_user", mock_user):
            resp = client.post("/prefs/system/clear_log")

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "insufficient_access_level"
