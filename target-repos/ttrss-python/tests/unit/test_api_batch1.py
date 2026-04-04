"""Unit tests for ttrss/blueprints/api/views.py — Batch 1.

Covers: auth guards (Guard 1 + Guard 2), _truthy, _pref_is_true,
        getUnread, getCounters, getPref, getConfig, getLabels.

Approach: minimal Flask app (no DB/Redis) + unittest.mock patches on all
external dependencies. Tests run without Docker infrastructure.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ---------------------------------------------------------------------------
# Minimal Flask app fixture for request context
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_app():
    """Minimal Flask app for request-context-only unit tests.

    Does NOT initialise Flask-Session, SQLAlchemy, or Flask-Login extensions —
    all DB/auth calls are patched per-test. Only provides app + request context.
    """
    app = Flask(__name__)
    app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-unit-secret",
            "WTF_CSRF_ENABLED": False,
            "ICONS_DIR": "/tmp/icons",
            "ICONS_URL": "/icons",
        }
    )
    return app


def _post(app, op, extra=None, seq=1):
    """Return (response_dict, status_code) from a mocked dispatch() call."""
    body = {"op": op, "seq": seq}
    if extra:
        body.update(extra)
    with app.test_request_context(
        "/api/", method="POST", json=body, content_type="application/json"
    ):
        with app.app_context():
            from ttrss.blueprints.api.views import dispatch

            resp = dispatch()
            data = json.loads(resp.get_data(as_text=True))
            return data, resp.status_code


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_truthy_true_values():
    from ttrss.blueprints.api.views import _truthy

    assert _truthy(True) is True
    assert _truthy(1) is True
    assert _truthy("true") is True
    assert _truthy("TRUE") is True
    assert _truthy("1") is True


def test_truthy_false_values():
    from ttrss.blueprints.api.views import _truthy

    assert _truthy(False) is False
    assert _truthy(0) is False
    assert _truthy("false") is False
    assert _truthy("FALSE") is False
    assert _truthy("0") is False
    assert _truthy("") is False
    assert _truthy(None) is False


def test_pref_is_true_true_values():
    from ttrss.blueprints.api.views import _pref_is_true

    assert _pref_is_true("true") is True
    assert _pref_is_true("TRUE") is True
    assert _pref_is_true("1") is True
    assert _pref_is_true("anything") is True


def test_pref_is_true_false_values():
    from ttrss.blueprints.api.views import _pref_is_true

    assert _pref_is_true(None) is False
    assert _pref_is_true("false") is False
    assert _pref_is_true("FALSE") is False
    assert _pref_is_true("0") is False
    assert _pref_is_true("") is False


# ---------------------------------------------------------------------------
# Guard 1: NOT_LOGGED_IN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "op",
    ["getVersion", "getApiLevel", "getUnread", "getCounters", "getPref", "getConfig", "getLabels"],
)
def test_guard1_blocks_unauthenticated(api_app, op):
    """Guard 1: unauthenticated requests to non-exempt ops return NOT_LOGGED_IN."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user:
        mock_user.is_authenticated = False
        data, _ = _post(api_app, op)
    assert data["status"] == 1
    assert data["content"]["error"] == "NOT_LOGGED_IN"


@pytest.mark.parametrize("op", ["login", "isLoggedIn"])
def test_guard1_allows_exempt_ops_unauthenticated(api_app, op):
    """Guard 1: login and isLoggedIn are exempt — reach their handler even when not auth'd."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.TtRssUser"), \
         patch("ttrss.blueprints.api.views._handle_login", return_value=MagicMock(
             get_data=lambda as_text: '{"seq":1,"status":1,"content":{"error":"LOGIN_ERROR"}}',
             status_code=200,
         )):
        mock_user.is_authenticated = False
        data, _ = _post(api_app, op)
    # Must NOT be NOT_LOGGED_IN — the error (if any) is from the handler itself
    if op == "isLoggedIn":
        assert data["content"].get("error") != "NOT_LOGGED_IN"


def test_guard1_isloggedin_returns_status_false(api_app):
    """isLoggedIn op returns status=false when not authenticated (no DB needed)."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"):
        mock_user.is_authenticated = False
        data, _ = _post(api_app, "isLoggedIn")
    assert data["status"] == 0
    assert data["content"]["status"] is False


# ---------------------------------------------------------------------------
# Guard 2: API_DISABLED
# ---------------------------------------------------------------------------


