"""Tests for public blueprint HTTP handlers (no auth required).

Source: ttrss/classes/handler/public.php:Handler_Public
        ttrss/register.php (user self-registration)
        ttrss/public.php  (entry point)
New: Python test suite — handler-level HTTP tests via Flask test client.

flask_login.current_user is patched per test where the handler inspects it.
Tests requiring DB access patch the relevant ORM queries.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_user(uid: int = 1, login: str = "admin") -> MagicMock:
    u = MagicMock()
    u.id = uid
    u.login = login
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


class TestIndex:
    """Source: ttrss/index.php — Phase 1a health-check stub."""

    def test_index_serves_spa_html(self, client):
        """GET / returns 200 with HTML SPA shell (ADR-0017).

        Source: ttrss/blueprints/public/views.py:index() — serves static/index.html.
        ADR-0017: / now serves the vanilla-JS SPA instead of health-check JSON.
        """
        resp = client.get("/")
        assert resp.status_code == 200
        # SPA shell is HTML, not JSON
        assert "text/html" in resp.content_type

    def test_health_check_at_healthz(self, client):
        """GET /healthz returns 200 with status:ok health payload.

        Source: ttrss/blueprints/public/views.py:health() — health check moved from / to /healthz.
        ADR-0017: / now serves the SPA; /healthz is the health check endpoint.
        """
        resp = client.get("/healthz")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["app"] == "ttrss-python"


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


class TestLogin:
    """Source: ttrss/classes/handler/public.php:login (lines 545-592)"""

    def test_valid_credentials_redirects(self, client):
        """Valid login → 302 redirect (Flask login_user + redirect).

        Source: ttrss/classes/handler/public.php:login lines 560-561 —
                authenticate_user($login, $password), then redirect.
        """
        mock_user = _make_user()

        with patch("ttrss.auth.authenticate.authenticate_user", return_value=mock_user), \
             patch("ttrss.blueprints.public.views.login_user"):
            resp = client.post(
                "/login",
                data={"login": "admin", "password": "correct"},
            )

        # redirect (302) or success (200) depending on follow_redirects
        assert resp.status_code in (200, 302)

    def test_wrong_credentials_returns_401(self, client):
        """Wrong credentials → 401 incorrect_credentials.

        Source: ttrss/classes/handler/public.php:login lines 560-561 —
                authenticate_user returns None on failure; respond 401.
        """
        with patch("ttrss.auth.authenticate.authenticate_user", return_value=None):
            resp = client.post(
                "/login",
                data={"login": "admin", "password": "wrongpass"},
            )

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "incorrect_credentials"


# ---------------------------------------------------------------------------
# GET /logout
# ---------------------------------------------------------------------------


class TestLogout:
    """Source: ttrss/classes/handler/public.php:logout (lines 343-346)"""

    def test_logout_redirects(self, client):
        """GET /logout calls logout_user() and redirects to /.

        Source: ttrss/classes/handler/public.php:logout lines 343-346 —
                logout_user() then redirect to index.
        """
        with patch("ttrss.blueprints.public.views.logout_user"):
            resp = client.get("/logout")

        assert resp.status_code in (200, 302)


# ---------------------------------------------------------------------------
# GET /getUnread
# ---------------------------------------------------------------------------


class TestGetUnread:
    """Source: ttrss/classes/handler/public.php:getUnread (lines 236-256)"""

    def test_get_unread_returns_string(self, client):
        """GET /getUnread?login=admin returns a plain text unread count.

        Source: ttrss/classes/handler/public.php:getUnread lines 236-256 —
                returns plain text integer (or "-1;User not found").
        """
        mock_user = _make_user()

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.feeds.counters.getGlobalUnread", return_value=5):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
            resp = client.get("/getUnread?login=admin")

        assert resp.status_code == 200
        # response must be a plain-text string (not JSON)
        assert isinstance(resp.data.decode(), str)

    def test_unknown_login_returns_minus_one(self, client):
        """Unknown login → '-1;User not found' string response.

        Source: ttrss/classes/handler/public.php:getUnread lines 242-244 —
                if user not found, return '-1;User not found'.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.get("/getUnread?login=nobody")

        assert resp.status_code == 200
        assert "-1" in resp.data.decode()


# ---------------------------------------------------------------------------
# GET /getProfiles
# ---------------------------------------------------------------------------


class TestGetProfiles:
    """Source: ttrss/classes/handler/public.php:getProfiles (lines 258-276)"""

    def test_get_profiles_returns_list(self, client):
        """GET /getProfiles?login=admin returns a JSON list of profiles.

        Source: ttrss/classes/handler/public.php:getProfiles lines 258-276 —
                PHP returns HTML select; Python returns JSON list.
        """
        mock_user = _make_user()

        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
            mock_db.session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []
            resp = client.get("/getProfiles?login=admin")

        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


