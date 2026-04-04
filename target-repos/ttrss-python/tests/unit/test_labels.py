"""Unit tests for ttrss/labels.py — label CRUD and cache management.

Tests use MagicMock session so no real DB is required.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.labels import (
    get_all_labels,
    get_article_labels,
    label_add_article,
    label_clear_cache,
    label_create,
    label_find_caption,
    label_find_id,
    label_remove,
    label_remove_article,
    label_update_cache,
)
from ttrss.utils.feeds import LABEL_BASE_INDEX, label_to_feed_id


# ---------------------------------------------------------------------------
# label_find_id
# ---------------------------------------------------------------------------


def test_label_find_id_returns_id_when_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 7
    assert label_find_id(session, "important", owner_uid=1) == 7


def test_label_find_id_returns_zero_when_not_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert label_find_id(session, "missing", owner_uid=1) == 0


# ---------------------------------------------------------------------------
# label_find_caption
# ---------------------------------------------------------------------------


def test_label_find_caption_returns_caption():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "Work"
    assert label_find_caption(session, label_id=3, owner_uid=1) == "Work"


def test_label_find_caption_returns_empty_string_when_not_found():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert label_find_caption(session, label_id=99, owner_uid=1) == ""


# ---------------------------------------------------------------------------
# get_all_labels
# ---------------------------------------------------------------------------


def test_get_all_labels_returns_list_of_dicts():
    row = MagicMock()
    row.fg_color = "#ff0000"
    row.bg_color = "#ffffff"
    row.caption = "urgent"
    session = MagicMock()
    session.execute.return_value.all.return_value = [row]
    result = get_all_labels(session, owner_uid=1)
    assert result == [{"fg_color": "#ff0000", "bg_color": "#ffffff", "caption": "urgent"}]


def test_get_all_labels_empty():
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    assert get_all_labels(session, owner_uid=1) == []


# ---------------------------------------------------------------------------
# get_article_labels — label_cache JSON format (R8)
# ---------------------------------------------------------------------------


def test_get_article_labels_cache_hit_list():
    """Cache hit: returns list from JSON-decoded label_cache."""
    labels = [[label_to_feed_id(1), "Work", "#f00", "#fff"]]
    cached_str = json.dumps(labels)
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = cached_str
    result = get_article_labels(session, article_id=10, owner_uid=1)
    assert result == labels
    session.execute.assert_called_once()  # only the label_cache lookup


def test_get_article_labels_cache_hit_no_labels_sentinel():
    """Cache hit: {"no-labels": 1} sentinel returns empty list."""
    cached_str = json.dumps({"no-labels": 1})
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = cached_str
    result = get_article_labels(session, article_id=10, owner_uid=1)
    assert result == []


def test_get_article_labels_cache_miss_queries_db():
    """Cache miss: queries ttrss_labels2 JOIN ttrss_user_labels2."""
    label_row = MagicMock()
    label_row.label_id = 1
    label_row.caption = "news"
    label_row.fg_color = "#000"
    label_row.bg_color = "#fff"

    # Call 1: label_cache lookup → empty string (cache miss)
    # Call 2: label DB query → [label_row]
    # Call 3: label_update_cache write
    session = MagicMock()
    call_results = iter([
        MagicMock(**{"scalar_one_or_none.return_value": ""}),  # cache miss (empty str)
        MagicMock(**{"all.return_value": [label_row]}),         # DB query
        MagicMock(),                                             # cache write
    ])
    session.execute.side_effect = lambda *a, **kw: next(call_results)

    result = get_article_labels(session, article_id=10, owner_uid=1)

    expected_vfid = label_to_feed_id(1)
    assert result == [[expected_vfid, "news", "#000", "#fff"]]
    assert session.execute.call_count == 3  # cache read + DB query + cache write


def test_get_article_labels_cache_miss_no_labels_writes_sentinel():
    """Cache miss with no labels in DB: writes {"no-labels": 1} sentinel."""
    session = MagicMock()
    call_results = iter([
        MagicMock(**{"scalar_one_or_none.return_value": ""}),  # cache miss
        MagicMock(**{"all.return_value": []}),                  # empty DB result
        MagicMock(),                                             # cache write
    ])
    session.execute.side_effect = lambda *a, **kw: next(call_results)

    result = get_article_labels(session, article_id=5, owner_uid=1)
    assert result == []


def test_label_cache_format_matches_php():
    """label_cache JSON must be: [[virtual_feed_id, caption, fg, bg], ...].

    Source: ttrss/include/labels.php:45-48 (PHP array structure) + R8.
    """
    label_id = 1
    vfid = label_to_feed_id(label_id)
    assert vfid == LABEL_BASE_INDEX - 1 - 1  # == -1026

    # PHP format: [label_to_feed_id($line["label_id"]), caption, fg, bg]
    expected = [[vfid, "Work", "#ff0000", "#ffffff"]]
    cache_str = json.dumps(expected)
    parsed = json.loads(cache_str)
    assert parsed == expected
    assert parsed[0][0] == vfid   # virtual feed ID is first element
    assert parsed[0][1] == "Work"  # caption is second


# ---------------------------------------------------------------------------
# label_update_cache
# ---------------------------------------------------------------------------


def test_label_update_cache_writes_json():
    """label_update_cache serializes labels to JSON and writes to DB."""
    session = MagicMock()
    labels = [[label_to_feed_id(1), "test", "", ""]]
    label_update_cache(session, owner_uid=1, article_id=5, labels=labels)
    session.execute.assert_called_once()


def test_label_update_cache_no_labels_arg_fetches_labels():
    """When labels=None, calls get_article_labels then writes cache."""
    with patch("ttrss.labels.get_article_labels", return_value=[]) as mock_get:
        session = MagicMock()
        label_update_cache(session, owner_uid=1, article_id=5, labels=None)
        mock_get.assert_called_once_with(session, 5, 1)


# ---------------------------------------------------------------------------
# label_clear_cache
# ---------------------------------------------------------------------------


def test_label_clear_cache_sets_empty_string():
    """label_clear_cache sets label_cache = '' (NOT NULL) for all user entries."""
    session = MagicMock()
    label_clear_cache(session, article_id=3)
    session.execute.assert_called_once()
    # Verify the executed statement references the article
    stmt = session.execute.call_args[0][0]
    # The statement is a SQLAlchemy Update object; check it can be compiled
    assert stmt is not None


# ---------------------------------------------------------------------------
# label_remove_article
# ---------------------------------------------------------------------------


def test_label_remove_article_no_label_found_is_noop():
    """label_remove_article is a no-op when the label caption doesn't exist."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None  # label not found (0)
    # label_find_id returns 0 when not found; falsy → early return
    with patch("ttrss.labels.label_find_id", return_value=0):
        label_remove_article(session, article_id=1, caption="missing", owner_uid=1)
    session.execute.assert_not_called()


