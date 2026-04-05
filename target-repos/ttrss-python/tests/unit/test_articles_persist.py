"""Unit tests for ttrss/articles/persist.py — GUID, hash, upsert, filter actions."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.articles.persist import (
    _is_ngram_duplicate,
    _make_guid_from_title,
    apply_filter_actions,
    build_entry_guid,
    content_hash,
    persist_article,
    persist_enclosures,
    upsert_entry,
    upsert_user_entry,
)


# ---------------------------------------------------------------------------
# GUID helpers
# ---------------------------------------------------------------------------


def test_make_guid_from_title_returns_sha1_prefix():
    # PHP make_guid_from_title returns plain text (lowercase + punctuation→hyphen).
    # The SHA1 prefix is added later in build_entry_guid (owner-scoped hash).
    result = _make_guid_from_title("Hello World")
    assert result == "hello-world"  # PHP: mb_strtolower + replace space→hyphen


def test_make_guid_from_title_deterministic():
    a = _make_guid_from_title("same title")
    b = _make_guid_from_title("same title")
    assert a == b


def test_make_guid_from_title_different_titles():
    a = _make_guid_from_title("title A")
    b = _make_guid_from_title("title B")
    assert a != b


def test_build_entry_guid_uses_entry_id():
    entry = {"id": "http://example.com/article/1", "title": "T"}
    guid = build_entry_guid(entry, owner_uid=1)
    assert guid.startswith("SHA1:")


def test_build_entry_guid_falls_back_to_link():
    entry = {"link": "http://example.com/link", "title": "T"}
    guid = build_entry_guid(entry, owner_uid=1)
    assert guid.startswith("SHA1:")


def test_build_entry_guid_falls_back_to_title():
    entry = {"title": "My Article Title"}
    guid = build_entry_guid(entry, owner_uid=1)
    assert guid.startswith("SHA1:")


def test_build_entry_guid_is_owner_scoped():
    entry = {"id": "http://example.com/1", "title": "T"}
    guid1 = build_entry_guid(entry, owner_uid=1)
    guid2 = build_entry_guid(entry, owner_uid=2)
    assert guid1 != guid2


def test_build_entry_guid_truncated_to_245():
    # Very long id
    entry = {"id": "x" * 300, "title": "T"}
    guid = build_entry_guid(entry, owner_uid=1)
    assert len(guid) <= 245


def test_build_entry_guid_deterministic():
    entry = {"id": "http://example.com/1"}
    g1 = build_entry_guid(entry, owner_uid=5)
    g2 = build_entry_guid(entry, owner_uid=5)
    assert g1 == g2


# ---------------------------------------------------------------------------
# content_hash
# ---------------------------------------------------------------------------


def test_content_hash_returns_sha1_prefix():
    h = content_hash("article content here")
    assert h.startswith("SHA1:")


def test_content_hash_deterministic():
    assert content_hash("same") == content_hash("same")


def test_content_hash_different_content():
    assert content_hash("content A") != content_hash("content B")


def test_content_hash_empty_string():
    h = content_hash("")
    assert h.startswith("SHA1:")


# ---------------------------------------------------------------------------
# _is_ngram_duplicate
# ---------------------------------------------------------------------------


def test_is_ngram_duplicate_returns_false_when_no_match():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    assert _is_ngram_duplicate(session, "unique title", 1) is False


def test_is_ngram_duplicate_returns_true_when_match():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 42
    assert _is_ngram_duplicate(session, "duplicate title", 1) is True


def test_is_ngram_duplicate_empty_title_returns_false():
    session = MagicMock()
    assert _is_ngram_duplicate(session, "", 1) is False
    session.execute.assert_not_called()


def test_is_ngram_duplicate_swallows_exception():
    session = MagicMock()
    session.execute.side_effect = Exception("pg_trgm not installed")
    result = _is_ngram_duplicate(session, "title", 1)
    assert result is False


# ---------------------------------------------------------------------------
# apply_filter_actions
# ---------------------------------------------------------------------------


def _action(type_, param=""):
    return {"type": type_, "param": param}


def test_apply_filter_actions_catchup():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("catchup")], [])
    assert result["unread"] is False


def test_apply_filter_actions_mark():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("mark")], [])
    assert result["marked"] is True


def test_apply_filter_actions_publish():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("publish")], [])
    assert result["published"] is True


def test_apply_filter_actions_score():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("score", "10"), _action("score", "5")], [])
    assert result["score"] == 15


def test_apply_filter_actions_score_invalid_param_skipped():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("score", "bad"), _action("score", "3")], [])
    assert result["score"] == 3


def test_apply_filter_actions_tag_adds_to_list():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("tag", "python")], [])
    assert "python" in result["tags"]


def test_apply_filter_actions_tag_invalid_skipped():
    """Tags that fail tag_is_valid are not added."""
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [_action("tag", "")], [])
    assert result["tags"] == []


def test_apply_filter_actions_label_calls_label_add_article():
    session = MagicMock()
    with patch("ttrss.labels.label_add_article") as mock_add:
        apply_filter_actions(session, 42, 1, 5, [_action("label", "Tech")], [])
    mock_add.assert_called_once_with(session, 42, "Tech", 1)


def test_apply_filter_actions_label_empty_param_skipped():
    session = MagicMock()
    with patch("ttrss.labels.label_add_article") as mock_add:
        apply_filter_actions(session, 1, 1, 5, [_action("label", "")], [])
    mock_add.assert_not_called()


def test_apply_filter_actions_stop_breaks_loop():
    """Actions after 'stop' are not processed."""
    session = MagicMock()
    result = apply_filter_actions(
        session, 1, 1, 5,
        [_action("stop"), _action("catchup")],  # catchup after stop should be ignored
        [],
    )
    # After stop, catchup not processed → unread remains True
    assert result["unread"] is True


def test_apply_filter_actions_empty_no_change():
    session = MagicMock()
    result = apply_filter_actions(session, 1, 1, 5, [], [])
    assert result["unread"] is True
    assert result["marked"] is False
    assert result["published"] is False
    assert result["score"] == 0


# ---------------------------------------------------------------------------
# persist_enclosures
# ---------------------------------------------------------------------------


def test_persist_enclosures_inserts_new():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    persist_enclosures(session, article_id=1, enclosures=[
        {"content_url": "http://example.com/audio.mp3", "content_type": "audio/mpeg",
         "title": "Episode", "duration": "3600"},
    ])
    session.add.assert_called_once()


def test_persist_enclosures_deduplicates():
    session = MagicMock()
    # Existing URL already in DB
    session.execute.return_value.scalars.return_value.all.return_value = [
        "http://example.com/audio.mp3"
    ]

    persist_enclosures(session, article_id=1, enclosures=[
        {"content_url": "http://example.com/audio.mp3", "content_type": "audio/mpeg",
         "title": "", "duration": ""},
    ])
    # Already exists — no insert
    session.add.assert_not_called()


def test_persist_enclosures_skips_empty_url():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    persist_enclosures(session, article_id=1, enclosures=[
        {"content_url": "", "content_type": "audio/mpeg", "title": "", "duration": ""},
    ])
    session.add.assert_not_called()


def test_persist_enclosures_deduplicates_within_batch():
    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    # Same URL twice in the batch
    persist_enclosures(session, article_id=1, enclosures=[
        {"content_url": "http://dup.com/file.mp3", "content_type": "", "title": "", "duration": ""},
        {"content_url": "http://dup.com/file.mp3", "content_type": "", "title": "", "duration": ""},
    ])
    assert session.add.call_count == 1


# ---------------------------------------------------------------------------
# upsert_entry
# ---------------------------------------------------------------------------


def _now():
    return datetime.now(timezone.utc)


def test_upsert_entry_new_entry():
    session = MagicMock()
    # No existing entry
    session.execute.return_value.one_or_none.return_value = None

    entry_obj = MagicMock()
    entry_obj.id = 10
    session.add = MagicMock()
    session.flush = MagicMock()

    def add_side_effect(obj):
        obj.id = 10  # simulate DB assign

    session.add.side_effect = add_side_effect

    entry_id, is_new = upsert_entry(
        session, guid="SHA1:abc", title="T", link="http://x.com", content="body",
        content_hash_val="SHA1:xyz", author="A", updated=_now(),
    )
    assert is_new is True
    session.add.assert_called_once()
    session.flush.assert_called_once()


def test_upsert_entry_existing_same_hash_no_update():
    session = MagicMock()
    existing = MagicMock()
    existing.id = 5
    existing.content_hash = "SHA1:xyz"
    session.execute.return_value.one_or_none.return_value = existing

    entry_id, is_new = upsert_entry(
        session, guid="SHA1:abc", title="T", link="http://x.com", content="body",
        content_hash_val="SHA1:xyz", author="A", updated=_now(),
    )
    assert is_new is False
    assert entry_id == 5
    # No UPDATE executed (content_hash unchanged)
    session.execute.assert_called_once()  # only the SELECT


def test_upsert_entry_existing_changed_hash_updates():
    session = MagicMock()
    existing = MagicMock()
    existing.id = 5
    existing.content_hash = "SHA1:old"
    session.execute.return_value.one_or_none.return_value = existing

    # Second execute is the UPDATE
    session.execute.side_effect = [
        MagicMock(**{"one_or_none.return_value": existing}),  # SELECT
        MagicMock(),  # UPDATE
    ]

    entry_id, is_new = upsert_entry(
        session, guid="SHA1:abc", title="T", link="http://x.com", content="body",
        content_hash_val="SHA1:new", author="A", updated=_now(),
    )
    assert is_new is False
    assert entry_id == 5
    assert session.execute.call_count == 2


# ---------------------------------------------------------------------------
# upsert_user_entry
# ---------------------------------------------------------------------------


def test_upsert_user_entry_new():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    new_ue = MagicMock()
    new_ue.int_id = 100

    def add_side(obj):
        obj.int_id = 100

    session.add.side_effect = add_side
    session.flush = MagicMock()

    result = upsert_user_entry(session, ref_id=1, feed_id=5, owner_uid=1)
    assert result == 100
    session.add.assert_called_once()


def test_upsert_user_entry_existing_returns_none():
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = 42  # already exists

    result = upsert_user_entry(session, ref_id=1, feed_id=5, owner_uid=1)
    assert result is None
    session.add.assert_not_called()


# ---------------------------------------------------------------------------
# persist_article — integration smoke test
# ---------------------------------------------------------------------------


def _make_entry(**overrides):
    base = {
        "id": "http://example.com/article/1",
        "title": "Test Article",
        "link": "http://example.com/article/1",
        "summary": "Content here",
        "author": "Alice",
        "tags": [],
        "enclosures": [],
        "updated_parsed": None,
        "published_parsed": None,
    }
    base.update(overrides)
    return base


def test_persist_article_new_article():
    session = MagicMock()

    # SELECT for existing entry → None (new)
    # SELECT for existing user_entry → None (new)
    # SELECT for enclosures → empty
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        r.one_or_none.return_value = None    # upsert_entry: no existing
        r.scalar_one_or_none.return_value = None  # upsert_user_entry: no existing
        r.scalars.return_value.all.return_value = []  # enclosures
        return r

    session.execute.side_effect = execute_side_effect
    session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1) or setattr(obj, "int_id", 10))
    session.flush = MagicMock()

    with patch("ttrss.articles.persist._is_ngram_duplicate", return_value=False), \
         patch("ttrss.articles.filters.get_article_filters", return_value=[]), \
         patch("ttrss.articles.filters.calculate_article_score", return_value=0), \
         patch("ttrss.articles.persist.setArticleTags"):
        result = persist_article(
            session,
            entry=_make_entry(),
            feed_id=5,
            owner_uid=1,
            filters=[],
        )
    assert result is True


def test_persist_article_existing_entry_returns_false():
    session = MagicMock()
    existing = MagicMock()
    existing.id = 5
    existing.content_hash = "SHA1:same"

    session.execute.return_value.one_or_none.return_value = existing

    with patch("ttrss.articles.persist._is_ngram_duplicate", return_value=False):
        result = persist_article(
            session,
            entry=_make_entry(),
            feed_id=5,
            owner_uid=1,
            filters=[],
        )
    assert result is False


def test_persist_article_with_enclosures():
    session = MagicMock()

    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        call_count[0] += 1
        r = MagicMock()
        r.one_or_none.return_value = None
        r.scalar_one_or_none.return_value = None
        r.scalars.return_value.all.return_value = []
        return r

    session.execute.side_effect = execute_side_effect
    session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1) or setattr(obj, "int_id", 10))
    session.flush = MagicMock()

    enc = [{"content_url": "http://example.com/ep.mp3", "content_type": "audio/mpeg",
            "title": "Ep 1", "duration": "1800"}]

    with patch("ttrss.articles.persist._is_ngram_duplicate", return_value=False), \
         patch("ttrss.articles.filters.get_article_filters", return_value=[]), \
         patch("ttrss.articles.filters.calculate_article_score", return_value=0), \
         patch("ttrss.articles.persist.setArticleTags"):
        result = persist_article(
            session,
            entry=_make_entry(),
            feed_id=5,
            owner_uid=1,
            filters=[],
            enclosures=enc,
        )
    assert result is True


def test_persist_article_with_filter_actions_catchup_and_score():
    session = MagicMock()

    def execute_side_effect(*args, **kwargs):
        r = MagicMock()
        r.one_or_none.return_value = None
        r.scalar_one_or_none.return_value = None
        r.scalars.return_value.all.return_value = []
        return r

    session.execute.side_effect = execute_side_effect
    session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1) or setattr(obj, "int_id", 10))
    session.flush = MagicMock()

    matched = [{"type": "catchup", "param": ""}, {"type": "score", "param": "10"}]

    with patch("ttrss.articles.persist._is_ngram_duplicate", return_value=False), \
         patch("ttrss.articles.filters.get_article_filters", return_value=matched), \
         patch("ttrss.articles.filters.calculate_article_score", return_value=10), \
         patch("ttrss.articles.persist.setArticleTags"):
        result = persist_article(
            session,
            entry=_make_entry(),
            feed_id=5,
            owner_uid=1,
            filters=[],
        )
    assert result is True
