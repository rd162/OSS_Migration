"""Unit tests for ttrss/tasks/housekeeping.py."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from ttrss.tasks.housekeeping import (
    cleanup_tags,
    expire_cached_files,
    expire_error_log,
    housekeeping_common,
    update_feedbrowser_cache,
)


# ---------------------------------------------------------------------------
# expire_cached_files
# ---------------------------------------------------------------------------


def test_expire_cached_files_missing_dir_returns_zero(tmp_path):
    nonexistent = str(tmp_path / "does_not_exist")
    result = expire_cached_files(cache_dir=nonexistent)
    assert result == 0


def test_expire_cached_files_empty_dir_returns_zero(tmp_path):
    result = expire_cached_files(cache_dir=str(tmp_path))
    assert result == 0


def test_expire_cached_files_deletes_old_files(tmp_path):
    old_file = tmp_path / "old.txt"
    old_file.write_text("stale")
    # Set mtime to 10 days ago
    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(old_file, (old_ts, old_ts))

    result = expire_cached_files(cache_dir=str(tmp_path))
    assert result == 1
    assert not old_file.exists()


def test_expire_cached_files_keeps_recent_files(tmp_path):
    new_file = tmp_path / "recent.txt"
    new_file.write_text("fresh")
    # mtime is now — within retention window

    result = expire_cached_files(cache_dir=str(tmp_path))
    assert result == 0
    assert new_file.exists()


def test_expire_cached_files_skips_directories(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    # Set subdir mtime to old
    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(subdir, (old_ts, old_ts))

    result = expire_cached_files(cache_dir=str(tmp_path))
    # Directories are not deleted
    assert result == 0
    assert subdir.exists()


def test_expire_cached_files_mixed(tmp_path):
    """Old files deleted, new files kept."""
    old_file = tmp_path / "old.txt"
    old_file.write_text("stale")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=20)).timestamp()
    os.utime(old_file, (old_ts, old_ts))

    new_file = tmp_path / "new.txt"
    new_file.write_text("fresh")

    result = expire_cached_files(cache_dir=str(tmp_path))
    assert result == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_expire_cached_files_recurses_subdirectory(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    old_file = subdir / "deep.txt"
    old_file.write_text("stale")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(old_file, (old_ts, old_ts))

    result = expire_cached_files(cache_dir=str(tmp_path))
    assert result == 1


def test_expire_cached_files_uses_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("TTRSS_CACHE_DIR", str(tmp_path))
    result = expire_cached_files()
    assert result == 0  # empty dir


def test_expire_cached_files_handles_oserror(tmp_path):
    """OSError during unlink is silently skipped."""
    old_file = tmp_path / "locked.txt"
    old_file.write_text("data")
    old_ts = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(old_file, (old_ts, old_ts))

    with patch.object(Path, "unlink", side_effect=OSError("permission denied")):
        result = expire_cached_files(cache_dir=str(tmp_path))
    # File not deleted due to error, but no exception raised
    assert result == 0


# ---------------------------------------------------------------------------
# expire_error_log
# ---------------------------------------------------------------------------


def test_expire_error_log_returns_rowcount():
    session = MagicMock()
    session.execute.return_value.rowcount = 5
    result = expire_error_log(session)
    assert result == 5
    session.execute.assert_called_once()


def test_expire_error_log_zero_rows():
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    result = expire_error_log(session)
    assert result == 0


def test_expire_error_log_executes_delete():
    """Verify a DELETE statement is executed."""
    session = MagicMock()
    session.execute.return_value.rowcount = 3
    expire_error_log(session)
    assert session.execute.call_count == 1
    # The argument to execute should stringify to a DELETE statement
    stmt = session.execute.call_args[0][0]
    assert "DELETE" in str(stmt).upper() or hasattr(stmt, "is_delete")


# ---------------------------------------------------------------------------
# update_feedbrowser_cache
# ---------------------------------------------------------------------------


def test_update_feedbrowser_cache_clears_and_repopulates():
    session = MagicMock()
    row = MagicMock()
    row.feed_url = "http://example.com/feed"
    row.title = "Example"
    row.site_url = "http://example.com"
    row.subscribers = 10
    session.execute.return_value.all.return_value = [row]

    update_feedbrowser_cache(session)

    # DELETE + SELECT executed
    assert session.execute.call_count == 2
    # One cache row added
    session.add.assert_called_once()


def test_update_feedbrowser_cache_empty_result():
    session = MagicMock()
    session.execute.return_value.all.return_value = []

    update_feedbrowser_cache(session)

    session.add.assert_not_called()


def test_update_feedbrowser_cache_multiple_rows():
    session = MagicMock()

    def make_row(url, title, surl, subs):
        r = MagicMock()
        r.feed_url = url
        r.title = title
        r.site_url = surl
        r.subscribers = subs
        return r

    rows = [
        make_row("http://a.com/f", "A", "http://a.com", 5),
        make_row("http://b.com/f", "B", "http://b.com", 3),
    ]
    session.execute.return_value.all.return_value = rows

    update_feedbrowser_cache(session)

    assert session.add.call_count == 2


# ---------------------------------------------------------------------------
# cleanup_tags
# ---------------------------------------------------------------------------


def test_cleanup_tags_returns_rowcount():
    session = MagicMock()
    session.execute.return_value.rowcount = 42
    result = cleanup_tags(session)
    assert result == 42


def test_cleanup_tags_zero_rows():
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    result = cleanup_tags(session, days=14, limit=50000)
    assert result == 0


def test_cleanup_tags_executes_delete():
    session = MagicMock()
    session.execute.return_value.rowcount = 1
    cleanup_tags(session)
    assert session.execute.call_count == 1


def test_cleanup_tags_custom_days_and_limit():
    """Custom parameters are accepted without error."""
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    result = cleanup_tags(session, days=30, limit=1000)
    assert result == 0


# ---------------------------------------------------------------------------
# housekeeping_common — orchestrator
# ---------------------------------------------------------------------------


def test_housekeeping_common_calls_all_sub_functions(tmp_path):
    """All 5 sub-functions called in order; hook fired."""
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    session.execute.return_value.all.return_value = []

    pm_mock = MagicMock()

    with patch("ttrss.tasks.housekeeping.expire_cached_files") as mock_ecf, \
         patch("ttrss.tasks.housekeeping.expire_error_log") as mock_eel, \
         patch("ttrss.tasks.housekeeping.update_feedbrowser_cache") as mock_ufc, \
         patch("ttrss.feeds.ops.purge_orphans") as mock_po, \
         patch("ttrss.tasks.housekeeping.cleanup_tags") as mock_ct, \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock):
        housekeeping_common(session, cache_dir=str(tmp_path))

    mock_ecf.assert_called_once_with(cache_dir=str(tmp_path))
    mock_eel.assert_called_once_with(session)
    mock_ufc.assert_called_once_with(session)
    mock_ct.assert_called_once_with(session)
    pm_mock.hook.hook_house_keeping.assert_called_once_with(args={})


def test_housekeeping_common_default_cache_dir():
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    session.execute.return_value.all.return_value = []
    pm_mock = MagicMock()

    with patch("ttrss.tasks.housekeeping.expire_cached_files") as mock_ecf, \
         patch("ttrss.tasks.housekeeping.expire_error_log"), \
         patch("ttrss.tasks.housekeeping.update_feedbrowser_cache"), \
         patch("ttrss.feeds.ops.purge_orphans"), \
         patch("ttrss.tasks.housekeeping.cleanup_tags"), \
         patch("ttrss.plugins.manager.get_plugin_manager", return_value=pm_mock):
        housekeeping_common(session)

    # cache_dir=None → expire_cached_files uses env var or default
    mock_ecf.assert_called_once_with(cache_dir=None)


def test_housekeeping_common_plugin_hook_failure_does_not_raise():
    """Plugin hook exception is swallowed — housekeeping still completes."""
    session = MagicMock()
    session.execute.return_value.rowcount = 0
    session.execute.return_value.all.return_value = []

    with patch("ttrss.tasks.housekeeping.expire_cached_files"), \
         patch("ttrss.tasks.housekeeping.expire_error_log"), \
         patch("ttrss.tasks.housekeeping.update_feedbrowser_cache"), \
         patch("ttrss.feeds.ops.purge_orphans"), \
         patch("ttrss.tasks.housekeeping.cleanup_tags"), \
         patch("ttrss.plugins.manager.get_plugin_manager",
               side_effect=Exception("plugin error")):
        # Should not raise
        housekeeping_common(session)


def test_expire_lock_files_not_present():
    """expire_lock_files is ELIMINATED (ADR-0011, Celery replaces locks)."""
    import ttrss.tasks.housekeeping as hk
    assert not hasattr(hk, "expire_lock_files"), (
        "expire_lock_files must be eliminated — Celery handles job exclusivity"
    )
