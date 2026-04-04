"""
Batch 4 unit tests: getHeadlines, subscribeToFeed, unsubscribeFeed, shareToPublished.

Coverage target: ttrss.blueprints.api.views — cumulative ≥80% with batch1-4.
All external deps patched; no DB connection or Redis required.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ---------------------------------------------------------------------------
# Minimal Flask app fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    flask_app = Flask(__name__)
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test",
        WTF_CSRF_ENABLED=False,
        ICONS_DIR="feed-icons",
        ICONS_URL="feed-icons",
    )
    return flask_app


def _make_headline_row(**kwargs):
    """Build a mock row as returned by queryFeedHeadlines."""
    row = MagicMock()
    row.id = kwargs.get("id", 101)
    row.guid = kwargs.get("guid", "abc123")
    row.title = kwargs.get("title", "Test Headline")
    row.link = kwargs.get("link", "https://example.com/article")
    row.updated = kwargs.get("updated", datetime(2024, 6, 1, 12, 30, 45, tzinfo=timezone.utc))
    row.content = kwargs.get("content", "<p>Body text</p>")
    row.author = kwargs.get("author", "Author")
    row.feed_id = kwargs.get("feed_id", 5)
    row.unread = kwargs.get("unread", True)
    row.marked = kwargs.get("marked", False)
    row.published = kwargs.get("published", False)
    row.score = kwargs.get("score", 0)
    row.note = kwargs.get("note", "")
    row.lang = kwargs.get("lang", "en")
    row.num_comments = kwargs.get("num_comments", 0)
    row.comments = kwargs.get("comments", "")
    row.tag_cache = kwargs.get("tag_cache", "python,flask")
    row.label_cache = kwargs.get("label_cache", "")
    row.int_id = kwargs.get("int_id", 201)
    row.uuid = kwargs.get("uuid", "uuid-test")
    row.last_read = kwargs.get("last_read", None)
    row.always_display_enclosures = kwargs.get("always_display_enclosures", False)
    row.feed_title = kwargs.get("feed_title", "Test Feed")
    return row


def _dispatch_b4(app, payload, mock_db_session=None, user_id=1):
    """Run dispatch() with Batch 4 deps patched."""
    mock_user = MagicMock()
    mock_user.is_authenticated = True
    mock_user.id = user_id

    if mock_db_session is None:
        mock_db_session = MagicMock()

    with app.test_request_context(
        "/api/",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    ):
        with (
            patch("ttrss.blueprints.api.views.current_user", mock_user),
            patch("ttrss.blueprints.api.views.db") as mock_db,
            patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
            patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]),
            patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]),
        ):
            mock_db.session = mock_db_session
            mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

            from ttrss.blueprints.api.views import dispatch

            resp = dispatch()
            return json.loads(resp.get_data(as_text=True)), mock_db_session


# ===========================================================================
# getHeadlines tests
# ===========================================================================


class TestGetHeadlines:
    def test_returns_headline_list(self, app):
        row = _make_headline_row()
        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_api.return_value = []

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getHeadlines", "seq": 1, "feed_id": 5}),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", MagicMock(is_authenticated=True, id=1)),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.queryFeedHeadlines", return_value=[row]),
                patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]),
                patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]),
                patch("ttrss.blueprints.api.views.get_plugin_manager", return_value=mock_pm),
            ):
                mock_db.session = MagicMock()
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        assert len(data["content"]) == 1
        h = data["content"][0]
        assert h["id"] == 101
        assert h["title"] == "Test Headline"
        # guid removed from API response (not in PHP getHeadlines output)
        assert "guid" not in h

    def test_is_updated_semantics(self, app):
        """is_updated = last_read IS NULL and NOT unread (PHP: $line['last_read']=="" && !$line['unread'])."""
        # Article with last_read=None and unread=False → is_updated=True
        row_updated = _make_headline_row(id=10)
        row_updated.last_read = None
        row_updated.unread = False
        # Article with last_read=None and unread=True → is_updated=False
        row_unread = _make_headline_row(id=11)
        row_unread.last_read = None
        row_unread.unread = True
        # Article with last_read set → is_updated=False
        row_read = _make_headline_row(id=12)
        row_read.last_read = datetime(2024, 6, 1, tzinfo=timezone.utc)
        row_read.unread = False
        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_api.return_value = []

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getHeadlines", "seq": 2, "feed_id": 5}),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", MagicMock(is_authenticated=True, id=1)),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.queryFeedHeadlines", return_value=[row_updated, row_unread, row_read]),
                patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]),
                patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]),
                patch("ttrss.blueprints.api.views.get_plugin_manager", return_value=mock_pm),
            ):
                mock_db.session = MagicMock()
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        items = data["content"]
        assert items[0]["is_updated"] is True   # last_read=None, unread=False
        assert items[1]["is_updated"] is False  # last_read=None, unread=True
        assert items[2]["is_updated"] is False  # last_read set

    def test_show_excerpt_strips_html(self, app):
        row = _make_headline_row(content="<p>Hello world this is a test article body text</p>")
        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_api.return_value = []

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getHeadlines", "seq": 3, "feed_id": 5, "show_excerpt": True}),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", MagicMock(is_authenticated=True, id=1)),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.queryFeedHeadlines", return_value=[row]),
                patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]),
                patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]),
                patch("ttrss.blueprints.api.views.get_plugin_manager", return_value=mock_pm),
            ):
                mock_db.session = MagicMock()
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        excerpt = data["content"][0]["excerpt"]
        assert "<p>" not in excerpt
        assert "Hello world" in excerpt

    def test_hook_render_article_api_fires_per_row(self, app):
        rows = [_make_headline_row(id=i) for i in [10, 11, 12]]
        hook_results = [{"article": {"id": r.id, "_hook": True}} for r in rows]
        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_api.side_effect = [
            [hook_results[0]],
            [hook_results[1]],
            [hook_results[2]],
        ]

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getHeadlines", "seq": 4, "feed_id": -4}),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", MagicMock(is_authenticated=True, id=1)),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.queryFeedHeadlines", return_value=rows),
                patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]),
                patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]),
                patch("ttrss.blueprints.api.views.get_plugin_manager", return_value=mock_pm),
            ):
                mock_db.session = MagicMock()
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        # hook fired 3 times (once per row) — all transformed articles have _hook=True
        assert mock_pm.hook.hook_render_article_api.call_count == 3
        for h in data["content"]:
            assert h.get("_hook") is True

    def test_empty_feed_returns_empty_list(self, app):
        mock_pm = MagicMock()
        mock_pm.hook.hook_render_article_api.return_value = []

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getHeadlines", "seq": 5, "feed_id": 99}),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", MagicMock(is_authenticated=True, id=1)),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.queryFeedHeadlines", return_value=[]),
                patch("ttrss.blueprints.api.views.get_article_labels", return_value=[]),
                patch("ttrss.blueprints.api.views.get_article_enclosures", return_value=[]),
                patch("ttrss.blueprints.api.views.get_plugin_manager", return_value=mock_pm),
            ):
                mock_db.session = MagicMock()
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        assert data["content"] == []


# ===========================================================================
# subscribeToFeed tests
# ===========================================================================


class TestSubscribeToFeed:
    def _run(self, app, payload, subscribe_result):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(payload),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch(
                    "ttrss.blueprints.api.views.subscribe_to_feed",
                    return_value=subscribe_result,
                ),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                return json.loads(resp.get_data(as_text=True))

    def test_new_subscription_returns_code_1(self, app):
        data = self._run(
            app,
            {"op": "subscribeToFeed", "seq": 1, "feed_url": "https://example.com/feed"},
            {"code": 1},
        )
        assert data["status"] == 0
        assert data["content"]["status"]["code"] == 1

    def test_already_subscribed_returns_code_0(self, app):
        data = self._run(
            app,
            {"op": "subscribeToFeed", "seq": 2, "feed_url": "https://example.com/feed"},
            {"code": 0},
        )
        assert data["content"]["status"]["code"] == 0

    def test_invalid_url_returns_code_2(self, app):
        data = self._run(
            app,
            {"op": "subscribeToFeed", "seq": 3, "feed_url": "not-a-url"},
            {"code": 2},
        )
        assert data["content"]["status"]["code"] == 2


# ===========================================================================
# unsubscribeFeed tests
# ===========================================================================


class TestUnsubscribeFeed:
    def test_owner_can_unsubscribe(self, app):
        mock_db_session = MagicMock()
        # Ownership check returns owner_uid == current_user.id == 1
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = 1

        data, _ = _dispatch_b4(
            app,
            {"op": "unsubscribeFeed", "seq": 1, "feed_id": 42},
            mock_db_session=mock_db_session,
        )
        assert data["status"] == 0
        assert data["content"]["status"] == "OK"

    def test_non_owner_gets_error(self, app):
        mock_db_session = MagicMock()
        # Ownership check returns owner_uid=99 != current_user.id=1
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = 99

        data, _ = _dispatch_b4(
            app,
            {"op": "unsubscribeFeed", "seq": 2, "feed_id": 42},
            mock_db_session=mock_db_session,
        )
        assert data["status"] == 1
        assert data["content"]["error"] == "FEED_NOT_FOUND"

    def test_nonexistent_feed_gets_error(self, app):
        mock_db_session = MagicMock()
        # Feed not found → None (can't own a non-existent feed)
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        data, _ = _dispatch_b4(
            app,
            {"op": "unsubscribeFeed", "seq": 3, "feed_id": 999},
            mock_db_session=mock_db_session,
        )
        assert data["status"] == 1
        assert data["content"]["error"] == "FEED_NOT_FOUND"


# ===========================================================================
# shareToPublished tests
# ===========================================================================


class TestShareToPublished:
    def _run(self, app, payload, existing_entry_id=None):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        # First execute → entry lookup (scalar_one_or_none returns existing_entry_id or None)
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_entry_id

        # When adding a new TtRssEntry, flush gives it id=99
        def fake_add(obj):
            if hasattr(obj, "guid"):
                obj.id = 99

        mock_db_session.flush.side_effect = lambda: None
        mock_db_session.add.side_effect = fake_add

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(payload),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        return data, mock_db_session

    def test_new_entry_created_and_user_entry_added(self, app):
        data, mock_session = self._run(
            app,
            {
                "op": "shareToPublished",
                "seq": 1,
                "title": "My Article",
                "url": "https://example.com/shared",
                "content": "Article body",
            },
            existing_entry_id=None,  # new entry
        )
        assert data["status"] == 0
        assert data["content"]["status"] == "OK"
        # session.add called twice: once for TtRssEntry, once for TtRssUserEntry
        assert mock_session.add.call_count == 2

    def test_existing_entry_reused(self, app):
        """Entry exists → only user_entry added if not already present."""
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        # Two execute() calls: first returns 77 (entry exists), second returns None (no user_entry)
        exec_results = [MagicMock(), MagicMock()]
        exec_results[0].scalar_one_or_none.return_value = 77
        exec_results[1].scalar_one_or_none.return_value = None
        exec_iter = iter(exec_results)
        mock_db_session.execute.side_effect = lambda *a, **kw: next(exec_iter)
        mock_db_session.flush.side_effect = lambda: None

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({
                "op": "shareToPublished",
                "seq": 2,
                "title": "Existing",
                "url": "https://example.com/shared",
                "content": "",
            }),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        # Only TtRssUserEntry added (not TtRssEntry)
        assert mock_db_session.add.call_count == 1

    def test_user_entry_has_feed_id_none(self, app):
        """feed_id must be None (NOT -2) — R16 invariant."""
        added_objects = []

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        # Two execute() calls: entry found (77), user_entry not found (None) → new user_entry
        exec_results = [MagicMock(), MagicMock()]
        exec_results[0].scalar_one_or_none.return_value = 77
        exec_results[1].scalar_one_or_none.return_value = None
        exec_iter = iter(exec_results)
        mock_db_session.execute.side_effect = lambda *a, **kw: next(exec_iter)

        def capture_add(obj):
            added_objects.append(obj)

        mock_db_session.add.side_effect = capture_add

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(
                {"op": "shareToPublished", "seq": 3, "title": "T", "url": "U", "content": "C"}
            ),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                dispatch()

        # The TtRssUserEntry should have feed_id=None
        from ttrss.models.user_entry import TtRssUserEntry

        user_entries = [o for o in added_objects if isinstance(o, TtRssUserEntry)]
        assert len(user_entries) == 1
        assert user_entries[0].feed_id is None
        assert user_entries[0].published is True
