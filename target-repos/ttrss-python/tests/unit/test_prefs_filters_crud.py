"""Unit tests for ttrss/prefs/filters_crud.py.

Source PHP: ttrss/classes/pref/filters.php (Pref_Filters handler, 1054 lines)

filters_crud.py uses ``from ttrss.extensions import db`` at module import time
(not lazily).  Tests therefore patch ``ttrss.prefs.filters_crud.db`` so that
all db.session.* calls resolve to the mock's session attribute.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_mock():
    """Return a MagicMock shaped like Flask-SQLAlchemy's ``db`` extension."""
    db = MagicMock()
    return db


def _patched_db(db_mock):
    """Context manager: patch the module-level ``db`` in filters_crud."""
    return patch("ttrss.prefs.filters_crud.db", db_mock)


# ---------------------------------------------------------------------------
# 1. get_filter_rows
# ---------------------------------------------------------------------------


class TestGetFilterRows:
    """Source: ttrss/classes/pref/filters.php:getfiltertree (line 159)"""

    def test_execute_called_and_list_returned(self):
        """Source: ttrss/classes/pref/filters.php:159 — SELECT … ORDER BY order_id, title

        get_filter_rows() should call db.session.execute() and return the
        list produced by .scalars().all().
        """
        db = _make_db_mock()
        fake_filter = MagicMock()
        db.session.execute.return_value.scalars.return_value.all.return_value = [fake_filter]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import get_filter_rows
            result = get_filter_rows(owner_uid=1)

        db.session.execute.assert_called_once()
        assert result == [fake_filter]


# ---------------------------------------------------------------------------
# 2. create_filter
# ---------------------------------------------------------------------------


class TestCreateFilter:
    """Source: ttrss/classes/pref/filters.php:add (line 581-583)"""

    def test_add_and_flush_called(self):
        """Source: ttrss/classes/pref/filters.php:581-583 — INSERT new filter row + flush

        create_filter() should call db.session.add() with a new TtRssFilter2 and
        then db.session.flush() to get the auto-generated id without committing.
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import create_filter
            result = create_filter(
                owner_uid=1,
                enabled=True,
                match_any_rule=False,
                inverse=False,
                title="My Filter",
            )

        db.session.add.assert_called_once()
        db.session.flush.assert_called_once()
        db.session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# 3. update_filter
# ---------------------------------------------------------------------------


class TestUpdateFilter:
    """Source: ttrss/classes/pref/filters.php:editSave (line 457-462)"""

    def test_execute_called_without_commit(self):
        """Source: ttrss/classes/pref/filters.php:457-462 — UPDATE core fields, no commit here

        update_filter() issues an UPDATE via db.session.execute() but should NOT
        commit (the caller is responsible for committing via commit_filter()).
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import update_filter
            update_filter(
                filter_id=5, owner_uid=1,
                enabled=True, match_any_rule=True, inverse=False, title="Updated",
            )

        db.session.execute.assert_called_once()
        db.session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# 4-5. fetch_filter
# ---------------------------------------------------------------------------


class TestFetchFilter:
    """Source: ttrss/classes/pref/filters.php:edit (line 234)"""

    def test_found_returns_object(self):
        """Source: ttrss/classes/pref/filters.php:234 — SELECT WHERE id AND owner_uid

        fetch_filter() should return the ORM object when the filter is found
        and belongs to owner_uid.
        """
        db = _make_db_mock()
        fake_filter = MagicMock()
        db.session.execute.return_value.scalar_one_or_none.return_value = fake_filter

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_filter
            result = fetch_filter(filter_id=5, owner_uid=1)

        assert result is fake_filter

    def test_wrong_uid_returns_none(self):
        """Source: ttrss/classes/pref/filters.php:234 — ownership enforced via owner_uid WHERE clause

        fetch_filter() should return None when owner_uid does not match — the DB
        query finds nothing and scalar_one_or_none() returns None.
        """
        db = _make_db_mock()
        db.session.execute.return_value.scalar_one_or_none.return_value = None

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_filter
            result = fetch_filter(filter_id=5, owner_uid=999)

        assert result is None


# ---------------------------------------------------------------------------
# 6. fetch_filter_rules
# ---------------------------------------------------------------------------


