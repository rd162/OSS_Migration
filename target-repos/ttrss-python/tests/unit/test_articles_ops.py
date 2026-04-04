"""Unit tests for ttrss/articles/ops.py — format_article, enclosures, catchup."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.articles.ops import (
    catchup_feed,
    catchupArticlesById,
    format_article,
    get_article_enclosures,
)
from ttrss.utils.feeds import LABEL_BASE_INDEX, label_to_feed_id


# ---------------------------------------------------------------------------
# get_article_enclosures
# ---------------------------------------------------------------------------


def test_get_article_enclosures_empty():
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    result = get_article_enclosures(session, article_id=1)
    assert result == []


def test_get_article_enclosures_returns_dicts():
    session = MagicMock()
    row = MagicMock()
    row.id = 10
    row.content_url = "http://example.com/audio.mp3"
    row.content_type = "audio/mpeg"
    row.title = "Episode 1"
    row.duration = "3600"
    session.execute.return_value.all.return_value = [row]

    result = get_article_enclosures(session, article_id=5)
    assert len(result) == 1
    assert result[0]["content_url"] == "http://example.com/audio.mp3"
    assert result[0]["content_type"] == "audio/mpeg"


# ---------------------------------------------------------------------------
# format_article
# ---------------------------------------------------------------------------


def _make_article_row(**overrides):
    """Build a mock article DB row with sensible defaults."""
    defaults = dict(
        id=42,
        title="Test Article",
        link="http://example.com/article",
        content="<p>Content</p>",
        comments="",
        lang="en",
        updated=datetime(2025, 1, 1, tzinfo=timezone.utc),
        num_comments=0,
        author="Alice",
        int_id=100,
        feed_id=5,
        orig_feed_id=None,
        tag_cache="",
        note=None,
        unread=False,
        marked=False,
        published=False,
        score=0,
        site_url="http://example.com",
        feed_title="Example Feed",
        hide_images=False,
        always_display_enclosures=False,
    )
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def test_format_article_not_found():
    """When the JOIN query returns no row, format_article returns None."""
    session = MagicMock()
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            r.scalar_one_or_none.return_value = 5  # feed_id
        elif call_count[0] == 3:
            r.one_or_none.return_value = None
        return r

    session.execute.side_effect = side_effect

    with patch("ttrss.articles.ops.ccache_update"):
        result = format_article(session, article_id=99, owner_uid=1)

    assert result is None


def test_format_article_returns_dict():
    """Happy path: returns dict with all expected keys."""
    row = _make_article_row()
    session = MagicMock()
    # Call 1: feed_id lookup
    # Call 2: UPDATE mark as read
    # Call 3+: ccache internals
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            r.scalar_one_or_none.return_value = 5  # feed_id
        elif call_count[0] == 3:
            r.one_or_none.return_value = row
        return r

    session.execute.side_effect = side_effect

    with patch("ttrss.articles.ops.ccache_update"), \
         patch("ttrss.articles.ops.get_article_tags", return_value=["python"]), \
         patch("ttrss.articles.ops.get_article_enclosures", return_value=[]), \
         patch("ttrss.articles.ops.get_article_labels", return_value=[]):
        result = format_article(session, article_id=42, owner_uid=1)

    assert result is not None
    assert result["id"] == 42
    assert result["title"] == "Test Article"
    assert result["tags"] == ["python"]
    assert isinstance(result["enclosures"], list)
    assert isinstance(result["labels"], list)
    assert "updated" in result
    assert result["feed_title"] == "Example Feed"


def test_format_article_no_mark_as_read():
    """mark_as_read=False skips UPDATE and ccache_update."""
    row = _make_article_row()
    session = MagicMock()
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            r.scalar_one_or_none.return_value = 5
        elif call_count[0] == 2:
            r.one_or_none.return_value = row
        return r

    session.execute.side_effect = side_effect

    with patch("ttrss.articles.ops.ccache_update") as mock_ccache, \
         patch("ttrss.articles.ops.get_article_tags", return_value=[]), \
         patch("ttrss.articles.ops.get_article_enclosures", return_value=[]), \
         patch("ttrss.articles.ops.get_article_labels", return_value=[]):
        result = format_article(
            session, article_id=42, owner_uid=1, mark_as_read=False
        )

    mock_ccache.assert_not_called()
    # Only 2 execute calls (feed_id + main SELECT)
    assert session.execute.call_count == 2


def test_format_article_updated_as_iso():
    row = _make_article_row(updated=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc))
    session = MagicMock()
    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        if call_count[0] == 1:
            r.scalar_one_or_none.return_value = 5
        elif call_count[0] == 2:
            r.one_or_none.return_value = row
        return r

    session.execute.side_effect = side_effect

    with patch("ttrss.articles.ops.ccache_update"), \
         patch("ttrss.articles.ops.get_article_tags", return_value=[]), \
         patch("ttrss.articles.ops.get_article_enclosures", return_value=[]), \
         patch("ttrss.articles.ops.get_article_labels", return_value=[]):
        result = format_article(
            session, article_id=42, owner_uid=1, mark_as_read=False
        )

    assert "2025-06-15" in result["updated"]


# ---------------------------------------------------------------------------
# catchupArticlesById
# ---------------------------------------------------------------------------


def test_catchupArticlesById_empty_ids_no_op():
    session = MagicMock()
    catchupArticlesById(session, ids=[], cmode=0, owner_uid=1)
    session.execute.assert_not_called()


def test_catchupArticlesById_cmode_0_marks_read():
    session = MagicMock()
    # UPDATE call + feed_id SELECT + ccache per feed
    feed_ids_mock = MagicMock()
    feed_ids_mock.scalars.return_value.all.return_value = [5]
    session.execute.side_effect = [
        MagicMock(),         # UPDATE unread=false
        feed_ids_mock,       # SELECT DISTINCT feed_id
    ]
    with patch("ttrss.articles.ops.ccache_update") as mock_ccache:
        catchupArticlesById(session, ids=[10, 11], cmode=0, owner_uid=1)
    assert session.execute.call_count == 2
    mock_ccache.assert_called_once_with(session, 5, 1)


def test_catchupArticlesById_cmode_1_marks_unread():
    session = MagicMock()
    feed_ids_mock = MagicMock()
    feed_ids_mock.scalars.return_value.all.return_value = [3]
    session.execute.side_effect = [
        MagicMock(),
        feed_ids_mock,
    ]
    with patch("ttrss.articles.ops.ccache_update"):
        catchupArticlesById(session, ids=[7], cmode=1, owner_uid=1)
    assert session.execute.call_count == 2


def test_catchupArticlesById_cmode_2_toggles():
    session = MagicMock()
    feed_ids_mock = MagicMock()
    feed_ids_mock.scalars.return_value.all.return_value = []
    session.execute.side_effect = [
        MagicMock(),
        feed_ids_mock,
    ]
    with patch("ttrss.articles.ops.ccache_update"):
        catchupArticlesById(session, ids=[1, 2], cmode=2, owner_uid=1)
    assert session.execute.call_count == 2


def test_catchupArticlesById_multiple_feeds_calls_ccache_each():
    session = MagicMock()
    feed_ids_mock = MagicMock()
    feed_ids_mock.scalars.return_value.all.return_value = [5, 7]
    session.execute.side_effect = [
        MagicMock(),
        feed_ids_mock,
    ]
    with patch("ttrss.articles.ops.ccache_update") as mock_ccache:
        catchupArticlesById(session, ids=[10, 11], cmode=0, owner_uid=1)
    assert mock_ccache.call_count == 2


def test_catchupArticlesById_skips_none_feed_id():
    session = MagicMock()
    feed_ids_mock = MagicMock()
    feed_ids_mock.scalars.return_value.all.return_value = [None, 5]
    session.execute.side_effect = [
        MagicMock(),
        feed_ids_mock,
    ]
    with patch("ttrss.articles.ops.ccache_update") as mock_ccache:
        catchupArticlesById(session, ids=[10], cmode=0, owner_uid=1)
    assert mock_ccache.call_count == 1  # None skipped, 5 processed


# ---------------------------------------------------------------------------
# catchup_feed
# ---------------------------------------------------------------------------


def test_catchup_feed_regular_mode_all():
    """feed > 0, cat_view=False, mode='all' — no date filter."""
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update") as mock_ccache:
        catchup_feed(session, feed_id=5, cat_view=False, owner_uid=1, mode="all")
    session.execute.assert_called_once()
    mock_ccache.assert_called_once()


def test_catchup_feed_mode_1day_adds_date_filter():
    """mode='1day' adds date subquery WHERE clause."""
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=5, cat_view=False, owner_uid=1, mode="1day")
    session.execute.assert_called_once()


def test_catchup_feed_starred_feed_minus_one():
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=-1, cat_view=False, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_published_feed_minus_two():
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=-2, cat_view=False, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_fresh_feed_minus_three():
    session = MagicMock()
    # pref lookups for FRESH_ARTICLE_MAX_AGE (2 calls: user + system pref)
    pref_user = MagicMock(**{"scalar_one_or_none.return_value": None})
    pref_sys = MagicMock(**{"scalar_one_or_none.return_value": "12"})
    update_result = MagicMock()
    session.execute.side_effect = [pref_user, pref_sys, update_result]

    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=-3, cat_view=False, owner_uid=1)
    assert session.execute.call_count == 3


def test_catchup_feed_all_articles_minus_four():
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=-4, cat_view=False, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_label_feed():
    label_vfid = label_to_feed_id(1)  # < LABEL_BASE_INDEX
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=label_vfid, cat_view=False, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_cat_view_positive_cat():
    """cat_view=True, feed=3 — get children + mark by feed_subq."""
    session = MagicMock()
    with patch("ttrss.feeds.categories.getChildCategories", return_value=[10, 11]):
        with patch("ttrss.articles.ops.ccache_update"):
            catchup_feed(session, feed_id=3, cat_view=True, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_cat_view_uncategorized_zero():
    """cat_view=True, feed=0 — IS NULL cat."""
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=0, cat_view=True, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_cat_view_labels_minus_two():
    """cat_view=True, feed=-2 — label entries."""
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update"):
        catchup_feed(session, feed_id=-2, cat_view=True, owner_uid=1)
    session.execute.assert_called_once()


def test_catchup_feed_tag_feed():
    """Non-numeric feed string → tag-based UPDATE."""
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update") as mock_ccache:
        catchup_feed(session, feed_id="linux", cat_view=False, owner_uid=1)
    session.execute.assert_called_once()
    mock_ccache.assert_not_called()  # tag feeds: is_numeric=False, no ccache_update


def test_catchup_feed_ccache_not_called_for_tag():
    """Tag feeds (non-numeric) don't call ccache_update."""
    session = MagicMock()
    with patch("ttrss.articles.ops.ccache_update") as mock_ccache:
        catchup_feed(session, feed_id="tech", cat_view=False, owner_uid=1)
    mock_ccache.assert_not_called()
