"""
Unit tests for ttrss/prefs/ops.py.

Source PHP: ttrss/include/db-prefs.php (get_pref, set_pref, initialize_user_prefs)
            ttrss/include/functions.php:get_schema_version (line 988)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_mock():
    """Return a MagicMock that stands in for ttrss.extensions.db."""
    db = MagicMock()
    session = MagicMock()
    db.session = session
    return db, session


# ---------------------------------------------------------------------------
# get_schema_version
# ---------------------------------------------------------------------------


class TestGetSchemaVersion:
    """Source: ttrss/include/functions.php:get_schema_version (line 988)"""

    def test_returns_schema_version_int_when_row_exists(self):
        """
        When ttrss_version has a row, return its schema_version as int.

        Source: ttrss/include/functions.php:get_schema_version (line 988-989)
        Source: ttrss/include/sessions.php:session_get_schema_version (lines 26-31)
        """
        db, session = _make_db_mock()

        mock_row = MagicMock()
        mock_row.schema_version = 142
        session.query.return_value.first.return_value = mock_row

        with patch("ttrss.prefs.ops.db", db):
            from ttrss.prefs.ops import get_schema_version
            result = get_schema_version()

        assert result == 142
        session.query.assert_called_once()

    def test_returns_zero_when_no_row(self):
        """
        When ttrss_version is empty, return 0 (guard against empty table).

        Source: ttrss/include/functions.php:get_schema_version (line 988)
        Adapted: PHP assumes ttrss_version always has one row; Python guards
                 against the empty-table edge-case (no PHP equivalent).
        """
        db, session = _make_db_mock()
        session.query.return_value.first.return_value = None

        with patch("ttrss.prefs.ops.db", db):
            from ttrss.prefs.ops import get_schema_version
            result = get_schema_version()

        assert result == 0


# ---------------------------------------------------------------------------
# get_user_pref
# ---------------------------------------------------------------------------


class TestGetUserPref:
    """Source: ttrss/include/db-prefs.php:get_pref (full function)"""

    def _run(self, db, **kwargs):
        with patch("ttrss.prefs.ops.db", db):
            from ttrss.prefs.ops import get_user_pref
            return get_user_pref(**kwargs)

    def test_user_row_exists_returns_user_value(self):
        """
        When a ttrss_user_prefs row exists for (owner_uid, pref_name), return its value.

        Source: ttrss/include/db-prefs.php:get_pref — return $row['value'] (user override)
        """
        db, session = _make_db_mock()

        user_row = MagicMock()
        user_row.value = "dark"
        # query chain: .filter().filter().first()
        session.query.return_value.filter.return_value.filter.return_value.first.return_value = user_row

        result = self._run(db, owner_uid=1, pref_name="THEME")
        assert result == "dark"

    def test_no_user_row_system_row_returns_def_value(self):
        """
        When no user row exists but ttrss_prefs row exists, return def_value.

        Source: ttrss/include/db-prefs.php:get_pref — fallback SELECT def_value
                FROM ttrss_prefs WHERE pref_name = :pref_name
        """
        db, session = _make_db_mock()

        # user query returns None
        session.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        # system fallback via session.get
        system_row = MagicMock()
        system_row.def_value = "light"
        session.get.return_value = system_row

        result = self._run(db, owner_uid=1, pref_name="THEME")
        assert result == "light"

    def test_no_rows_returns_none(self):
        """
        When neither user nor system row exists, return None.

        Source: ttrss/include/db-prefs.php:get_pref — PHP returns false for
                unknown pref_name; Python returns None (no PHP equivalent guard).
        """
        db, session = _make_db_mock()

        session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        session.get.return_value = None

        result = self._run(db, owner_uid=1, pref_name="UNKNOWN_PREF")
        assert result is None

    def test_profile_int_applies_profile_filter(self):
        """
        When profile=5 is passed, the query must include AND profile = 5.

        Source: ttrss/include/db-prefs.php:get_pref — AND profile = :profile
        """
        db, session = _make_db_mock()

        user_row = MagicMock()
        user_row.value = "compact"
        filter_chain = session.query.return_value.filter.return_value.filter.return_value
        filter_chain.first.return_value = user_row

        result = self._run(db, owner_uid=2, pref_name="LAYOUT", profile=5)
        assert result == "compact"
        # Verify that a second .filter() was called (for the profile condition)
        assert session.query.return_value.filter.return_value.filter.call_count >= 1

    def test_profile_none_applies_is_null_filter(self):
        """
        When profile=None (default), the query must include AND profile IS NULL.

        Source: ttrss/include/db-prefs.php:get_pref — AND profile IS NULL
                (default profile filter)
        """
        db, session = _make_db_mock()

        user_row = MagicMock()
        user_row.value = "en_US"
        filter_chain = session.query.return_value.filter.return_value.filter.return_value
        filter_chain.first.return_value = user_row

        result = self._run(db, owner_uid=3, pref_name="LANGUAGE", profile=None)
        assert result == "en_US"
        # profile=None branch calls .filter(TtRssUserPref.profile.is_(None))
        # Confirm the second filter was applied
        assert session.query.return_value.filter.return_value.filter.called


# ---------------------------------------------------------------------------
# set_user_pref
# ---------------------------------------------------------------------------


class TestSetUserPref:
    """Source: ttrss/include/db-prefs.php:set_pref (full function)"""

    def test_merge_and_commit_called(self):
        """
        set_user_pref must call session.merge(row) then session.commit().

        Source: ttrss/include/db-prefs.php:set_pref — INSERT … ON CONFLICT DO UPDATE
        Adapted: PHP uses raw SQL upsert; Python uses session.merge() for upsert
                 semantics, followed by explicit commit (no PHP equivalent).
        """
        db, session = _make_db_mock()

        with patch("ttrss.prefs.ops.db", db):
            from ttrss.prefs.ops import set_user_pref
            set_user_pref(owner_uid=7, pref_name="HIDE_READ_FEEDS", value="true")

        session.merge.assert_called_once()
        session.commit.assert_called_once()

        # Verify the merged object has expected attributes
        merged_obj = session.merge.call_args[0][0]
        assert merged_obj.owner_uid == 7
        assert merged_obj.pref_name == "HIDE_READ_FEEDS"
        assert merged_obj.value == "true"


# ---------------------------------------------------------------------------
# initialize_user_prefs
# ---------------------------------------------------------------------------


class TestInitializeUserPrefs:
    """Source: ttrss/include/db-prefs.php:initialize_user_prefs (full function)
              ttrss/include/functions.php:initialize_user_prefs (lines 639-723)
    """

    def test_merge_called_per_system_pref_then_commit(self):
        """
        initialize_user_prefs must call session.merge() once per system pref row,
        then call session.commit() exactly once.

        Source: ttrss/include/db-prefs.php:initialize_user_prefs —
                INSERT … ON CONFLICT DO NOTHING (one row per system pref).
        Adapted: Python iterates system prefs and calls session.merge per row
                 rather than a bulk SQL statement.
        """
        db, session = _make_db_mock()

        # Two system prefs returned by SELECT * FROM ttrss_prefs
        pref_a = MagicMock()
        pref_a.pref_name = "HIDE_READ_FEEDS"
        pref_a.def_value = "false"
        pref_b = MagicMock()
        pref_b.pref_name = "THEME"
        pref_b.def_value = "default"
        session.query.return_value.all.return_value = [pref_a, pref_b]

        with patch("ttrss.prefs.ops.db", db):
            from ttrss.prefs.ops import initialize_user_prefs
            initialize_user_prefs(owner_uid=42)

        # One merge call per system pref
        assert session.merge.call_count == 2
        # Exactly one commit after all merges
        session.commit.assert_called_once()

        # Verify merged objects carry the correct owner_uid and pref values
        merged_calls = [c[0][0] for c in session.merge.call_args_list]
        pref_names = {obj.pref_name for obj in merged_calls}
        assert pref_names == {"HIDE_READ_FEEDS", "THEME"}
        for obj in merged_calls:
            assert obj.owner_uid == 42