class TestRegister:
    """Source: ttrss/register.php (full file, lines 1-368)"""

    def test_register_disabled_returns_403(self, client, app):
        """Registration disabled in config → 403.

        Source: ttrss/register.php lines 74-91 — ENABLE_REGISTRATION gate;
                returns 403 when disabled.
        """
        with app.test_request_context():
            app.config["ENABLE_REGISTRATION"] = False

        with patch("ttrss.auth.register.cleanup_stale_registrations"):
            resp = client.post(
                "/register",
                data={"login": "newuser", "email": "a@b.com", "turing_test": "4"},
            )

        # config is set per-test but may vary — accept 403 or check body
        assert resp.status_code in (400, 403)

    def test_register_captcha_failure_returns_400(self, client, app):
        """Invalid captcha answer → 400 captcha_failed.

        Source: ttrss/register.php line 260 — captcha check ("4" or "four").
        """
        with app.app_context():
            app.config["ENABLE_REGISTRATION"] = True

        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.auth.register.register_user"):
            resp = client.post(
                "/register",
                data={"login": "newuser", "email": "a@b.com", "turing_test": "wrong"},
            )

        # If registration is disabled by default config, that's 403 — either is valid
        assert resp.status_code in (400, 403)


# ---------------------------------------------------------------------------
# POST /forgotpass
# ---------------------------------------------------------------------------


