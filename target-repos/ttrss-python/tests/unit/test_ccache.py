"""Unit tests for ttrss/ccache.py — counter cache management.

Tests use MagicMock session so no real DB is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.ccache import (
    _count_feed_articles,
    ccache_find,
    ccache_remove,
    ccache_update,
    ccache_zero_all,
)
from ttrss.utils.feeds import LABEL_BASE_INDEX


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute(scalar_value=None, scalar_one_or_none_value=None, scalars_all=None):
    """Build a mock session.execute() return value."""
    result = MagicMock()
    result.scalar.return_value = scalar_value
    result.scalar_one_or_none.return_value = scalar_one_or_none_value
    result.scalars.return_value.all.return_value = scalars_all or []
    return result


def _sequential_session(*returns):
    """Build a mock session whose execute() yields each element of returns in sequence.

    Each element should be a dict with keys: scalar, scalar_one_or_none, scalars_all.
    """
    session = MagicMock()
    results = []
    for r in returns:
        results.append(
            _make_execute(
                scalar_value=r.get("scalar"),
                scalar_one_or_none_value=r.get("scalar_one_or_none"),
                scalars_all=r.get("scalars_all"),
            )
        )
    session.execute.side_effect = results
    return session


# ---------------------------------------------------------------------------
# ccache_zero_all
# ---------------------------------------------------------------------------


def test_ccache_zero_all_executes_two_updates():
    """Must UPDATE both ttrss_counters_cache and ttrss_cat_counters_cache."""
    session = MagicMock()
    ccache_zero_all(session, owner_uid=1)
    assert session.execute.call_count == 2


# ---------------------------------------------------------------------------
# ccache_remove
# ---------------------------------------------------------------------------


def test_ccache_remove_feed_executes_delete():
    session = MagicMock()
    ccache_remove(session, feed_id=5, owner_uid=1, is_cat=False)
    session.execute.assert_called_once()


def test_ccache_remove_cat_executes_delete():
    session = MagicMock()
    ccache_remove(session, feed_id=3, owner_uid=1, is_cat=True)
    session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# ccache_find
# ---------------------------------------------------------------------------


def test_ccache_find_returns_cached_value():
    """Cache hit: returns the stored value without calling ccache_update."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 42
    result = ccache_find(session, feed_id=1, owner_uid=1)
    assert result == 42


def test_ccache_find_cache_miss_no_update_returns_minus_one():
    """Cache miss with no_update=True must return -1."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    result = ccache_find(session, feed_id=1, owner_uid=1, no_update=True)
    assert result == -1


def test_ccache_find_zero_value_is_cache_hit():
    """Cached value of 0 must be returned, not trigger a cache miss (R12 TTL dead code)."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 0
    result = ccache_find(session, feed_id=1, owner_uid=1)
    assert result == 0


def test_ccache_find_no_time_filter_in_select():
    """ccache_find must NOT filter the SELECT by 'updated' column (R12 dead code exclusion).

    Verified structurally: the ccache_find implementation queries only owner_uid + feed_id.
    Behaviorally confirmed by test_ccache_find_zero_value_is_cache_hit:
    a stale 0-value entry is returned without triggering a time-based cache miss.
    """
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 0
    result = ccache_find(session, feed_id=7, owner_uid=2)
    # Verify only one execute (the SELECT) — no second execute for TTL re-check
    assert session.execute.call_count == 1
    assert result == 0


# ---------------------------------------------------------------------------
# _count_feed_articles — virtual feed routing
# ---------------------------------------------------------------------------


def test_count_recently_read_returns_zero_without_db():
    """feed_id == -6 (Recently Read) must return 0 without querying DB."""
    session = MagicMock()
    result = _count_feed_articles(session, -6, owner_uid=1)
    assert result == 0
    session.execute.assert_not_called()


def test_count_starred_feed():
    """feed_id == -1 (Starred/marked) returns DB count."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 7
    result = _count_feed_articles(session, -1, owner_uid=1)
    assert result == 7


def test_count_published_feed():
    """feed_id == -2 (Published) returns DB count."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 3
    result = _count_feed_articles(session, -2, owner_uid=1)
    assert result == 3


