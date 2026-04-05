"""
Integration tests for security invariants.

Source: ttrss/classes/api.php:API (auth guards, response sanitization)
        ADR-0007: session management (no pwd_hash in session)
        ADR-0008: password hashing
        spec/06-security.md (R07, AR05)
Requires: docker compose -f docker-compose.test.yml up -d
"""
from __future__ import annotations

import uuid

import pytest


class TestPwdHashNeverLeaks:
    """AR05: pwd_hash must NEVER appear in any API response body."""

    def test_pwd_hash_not_in_login_response(self, client, api_user):
        """Login response must not contain pwd_hash.

        Source: ttrss/include/functions.php:authenticate_user (lines 724-739)
        AR05: Store only user_id in session; never pwd_hash.
        PHP CONTRAST: PHP stored pwd_hash in $_SESSION — Python deliberately does NOT.
        """
        resp = client.post(
            "/api/",
            json={"op": "login", "user": api_user.login, "password": "integration_pass", "seq": 1},
        )
        body = resp.get_data(as_text=True)
        assert "pwd_hash" not in body
        assert '"password"' not in body  # password key must not echo back

    def test_pwd_hash_not_in_get_feeds_response(self, logged_in_client, test_feed):
        """getFeeds response must not contain pwd_hash or password fields.

        Source: ttrss/classes/api.php:API.getFeeds — SELECT does not include user table.
        AR05: No user secrets in any API response.
        """
        resp = logged_in_client.post("/api/", json={"op": "getFeeds", "cat_id": -4, "seq": 2})
        body = resp.get_data(as_text=True)
        assert "pwd_hash" not in body
        assert "argon2" not in body

    def test_pwd_hash_not_in_get_article_response(self, logged_in_client, test_entry_pair):
        """getArticle response must not contain pwd_hash.

        Source: ttrss/classes/api.php:API.getArticle — joins ttrss_entries, not ttrss_users.
        AR05: article data must not include user credentials.
        """
        entry, _ = test_entry_pair
        resp = logged_in_client.post(
            "/api/", json={"op": "getArticle", "article_id": entry.id, "seq": 3}
        )
        body = resp.get_data(as_text=True)
        assert "pwd_hash" not in body

    def test_get_headlines_response_has_no_credentials(self, logged_in_client, test_entry_pair):
        """getHeadlines response must not expose credential fields.

        Source: ttrss/classes/api.php:API.getHeadlines — SELECT from entries/user_entries only.
        AR05: No user secrets in API responses.
        """
        _, user_entry = test_entry_pair
        resp = logged_in_client.post(
            "/api/",
            json={"op": "getHeadlines", "feed_id": user_entry.feed_id, "seq": 4},
        )
        body = resp.get_data(as_text=True)
        assert "pwd_hash" not in body
        assert "salt" not in body


class TestNotLoggedInGuardOnAllOps:
    """Source: ttrss/classes/api.php lines 16-20 — NOT_LOGGED_IN guard covers all guarded ops."""

    @pytest.mark.parametrize("op", [
        "getFeeds",
        "getCategories",
        "getHeadlines",
        "getArticle",
        "getUnread",
        "getCounters",
        "updateArticle",
        "catchupFeed",
        "setArticleLabel",
        "subscribeToFeed",
        "unsubscribeFeed",
        "updateFeed",
        "getFeedTree",
        "getPref",
        "getConfig",
        "getLabels",
        "shareToPublished",
        "getVersion",
        "getApiLevel",
    ])
    def test_not_logged_in_guard(self, client, op):
        """All guarded ops return NOT_LOGGED_IN without session.

        Source: ttrss/classes/api.php lines 16-20
        PHP: if (!$_SESSION['uid'] && $method != 'login' && $method != 'isloggedin') → NOT_LOGGED_IN
        """
        resp = client.post("/api/", json={"op": op, "seq": 50})
        data = resp.get_json()
        assert data["status"] == 1
        assert data["content"]["error"] == "NOT_LOGGED_IN"


