"""Tests for prefs blueprint — HOOK_PREFS_* hook invocation sites.

Source: ttrss/prefs.php, ttrss/classes/pref/*.php
New: Python test suite.
"""
import pytest
from unittest.mock import MagicMock, patch


def _unwrap(fn):
    """Return the innermost wrapped function (bypasses login_required etc.)."""
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


class TestPrefsIndex:
    """GET /prefs/ — fires HOOK_PREFS_TABS."""

    def test_hook_prefs_tabs_fires(self, app):
        """HOOK_PREFS_TABS fires when index() is called.

        Source: ttrss/prefs.php:139 — run_hooks(HOOK_PREFS_TABS)
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tabs = MagicMock(return_value=[])

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import views
                _unwrap(views.index)()

        mock_pm.hook.hook_prefs_tabs.assert_called_once()

    def test_returns_json(self, app):
        """index() returns JSON with plugin_tabs key."""
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tabs = MagicMock(return_value=[])

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import views
                resp = _unwrap(views.index)()
        data = resp.get_json()
        assert "plugin_tabs" in data


class TestPrefsFeedsEditSave:
    """Feed pref handlers fire HOOK_PREFS_EDIT_FEED / HOOK_PREFS_SAVE_FEED."""

    def test_hook_prefs_edit_feed_fires(self, app):
        """HOOK_PREFS_EDIT_FEED fires on feed edit.

        Source: ttrss/classes/pref/feeds.php:748
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_edit_feed = MagicMock(return_value=[])
        mock_pm.hook.hook_prefs_tab_section = MagicMock(return_value=[])
        mock_pm.hook.hook_prefs_tab = MagicMock(return_value=[])

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import feeds
                _unwrap(feeds.edit_feed)(feed_id=1)

        mock_pm.hook.hook_prefs_edit_feed.assert_called_once_with(feed_id=1)

    def test_hook_prefs_save_feed_fires(self, app):
        """HOOK_PREFS_SAVE_FEED fires on feed save.

        Source: ttrss/classes/pref/feeds.php:981
        """
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_save_feed = MagicMock()

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import feeds
                _unwrap(feeds.save_feed)(feed_id=1)

        mock_pm.hook.hook_prefs_save_feed.assert_called_once_with(feed_id=1)


class TestPrefsTabHooks:
    """HOOK_PREFS_TAB fires in filters, labels, system, user_prefs, users."""

    def test_hook_prefs_tab_fires_filters(self, app):
        """HOOK_PREFS_TAB fires in filters handler."""
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab = MagicMock(return_value=[])

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import filters
                _unwrap(filters.filters)()

        mock_pm.hook.hook_prefs_tab.assert_called()

    def test_hook_prefs_tab_fires_labels(self, app):
        """HOOK_PREFS_TAB fires in labels handler."""
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab = MagicMock(return_value=[])

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import labels
                _unwrap(labels.labels)()

        mock_pm.hook.hook_prefs_tab.assert_called()

    def test_hook_prefs_tab_fires_system(self, app):
        """HOOK_PREFS_TAB fires in system handler."""
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab = MagicMock(return_value=[])

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm):
                from ttrss.blueprints.prefs import system
                _unwrap(system.system)()

        mock_pm.hook.hook_prefs_tab.assert_called()

    def test_hook_prefs_tab_fires_users(self, app):
        """HOOK_PREFS_TAB fires in users handler (requires admin access_level=10)."""
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab = MagicMock(return_value=[])
        mock_pm.hook.hook_prefs_tab_section = MagicMock(return_value=[])

        mock_admin = MagicMock()
        mock_admin.id = 1
        mock_admin.access_level = 10  # admin

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.users.current_user", mock_admin):
                from ttrss.blueprints.prefs import users
                _unwrap(users.users)()

        mock_pm.hook.hook_prefs_tab.assert_called()

    def test_hook_prefs_tab_fires_user_prefs(self, app):
        """HOOK_PREFS_TAB fires in user_prefs handler."""
        mock_pm = MagicMock()
        mock_pm.hook.hook_prefs_tab = MagicMock(return_value=[])
        mock_pm.hook.hook_prefs_tab_section = MagicMock(return_value=[])

        mock_user = MagicMock()
        mock_user.get_id.return_value = 1

        with app.test_request_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.blueprints.prefs.user_prefs.current_user", mock_user), \
                 patch("ttrss.prefs.ops.get_user_pref", return_value=""):
                from ttrss.blueprints.prefs import user_prefs
                _unwrap(user_prefs.user_prefs)()

        mock_pm.hook.hook_prefs_tab.assert_called()

    def test_no_direct_sql_in_prefs_blueprint(self):
        """AR-2: No direct db.session or SQLAlchemy calls in blueprints/prefs/*.

        Source: Phase 5 plan AR-2 — pref handlers delegate to Phase 3 functions.
        """
        import pathlib
        prefs_dir = pathlib.Path(
            "/Users/rd/devel/Capgemini/Capgemini_Internal/OSS_Migration/target-repos/ttrss-python/ttrss/blueprints/prefs"
        )
        for py_file in prefs_dir.glob("*.py"):
            source = py_file.read_text()
            assert "db.session" not in source, f"{py_file}: direct db.session call"
            assert "__tablename__" not in source, f"{py_file}: new model definition"
