"""HTTP-handler tests for ttrss/blueprints/prefs/feeds.py.

Source: ttrss/classes/pref/feeds.php (Pref_Feeds handler, 1925 lines)
New: Python test suite — no PHP equivalent.

Each test drives the Blueprint via app.test_request_context() with the
login_required decorator bypassed through _unwrap(), following the project's
established unit-test pattern (see tests/unit/test_prefs_blueprint.py).

All CRUD collaborators are mocked; no Postgres connection is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unwrap(fn):
    """Return the innermost wrapped function (bypasses login_required etc.)."""
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


def _mock_user(user_id: int = 1, access_level: int = 10) -> MagicMock:
    m = MagicMock()
    m.id = user_id
    m.access_level = access_level
    return m


# ---------------------------------------------------------------------------
# GET /prefs/feeds/<id>
# ---------------------------------------------------------------------------


class TestEditFeedGet:
    """GET /prefs/feeds/<id> — edit dialog data."""

    def test_valid_feed_returns_200(self, app):
        """GET /prefs/feeds/<id> with a valid feed returns 200 with feed data.

        Source: ttrss/classes/pref/feeds.php:535 — SELECT * FROM ttrss_feeds WHERE id AND owner_uid
        Source: ttrss/classes/pref/feeds.php:748 — HOOK_PREFS_EDIT_FEED
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_edit_feed.return_value = []
        mock_pm.hook.hook_prefs_tab_section.return_value = []
        mock_pm.hook.hook_prefs_tab.return_value = []

        mock_user = _mock_user()

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.get_feed_for_edit.return_value = {
                    "id": 1, "title": "Test Feed", "feed_url": "http://example.com/feed"
                }
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.edit_feed)(feed_id=1)

        data = resp.get_json()
        assert resp.status_code == 200
        assert data["id"] == 1
        assert data["title"] == "Test Feed"
        assert "plugin_fields" in data

    def test_feed_not_found_returns_404(self, app):
        """GET /prefs/feeds/<id> returns 404 when feed doesn't belong to user.

        Source: ttrss/classes/pref/feeds.php:535 — SELECT guarded by owner_uid
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_edit_feed.return_value = []
        mock_pm.hook.hook_prefs_tab_section.return_value = []
        mock_pm.hook.hook_prefs_tab.return_value = []

        mock_user = _mock_user()

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.get_feed_for_edit.return_value = None
                from ttrss.blueprints.prefs import feeds
                result = _unwrap(feeds.edit_feed)(feed_id=999)
            resp = app.make_response(result)

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "feed_not_found"

    def test_hook_prefs_edit_feed_fires_before_not_found(self, app):
        """HOOK_PREFS_EDIT_FEED fires unconditionally before any early return.

        Source: ttrss/classes/pref/feeds.php:748 — run_hooks(HOOK_PREFS_EDIT_FEED, $feed_id)
                Comment: 'must fire BEFORE any early return'
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_edit_feed.return_value = []
        mock_pm.hook.hook_prefs_tab_section.return_value = []
        mock_pm.hook.hook_prefs_tab.return_value = []

        mock_user = _mock_user()

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.get_feed_for_edit.return_value = None  # feed not found
                from ttrss.blueprints.prefs import feeds
                _unwrap(feeds.edit_feed)(feed_id=99)

        # Hook must fire even though feed was not found
        mock_pm.hook.hook_prefs_edit_feed.assert_called_once_with(feed_id=99)


# ---------------------------------------------------------------------------
# POST /prefs/feeds/<id>
# ---------------------------------------------------------------------------


class TestSaveFeedPost:
    """POST /prefs/feeds/<id> — save feed settings."""

    def test_valid_save_returns_200(self, app):
        """POST /prefs/feeds/<id> with a valid feed returns 200.

        Source: ttrss/classes/pref/feeds.php:912 — editSave / editsaveops(false)
        """
        mock_pm = MagicMock()
        mock_user = _mock_user()

        with app.test_request_context(method="POST", data={"title": "Updated"}):
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.save_feed_settings.return_value = True
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.save_feed)(feed_id=1)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        assert resp.get_json()["feed_id"] == 1

    def test_save_feed_not_found_returns_404(self, app):
        """POST /prefs/feeds/<id> returns 404 when feed not found for user.

        Source: ttrss/classes/pref/feeds.php:912 — owner_uid guard
        """
        mock_pm = MagicMock()
        mock_user = _mock_user()

        with app.test_request_context(method="POST", data={}):
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.save_feed_settings.return_value = False
                from ttrss.blueprints.prefs import feeds
                result = _unwrap(feeds.save_feed)(feed_id=999)
            resp = app.make_response(result)

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "feed_not_found"

    def test_hook_prefs_save_feed_fires(self, app):
        """HOOK_PREFS_SAVE_FEED fires unconditionally before early return.

        Source: ttrss/classes/pref/feeds.php:981 — run_hooks(HOOK_PREFS_SAVE_FEED, $feed_id)
        """
        mock_pm = MagicMock()
        mock_user = _mock_user()

        with app.test_request_context(method="POST", data={}):
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.save_feed_settings.return_value = True
                from ttrss.blueprints.prefs import feeds
                _unwrap(feeds.save_feed)(feed_id=7)

        mock_pm.hook.hook_prefs_save_feed.assert_called_once_with(feed_id=7)