class TestFetchFilterRules:
    """Source: ttrss/classes/pref/filters.php:edit (line 282-301)"""

    def test_scalars_list_returned(self):
        """Source: ttrss/classes/pref/filters.php:282-301 — SELECT rules ORDER BY reg_exp, id

        fetch_filter_rules() should return the list obtained from .scalars().all().
        """
        db = _make_db_mock()
        fake_rule = MagicMock()
        db.session.execute.return_value.scalars.return_value.all.return_value = [fake_rule]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_filter_rules
            result = fetch_filter_rules(filter_id=5)

        assert result == [fake_rule]


# ---------------------------------------------------------------------------
# 7. delete_filter
# ---------------------------------------------------------------------------


class TestDeleteFilter:
    """Source: ttrss/classes/pref/filters.php:remove (line 468)"""

    def test_execute_and_commit_called(self):
        """Source: ttrss/classes/pref/filters.php:468 — DELETE WHERE id AND owner_uid, then commit

        delete_filter() should issue the DELETE via execute() and then call commit().
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import delete_filter
            delete_filter(filter_id=5, owner_uid=1)

        db.session.execute.assert_called_once()
        db.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 8. save_rules_and_actions — valid rule
# ---------------------------------------------------------------------------


class TestSaveRulesAndActions:
    """Source: ttrss/classes/pref/filters.php:saveRulesAndActions (line 477)"""

    def test_begin_nested_delete_and_add_called(self):
        """Source: ttrss/classes/pref/filters.php:479-480 — delete existing rules/actions first
                   ttrss/classes/pref/filters.php:488-536 — insert new rules
                   ttrss/classes/pref/filters.php:577,592 — savepoint wraps deletion + insertion

        For a valid rule JSON, save_rules_and_actions() must:
          1. Enter a savepoint (begin_nested)
          2. DELETE existing rules and actions (two execute() calls)
          3. ADD a new TtRssFilter2Rule (session.add)
          4. ADD any provided actions (session.add again)
        """
        db = _make_db_mock()
        # begin_nested() must work as a context manager
        ctx = MagicMock()
        db.session.begin_nested.return_value = ctx

        rule_json = json.dumps({"reg_exp": "foo.*bar", "filter_type": 1, "feed_id": ""})
        action_json = json.dumps({"action_id": 2, "action_param": "", "action_param_label": ""})

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(filter_id=5, rules_json_list=[rule_json], actions_json_list=[action_json])

        db.session.begin_nested.assert_called_once()
        # Two DELETEs: rules + actions
        assert db.session.execute.call_count >= 2
        # At least one add call (for the rule and/or action)
        assert db.session.add.call_count >= 1

    def test_invalid_regex_skipped(self):
        """Source: ttrss/classes/pref/filters.php:509 — validate regex before saving (@preg_match)

        Rules with invalid regexes must be silently skipped (PHP: @preg_match returns
        false/0 for bad patterns).  No TtRssFilter2Rule should be added for a rule
        whose reg_exp fails re.compile().
        """
        db = _make_db_mock()
        ctx = MagicMock()
        db.session.begin_nested.return_value = ctx

        bad_rule_json = json.dumps({"reg_exp": "[", "filter_type": 1, "feed_id": ""})

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(filter_id=5, rules_json_list=[bad_rule_json], actions_json_list=[])

        rule_adds = [
            c for c in db.session.add.call_args_list
            if hasattr(c[0][0], "reg_exp")
        ]
        # Invalid regex must be skipped — no rule added.
        assert len(rule_adds) == 0


# ---------------------------------------------------------------------------
# 10-11. join_filters
# ---------------------------------------------------------------------------


class TestJoinFilters:
    """Source: ttrss/classes/pref/filters.php:join (line 979)"""

    def test_owned_base_triggers_execute_and_commit(self):
        """Source: ttrss/classes/pref/filters.php:986-993 — move rules/actions into base_id
                   ttrss/classes/pref/filters.php:992 — delete merged filters
                   ttrss/classes/pref/filters.php:993 — set match_any_rule on base

        When base_id is owned by owner_uid, join_filters() must:
          - verify ownership (scalar_one_or_none returns a value)
          - call execute() multiple times (UPDATE rules, UPDATE actions, DELETE, UPDATE base)
          - call commit() once at the end
        """
        db = _make_db_mock()
        # Ownership check for base_id → returns its id (truthy)
        db.session.execute.return_value.scalar_one_or_none.return_value = 1
        # optimize_filter inner queries return empty lists
        db.session.execute.return_value.scalars.return_value.all.return_value = []

        with _patched_db(db):
            from ttrss.prefs.filters_crud import join_filters
            join_filters(owner_uid=1, base_id=1, merge_ids=[2])

        assert db.session.execute.call_count >= 4
        db.session.commit.assert_called_once()

    def test_non_owned_base_returns_immediately(self):
        """Source: ttrss/classes/pref/filters.php:join — security: base filter ownership guard
        (D01) If base_id is not owned by owner_uid, join_filters() should abort
        immediately — no UPDATE or DELETE should be executed.
        """
        db = _make_db_mock()
        # Ownership check for base_id → None (not owned)
        db.session.execute.return_value.scalar_one_or_none.return_value = None

        with _patched_db(db):
            from ttrss.prefs.filters_crud import join_filters
            join_filters(owner_uid=1, base_id=999, merge_ids=[2])

        # Only the ownership-check execute() should have been called
        assert db.session.execute.call_count == 1
        db.session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# 11. fetch_filter_actions
# ---------------------------------------------------------------------------


class TestFetchFilterActions:
    """Source: ttrss/classes/pref/filters.php:edit (line 330-344)"""

    def test_returns_list_of_action_rows(self):
        """Source: ttrss/classes/pref/filters.php:330-344 — SELECT actions ORDER BY id

        fetch_filter_actions() should call db.session.execute() and return the
        list produced by .scalars().all(), ordered by action id.
        """
        db = _make_db_mock()
        fake_action = MagicMock()
        db.session.execute.return_value.scalars.return_value.all.return_value = [fake_action]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_filter_actions
            result = fetch_filter_actions(filter_id=7)

        db.session.execute.assert_called_once()
        assert result == [fake_action]

    def test_no_actions_returns_empty_list(self):
        """Source: ttrss/classes/pref/filters.php:330-344 — empty result for filter with no actions

        fetch_filter_actions() should return [] when the DB has no action rows
        for the given filter_id.
        """
        db = _make_db_mock()
        db.session.execute.return_value.scalars.return_value.all.return_value = []

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_filter_actions
            result = fetch_filter_actions(filter_id=99)

        assert result == []


# ---------------------------------------------------------------------------
# 12. save_rules_and_actions — action insertion paths
# ---------------------------------------------------------------------------


class TestSaveRulesAndActionsActions:
    """Source: ttrss/classes/pref/filters.php:saveRulesAndActions (line 538-560)"""

    def test_action_id7_uses_action_param_label(self):
        """Source: ttrss/classes/pref/filters.php:545-551 — action_id=7 uses action_param_label

        When action_id == 7, save_rules_and_actions() should store action_param_label
        as the action_param value (not the raw action_param field).
        """
        db = _make_db_mock()
        ctx = MagicMock()
        db.session.begin_nested.return_value = ctx

        rule_json = json.dumps({"reg_exp": "test", "filter_type": 1, "feed_id": ""})
        action_json = json.dumps({
            "action_id": 7,
            "action_param": "ignored",
            "action_param_label": "label_value",
        })

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(filter_id=5, rules_json_list=[rule_json], actions_json_list=[action_json])

        # Verify an action was added; exact param checked via call inspection
        action_adds = [
            c for c in db.session.add.call_args_list
            if hasattr(c[0][0], "action_id")
        ]
        assert len(action_adds) == 1
        added_action = action_adds[0][0][0]
        assert added_action.action_param == "label_value"

    def test_action_id6_strips_plus_from_param(self):
        """Source: ttrss/classes/pref/filters.php:549-551 — action_id=6 normalises score param

        When action_id == 6, save_rules_and_actions() should strip a leading '+'
        and convert the value to an int string (e.g. '+10' → '10').
        """
        db = _make_db_mock()
        ctx = MagicMock()
        db.session.begin_nested.return_value = ctx

        rule_json = json.dumps({"reg_exp": "test", "filter_type": 1, "feed_id": ""})
        action_json = json.dumps({
            "action_id": 6,
            "action_param": "+10",
            "action_param_label": "",
        })

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(filter_id=5, rules_json_list=[rule_json], actions_json_list=[action_json])

        action_adds = [
            c for c in db.session.add.call_args_list
            if hasattr(c[0][0], "action_id")
        ]
        assert len(action_adds) == 1
        added_action = action_adds[0][0][0]
        assert added_action.action_param == "10"

    def test_duplicate_action_skipped(self):
        """Source: ttrss/classes/pref/filters.php:541-543 — skip duplicate action entries

        When two identical action JSON blobs are passed, the second should be
        de-duplicated and only one TtRssFilter2Action should be added.
        """
        db = _make_db_mock()
        ctx = MagicMock()
        db.session.begin_nested.return_value = ctx

        rule_json = json.dumps({"reg_exp": "test", "filter_type": 1, "feed_id": ""})
        action_json = json.dumps({"action_id": 2, "action_param": "", "action_param_label": ""})

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(
                filter_id=5,
                rules_json_list=[rule_json],
                actions_json_list=[action_json, action_json],  # duplicate
            )

        action_adds = [
            c for c in db.session.add.call_args_list
            if hasattr(c[0][0], "action_id")
        ]
        assert len(action_adds) == 1


# ---------------------------------------------------------------------------
# 13. save_filter_order
# ---------------------------------------------------------------------------


class TestSaveFilterOrder:
    """Source: ttrss/classes/pref/filters.php:savefilterorder (line 28-41)"""

    def test_update_called_per_filter_then_commit(self):
        """Source: ttrss/classes/pref/filters.php:28-41 — UPDATE order_id for each filter, commit

        save_filter_order() should call db.session.execute() once for each
        filter_id in the supplied list and then call commit() exactly once.
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_filter_order
            save_filter_order(owner_uid=1, filter_id_order=[10, 20, 30])

        assert db.session.execute.call_count == 3
        db.session.commit.assert_called_once()

    def test_empty_order_commits_without_updates(self):
        """Source: ttrss/classes/pref/filters.php:28-41 — no-op when list is empty, still commits

        save_filter_order() with an empty list should still call commit() but
        should not issue any UPDATE execute() calls.
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_filter_order
            save_filter_order(owner_uid=1, filter_id_order=[])

        db.session.execute.assert_not_called()
        db.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 14. reset_filter_order
# ---------------------------------------------------------------------------


class TestResetFilterOrder:
    """Source: ttrss/classes/pref/filters.php:filtersortreset (line 11)"""

    def test_update_and_commit_called(self):
        """Source: ttrss/classes/pref/filters.php:filtersortreset (line 11)
        PHP: UPDATE ttrss_filters2 SET order_id=0 WHERE owner_uid.

        reset_filter_order() should issue one UPDATE execute() and then commit.
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import reset_filter_order
            reset_filter_order(owner_uid=1)

        db.session.execute.assert_called_once()
        db.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# 15. fetch_recent_articles_for_test
