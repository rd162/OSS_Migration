"""Unit tests for ttrss/feeds/counters.py — counter aggregation functions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ttrss.feeds.counters import (
    getAllCounters,
    getCategoryChildrenUnread,
    getCategoryCounters,
    getCategoryUnread,
    getFeedArticles,
    getFeedCounters,
    getGlobalCounters,
    getGlobalUnread,
    getLabelCounters,
    getVirtCounters,
)
from ttrss.utils.feeds import LABEL_BASE_INDEX, label_to_feed_id


# ---------------------------------------------------------------------------
# getGlobalUnread
# ---------------------------------------------------------------------------


def test_getGlobalUnread_returns_sum():
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 42
    assert getGlobalUnread(session, owner_uid=1) == 42


def test_getGlobalUnread_none_returns_zero():
    session = MagicMock()
    session.execute.return_value.scalar.return_value = None
    assert getGlobalUnread(session, owner_uid=1) == 0


# ---------------------------------------------------------------------------
# getGlobalCounters
# ---------------------------------------------------------------------------


def test_getGlobalCounters_structure():
    session = MagicMock()
    # First call: global unread SUM
    # Second call: subscribed feeds COUNT
    session.execute.side_effect = [
        MagicMock(**{"scalar.return_value": 10}),
        MagicMock(**{"scalar.return_value": 5}),
    ]
    result = getGlobalCounters(session, owner_uid=1)
    assert len(result) == 2
    assert result[0] == {"id": "global-unread", "counter": 10}
    assert result[1] == {"id": "subscribed-feeds", "counter": 5}


def test_getGlobalCounters_handles_none_subscribed():
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"scalar.return_value": 0}),
        MagicMock(**{"scalar.return_value": None}),
    ]
    result = getGlobalCounters(session, owner_uid=1)
    assert result[1]["counter"] == 0


# ---------------------------------------------------------------------------
# getCategoryUnread
# ---------------------------------------------------------------------------


def test_getCategoryUnread_positive_cat():
    """cat >= 1: counts unread via feed_subq IN."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 7
    result = getCategoryUnread(session, cat_id=3, owner_uid=1)
    assert result == 7


def test_getCategoryUnread_uncategorized_cat_zero():
    """cat_id=0: feeds with cat_id IS NULL."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 3
    result = getCategoryUnread(session, cat_id=0, owner_uid=1)
    assert result == 3


def test_getCategoryUnread_special_cat_minus_one():
    """cat_id=-1: sum of feeds -1, -2, -3, 0."""
    session = MagicMock()
    # 4 calls (one per virtual feed)
    session.execute.return_value.scalar.return_value = 2
    result = getCategoryUnread(session, cat_id=-1, owner_uid=1)
    assert result == 8  # 4 feeds × 2 each


def test_getCategoryUnread_labels_cat_minus_two():
    """cat_id=-2: entries with any label."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 5
    result = getCategoryUnread(session, cat_id=-2, owner_uid=1)
    assert result == 5


def test_getCategoryUnread_none_result_coerces():
    session = MagicMock()
    session.execute.return_value.scalar.return_value = None
    result = getCategoryUnread(session, cat_id=5, owner_uid=1)
    assert result == 0


def test_getCategoryUnread_unknown_cat_returns_zero():
    """cat_id < -2 or other negatives → 0."""
    session = MagicMock()
    result = getCategoryUnread(session, cat_id=-99, owner_uid=1)
    assert result == 0
    session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# getCategoryChildrenUnread
# ---------------------------------------------------------------------------


def test_getCategoryChildrenUnread_no_children():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    result = getCategoryChildrenUnread(session, cat_id=3, owner_uid=1)
    assert result == 0


def test_getCategoryChildrenUnread_with_children():
    """Two children, each with 3 unread, no grandchildren."""
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        # Calls: 1=child list [10,11], 2=count for 10, 3=grandchildren of 10,
        #        4=count for 11, 5=grandchildren of 11
        if call_count[0] == 1:
            r.scalars.return_value.all.return_value = [10, 11]
        elif call_count[0] in (3, 5):
            r.scalars.return_value.all.return_value = []
        else:
            r.scalar.return_value = 3
        return r

    session = MagicMock()
    session.execute.side_effect = side_effect
    result = getCategoryChildrenUnread(session, cat_id=3, owner_uid=1)
    assert result == 6  # 3 + 3


# ---------------------------------------------------------------------------
# getCategoryCounters
# ---------------------------------------------------------------------------


def test_getCategoryCounters_includes_labels_and_uncategorized():
    """Result must always include cat_id -2 and cat_id 0 entries."""
    session = MagicMock()

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        # Call 1: getCategoryUnread(-2) — labels count
        # Call 2: main category rows SELECT — empty
        # Call 3: ccache_find for cat=0
        if call_count[0] == 1:
            r.scalar.return_value = 4
        elif call_count[0] == 2:
            r.all.return_value = []
        else:
            r.scalar_one_or_none.return_value = 2  # ccache_find returns 2
        return r

    session.execute.side_effect = side_effect

    result = getCategoryCounters(session, owner_uid=1)
    ids = [c["id"] for c in result]
    assert -2 in ids
    assert 0 in ids


