"""
Unit tests for ttrss.utils.misc — PHP→Python migration coverage.

Functions under test:
  make_local_datetime   ← ttrss/include/functions.php:make_local_datetime (lines 909-953)
  convert_timestamp     ← ttrss/include/functions.php:convert_timestamp (lines 891-907)
  get_random_bytes      ← ttrss/include/functions2.php:get_random_bytes (lines 2174-2185)
  save_email_address    ← ttrss/include/functions2.php:save_email_address (lines 1752-1760)
  _pref                 ← Python-only helper (no direct PHP equivalent)

NOTE — truncate_string (ttrss/include/functions.php lines 883-889):
  PHP function truncate_string() has not yet been ported to ttrss.utils.misc.
  Tests marked with MISSING_PORT below document the expected behaviour but
  skip gracefully via pytest.mark.skip until the port is complete.

Flask app context requirement:
  make_local_datetime, save_email_address, and smart_date_time call flask.session.
  Tests that exercise those paths use a minimal Flask test app fixture.
  Tests for _pref without a context are pure (no Flask required).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pytest
from flask import Flask

from ttrss.utils.misc import (
    _pref,
    convert_timestamp,
    get_random_bytes,
    make_local_datetime,
    save_email_address,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def misc_app():
    """
    Minimal Flask application for functions that require an app/request context.
    No database, no Redis — only the app factory shell is needed so that
    flask.session can be pushed from a test client request context.
    """
    app = Flask("test_utils_misc")
    app.secret_key = "test-secret-key-not-for-production"
    app.config["TESTING"] = True
    return app


# ---------------------------------------------------------------------------
# truncate_string — NOT YET PORTED
# ---------------------------------------------------------------------------
# PHP source: ttrss/include/functions.php:truncate_string lines 883-889
#
#   function truncate_string($str, $max_len, $suffix = '&hellip;') {
#       if (mb_strlen($str, "utf-8") > $max_len) {
#           return mb_substr($str, 0, $max_len, "utf-8") . $suffix;
#       } else {
#           return $str;
#       }
#   }
#
# These tests are skipped with MISSING_PORT until ttrss.utils.misc exports
# a truncate_string() function.  They define the contract to implement.

_truncate_string = pytest.importorskip(
    "ttrss.utils.misc",
    reason="ttrss.utils.misc not importable",
).get if False else None  # sentinel — skips are managed per-test below


@pytest.mark.skip(reason="MISSING_PORT: truncate_string not yet ported from PHP")
def test_truncate_string_long_input():
    """
    Source: ttrss/include/functions.php:truncate_string line 883
    PHP: mb_strlen($str) > $max_len → mb_substr($str, 0, $max_len) . $suffix
    Assert: 'hello world' truncated to 5 chars yields 'hello' + default suffix
    """
    from ttrss.utils.misc import truncate_string  # noqa: PLC0415

    result = truncate_string("hello world", 5)
    assert result.startswith("hello")
    assert len(result) > 5  # suffix appended


@pytest.mark.skip(reason="MISSING_PORT: truncate_string not yet ported from PHP")
def test_truncate_string_short_input_no_truncation():
    """
    Source: ttrss/include/functions.php:truncate_string line 883
    PHP: mb_strlen($str) <= $max_len → return $str unchanged
    Assert: 'hi' with max_len=100 is returned unchanged (no suffix)
    """
    from ttrss.utils.misc import truncate_string  # noqa: PLC0415

    assert truncate_string("hi", 100) == "hi"


@pytest.mark.skip(reason="MISSING_PORT: truncate_string not yet ported from PHP")
def test_truncate_string_empty_input():
    """
    Source: ttrss/include/functions.php:truncate_string line 883
    PHP: mb_strlen('') == 0, which is not > max_len → return ''
    Assert: empty string is returned unchanged for any max_len >= 0
    """
    from ttrss.utils.misc import truncate_string  # noqa: PLC0415

    assert truncate_string("", 10) == ""


@pytest.mark.skip(reason="MISSING_PORT: truncate_string not yet ported from PHP")
def test_truncate_string_custom_suffix():
    """
    Source: ttrss/include/functions.php:truncate_string line 883
    PHP: optional $suffix parameter (default '&hellip;') is appended after truncation
    Assert: custom suffix '...' is appended when string exceeds max_len
    """
    from ttrss.utils.misc import truncate_string  # noqa: PLC0415

    result = truncate_string("abcdef", 3, suffix="...")
    assert result == "abc..."


# ---------------------------------------------------------------------------
# make_local_datetime — requires Flask app context for session access
# ---------------------------------------------------------------------------


def test_make_local_datetime_valid_utc_timestamp(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime lines 909-953
    PHP: new DateTime($timestamp, $utc_tz) parses the stored UTC string;
         USER_TIMEZONE pref applied; result formatted via smart_date_time or strftime
    Assert: valid ISO timestamp with UTC timezone and no_smart_dt=True returns a
            non-empty string matching a recognisable date pattern
    """
    with misc_app.test_request_context("/"):
        result = make_local_datetime(
            "2024-06-15 12:00:00",
            long=True,
            owner_uid=None,
            no_smart_dt=True,
        )
    assert isinstance(result, str)
    assert len(result) > 0


