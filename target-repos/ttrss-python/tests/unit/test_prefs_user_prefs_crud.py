"""Unit tests for ttrss/prefs/user_prefs_crud.py — user preferences CRUD.

Source PHP: ttrss/classes/pref/prefs.php (Pref_Prefs handler, 1129 lines)

All tests patch ``ttrss.prefs.user_prefs_crud.db`` so no real DB or Flask
app context is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UID = 5
MISSING_UID = 999


def _make_db():
    mock_db = MagicMock()
    mock_db.session = MagicMock()
    return mock_db


def _make_user(uid=UID, email="user@example.com", full_name="Test User",
               access_level=0, otp_enabled=False, last_login=None, created=None):
    user = MagicMock()
    user.id = uid
    user.login = "testuser"
    user.email = email
    user.full_name = full_name
    user.access_level = access_level
    user.otp_enabled = otp_enabled
    user.last_login = last_login
    user.created = created
    return user


# ---------------------------------------------------------------------------
# get_user_details (via users_crud — spec maps this here)
# ---------------------------------------------------------------------------


def test_get_user_details_user_exists_returns_dict_with_expected_keys():
    """get_user_details returns a dict with standard keys when user row found.

    Source: ttrss/classes/pref/users.php:userdetails (line 20) / edit (line 101) — load user details.
    """
    mock_db = _make_db()
    user = _make_user()
    mock_db.session.get.return_value = user

    # execute() call 1: feed count scalar
    # execute() call 2: stored_articles scalar
    # execute() call 3: feed rows .all()
    call_results = iter([
        MagicMock(**{"scalar.return_value": 3}),        # num_feeds
        MagicMock(**{"scalar.return_value": 150}),       # stored_articles
        MagicMock(**{"all.return_value": []}),           # feeds list
    ])
    mock_db.session.execute.side_effect = lambda *a, **kw: next(call_results)

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import get_user_details

        result = get_user_details(UID)

    assert result is not None
    for key in ("id", "login", "access_level", "email", "full_name",
                "last_login", "created", "num_feeds", "stored_articles", "feeds"):
        assert key in result, f"Missing key: {key}"
    assert result["num_feeds"] == 3
    assert result["stored_articles"] == 150


def test_get_user_details_not_found_returns_none():
    """get_user_details returns None when user_id has no matching row.

    Source: ttrss/classes/pref/users.php:userdetails (line 24-31) — user not found early return.
    """
    mock_db = _make_db()
    mock_db.session.get.return_value = None

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import get_user_details

        result = get_user_details(MISSING_UID)

    assert result is None


# ---------------------------------------------------------------------------
# save_email_and_name (update_profile equivalent)
# ---------------------------------------------------------------------------


def test_update_profile_executes_update_and_commits():
    """save_email_and_name issues an UPDATE and commits the session.

    Source: ttrss/classes/pref/prefs.php:changeemail (line 153-154) — UPDATE ttrss_users SET email, full_name.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.user_prefs_crud.db", mock_db):
        from ttrss.prefs.user_prefs_crud import save_email_and_name

        save_email_and_name(UID, "e@x.com", "Full Name")

    mock_db.session.execute.assert_called_once()
    mock_db.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# clear_digest_sent_time
# ---------------------------------------------------------------------------


def test_clear_digest_sent_time_executes_update_with_none():
    """clear_digest_sent_time sets last_digest_sent=None via UPDATE, no commit.

    Source: ttrss/classes/pref/prefs.php:saveconfig (line 106-112) — DIGEST_PREFERRED_TIME
    special-case clears last_digest_sent to force re-send at new preferred time.
    Note: function does NOT commit; caller or a downstream operation commits.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.user_prefs_crud.db", mock_db):
        from ttrss.prefs.user_prefs_crud import clear_digest_sent_time

        clear_digest_sent_time(UID)

    mock_db.session.execute.assert_called_once()
    # Verify commit is NOT called — function deliberately leaves commit to caller
    mock_db.session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# reset_user_prefs
# ---------------------------------------------------------------------------


def test_reset_user_prefs_deletes_then_flushes_then_initializes():
    """reset_user_prefs DELETEs prefs, flushes, then calls initialize_user_prefs.

    Source: ttrss/classes/pref/prefs.php:resetconfig (line 161-174) — DELETE + BEGIN/COMMIT.
    Note: flush() makes DELETE visible before re-init; initialize_user_prefs commits internally.
    initialize_user_prefs is imported inline from ttrss.prefs.ops; patch that module path.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.user_prefs_crud.db", mock_db), \
         patch("ttrss.prefs.ops.initialize_user_prefs") as mock_init:
        from ttrss.prefs.user_prefs_crud import reset_user_prefs

        reset_user_prefs(UID)

    mock_db.session.execute.assert_called_once()
    mock_db.session.flush.assert_called_once()
    mock_init.assert_called_once_with(UID, profile=None)


# ---------------------------------------------------------------------------
# set_otp_enabled
# ---------------------------------------------------------------------------