def test_getCategoryCounters_returns_kind_cat():
    session = MagicMock()

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            r.scalar.return_value = 0
        elif call_count[0] == 2:
            r.all.return_value = []
        else:
            r.scalar_one_or_none.return_value = 0
        return r

    session.execute.side_effect = side_effect
    result = getCategoryCounters(session, owner_uid=1)
    for entry in result:
        assert entry.get("kind") == "cat"


# ---------------------------------------------------------------------------
# getVirtCounters
# ---------------------------------------------------------------------------


def test_getVirtCounters_returns_five_entries():
    """Must return entries for 0, -1, -2, -3, -4."""
    session = MagicMock()
    session.execute.return_value.scalar.return_value = 1
    result = getVirtCounters(session, owner_uid=1)
    ids = [e["id"] for e in result]
    assert set(ids) == {0, -1, -2, -3, -4}


def test_getVirtCounters_auxcounter_only_for_0_neg1_neg2():
    """auxcounter > 0 only for feed IDs 0, -1, -2 (total count query)."""
    session = MagicMock()
    # unread returns 1 for all, total returns 5 for all
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        r.scalar.return_value = 5
        return r

    session.execute.side_effect = side_effect
    result = getVirtCounters(session, owner_uid=1)

    # Verify feeds with auxcounter > 0
    auxmap = {e["id"]: e["auxcounter"] for e in result}
    for fid in (0, -1, -2):
        assert auxmap[fid] == 5, f"feed {fid} should have auxcounter"
    # -3 and -4 should have auxcounter == 0
    assert auxmap[-3] == 0
    assert auxmap[-4] == 0


# ---------------------------------------------------------------------------
# getLabelCounters
# ---------------------------------------------------------------------------


def test_getLabelCounters_returns_virtual_feed_ids():
    """Counter IDs must be virtual feed IDs (label_to_feed_id)."""
    session = MagicMock()
    row = MagicMock()
    row.id = 1
    row.caption = "Important"
    row.unread = 3
    row.total = 10
    session.execute.return_value.all.return_value = [row]

    result = getLabelCounters(session, owner_uid=1)
    assert len(result) == 1
    assert result[0]["id"] == label_to_feed_id(1)
    assert result[0]["counter"] == 3
    assert result[0]["auxcounter"] == 10


def test_getLabelCounters_descriptions_flag():
    session = MagicMock()
    row = MagicMock()
    row.id = 2
    row.caption = "Work"
    row.unread = 0
    row.total = 5
    session.execute.return_value.all.return_value = [row]

    result = getLabelCounters(session, owner_uid=1, descriptions=True)
    assert result[0]["description"] == "Work"


def test_getLabelCounters_no_descriptions_by_default():
    session = MagicMock()
    row = MagicMock()
    row.id = 2
    row.caption = "Work"
    row.unread = 0
    row.total = 0
    session.execute.return_value.all.return_value = [row]

    result = getLabelCounters(session, owner_uid=1)
    assert "description" not in result[0]


def test_getLabelCounters_none_unread_coerced():
    session = MagicMock()
    row = MagicMock()
    row.id = 3
    row.caption = "Misc"
    row.unread = None
    row.total = None
    session.execute.return_value.all.return_value = [row]

    result = getLabelCounters(session, owner_uid=1)
    assert result[0]["counter"] == 0
    assert result[0]["auxcounter"] == 0


def test_getLabelCounters_empty():
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    result = getLabelCounters(session, owner_uid=1)
    assert result == []


# ---------------------------------------------------------------------------
# getFeedCounters
# ---------------------------------------------------------------------------


def _make_feed_row(feed_id, count, last_updated=None, last_error="", title="Test"):
    from datetime import datetime, timezone
    row = MagicMock()
    row.id = feed_id
    row.title = title
    row.count = count
    row.last_error = last_error
    row.last_updated = last_updated or datetime(2025, 1, 1, tzinfo=timezone.utc)
    return row


def test_getFeedCounters_basic_structure():
    session = MagicMock()
    row = _make_feed_row(5, 3)
    session.execute.return_value.all.return_value = [row]

    with patch("ttrss.feeds.ops.feed_has_icon", return_value=False):
        result = getFeedCounters(session, owner_uid=1)

    assert len(result) == 1
    assert result[0]["id"] == 5
    assert result[0]["counter"] == 3
    assert "updated" in result[0]
    assert "has_img" in result[0]


def test_getFeedCounters_has_img_true(tmp_path):
    from datetime import datetime, timezone
    session = MagicMock()
    row = _make_feed_row(5, 0)
    session.execute.return_value.all.return_value = [row]

    # Write a real icon file
    icon = tmp_path / "5.ico"
    icon.write_bytes(b"\x00\x00\x01\x00")
    result = getFeedCounters(session, owner_uid=1, icons_dir=str(tmp_path))
    assert result[0]["has_img"] == 1


