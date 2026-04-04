"""
Batch 5 unit tests: getFeedTree.

Coverage target: ttrss.blueprints.api.views — cumulative ≥80% with batch1-5.
All external deps patched; no DB connection or Redis required.
"""
from __future__ import annotations

import json
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


def _make_cat_row(id=1, title="Tech", order_id=0, parent_cat=None):
    row = MagicMock()
    row.id = id
    row.title = title
    row.order_id = order_id
    row.parent_cat = parent_cat
    return row


def _make_feed_row(id=10, title="My Feed", order_id=0, cat_id=1):
    row = MagicMock()
    row.id = id
    row.title = title
    row.order_id = order_id
    row.cat_id = cat_id
    return row


def _make_label_row(id=1, caption="Technology"):
    row = MagicMock()
    row.id = id
    row.caption = caption
    return row


def _dispatch(app, payload):
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
        ):
            mock_db.session = mock_db_session
            mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

            yield mock_db_session


class TestGetFeedTreeEnvelope:
    def test_response_envelope(self, app):
        """Response must have identifier/label/items envelope (pref/feeds.php:291-292)."""
        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getFeedTree", "seq": 1}),
            content_type="application/json",
        ):
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_db_session = MagicMock()
            # All DB calls return empty
            mock_exec = MagicMock()
            mock_exec.all.return_value = []
            mock_db_session.execute.return_value = mock_exec

            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="Special"),
                patch("ttrss.blueprints.api.views.getFeedTitle", return_value="Virtual"),
                patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0),
                patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False),
                patch("ttrss.blueprints.api.views.label_to_feed_id", return_value=-1001),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        cats = data["content"]["categories"]
        assert "identifier" in cats
        assert "label" in cats
        assert "items" in cats
        assert cats["identifier"] == "id"
        assert cats["label"] == "name"

    def test_special_cat_has_cid_prefix(self, app):
        """CAT:-1 (Special) must appear as id='CAT:-1' with bare_id=-1."""
        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getFeedTree", "seq": 2}),
            content_type="application/json",
        ):
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_db_session = MagicMock()
            mock_exec = MagicMock()
            mock_exec.all.return_value = []
            mock_db_session.execute.return_value = mock_exec

            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="Special"),
                patch("ttrss.blueprints.api.views.getFeedTitle", return_value="Virtual"),
                patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0),
                patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False),
                patch("ttrss.blueprints.api.views.label_to_feed_id", return_value=-1001),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        items = data["content"]["categories"]["items"]
        special = items[0]  # Special is always first
        assert special["id"] == "CAT:-1"
        assert special["bare_id"] == -1
        assert special["auxcounter"] == 0
        assert special["type"] == "category"

    def test_virtual_feeds_in_correct_order(self, app):
        """Virtual feeds in Special cat must be in order: [-4,-3,-1,-2,0,-6]."""
        def mock_get_feed_title(session, feed_id):
            return f"VF{feed_id}"

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getFeedTree", "seq": 3}),
            content_type="application/json",
        ):
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_db_session = MagicMock()
            mock_exec = MagicMock()
            mock_exec.all.return_value = []
            mock_db_session.execute.return_value = mock_exec

            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="Cat"),
                patch("ttrss.blueprints.api.views.getFeedTitle", side_effect=mock_get_feed_title),
                patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0),
                patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False),
                patch("ttrss.blueprints.api.views.label_to_feed_id", return_value=-1001),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        items = data["content"]["categories"]["items"]
        special_items = items[0]["items"]
        assert len(special_items) == 6
        bare_ids = [item["bare_id"] for item in special_items]
        assert bare_ids == [-4, -3, -1, -2, 0, -6]

    def test_feed_ids_have_feed_prefix(self, app):
        """All feed nodes must have id='FEED:{id}' and bare_id=int."""
        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getFeedTree", "seq": 4}),
            content_type="application/json",
        ):
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_db_session = MagicMock()
            mock_exec = MagicMock()
            mock_exec.all.return_value = []
            mock_db_session.execute.return_value = mock_exec

            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="Cat"),
                patch("ttrss.blueprints.api.views.getFeedTitle", return_value="Feed"),
                patch("ttrss.blueprints.api.views._count_feed_articles", return_value=3),
                patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False),
                patch("ttrss.blueprints.api.views.label_to_feed_id", return_value=-1001),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        items = data["content"]["categories"]["items"]
        special_items = items[0]["items"]
        for feed_node in special_items:
            assert feed_node["id"].startswith("FEED:")
            assert isinstance(feed_node["bare_id"], int)
            assert feed_node["auxcounter"] == 0

    def test_real_category_with_feeds(self, app):
        """Real categories with feeds appear with correct structure."""
        cat = _make_cat_row(id=5, title="Science")
        feed = _make_feed_row(id=42, title="Ars Technica", cat_id=5)

        call_count = [0]

        def smart_execute(*args, **kwargs):
            """Returns categories on first call, feeds on second, empty on rest."""
            result = MagicMock()
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                # labels query
                result.all.return_value = []
            elif c == 1:
                # root categories query
                result.all.return_value = [cat]
            elif c == 2:
                # child cats of category 5
                result.all.return_value = []
            elif c == 3:
                # feeds in category 5
                result.all.return_value = [feed]
            elif c == 4:
                # uncategorized feeds
                result.all.return_value = []
            else:
                result.all.return_value = []
            return result

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getFeedTree", "seq": 5}),
            content_type="application/json",
        ):
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_db_session = MagicMock()
            mock_db_session.execute.side_effect = smart_execute

            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="Cat"),
                patch("ttrss.blueprints.api.views.getFeedTitle", return_value="VF"),
                patch("ttrss.blueprints.api.views._count_feed_articles", return_value=5),
                patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False),
                patch("ttrss.blueprints.api.views.label_to_feed_id", return_value=-1001),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        items = data["content"]["categories"]["items"]
        # Should have: Special(-1), Science category
        science_nodes = [n for n in items if n.get("id") == "CAT:5"]
        assert len(science_nodes) == 1
        science = science_nodes[0]
        assert science["bare_id"] == 5
        assert science["type"] == "category"
        # Should contain the feed
        assert len(science["items"]) == 1
        assert science["items"][0]["id"] == "FEED:42"
        assert science["items"][0]["bare_id"] == 42

    def test_cycle_detection_prevents_infinite_loop(self, app):
        """BFS cycle detection (visited set) must not infinite-loop on circular parent_cat."""
        call_count = [0]

        def smart_execute(*args, **kwargs):
            result = MagicMock()
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                # labels
                result.all.return_value = []
            elif c == 1:
                # root categories — one cat with id=1
                cat = _make_cat_row(id=1, title="Root")
                result.all.return_value = [cat]
            elif c == 2:
                # child cats of cat 1 → returns cat 2
                cat2 = _make_cat_row(id=2, title="Child")
                result.all.return_value = [cat2]
            elif c == 3:
                # feeds in cat 1 → empty
                result.all.return_value = []
            elif c == 4:
                # child cats of cat 2 → returns cat 1 AGAIN (cycle)
                cat1_again = _make_cat_row(id=1, title="Root Again")
                result.all.return_value = [cat1_again]
            elif c == 5:
                # feeds in cat 2 → empty
                result.all.return_value = []
            else:
                result.all.return_value = []
            return result

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "getFeedTree", "seq": 6, "include_empty": True}),
            content_type="application/json",
        ):
            mock_user = MagicMock()
            mock_user.is_authenticated = True
            mock_user.id = 1
            mock_db_session = MagicMock()
            mock_db_session.execute.side_effect = smart_execute

            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.getCategoryTitle", return_value="Cat"),
                patch("ttrss.blueprints.api.views.getFeedTitle", return_value="VF"),
                patch("ttrss.blueprints.api.views._count_feed_articles", return_value=0),
                patch("ttrss.blueprints.api.views.feed_has_icon", return_value=False),
                patch("ttrss.blueprints.api.views.label_to_feed_id", return_value=-1001),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                # Must not raise RecursionError or timeout
                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        # Should succeed without infinite loop
        assert data["status"] == 0
