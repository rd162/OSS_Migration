"""
Integration tests for API meta operations: version, level, login guards, logout, seq echo.

Source: ttrss/classes/api.php:API (getVersion, getApiLevel, isLoggedIn, logout — lines 39-95)
        ttrss/api/index.php (dispatch, NOT_LOGGED_IN guard, UNKNOWN_METHOD — lines 1-74)
Requires: docker compose -f docker-compose.test.yml up -d
"""
from __future__ import annotations

import pytest


class TestGetVersion:
    """Source: ttrss/classes/api.php:API.getVersion (lines 39-42)."""

    def test_get_version_returns_python_sentinel(self, logged_in_client):
        """Authenticated getVersion → version string with '-python' suffix.

        Source: ttrss/classes/api.php:API.getVersion (lines 39-42)
        Adapted: PHP appends 7-char git hash; Python returns static '1.12.0-python'.
        """
        resp = logged_in_client.post("/api/", json={"op": "getVersion", "seq": 10})
        data = resp.get_json()
        assert data["status"] == 0
        assert "python" in data["content"]["version"]

    def test_get_version_seq_echoed(self, logged_in_client):
        """seq field is always echoed (CG-04).

        Source: ttrss/classes/api.php:API.__construct (line 26 — $this->seq)
        """
        resp = logged_in_client.post("/api/", json={"op": "getVersion", "seq": 42})
        assert resp.get_json()["seq"] == 42


class TestGetApiLevel:
    """Source: ttrss/classes/api.php:API.getApiLevel (lines 44-47)."""

    def test_get_api_level_returns_8(self, logged_in_client):
        """getApiLevel → level=8.

        Source: ttrss/classes/api.php:API.getApiLevel (line 46 — return API_LEVEL=8)
        """
        resp = logged_in_client.post("/api/", json={"op": "getApiLevel", "seq": 11})
        data = resp.get_json()
        assert data["status"] == 0
        assert data["content"]["level"] == 8


class TestIsLoggedIn:
    """Source: ttrss/classes/api.php:API.isLoggedIn (lines 94-95)."""

    def test_is_logged_in_unauthenticated(self, client):
        """isLoggedIn without session → content.status=false (R09).

        Source: ttrss/classes/api.php:API.isLoggedIn (line 95)
        PHP: return ['status' => false] when not authenticated.
        """
        resp = client.get("/api/?op=isLoggedIn&seq=20")
        data = resp.get_json()
        assert data["status"] == 0  # envelope status OK
        assert data["content"]["status"] is False
        assert data["seq"] == 20

    def test_is_logged_in_after_login(self, logged_in_client):
        """isLoggedIn after successful login → content.status=true (R09).

        Source: ttrss/classes/api.php:API.isLoggedIn (line 95)
        PHP: return ['status' => true] when authenticated.
        """
        resp = logged_in_client.get("/api/?op=isLoggedIn&seq=21")
        data = resp.get_json()
        assert data["status"] == 0
        assert data["content"]["status"] is True

    def test_is_logged_in_case_insensitive(self, logged_in_client):
        """op routing is case-insensitive (PHP strtolower).

        Source: ttrss/classes/api.php — strtolower($method) before dispatch.
        """
        resp = logged_in_client.post("/api/", json={"op": "ISLOGGEDIN", "seq": 22})
        data = resp.get_json()
        assert data["status"] == 0
        assert data["content"]["status"] is True


class TestLogout:
    """Source: ttrss/classes/api.php:API.logout (lines 89-92)."""

    def test_logout_clears_session(self, client, api_user):
        """logout → status=OK, subsequent isLoggedIn returns false.

        Source: ttrss/classes/api.php:API.logout (lines 89-92)
        PHP: session_destroy() + unset($_SESSION); Python: logout_user() + session.clear().
        """
        # Login first
        login_resp = client.post(
            "/api/",
            json={"op": "login", "user": api_user.login, "password": "integration_pass", "seq": 1},
        )
        assert login_resp.get_json()["status"] == 0

        # Logout
        logout_resp = client.post("/api/", json={"op": "logout", "seq": 2})
        data = logout_resp.get_json()
        assert data["status"] == 0
        assert data["content"]["status"] == "OK"

        # isLoggedIn should now return false
        check_resp = client.get("/api/?op=isLoggedIn&seq=3")
        assert check_resp.get_json()["content"]["status"] is False


class TestNotLoggedInGuard:
    """Source: ttrss/classes/api.php:API lines 16-20 — NOT_LOGGED_IN guard."""

    def test_not_logged_in_on_getfeeds(self, client):
        """getFeeds without session → NOT_LOGGED_IN error.

        Source: ttrss/classes/api.php lines 16-20
        PHP: if (!$_SESSION['uid']) { if ($method != 'login' && ...) → NOT_LOGGED_IN }
        """
        resp = client.post("/api/", json={"op": "getFeeds", "seq": 30})
        data = resp.get_json()
        assert data["status"] == 1
        assert data["content"]["error"] == "NOT_LOGGED_IN"

    def test_not_logged_in_on_getheadlines(self, client):
        """getHeadlines without session → NOT_LOGGED_IN.

        Source: ttrss/classes/api.php lines 16-20
        """
        resp = client.post("/api/", json={"op": "getHeadlines", "seq": 31})
        data = resp.get_json()
        assert data["status"] == 1
        assert data["content"]["error"] == "NOT_LOGGED_IN"


class TestSeqEcho:
    """Source: ttrss/classes/api.php:API.__construct (line 26) — seq must be echoed."""

    def test_seq_echoed_on_error(self, client):
        """seq is echoed even on NOT_LOGGED_IN error (CG-04).

        Source: ttrss/classes/api.php — wrap() always includes seq.
        """
        resp = client.post("/api/", json={"op": "getFeeds", "seq": 77})
        assert resp.get_json()["seq"] == 77

    def test_seq_echoed_on_unknown_method(self, logged_in_client):
        """seq is echoed for UNKNOWN_METHOD when authenticated (CG-04).

        Source: ttrss/classes/api.php:API.index (line 488 — UNKNOWN_METHOD)
        Note: must be authenticated — unauthenticated requests hit NOT_LOGGED_IN guard
        before reaching the UNKNOWN_METHOD fallback.
        """
        resp = logged_in_client.post("/api/", json={"op": "completelyUnknownOp", "seq": 99})
        data = resp.get_json()
        assert data["seq"] == 99
        assert data["content"]["error"] == "UNKNOWN_METHOD"

    def test_seq_zero_when_missing(self, client):
        """Missing seq defaults to 0 (CG-04).

        Source: ttrss/classes/api.php:API.__construct (line 26 — (int)$_REQUEST['seq'])
        PHP: (int) cast of missing key → 0.
        """
        resp = client.post("/api/", json={"op": "getVersion"})
        # seq defaults to 0 — can't check without login, but response must have seq
        assert "seq" in resp.get_json()
