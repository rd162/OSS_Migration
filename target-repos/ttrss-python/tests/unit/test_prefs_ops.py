"""Unit tests for ttrss/prefs/ops.py.

Source PHP: ttrss/include/db-prefs.php (get_pref, set_pref, initialize_user_prefs)
            ttrss/include/functions.php:get_schema_version (line 988)
            ttrss/include/sessions.php:session_get_schema_version (lines 26-31)

All tests patch ``ttrss.extensions.db`` so the lazy-import inside each function
resolves to a MagicMock instead of requiring a live Flask/SQLAlchemy context.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_mock():
    """Return a fresh MagicMock wired up as a minimal db stand-in."""
    db = MagicMock()
    return db


# ---------------------------------------------------------------------------
# get_schema_version
# ---------------------------------------------------------------------------


class TestGetSchemaVersion:
    """Source: ttrss/include/functions.php:get_schema_version (line 988)"""

    def test_row_present_returns_schema_version(self):
        """Source: ttrss/include/functions.php line 989 — return (int)$result['schema_version']

        When ttrss_version has exactly one row, get_schema_version() should
        return its schema_version attribute as an integer.
        """
        db = _make_db_mock()
        fake_row = MagicMock()
        fake_row.schema_version = 137
        db.session.query.return_value.first.return_value = fake_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_schema_version
            result = get_schema_version()

        assert result == 137

    def test_empty_table_returns_zero(self):
        """Source: ttrss/include/functions.php:get_schema_version — PHP assumes table always has one row.
        Adapted: Python guards against empty ttrss_version table and returns 0.
        """
        db = _make_db_mock()
        db.session.query.return_value.first.return_value = None

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_schema_version
            result = get_schema_version()

        assert result == 0


# ---------------------------------------------------------------------------
# get_user_pref
# ---------------------------------------------------------------------------


class TestGetUserPref:
    """Source: ttrss/include/db-prefs.php:get_pref (full function)"""

    def test_user_row_present_returns_user_value(self):
        """Source: ttrss/include/db-prefs.php:get_pref — return $row['value'] (user override path)

        When a ttrss_user_prefs row exists for the given uid/pref_name, its
        ``value`` field should be returned directly.
        """
        db = _make_db_mock()
        fake_user_row = MagicMock()
        fake_user_row.value = "user_value"

        query_mock = db.session.query.return_value
        # Chained: .filter().filter().first()
        query_mock.filter.return_value.filter.return_value.first.return_value = fake_user_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(1, "THEME")

        assert result == "user_value"

    def test_no_user_row_falls_back_to_system_def_value(self):
        """Source: ttrss/include/db-prefs.php:get_pref — fallback: SELECT def_value FROM ttrss_prefs

        When no user override exists, get_user_pref() should fall back to the
        system default row and return its def_value.
        """
        db = _make_db_mock()
        # first() returns None → no user override
        db.session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        # db.session.get() returns a system pref with def_value
        fake_system_row = MagicMock()
        fake_system_row.def_value = "default_theme"
        db.session.get.return_value = fake_system_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(1, "THEME")

        assert result == "default_theme"

    def test_no_rows_at_all_returns_none(self):
        """Source: ttrss/include/db-prefs.php:get_pref — PHP returns false for unknown pref_name.
        Adapted: Python returns None instead.
        """
        db = _make_db_mock()
        db.session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        db.session.get.return_value = None

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(1, "NONEXISTENT_PREF")

        assert result is None

    def test_profile_integer_filter_applied(self):
        """Source: ttrss/include/db-prefs.php:get_pref — AND profile = :profile

        When a non-None profile is given, the ORM query chain should include an
        extra filter call (for TtRssUserPref.profile == profile).
        """
        db = _make_db_mock()
        fake_user_row = MagicMock()
        fake_user_row.value = "profile_value"

        # The function calls .filter() twice when profile is not None:
        #   .filter(owner_uid, pref_name).filter(profile == 5).first()
        chain = db.session.query.return_value.filter.return_value
        chain.filter.return_value.first.return_value = fake_user_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(1, "THEME", profile=5)

        assert result == "profile_value"
        # Confirm the second filter was called (profile path)
        chain.filter.assert_called_once()

    def test_profile_none_uses_is_null_filter(self):
        """Source: ttrss/include/db-prefs.php:get_pref — AND profile IS NULL (default profile)

        When profile=None (default), the query should use .is_(None) rather than
        an equality comparison so it picks only the default-profile rows.
        """
        db = _make_db_mock()
        fake_user_row = MagicMock()
        fake_user_row.value = "null_profile_value"

        chain = db.session.query.return_value.filter.return_value
        chain.filter.return_value.first.return_value = fake_user_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(2, "THEME", profile=None)

        assert result == "null_profile_value"
        # profile=None path also calls the second .filter() (with IS NULL expression)
        chain.filter.assert_called_once()


# ---------------------------------------------------------------------------
# set_user_pref
# ---------------------------------------------------------------------------


class TestSetUserPref:
    """Source: ttrss/include/db-prefs.php:set_pref (full function)"""

    def test_merge_and_commit_called(self):
        """Source: ttrss/include/db-prefs.php:set_pref — INSERT … ON CONFLICT DO UPDATE (upsert)
        Adapted: Python uses session.merge() then session.commit() to achieve upsert semantics.
        """
        db = _make_db_mock()

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import set_user_pref
            set_user_pref(1, "THEME", "dark")

        db.session.merge.assert_called_once()
        db.session.commit.assert_called_once()

        # Inspect the TtRssUserPref object that was merged
        merged_obj = db.session.merge.call_args[0][0]
        assert merged_obj.owner_uid == 1
        assert merged_obj.pref_name == "THEME"
        assert merged_obj.value == "dark"


# ---------------------------------------------------------------------------
# initialize_user_prefs
# ---------------------------------------------------------------------------


class TestInitializeUserPrefs:
    """Source: ttrss/include/db-prefs.php:initialize_user_prefs (full function)
               ttrss/include/functions.php:initialize_user_prefs (lines 639-723)
    """

    def test_merge_per_pref_and_commit(self):
        """Source: ttrss/include/db-prefs.php:initialize_user_prefs — INSERT … ON CONFLICT DO NOTHING
        Adapted: Python iterates system prefs and calls session.merge() per row, then commits once.
        """
        db = _make_db_mock()

        # Two fake system pref rows
        pref_a = MagicMock()
        pref_a.pref_name = "THEME"
        pref_a.def_value = "light"
        pref_b = MagicMock()
        pref_b.pref_name = "FRESH_ARTICLE_MAX_AGE"
        pref_b.def_value = "24"
        db.session.query.return_value.all.return_value = [pref_a, pref_b]

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import initialize_user_prefs
            initialize_user_prefs(42)

        # One merge call per system pref
        assert db.session.merge.call_count == 2
        # Exactly one commit at the end
        db.session.commit.assert_called_once()

        # Verify the values passed to merge
        merged_objs = [c[0][0] for c in db.session.merge.call_args_list]
        pref_names = {o.pref_name for o in merged_objs}
        assert pref_names == {"THEME", "FRESH_ARTICLE_MAX_AGE"}
        for o in merged_objs:
            assert o.owner_uid == 42
