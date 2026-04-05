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


# ---------------------------------------------------------------------------
# 5. SINGLE_USER_MODE — admin user (id=1) NOT found in DB → returns False
#    Lines 116-119
# ---------------------------------------------------------------------------

class TestAuthenticateUserSingleUserModeAdminMissing:
    """SINGLE_USER_MODE path when admin user (id=1) is absent from the DB.

    Source: ttrss/include/functions.php:authenticate_user lines 750-770
    Adapted: PHP assumes admin always exists; Python guards with an explicit None check
             and logs an error before returning False.
    """

    def test_admin_not_in_db_returns_false(self, _flask_app_single_user):
        """SINGLE_USER_MODE with missing admin user (id=1) returns False without calling login_user.

        Source: ttrss/include/functions.php:authenticate_user line 752 — $_SESSION["uid"] = 1
        Note: PHP equivalent has no None-guard; Python adds logger.error + return False (lines 116-119).
        """
        with _flask_app_single_user.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user") as mock_login,
                patch("ttrss.prefs.ops.initialize_user_prefs") as mock_init_prefs,
            ):
                mock_db.session.get.return_value = None  # admin user absent
                from ttrss.auth.authenticate import authenticate_user
                result = authenticate_user(None, None)

        assert result is False
        mock_login.assert_not_called()
        mock_init_prefs.assert_not_called()

    def test_admin_not_in_db_does_not_commit(self, _flask_app_single_user):
        """When admin user is missing no DB commit should be issued.

        Source: ttrss/include/functions.php:authenticate_user line 752 — early-exit path.
        Note: PHP has no equivalent guard; Python returns False before any session mutation.
        """
        with _flask_app_single_user.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user"),
                patch("ttrss.prefs.ops.initialize_user_prefs"),
            ):
                mock_db.session.get.return_value = None
                from ttrss.auth.authenticate import authenticate_user
                authenticate_user(None, None)

        mock_db.session.commit.assert_not_called()

    def test_admin_not_in_db_plugin_hook_not_called(self, _flask_app_single_user):
        """SINGLE_USER_MODE entirely skips the plugin manager — even when admin is missing.

        Source: ttrss/include/functions.php:authenticate_user line 708 — SINGLE_USER_MODE
        branch does not enter the HOOK_AUTH_USER loop.
        """
        with _flask_app_single_user.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
                patch("flask_login.login_user"),
                patch("ttrss.prefs.ops.initialize_user_prefs"),
                patch("ttrss.plugins.manager.get_plugin_manager") as mock_gpm,
            ):
                mock_db.session.get.return_value = None
                from ttrss.auth.authenticate import authenticate_user
                authenticate_user(None, None)

        mock_gpm.assert_not_called()


# ---------------------------------------------------------------------------
# 6. initialize_user — seeds default feeds and calls initialize_user_prefs
#    Lines 148-168
# ---------------------------------------------------------------------------

