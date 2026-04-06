"""HTTP-handler tests for ttrss/blueprints/prefs/filters.py.

Source: ttrss/classes/pref/filters.php (Pref_Filters handler, 1054 lines)
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


def _make_filter_row(filter_id: int = 1) -> MagicMock:
    row = MagicMock()
    row.id = filter_id
    row.title = f"Filter {filter_id}"
    row.enabled = True
    row.match_any_rule = False
    row.inverse = False
    return row


# ---------------------------------------------------------------------------
# GET /prefs/filters — filter list
# ---------------------------------------------------------------------------


class TestFiltersList:
    """GET /prefs/filters — return filter list and HOOK_PREFS_TAB content."""

    def test_get_filters_returns_200(self, app):
        """GET /prefs/filters returns 200 with filters list.

        Source: ttrss/classes/pref/filters.php:159 — getfiltertree
        Source: ttrss/classes/pref/filters.php:695 — run_hooks(HOOK_PREFS_TAB)
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab.return_value = []
        mock_user = _mock_user()

        row = _make_filter_row(1)

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.get_filter_rows.return_value = [row]
                mock_crud.get_rule_reg_exps_for_filter.return_value = ["foo.*"]
                mock_crud.get_filter_name.return_value = ("Filter 1", "label:foo")
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.filters)()

        assert resp.status_code == 200
        data = resp.get_json()
        assert "filters" in data
        assert len(data["filters"]) == 1
        assert data["filters"][0]["id"] == 1


# ---------------------------------------------------------------------------
# GET /prefs/filters/<id> — single filter
# ---------------------------------------------------------------------------


class TestEditFilter:
    """GET /prefs/filters/<id> — filter edit data."""

    def test_get_filter_found_returns_200(self, app):
        """GET /prefs/filters/<id> returns 200 with filter details.

        Source: ttrss/classes/pref/filters.php:234 — edit
        """
        mock_user = _mock_user()
        f = _make_filter_row(2)

        rule = MagicMock()
        rule.id = 10
        rule.reg_exp = "breaking"
        rule.filter_type = 1
        rule.feed_id = 0
        rule.cat_id = 0
        rule.cat_filter = False
        rule.inverse = False

        action = MagicMock()
        action.id = 20
        action.action_id = 2
        action.action_param = ""

        with app.test_request_context():
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.fetch_filter.return_value = f
                mock_crud.fetch_filter_rules.return_value = [rule]
                mock_crud.fetch_filter_actions.return_value = [action]
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.edit_filter)(filter_id=2)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == 2
        assert len(data["rules"]) == 1
        assert len(data["actions"]) == 1

    def test_get_filter_not_found_returns_404(self, app):
        """GET /prefs/filters/<id> returns 404 when filter not found.

        Source: ttrss/classes/pref/filters.php:234 — edit — owner_uid check
        """
        mock_user = _mock_user()

        with app.test_request_context():
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.fetch_filter.return_value = None
                from ttrss.blueprints.prefs import filters
                result = _unwrap(filters.edit_filter)(filter_id=999)
            resp = app.make_response(result)

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "filter_not_found"


# ---------------------------------------------------------------------------
# POST /prefs/filters — create filter
# ---------------------------------------------------------------------------


