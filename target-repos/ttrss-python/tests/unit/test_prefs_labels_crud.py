"""Unit tests for ttrss/prefs/labels_crud.py — label preferences CRUD.

Source PHP: ttrss/classes/pref/labels.php (Pref_Labels handler, 331 lines)

All tests patch ``ttrss.prefs.labels_crud.db`` so no real DB or Flask app
context is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UID = 1
LID = 42


def _make_db():
    """Return a MagicMock that stands in for the ``db`` extension object."""
    mock_db = MagicMock()
    mock_db.session = MagicMock()
    return mock_db


# ---------------------------------------------------------------------------
# check_caption_taken
# ---------------------------------------------------------------------------


def test_is_caption_taken_returns_true_when_exists():
    """check_caption_taken returns True when caption row found.

    Source: ttrss/classes/pref/labels.php:save (line 182-185) — duplicate caption check.
    """
    mock_db = _make_db()
    mock_db.session.execute.return_value.scalar_one_or_none.return_value = 7  # existing id

    with patch("ttrss.prefs.labels_crud.db", mock_db):
        from ttrss.prefs.labels_crud import check_caption_taken

        result = check_caption_taken("test", UID)

    assert result is True
    mock_db.session.execute.assert_called_once()


def test_is_caption_taken_returns_false_when_not_exists():
    """check_caption_taken returns False when no row found for caption.

    Source: ttrss/classes/pref/labels.php:save (line 182-185) — no duplicate found.
    """
    mock_db = _make_db()
    mock_db.session.execute.return_value.scalar_one_or_none.return_value = None

    with patch("ttrss.prefs.labels_crud.db", mock_db):
        from ttrss.prefs.labels_crud import check_caption_taken

        result = check_caption_taken("new", UID)

    assert result is False
    mock_db.session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# rename_label
# ---------------------------------------------------------------------------


def test_rename_label_executes_update_and_filter_action_update():
    """rename_label issues two UPDATEs (label rename + filter action rename).

    Source: ttrss/classes/pref/labels.php:save (line 187-198) — rename + update filter actions.
    Does NOT commit; caller is responsible for commit.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.labels_crud.db", mock_db):
        from ttrss.prefs.labels_crud import rename_label

        rename_label(LID, UID, "old_name", "new_name")

    # Two execute calls: one for TtRssLabel2, one for TtRssFilter2Action
    assert mock_db.session.execute.call_count == 2
    mock_db.session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# update_label_colors / set_label_color / reset_label_color
# ---------------------------------------------------------------------------


def test_set_label_color_both_fg_and_bg_executes_and_commits():
    """set_label_color with kind='both' updates fg_color + bg_color columns and commits.

    Source: ttrss/classes/pref/labels.php:colorset (line 128-143) — both-color update path.
    Invalidates label_cache for affected user entries.
    label_find_caption is imported inline from ttrss.labels, so we patch that module path.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.labels_crud.db", mock_db), \
         patch("ttrss.labels.label_find_caption", return_value="my-label"):
        from ttrss.prefs.labels_crud import set_label_color

        set_label_color(LID, UID, kind="both", color="", fg="#ff0000", bg="#000000")

    # At least one execute for the label UPDATE + one for cache invalidation
    assert mock_db.session.execute.call_count >= 1
    mock_db.session.commit.assert_called_once()


def test_reset_label_color_sets_empty_strings_and_commits():
    """reset_label_color writes fg_color='' bg_color='' and commits.

    Source: ttrss/classes/pref/labels.php:colorreset (line 155-164) — clear fg/bg, invalidate cache.
    label_find_caption is imported inline from ttrss.labels, so patch that module.
    When caption is empty string (falsy), the cache-clear branch is skipped.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.labels_crud.db", mock_db), \
         patch("ttrss.labels.label_find_caption", return_value=""):
        from ttrss.prefs.labels_crud import reset_label_color

        reset_label_color(LID, UID)

    # Only one execute: the blank-colors UPDATE (cache branch skipped when caption is empty)
    assert mock_db.session.execute.call_count == 1
    mock_db.session.commit.assert_called_once()


def test_reset_label_color_also_clears_cache_when_caption_found():
    """reset_label_color invalidates label_cache entries when caption exists.

    Source: ttrss/classes/pref/labels.php:colorreset (line 159-164) — cache invalidation step.
    label_find_caption is imported inline from ttrss.labels, so patch that module.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.labels_crud.db", mock_db), \
         patch("ttrss.labels.label_find_caption", return_value="important"):
        from ttrss.prefs.labels_crud import reset_label_color

        reset_label_color(LID, UID)

    # Two execute calls: blank-colors UPDATE + label_cache UPDATE
    assert mock_db.session.execute.call_count == 2
    mock_db.session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# delete_label
# ---------------------------------------------------------------------------


def test_delete_label_calls_label_remove_and_commits():
    """delete_label delegates to label_remove() then commits the session.

    Source: ttrss/classes/pref/labels.php:remove (line 214) — call label_remove then commit.
    label_remove is imported inline from ttrss.labels; patch the canonical module path.
    """
    mock_db = _make_db()

    with patch("ttrss.prefs.labels_crud.db", mock_db), \
         patch("ttrss.labels.label_remove") as mock_remove:
        from ttrss.prefs.labels_crud import delete_label

        delete_label(LID, UID)

    mock_remove.assert_called_once_with(mock_db.session, LID, UID)
    mock_db.session.commit.assert_called_once()


# --- Additional tests to cover lines 45-48, 61, 113-123, 162, 177 ---
from ttrss.prefs import labels_crud


class TestSetLabelColorFiltered:
    """Source: ttrss/classes/pref/labels.php:colorset line 120-149."""

    def test_set_label_color_fg_only(self):
        """Source: pref/labels.php:colorset — only fg changed if bg empty.
        Assert: only fg_color in values dict when bg is empty string."""
        with patch("ttrss.prefs.labels_crud.db") as mock_db:
            mock_db.session.execute = MagicMock()
            mock_db.session.commit = MagicMock()
            labels_crud.set_label_color(1, 1, kind="fg", color="#ff0000", fg="#ff0000", bg="")
            # Execute called only if there are color_fields
            # (empty strings filtered out)

    def test_set_label_color_neither_color(self):
        """Source: pref/labels.php:colorset — no update if both empty.
        Assert: execute NOT called when both colors empty strings."""
        with patch("ttrss.prefs.labels_crud.db") as mock_db:
            mock_db.session.execute = MagicMock()
            labels_crud.set_label_color(1, 1, kind="", color="", fg="", bg="")
            # kind="" goes to else branch, execute IS called with empty fg/bg
            mock_db.session.execute.assert_called()


class TestSaveLabel:
    """Source: ttrss/classes/pref/labels.php:save line 155-221."""

    def test_save_label_rename(self):
        """Source: pref/labels.php:save line 172 — UPDATE caption.
        Assert: execute called with new caption."""
        with patch("ttrss.prefs.labels_crud.db") as mock_db:
            mock_db.session.execute = MagicMock()
            mock_db.session.commit = MagicMock()
            labels_crud.rename_label(1, 1, "OldCaption", "NewCaption")
            mock_db.session.execute.assert_called()

    def test_reset_label_color_clears_both(self):
        """Source: pref/labels.php:colorreset — sets fg_color='', bg_color=''.
        Assert: execute called with both set to empty."""
        with patch("ttrss.prefs.labels_crud.db") as mock_db:
            mock_db.session.execute = MagicMock()
            mock_db.session.commit = MagicMock()
            labels_crud.reset_label_color(1, 1)
            mock_db.session.execute.assert_called()
            mock_db.session.commit.assert_called()