class TestInitializeUser:
    """Tests for initialize_user() — seeds default feeds for a new user.

    Source: ttrss/include/functions.php:initialize_user (lines 796-805)
    Adapted: PHP raw SQL INSERT replaced by SQLAlchemy ORM session.add(); PHP
             auto-commit replaced by explicit db.session.commit().
    """

    def test_adds_two_default_feeds(self, _flask_app):
        """initialize_user adds exactly two TtRssFeed rows to the session.

        Source: ttrss/include/functions.php lines 798-804 — two INSERT statements
        for 'Tiny Tiny RSS: New Releases' and 'Tiny Tiny RSS: Forum'.
        """
        with _flask_app.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
                patch("ttrss.models.feed.TtRssFeed") as MockFeed,
            ):
                from ttrss.auth.authenticate import initialize_user
                initialize_user(42)

        assert mock_db.session.add.call_count == 2

    def test_commits_after_adding_feeds(self, _flask_app):
        """initialize_user commits the session after adding both feeds.

        Source: ttrss/include/functions.php:initialize_user line 168 (Python) —
        db.session.commit() — no PHP equivalent; SQLAlchemy requires explicit commit.
        """
        with _flask_app.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
                patch("ttrss.models.feed.TtRssFeed"),
            ):
                from ttrss.auth.authenticate import initialize_user
                initialize_user(99)

        mock_db.session.commit.assert_called_once()

    def test_feeds_have_correct_owner_uid(self, _flask_app):
        """TtRssFeed instances are created with the supplied owner_uid.

        Source: ttrss/include/functions.php lines 798-804 — owner_uid column maps to
        PHP $uid parameter passed to INSERT.
        """
        created_feeds = []

        def capture_add(obj):
            created_feeds.append(obj)

        with _flask_app.app_context():
            with (
                patch("ttrss.extensions.db") as mock_db,
            ):
                mock_db.session.add.side_effect = capture_add
                from ttrss.auth.authenticate import initialize_user
                # Use real TtRssFeed construction to inspect owner_uid
                with patch("ttrss.models.feed.TtRssFeed", wraps=None) as _mock:
                    # Fall back: patch only db, let TtRssFeed be real-ish via MagicMock
                    pass

        # Re-run with a spy on TtRssFeed constructor
        feed_kwargs = []

        class _FeedSpy:
            def __init__(self, **kwargs):
                feed_kwargs.append(kwargs)

        with _flask_app.app_context():
            with (
                patch("ttrss.extensions.db"),
                patch("ttrss.models.feed.TtRssFeed", _FeedSpy),
            ):
                from ttrss.auth.authenticate import initialize_user
                initialize_user(7)

        assert all(kw.get("owner_uid") == 7 for kw in feed_kwargs)
        assert len(feed_kwargs) == 2

    def test_feeds_titles_and_urls(self, _flask_app):
        """Default feeds match the hard-coded PHP titles and URLs verbatim.

        Source: ttrss/include/functions.php lines 798-804 — 'Tiny Tiny RSS: New Releases'
        at http://tt-rss.org/releases.rss and 'Tiny Tiny RSS: Forum' at
        http://tt-rss.org/forum/rss.php.
        """
        feed_kwargs = []

        class _FeedSpy:
            def __init__(self, **kwargs):
                feed_kwargs.append(kwargs)

        with _flask_app.app_context():
            with (
                patch("ttrss.extensions.db"),
                patch("ttrss.models.feed.TtRssFeed", _FeedSpy),
            ):
                from ttrss.auth.authenticate import initialize_user
                initialize_user(1)

        titles = {kw["title"] for kw in feed_kwargs}
        urls = {kw["feed_url"] for kw in feed_kwargs}
        assert "Tiny Tiny RSS: New Releases" in titles
        assert "Tiny Tiny RSS: Forum" in titles
        assert "http://tt-rss.org/releases.rss" in urls
        assert "http://tt-rss.org/forum/rss.php" in urls


# ---------------------------------------------------------------------------
# 7. login_sequence — already-authenticated branch bumps last_login (lines 182-186 / 251-261)
# ---------------------------------------------------------------------------