def test_count_fresh_feed_reads_pref():
    """feed_id == -3 (Fresh) reads FRESH_ARTICLE_MAX_AGE preference."""
    # Call 1: TtRssUserPref lookup → None (no user override)
    # Call 2: TtRssPref default lookup → "12"
    # Call 3: COUNT query → 5
    session = _sequential_session(
        {"scalar_one_or_none": None},   # user pref miss
        {"scalar_one_or_none": "12"},   # system default
        {"scalar": 5},                  # count result
    )
    result = _count_feed_articles(session, -3, owner_uid=1)
    assert result == 5


def test_count_fresh_feed_uses_default_when_pref_missing():
    """feed_id == -3: falls back to 12h default when pref is absent."""
    session = _sequential_session(
        {"scalar_one_or_none": None},   # no user pref
        {"scalar_one_or_none": None},   # no system default
        {"scalar": 2},
    )
    result = _count_feed_articles(session, -3, owner_uid=1)
    assert result == 2


def test_count_all_articles_feed():
    """feed_id == -4 (All articles) returns unread count."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 100
    result = _count_feed_articles(session, -4, owner_uid=1)
    assert result == 100


def test_count_regular_feed():
    """feed_id > 0 (regular feed) returns DB count."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 15
    result = _count_feed_articles(session, 42, owner_uid=1)
    assert result == 15


def test_count_label_feed_below_base_index():
    """feed_id < LABEL_BASE_INDEX routes to label join query (always unread)."""
    label_virtual_id = LABEL_BASE_INDEX - 1  # == -1025
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 4
    result = _count_feed_articles(session, label_virtual_id, owner_uid=1)
    assert result == 4
    session.execute.assert_called_once()


def test_count_tag_feed_string():
    """String feed_id routes to tag join query."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 9
    result = _count_feed_articles(session, "linux", owner_uid=1)
    assert result == 9


def test_count_unhandled_range_returns_zero():
    """Plugin/unhandled feed IDs (e.g. -7 to -127) return 0 without DB call."""
    session = MagicMock()
    result = _count_feed_articles(session, -7, owner_uid=1)
    assert result == 0
    # No DB query expected for unhandled range
    session.execute.assert_not_called()


def test_count_none_result_coerces_to_zero():
    """DB returning None (e.g. empty table) is coerced to 0."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = None
    result = _count_feed_articles(session, 1, owner_uid=1)
    assert result == 0


# ---------------------------------------------------------------------------
# ccache_update — high-level smoke tests
# ---------------------------------------------------------------------------


def test_ccache_update_label_feed_delegates_to_update_all():
    """Negative feed_id triggers ccache_update_all and returns 0."""
    with patch("ttrss.ccache.ccache_update_all") as mock_all:
        with patch("ttrss.ccache.ccache_find", return_value=-1):
            session = MagicMock()
            result = ccache_update(session, feed_id=-1, owner_uid=1)
    mock_all.assert_called_once_with(session, 1)
    assert result == 0