def test_getFeedCounters_error_included():
    session = MagicMock()
    row = _make_feed_row(5, 0, last_error="  HTTP 404  ")
    session.execute.return_value.all.return_value = [row]

    with patch("ttrss.feeds.ops.feed_has_icon", return_value=False):
        result = getFeedCounters(session, owner_uid=1)

    assert result[0].get("error") == "HTTP 404"


def test_getFeedCounters_no_error_key_when_empty():
    session = MagicMock()
    row = _make_feed_row(5, 0, last_error="")
    session.execute.return_value.all.return_value = [row]

    with patch("ttrss.feeds.ops.feed_has_icon", return_value=False):
        result = getFeedCounters(session, owner_uid=1)

    assert "error" not in result[0]


def test_getFeedCounters_active_feed_gets_title():
    session = MagicMock()
    row = _make_feed_row(7, 2, title="A" * 40)
    session.execute.return_value.all.return_value = [row]

    with patch("ttrss.feeds.ops.feed_has_icon", return_value=False):
        result = getFeedCounters(session, owner_uid=1, active_feed=7)

    assert "title" in result[0]
    assert len(result[0]["title"]) <= 30


def test_getFeedCounters_stale_last_updated_blanked():
    """last_updated > 2 years old → empty string."""
    from datetime import datetime, timezone
    session = MagicMock()
    old_date = datetime(2000, 1, 1, tzinfo=timezone.utc)  # well over 2 years ago
    row = _make_feed_row(5, 0, last_updated=old_date)
    session.execute.return_value.all.return_value = [row]

    with patch("ttrss.feeds.ops.feed_has_icon", return_value=False):
        result = getFeedCounters(session, owner_uid=1)

    assert result[0]["updated"] == ""


def test_getFeedCounters_empty():
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    result = getFeedCounters(session, owner_uid=1)
    assert result == []


# ---------------------------------------------------------------------------
# getAllCounters
# ---------------------------------------------------------------------------


def test_getAllCounters_aggregates_all_subtypes():
    """getAllCounters must include entries from all 5 sub-functions."""
    session = MagicMock()

    with patch("ttrss.feeds.counters.getGlobalCounters", return_value=[{"id": "global-unread", "counter": 0}]), \
         patch("ttrss.feeds.counters.getVirtCounters", return_value=[{"id": -1, "counter": 0}]), \
         patch("ttrss.feeds.counters.getLabelCounters", return_value=[{"id": LABEL_BASE_INDEX - 1, "counter": 0}]), \
         patch("ttrss.feeds.counters.getFeedCounters", return_value=[{"id": 5, "counter": 3}]), \
         patch("ttrss.feeds.counters.getCategoryCounters", return_value=[{"id": 0, "kind": "cat", "counter": 0}]):
        result = getAllCounters(session, owner_uid=1)

    ids = [r["id"] for r in result]
    assert "global-unread" in ids
    assert -1 in ids
    assert 5 in ids
    assert 0 in ids


def test_getAllCounters_returns_list():
    session = MagicMock()
    with patch("ttrss.feeds.counters.getGlobalCounters", return_value=[]), \
         patch("ttrss.feeds.counters.getVirtCounters", return_value=[]), \
         patch("ttrss.feeds.counters.getLabelCounters", return_value=[]), \
         patch("ttrss.feeds.counters.getFeedCounters", return_value=[]), \
         patch("ttrss.feeds.counters.getCategoryCounters", return_value=[]):
        result = getAllCounters(session, owner_uid=1)
    assert result == []


# ---------------------------------------------------------------------------
# getFeedArticles public wrapper
# ---------------------------------------------------------------------------


def test_getFeedArticles_is_cat_delegates_to_getCategoryUnread():
    session = MagicMock()
    with patch("ttrss.feeds.counters.getCategoryUnread", return_value=9) as mock_cat:
        result = getFeedArticles(session, feed_id=3, owner_uid=1, is_cat=True)
    assert result == 9
    mock_cat.assert_called_once_with(session, 3, 1)


def test_getFeedArticles_regular_feed():
    session = MagicMock()
    with patch("ttrss.feeds.counters._count_feed_articles", return_value=5) as mock_cnt:
        result = getFeedArticles(session, feed_id=7, owner_uid=1)
    assert result == 5
    mock_cnt.assert_called_once_with(session, 7, 1, unread_only=True)


def test_getFeedArticles_total_not_unread():
    session = MagicMock()
    with patch("ttrss.feeds.counters._count_feed_articles", return_value=20) as mock_cnt:
        result = getFeedArticles(session, feed_id=7, owner_uid=1, unread_only=False)
    assert result == 20
    mock_cnt.assert_called_once_with(session, 7, 1, unread_only=False)


def test_getFeedArticles_none_coerces_to_zero():
    session = MagicMock()
    with patch("ttrss.feeds.counters._count_feed_articles", return_value=None):
        result = getFeedArticles(session, feed_id=7, owner_uid=1)
    assert result == 0