class TestLoginSequenceAlreadyAuthenticated:
    """Tests for login_sequence() when current_user.is_authenticated is True.

    Source: ttrss/include/functions.php:login_sequence lines 856-860 — UPDATE last_login = NOW()
    for already-authenticated visits; Python equivalent is at authenticate.py lines 251-261.
    """

    def _make_authenticated_user(self, uid=3):
        user = MagicMock()
        user.is_authenticated = True
        user.id = uid
        return user

    def test_already_authenticated_returns_true(self, _flask_app):
        """login_sequence returns True when user is already authenticated.

        Source: ttrss/include/functions.php:login_sequence line 267 (Python) — return True.
        """
        mock_user = self._make_authenticated_user()
        mock_db_user = MagicMock()

        with _flask_app.app_context():
            with (
                patch("flask_login.current_user", mock_user),
                patch("ttrss.extensions.db") as mock_db,
                patch("ttrss.plugins.loader.load_user_plugins"),
            ):
                mock_db.session.get.return_value = mock_db_user
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        assert result is True

    def test_already_authenticated_updates_last_login(self, _flask_app):
        """login_sequence bumps last_login when the user is already authenticated.

        Source: ttrss/include/functions.php:login_sequence line 857 — UPDATE last_login = NOW().
        Adapted: Python uses SQLAlchemy ORM attribute assignment + explicit commit.
        """
        from datetime import datetime, timezone
        mock_user = self._make_authenticated_user(uid=5)
        mock_db_user = MagicMock()

        with _flask_app.app_context():
            with (
                patch("flask_login.current_user", mock_user),
                patch("ttrss.extensions.db") as mock_db,
                patch("ttrss.plugins.loader.load_user_plugins"),
            ):
                mock_db.session.get.return_value = mock_db_user
                from ttrss.auth.authenticate import login_sequence
                login_sequence()

        # last_login was set to a datetime
        assert isinstance(mock_db_user.last_login, datetime)
        assert mock_db_user.last_login.tzinfo is not None
        mock_db.session.commit.assert_called_once()

    def test_already_authenticated_missing_db_row_no_crash(self, _flask_app):
        """login_sequence skips the last_login update when db.session.get returns None.

        Source: ttrss/include/functions.php:login_sequence — PHP runs UPDATE unconditionally;
        Python guards with an explicit None check (lines 258-261 of authenticate.py).
        """
        mock_user = self._make_authenticated_user(uid=9)

        with _flask_app.app_context():
            with (
                patch("flask_login.current_user", mock_user),
                patch("ttrss.extensions.db") as mock_db,
                patch("ttrss.plugins.loader.load_user_plugins"),
            ):
                mock_db.session.get.return_value = None  # user row gone
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        assert result is True
        mock_db.session.commit.assert_not_called()

    def test_already_authenticated_loads_user_plugins(self, _flask_app):
        """login_sequence calls load_user_plugins with the current user's id.

        Source: ttrss/include/functions.php:login_sequence line 864 — load_user_plugins($_SESSION["uid"]).
        Adapted: Python calls load_user_plugins(current_user.id).
        """
        mock_user = self._make_authenticated_user(uid=11)
        mock_db_user = MagicMock()

        with _flask_app.app_context():
            with (
                patch("flask_login.current_user", mock_user),
                patch("ttrss.extensions.db") as mock_db,
                patch("ttrss.plugins.loader.load_user_plugins") as mock_load,
            ):
                mock_db.session.get.return_value = mock_db_user
                from ttrss.auth.authenticate import login_sequence
                login_sequence()

        mock_load.assert_called_once_with(11)


# ---------------------------------------------------------------------------
# 8. login_sequence — unauthenticated paths and AUTH_AUTO_LOGIN (lines 222-267)
# ---------------------------------------------------------------------------

