"""Tests for /prefs/users* HTTP handlers (admin user management).

Source: ttrss/classes/pref/users.php (Pref_Users, 458 lines)
New: Python test suite — handler-level HTTP tests via Flask test client.

All admin endpoints require access_level=10.  Non-admin requests are blocked
by _require_admin() which mirrors PHP's before() check on access_level < 10.
Source: ttrss/classes/pref/users.php:3-12 — before() guard.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_admin(uid: int = 1) -> MagicMock:
    """Return a mock user with admin access_level=10."""
    u = MagicMock()
    u.id = uid
    u.access_level = 10
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


def _make_regular_user(uid: int = 2) -> MagicMock:
    """Return a mock user with access_level=0 (no admin)."""
    u = MagicMock()
    u.id = uid
    u.access_level = 0
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


# ---------------------------------------------------------------------------
# GET /prefs/users
# ---------------------------------------------------------------------------


class TestListUsers:
    """Source: ttrss/classes/pref/users.php:303 — index (user listing query)"""

    def test_admin_gets_200(self, client):
        """Admin user receives the user list.

        Source: ttrss/classes/pref/users.php:303-453 — user listing query,
                executed only when access_level >= 10.
        """
        mock_admin = _make_admin()
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab_section.return_value = []
        mock_pm.hook.hook_prefs_tab.return_value = []

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud, \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
            mock_crud.list_users.return_value = []
            resp = client.get("/prefs/users")

        assert resp.status_code == 200
        data = resp.get_json()
        assert "users" in data

    def test_non_admin_gets_403(self, client):
        """Non-admin user is blocked by _require_admin().

        Source: ttrss/classes/pref/users.php:3-12 — before() rejects
                access_level < 10.
        """
        mock_user = _make_regular_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_user):
            resp = client.get("/prefs/users")

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "insufficient_access_level"


# ---------------------------------------------------------------------------
# POST /prefs/users  — create user
# ---------------------------------------------------------------------------


class TestAddUser:
    """Source: ttrss/classes/pref/users.php:208 — add"""

    def test_create_user_success(self, client):
        """Admin creates a new user → 200 with status ok.

        Source: ttrss/classes/pref/users.php:208-235 — INSERT user +
                initialize_user_prefs.
        """
        mock_admin = _make_admin()

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud:
            mock_crud.find_user_by_login.return_value = None
            mock_crud.create_user.return_value = {"tmp_password": "tmpXXX"}

            resp = client.post("/prefs/users", data={"login": "newuser"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_duplicate_login_returns_409(self, client):
        """Duplicate login name → 409 login_taken.

        Source: ttrss/classes/pref/users.php:215-216 — duplicate login check.
        """
        mock_admin = _make_admin()
        existing = MagicMock()

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud:
            mock_crud.find_user_by_login.return_value = existing

            resp = client.post("/prefs/users", data={"login": "existinguser"})

        assert resp.status_code == 409
        assert resp.get_json()["error"] == "login_taken"


# ---------------------------------------------------------------------------
# POST /prefs/users/<id>  — update user
# ---------------------------------------------------------------------------


class TestSaveUser:
    """Source: ttrss/classes/pref/users.php:175 — editSave"""

    def test_update_user_returns_200(self, client):
        """Admin updates an existing user's fields.

        Source: ttrss/classes/pref/users.php:175-193 — UPDATE ttrss_users
                (login, access_level, email, otp, pwd_hash).
        """
        mock_admin = _make_admin()

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud:
            mock_crud.update_user.return_value = True

            resp = client.post(
                "/prefs/users/99",
                data={"login": "renamed", "access_level": "0", "email": "a@b.com"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /prefs/users/<id>  — user details
# ---------------------------------------------------------------------------


class TestUserDetails:
    """Source: ttrss/classes/pref/users.php:20 — userdetails / edit (line 101)"""

    def test_get_user_details_returns_200(self, client):
        """Admin fetches details for a specific user → 200 with details dict.

        Source: ttrss/classes/pref/users.php:24-69 — load user row,
                feed count, article count, feeds list.
        """
        mock_admin = _make_admin()
        details = {"id": 99, "login": "someuser", "feed_count": 3}

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud:
            mock_crud.get_user_details.return_value = details
            resp = client.get("/prefs/users/99")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == 99


# ---------------------------------------------------------------------------
# DELETE /prefs/users/<id>
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Source: ttrss/classes/pref/users.php:196 — remove"""

    def test_delete_other_user_returns_200(self, client):
        """Admin deletes a different user → 200 ok.

        Source: ttrss/classes/pref/users.php:201-203 — delete tags, feeds,
                user row.
        """
        mock_admin = _make_admin(uid=1)

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud:
            resp = client.delete("/prefs/users/99")

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.delete_user.assert_called_once_with(99)

    def test_delete_self_returns_400(self, client):
        """Admin cannot delete their own account → 400 cannot_delete_self.

        Source: ttrss/classes/pref/users.php:196 — remove guards against
                self-deletion (PHP: same guard in Python _owner_uid() check).
        """
        mock_admin = _make_admin(uid=7)

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin):
            resp = client.delete("/prefs/users/7")

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "cannot_delete_self"

    def test_delete_admin_user1_returns_400(self, client):
        """Deletion of user id=1 (primary admin) is always blocked → 400 cannot_delete_admin.

        Source: ttrss/classes/pref/users.php:200 — if ($id != $_SESSION["uid"] && $id != 1)
        PHP explicitly protects user id=1 from deletion regardless of who is requesting.
        """
        mock_admin = _make_admin(uid=2)  # another admin trying to delete user 1

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud"):
            resp = client.delete("/prefs/users/1")

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "cannot_delete_admin"


# ---------------------------------------------------------------------------
# POST /prefs/users/<id>/reset_password
# ---------------------------------------------------------------------------


class TestResetUserPassword:
    """Source: ttrss/classes/pref/users.php:298 — resetPass / resetUserPassword"""

    def test_reset_password_returns_200(self, client):
        """Admin resets another user's password → 200 with new tmp password.

        Source: ttrss/classes/pref/users.php:256-261 — generate and store
                new hash, return tmp_password to caller.
        """
        mock_admin = _make_admin()

        with patch("flask_login.utils._get_user", return_value=mock_admin), \
             patch("ttrss.blueprints.prefs.users.current_user", mock_admin), \
             patch("ttrss.blueprints.prefs.users.users_crud") as mock_crud:
            mock_crud.reset_user_password.return_value = {"tmp_password": "abc123"}

            resp = client.post("/prefs/users/55/reset_password")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "tmp_password" in data