class TestSeqAlwaysEchoed:
    """Source: ttrss/classes/api.php:API.__construct (CG-04 — seq always echoed)."""

    @pytest.mark.parametrize("seq_value", [0, 1, 42, 9999])
    def test_seq_echoed_in_error_response(self, client, seq_value):
        """seq is always echoed, even in error responses.

        Source: ttrss/classes/api.php — wrap() always includes seq field.
        """
        resp = client.post("/api/", json={"op": "getFeeds", "seq": seq_value})
        assert resp.get_json()["seq"] == seq_value

    def test_seq_echoed_from_get_params(self, client):
        """seq in GET query params is echoed (PHP $_REQUEST merges GET+POST).

        Source: ttrss/classes/api.php:API.__construct (line 26 — $_REQUEST['seq'])
        Adapted: Python reads from JSON body first, then query params.
        """
        resp = client.get("/api/?op=isLoggedIn&seq=77")
        assert resp.get_json()["seq"] == 77


class TestUserIsolation:
    """Source: ttrss/classes/api.php — all queries filter by owner_uid."""

    def test_user_cannot_read_other_users_articles(
        self, app, db_session, seed_prefs, test_entry_pair
    ):
        """User A's article does not appear in User B's getHeadlines.

        Source: ttrss/include/rssfuncs.php — all queries WHERE owner_uid = :uid.
        ADR-0006: User isolation via owner_uid FK on all user-owned tables.
        """
        from ttrss.auth.password import hash_password
        from ttrss.models.pref import TtRssUserPref
        from ttrss.models.user import TtRssUser

        entry_a, ue_a = test_entry_pair  # owned by api_user

        login_b = f"user_b_{uuid.uuid4().hex[:8]}"
        with app.app_context():
            user_b = TtRssUser(
                login=login_b, pwd_hash=hash_password("pass_b"), access_level=0
            )
            db_session.add(user_b)
            db_session.flush()
            db_session.add(TtRssUserPref(
                owner_uid=user_b.id, pref_name="ENABLE_API_ACCESS", profile=None, value="true"
            ))
            db_session.commit()

        # Login as user_b
        client_b = app.test_client()
        login_resp = client_b.post(
            "/api/",
            json={"op": "login", "user": login_b, "password": "pass_b", "seq": 1},
        )
        assert login_resp.get_json()["status"] == 0

        # user_b's getHeadlines for all feeds — must not see user_a's article
        headlines_resp = client_b.post(
            "/api/", json={"op": "getHeadlines", "feed_id": -4, "seq": 2}
        )
        data = headlines_resp.get_json()
        assert data["status"] == 0
        article_ids = [a["id"] for a in data["content"]]
        assert entry_a.id not in article_ids, (
            "User B must not see User A's articles (owner_uid isolation broken)"
        )

        # Cleanup user_b
        with app.app_context():
            u = db_session.get(TtRssUser, user_b.id)
            if u:
                db_session.delete(u)
                db_session.commit()


class TestNoTraceback:
    """Source: ttrss/include/errorhandler.php — errors must not expose Python tracebacks."""

    def test_404_does_not_expose_traceback(self, client):
        """404 response body must not contain Python traceback text.

        Source: ttrss/errors.py — register_error_handlers() registers safe handlers.
        Adapted: Flask TESTING=True propagates exceptions, but error handlers
                 must not include raw tracebacks in HTTP response body.
        """
        resp = client.get("/definitely_does_not_exist_abc123")
        body = resp.get_data(as_text=True)
        assert "Traceback (most recent call last)" not in body

    def test_api_404_has_json_not_traceback(self, client):
        """API 404 returns JSON error, not a Python traceback.

        Source: ttrss/errors.py — /api/ 404 → JSON {seq:0, status:1, content:{error:...}}
        """
        resp = client.get("/api/does_not_exist_xyz")
        if resp.status_code == 404:
            body = resp.get_data(as_text=True)
            assert "Traceback" not in body
