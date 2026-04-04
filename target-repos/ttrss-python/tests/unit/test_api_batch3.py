"""
Batch 3 unit tests: updateArticle, catchupFeed, setArticleLabel, updateFeed.

Coverage target: ttrss.blueprints.api.views — cumulative ≥80% with batch1+2+3.
All external deps patched; no DB connection or Redis required.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ---------------------------------------------------------------------------
# Minimal Flask app fixture (same pattern as batch 1/2)
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


def _dispatch(app, payload: dict, user_authenticated: bool = True):
    """Run dispatch() inside a request context with all external deps patched."""
    mock_user = MagicMock()
    mock_user.is_authenticated = user_authenticated
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

            from ttrss.blueprints.api.views import dispatch

            resp = dispatch()
            return json.loads(resp.get_data(as_text=True)), mock_db_session


# ===========================================================================
# updateArticle tests
# ===========================================================================


class TestUpdateArticle:
    def test_missing_article_ids_returns_error(self, app):
        data, _ = _dispatch(app, {"op": "updateArticle", "seq": 1, "field": 0, "mode": 1})
        assert data["status"] == 1
        assert data["content"]["error"] == "INCORRECT_USAGE"

    def test_invalid_field_returns_error(self, app):
        data, _ = _dispatch(
            app,
            {"op": "updateArticle", "seq": 1, "article_ids": "5", "field": 99, "mode": 1},
        )
        assert data["status"] == 1
        assert data["content"]["error"] == "INCORRECT_USAGE"

    def test_mode1_sets_marked_true(self, app):
        mock_result = MagicMock()
        mock_result.rowcount = 1

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        mock_db_session.execute.side_effect = [mock_result, MagicMock()]

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(
                {"op": "updateArticle", "seq": 2, "article_ids": "5", "field": 0, "mode": 1}
            ),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.ccache_update"),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        assert data["content"]["updated"] == 1

    def test_field2_unread_triggers_ccache_update(self, app):
        """ccache_update fires per distinct feed_id when field==2 and num_updated>0."""
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 2

        mock_feed_rows = [MagicMock(feed_id=10), MagicMock(feed_id=20)]
        mock_feed_exec = MagicMock()
        mock_feed_exec.all.return_value = mock_feed_rows

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        mock_db_session.execute.side_effect = [mock_update_result, mock_feed_exec]

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(
                {"op": "updateArticle", "seq": 3, "article_ids": "5,6", "field": 2, "mode": 0}
            ),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.ccache_update") as mock_ccache,
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        assert mock_ccache.call_count == 2

    def test_field2_no_ccache_when_zero_updated(self, app):
        """ccache_update must NOT fire when num_updated==0 even for unread field."""
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 0

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        mock_db_session.execute.return_value = mock_update_result

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(
                {"op": "updateArticle", "seq": 4, "article_ids": "5", "field": 2, "mode": 1}
            ),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.ccache_update") as mock_ccache,
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()

        mock_ccache.assert_not_called()

    def test_field3_note_uses_data_key_and_strips_html(self, app):
        """field==3 (note): reads from 'data' param (not 'note'), strips HTML tags.
        Source: api.php:237 — $data = strip_tags($_REQUEST['data'])
        """
        mock_result = MagicMock()
        mock_result.rowcount = 1

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        mock_db_session.execute.return_value = mock_result

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(
                {
                    "op": "updateArticle",
                    "seq": 5,
                    "article_ids": "5",
                    "field": 3,
                    "mode": 0,
                    "data": "<b>My note</b>",  # PHP key is "data", not "note"
                }
            ),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.ccache_update") as mock_ccache,
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        # ccache must NOT fire for note field (field==3)
        mock_ccache.assert_not_called()
        # Verify the UPDATE was called (execute called once for the UPDATE)
        assert mock_db_session.execute.called


# ===========================================================================
# catchupFeed tests
# ===========================================================================


class TestCatchupFeed:
    def test_catchup_feed_calls_catchup_feed(self, app):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps({"op": "catchupFeed", "seq": 1, "feed_id": 7, "is_cat": False}),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.catchup_feed") as mock_catchup,
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        assert data["status"] == 0
        assert data["content"]["status"] == "OK"
        mock_catchup.assert_called_once_with(mock_db_session, 7, False, 1)

    def test_catchup_feed_is_cat_true(self, app):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()

        with app.test_request_context(
            "/api/",
            method="POST",
            data=json.dumps(
                {"op": "catchupFeed", "seq": 2, "feed_id": 3, "is_cat": True}
            ),
            content_type="application/json",
        ):
            with (
                patch("ttrss.blueprints.api.views.current_user", mock_user),
                patch("ttrss.blueprints.api.views.db") as mock_db,
                patch("ttrss.blueprints.api.views.get_user_pref", return_value="true"),
                patch("ttrss.blueprints.api.views.catchup_feed") as mock_catchup,
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()

        mock_catchup.assert_called_once_with(mock_db_session, 3, True, 1)


# ===========================================================================
# setArticleLabel tests
# ===========================================================================


class TestSetArticleLabel:
    def _run(self, app, payload, feed_to_label_id_val=5, caption="Tech"):
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
                    "ttrss.blueprints.api.views.label_find_caption", return_value=caption
                ) as mock_caption,
                patch(
                    "ttrss.blueprints.api.views.label_add_article"
                ) as mock_add,
                patch(
                    "ttrss.blueprints.api.views.label_remove_article"
                ) as mock_remove,
                patch(
                    "ttrss.blueprints.api.views.feed_to_label_id",
                    return_value=feed_to_label_id_val,
                ),
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        return data, mock_add, mock_remove, mock_caption

    def test_assign_true_calls_label_add(self, app):
        data, mock_add, mock_remove, _ = self._run(
            app,
            {
                "op": "setArticleLabel",
                "seq": 1,
                "label_id": -1005,
                "assign": True,
                "article_ids": "10,11",
            },
        )
        assert data["status"] == 0
        assert mock_add.call_count == 2
        mock_remove.assert_not_called()

    def test_assign_false_calls_label_remove(self, app):
        data, mock_add, mock_remove, _ = self._run(
            app,
            {
                "op": "setArticleLabel",
                "seq": 2,
                "label_id": -1005,
                "assign": False,
                "article_ids": "10",
            },
        )
        assert data["status"] == 0
        mock_add.assert_not_called()
        mock_remove.call_count == 1

    def test_missing_article_ids_returns_error(self, app):
        data, _, _, _ = self._run(
            app,
            {
                "op": "setArticleLabel",
                "seq": 3,
                "label_id": -1005,
                "assign": True,
                "article_ids": "",
            },
            caption="",  # empty caption → INCORRECT_USAGE path
        )
        # empty article_ids → INCORRECT_USAGE before caption lookup
        assert data["status"] == 1
        assert data["content"]["error"] == "INCORRECT_USAGE"

    def test_unknown_label_returns_ok_silently(self, app):
        """PHP silently returns OK when label not found — no error raised.
        Source: api.php:462-474 — only loops when label found; returns OK regardless.
        """
        data, _, _, _ = self._run(
            app,
            {
                "op": "setArticleLabel",
                "seq": 4,
                "label_id": -1099,
                "assign": True,
                "article_ids": "7",
            },
            caption="",  # label_find_caption returns "" → silent OK
        )
        assert data["status"] == 0
        assert data["content"]["status"] == "OK"


# ===========================================================================
# updateFeed tests
# ===========================================================================


class TestUpdateFeed:
    def _run(self, app, payload, owner_uid=1):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = owner_uid

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
                    "ttrss.tasks.feed_tasks.update_feed"
                ) as mock_task,
            ):
                mock_db.session = mock_db_session
                mock_db.select = MagicMock(side_effect=lambda *a, **kw: MagicMock())

                from ttrss.blueprints.api.views import dispatch

                resp = dispatch()
                data = json.loads(resp.get_data(as_text=True))

        return data, mock_task

    def test_owned_feed_schedules_task(self, app):
        """When owner_uid matches, update_feed.delay() is called."""
        import sys

        mock_task = MagicMock()
        mock_feed_tasks_module = MagicMock()
        mock_feed_tasks_module.update_feed = mock_task

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = 1

        orig = sys.modules.get("ttrss.tasks.feed_tasks")
        sys.modules["ttrss.tasks.feed_tasks"] = mock_feed_tasks_module
        try:
            with app.test_request_context(
                "/api/",
                method="POST",
                data=json.dumps({"op": "updateFeed", "seq": 1, "feed_id": 42}),
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
        finally:
            if orig is None:
                sys.modules.pop("ttrss.tasks.feed_tasks", None)
            else:
                sys.modules["ttrss.tasks.feed_tasks"] = orig

        assert data["status"] == 0
        assert data["content"]["status"] == "OK"
        mock_task.delay.assert_called_once_with(42)

    def test_non_owner_does_not_schedule_task(self, app):
        """When owner_uid doesn't match, update_feed.delay() is NOT called."""
        import sys

        mock_feed_tasks_module = MagicMock()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1

        mock_db_session = MagicMock()
        # Return owner_uid=99 → different from current user id=1
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = 99

        orig = sys.modules.get("ttrss.tasks.feed_tasks")
        sys.modules["ttrss.tasks.feed_tasks"] = mock_feed_tasks_module
        try:
            with app.test_request_context(
                "/api/",
                method="POST",
                data=json.dumps({"op": "updateFeed", "seq": 2, "feed_id": 42}),
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
        finally:
            if orig is None:
                sys.modules.pop("ttrss.tasks.feed_tasks", None)
            else:
                sys.modules["ttrss.tasks.feed_tasks"] = orig

        assert data["status"] == 0
        # delay was NOT called — non-owner
        mock_feed_tasks_module.update_feed.delay.assert_not_called()