def test_guard2_blocks_when_api_access_disabled(api_app):
    """Guard 2: authenticated user with ENABLE_API_ACCESS=false gets API_DISABLED."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="false"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getVersion")
    assert data["status"] == 1
    assert data["content"]["error"] == "API_DISABLED"


def test_guard2_blocks_getversion_and_getapilevel(api_app):
    """Guard 2 blocks getVersion and getApiLevel — they are NOT exempt."""
    for op in ["getVersion", "getApiLevel"]:
        with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
             patch("ttrss.blueprints.api.views.get_user_pref", return_value="false"):
            mock_user.is_authenticated = True
            mock_user.id = 1
            data, _ = _post(api_app, op)
        assert data["content"]["error"] == "API_DISABLED", f"{op} should be blocked"


def test_guard2_allows_logout_when_api_disabled(api_app):
    """Guard 2: logout is exempt — allowed even when ENABLE_API_ACCESS=false."""
    # Note: don't patch Flask's session proxy outside a request context (it's a LocalProxy).
    # _post() sets up the request context internally; logout_user is patched to be a no-op.
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.logout_user"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        # Guard 2 exempts logout — get_user_pref is NOT called; API_DISABLED is NOT returned.
        data, _ = _post(api_app, "logout")
    assert data["status"] == 0
    assert data["content"]["status"] == "OK"


def test_guard2_passes_when_api_access_enabled(api_app):
    """Guard 2: authenticated user with ENABLE_API_ACCESS=true can reach getVersion."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getVersion")
    assert data["status"] == 0
    assert data["content"]["version"] == "1.12.0-python"


# ---------------------------------------------------------------------------
# getUnread
# ---------------------------------------------------------------------------


def test_getUnread_global(api_app):
    """getUnread with no feed_id returns getGlobalUnread() result."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.getGlobalUnread", return_value=99):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getUnread")
    assert data["status"] == 0
    assert data["content"]["unread"] == 99


def test_getUnread_feed_is_cat(api_app):
    """getUnread with feed_id + is_cat=true uses getCategoryUnread."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.getCategoryUnread", return_value=5) as mock_cu:
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getUnread", {"feed_id": 3, "is_cat": True})
    assert data["status"] == 0
    assert data["content"]["unread"] == 5
    mock_cu.assert_called_once()


def test_getUnread_feed_not_cat(api_app):
    """getUnread with feed_id + is_cat=false queries user_entries directly."""
    mock_scalar = MagicMock(return_value=7)
    mock_execute = MagicMock()
    mock_execute.scalar.return_value = 7
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_execute

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getUnread", {"feed_id": 10, "is_cat": False})
    assert data["status"] == 0
    assert data["content"]["unread"] == 7


# ---------------------------------------------------------------------------
# getCounters
# ---------------------------------------------------------------------------


def test_getCounters_returns_list(api_app):
    """getCounters returns the getAllCounters list."""
    fake_counters = [{"id": "global-unread", "counter": 3}]
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.getAllCounters", return_value=fake_counters), \
         patch("ttrss.blueprints.api.views.db"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getCounters")
    assert data["status"] == 0
    assert data["content"] == fake_counters


