"""
Integration tests for /api/ login endpoint (R08, R09, R15).
Requires real Postgres + Redis (docker-compose.test.yml).
AR07: no SQLite — app fixture in conftest.py targets TEST_DATABASE_URL.

Note: seed_prefs fixture (integration/conftest.py) is session-scoped autouse=True,
so ENABLE_API_ACCESS system default is available for all tests here.
"""
import pytest

from ttrss.auth.password import hash_password
from ttrss.extensions import db as _db
from ttrss.models.user import TtRssUser


@pytest.fixture()
def test_user(app, db_session, seed_prefs):
    """Create a test user with argon2id-hashed password.

    API access enabled via system default: seed_prefs sets
    TtRssPref(ENABLE_API_ACCESS, def_value='true') so get_user_pref()
    returns 'true' for all users via system-default fallback.

    Source: ttrss/classes/pref/users.php:Pref_Users::save (user creation)
    """
    with app.app_context():
        user = TtRssUser(
            login="testuser",
            pwd_hash=hash_password("testpassword"),
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        existing = db_session.get(TtRssUser, user.id)
        if existing:
            db_session.delete(existing)
            db_session.commit()


def test_login_success(client, test_user):
    """POST /api/ op=login → status=0, session_id, api_level=8 (R08)."""
    resp = client.post(
        "/api/",
        json={"op": "login", "user": "testuser", "password": "testpassword", "seq": 1},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["seq"] == 1, "seq must be echoed from request (CG-04, R08)"
    assert data["status"] == 0
    assert "session_id" in data["content"]
    assert data["content"]["api_level"] == 8


def test_login_wrong_password(client, test_user):
    """Wrong password → status=1, error=LOGIN_ERROR."""
    resp = client.post(
        "/api/",
        json={"op": "login", "user": "testuser", "password": "wrongpassword", "seq": 2},
    )
    data = resp.get_json()
    assert data["seq"] == 2
    assert data["status"] == 1
    assert data["content"]["error"] == "LOGIN_ERROR"


def test_login_unknown_user(client):
    """Unknown user → status=1."""
    resp = client.post(
        "/api/",
        json={"op": "login", "user": "nobody", "password": "anything", "seq": 3},
    )
    data = resp.get_json()
    assert data["seq"] == 3
    assert data["status"] == 1


def test_is_logged_in_unauthenticated(client):
    """isLoggedIn without session → content.status=0 (R09)."""
    resp = client.get("/api/?op=isLoggedIn&seq=4")
    data = resp.get_json()
    assert data["seq"] == 4
    assert data["status"] == 0
    assert data["content"]["status"] == 0


def test_is_logged_in_after_login(client, test_user):
    """After login, isLoggedIn → content.status=1 (R09)."""
    login_resp = client.post(
        "/api/",
        json={"op": "login", "user": "testuser", "password": "testpassword", "seq": 5},
    )
    assert login_resp.get_json()["status"] == 0

    resp = client.get("/api/?op=isLoggedIn&seq=6")
    data = resp.get_json()
    assert data["seq"] == 6
    assert data["content"]["status"] == 1


def test_seq_echoed_on_unknown_method(client):
    """seq is echoed even for unknown methods (CG-04)."""
    resp = client.post("/api/", json={"op": "nonexistent", "seq": 99})
    data = resp.get_json()
    assert data["seq"] == 99


def test_response_never_contains_pwd_hash(client, test_user):
    """AR05: pwd_hash must never appear in any API response."""
    resp = client.post(
        "/api/",
        json={"op": "login", "user": "testuser", "password": "testpassword", "seq": 7},
    )
    resp_text = resp.get_data(as_text=True)
    assert "pwd_hash" not in resp_text
    # "password" key is in request but must not leak into response body
    assert '"password"' not in resp_text