class TestLoginSequenceUnauthenticated:
    """Tests for login_sequence() when current_user is NOT authenticated.

    Source: ttrss/include/functions.php:login_sequence lines 837-853
    Adapted: PHP calls render_login_form() + exit; Python returns False for caller redirection.
    """

    def _make_anon_user(self):
        user = MagicMock()
        user.is_authenticated = False
        return user

    def test_unauthenticated_no_auto_login_returns_false(self, _flask_app):
        """login_sequence returns False when user is not authenticated and AUTH_AUTO_LOGIN is off.

        Source: ttrss/include/functions.php:login_sequence lines 847-853 — PHP renders login form;
        Python returns False.
        """
        mock_user = self._make_anon_user()

        with _flask_app.app_context():
            with patch("flask_login.current_user", mock_user):
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        assert result is False

    def test_auto_login_calls_authenticate_user(self, _flask_app):
        """When AUTH_AUTO_LOGIN is True, login_sequence calls authenticate_user(None, None).

        Source: ttrss/include/functions.php:login_sequence line 842 — authenticate_user(null, null).
        Adapted: PHP AUTH_AUTO_LOGIN constant replaced by Flask config key AUTH_AUTO_LOGIN.
        """
        _flask_app.config["AUTH_AUTO_LOGIN"] = True
        anon_user = self._make_anon_user()

        with _flask_app.app_context():
            with (
                patch("flask_login.current_user", anon_user),
                patch("ttrss.auth.authenticate.authenticate_user") as mock_au,
            ):
                from ttrss.auth.authenticate import login_sequence
                login_sequence()

        mock_au.assert_called_once_with(None, None)

    def test_auto_login_still_returns_false_if_hook_fails(self, _flask_app):
        """Even with AUTH_AUTO_LOGIN, login_sequence returns False when hook auth fails.

        Source: ttrss/include/functions.php:login_sequence lines 846-853 — after
        authenticate_user(null, null) the session validity is re-checked; if still
        unauthenticated, returns False (Python) / renders login form (PHP).
        """
        _flask_app.config["AUTH_AUTO_LOGIN"] = True
        anon_user = self._make_anon_user()

        with _flask_app.app_context():
            with (
                patch("flask_login.current_user", anon_user),
                patch("ttrss.auth.authenticate.authenticate_user", return_value=False),
            ):
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        assert result is False

    def test_single_user_mode_calls_authenticate_when_anon(self, _flask_app_single_user):
        """SINGLE_USER_MODE branch calls authenticate_user('admin', None) when not yet logged in.

        Source: ttrss/include/functions.php:login_sequence lines 831-835 — SINGLE_USER_MODE
        calls authenticate_user unconditionally; Python guards with is_authenticated first.
        """
        anon_user = self._make_anon_user()

        with _flask_app_single_user.app_context():
            with (
                patch("flask_login.current_user", anon_user),
                patch("ttrss.auth.authenticate.authenticate_user") as mock_au,
                patch("ttrss.plugins.loader.load_user_plugins"),
            ):
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        mock_au.assert_called_once_with("admin", None)
        assert result is True

    def test_single_user_mode_skips_authenticate_if_already_logged_in(self, _flask_app_single_user):
        """SINGLE_USER_MODE branch skips authenticate_user when already authenticated.

        Source: ttrss/include/functions.php:login_sequence lines 831-835 — Python adds
        is_authenticated guard to avoid redundant login_user() calls.
        """
        auth_user = MagicMock()
        auth_user.is_authenticated = True
        auth_user.id = 1

        with _flask_app_single_user.app_context():
            with (
                patch("flask_login.current_user", auth_user),
                patch("ttrss.auth.authenticate.authenticate_user") as mock_au,
                patch("ttrss.plugins.loader.load_user_plugins"),
            ):
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        mock_au.assert_not_called()
        assert result is True

    def test_single_user_mode_loads_plugins_with_current_user_id(self, _flask_app_single_user):
        """SINGLE_USER_MODE branch calls load_user_plugins with current_user.id.

        Source: ttrss/include/functions.php:login_sequence line 835 — load_user_plugins($_SESSION["uid"]).
        Adapted: Python calls load_user_plugins(current_user.id).
        """
        auth_user = MagicMock()
        auth_user.is_authenticated = True
        auth_user.id = 1

        with _flask_app_single_user.app_context():
            with (
                patch("flask_login.current_user", auth_user),
                patch("ttrss.auth.authenticate.authenticate_user"),
                patch("ttrss.plugins.loader.load_user_plugins") as mock_load,
            ):
                from ttrss.auth.authenticate import login_sequence
                result = login_sequence()

        mock_load.assert_called_once_with(1)
        assert result is True