# ---------------------------------------------------------------------------
# POST /prefs/feeds/batch_edit
# ---------------------------------------------------------------------------


class TestBatchEditFeeds:
    """POST /prefs/feeds/batch_edit — bulk settings update."""

    def test_batch_edit_returns_200(self, app):
        """POST /prefs/feeds/batch_edit calls batch_edit_feeds and returns 200.

        Source: ttrss/classes/pref/feeds.php:908 — batchEditSave / editsaveops(true)
        """
        mock_user = _mock_user()

        with app.test_request_context(
            method="POST",
            data={"feed_ids[]": ["1", "2", "3"], "cat_id": "5"},
        ):
            with patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.batch_edit_feeds.return_value = None
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.batch_edit_feeds)()

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.batch_edit_feeds.assert_called_once()


# ---------------------------------------------------------------------------
# POST /prefs/feeds/order
# ---------------------------------------------------------------------------


class TestSaveFeedOrder:
    """POST /prefs/feeds/order — persist drag-and-drop ordering."""

    def test_save_order_returns_200(self, app):
        """POST /prefs/feeds/order persists feed order and returns 200.

        Source: ttrss/classes/pref/feeds.php:386 — savefeedorder
        """
        mock_user = _mock_user()
        payload = {"items": [{"id": 1, "cat_id": 0}, {"id": 2, "cat_id": 0}]}

        with app.test_request_context(
            method="POST",
            json=payload,
            content_type="application/json",
        ):
            with patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.save_feed_order.return_value = None
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.save_feed_order)()

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.save_feed_order.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /prefs/feeds/<id>
# ---------------------------------------------------------------------------


class TestRemoveFeed:
    """DELETE /prefs/feeds/<id> — unsubscribe from feed."""

    def test_remove_feed_valid_returns_200(self, app):
        """DELETE /prefs/feeds/<id> removes feed and returns 200.

        Source: ttrss/classes/pref/feeds.php:1078 — remove / remove_feed (line 1707)
        """
        mock_user = _mock_user()

        with app.test_request_context(method="DELETE"):
            with patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.remove_feed.return_value = None  # no error
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.remove_feed)(feed_id=1)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_remove_feed_self_delete_returns_400(self, app):
        """DELETE /prefs/feeds/<id> returns 400 when removal is disallowed.

        Source: ttrss/classes/pref/feeds.php:1078 — remove_feed returns error string on failure
                (e.g., attempted removal of feed reserved for the owner's session)
        """
        mock_user = _mock_user()

        with app.test_request_context(method="DELETE"):
            with patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.remove_feed.return_value = "cannot_remove_self"
                from ttrss.blueprints.prefs import feeds
                result = _unwrap(feeds.remove_feed)(feed_id=1)
            resp = app.make_response(result)

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "cannot_remove_self"


# ---------------------------------------------------------------------------
# POST /prefs/feeds/<id>/rescore
# ---------------------------------------------------------------------------


class TestRescoreFeed:
    """POST /prefs/feeds/<id>/rescore — re-apply filter scoring."""

    def test_rescore_feed_returns_200(self, app):
        """POST /prefs/feeds/<id>/rescore rescores articles and returns 200.

        Source: ttrss/classes/pref/feeds.php:1094-1147 — rescore
        """
        mock_user = _mock_user()

        with app.test_request_context(method="POST"):
            with patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.rescore_feed_impl.return_value = None
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.rescore_feed)(feed_id=3)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.rescore_feed_impl.assert_called_once()


# ---------------------------------------------------------------------------
# POST /prefs/feeds/keys/opml/regen
# ---------------------------------------------------------------------------


class TestRegenOpmlKey:
    """POST /prefs/feeds/keys/opml/regen — regenerate OPML publish key."""

    def test_regen_opml_key_returns_200_with_key(self, app):
        """POST /prefs/feeds/keys/opml/regen returns 200 with a new access_key.

        Source: ttrss/classes/pref/feeds.php:Pref_Feeds::regenOPMLKey (lines 1861-1867)
        """
        mock_user = _mock_user()

        with app.test_request_context(method="POST"):
            with patch("ttrss.blueprints.prefs.feeds.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.feeds.feeds_crud") as mock_crud:
                mock_crud.regen_opml_key.return_value = "abc123newkey"
                from ttrss.blueprints.prefs import feeds
                resp = _unwrap(feeds.regen_opml_key)()

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["access_key"] == "abc123newkey"
        mock_crud.regen_opml_key.assert_called_once()
