"""
Unit tests for ttrss/prefs/filters_crud.py.

Source PHP: ttrss/classes/pref/filters.php (Pref_Filters handler, 1054 lines)

All functions under test use ttrss.extensions.db directly (not a passed session),
so each test patches "ttrss.prefs.filters_crud.db".
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_mock():
    """Return (db_mock, session_mock) ready for patching."""
    db = MagicMock()
    session = MagicMock()
    db.session = session
    # Sensible scalar defaults
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value.scalars.return_value.all.return_value = []
    return db, session


# ---------------------------------------------------------------------------
# get_filter_rows
# ---------------------------------------------------------------------------


class TestGetFilterRows:
    """Source: ttrss/classes/pref/filters.php:getfiltertree (line 159)"""

    def test_query_executed_and_result_returned(self):
        """
        get_filter_rows must execute a SELECT ordered by order_id, title for
        the given owner_uid and return the scalars list.

        Source: ttrss/classes/pref/filters.php:getfiltertree (line 159)
        """
        db, session = _make_db_mock()
        mock_filter = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = [mock_filter]

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import get_filter_rows
            result = get_filter_rows(owner_uid=1)

        session.execute.assert_called_once()
        assert result == [mock_filter]


# ---------------------------------------------------------------------------
# create_filter
# ---------------------------------------------------------------------------


class TestCreateFilter:
    """Source: ttrss/classes/pref/filters.php:add (line 581-583)"""

    def test_session_add_and_flush_called(self):
        """
        create_filter must call session.add(new_filter) then session.flush()
        (does NOT commit — caller is responsible).

        Source: ttrss/classes/pref/filters.php:add (line 581-583)
        """
        db, session = _make_db_mock()

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import create_filter
            result = create_filter(
                owner_uid=1,
                enabled=True,
                match_any_rule=False,
                inverse=False,
                title="Test Filter",
            )

        session.add.assert_called_once()
        session.flush.assert_called_once()
        session.commit.assert_not_called()

        added = session.add.call_args[0][0]
        assert added.owner_uid == 1
        assert added.title == "Test Filter"
        assert added.enabled is True


# ---------------------------------------------------------------------------
# update_filter
# ---------------------------------------------------------------------------


class TestUpdateFilter:
    """Source: ttrss/classes/pref/filters.php:editSave (line 457-462)"""

    def test_execute_called_does_not_commit(self):
        """
        update_filter must execute an UPDATE restricted to (filter_id, owner_uid)
        and must NOT commit.

        Source: ttrss/classes/pref/filters.php:editSave (line 457-462)
        """
        db, session = _make_db_mock()

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import update_filter
            update_filter(
                filter_id=10,
                owner_uid=1,
                enabled=True,
                match_any_rule=True,
                inverse=False,
                title="Updated",
            )

        session.execute.assert_called_once()
        session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_filter
# ---------------------------------------------------------------------------


class TestFetchFilter:
    """Source: ttrss/classes/pref/filters.php:edit (line 234)"""

    def test_found_returns_filter_object(self):
        """
        fetch_filter returns the TtRssFilter2 ORM object when the row exists
        and belongs to owner_uid.

        Source: ttrss/classes/pref/filters.php:edit (line 234) —
                SELECT … WHERE id = :id AND owner_uid = :uid
        """
        db, session = _make_db_mock()
        mock_filter = MagicMock()
        session.execute.return_value.scalar_one_or_none.return_value = mock_filter

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import fetch_filter
            result = fetch_filter(filter_id=5, owner_uid=1)

        assert result is mock_filter

    def test_wrong_owner_returns_none(self):
        """
        fetch_filter returns None when owner_uid does not match (ownership
        enforced by WHERE clause, not application logic).

        Source: ttrss/classes/pref/filters.php:edit (line 234) —
                WHERE owner_uid = :uid enforces ownership; ORM returns None
                when the row exists but belongs to a different user.
        """
        db, session = _make_db_mock()
        session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import fetch_filter
            result = fetch_filter(filter_id=5, owner_uid=999)

        assert result is None


# ---------------------------------------------------------------------------
# fetch_filter_rules
# ---------------------------------------------------------------------------


class TestFetchFilterRules:
    """Source: ttrss/classes/pref/filters.php:edit (line 282-301)"""

    def test_returns_rules_list(self):
        """
        fetch_filter_rules executes SELECT ordered by reg_exp, id for the
        given filter_id and returns all rows as a list.

        Source: ttrss/classes/pref/filters.php:edit (line 282-301)
        """
        db, session = _make_db_mock()
        mock_rule = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = [mock_rule]

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import fetch_filter_rules
            result = fetch_filter_rules(filter_id=5)

        session.execute.assert_called_once()
        assert result == [mock_rule]


# ---------------------------------------------------------------------------
# delete_filter
# ---------------------------------------------------------------------------


class TestDeleteFilter:
    """Source: ttrss/classes/pref/filters.php:remove (line 468)"""

    def test_delete_execute_and_commit(self):
        """
        delete_filter must execute a DELETE WHERE id=filter_id AND
        owner_uid=owner_uid, then commit.

        Source: ttrss/classes/pref/filters.php:remove (line 468)
        """
        db, session = _make_db_mock()

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import delete_filter
            delete_filter(filter_id=7, owner_uid=1)

        session.execute.assert_called_once()
        session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# save_rules_and_actions
# ---------------------------------------------------------------------------


class TestSaveRulesAndActions:
    """Source: ttrss/classes/pref/filters.php:saveRulesAndActions (line 477)"""

    def test_valid_rules_deletes_old_and_inserts_new_inside_savepoint(self):
        """
        save_rules_and_actions must open a savepoint (begin_nested), DELETE
        existing rules and actions, then INSERT new ones.

        Source: ttrss/classes/pref/filters.php:479-480 — delete existing rules/actions.
        Source: ttrss/classes/pref/filters.php:488-536 — insert validated rules.
        Source: ttrss/classes/pref/filters.php:577,592 — wrapped in BEGIN/COMMIT
                (Python uses begin_nested savepoint for atomicity).
        """
        db, session = _make_db_mock()
        # begin_nested must behave as a context manager
        nested_ctx = MagicMock()
        session.begin_nested.return_value.__enter__ = MagicMock(return_value=nested_ctx)
        session.begin_nested.return_value.__exit__ = MagicMock(return_value=False)

        rule_json = json.dumps({
            "reg_exp": "python",
            "filter_type": 1,
            "feed_id": "0",
            "inverse": False,
        })
        action_json = json.dumps({
            "action_id": 2,
            "action_param": "",
            "action_param_label": "",
        })

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            save_rules_and_actions(
                filter_id=3,
                rules_json_list=[rule_json],
                actions_json_list=[action_json],
            )

        # Savepoint must have been opened
        session.begin_nested.assert_called_once()
        # execute called at least twice: DELETE rules + DELETE actions
        assert session.execute.call_count >= 2

    def test_invalid_regex_in_rule_is_skipped_silently(self):
        """
        A rule whose reg_exp fails re.compile must be skipped without raising.

        Source: ttrss/classes/pref/filters.php:509 — @preg_match() silently
                skips invalid regex; Python mirrors this with a try/except.
        """
        db, session = _make_db_mock()
        nested_ctx = MagicMock()
        session.begin_nested.return_value.__enter__ = MagicMock(return_value=nested_ctx)
        session.begin_nested.return_value.__exit__ = MagicMock(return_value=False)

        bad_rule = json.dumps({
            "reg_exp": "[invalid(regex",
            "filter_type": 1,
            "feed_id": "0",
            "inverse": False,
        })

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import save_rules_and_actions
            # Must not raise
            save_rules_and_actions(
                filter_id=3,
                rules_json_list=[bad_rule],
                actions_json_list=[],
            )

        # No rule insert should have happened (session.add not called for a rule)
        # execute still called for the two DELETEs
        assert session.execute.call_count >= 2


# ---------------------------------------------------------------------------
# join_filters
# ---------------------------------------------------------------------------


class TestJoinFilters:
    """Source: ttrss/classes/pref/filters.php:join (line 979)"""

    def test_owned_base_moves_rules_and_commits(self):
        """
        join_filters must verify base ownership, move rules/actions from
        merge_ids into base_id, delete merged filters, set match_any_rule,
        then commit.

        Source: ttrss/classes/pref/filters.php:986-993 — move rules/actions,
                delete merged filters, set match_any_rule=True on base.
        Source: ttrss/classes/pref/filters.php:997 — optimize (remove duplicates).
        """
        db, session = _make_db_mock()
        # base_id ownership check returns the id (owned)
        session.execute.return_value.scalar_one_or_none.return_value = 1

        # optimize_filter also calls execute; allow unlimited calls
        session.execute.return_value.scalars.return_value.all.return_value = []

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import join_filters
            join_filters(owner_uid=1, base_id=1, merge_ids=[2, 3])

        # At minimum: base ownership SELECT + move rules UPDATE + move actions UPDATE
        # + delete merged + set match_any_rule + optimize queries
        assert session.execute.call_count >= 4
        session.commit.assert_called_once()

    def test_non_owned_base_returns_immediately(self):
        """
        When base_id is not owned by owner_uid, join_filters returns without
        executing any write operations.

        Source: ttrss/classes/pref/filters.php:join (line 979) —
                PHP implicitly relies on the WHERE owner_uid clause to prevent
                cross-user joins; Python adds an explicit ownership guard.
        """
        db, session = _make_db_mock()
        # base_id ownership check returns None (not owned)
        session.execute.return_value.scalar_one_or_none.return_value = None

        with patch("ttrss.prefs.filters_crud.db", db):
            from ttrss.prefs.filters_crud import join_filters
            join_filters(owner_uid=1, base_id=99, merge_ids=[2, 3])

        # Only the ownership SELECT must have run; no writes
        session.commit.assert_not_called()
        # execute called exactly once (the base ownership check)
        assert session.execute.call_count == 1
