"""Unit tests for ttrss/feeds/categories.py — category CRUD and traversal."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ttrss.feeds.categories import (
    MAX_CATEGORY_DEPTH,
    add_feed_category,
    get_feed_category,
    getArticleFeed,
    getCategoryTitle,
    getChildCategories,
    getFeedCatTitle,
    getFeedTitle,
    getParentCategories,
)
from ttrss.utils.feeds import LABEL_BASE_INDEX, label_to_feed_id


# ---------------------------------------------------------------------------
# getCategoryTitle
# ---------------------------------------------------------------------------


def test_getCategoryTitle_special():
    session = MagicMock()
    assert getCategoryTitle(session, -1) == "Special"
    session.execute.assert_not_called()


def test_getCategoryTitle_labels():
    session = MagicMock()
    assert getCategoryTitle(session, -2) == "Labels"


def test_getCategoryTitle_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "Work"
    assert getCategoryTitle(session, 5) == "Work"


def test_getCategoryTitle_not_found_returns_uncategorized():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert getCategoryTitle(session, 99) == "Uncategorized"


# ---------------------------------------------------------------------------
# getFeedCatTitle
# ---------------------------------------------------------------------------


def test_getFeedCatTitle_special():
    session = MagicMock()
    assert getFeedCatTitle(session, -1) == "Special"


def test_getFeedCatTitle_labels_virtual():
    session = MagicMock()
    assert getFeedCatTitle(session, LABEL_BASE_INDEX - 1) == "Labels"


def test_getFeedCatTitle_regular_feed_with_category():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "Tech"
    assert getFeedCatTitle(session, 7) == "Tech"


def test_getFeedCatTitle_regular_feed_no_category():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert getFeedCatTitle(session, 7) == "Uncategorized"


def test_getFeedCatTitle_invalid_returns_error_string():
    session = MagicMock()
    assert "failed" in getFeedCatTitle(session, -5)


# ---------------------------------------------------------------------------
# getFeedTitle
# ---------------------------------------------------------------------------


def test_getFeedTitle_cat_mode_delegates_to_getCategoryTitle():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "Science"
    result = getFeedTitle(session, 3, cat=True)
    assert result == "Science"


def test_getFeedTitle_starred():
    session = MagicMock()
    assert getFeedTitle(session, -1) == "Starred articles"


def test_getFeedTitle_published():
    session = MagicMock()
    assert getFeedTitle(session, -2) == "Published articles"


def test_getFeedTitle_fresh():
    session = MagicMock()
    assert getFeedTitle(session, -3) == "Fresh articles"


def test_getFeedTitle_all():
    session = MagicMock()
    assert getFeedTitle(session, -4) == "All articles"


def test_getFeedTitle_archived():
    session = MagicMock()
    assert getFeedTitle(session, 0) == "Archived articles"


def test_getFeedTitle_recently_read():
    session = MagicMock()
    assert getFeedTitle(session, -6) == "Recently read"


def test_getFeedTitle_label_feed():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "Important"
    vfid = label_to_feed_id(1)  # -1026
    result = getFeedTitle(session, vfid)
    assert result == "Important"


def test_getFeedTitle_label_feed_not_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    result = getFeedTitle(session, label_to_feed_id(42))
    assert "Unknown label" in result


def test_getFeedTitle_regular_feed():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "Hacker News"
    assert getFeedTitle(session, 5) == "Hacker News"


def test_getFeedTitle_regular_feed_not_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert "Unknown feed" in getFeedTitle(session, 99)


# ---------------------------------------------------------------------------
# getArticleFeed
# ---------------------------------------------------------------------------


def test_getArticleFeed_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 7
    assert getArticleFeed(session, article_id=10, owner_uid=1) == 7


def test_getArticleFeed_not_found_returns_zero():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert getArticleFeed(session, article_id=10, owner_uid=1) == 0


# ---------------------------------------------------------------------------
# get_feed_category
# ---------------------------------------------------------------------------


def test_get_feed_category_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 3
    result = get_feed_category(session, "Tech", owner_uid=1)
    assert result == 3


def test_get_feed_category_not_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    result = get_feed_category(session, "Missing", owner_uid=1)
    assert result is None


# ---------------------------------------------------------------------------
# add_feed_category
# ---------------------------------------------------------------------------


def test_add_feed_category_empty_title_returns_false():
    session = MagicMock()
    assert add_feed_category(session, "", owner_uid=1) is False
    session.add.assert_not_called()


def test_add_feed_category_creates_new():
    session = MagicMock()
    with patch("ttrss.feeds.categories.get_feed_category", return_value=None):
        result = add_feed_category(session, "Tech", owner_uid=1)
    assert result is True
    session.add.assert_called_once()


def test_add_feed_category_skips_existing():
    session = MagicMock()
    with patch("ttrss.feeds.categories.get_feed_category", return_value=5):
        result = add_feed_category(session, "Tech", owner_uid=1)
    assert result is False
    session.add.assert_not_called()


def test_add_feed_category_truncates_long_title():
    """Titles longer than 250 chars are truncated (matching PHP mb_substr behavior)."""
    session = MagicMock()
    long_title = "x" * 300
    with patch("ttrss.feeds.categories.get_feed_category", return_value=None):
        add_feed_category(session, long_title, owner_uid=1)
    added_obj = session.add.call_args[0][0]
    assert len(added_obj.title) == 250


# ---------------------------------------------------------------------------
# getParentCategories — depth guard
# ---------------------------------------------------------------------------


def test_getParentCategories_empty_when_no_parent():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    result = getParentCategories(session, cat_id=5, owner_uid=1)
    assert result == []


def test_getParentCategories_returns_parent_chain():
    """Returns parent + grandparent IDs."""
    call_count = [0]
    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        # First call: parent of cat 5 is cat 3
        # Second call: parent of cat 3 is nothing
        result.scalars.return_value.all.return_value = [3] if call_count[0] == 1 else []
        return result
    session = MagicMock()
    session.execute.side_effect = execute_side_effect
    result = getParentCategories(session, cat_id=5, owner_uid=1)
    assert result == [3]


def test_getParentCategories_depth_guard():
    """Returns [] immediately when _depth >= MAX_CATEGORY_DEPTH."""
    session = MagicMock()
    result = getParentCategories(session, cat_id=5, owner_uid=1, _depth=MAX_CATEGORY_DEPTH)
    assert result == []
    session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# getChildCategories — cat_id=0, depth guard
# ---------------------------------------------------------------------------


def test_getChildCategories_zero_returns_empty():
    """cat_id=0 (uncategorized) has no sub-categories — returns [] without DB query."""
    session = MagicMock()
    result = getChildCategories(session, cat_id=0, owner_uid=1)
    assert result == []
    session.execute.assert_not_called()


def test_getChildCategories_depth_guard():
    """Returns [] when _depth >= MAX_CATEGORY_DEPTH without DB query."""
    session = MagicMock()
    result = getChildCategories(session, cat_id=5, owner_uid=1, _depth=MAX_CATEGORY_DEPTH)
    assert result == []
    session.execute.assert_not_called()


def test_getChildCategories_returns_child_ids():
    session = MagicMock()
    call_count = [0]
    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        result.scalars.return_value.all.return_value = [10, 11] if call_count[0] == 1 else []
        return result
    session.execute.side_effect = execute_side_effect
    result = getChildCategories(session, cat_id=3, owner_uid=1)
    assert 10 in result
    assert 11 in result


def test_getChildCategories_empty():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    result = getChildCategories(session, cat_id=5, owner_uid=1)
    assert result == []