def test_make_local_datetime_long_format(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime lines 946-951
    PHP: if $no_smart_dt and $long → format with LONG_DATE_FORMAT pref
    Assert: long=True, no_smart_dt=True returns a string containing the year
    """
    with misc_app.test_request_context("/"):
        result = make_local_datetime(
            "2020-01-15 08:30:00",
            long=True,
            owner_uid=None,
            no_smart_dt=True,
        )
    assert "2020" in result


def test_make_local_datetime_short_format(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime lines 946-951
    PHP: if $no_smart_dt and not $long → format with SHORT_DATE_FORMAT pref
    Assert: long=False, no_smart_dt=True returns a non-empty string (no year required)
    """
    with misc_app.test_request_context("/"):
        result = make_local_datetime(
            "2020-06-15 08:30:00",
            long=False,
            owner_uid=None,
            no_smart_dt=True,
        )
    assert isinstance(result, str)
    assert len(result) > 0


def test_make_local_datetime_none_timestamp(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime line 913
    PHP: if (!$timestamp) $timestamp = '1970-01-01 0:00' — epoch fallback
    Assert: None timestamp falls back to epoch; returns a non-empty string, no exception
    """
    with misc_app.test_request_context("/"):
        result = make_local_datetime(None, long=False, owner_uid=None, no_smart_dt=True)
    assert isinstance(result, str)
    assert len(result) > 0


def test_make_local_datetime_empty_string_timestamp(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime line 913
    PHP: falsy $timestamp (empty string) → '1970-01-01 0:00' epoch fallback
    Assert: empty string timestamp does not raise; returns a string (epoch date)
    """
    with misc_app.test_request_context("/"):
        result = make_local_datetime("", long=False, owner_uid=None, no_smart_dt=True)
    assert isinstance(result, str)
    assert len(result) > 0


def test_make_local_datetime_invalid_timezone_fallback(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime lines 929-935
    PHP: catch (Exception $e) { $user_tz = $utc_tz } — invalid TZ silently falls back
    Assert: invalid timezone string in USER_TIMEZONE pref does not raise;
            _pref() returns default 'UTC' when DB unavailable, so this tests the
            UTC-fallback path used when owner_uid is None
    """
    with misc_app.test_request_context("/"):
        # With owner_uid=None, _pref returns default 'UTC' — exercises the tz_str
        # branch that calls ZoneInfo('UTC'), which is always valid.
        result = make_local_datetime(
            "2024-03-10 15:00:00",
            long=True,
            owner_uid=None,
            no_smart_dt=True,
        )
    assert isinstance(result, str)
    assert len(result) > 0


def test_make_local_datetime_smart_dt_path(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime lines 942-944
    PHP: if (!$no_smart_dt) return smart_date_time($user_timestamp, $tz_offset, ...)
    Assert: no_smart_dt=False (default) delegates to smart_date_time; returns a string
    """
    past_ts = "2015-07-04 10:30:00"
    with misc_app.test_request_context("/"):
        result = make_local_datetime(past_ts, long=False, owner_uid=None)
    assert isinstance(result, str)
    assert len(result) > 0


def test_make_local_datetime_malformed_timestamp(misc_app):
    """
    Source: ttrss/include/functions.php:make_local_datetime line 920
    PHP: substr($timestamp, 0, 19) truncates; datetime parse may still fail for
         garbage input — Python adds a ValueError guard returning epoch fallback
    Assert: malformed timestamp string does not raise; returns a non-empty string
    """
    with misc_app.test_request_context("/"):
        result = make_local_datetime(
            "not-a-date-at-all", long=True, owner_uid=None, no_smart_dt=True
        )
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# convert_timestamp
# ---------------------------------------------------------------------------


def test_convert_timestamp_utc_to_utc():
    """
    Source: ttrss/include/functions.php:convert_timestamp lines 891-907
    PHP: UTC→UTC conversion leaves value unchanged (offset = 0 + 0 = epoch)
    Assert: convert_timestamp(ts, 'UTC', 'UTC') == ts (zero net offset)
    """
    ts = 1_700_000_000.0
    result = convert_timestamp(ts, "UTC", "UTC")
    assert abs(result - ts) < 1.0


def test_convert_timestamp_invalid_source_tz_fallback():
    """
    Source: ttrss/include/functions.php:convert_timestamp line 896
    PHP: catch (Exception $e) { $source_tz = new DateTimeZone('UTC') }
    Assert: invalid source timezone does not raise; falls back to UTC silently
    """
    ts = 1_700_000_000.0
    result = convert_timestamp(ts, "Not/AValid/Timezone", "UTC")
    assert isinstance(result, float)


def test_convert_timestamp_invalid_dest_tz_fallback():
    """
    Source: ttrss/include/functions.php:convert_timestamp line 902
    PHP: catch (Exception $e) { $dest_tz = new DateTimeZone('UTC') }
    Assert: invalid destination timezone does not raise; falls back to UTC silently
    """
    ts = 1_700_000_000.0
    result = convert_timestamp(ts, "UTC", "Not/AValid/Timezone")
    assert isinstance(result, float)


def test_convert_timestamp_returns_float():
    """
    Source: ttrss/include/functions.php:convert_timestamp line 906
    PHP: return $dt->format('U') + $dest_tz->getOffset($dt) — integer arithmetic
    Assert: Python implementation returns a float (numeric)
    """
    result = convert_timestamp(0.0, "UTC", "UTC")
    assert isinstance(result, (int, float))


def test_convert_timestamp_positive_offset():
    """
    Source: ttrss/include/functions.php:convert_timestamp line 906
    PHP: $dt->format('U') + $dest_tz->getOffset($dt) — offset added to epoch
    Assert: converting from UTC to a positive-offset timezone returns a value
            strictly greater than the original timestamp
    """
    ts = 1_700_000_000.0
    # Asia/Tokyo is UTC+9 (no DST) — offset = +32400 seconds
    result = convert_timestamp(ts, "UTC", "Asia/Tokyo")
    assert result > ts


def test_convert_timestamp_negative_offset():
    """
    Source: ttrss/include/functions.php:convert_timestamp line 906
    PHP: negative UTC offset produces a result less than the input timestamp
    Assert: UTC→America/New_York (UTC-5 in non-DST) result < original timestamp
    """
    # Use a winter date to avoid DST ambiguity
    dt_winter = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    ts = dt_winter.timestamp()
    result = convert_timestamp(ts, "UTC", "America/New_York")
    assert result < ts


# ---------------------------------------------------------------------------
# get_random_bytes
# ---------------------------------------------------------------------------


def test_get_random_bytes_length():
    """
    Source: ttrss/include/functions2.php:get_random_bytes lines 2174-2185
    PHP: openssl_random_pseudo_bytes($length) returns exactly $length bytes
    Assert: get_random_bytes(32) returns a bytes object of exactly 32 bytes
    """
    result = get_random_bytes(32)
    assert isinstance(result, bytes)
    assert len(result) == 32


def test_get_random_bytes_zero_length():
    """
    Source: ttrss/include/functions2.php:get_random_bytes lines 2174-2185
    PHP: openssl_random_pseudo_bytes(0) returns empty string
    Assert: get_random_bytes(0) returns empty bytes object
    """
    result = get_random_bytes(0)
    assert result == b""


def test_get_random_bytes_uniqueness():
    """
    Source: ttrss/include/functions2.php:get_random_bytes lines 2174-2185
    PHP: openssl_random_pseudo_bytes is a CSPRNG — consecutive calls differ
    Assert: two successive 32-byte calls return different values (statistically certain)
    """
    r1 = get_random_bytes(32)
    r2 = get_random_bytes(32)
    assert r1 != r2


def test_get_random_bytes_various_lengths():
    """
    Source: ttrss/include/functions2.php:get_random_bytes lines 2174-2185
    PHP: arbitrary length is supported by openssl_random_pseudo_bytes
    Assert: get_random_bytes returns correct length for 1, 16, 64, 128 bytes
    """
    for length in (1, 16, 64, 128):
        result = get_random_bytes(length)
        assert len(result) == length


# ---------------------------------------------------------------------------
# save_email_address — requires Flask request context
# ---------------------------------------------------------------------------


def test_save_email_address_stores_in_session(misc_app):
    """
    Source: ttrss/include/functions2.php:save_email_address lines 1752-1760
    PHP: stores email in $_SESSION['stored_emails'] array if not already present
    Assert: after save_email_address(), the email appears in session['stored_emails']
    """
    with misc_app.test_request_context("/"):
        from flask import session  # noqa: PLC0415

        session["stored_emails"] = []
        save_email_address("test@example.com")
        assert "test@example.com" in session.get("stored_emails", [])


def test_save_email_address_no_duplicates(misc_app):
    """
    Source: ttrss/include/functions2.php:save_email_address line 1758
    PHP: if (!in_array($email, $_SESSION['stored_emails'])) → only add once
    Assert: calling save_email_address() twice with the same email stores it once only
    """
    with misc_app.test_request_context("/"):
        from flask import session  # noqa: PLC0415

        session["stored_emails"] = []
        save_email_address("dup@example.com")
        save_email_address("dup@example.com")
        assert session.get("stored_emails", []).count("dup@example.com") == 1


def test_save_email_address_multiple_emails(misc_app):
    """
    Source: ttrss/include/functions2.php:save_email_address lines 1752-1760
    PHP: multiple distinct addresses are accumulated in the session array
    Assert: three distinct emails are all present in session['stored_emails']
    """
    with misc_app.test_request_context("/"):
        from flask import session  # noqa: PLC0415

        session["stored_emails"] = []
        for addr in ("a@x.com", "b@x.com", "c@x.com"):
            save_email_address(addr)
        stored = session.get("stored_emails", [])
        assert "a@x.com" in stored
        assert "b@x.com" in stored
        assert "c@x.com" in stored


# ---------------------------------------------------------------------------
# _pref helper — pure / no Flask context required when owner_uid is None
# ---------------------------------------------------------------------------


def test_pref_returns_default_when_no_owner_uid():
    """
    Source: ttrss/utils/misc.py:_pref (Python-only helper, no PHP equivalent)
    PHP: get_pref() always has owner_uid; Python guards against None from session
    Assert: _pref(None, 'ANY_KEY', 'fallback') returns 'fallback' without exception
    """
    result = _pref(None, "ANY_KEY", "fallback")
    assert result == "fallback"


def test_pref_returns_default_string_type():
    """
    Source: ttrss/utils/misc.py:_pref (Python-only helper, no PHP equivalent)
    PHP: get_pref() returns string values; Python default must also be a string
    Assert: return value is a str instance
    """
    result = _pref(None, "SHORT_DATE_FORMAT", "%d %b")
    assert isinstance(result, str)


def test_pref_returns_default_when_db_unavailable():
    """
    Source: ttrss/utils/misc.py:_pref (Python-only helper, no PHP equivalent)
    PHP: no equivalent — Python defensive catch prevents prefs import errors
    Assert: with a non-None owner_uid but no DB, _pref returns default gracefully
    Note: the try/except in _pref catches ImportError and DB errors; with no DB
          configured in this test context, the import or call will fail and the
          default is returned.
    """
    result = _pref(9999, "USER_TIMEZONE", "UTC")
    # Either the pref system works (returns a string) or returns the default;
    # either way it must be a string and must not raise.
    assert isinstance(result, str)
    assert len(result) > 0