# ---------------------------------------------------------------------------


class TestFetchRecentArticlesForTest:
    """Source: ttrss/classes/pref/filters.php:testFilter (line 86-88)"""

    def test_returns_list_from_execute(self):
        """Source: ttrss/classes/pref/filters.php:testFilter (lines 86-88)
        PHP: SELECT title, content, link, author, date_entered, feed_title
             FROM ttrss_entries … ORDER BY date_entered DESC LIMIT limit.

        fetch_recent_articles_for_test() should call db.session.execute() once
        and return the raw row list produced by .all().
        """
        db = _make_db_mock()
        fake_row = MagicMock()
        db.session.execute.return_value.all.return_value = [fake_row]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_recent_articles_for_test
            result = fetch_recent_articles_for_test(owner_uid=1, limit=5)

        db.session.execute.assert_called_once()
        assert result == [fake_row]

    def test_default_limit_respected(self):
        """Source: ttrss/classes/pref/filters.php:testFilter (line 86) — default limit=30

        When called without an explicit limit, fetch_recent_articles_for_test()
        should still call execute() once (the default limit of 30 is baked into
        the query via .limit(30)).
        """
        db = _make_db_mock()
        db.session.execute.return_value.all.return_value = []

        with _patched_db(db):
            from ttrss.prefs.filters_crud import fetch_recent_articles_for_test
            result = fetch_recent_articles_for_test(owner_uid=1)

        db.session.execute.assert_called_once()
        assert result == []


