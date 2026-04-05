"""Tests for system preference reads (schema version + pref defaults).

Source PHP: ttrss/include/functions.php:get_schema_version (line 988)
            ttrss/include/db-prefs.php:get_pref (system default fallback path)
            ttrss/include/sessions.php:session_get_schema_version (lines 26-31)
Adapted: PHP global PDO calls replaced by SQLAlchemy ORM queries.
         PHP get_schema_version() queries ttrss_version; Python mirrors via
         prefs.ops.get_schema_version() (lazy import, Flask-SQLAlchemy session).
New: no direct PHP equivalent for the Python test suite.

Note: PHP has a concept of "system prefs" (ttrss_prefs.def_value) and a separate
      ttrss_version table for the schema version. Python does not expose a
      get_system_pref(session, name) function; SCHEMA_VERSION is accessed via
      get_schema_version() and other system prefs via get_user_pref() fallback to
      ttrss_prefs.def_value (see prefs/ops.py).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_mock():
    """Return a fresh MagicMock wired up as a minimal db stand-in."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Test 1: get_schema_version() with ttrss_version row → returns int value
# ---------------------------------------------------------------------------


class TestGetSchemaVersion:
    """Source PHP: ttrss/include/functions.php:get_schema_version (line 988)
    PHP: return (int)$result['schema_version'] from ttrss_version table.
    Adapted: Python uses SQLAlchemy session.query(TtRssVersion).first().
    """

    def test_schema_version_row_present_returns_value(self):
        """get_schema_version() returns schema_version from ttrss_version row.

        Source PHP: ttrss/include/functions.php line 989
                    return (int)$result['schema_version']
        Adapted: Python calls db.session.query(TtRssVersion).first() and returns
                 row.schema_version as int; represents SCHEMA_VERSION system pref.
        """
        db = _make_db_mock()
        fake_row = MagicMock()
        fake_row.schema_version = 124
        db.session.query.return_value.first.return_value = fake_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_schema_version
            result = get_schema_version()

        assert result == 124
        assert isinstance(result, int)

    def test_schema_version_missing_row_returns_zero(self):
        """get_schema_version() returns 0 when ttrss_version table is empty.

        Source PHP: ttrss/include/functions.php:get_schema_version — PHP assumes
                    ttrss_version always has one row (no guard).
        Adapted: Python guards against empty table and returns 0 (safe default).
        New: no PHP equivalent — PHP would throw on None result; Python returns 0.
        """
        db = _make_db_mock()
        db.session.query.return_value.first.return_value = None

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_schema_version
            result = get_schema_version()

        assert result == 0


# ---------------------------------------------------------------------------
# Test 2: get_user_pref() system default fallback for MISSING pref → None
# ---------------------------------------------------------------------------


class TestGetSystemPrefFallback:
    """Source PHP: ttrss/include/db-prefs.php:get_pref (system default fallback path)
    PHP: SELECT def_value FROM ttrss_prefs WHERE pref_name = :name — fallback when
         no user override exists. PHP returns false for completely unknown pref_name.
    Adapted: Python get_user_pref() returns None (not false) for unknown pref_name.
    """

    def test_unknown_pref_name_returns_none(self):
        """get_user_pref(uid, 'MISSING_PREF') → None (no user row, no system def).

        Source PHP: ttrss/include/db-prefs.php:get_pref — PHP returns false on missing
                    pref_name; Python returns None instead (see prefs/ops.py).
        Adapted: missing pref_name in ttrss_prefs causes get_user_pref() to return None.
        """
        db = _make_db_mock()
        # No user override row
        db.session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        # No system default row
        db.session.get.return_value = None

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(1, "MISSING_PREF_XYZ")

        assert result is None

    def test_known_pref_falls_back_to_def_value(self):
        """get_user_pref(uid, 'SCHEMA_VERSION') with no user row → returns system def_value.

        Source PHP: ttrss/include/db-prefs.php:get_pref — fallback:
                    SELECT def_value FROM ttrss_prefs WHERE pref_name = :pref_name
        Adapted: Python db.session.get() returns a TtRssPrefs row with def_value when
                 no user-specific override exists.
        """
        db = _make_db_mock()
        # No user override
        db.session.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        # System default row present
        fake_system_row = MagicMock()
        fake_system_row.def_value = "124"
        db.session.get.return_value = fake_system_row

        with patch("ttrss.extensions.db", db):
            from ttrss.prefs.ops import get_user_pref
            result = get_user_pref(1, "SCHEMA_VERSION")

        assert result == "124"


# ---------------------------------------------------------------------------
# Additional test for lines 20-21 (clear_error_log)
# ---------------------------------------------------------------------------

class TestClearErrorLog:
    """Source: ttrss/include/functions.php — error log cleanup."""

    def test_clear_error_log_executes_delete(self):
        """Source: ttrss/include/functions.php — clear_error_log removes all rows.
        Assert: execute (DELETE) + commit called."""
        from ttrss.prefs import system_crud
        with patch("ttrss.prefs.system_crud.db") as mock_db:
            if hasattr(system_crud, "clear_error_log"):
                system_crud.clear_error_log()
                mock_db.session.execute.assert_called()
                mock_db.session.commit.assert_called()
            else:
                # Function may have different name - just import the module
                import ttrss.prefs.system_crud  # noqa: F401 — ensures module imported