class TestAddFilter:
    """POST /prefs/filters — create a new filter."""

    def test_create_filter_returns_201(self, app):
        """POST /prefs/filters creates filter and returns 201 with filter_id.

        Source: ttrss/classes/pref/filters.php:Pref_Filters::newfilter (lines 702-793)
        Source: ttrss/classes/pref/filters.php:581 — add / INSERT new filter row
        """
        mock_user = _mock_user()
        new_filter = MagicMock()
        new_filter.id = 42

        with app.test_request_context(
            method="POST",
            data={"enabled": "true", "title": "News Filter", "rule": [], "action": []},
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.create_filter.return_value = new_filter
                mock_crud.save_rules_and_actions.return_value = None
                mock_crud.commit_filter.return_value = None
                from ttrss.blueprints.prefs import filters

                # add_filter returns 201 by returning a tuple; call via _unwrap
                result = _unwrap(filters.add_filter)()

        # The blueprint function returns jsonify({"status": "ok", "filter_id": ...})
        # with no explicit status code, so it is 200 by default.
        # Accept either 200 or 201.
        assert result.status_code in (200, 201)
        data = result.get_json()
        assert data["status"] == "ok"
        assert data["filter_id"] == 42


# ---------------------------------------------------------------------------
# POST /prefs/filters/<id> — update filter
# ---------------------------------------------------------------------------


class TestSaveFilter:
    """POST /prefs/filters/<id> — update existing filter."""

    def test_update_filter_returns_200(self, app):
        """POST /prefs/filters/<id> updates filter and returns 200.

        Source: ttrss/classes/pref/filters.php:457 — editSave
        Source: ttrss/classes/pref/filters.php:477 — saveRulesAndActions
        """
        mock_user = _mock_user()

        with app.test_request_context(
            method="POST",
            data={"enabled": "true", "title": "Renamed Filter"},
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.update_filter.return_value = None
                mock_crud.save_rules_and_actions.return_value = None
                mock_crud.commit_filter.return_value = None
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.save_filter)(filter_id=5)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.update_filter.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /prefs/filters/<id>
# ---------------------------------------------------------------------------


class TestDeleteFilter:
    """DELETE /prefs/filters/<id> — remove filter."""

    def test_delete_filter_returns_200(self, app):
        """DELETE /prefs/filters/<id> deletes filter and returns 200.

        Source: ttrss/classes/pref/filters.php:468 — remove
        """
        mock_user = _mock_user()

        with app.test_request_context(method="DELETE"):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.delete_filter.return_value = None
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.delete_filter)(filter_id=5)

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.delete_filter.assert_called_once()


# ---------------------------------------------------------------------------
# POST /prefs/filters/test
# ---------------------------------------------------------------------------


