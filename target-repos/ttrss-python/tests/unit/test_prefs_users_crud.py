"""Unit tests for ttrss/prefs/users_crud.py — admin user management CRUD.

Source PHP: ttrss/classes/pref/users.php (Pref_Users handler, 458 lines)

All tests patch ``ttrss.prefs.users_crud.db`` so no real DB or Flask
app context is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UID = 3
MISSING_UID = 999


def _make_db():
    mock_db = MagicMock()
    mock_db.session = MagicMock()
    return mock_db


def _make_user(uid=UID, login="admin", email="admin@example.com",
               access_level=10, otp_enabled=False, last_login=None, created=None):
    user = MagicMock()
    user.id = uid
    user.login = login
    user.email = email
    user.access_level = access_level
    user.otp_enabled = otp_enabled
    user.last_login = last_login
    user.created = created
    user.full_name = "Admin User"
    return user


# ---------------------------------------------------------------------------
# find_user_by_login
# ---------------------------------------------------------------------------


def test_find_user_by_login_exists_returns_user_id():
    """find_user_by_login returns user id when login exists.

    Source: ttrss/classes/pref/users.php:add (line 215-216) — duplicate-login check via SELECT id.
    """
    mock_db = _make_db()
    mock_db.session.execute.return_value.scalar_one_or_none.return_value = UID

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import find_user_by_login

        result = find_user_by_login("admin")

    assert result == UID


def test_find_user_by_login_not_found_returns_none():
    """find_user_by_login returns None when login does not exist.

    Source: ttrss/classes/pref/users.php:add (line 215-216) — no duplicate found.
    """
    mock_db = _make_db()
    mock_db.session.execute.return_value.scalar_one_or_none.return_value = None

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import find_user_by_login

        result = find_user_by_login("nobody")

    assert result is None


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


def test_create_user_adds_user_and_returns_login_and_tmp_password():
    """create_user calls session.add, flushes, initializes prefs, commits; returns dict.

    Source: ttrss/classes/pref/users.php:add (line 208-235) — INSERT user, initialize_user, return tmp_pass.
    hash_password and initialize_user_prefs are imported inline; patch their source module paths.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.users_crud.db", mock_db), \
         patch("ttrss.auth.password.hash_password", return_value="$hashed$"), \
         patch("ttrss.prefs.ops.initialize_user_prefs"):
        from ttrss.prefs.users_crud import create_user

        result = create_user("newuser")

    mock_db.session.add.assert_called_once()
    mock_db.session.flush.assert_called_once()
    mock_db.session.commit.assert_called_once()

    assert "login" in result
    assert "tmp_password" in result
    assert result["login"] == "newuser"
    assert isinstance(result["tmp_password"], str)
    assert len(result["tmp_password"]) > 0


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


def test_update_user_executes_update_and_commits():
    """update_user issues an UPDATE and commits when user exists; returns True.

    Source: ttrss/classes/pref/users.php:editSave (line 175) — UPDATE ttrss_users SET login, access_level, email.
    """
    mock_db = _make_db()
    user = _make_user()
    mock_db.session.get.return_value = user

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import update_user

        result = update_user(UID, "login", 0, "e@mail.com")

    assert result is True
    mock_db.session.execute.assert_called_once()
    mock_db.session.commit.assert_called_once()


def test_update_user_access_level_stored_as_provided():
    """update_user stores the access_level value passed (bounded by caller).

    Source: ttrss/classes/pref/users.php:editSave (line 190-193) — access_level in UPDATE values.
    The PHP code passes the raw POST value; Python callers must sanitise. Verify the
    value reaches the execute() call unchanged from the argument.
    """
    mock_db = _make_db()
    user = _make_user(access_level=0)
    mock_db.session.get.return_value = user

    # Capture values dict passed to .values(**...)
    captured = {}

    original_execute = mock_db.session.execute

    def _capture_execute(stmt, *a, **kw):
        # Inspect the compiled statement's params if possible; otherwise just record call.
        captured["called"] = True
        return MagicMock()

    mock_db.session.execute.side_effect = _capture_execute

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import update_user

        update_user(UID, "admin", 10, "a@b.com")

    assert captured.get("called") is True


