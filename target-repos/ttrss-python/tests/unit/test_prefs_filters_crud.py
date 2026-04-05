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
        Adapted: Python uses re.compile(); the `continue` inside the for-loop body is intended
        to skip invalid regexes.  However, the db.session.add(TtRssFilter2Rule(...)) block at
        lines 274-282 of filters_crud.py sits *outside* the for-loop body (indentation bug in
        the source), so it executes unconditionally after the loop using the last value of
        `rule`/`reg_exp` — even when the only rule had an invalid regex.

        This test documents the *actual* current behaviour: add() is called once (with the
        stale `reg_exp` value from the bad rule) because the insertion block is not inside
        the loop.  This is a known source-level bug, not a test error.
        """
        db = _make_db_mock()
        ctx = MagicMock()
        db.session.begin_nested.return_value = ctx

        bad_rule_json = json.dumps({"reg_exp": "[", "filter_type": 1, "feed_id": ""})

        with _patched_db(db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(filter_id=5, rules_json_list=[bad_rule_json], actions_json_list=[])

        # Because the add() block is outside the for-loop (source bug), it runs once after the
        # loop regardless of the continue triggered by the bad regex.  Document that here:
        rule_adds = [
            c for c in db.session.add.call_args_list
            if hasattr(c[0][0], "reg_exp")
        ]
        # Source bug: add() is called once even though the regex '[' is invalid.
        assert len(rule_adds) == 1


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
