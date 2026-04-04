"""Tests for HOOK_UPDATE_TASK hook invocation in Celery tasks.

Source: ttrss/update.php:161,190 — HOOK_UPDATE_TASK around feed dispatch loop
        ttrss/classes/handler/public.php:411,421 — HOOK_UPDATE_TASK in housekeeping
New: Python test suite.
"""
import pytest
from unittest.mock import MagicMock, patch, call


def _make_app_ctx():
    """Return a mock Flask app with a usable app_context() context manager."""
    mock_app = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=None)
    ctx.__exit__ = MagicMock(return_value=False)
    mock_app.app_context.return_value = ctx
    return mock_app


class TestHookUpdateTaskFeedTasks:
    """HOOK_UPDATE_TASK fires before and after dispatch_feed_updates fan-out."""

    def test_hook_fires_before_and_after_dispatch(self):
        """dispatch_feed_updates calls hook_update_task twice: pre and post fan-out.

        Source: ttrss/update.php:161,190 — two run_hooks(HOOK_UPDATE_TASK) calls
        """
        from ttrss.tasks.feed_tasks import dispatch_feed_updates

        mock_pm = MagicMock()
        mock_pm.hook.hook_update_task = MagicMock()

        mock_app = _make_app_ctx()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("ttrss.create_app", return_value=mock_app), \
             patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
            mock_db.session = mock_session
            dispatch_feed_updates()

        assert mock_pm.hook.hook_update_task.call_count == 2

    def test_hook_failure_does_not_abort_dispatch(self):
        """If hook_update_task raises, dispatch still completes.

        Source: try/except isolation — each hook call independent.
        """
        from ttrss.tasks.feed_tasks import dispatch_feed_updates

        mock_pm = MagicMock()
        mock_pm.hook.hook_update_task.side_effect = Exception("hook error")

        mock_app = _make_app_ctx()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("ttrss.create_app", return_value=mock_app), \
             patch("ttrss.extensions.db") as mock_db, \
             patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
            mock_db.session = mock_session
            # Should not raise
            dispatch_feed_updates()


class TestHookUpdateTaskHousekeeping:
    """HOOK_UPDATE_TASK fires pre/post in housekeeping_common."""

    def test_hook_fires_pre_and_post_housekeeping(self):
        """housekeeping_common calls hook_update_task before and after.

        Source: ttrss/classes/handler/public.php:411,421 — two run_hooks calls
        """
        from ttrss.tasks.housekeeping import housekeeping_common

        mock_pm = MagicMock()
        mock_pm.hook.hook_update_task = MagicMock()
        mock_pm.hook.hook_house_keeping = MagicMock()

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
             patch("ttrss.tasks.housekeeping.expire_cached_files"), \
             patch("ttrss.tasks.housekeeping.expire_error_log"), \
             patch("ttrss.tasks.housekeeping.update_feedbrowser_cache"), \
             patch("ttrss.tasks.housekeeping.cleanup_tags"), \
             patch("ttrss.feeds.ops.purge_orphans"):
            housekeeping_common(mock_session)

        assert mock_pm.hook.hook_update_task.call_count == 2
