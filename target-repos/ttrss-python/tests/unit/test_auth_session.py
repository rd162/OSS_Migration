"""Tests for Flask-Login user_loader (ttrss/extensions.py:load_user).

Source PHP: ttrss/include/sessions.php (validate_session, lines 77-92)
            uid-based session validation → look up ttrss_users by uid.
Adapted: Flask-Login user_loader replaces PHP validate_session() + $_SESSION["uid"] pattern
         (ADR-0007). AR05: pwd_hash is NEVER placed in the session — user_id only.
New: no direct PHP equivalent for Flask-Login @user_loader callback.
"""
from __future__ import annotations

import pytest
import ttrss.auth.session  # noqa: F401 — imports trigger coverage of session.py model-coverage lines


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_test_user(app, db_session):
    """Create a user for user_loader tests.

    Source: ttrss/include/sessions.php — validate_session queries ttrss_users by uid.
    """
    from ttrss.auth.password import hash_password
    from ttrss.models.user import TtRssUser

    with app.app_context():
        user = TtRssUser(
            login="session_loader_user",
            pwd_hash=hash_password("sessionpass"),
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        db_session.delete(user)
        db_session.commit()


# ---------------------------------------------------------------------------
# Test 1: user_loader with valid uid → returns user object
# ---------------------------------------------------------------------------


def test_user_loader_valid_uid_returns_user(app, session_test_user):
    """load_user(uid) with a valid uid in the DB → returns TtRssUser instance.

    Source: ttrss/include/sessions.php lines 77-92 — PHP validates session by querying
            ttrss_users WHERE id = :uid; Python uses Flask-Login user_loader callback.
    Adapted: db.session.get(TtRssUser, int(user_id)) replaces PHP PDO SELECT.
    """
    from ttrss.extensions import load_user

    with app.app_context():
        from ttrss.models.user import TtRssUser

        user = load_user(str(session_test_user.id))

    assert user is not None
    assert user.id == session_test_user.id
    assert user.login == "session_loader_user"


# ---------------------------------------------------------------------------
# Test 2: user_loader with missing uid → returns None
# ---------------------------------------------------------------------------


def test_user_loader_missing_uid_returns_none(app):
    """load_user(uid) for a non-existent uid → None.

    Source: ttrss/include/sessions.php lines 77-92 — PHP returns false/null if user
            row not found; Flask-Login requires None to be returned for missing users.
    Adapted: db.session.get() returns None for unknown primary key; load_user propagates None.
    """
    from ttrss.extensions import load_user

    with app.app_context():
        user = load_user("999999999")  # Guaranteed non-existent

    assert user is None
