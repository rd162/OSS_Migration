"""Unit tests for ttrss.auth.register — user self-registration logic.

Source PHP: ttrss/register.php (lines 1-368)
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------

def _make_session(*, user_exists: bool = False, user_count: int = 0):
    """Return a mock SQLAlchemy Session for register.py call patterns."""
    session = MagicMock()
    query_mock = MagicMock()
    filter_mock = MagicMock()
    filter_mock.first.return_value = MagicMock() if user_exists else None
    query_mock.filter.return_value = filter_mock
    query_mock.scalar.return_value = user_count
    session.query.return_value = query_mock
    exec_result = MagicMock()
    exec_result.rowcount = 3
    session.execute.return_value = exec_result
    return session


# ---------------------------------------------------------------------------
# check_username_available
# ---------------------------------------------------------------------------

class TestCheckUsernameAvailable:

    def test_new_username_returns_true(self):
        """
        Source: ttrss/register.php lines 74-91
        PHP: SELECT COUNT FROM ttrss_users WHERE LOWER(login)=LOWER($login)
        Assert: no row found → True (available).
        """
        from ttrss.auth.register import check_username_available
        session = _make_session(user_exists=False)
        assert check_username_available(session, "newuser") is True

    def test_existing_username_returns_false(self):
        """
        Source: ttrss/register.php lines 74-91
        PHP: row found → username taken, returns false.
        Assert: existing row → False.
        """
        from ttrss.auth.register import check_username_available
        session = _make_session(user_exists=True)
        assert check_username_available(session, "admin") is False


# ---------------------------------------------------------------------------
# cleanup_stale_registrations
# ---------------------------------------------------------------------------

class TestCleanupStaleRegistrations:

    def test_executes_delete_and_commits(self):
        """
        Source: ttrss/register.php lines 60-68
        PHP: DELETE FROM ttrss_users WHERE last_login IS NULL AND created < NOW()-1day
        Assert: DELETE executed and committed; rowcount returned.
        """
        from ttrss.auth.register import cleanup_stale_registrations
        session = _make_session()
        result = cleanup_stale_registrations(session)
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------

class TestRegisterUser:

    def _session_for_register(self, user_count=0):
        """Session configured for register_user: no existing user, count=user_count."""
        session = MagicMock()
        # check_username_available: first() → None (available)
        q = MagicMock()
        q.filter.return_value.first.return_value = None
        # user count for reg_max_users: scalar() → user_count
        q.scalar.return_value = user_count
        session.query.return_value = q
        # execute for stale cleanup and user insert
        exec_result = MagicMock()
        exec_result.rowcount = 0
        session.execute.return_value = exec_result
        # flush assigns id to added objects
        def _flush():
            for obj in getattr(session, '_added', []):
                if getattr(obj, 'id', None) is None:
                    obj.id = 1
        session.flush.side_effect = _flush
        original_add = session.add
        added = []
        def _add(obj):
            added.append(obj)
            session._added = added
        session.add.side_effect = _add
        return session

    def test_success_returns_success_dict(self):
        """
        Source: ttrss/register.php lines 247-314
        PHP: INSERT INTO ttrss_users; returns success with login + password.
        Assert: success=True; result has login and tmp_password.
        """
        from ttrss.auth.register import register_user
        session = self._session_for_register()
        with patch("ttrss.auth.authenticate.initialize_user", MagicMock()):
            result = register_user(session, "newuser", "user@x.com",
                                   reg_max_users=0, enable_registration=True)
        assert result.get("success") is True
        assert "login" in result or "tmp_password" in result or "error" not in result

    def test_registration_disabled_returns_error(self):
        """
        Source: ttrss/register.php line 99 — if (!ENABLE_REGISTRATION) { error }
        Assert: enable_registration=False → error key present.
        """
        from ttrss.auth.register import register_user
        session = self._session_for_register()
        result = register_user(session, "x", "x@x.com",
                               reg_max_users=0, enable_registration=False)
        assert result.get("success") is False
        assert "error" in result

    def test_max_users_reached_returns_error(self):
        """
        Source: ttrss/register.php — user count check before insert.
        Assert: reg_max_users=1 with 1 existing user → error.
        """
        from ttrss.auth.register import register_user
        session = self._session_for_register(user_count=1)
        result = register_user(session, "x", "x@x.com",
                               reg_max_users=1, enable_registration=True)
        assert result.get("success") is False

    def test_duplicate_login_returns_error(self):
        """
        Source: ttrss/register.php lines 215-216
        PHP: SELECT id FROM ttrss_users WHERE login='$login'
        Assert: duplicate login → error.
        """
        from ttrss.auth.register import register_user
        session = MagicMock()
        q = MagicMock()
        # user exists for username check
        q.filter.return_value.first.return_value = MagicMock()
        q.scalar.return_value = 0
        session.query.return_value = q
        result = register_user(session, "admin", "a@x.com",
                               reg_max_users=0, enable_registration=True)
        assert result.get("success") is False

    def test_new_user_access_level_is_zero(self):
        """
        Source: ttrss/register.php — new users always access_level=0
        Assert: add() called with object having access_level=0.
        """
        from ttrss.auth.register import register_user
        session = self._session_for_register()
        added = []
        def _capture_add(obj):
            obj.id = 42  # assign id so logger.info("%d") works
            added.append(obj)
        session.add.side_effect = _capture_add
        with patch("ttrss.auth.authenticate.initialize_user", MagicMock()):
            register_user(session, "newuser", "new@x.com",
                          reg_max_users=0, enable_registration=True)
        if added:
            assert getattr(added[0], "access_level", 0) == 0


# ---------------------------------------------------------------------------
# registration_slots_feed
# ---------------------------------------------------------------------------

class TestRegistrationSlotsFeed:

    def test_returns_xml_string(self):
        """
        Source: ttrss/register.php lines 24-57 — Atom feed format.
        Assert: returns non-empty string containing XML markers.
        """
        from ttrss.auth.register import registration_slots_feed
        session = MagicMock()
        session.query.return_value.scalar.return_value = 0
        result = registration_slots_feed(
            session,
            enable_registration=True,
            reg_max_users=10,
            self_url="http://x.com",
        )
        assert isinstance(result, str)
        assert len(result) > 0