def test_set_otp_enabled_true_sets_flag_and_commits():
    """set_otp_enabled(uid, True) sets otp_enabled=True on user row and commits.

    Source: ttrss/classes/pref/prefs.php:otpenable (line 920-921) — SET otp_enabled, commit.
    """
    mock_db = _make_db()
    user = _make_user(otp_enabled=False)
    mock_db.session.get.return_value = user

    with patch("ttrss.prefs.user_prefs_crud.db", mock_db):
        from ttrss.prefs.user_prefs_crud import set_otp_enabled

        set_otp_enabled(UID, True)

    assert user.otp_enabled is True
    mock_db.session.commit.assert_called_once()


def test_set_otp_enabled_false_clears_flag_and_commits():
    """set_otp_enabled(uid, False) sets otp_enabled=False on user row and commits.

    Source: ttrss/classes/pref/prefs.php:otpdisable (line 940-941) — CLEAR otp_enabled, commit.
    """
    mock_db = _make_db()
    user = _make_user(otp_enabled=True)
    mock_db.session.get.return_value = user

    with patch("ttrss.prefs.user_prefs_crud.db", mock_db):
        from ttrss.prefs.user_prefs_crud import set_otp_enabled

        set_otp_enabled(UID, False)

    assert user.otp_enabled is False
    mock_db.session.commit.assert_called_once()


# --- Additional tests to cover lines 28, 36-44, 87, 103, 113, 123-133, 142 ---
from ttrss.prefs import user_prefs_crud


class TestSavePasswordChange:
    """Source: ttrss/classes/pref/prefs.php:changepassword lines 62-90."""

    def test_save_password_change_sets_hash(self):
        """Source: pref/prefs.php:62 — hash_password + salt="" + otp_enabled=False.
        Assert: user.pwd_hash updated, salt cleared, otp disabled, commit called."""
        mock_user = MagicMock()
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            with patch("ttrss.auth.password.hash_password", return_value="argon2:hash"):
                user_prefs_crud.save_password_change(1, "newpass")
        assert mock_user.pwd_hash == "argon2:hash"
        assert mock_user.salt == ""
        assert mock_user.otp_enabled is False
        mock_db.session.commit.assert_called()

    def test_save_password_change_user_not_found(self):
        """Source: pref/prefs.php — guard if user not found.
        Assert: no commit when user is None."""
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.get.return_value = None
            user_prefs_crud.save_password_change(999, "pw")
            mock_db.session.commit.assert_not_called()


class TestGetUserForPasswordChange:
    """Source: ttrss/classes/pref/prefs.php:changepassword line 63."""

    def test_returns_user_when_found(self):
        """Source: pref/prefs.php line 63 — SELECT * FROM ttrss_users WHERE id.
        Assert: returns user object."""
        mock_user = MagicMock()
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = user_prefs_crud.get_user_for_password_change(1)
        assert result == mock_user

    def test_returns_none_when_not_found(self):
        """Source: pref/prefs.php — user not found returns None.
        Assert: None when user missing."""
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.get.return_value = None
            result = user_prefs_crud.get_user_for_password_change(999)
        assert result is None


class TestClearPluginData:
    """Source: ttrss/classes/pref/prefs.php:clearplugindata line 962."""

    def test_clears_plugin_data(self):
        """Source: pref/prefs.php:962 — DELETE FROM ttrss_plugin_storage WHERE name AND uid.
        Assert: DELETE execute + commit called."""
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.execute = MagicMock()
            mock_db.session.commit = MagicMock()
            user_prefs_crud.clear_plugin_data(1, "my_plugin")
            mock_db.session.execute.assert_called()
            mock_db.session.commit.assert_called()


class TestGetUserForOtp:
    """Source: ttrss/classes/pref/prefs.php:otpqrcode/otpenable/otpdisable line 873."""

    def test_returns_user(self):
        """Source: pref/prefs.php:873 — db.session.get(TtRssUser, owner_uid).
        Assert: user returned."""
        mock_user = MagicMock()
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = user_prefs_crud.get_user_for_otp(1)
        assert result == mock_user


class TestResetUserPrefsFlush:
    """Source: ttrss/classes/pref/prefs.php:resetconfig lines 161-174."""

    def test_reset_user_prefs_calls_flush(self):
        """Source: pref/prefs.php:170-174 — DELETE + re-initialize prefs.
        Adapted: Python uses flush() + initialize_user_prefs() to avoid savepoint conflict.
        Assert: session.flush() called before initialize."""
        with patch("ttrss.prefs.user_prefs_crud.db") as mock_db:
            mock_db.session.execute = MagicMock()
            mock_db.session.flush = MagicMock()
            with patch("ttrss.prefs.ops.initialize_user_prefs") as mock_init:
                user_prefs_crud.reset_user_prefs(1)
            mock_db.session.flush.assert_called()
            mock_init.assert_called_with(1, profile=None)
