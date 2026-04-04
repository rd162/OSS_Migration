"""
Miscellaneous utility functions — datetime conversion, random bytes, email helpers.

Source: ttrss/include/functions.php:convert_timestamp (lines 891-907)
        ttrss/include/functions.php:make_local_datetime (lines 909-953)
        ttrss/include/functions.php:smart_date_time (lines 955-967)
        ttrss/include/functions2.php:get_random_bytes (lines 2174-2185)
        ttrss/include/functions2.php:save_email_address (lines 1752-1760)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from flask import session


def convert_timestamp(timestamp: float, source_tz: str, dest_tz: str) -> float:
    """
    Convert Unix timestamp from source_tz to dest_tz, returning a "fake local" Unix
    timestamp: UTC epoch + destination timezone's UTC offset in seconds.

    Source: ttrss/include/functions.php:convert_timestamp (lines 891-907)
    Adapted: PHP DateTimeZone/DateTime replaced by zoneinfo.ZoneInfo; invalid TZ
             falls back to UTC as in PHP catch (Exception $e) { ... = UTC }.
    """
    # NOTE: PHP line 906 returns $dt->format('U') + $dest_tz->getOffset($dt).
    # $dt->format('U') is the UTC epoch; getOffset($dt) is the destination timezone's
    # offset in seconds at that moment (including DST).  The result is NOT a standard
    # UTC timestamp — it is a "fake local" value equal to the UTC epoch plus the
    # destination offset.  Python's datetime.timestamp() returns a pure UTC epoch and
    # therefore produces a different numeric value.  This function replicates the PHP
    # arithmetic explicitly to match return semantics.
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        src = ZoneInfo(source_tz)
    except (ZoneInfoNotFoundError, KeyError):
        # Source: ttrss/include/functions.php line 896 — catch (Exception $e) { $source_tz = UTC }
        src = timezone.utc
    try:
        dst = ZoneInfo(dest_tz)
    except (ZoneInfoNotFoundError, KeyError):
        # Source: ttrss/include/functions.php line 902 — catch (Exception $e) { $dest_tz = UTC }
        dst = timezone.utc

    # Source: ttrss/include/functions.php line 905 — new DateTime(date('Y-m-d H:i:s', $timestamp), $source_tz)
    dt = datetime.fromtimestamp(timestamp, tz=src)

    # Source: ttrss/include/functions.php line 906 — $dt->format('U') + $dest_tz->getOffset($dt)
    # utc_epoch   = $dt->format('U')        — pure UTC epoch of the moment
    # dest_offset = $dest_tz->getOffset($dt) — dest TZ offset in seconds (incl. DST)
    # Return value is their sum: a "fake local" epoch, not a standard UTC timestamp.
    utc_epoch = dt.timestamp()
    dest_offset = dt.astimezone(dst).utcoffset().total_seconds()
    return utc_epoch + dest_offset


def smart_date_time(
    timestamp: float,
    tz_offset: int = 0,
    owner_uid: Optional[int] = None,
) -> str:
    """
    Return human-friendly date string:
      - same day  → "H:MM" (24-hour, no leading zero)
      - same year → SHORT_DATE_FORMAT preference
      - other     → LONG_DATE_FORMAT preference

    Source: ttrss/include/functions.php:smart_date_time (lines 955-967)
    Adapted: PHP date() replaced by datetime.strftime(); preference fallbacks used when
             prefs.ops is unavailable (e.g., during a worker without DB context).
    """
    # Source: ttrss/include/functions.php line 956 — if (!$owner_uid) $owner_uid = $_SESSION['uid']
    if owner_uid is None:
        owner_uid = session.get("uid") if session else None

    # PHP compares date("Y.m.d", $timestamp) with date("Y.m.d", time() + $tz_offset).
    # $timestamp is already the adjusted local Unix timestamp; now() comparison also
    # uses $tz_offset to normalise "current local date".
    # Source: ttrss/include/functions.php lines 958-966
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    now_adj = datetime.fromtimestamp(
        datetime.now(tz=timezone.utc).timestamp() + tz_offset, tz=timezone.utc
    )

    if dt.date() == now_adj.date():
        # Source: ttrss/include/functions.php line 959 — date("G:i", $timestamp): 24h, no leading zero
        return f"{dt.hour}:{dt.strftime('%M')}"

    if dt.year == now_adj.year:
        # Source: ttrss/include/functions.php line 961 — get_pref('SHORT_DATE_FORMAT', $owner_uid)
        fmt = _pref(owner_uid, "SHORT_DATE_FORMAT", "%d %b")
        return dt.strftime(fmt or "%d %b")

    # Source: ttrss/include/functions.php line 964 — get_pref('LONG_DATE_FORMAT', $owner_uid)
    fmt = _pref(owner_uid, "LONG_DATE_FORMAT", "%d %b %Y")
    return dt.strftime(fmt or "%d %b %Y")


def make_local_datetime(
    timestamp: Optional[str],
    long: bool,
    owner_uid: Optional[int] = None,
    no_smart_dt: bool = False,
) -> str:
    """
    Convert stored UTC timestamp string to localised display string.

    Source: ttrss/include/functions.php:make_local_datetime (lines 909-953)
    Adapted: PHP DateTimeZone/DateTime/getOffset replaced by zoneinfo; $_SESSION["uid"]
             fallback replaced by flask.session.get("uid").
    """
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    # Source: ttrss/include/functions.php line 912 — if (!$owner_uid) $owner_uid = $_SESSION['uid']
    if owner_uid is None:
        owner_uid = session.get("uid") if session else None

    # Source: ttrss/include/functions.php line 913 — if (!$timestamp) $timestamp = '1970-01-01 0:00'
    if not timestamp:
        timestamp = "1970-01-01 00:00:00"

    # Source: ttrss/include/functions.php line 920 — $timestamp = substr($timestamp, 0, 19)
    timestamp = str(timestamp)[:19]

    # Source: ttrss/include/functions.php line 923 — new DateTime($timestamp, $utc_tz): stored as UTC
    try:
        dt = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
    except ValueError:  # New: PHP has no try/except here; epoch fallback guards against malformed strings that survive the substr() truncation.
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc)

    # Source: ttrss/include/functions.php line 925 — get_pref('USER_TIMEZONE', $owner_uid)
    tz_offset = 0
    tz_str = _pref(owner_uid, "USER_TIMEZONE", "UTC")
    if tz_str and tz_str != "Automatic":  # Source: ttrss/include/functions.php line 927 — if ($user_tz_string != 'Automatic'). Adapted: Python also guards falsy tz_str since _pref() can return None when DB unavailable.
        # Source: ttrss/include/functions.php lines 929-935 — try { $user_tz = new DateTimeZone($user_tz_string) }
        #         catch (Exception $e) { $user_tz = $utc_tz }
        # Exception path leaves tz_offset = 0, matching PHP UTC fallback (UTC offset = 0).
        # Adapted: PHP caches $user_tz as a global across calls (line 930: if (!$user_tz)).
        #          Python creates a new ZoneInfo on every call; ZoneInfo is lightweight and
        #          the global-cache optimisation is not reproduced.
        try:
            user_tz = ZoneInfo(tz_str)
            dt_local = dt.astimezone(user_tz)
            tz_offset = int(dt_local.utcoffset().total_seconds())
        except (ZoneInfoNotFoundError, KeyError, AttributeError):  # Source: ttrss/include/functions.php line 933 — catch (Exception $e) { $user_tz = $utc_tz }
            tz_offset = 0  # Adapted: PHP line 935 computes offset via $user_tz->getOffset($dt) on UTC TZ (= 0); Python sets 0 directly, skipping the getOffset call.
    else:
        # Source: ttrss/include/functions.php lines 936-938 — "Automatic" branch reads
        # $tz_offset = (int) -$_SESSION["clientTzOffset"].
        # Client-supplied timezone offset is not yet plumbed through the API layer;
        # tz_offset remains 0 as a safe UTC default.
        tz_offset = 0  # New: diverges from PHP line 937 ($tz_offset = (int) -$_SESSION["clientTzOffset"]); client TZ offset not yet available in API layer.

    # Source: ttrss/include/functions.php line 940 — $user_timestamp = $dt->format('U') + $tz_offset
    user_timestamp = dt.timestamp() + tz_offset

    if not no_smart_dt:
        # Source: ttrss/include/functions.php lines 942-944 — smart_date_time($user_timestamp, $tz_offset)
        return smart_date_time(user_timestamp, tz_offset, owner_uid)

    # Source: ttrss/include/functions.php lines 946-951 — direct strftime with long/short format pref
    if long:
        fmt = _pref(owner_uid, "LONG_DATE_FORMAT", "%d %b %Y")
    else:
        fmt = _pref(owner_uid, "SHORT_DATE_FORMAT", "%d %b")
    return datetime.fromtimestamp(user_timestamp, tz=timezone.utc).strftime(
        fmt or ("%d %b %Y" if long else "%d %b")
    )


def get_random_bytes(length: int) -> bytes:
    """
    Return cryptographically random bytes of the requested length.

    Source: ttrss/include/functions2.php:get_random_bytes (lines 2174-2185)
    Adapted: openssl_random_pseudo_bytes() replaced by os.urandom() — both use the
             OS CSPRNG; the PHP fallback (mt_rand loop) is not reproduced (insecure).
    """
    return os.urandom(length)


def save_email_address(email: str) -> None:
    """
    Persist email address in the Flask session for later reuse (e.g., digest sending).

    Source: ttrss/include/functions2.php:save_email_address (lines 1752-1760)
    Adapted: PHP $_SESSION['stored_emails'] replaced by Flask session dict.
    Note: ttrss/include/functions2.php line 1753 — // FIXME: implement persistent storage
          of emails.  This limitation applies equally here; storage is session-only.
    """
    # Source: ttrss/include/functions2.php line 1755 — if (!$_SESSION['stored_emails']) init array
    stored: list[str] = session.get("stored_emails", [])
    if email not in stored:  # Source: ttrss/include/functions2.php line 1758 — if (!in_array($email, ...))
        stored.append(email)
        session["stored_emails"] = stored
        session.modified = True  # New: no PHP equivalent — Flask requires explicit session.modified = True when mutating a mutable value retrieved from the session dict.


# ---------------------------------------------------------------------------
# Internal helper — lazy preference read (avoids circular import with prefs.ops)
# ---------------------------------------------------------------------------

def _pref(owner_uid: Optional[int], pref_name: str, default: str) -> str:
    """
    Read a user preference; return *default* if prefs.ops is unavailable.

    New: no PHP equivalent — lazy import pattern prevents circular imports
         (prefs.ops depends on models defined after this module is first imported).
    """
    if owner_uid is None:  # New: no PHP equivalent — PHP always has owner_uid available; Python guards against None from callers without session.
        return default
    try:
        from ttrss.prefs.ops import get_user_pref
        value = get_user_pref(owner_uid, pref_name)
        return value if value is not None else default
    except Exception:  # New: no PHP equivalent — defensive catch prevents prefs import errors (circular import, DB unavailable) from propagating to callers.
        return default
