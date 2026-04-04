"""Unit tests for ttrss/articles/tags.py — article tag operations."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.articles.tags import get_article_tags, setArticleTags, tag_is_valid


# ---------------------------------------------------------------------------
# tag_is_valid
# ---------------------------------------------------------------------------


def test_tag_is_valid_empty():
    assert tag_is_valid("") is False


def test_tag_is_valid_whitespace_only():
    assert tag_is_valid("   ") is False


def test_tag_is_valid_numeric():
    assert tag_is_valid("123") is False


def test_tag_is_valid_ok():
    assert tag_is_valid("python") is True


def test_tag_is_valid_too_long():
    assert tag_is_valid("x" * 251) is False


def test_tag_is_valid_exactly_250():
    assert tag_is_valid("x" * 250) is True


def test_tag_is_valid_alphanumeric_not_purely_numeric():
    assert tag_is_valid("tag1") is True


# ---------------------------------------------------------------------------
# get_article_tags — cache hit
# ---------------------------------------------------------------------------


def test_get_article_tags_cache_hit_splits_on_comma():
    session = MagicMock()
    result = get_article_tags(session, article_id=10, owner_uid=1, tag_cache="python,linux")
    assert result == ["python", "linux"]
    session.execute.assert_not_called()


def test_get_article_tags_empty_cache_string_is_miss():
    """Empty string tag_cache → treated as cache miss → DB query."""
    session = MagicMock()
    # First execute: int_id subq → tag lookup
    tags_mock = MagicMock()
    tags_mock.scalars.return_value.all.return_value = ["go"]
    update_mock = MagicMock()
    session.execute.side_effect = [tags_mock, update_mock]

    result = get_article_tags(session, article_id=10, owner_uid=1, tag_cache="")
    assert result == ["go"]


def test_get_article_tags_none_tag_cache_reads_db():
    """tag_cache=None → load from DB, then on miss query ttrss_tags."""
    session = MagicMock()
    # Call 1: load tag_cache → None (miss)
    # Call 2: tag names query
    # Call 3: cache write UPDATE
    session.execute.side_effect = [
        MagicMock(**{"scalar_one_or_none.return_value": None}),
        MagicMock(**{"scalars.return_value.all.return_value": ["rust"]}),
        MagicMock(),  # UPDATE
    ]
    result = get_article_tags(session, article_id=5, owner_uid=1)
    assert result == ["rust"]
    assert session.execute.call_count == 3


def test_get_article_tags_uses_cached_value_from_db():
    """tag_cache loaded from DB is non-empty → split and return."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "a,b,c"
    result = get_article_tags(session, article_id=5, owner_uid=1)
    assert result == ["a", "b", "c"]
    assert session.execute.call_count == 1


def test_get_article_tags_filters_empty_strings():
    """Trailing comma in cache → no empty strings in output."""
    session = MagicMock()
    result = get_article_tags(session, article_id=1, owner_uid=1, tag_cache="a,b,")
    assert "" not in result
    assert result == ["a", "b"]


# ---------------------------------------------------------------------------
# setArticleTags
# ---------------------------------------------------------------------------


def test_setArticleTags_no_op_when_no_int_id():
    """No user_entry found → early return, no DB writes."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    setArticleTags(session, article_id=10, owner_uid=1, tags=["tag"])
    # Only one execute (the int_id lookup)
    assert session.execute.call_count == 1
    session.add.assert_not_called()


def test_setArticleTags_deletes_and_inserts():
    session = MagicMock()
    # Call 1: int_id lookup
    # Call 2: DELETE existing tags
    # Call 3: UPDATE tag_cache
    session.execute.side_effect = [
        MagicMock(**{"scalar_one_or_none.return_value": 99}),
        MagicMock(),  # DELETE
        MagicMock(),  # UPDATE cache
    ]
    setArticleTags(session, article_id=5, owner_uid=1, tags=["linux", "python"])
    assert session.execute.call_count == 3
    assert session.add.call_count == 2


def test_setArticleTags_filters_invalid_tags():
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"scalar_one_or_none.return_value": 42}),
        MagicMock(),  # DELETE
        MagicMock(),  # UPDATE
    ]
    # "123" is numeric → invalid; "" is empty → invalid; "ok" is valid
    setArticleTags(session, article_id=5, owner_uid=1, tags=["123", "", "ok"])
    assert session.add.call_count == 1


def test_setArticleTags_empty_list_clears_all():
    """Empty tag list: delete all tags, set empty cache."""
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"scalar_one_or_none.return_value": 7}),
        MagicMock(),  # DELETE
        MagicMock(),  # UPDATE
    ]
    setArticleTags(session, article_id=5, owner_uid=1, tags=[])
    session.add.assert_not_called()
    assert session.execute.call_count == 3


def test_setArticleTags_strips_whitespace_from_tags():
    session = MagicMock()
    session.execute.side_effect = [
        MagicMock(**{"scalar_one_or_none.return_value": 7}),
        MagicMock(),
        MagicMock(),
    ]
    setArticleTags(session, article_id=5, owner_uid=1, tags=["  linux  ", "  "])
    # "  linux  ".strip() → "linux" → valid; "  ".strip() → "" → invalid
    assert session.add.call_count == 1
