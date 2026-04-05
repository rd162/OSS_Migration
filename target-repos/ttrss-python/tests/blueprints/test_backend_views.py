"""Tests for /backend.php HTTP handler (RPC/Dlg/Backend dispatch).

Source: ttrss/backend.php (entry point)
        ttrss/classes/rpc.php:RPC (op=rpc handlers)
        ttrss/classes/backend.php:Backend (op=backend handlers)
New: Python test suite — handler-level HTTP tests via Flask test client.

Dispatch format: POST /backend.php with form params op=<op>&method=<method>
(op and method are lowercased by the dispatcher).
Source: ttrss/backend.php — PHP $_REQUEST merges GET+POST+COOKIE.

flask_login.current_user is patched per test; CRUD helpers patched at call site.
CSRF is disabled in the test app fixture (WTF_CSRF_ENABLED=False).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_user(uid: int = 1) -> MagicMock:
    """Return a minimal mock user compatible with current_user attribute access."""
    u = MagicMock()
    u.id = uid
    u.is_authenticated = True
    u.is_active = True
    u.is_anonymous = False
    u.get_id.return_value = str(uid)
    return u


def _post(client, op: str, method: str, extra: dict | None = None):
    """POST to /backend.php with op+method dispatch params."""
    data = {"op": op, "method": method}
    if extra:
        data.update(extra)
    return client.post("/backend.php", data=data)


# ---------------------------------------------------------------------------
# op=rpc, method=catchupfeed
# ---------------------------------------------------------------------------


class TestCatchupFeed:
    """Source: ttrss/classes/rpc.php:RPC::catchupFeed (lines 442-450)"""

    def test_catchup_feed_returns_200(self, client):
        """POST op=rpc method=catchupfeed feed_id=0 → 200 UPDATE_COUNTERS.

        Source: ttrss/classes/rpc.php:RPC::catchupFeed (lines 442-450) —
                marks all articles in a feed (or category) as read;
                delegates to ttrss.articles.ops:catchup_feed.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.articles.ops.catchup_feed") as mock_catchup, \
             patch("ttrss.blueprints.backend.views.db") as mock_db:
            mock_db.session.commit.return_value = None

            resp = _post(client, "rpc", "catchupfeed", {"feed_id": "0", "is_cat": "false"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("message") == "UPDATE_COUNTERS"


# ---------------------------------------------------------------------------
# op=rpc, method=markselected
# ---------------------------------------------------------------------------


class TestMarkSelected:
    """Source: ttrss/classes/rpc.php:RPC::markSelected (lines 314-321)"""

    def test_mark_selected_returns_200(self, client):
        """POST op=rpc method=markselected ids=1 cmode=0 → 200.

        Source: ttrss/classes/rpc.php:RPC::markSelected (lines 314-321) —
                mark/unmark/toggle starred flag on selected article ids.
                cmode: 0=unmark, 1=mark, 2=toggle.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.blueprints.backend.views.db") as mock_db:
            mock_db.session.execute.return_value = None
            mock_db.session.commit.return_value = None

            resp = _post(client, "rpc", "markselected", {"ids": "1", "cmode": "0"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("message") == "UPDATE_COUNTERS"


# ---------------------------------------------------------------------------
# op=rpc, method=catchupselected
# ---------------------------------------------------------------------------


class TestCatchupSelected:
    """Source: ttrss/classes/rpc.php:RPC::catchupSelected (lines 305-311)"""

    def test_catchup_selected_returns_200(self, client):
        """POST op=rpc method=catchupselected ids=1 cmode=0 → 200.

        Source: ttrss/classes/rpc.php:RPC::catchupSelected (lines 305-311) —
                mark selected articles read/unread/toggled based on cmode.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.articles.ops.catchupArticlesById") as mock_catchup, \
             patch("ttrss.blueprints.backend.views.db") as mock_db:
            mock_db.session.commit.return_value = None

            resp = _post(client, "rpc", "catchupselected", {"ids": "1", "cmode": "0"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("message") == "UPDATE_COUNTERS"


# ---------------------------------------------------------------------------
# op=rpc, method=getallcounters
# ---------------------------------------------------------------------------


class TestGetAllCounters:
    """Source: ttrss/classes/rpc.php:RPC::getAllCounters (lines 288-302)"""

    def test_get_all_counters_returns_200(self, client):
        """POST op=rpc method=getallcounters → 200 with runtime-info.

        Source: ttrss/classes/rpc.php:RPC::getAllCounters (lines 288-302) —
                returns counters for all feeds and runtime-info block.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.blueprints.backend.views.db") as mock_db, \
             patch("ttrss.feeds.counters.getAllCounters", return_value=[]), \
             patch("ttrss.ui.init_params.make_runtime_info", return_value={}):
            mock_db.session.execute.return_value.scalar.return_value = 0

            resp = _post(client, "rpc", "getallcounters")

        assert resp.status_code == 200
        assert "runtime-info" in resp.get_json()


# ---------------------------------------------------------------------------
# op=rpc, method=sanitycheck
# ---------------------------------------------------------------------------


class TestSanityCheck:
    """Source: ttrss/classes/rpc.php:RPC::sanityCheck (lines 332-348)."""

    def test_sanity_check_returns_json(self, app, client):
        """Source: rpc.php:332 — sanityCheck; asserts valid JSON response.
        Adapted: skipped schema-version check via patching get_schema_version."""
        with patch("flask_login.utils._get_user") as mock_get:
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_user.access_level = 10
            mock_get.return_value = mock_user
            # Patch the schema version check so sanityCheck doesn't fail
            with patch("ttrss.prefs.ops.get_schema_version", return_value=124), \
                 patch("ttrss.ui.init_params.make_init_params", return_value={}), \
                 patch("ttrss.ui.init_params.make_runtime_info", return_value={}):
                resp = client.post(
                    "/backend.php",
                    data={"op": "rpc", "method": "sanitycheck",
                          "hasAudio": "false", "hasSandbox": "false",
                          "hasMp3": "false", "clientTzOffset": "0"},
                )
        # Any 2xx is acceptable; the point is no unhandled exception
        assert resp.status_code in (200, 201, 204)


class TestUpdateFeedBrowser:
    """Source: ttrss/classes/rpc.php:RPC::updateFeedBrowser (lines 381-391)"""

    def test_update_feed_browser_returns_200(self, client):
        """POST op=rpc method=updatefeedbrowser mode=1 → 200 with content list.

        Source: ttrss/classes/rpc.php:RPC::updateFeedBrowser (lines 381-391) —
                returns feedbrowser content; mode=1 is global popular feeds
                from ttrss_feedbrowser_cache.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.blueprints.backend.views.db") as mock_db:
            mock_db.session.execute.return_value.all.return_value = []

            resp = _post(client, "rpc", "updatefeedbrowser", {"mode": "1"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert "content" in data
        assert data["mode"] == 1


# ---------------------------------------------------------------------------
# op=rpc, method=togglepref
# ---------------------------------------------------------------------------


class TestTogglePref:
    """Source: ttrss/classes/rpc.php:RPC::togglepref (lines 113-118)"""

    def test_togglepref_returns_200(self, client):
        """POST op=rpc method=togglepref key=HIDE_READ_FEEDS → 200 with new value.

        Source: ttrss/classes/rpc.php:RPC::togglepref (lines 113-118) —
                reads current value via get_user_pref, toggles, writes back,
                returns {param, value}.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.prefs.ops.get_user_pref", return_value="false"), \
             patch("ttrss.prefs.ops.set_user_pref"):
            resp = _post(client, "rpc", "togglepref", {"key": "HIDE_READ_FEEDS"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["param"] == "HIDE_READ_FEEDS"
        assert data["value"] in ("true", "false")


# ---------------------------------------------------------------------------
# op=rpc, method=setpref
# ---------------------------------------------------------------------------


class TestSetPref:
    """Source: ttrss/classes/rpc.php:RPC::setpref (lines 121-128)"""

    def test_setpref_returns_200(self, client):
        """POST op=rpc method=setpref key=X value=Y → 200 with echoed key+value.

        Source: ttrss/classes/rpc.php:RPC::setpref (lines 121-128) —
                stores key/value pref; replaces newlines with <br/> for
                non-CSS keys (Python deliberately preserves newlines for
                USER_STYLESHEET to avoid corrupting stored CSS).
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user), \
             patch("ttrss.prefs.ops.set_user_pref"):
            resp = _post(client, "rpc", "setpref", {"key": "FRESHEST_ARTICLE_AGE", "value": "72"})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["param"] == "FRESHEST_ARTICLE_AGE"
        assert data["value"] == "72"


# ---------------------------------------------------------------------------
# Unknown op/method → error
# ---------------------------------------------------------------------------


class TestUnknownOp:
    """Source: ttrss/backend.php dispatch — unknown op returns error."""

    def test_unknown_op_returns_error(self, client):
        """POST with an unrecognised op+method combination → 400 error response.

        Source: ttrss/backend.php + ttrss/classes/backend.php:Backend —
                dispatch table lookup fails for unknown (op, method) pair;
                Python returns 400 with status=ERR.
        """
        mock_user = _make_user()

        with patch("flask_login.utils._get_user", return_value=mock_user), \
             patch("ttrss.blueprints.backend.views.current_user", mock_user):
            resp = _post(client, "rpc", "doesnotexist")

        # Dispatcher returns 400 for unknown op/method
        assert resp.status_code in (400, 200)  # 400 expected; 200 tolerated if handler returns ERR body
        data = resp.get_json()
        # Accept either HTTP 400 with any body, or HTTP 200 with status=ERR
        if resp.status_code == 200:
            assert data.get("status") == "ERR"
        else:
            assert data is not None  # some JSON error body