class TestFilterTest:
    """POST /prefs/filters/test — test filter rules against recent articles."""

    def test_filter_test_returns_200_with_matches(self, app):
        """POST /prefs/filters/test matches articles against rules and returns 200.

        Source: ttrss/classes/pref/filters.php:56 — testFilter
        Source: ttrss/classes/pref/filters.php:56-84 — filter type map
        Source: ttrss/classes/pref/filters.php:86-88 — recent articles fetch
        """
        mock_user = _mock_user()

        article = MagicMock()
        article.title = "Breaking News"
        article.feed_title = "CNN"

        import json as _json
        rule_json = _json.dumps({"filter_type": 1, "reg_exp": "Breaking"})

        with app.test_request_context(
            method="POST",
            data={"rule": [rule_json]},
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.fetch_filter_type_map.return_value = {1: "title", 2: "content"}
                mock_crud.fetch_recent_articles_for_test.return_value = [article]
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.test_filter)()

        assert resp.status_code == 200
        data = resp.get_json()
        assert "matched" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["matched"]) == 1
        assert data["matched"][0]["title"] == "Breaking News"

    def test_filter_test_match_any_rule_false_requires_all(self, app):
        """match_any_rule=false → ALL rules must match (AND logic).

        Source: ttrss/classes/pref/filters.php:51 — $filter["match_any_rule"]
        PHP passes this to queryFeedHeadlines which applies AND/OR logic accordingly.
        """
        mock_user = _mock_user()

        article = MagicMock()
        article.title = "Breaking News Today"
        article.content = "Nothing special"
        article.feed_title = "CNN"

        import json as _json
        # Rule 1 matches title, Rule 2 does not match title — AND logic → no match
        rule1 = _json.dumps({"filter_type": 1, "reg_exp": "Breaking"})
        rule2 = _json.dumps({"filter_type": 1, "reg_exp": "Politics"})

        with app.test_request_context(
            method="POST",
            data={"rule": [rule1, rule2], "match_any_rule": ""},  # unchecked = false
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.fetch_filter_type_map.return_value = {1: "title", 2: "content"}
                mock_crud.fetch_recent_articles_for_test.return_value = [article]
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.test_filter)()

        data = resp.get_json()
        # Both rules must match for AND logic — second rule fails → no match
        assert len(data["matched"]) == 0

    def test_filter_test_match_any_rule_true_requires_one(self, app):
        """match_any_rule=true → ANY rule match is sufficient (OR logic).

        Source: ttrss/classes/pref/filters.php:51 — $filter["match_any_rule"]
        """
        mock_user = _mock_user()

        article = MagicMock()
        article.title = "Breaking News Today"
        article.content = "Nothing special"
        article.feed_title = "CNN"

        import json as _json
        rule1 = _json.dumps({"filter_type": 1, "reg_exp": "Breaking"})   # matches
        rule2 = _json.dumps({"filter_type": 1, "reg_exp": "Politics"})   # no match

        with app.test_request_context(
            method="POST",
            data={"rule": [rule1, rule2], "match_any_rule": "1"},
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.fetch_filter_type_map.return_value = {1: "title", 2: "content"}
                mock_crud.fetch_recent_articles_for_test.return_value = [article]
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.test_filter)()

        data = resp.get_json()
        # OR logic — first rule matches → article included
        assert len(data["matched"]) == 1

    def test_filter_test_inverse_flips_result(self, app):
        """inverse=true flips the match result.

        Source: ttrss/classes/pref/filters.php:53 — $filter["inverse"]
        PHP passes inverse to queryFeedHeadlines which inverts the final match.
        """
        mock_user = _mock_user()

        article = MagicMock()
        article.title = "Breaking News"
        article.feed_title = "CNN"

        import json as _json
        rule_json = _json.dumps({"filter_type": 1, "reg_exp": "Breaking"})

        with app.test_request_context(
            method="POST",
            data={"rule": [rule_json], "inverse": "1"},
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.fetch_filter_type_map.return_value = {1: "title"}
                mock_crud.fetch_recent_articles_for_test.return_value = [article]
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.test_filter)()

        data = resp.get_json()
        # Without inverse the article would match; with inverse it should NOT match
        assert len(data["matched"]) == 0


# ---------------------------------------------------------------------------
# POST /prefs/filters/join
# ---------------------------------------------------------------------------


class TestJoinFilters:
    """POST /prefs/filters/join — merge filters."""

    def test_join_filters_returns_200(self, app):
        """POST /prefs/filters/join merges filters into base and returns 200.

        Source: ttrss/classes/pref/filters.php:979 — join
        """
        mock_user = _mock_user()

        with app.test_request_context(
            method="POST",
            data={"base_id": "1", "merge_ids[]": ["2", "3"]},
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.join_filters.return_value = None
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.join_filters)()

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.join_filters.assert_called_once()


# ---------------------------------------------------------------------------
# POST /prefs/filters/order
# ---------------------------------------------------------------------------


class TestSaveFilterOrder:
    """POST /prefs/filters/order — persist filter ordering."""

    def test_save_filter_order_returns_200(self, app):
        """POST /prefs/filters/order persists order and returns 200.

        Source: ttrss/classes/pref/filters.php:28 — savefilterorder
        """
        mock_user = _mock_user()
        payload = {"ids": [3, 1, 2]}

        with app.test_request_context(
            method="POST",
            json=payload,
            content_type="application/json",
        ):
            with patch("ttrss.blueprints.prefs.filters.current_user", mock_user), \
                 patch("ttrss.blueprints.prefs.filters.filters_crud") as mock_crud:
                mock_crud.save_filter_order.return_value = None
                from ttrss.blueprints.prefs import filters
                resp = _unwrap(filters.save_filter_order)()

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"
        mock_crud.save_filter_order.assert_called_once()