# ---------------------------------------------------------------------------
# 16. get_rule_reg_exps_for_filter
# ---------------------------------------------------------------------------


class TestGetRuleRegExpsForFilter:
    """Source: ttrss/classes/pref/filters.php:getfiltertree (line 180-191)"""

    def test_returns_scalars_list(self):
        """Source: ttrss/classes/pref/filters.php:getfiltertree (lines 180-191)
        PHP: SELECT reg_exp FROM ttrss_filters2_rules WHERE filter_id.

        get_rule_reg_exps_for_filter() should call db.session.execute() once and
        return the list produced by .scalars().all().
        """
        db = _make_db_mock()
        db.session.execute.return_value.scalars.return_value.all.return_value = ["foo.*", "bar"]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import get_rule_reg_exps_for_filter
            result = get_rule_reg_exps_for_filter(filter_id=3)

        db.session.execute.assert_called_once()
        assert result == ["foo.*", "bar"]


# ---------------------------------------------------------------------------
# 17. get_filter_name
# ---------------------------------------------------------------------------


class TestGetFilterName:
    """Source: ttrss/classes/pref/filters.php:getFilterName (line 944)"""

    def test_unknown_filter_returns_fallback_tuple(self):
        """Source: ttrss/classes/pref/filters.php:getFilterName (line 944)
        PHP: returns ('[Unknown]', '') when filter_id does not exist.

        get_filter_name() should return ('[Unknown]', '') when the first query
        finds no row (one_or_none returns None).
        """
        db = _make_db_mock()
        db.session.execute.return_value.one_or_none.return_value = None

        with _patched_db(db):
            from ttrss.prefs.filters_crud import get_filter_name
            title, actions = get_filter_name(filter_id=999)

        assert title == "[Unknown]"
        assert actions == ""

    def test_known_filter_no_title_returns_no_caption(self):
        """Source: ttrss/classes/pref/filters.php:getFilterName (line 944)
        PHP: title=None is replaced with '[No caption]'.

        When the filter row has title=None, get_filter_name() should use
        '[No caption]' as the base title string.
        """
        db = _make_db_mock()

        fake_row = MagicMock()
        fake_row.title = None
        fake_row.num_rules = 1
        fake_row.num_actions = 0

        # First execute → one_or_none returns the row
        # Second execute (first action) → one_or_none returns None (no actions)
        db.session.execute.return_value.one_or_none.side_effect = [fake_row, None]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import get_filter_name
            title, actions = get_filter_name(filter_id=5)

        assert "[No caption]" in title
        assert "(1 rule)" in title
        assert actions == ""

    def test_known_filter_with_title_and_single_action(self):
        """Source: ttrss/classes/pref/filters.php:getFilterName (line 944)
        PHP: title shown with rule count and first action description.

        When a filter has a title, 2 rules, and 1 action (action_id not in 4/6/7),
        get_filter_name() should return a title like 'My Filter (2 rules)'
        and the action description as the actions string.
        """
        db = _make_db_mock()

        fake_row = MagicMock()
        fake_row.title = "My Filter"
        fake_row.num_rules = 2
        fake_row.num_actions = 1

        fake_action_row = MagicMock()
        # first_action[0] is the TtRssFilter2Action, first_action.description is action description
        fake_action_row.__getitem__ = lambda self, idx: MagicMock(action_id=2, action_param="")
        fake_action_row.description = "Mark as read"

        db.session.execute.return_value.one_or_none.side_effect = [fake_row, fake_action_row]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import get_filter_name
            title, actions = get_filter_name(filter_id=5)

        assert "My Filter" in title
        assert "(2 rules)" in title
        assert "Mark as read" in actions

    def test_known_filter_action_id4_appends_param(self):
        """Source: ttrss/classes/pref/filters.php:getFilterName — action_id in (4, 6, 7) appends param

        When the first action has action_id == 4 (assign label), the action_param
        should be appended to the description with ': '.
        """
        db = _make_db_mock()

        fake_row = MagicMock()
        fake_row.title = "Labeller"
        fake_row.num_rules = 1
        fake_row.num_actions = 1

        fake_action_obj = MagicMock()
        fake_action_obj.action_id = 4
        fake_action_obj.action_param = "news"

        fake_action_row = MagicMock()
        fake_action_row.__getitem__ = lambda self, idx: fake_action_obj
        fake_action_row.description = "Assign label"

        db.session.execute.return_value.one_or_none.side_effect = [fake_row, fake_action_row]

        with _patched_db(db):
            from ttrss.prefs.filters_crud import get_filter_name
            title, actions = get_filter_name(filter_id=5)

        assert "Assign label: news" in actions