def test_ccache_find_cache_miss_triggers_update():
    """Cache miss with no_update=False calls ccache_update (not no_update=True)."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None  # cache miss
    with patch("ttrss.ccache.ccache_update", return_value=8) as mock_update:
        result = ccache_find(session, feed_id=1, owner_uid=1, no_update=False)
    mock_update.assert_called_once_with(session, 1, 1, False)
    assert result == 8


def test_pref_int_invalid_returns_default():
    """_pref_int with non-numeric pref value returns the default."""
    from ttrss.ccache import _pref_int
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "not-a-number"
    result = _pref_int(session, "SOME_PREF", owner_uid=1, default=42)
    assert result == 42


def test_pref_bool_true():
    """_pref_bool returns True when pref value is 'true' (case insensitive)."""
    from ttrss.ccache import _pref_bool
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "true"
    assert _pref_bool(session, "ENABLE_FEED_CATS", owner_uid=1) is True


def test_pref_bool_false():
    """_pref_bool returns False when pref value is 'false'."""
    from ttrss.ccache import _pref_bool
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "false"
    assert _pref_bool(session, "ENABLE_FEED_CATS", owner_uid=1) is False


def test_ccache_update_all_non_cat_mode_no_feeds():
    """ccache_update_all in non-cat mode with no feeds: 2 executes (GROUP BY + zero-out UPDATE).

    Zero-out UPDATE ensures cached feeds with now-zero unread are set to 0 (C7 fix).
    """
    with patch("ttrss.ccache._pref_bool", return_value=False):
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        from ttrss.ccache import ccache_update_all
        ccache_update_all(session, owner_uid=1)
    # 1 GROUP BY + 1 zero-out UPDATE
    assert session.execute.call_count == 2


def test_ccache_update_all_non_cat_mode_with_feeds():
    """ccache_update_all in non-cat mode: GROUP BY + zero-out UPDATE + bulk UPSERT."""
    feed_row = MagicMock()
    feed_row.feed_id = 5
    feed_row.value = 3

    with patch("ttrss.ccache._pref_bool", return_value=False):
        session = MagicMock()
        call_results = iter([
            MagicMock(**{"all.return_value": [feed_row]}),  # GROUP BY
            MagicMock(),                                     # zero-out UPDATE
            MagicMock(),                                     # bulk UPSERT
        ])
        session.execute.side_effect = lambda *a, **kw: next(call_results)
        from ttrss.ccache import ccache_update_all
        ccache_update_all(session, owner_uid=1)
    assert session.execute.call_count == 3


def test_ccache_update_all_cat_mode_with_feeds():
    """ccache_update_all in cat mode: GROUP BY + zero-out + UPSERT feeds + cat GROUP BY + UPSERT cat."""
    feed_row = MagicMock()
    feed_row.feed_id = 5
    feed_row.value = 3

    cat_row = MagicMock()
    cat_row.cat_id = 1
    cat_row.value = 3

    with patch("ttrss.ccache._pref_bool", return_value=True):
        session = MagicMock()
        call_results = iter([
            MagicMock(**{"all.return_value": [feed_row]}),  # feed GROUP BY
            MagicMock(),                                     # zero-out UPDATE
            MagicMock(),                                     # feed UPSERT
            MagicMock(**{"all.return_value": [cat_row]}),   # cat GROUP BY
            MagicMock(),                                     # cat UPSERT
        ])
        session.execute.side_effect = lambda *a, **kw: next(call_results)
        from ttrss.ccache import ccache_update_all
        ccache_update_all(session, owner_uid=1)
    assert session.execute.call_count == 5


def test_ccache_update_category_branch_pcat_fast():
    """ccache_update with is_cat=True, pcat_fast=True: skips child loop, SUMs, UPSERTs."""
    from ttrss.ccache import ccache_update as cu
    with patch("ttrss.ccache.ccache_find", return_value=7):  # prev==new → no cascade
        session = MagicMock()
        call_results = iter([
            MagicMock(**{"scalar.return_value": 7}),  # SUM query
            MagicMock(),                               # UPSERT
        ])
        session.execute.side_effect = lambda *a, **kw: next(call_results)
        result = cu(session, feed_id=2, owner_uid=1, is_cat=True, pcat_fast=True)
    assert result == 7


def test_ccache_update_regular_feed_upserts():
    """ccache_update for a regular feed calls _count_feed_articles and executes UPSERT.

    prev_unread is patched to match the new count so parent-category cascade is skipped.
    """
    with patch("ttrss.ccache.ccache_find", return_value=3):  # prev == new → no parent update
        with patch("ttrss.ccache._count_feed_articles", return_value=3):
            session = MagicMock()
            result = ccache_update(session, feed_id=5, owner_uid=1)
    # One execute for the UPSERT; parent cascade skipped because count unchanged
    assert result == 3