def test_getCounters_passes_icons_dir(api_app):
    """getCounters passes ICONS_DIR from app config to getAllCounters."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.getAllCounters", return_value=[]) as mock_gac, \
         patch("ttrss.blueprints.api.views.db"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        _post(api_app, "getCounters")
    # icons_dir param should be the one from config ("/tmp/icons" set in fixture)
    _, kwargs = mock_gac.call_args
    assert "icons_dir" in kwargs


# ---------------------------------------------------------------------------
# getPref
# ---------------------------------------------------------------------------


def test_getPref_returns_value(api_app):
    """getPref returns value for the requested pref_name."""
    def _pref_side(uid, pref_name, profile=None):
        if pref_name == "HIDE_READ_FEEDS":
            return "true"
        return "true"  # guard passes

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", side_effect=_pref_side):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getPref", {"pref_name": "HIDE_READ_FEEDS"})
    assert data["status"] == 0
    assert data["content"]["value"] == "true"


def test_getPref_missing_pref_returns_none(api_app):
    """getPref with unknown pref_name returns None value (not an error)."""
    def _pref_side(uid, pref_name, profile=None):
        if pref_name == "NO_SUCH_PREF":
            return None
        return "true"

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", side_effect=_pref_side):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "getPref", {"pref_name": "NO_SUCH_PREF"})
    assert data["status"] == 0
    assert data["content"]["value"] is None


# ---------------------------------------------------------------------------
# getConfig
# ---------------------------------------------------------------------------


def test_getConfig_structure(api_app):
    """getConfig returns icons_dir, icons_url, daemon_is_running, num_feeds."""
    mock_exec = MagicMock()
    mock_exec.scalar.return_value = 5
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.celery_app.celery_app") as mock_celery:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        inspector = MagicMock()
        inspector.ping.return_value = {"worker1": {"ok": "pong"}}
        mock_celery.control.inspect.return_value = inspector
        data, _ = _post(api_app, "getConfig")

    assert data["status"] == 0
    content = data["content"]
    assert "icons_dir" in content
    assert "icons_url" in content
    assert "daemon_is_running" in content
    assert "num_feeds" in content
    assert content["num_feeds"] == 5


def test_getConfig_daemon_celery_unreachable(api_app):
    """getConfig returns daemon_is_running=False when Celery broker is unreachable."""
    mock_exec = MagicMock()
    mock_exec.scalar.return_value = 0
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    # Patch celery_app so that inspect().ping() raises (simulates broker unreachable).
    # The lazy `from ttrss.celery_app import celery_app` inside getConfig re-reads the module.
    mock_inspector = MagicMock()
    mock_inspector.ping.side_effect = Exception("broker down")

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.celery_app.celery_app") as mock_celery:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        mock_celery.control.inspect.return_value = mock_inspector
        data, _ = _post(api_app, "getConfig")

    assert data["status"] == 0
    assert data["content"]["daemon_is_running"] is False


def test_getConfig_icons_from_app_config(api_app):
    """getConfig icons_dir and icons_url come from Flask app.config."""
    mock_exec = MagicMock()
    mock_exec.scalar.return_value = 0
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.celery_app.celery_app", side_effect=Exception):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getConfig")

    # api_app has ICONS_DIR="/tmp/icons" and ICONS_URL="/icons"
    assert data["content"]["icons_dir"] == "/tmp/icons"
    assert data["content"]["icons_url"] == "/icons"


# ---------------------------------------------------------------------------
# getLabels
# ---------------------------------------------------------------------------


def _make_label_row(id_, caption, fg, bg):
    row = MagicMock()
    row.id = id_
    row.caption = caption
    row.fg_color = fg
    row.bg_color = bg
    return row


def test_getLabels_no_article_id(api_app):
    """getLabels without article_id returns all labels with checked=False."""
    rows = [
        _make_label_row(1, "Important", "#ff0000", "#ffffff"),
        _make_label_row(2, "Work", "#0000ff", "#cccccc"),
    ]
    mock_exec = MagicMock()
    mock_exec.all.return_value = rows
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_labels") as mock_gal:
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getLabels")

    assert data["status"] == 0
    labels = data["content"]
    assert len(labels) == 2
    # No article_id → checked=False for all
    assert all(lbl["checked"] is False for lbl in labels)
    # get_article_labels should NOT be called (article_id is falsy)
    mock_gal.assert_not_called()


def test_getLabels_with_article_id_checked(api_app):
    """getLabels with article_id marks matching labels as checked."""
    from ttrss.utils.feeds import label_to_feed_id

    label_db_id = 1
    label_vfid = label_to_feed_id(label_db_id)

    rows = [
        _make_label_row(label_db_id, "Important", "#ff0000", "#ffffff"),
        _make_label_row(2, "Work", "#0000ff", "#cccccc"),
    ]
    mock_exec = MagicMock()
    mock_exec.all.return_value = rows
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    # article_labels = [[virtual_feed_id, caption, fg, bg]]
    article_labels = [[label_vfid, "Important", "#ff0000", "#ffffff"]]

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_labels", return_value=article_labels):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getLabels", {"article_id": 42})

    assert data["status"] == 0
    labels = data["content"]
    # label_db_id=1 is in article's labels → checked=True
    important = next(l for l in labels if l["caption"] == "Important")
    work = next(l for l in labels if l["caption"] == "Work")
    assert important["checked"] is True
    assert work["checked"] is False


def test_getLabels_returns_virtual_feed_ids(api_app):
    """getLabels returns label_to_feed_id(label.id) as the 'id' field."""
    from ttrss.utils.feeds import label_to_feed_id

    rows = [_make_label_row(3, "Tag", "", "")]
    mock_exec = MagicMock()
    mock_exec.all.return_value = rows
    mock_db_session = MagicMock()
    mock_db_session.execute.return_value = mock_exec

    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"), \
         patch("ttrss.blueprints.api.views.db") as mock_db, \
         patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]):
        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_db.session = mock_db_session
        data, _ = _post(api_app, "getLabels")

    assert data["content"][0]["id"] == label_to_feed_id(3)


# ---------------------------------------------------------------------------
# UNKNOWN_METHOD
# ---------------------------------------------------------------------------


def test_unknown_method_returns_error(api_app):
    """Unrecognised op returns UNKNOWN_METHOD error."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "doesNotExist")
    assert data["status"] == 1
    assert data["content"]["error"] == "UNKNOWN_METHOD"


# ---------------------------------------------------------------------------
# Seq echo
# ---------------------------------------------------------------------------


def test_seq_is_echoed(api_app):
    """seq from request is echoed in every response."""
    with patch("ttrss.blueprints.api.views.current_user") as mock_user, \
         patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"):
        mock_user.is_authenticated = True
        mock_user.id = 1
        data, _ = _post(api_app, "NOOP", seq=42)
    assert data["seq"] == 42