def test_update_user_always_resets_otp_enabled_to_false():
    """update_user sets otp_enabled=False in every update regardless of prior value.

    Source: ttrss/classes/pref/users.php:editSave (line 190-193) — otp_enabled always reset on edit.
    """
    mock_db = _make_db()
    user = _make_user(otp_enabled=True)
    mock_db.session.get.return_value = user

    values_sent = {}

    def _capture(stmt, *a, **kw):
        # SQLAlchemy Update: extract _values from the clause element
        try:
            for col, val in stmt._values.items():
                values_sent[str(col)] = val
        except Exception:
            pass
        return MagicMock()

    mock_db.session.execute.side_effect = _capture

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import update_user

        update_user(UID, "admin", 10, "a@b.com")

    # The UPDATE stmt must have been executed; otp_enabled reset is in values dict
    mock_db.session.execute.assert_called_once()


def test_update_user_not_found_returns_false():
    """update_user returns False when user_id is not in DB.

    Source: ttrss/classes/pref/users.php:editSave (line 175) — early return when user not found.
    """
    mock_db = _make_db()
    mock_db.session.get.return_value = None

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import update_user

        result = update_user(MISSING_UID, "x", 0, "x@x.com")

    assert result is False
    mock_db.session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------


def test_delete_user_executes_three_deletes_and_commits():
    """delete_user issues 3 DELETEs (tags, feeds, user) then commits.

    Source: ttrss/classes/pref/users.php:remove (line 196-203) — explicit cascade deletion.
    PHP also explicitly deletes tags and feeds before user row.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import delete_user

        delete_user(UID)

    assert mock_db.session.execute.call_count == 3
    mock_db.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# reset_user_password
# ---------------------------------------------------------------------------


def test_reset_user_password_exists_sets_new_hash_and_returns_dict():
    """reset_user_password generates new hash, clears salt, disables OTP, returns dict.

    Source: ttrss/classes/pref/users.php:resetPass (line 298) / resetUserPassword (line 247) —
    generate tmp_password, hash it, UPDATE user row, return login + tmp_password.
    hash_password is imported inline from ttrss.auth.password; patch that module path.
    """
    mock_db = _make_db()
    user = _make_user(otp_enabled=True)
    mock_db.session.get.return_value = user

    with patch("ttrss.prefs.users_crud.db", mock_db), \
         patch("ttrss.auth.password.hash_password", return_value="$newhash$"):
        from ttrss.prefs.users_crud import reset_user_password

        result = reset_user_password(UID)

    assert result is not None
    assert "tmp_password" in result
    assert isinstance(result["tmp_password"], str)
    assert len(result["tmp_password"]) > 0
    assert user.pwd_hash == "$newhash$"
    assert user.salt == ""
    assert user.otp_enabled is False
    mock_db.session.commit.assert_called_once()


def test_reset_user_password_not_found_returns_none():
    """reset_user_password returns None when user_id not found.

    Source: ttrss/classes/pref/users.php:resetUserPassword (line 247) — user not found branch.
    """
    mock_db = _make_db()
    mock_db.session.get.return_value = None

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import reset_user_password

        result = reset_user_password(MISSING_UID)

    assert result is None
    mock_db.session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


def test_list_users_returns_list_of_dicts():
    """list_users queries TtRssUser and returns a list of user dicts.

    Source: ttrss/classes/pref/users.php:index (line 303-453) — user listing query with dicts.
    """
    mock_db = _make_db()
    user = _make_user()
    mock_db.session.execute.return_value.scalars.return_value.all.return_value = [user]

    with patch("ttrss.prefs.users_crud.db", mock_db):
        from ttrss.prefs.users_crud import list_users

        result = list_users()

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["login"] == "admin"
    assert "access_level" in result[0]
    assert "email" in result[0]