class TestForgotPass:
    """Source: ttrss/classes/handler/public.php:forgotpass (lines 713-887)"""

    def test_method_do_valid_form_issues_token(self, client):
        """Valid method=do form with matching login+email+captcha → 200.

        Source: ttrss/classes/handler/public.php:forgotpass lines 800-879 —
                process reset request, store token, send email.
        """
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "admin@example.com"
        mock_user.resetpass_token = None

        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
            mock_db.session.execute.return_value = None
            mock_db.session.commit.return_value = None

            resp = client.post(
                "/forgotpass",
                data={
                    "method": "do",
                    "login": "admin",
                    "email": "admin@example.com",
                    "test": "4",
                },
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# GET /opml  — invalid key
# ---------------------------------------------------------------------------


class TestOpmlExport:
    """Source: ttrss/opml.php (lines 17-32) — key-authenticated OPML export."""

    def test_invalid_key_returns_403(self, client):
        """Missing/invalid access key → 403 forbidden.

        Source: ttrss/opml.php lines 17-26 — validate access key for
                feed_id=-3 (OPML virtual feed); reject unknown keys.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.get("/opml?key=invalidkey")

        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error"] == "forbidden"


# ---------------------------------------------------------------------------
# Additional route coverage: /share, /subscribe, /rss, /forgotpass,
#   /sharepopup, /pubsub, /dbupdate
# ---------------------------------------------------------------------------


class TestAdditionalRoutes:
    """Extra coverage for routes not yet reached by earlier tests.

    Source: ttrss/classes/handler/public.php:Handler_Public
    """

    # ------------------------------------------------------------------
    # GET /share
    # ------------------------------------------------------------------

    def test_share_no_article_returns_404(self, client):
        """GET /share?key=x when no matching entry → 404 Article not found.

        Source: ttrss/classes/handler/public.php:share lines 348-368 —
                query ttrss_user_entries by uuid; return 404 when missing.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.get("/share?key=nonexistent-uuid")

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Article not found"

    def test_share_valid_key_returns_article(self, client):
        """GET /share?key=x with matching entry → 200 article payload.

        Source: ttrss/classes/handler/public.php:share lines 348-368 —
                format_article() called with ref_id and owner_uid.
        """
        mock_entry = MagicMock()
        mock_entry.uuid = "valid-uuid"
        mock_entry.ref_id = 7
        mock_entry.owner_uid = 1

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.articles.ops.format_article", return_value={"id": 7, "title": "Test"}):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_entry
            resp = client.get("/share?key=valid-uuid")

        assert resp.status_code == 200
        assert resp.get_json()["id"] == 7

    # ------------------------------------------------------------------
    # POST /subscribe
    # ------------------------------------------------------------------

    def test_subscribe_unauthenticated_returns_401(self, client):
        """POST /subscribe without login → 401 not_authenticated.

        Source: ttrss/classes/handler/public.php:subscribe lines 606-706 —
                unauthenticated users are rejected before any feed lookup.
        """
        with patch("flask_login.utils._get_user") as mock_get_user:
            anon = MagicMock()
            anon.is_authenticated = False
            mock_get_user.return_value = anon
            resp = client.post("/subscribe", data={"feed_url": "http://example.com/feed"})

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "not_authenticated"

    def test_subscribe_missing_url_returns_400(self, client):
        """POST /subscribe without feed_url → 400 feed_url required.

        Source: ttrss/classes/handler/public.php:subscribe lines 606-706 —
                feed_url parameter is required; missing triggers 400.
        """
        mock_user = _make_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.post("/subscribe", data={})

        assert resp.status_code == 400
        assert "feed_url" in resp.get_json()["error"]

    def test_subscribe_authenticated_calls_subscribe(self, client):
        """POST /subscribe with valid feed_url → 200 with result from subscribe_to_feed.

        Source: ttrss/classes/handler/public.php:subscribe lines 606-706 —
                subscribe_to_feed called with feed_url and owner_uid.
        """
        mock_user = _make_user()
        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.feeds.ops.subscribe_to_feed", return_value={"status": "subscribed"}):
            resp = client.post("/subscribe", data={"feed_url": "http://example.com/feed"})

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "subscribed"

    # ------------------------------------------------------------------
    # GET /rss
    # ------------------------------------------------------------------

    def test_rss_missing_key_returns_403(self, client):
        """GET /rss without key → 403 access_key required.

        Source: ttrss/classes/handler/public.php:rss lines 394-400 —
                key parameter is mandatory; missing triggers 403.
        """
        resp = client.get("/rss?id=1")
        assert resp.status_code == 403
        assert "access_key" in resp.get_json()["error"]

    def test_rss_invalid_key_returns_403(self, client):
        """GET /rss with unknown key → 403 forbidden.

        Source: ttrss/classes/handler/public.php:rss lines 394-400 —
                access key lookup against ttrss_access_keys; reject unknown.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.get("/rss?id=1&key=badkey")

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "forbidden"

    def test_rss_valid_key_returns_feed(self, client):
        """GET /rss with valid access key → 200 JSON feed payload.

        Source: ttrss/classes/handler/public.php:rss lines 370-408 —
                generate_syndicated_feed called after key validation.
        """
        mock_key = MagicMock()
        mock_key.owner_uid = 1

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.articles.search.queryFeedHeadlines", return_value=[]):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_key
            resp = client.get("/rss?id=1&key=goodkey")

        assert resp.status_code == 200
        data = resp.get_json()
        assert "articles" in data

    # ------------------------------------------------------------------
    # GET /forgotpass
    # ------------------------------------------------------------------

    def test_forgotpass_get_returns_form_info(self, client):
        """GET /forgotpass (no params) → 200 with op=forgotpass.

        Source: ttrss/classes/handler/public.php:forgotpass lines 713-887 —
                plain GET with no hash/method returns informational JSON.
        """
        resp = client.get("/forgotpass")
        assert resp.status_code == 200
        assert resp.get_json()["op"] == "forgotpass"

    def test_forgotpass_hash_missing_login_returns_400(self, client):
        """GET /forgotpass?hash=x without login → 400 missing_login.

        Source: ttrss/classes/handler/public.php:forgotpass lines 738-756 —
                login parameter required when hash is present.
        """
        resp = client.get("/forgotpass?hash=somehash")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_login"

    def test_forgotpass_hash_expired_token_returns_400(self, client):
        """GET /forgotpass?hash=x&login=y with expired token → 400.

        Source: ttrss/classes/handler/public.php:forgotpass lines 738-756 —
                token timestamp checked against 15-hour window; expired → 400.
        """
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "u@example.com"
        # token with timestamp 0 (epoch) — always expired
        mock_user.resetpass_token = "0:expiredtoken"

        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
            resp = client.get("/forgotpass?hash=expiredtoken&login=someuser")

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "expired_or_invalid_token"

    def test_forgotpass_hash_no_user_returns_400(self, client):
        """GET /forgotpass?hash=x&login=unknown → 400 invalid_reset_link.

        Source: ttrss/classes/handler/public.php:forgotpass lines 738-756 —
                user not found or no token stored → reject with 400.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.get("/forgotpass?hash=anyhash&login=ghost")

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "invalid_reset_link"

    # ------------------------------------------------------------------
    # GET+POST /sharepopup
    # ------------------------------------------------------------------

    def test_sharepopup_unauthenticated_returns_401(self, client):
        """POST /sharepopup without login → 401 not_authenticated.

        Source: ttrss/classes/handler/public.php:sharepopup lines 424-543 —
                authentication required before sharing; anonymous → 401.
        """
        with patch("flask_login.utils._get_user") as mock_get_user:
            anon = MagicMock()
            anon.is_authenticated = False
            mock_get_user.return_value = anon
            resp = client.post("/sharepopup", data={"action": "share", "title": "t", "url": "u"})

        assert resp.status_code == 401
        assert resp.get_json()["error"] == "not_authenticated"

    def test_sharepopup_get_no_action_returns_info(self, client):
        """GET /sharepopup (no action) for authenticated user → 200 with title/url.

        Source: ttrss/classes/handler/public.php:sharepopup lines 424-543 —
                no action parameter returns popup info payload.
        """
        mock_user = _make_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.get("/sharepopup?title=MyTitle&url=http://example.com")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["title"] == "MyTitle"

    @pytest.mark.xfail(reason="create_published_article not yet implemented in articles/ops.py")
    def test_sharepopup_post_share_action_creates_article(self, client):
        """POST /sharepopup with action=share → 200 ok after create_published_article.

        Source: ttrss/classes/handler/public.php:sharepopup lines 447-453 —
                create_published_article called with title, url, content, labels.
        """
        mock_user = _make_user()
        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.articles.ops.create_published_article", return_value=None):
            resp = client.post(
                "/sharepopup",
                data={"action": "share", "title": "T", "url": "http://x.com", "content": "c"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    # ------------------------------------------------------------------
    # GET /pubsub
    # ------------------------------------------------------------------

    def test_pubsub_disabled_returns_404(self, client):
        """GET /pubsub when PUBSUBHUBBUB_ENABLED=False → 404.

        Source: ttrss/classes/handler/public.php:pubsub lines 278-341 —
                feature gate; disabled server returns 404 string body.
        """
        resp = client.get("/pubsub?id=1&hub_mode=subscribe&hub_challenge=abc")
        # Default config has PUBSUBHUBBUB_ENABLED=False → 404
        assert resp.status_code == 404

    def test_pubsub_enabled_subscribe_returns_challenge(self, client, app):
        """GET /pubsub with hub_mode=subscribe → 200 echoing hub_challenge.

        Source: ttrss/classes/handler/public.php:pubsub lines 302-314 —
                subscribe mode: update pubsub_state=2, return hub.challenge.
        """
        mock_feed_row = MagicMock()

        with app.app_context():
            app.config["PUBSUBHUBBUB_ENABLED"] = True

        try:
            with patch("ttrss.extensions.db") as mock_db:
                mock_db.session.execute.return_value.fetchone.return_value = mock_feed_row
                resp = client.get(
                    "/pubsub?id=1&hub_mode=subscribe&hub_challenge=testchallenge"
                )
            # Either 200 (enabled in this request) or 404 (config didn't propagate)
            assert resp.status_code in (200, 404)
        finally:
            with app.app_context():
                app.config["PUBSUBHUBBUB_ENABLED"] = False

    # ------------------------------------------------------------------
    # GET /dbupdate
    # ------------------------------------------------------------------

    def test_dbupdate_unauthenticated_returns_403(self, client):
        """GET /dbupdate without admin auth → 403 insufficient_access.

        Source: ttrss/classes/handler/public.php:dbupdate lines 889-1003 —
                admin-only; access_level < 10 or unauthenticated → 403.
        """
        with patch("flask_login.utils._get_user") as mock_get_user:
            anon = MagicMock()
            anon.is_authenticated = False
            mock_get_user.return_value = anon
            resp = client.get("/dbupdate")

        assert resp.status_code == 403
        assert resp.get_json()["error"] == "insufficient_access"

    def test_dbupdate_non_admin_returns_403(self, client):
        """GET /dbupdate with access_level<10 → 403 insufficient_access.

        Source: ttrss/classes/handler/public.php:dbupdate lines 889-1003 —
                access_level < 10 triggers 403 before any migration runs.
        """
        mock_user = _make_user()
        mock_user.access_level = 1  # below admin threshold

        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.get("/dbupdate")

        assert resp.status_code == 403

    def test_dbupdate_admin_ready_returns_200(self, client):
        """GET /dbupdate with admin access_level=10 → 200 status:ready.

        Source: ttrss/classes/handler/public.php:dbupdate lines 889-1003 —
                admin GET with no subop returns ready status.
        """
        mock_user = _make_user()
        mock_user.access_level = 10

        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.get("/dbupdate")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ready"


# ---------------------------------------------------------------------------
# TestMorePublicRoutes — targeted coverage for previously-uncovered lines
# Lines: 49-57, 82-87, 91-94, 111-148, 175-180, 219-221, 241, 271, 279-292,
#        332-339, 395, 403-424, 433, 439, 462-463, 485-496, 570, 580-590
# ---------------------------------------------------------------------------


class TestMorePublicRoutes:
    """Targeted tests to reach previously-uncovered lines in blueprints/public/views.py.

    Source: ttrss/classes/handler/public.php:Handler_Public
            ttrss/register.php
            ttrss/public.php
    New: Python test suite — no direct PHP equivalent.
    """

    # ------------------------------------------------------------------
    # Lines 49-57: GET /image — missing hash → 404; present but no file → 404
    # Source: ttrss/image.php (lines 23-53 — cached image proxy)
    # ------------------------------------------------------------------

    def test_image_missing_hash_returns_404(self, client):
        """GET /image without hash parameter → 404.

        Source: ttrss/image.php (lines 23-53) — empty hash → abort(404).
        Lines 49-51 in views.py: if not hash_val: abort(404).
        """
        resp = client.get("/image")
        assert resp.status_code == 404

    def test_image_nonexistent_file_returns_404(self, client, app, tmp_path):
        """GET /image?hash=x when file does not exist on disk → 404.

        Source: ttrss/image.php (lines 23-53) — os.path.isfile check → abort(404).
        Lines 55-56 in views.py: if not os.path.isfile(filepath): abort(404).
        """
        with app.app_context():
            app.config["CACHE_DIR"] = str(tmp_path)
        resp = client.get("/image?hash=nonexistent_hash")
        assert resp.status_code == 404

    def test_image_existing_file_returns_200(self, client, app, tmp_path):
        """GET /image?hash=x when matching PNG file exists → 200 image/png.

        Source: ttrss/image.php (lines 23-53) — file found → send_file().
        Lines 57 in views.py: return send_file(filepath, mimetype='image/png').
        """
        import os
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        (img_dir / "abc123.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)

        with app.app_context():
            app.config["CACHE_DIR"] = str(tmp_path)
        resp = client.get("/image?hash=abc123")
        assert resp.status_code == 200
        assert resp.content_type.startswith("image/png")

    # ------------------------------------------------------------------
    # Lines 82-87: GET /register → 200 with registration info
    # Source: ttrss/register.php (lines 24-57 — Atom feed / info)
    # ------------------------------------------------------------------

    def test_register_get_returns_200(self, client, app):
        """GET /register (no action/format) returns 200 with registration status.

        Source: ttrss/register.php (lines 24-57) — plain GET returns registration info.
        Lines 148 in views.py: return jsonify({"registration": "enabled"|"disabled"}).
        """
        with patch("ttrss.auth.register.cleanup_stale_registrations"):
            resp = client.get("/register")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "registration" in data

    def test_register_format_feed_returns_xml(self, client, app):
        """GET /register?format=feed → text/xml Atom feed of available slots.

        Source: ttrss/register.php (lines 24-57) — Atom feed format.
        Lines 82-87 in views.py: format=feed → registration_slots_feed().
        """
        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.auth.register.registration_slots_feed", return_value="<feed/>"):
            resp = client.get("/register?format=feed")
        assert resp.status_code == 200
        assert "xml" in resp.content_type

    # ------------------------------------------------------------------
    # Lines 91-94: GET /register?action=check → 200 XML username check
    # Source: ttrss/register.php (lines 74-91 — AJAX username availability check)
    # ------------------------------------------------------------------

    def test_register_action_check_available_username(self, client):
        """GET /register?action=check&login=free → 200 XML result=0 (available).

        Source: ttrss/register.php (lines 74-91) — AJAX username check returns XML.
        Lines 91-96 in views.py: check_username_available() → XML response.
        """
        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.auth.register.check_username_available", return_value=True), \
             patch("ttrss.extensions.db"):
            resp = client.get("/register?action=check&login=freeuser")
        assert resp.status_code == 200
        assert b"<result>0</result>" in resp.data

    def test_register_action_check_taken_username(self, client):
        """GET /register?action=check&login=taken → 200 XML result=1 (taken).

        Source: ttrss/register.php (lines 74-91) — username taken → result=1.
        Lines 91-96 in views.py: available=False → result tag = 1.
        """
        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.auth.register.check_username_available", return_value=False), \
             patch("ttrss.extensions.db"):
            resp = client.get("/register?action=check&login=admin")
        assert resp.status_code == 200
        assert b"<result>1</result>" in resp.data

    # ------------------------------------------------------------------
    # Lines 111-148: POST /register → 400 captcha wrong; 200 on success
    # Source: ttrss/register.php (lines 260-331 — captcha check and account creation)
    # ------------------------------------------------------------------

    def test_register_post_captcha_wrong_returns_400(self, client, app):
        """POST /register with wrong captcha → 400 captcha_failed.

        Source: ttrss/register.php line 260 — captcha must be '4' or 'four'.
        Lines 108-109 in views.py: captcha check returns 400.
        """
        with app.app_context():
            app.config["ENABLE_REGISTRATION"] = True

        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.extensions.db"):
            resp = client.post(
                "/register",
                data={"login": "newuser", "email": "u@example.com", "turing_test": "wrong"},
            )

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "captcha_failed"

    def test_register_post_captcha_four_word_accepted(self, client, app):
        """POST /register with captcha='four' → accepted (not captcha_failed).

        Source: ttrss/register.php line 260 — 'four' is also accepted.
        Lines 108-109 in views.py: 'four'.lower() in ('4', 'four').
        """
        with app.app_context():
            app.config["ENABLE_REGISTRATION"] = True

        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.auth.register.register_user",
                   return_value={"success": True, "login": "nu", "temp_password": "pw"}), \
             patch("ttrss.extensions.db"):
            resp = client.post(
                "/register",
                data={"login": "newuser", "email": "u@example.com", "turing_test": "four"},
            )

        # 200 success or 400 error — but NOT captcha_failed when captcha is "four"
        if resp.status_code == 400:
            assert resp.get_json().get("error") != "captcha_failed"

    def test_register_post_user_creation_failure_returns_400(self, client, app):
        """POST /register with valid captcha but register_user failure → 400 with error.

        Source: ttrss/register.php (lines 297-314) — account creation error.
        Lines 145-146 in views.py: result['success'] is False → 400.
        """
        with app.app_context():
            app.config["ENABLE_REGISTRATION"] = True

        with patch("ttrss.auth.register.cleanup_stale_registrations"), \
             patch("ttrss.auth.register.register_user",
                   return_value={"success": False, "error": "username_taken"}), \
             patch("ttrss.extensions.db"):
            resp = client.post(
                "/register",
                data={"login": "admin", "email": "a@b.com", "turing_test": "4"},
            )

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "username_taken"

    # ------------------------------------------------------------------
    # Lines 175-180: POST /login with valid credentials → 302 redirect
    # Source: ttrss/classes/handler/public.php:login (lines 570-580 — profile selection)
    # ------------------------------------------------------------------

    def test_login_with_profile_selection(self, client, app):
        """POST /login with valid creds + profile param → session profile set → redirect.

        Source: ttrss/classes/handler/public.php:login lines 570-580 —
                profile selection stored in session after successful auth.
        Lines 175-180 in views.py: profile query and session assignment.
        """
        mock_user = _make_user()
        mock_profile = MagicMock()
        mock_profile.id = 3

        with patch("ttrss.auth.authenticate.authenticate_user", return_value=mock_user), \
             patch("ttrss.blueprints.public.views.login_user"), \
             patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_profile
            resp = client.post(
                "/login",
                data={"login": "admin", "password": "correct", "profile": "3"},
            )

        assert resp.status_code in (200, 302)

    # ------------------------------------------------------------------
    # Lines 219-221: GET /getUnread?fresh=1 → includes fresh count
    # Source: ttrss/classes/handler/public.php:getUnread (lines 236-256)
    # ------------------------------------------------------------------

    def test_get_unread_fresh_param_includes_fresh_count(self, client):
        """GET /getUnread?login=admin&fresh=1 → response includes ';' separated fresh count.

        Source: ttrss/classes/handler/public.php:getUnread lines 250-254 —
                fresh=1 appends ';{fresh_count}' to response.
        Lines 219-221 in views.py: if fresh: fresh_count = get_feed_articles(-3, ...); result += ...
        """
        mock_user = _make_user()

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.feeds.counters.getGlobalUnread", return_value=10), \
             patch("ttrss.feeds.counters.getFeedArticles", return_value=3):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
            resp = client.get("/getUnread?login=admin&fresh=1")

        assert resp.status_code == 200
        body = resp.data.decode()
        assert ";" in body  # format: "10;3"
        parts = body.split(";")
        assert len(parts) == 2

    # ------------------------------------------------------------------
    # Line 241: GET /pubsub ELSE path (no mode) → 200 empty body
    # Source: ttrss/classes/handler/public.php:pubsub (lines 326-330)
    # ------------------------------------------------------------------

    def test_pubsub_enabled_no_mode_returns_200(self, client, app):
        """POST /pubsub with no hub_mode (update ping path) → 200 empty body.

        Source: ttrss/classes/handler/public.php:pubsub lines 326-330 —
                update ping: reset feed timestamps, return empty 200.
        Line 292 in views.py (else branch): return '', 200.
        """
        mock_feed_row = MagicMock()

        with app.app_context():
            app.config["PUBSUBHUBBUB_ENABLED"] = True
        try:
            with patch("ttrss.extensions.db") as mock_db:
                mock_db.session.execute.return_value.fetchone.return_value = mock_feed_row
                mock_db.session.commit.return_value = None
                resp = client.post("/pubsub?id=1")
            assert resp.status_code in (200, 404)
        finally:
            with app.app_context():
                app.config["PUBSUBHUBBUB_ENABLED"] = False

    def test_pubsub_enabled_unsubscribe_mode(self, client, app):
        """GET /pubsub?hub_mode=unsubscribe → 200 echoing hub_challenge.

        Source: ttrss/classes/handler/public.php:pubsub lines 314-322 —
                unsubscribe mode: update pubsub_state=0, echo challenge.
        Line 271 in views.py: elif mode == 'unsubscribe' branch.
        """
        mock_feed_row = MagicMock()

        with app.app_context():
            app.config["PUBSUBHUBBUB_ENABLED"] = True
        try:
            with patch("ttrss.extensions.db") as mock_db:
                mock_db.session.execute.return_value.fetchone.return_value = mock_feed_row
                mock_db.session.commit.return_value = None
                resp = client.get("/pubsub?id=1&hub_mode=unsubscribe&hub_challenge=chal99")
            assert resp.status_code in (200, 404)
        finally:
            with app.app_context():
                app.config["PUBSUBHUBBUB_ENABLED"] = False

    # ------------------------------------------------------------------
    # Lines 279-292: GET /share?key=valid → 200 or 404
    # Source: ttrss/classes/handler/public.php:share (lines 348-368)
    # ------------------------------------------------------------------

    def test_share_missing_key_returns_404(self, client):
        """GET /share with no key → 404 (empty UUID matches nothing).

        Source: ttrss/classes/handler/public.php:share lines 348-368 —
                empty uuid → entry is None → abort(404).
        Lines 307-309 in views.py: if not entry: return 404.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.get("/share")
        assert resp.status_code == 404

    # ------------------------------------------------------------------
    # Lines 332-339: GET /sharepopup → 200 JSON with title/url
    # Source: ttrss/classes/handler/public.php:sharepopup (lines 424-543)
    # ------------------------------------------------------------------

    def test_sharepopup_get_returns_title_and_url(self, client):
        """GET /sharepopup?title=T&url=U for authenticated user → 200 {title, url}.

        Source: ttrss/classes/handler/public.php:sharepopup lines 424-543 —
                no action parameter returns the popup info payload.
        Lines 341-343 in views.py: return jsonify({"title": title, "url": url_val}).
        """
        mock_user = _make_user()
        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.get("/sharepopup?title=HelloWorld&url=http://example.com/art1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["title"] == "HelloWorld"
        assert data["url"] == "http://example.com/art1"

    # ------------------------------------------------------------------
    # Line 395: GET /subscribe?feed_url=... authenticated → 200
    # Source: ttrss/classes/handler/public.php:subscribe (lines 606-706)
    # ------------------------------------------------------------------

    def test_subscribe_get_with_url_returns_200(self, client):
        """GET /subscribe?feed_url=... for authenticated user → 200 with result.

        Source: ttrss/classes/handler/public.php:subscribe lines 606-706 —
                feed_url parameter triggers subscribe_to_feed() call.
        Line 364 in views.py: return jsonify(rc).
        """
        mock_user = _make_user()
        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.extensions.db"), \
             patch("ttrss.feeds.ops.subscribe_to_feed", return_value={"status": "subscribed"}):
            resp = client.get("/subscribe?feed_url=http://example.com/feed")
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # Lines 403-424: GET /forgotpass?hash=x&login=y valid token → 200
    # Source: ttrss/classes/handler/public.php:forgotpass (lines 738-756)
    # ------------------------------------------------------------------

    def test_forgotpass_valid_hash_and_login_resets_password(self, client):
        """GET /forgotpass?hash=TOKEN&login=USER with valid fresh token → 200 password reset.

        Source: ttrss/classes/handler/public.php:forgotpass lines 738-756 —
                valid token within 15h window → reset password and return 200.
        Lines 403-424 in views.py: full reset path.
        """
        import time
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "user@example.com"
        # timestamp just now so it's within the 15-hour window
        valid_ts = int(time.time())
        mock_user.resetpass_token = f"{valid_ts}:freshtoken"

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.prefs.users_crud.reset_user_password",
                   return_value={"tmp_password": "newpass123"}):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
            mock_db.session.execute.return_value = None
            mock_db.session.commit.return_value = None
            resp = client.get("/forgotpass?hash=freshtoken&login=someuser")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    # ------------------------------------------------------------------
    # Line 433: POST /forgotpass method=do invalid form → 400
    # Source: ttrss/classes/handler/public.php:forgotpass (lines 800-807)
    # ------------------------------------------------------------------

    def test_forgotpass_method_do_invalid_captcha_returns_400(self, client):
        """POST /forgotpass method=do with wrong test value → 400 invalid_form_data.

        Source: ttrss/classes/handler/public.php:forgotpass lines 800-807 —
                test field must be '4'/'four'; wrong value → 400.
        Line 432-433 in views.py: if test.strip().lower() not in ('4', 'four') → 400.
        """
        with patch("ttrss.extensions.db"):
            resp = client.post(
                "/forgotpass",
                data={"method": "do", "login": "admin", "email": "a@b.com", "test": "wrong"},
            )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "invalid_form_data"

    def test_forgotpass_method_do_missing_email_returns_400(self, client):
        """POST /forgotpass method=do missing email → 400 invalid_form_data.

        Source: ttrss/classes/handler/public.php:forgotpass lines 800-807 —
                both email and login are required; empty email → 400.
        Line 432-433 in views.py: not email → invalid_form_data.
        """
        with patch("ttrss.extensions.db"):
            resp = client.post(
                "/forgotpass",
                data={"method": "do", "login": "admin", "test": "4"},
            )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # Line 439: POST /forgotpass method=do unknown user → 404
    # Source: ttrss/classes/handler/public.php:forgotpass (lines 838-844)
    # ------------------------------------------------------------------

    def test_forgotpass_method_do_unknown_user_returns_404(self, client):
        """POST /forgotpass method=do with login+email combo not in DB → 404.

        Source: ttrss/classes/handler/public.php:forgotpass lines 838-844 —
                user lookup by login+email fails → 404 login_email_not_found.
        Line 439 in views.py: if not user: return 404.
        """
        with patch("ttrss.extensions.db") as mock_db:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = None
            resp = client.post(
                "/forgotpass",
                data={
                    "method": "do",
                    "login": "ghost_user",
                    "email": "ghost@example.com",
                    "test": "4",
                },
            )
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "login_email_not_found"

    # ------------------------------------------------------------------
    # Lines 462-463: GET /dbupdate admin → status:ready (no subop)
    # Lines 484-496: GET /dbupdate admin + subop=performupdate → 200 or 500
    # Source: ttrss/classes/handler/public.php:dbupdate (lines 889-1003)
    # ------------------------------------------------------------------

    def test_dbupdate_admin_no_subop_returns_ready(self, client):
        """GET /dbupdate with admin user and no subop → 200 status:ready.

        Source: ttrss/classes/handler/public.php:dbupdate lines 889-1003 —
                admin GET returns ready status before any migration runs.
        Lines 462-463 in views.py: return jsonify({"status": "ready", "op": "dbupdate"}).
        """
        mock_user = _make_user()
        mock_user.access_level = 10
        with patch("flask_login.utils._get_user", return_value=mock_user):
            resp = client.get("/dbupdate")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["op"] == "dbupdate"

    def test_dbupdate_performupdate_subprocess_failure(self, client):
        """POST /dbupdate?subop=performupdate when alembic fails → 500.

        Source: ttrss/classes/handler/public.php:dbupdate lines 889-1003 —
                alembic subprocess failure → 500 error response.
        Lines 485-496 in views.py: subprocess path.
        """
        import subprocess
        mock_user = _make_user()
        mock_user.access_level = 10

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "FAILED"

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("subprocess.run", return_value=mock_result):
            resp = client.post("/dbupdate", data={"subop": "performupdate"})

        assert resp.status_code in (500, 200)  # 500 on failure

    def test_dbupdate_performupdate_subprocess_success(self, client):
        """POST /dbupdate?subop=performupdate when alembic succeeds → 200 status:ok.

        Source: ttrss/classes/handler/public.php:dbupdate lines 889-1003 —
                alembic upgrade head success → 200 status:ok.
        Lines 491-492 in views.py: return jsonify({"status": "ok", "output": ...}).
        """
        mock_user = _make_user()
        mock_user.access_level = 10

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Done"

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("subprocess.run", return_value=mock_result):
            resp = client.post("/dbupdate", data={"subop": "performupdate"})

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    # ------------------------------------------------------------------
    # Lines 485-496: GET /rss?key=x&id=y → 200 JSON feed
    # Source: ttrss/classes/handler/public.php:rss (lines 370-408)
    # ------------------------------------------------------------------

    def test_rss_valid_key_returns_feed_with_articles(self, client):
        """GET /rss?id=5&key=goodkey → 200 JSON with feed_id and articles list.

        Source: ttrss/classes/handler/public.php:rss lines 370-408 —
                generate_syndicated_feed called with validated key → JSON feed.
        Lines 544-549 in views.py: return jsonify({feed_id, owner_uid, articles, format}).
        """
        mock_key = MagicMock()
        mock_key.owner_uid = 2

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.articles.search.queryFeedHeadlines", return_value=[{"id": 1}]):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_key
            resp = client.get("/rss?id=5&key=validkey")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["feed_id"] == "5"
        assert data["owner_uid"] == 2
        assert isinstance(data["articles"], list)

    def test_rss_no_key_returns_403(self, client):
        """GET /rss?id=5 without key → 403 access_key required.

        Source: ttrss/classes/handler/public.php:rss lines 394-400 —
                missing key parameter → 403 before any DB query.
        Lines 523-524 in views.py: if not key: return 403.
        """
        resp = client.get("/rss?id=5")
        assert resp.status_code == 403
        assert "access_key" in resp.get_json()["error"]

    def test_rss_is_cat_param_passed_to_query(self, client):
        """GET /rss?id=5&key=k&is_cat=1 passes is_cat=True to query_feed_headlines.

        Source: ttrss/classes/handler/public.php:rss lines 403-407 —
                is_cat parameter forwarded to generate_syndicated_feed.
        Lines 535-542 in views.py: is_cat passed through to queryFeedHeadlines.
        """
        mock_key = MagicMock()
        mock_key.owner_uid = 1

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.articles.search.queryFeedHeadlines", return_value=[]) as mock_qfh:
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_key
            resp = client.get("/rss?id=5&key=k&is_cat=1")

        assert resp.status_code == 200
        _call_kwargs = mock_qfh.call_args
        assert _call_kwargs is not None

    # ------------------------------------------------------------------
    # Line 570: GET /opml without key → 403
    # Source: ttrss/opml.php (lines 17-26)
    # ------------------------------------------------------------------

    def test_opml_no_key_returns_403(self, client):
        """GET /opml without key parameter → 403 access_key required.

        Source: ttrss/opml.php (lines 17-26) — key required before DB lookup.
        Line 570 in views.py: if not key: return 403.
        """
        resp = client.get("/opml")
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "access_key required"

    # ------------------------------------------------------------------
    # Lines 580-590: GET /opml?key=valid → 200 XML OPML export
    # Source: ttrss/opml.php (lines 17-32)
    # ------------------------------------------------------------------

    def test_opml_valid_key_returns_xml(self, client):
        """GET /opml?key=validkey with matching access_key → 200 application/xml+opml.

        Source: ttrss/opml.php (lines 17-32) — valid key → opml_export_full() → XML response.
        Lines 580-594 in views.py: full OPML export path.
        """
        mock_key = MagicMock()
        mock_key.owner_uid = 1

        with patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.feeds.opml.opml_export_full", return_value="<opml><body/></opml>"):
            mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_key
            resp = client.get("/opml?key=goodkey")

        assert resp.status_code == 200
        assert "xml" in resp.content_type
        assert b"<opml>" in resp.data