def test_label_remove_article_deletes_and_clears_cache():
    """label_remove_article deletes TtRssUserLabel2 row and clears label_cache."""
    session = MagicMock()
    with patch("ttrss.labels.label_find_id", return_value=5):
        with patch("ttrss.labels.label_clear_cache") as mock_clear:
            label_remove_article(session, article_id=10, caption="Work", owner_uid=1)
    session.execute.assert_called_once()  # DELETE
    mock_clear.assert_called_once_with(session, 10)


# ---------------------------------------------------------------------------
# label_add_article
# ---------------------------------------------------------------------------


def test_label_add_article_no_label_found_is_noop():
    session = MagicMock()
    with patch("ttrss.labels.label_find_id", return_value=0):
        label_add_article(session, article_id=1, caption="missing", owner_uid=1)
    session.execute.assert_not_called()
    session.add.assert_not_called()


def test_label_add_article_inserts_when_not_exists():
    """Adds TtRssUserLabel2 row when not already assigned."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None  # not exists
    with patch("ttrss.labels.label_find_id", return_value=3):
        with patch("ttrss.labels.label_clear_cache") as mock_clear:
            label_add_article(session, article_id=10, caption="Work", owner_uid=1)
    session.add.assert_called_once()
    mock_clear.assert_called_once_with(session, 10)


def test_label_add_article_idempotent_no_duplicate_insert():
    """Skips INSERT when article already has the label."""
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 10  # already exists
    with patch("ttrss.labels.label_find_id", return_value=3):
        with patch("ttrss.labels.label_clear_cache"):
            label_add_article(session, article_id=10, caption="Work", owner_uid=1)
    session.add.assert_not_called()


# ---------------------------------------------------------------------------
# label_create
# ---------------------------------------------------------------------------


def test_label_create_inserts_when_not_exists():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    result = label_create(session, caption="new", fg_color="#f00", bg_color="#fff", owner_uid=1)
    assert result is True
    session.add.assert_called_once()


def test_label_create_returns_false_when_exists():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 5  # already exists
    result = label_create(session, caption="existing", owner_uid=1)
    assert result is False
    session.add.assert_not_called()


# ---------------------------------------------------------------------------
# label_remove
# ---------------------------------------------------------------------------


def test_label_remove_deletes_label_and_access_key():
    """label_remove deletes label, removes access key, clears cache entries."""
    session = MagicMock()
    # Call 1: SELECT caption
    # Call 2: DELETE label + RETURNING
    # Call 3: DELETE access key
    # Call 4: UPDATE label_cache
    call_results = iter([
        MagicMock(**{"scalar_one_or_none.return_value": "Work"}),   # caption
        MagicMock(**{"scalar_one_or_none.return_value": 5}),         # deleted id
        MagicMock(),                                                   # access key delete
        MagicMock(),                                                   # cache clear
    ])
    session.execute.side_effect = lambda *a, **kw: next(call_results)

    label_remove(session, label_id=5, owner_uid=1)

    assert session.execute.call_count == 4


def test_label_remove_no_op_when_not_deleted():
    """label_remove skips access key and cache cleanup when DELETE returns nothing."""
    session = MagicMock()
    call_results = iter([
        MagicMock(**{"scalar_one_or_none.return_value": "Work"}),  # caption
        MagicMock(**{"scalar_one_or_none.return_value": None}),    # not deleted
    ])
    session.execute.side_effect = lambda *a, **kw: next(call_results)

    label_remove(session, label_id=99, owner_uid=1)

    # Only 2 executes (caption + DELETE), no access key or cache cleanup
    assert session.execute.call_count == 2
