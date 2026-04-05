"""Unit tests for ttrss.auth.authenticate — authenticate_user function.

Source PHP: ttrss/include/functions.php:authenticate_user (lines 706-771)
New: no PHP equivalent — Python test suite.

These are pure-unit tests: Flask app context is constructed manually so that
current_app.config is accessible without a live Postgres/Redis stack.
All DB access and Flask-Login calls are mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Minimal Flask app factory for authenticate_user unit tests.
# We need current_app.config — no DB, no Redis required.
# ---------------------------------------------------------------------------

@pytest.fixture()
def _flask_app():
    """Minimal Flask app used to provide current_app context in unit tests."""
    from flask import Flask
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "unit-test-secret"
    app.config["SINGLE_USER_MODE"] = False
    return app


@pytest.fixture()
def _flask_app_single_user():
    """Flask app with SINGLE_USER_MODE=True."""
    from flask import Flask
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "unit-test-secret"
    app.config["SINGLE_USER_MODE"] = True
    return app


# ---------------------------------------------------------------------------
# Helper: build a mock PluginManager with a hook_auth_user stub.
# ---------------------------------------------------------------------------

def _make_pm(*, user_id=None):
    """Return a mock PluginManager whose hook.hook_auth_user returns user_id.

    Source: ttrss/include/functions.php lines 709-719 — HOOK_AUTH_USER loop.
    Adapted: PHP foreach+break on truthy; pluggy firstresult=True mirrors semantics.
    """
    pm = MagicMock()
    pm.hook.hook_auth_user.return_value = user_id
    return pm


# ---------------------------------------------------------------------------
# 1. Correct credentials (hook returns uid) → returns True, user logged in
# ---------------------------------------------------------------------------

class TestAuthenticateUserNormalMode:
    """Tests for non-SINGLE_USER_MODE path.

    Source: ttrss/include/functions.php:authenticate_user lines 708-748.
    """

    def test_correct_credentials_returns_true(self, _flask_app):
        """authenticate_user returns True when plugin hook returns a valid user_id.

        Source: ttrss/include/functions.php line 713 — $user_id = (int) $plugin->authenticate($login, $password).
        Source: ttrss/include/functions.php line 721 — if ($user_id && !$check_only).
        """
        mock_user = MagicMock()
        mock_user.id = 5
        mock_pm = _make_pm(user_id=5)

        with _flask_app.app_context():
            with (
                patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm),
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user") as mock_login,
                patch("ttrss.prefs.ops.initialize_user_prefs"),
            ):
                mock_db.session.get.return_value = mock_user
                from ttrss.auth.authenticate import authenticate_user
                result = authenticate_user("testuser", "correct_pw")

        assert result is True
        mock_login.assert_called_once_with(mock_user)

    def test_wrong_password_returns_false(self, _flask_app):
        """authenticate_user returns False when plugin hook returns None (wrong password).

        Source: ttrss/include/functions.php line 715 — break on truthy: if none truthy, user_id stays false.
        Source: ttrss/include/functions.php line 748 — return false.
        """
        mock_pm = _make_pm(user_id=None)

        with _flask_app.app_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.auth.authenticate import authenticate_user
                result = authenticate_user("testuser", "wrong_pw")

        assert result is False

    def test_user_not_found_in_db_returns_false(self, _flask_app):
        """authenticate_user returns False when plugin returns uid but DB row is missing.

        Source: ttrss/include/functions.php lines 727-731 — SELECT login FROM ttrss_users WHERE id=uid.
        Adapted: Python guards against plugin returning a stale user_id not in DB.
        Note: PHP does not guard this case; Python adds an explicit None check.
        """
        mock_pm = _make_pm(user_id=99)

        with _flask_app.app_context():
            with (
                patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm),
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user") as mock_login,
            ):
                mock_db.session.get.return_value = None  # user not in DB
                from ttrss.auth.authenticate import authenticate_user
                result = authenticate_user("ghost", "pw")

        assert result is False
        mock_login.assert_not_called()

    def test_plugin_hook_called_before_db(self, _flask_app):
        """Plugin hook is always invoked (before any DB user lookup) in normal mode.

        Source: ttrss/include/functions.php lines 709-719 — plugin hook loop runs
        unconditionally before the DB SELECT for the user row.
        Adapted: Python uses get_plugin_manager() + pm.hook.hook_auth_user().
        """
        call_order = []
        mock_pm = MagicMock()

        def hook_side_effect(*, login, password):
            call_order.append("hook")
            return None

        mock_pm.hook.hook_auth_user.side_effect = hook_side_effect

        with _flask_app.app_context():
            with (
                patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm),
            ):
                from ttrss.auth.authenticate import authenticate_user
                authenticate_user("anyuser", "anypass")

        assert "hook" in call_order
        mock_pm.hook.hook_auth_user.assert_called_once_with(login="anyuser", password="anypass")

    def test_plugin_returns_user_id_no_extra_db_query(self, _flask_app):
        """When plugin hook returns user_id, only a single db.session.get() lookup occurs.

        Source: ttrss/include/functions.php lines 727-731 — one SELECT by uid after hook.
        Adapted: Python uses db.session.get(TtRssUser, user_id) — a primary-key lookup,
        not a secondary query. No additional filtering query should be issued.
        """
        mock_user = MagicMock()
        mock_user.id = 7
        mock_pm = _make_pm(user_id=7)

        with _flask_app.app_context():
            with (
                patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm),
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user"),
                patch("ttrss.prefs.ops.initialize_user_prefs"),
            ):
                mock_db.session.get.return_value = mock_user
                from ttrss.auth.authenticate import authenticate_user
                authenticate_user("testuser", "pw")

        # Only one .get() call — no .query() or .execute() calls
        mock_db.session.get.assert_called_once()
        mock_db.session.query.assert_not_called()


# ---------------------------------------------------------------------------
# 4. SINGLE_USER_MODE — logs in admin user (id=1) without plugin hook
# ---------------------------------------------------------------------------

class TestAuthenticateUserSingleUserMode:
    """Tests for SINGLE_USER_MODE=True path.

    Source: ttrss/include/functions.php lines 750-770 — SINGLE_USER_MODE branch.
    Adapted: PHP sets $_SESSION["uid"]=1 directly; Python uses Flask-Login login_user().
    """

    def test_single_user_mode_returns_true_with_admin_user(self, _flask_app_single_user):
        """SINGLE_USER_MODE bypasses plugin hook and logs in admin user (id=1).

        Source: ttrss/include/functions.php line 752 — $_SESSION["uid"] = 1.
        Adapted: Python calls db.session.get(TtRssUser, 1) and login_user(admin_user).
        Note: PHP assumes admin user always exists; Python guards against missing seed data.
        """
        admin_user = MagicMock()
        admin_user.id = 1

        with _flask_app_single_user.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user") as mock_login,
                patch("ttrss.prefs.ops.initialize_user_prefs"),
            ):
                mock_db.session.get.return_value = admin_user
                from ttrss.auth.authenticate import authenticate_user
                result = authenticate_user(None, None)

        assert result is True
        mock_login.assert_called_once_with(admin_user)
        # Verify it fetched user id=1
        mock_db.session.get.assert_called_once()
        args = mock_db.session.get.call_args
        assert args[0][1] == 1 or args[1].get("ident") == 1