# ---------------------------------------------------------------------------
# 18. optimize_filter — deduplication paths
# ---------------------------------------------------------------------------


class TestOptimizeFilter:
    """Source: ttrss/classes/pref/filters.php:optimizeFilter (line 1002)"""

    def test_no_duplicates_nothing_deleted(self):
        """Source: ttrss/classes/pref/filters.php:optimizeFilter (line 1002)
        PHP: scans actions and rules; skips DELETE when no duplicates found.

        optimize_filter() with unique actions and rules should not call any
        DELETE execute() — only the two SELECT execute() calls.
        """
        db = _make_db_mock()

        action1 = MagicMock()
        action1.id = 1
        action1.action_id = 2
        action1.action_param = ""

        rule1 = MagicMock()
        rule1.id = 10
        rule1.reg_exp = "foo"
        rule1.filter_type = 1
        rule1.feed_id = None
        rule1.cat_id = None
        rule1.cat_filter = False
        rule1.inverse = False

        # Two scalars().all() calls: first for actions, second for rules
        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            m.all.return_value = [action1] if call_count["n"] == 0 else [rule1]
            call_count["n"] += 1
            return m

        db.session.execute.return_value.scalars.side_effect = scalars_se

        with _patched_db(db):
            from ttrss.prefs.filters_crud import optimize_filter
            optimize_filter(filter_id=5)

        # No DELETE execute calls — only the two SELECT-type calls
        assert db.session.execute.call_count == 2
        db.session.commit.assert_not_called()

    def test_duplicate_actions_triggers_delete(self):
        """Source: ttrss/classes/pref/filters.php:optimizeFilter (line 1002)
        PHP: duplicate (action_id, action_param) pairs → DELETE the extra row.

        When two action rows share the same (action_id, action_param), the second
        should be collected into dupe_ids and a DELETE execute() should be issued.
        """
        db = _make_db_mock()

        def make_action(aid, pid, param):
            a = MagicMock()
            a.id = aid
            a.action_id = pid
            a.action_param = param
            return a

        a1 = make_action(1, 2, "")
        a2 = make_action(2, 2, "")  # duplicate of a1

        rule1 = MagicMock()
        rule1.id = 10
        rule1.reg_exp = "foo"
        rule1.filter_type = 1
        rule1.feed_id = None
        rule1.cat_id = None
        rule1.cat_filter = False
        rule1.inverse = False

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            m.all.return_value = [a1, a2] if call_count["n"] == 0 else [rule1]
            call_count["n"] += 1
            return m

        db.session.execute.return_value.scalars.side_effect = scalars_se

        with _patched_db(db):
            from ttrss.prefs.filters_crud import optimize_filter
            optimize_filter(filter_id=5)

        # Should have 3 execute calls: actions SELECT, DELETE dupes, rules SELECT
        assert db.session.execute.call_count == 3

    def test_duplicate_rules_triggers_delete(self):
        """Source: ttrss/classes/pref/filters.php:optimizeFilter (line 1002)
        PHP: duplicate rule keys → DELETE the extra rule row.

        When two rule rows are identical on all key fields, the second should be
        flagged as a duplicate and a DELETE execute() should be issued.
        """
        db = _make_db_mock()

        def make_rule(rid):
            r = MagicMock()
            r.id = rid
            r.reg_exp = "bar"
            r.filter_type = 1
            r.feed_id = None
            r.cat_id = None
            r.cat_filter = False
            r.inverse = False
            return r

        r1 = make_rule(10)
        r2 = make_rule(11)  # duplicate of r1

        call_count = {"n": 0}
        def scalars_se(*a, **kw):
            m = MagicMock()
            m.all.return_value = [] if call_count["n"] == 0 else [r1, r2]
            call_count["n"] += 1
            return m

        db.session.execute.return_value.scalars.side_effect = scalars_se

        with _patched_db(db):
            from ttrss.prefs.filters_crud import optimize_filter
            optimize_filter(filter_id=5)

        # Should have 3 execute calls: actions SELECT (no dupes), rules SELECT, DELETE dupes
        assert db.session.execute.call_count == 3


# ---------------------------------------------------------------------------
# 19. join_filters — empty merge_ids early-return
# ---------------------------------------------------------------------------


class TestJoinFiltersEmptyMerge:
    """Source: ttrss/classes/pref/filters.php:join (line 979) — empty merge guard"""

    def test_empty_merge_ids_returns_without_any_db_call(self):
        """Source: ttrss/classes/pref/filters.php:join (line 979)
        PHP: early return when merge_ids list is empty to avoid a no-op query.

        join_filters() should return immediately (no execute, no commit) when
        merge_ids is an empty list.
        """
        db = _make_db_mock()

        with _patched_db(db):
            from ttrss.prefs.filters_crud import join_filters
            join_filters(owner_uid=1, base_id=1, merge_ids=[])

        db.session.execute.assert_not_called()
        db.session.commit.assert_not_called()
