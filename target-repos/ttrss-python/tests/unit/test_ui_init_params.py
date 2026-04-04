"""Tests for ttrss/ui/init_params.py — make_init_params, make_runtime_info, hotkeys.

Source: ttrss/include/functions2.php:make_init_params, get_hotkeys_map, get_hotkeys_info
        ttrss/index.php:213,252 — HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM
New: Python test suite.
"""
import json
import pytest
from unittest.mock import MagicMock, patch


class TestGetHotkeysInfo:
    """get_hotkeys_info returns dict with baseline + HOOK_HOTKEY_INFO pipeline."""

    def test_returns_dict_with_navigation_section(self):
        from ttrss.ui.init_params import get_hotkeys_info
        with patch("ttrss.plugins.manager.get_plugin_manager") as mock_gpm:
            mock_pm = MagicMock()
            mock_pm.hook.hook_hotkey_info = MagicMock(return_value=[])
            mock_gpm.return_value = mock_pm
            result = get_hotkeys_info()
        assert isinstance(result, dict)
        assert "navigation" in result
        assert "article" in result

    def test_json_serializable(self):
        from ttrss.ui.init_params import get_hotkeys_info
        with patch("ttrss.plugins.manager.get_plugin_manager") as mock_gpm:
            mock_pm = MagicMock()
            mock_pm.hook.hook_hotkey_info = MagicMock(return_value=[])
            mock_gpm.return_value = mock_pm
            result = get_hotkeys_info()
        # AR-1: must be JSON serializable (no HTML)
        json.dumps(result)

    def test_no_html_in_output(self):
        from ttrss.ui.init_params import get_hotkeys_info
        with patch("ttrss.plugins.manager.get_plugin_manager") as mock_gpm:
            mock_pm = MagicMock()
            mock_pm.hook.hook_hotkey_info = MagicMock(return_value=[])
            mock_gpm.return_value = mock_pm
            result = get_hotkeys_info()
        dumped = json.dumps(result)
        assert "<" not in dumped and ">" not in dumped


class TestGetHotkeysMap:
    """get_hotkeys_map returns (prefixes, map) + HOOK_HOTKEY_MAP pipeline."""

    def test_returns_tuple_of_prefixes_and_map(self):
        from ttrss.ui.init_params import get_hotkeys_map
        with patch("ttrss.plugins.manager.get_plugin_manager") as mock_gpm:
            mock_pm = MagicMock()
            mock_pm.hook.hook_hotkey_map = MagicMock(return_value=[])
            mock_gpm.return_value = mock_pm
            prefixes, hotkeys = get_hotkeys_map()
        assert isinstance(prefixes, list)
        assert isinstance(hotkeys, dict)

    def test_prefixes_are_single_chars(self):
        from ttrss.ui.init_params import get_hotkeys_map
        with patch("ttrss.plugins.manager.get_plugin_manager") as mock_gpm:
            mock_pm = MagicMock()
            mock_pm.hook.hook_hotkey_map = MagicMock(return_value=[])
            mock_gpm.return_value = mock_pm
            prefixes, _ = get_hotkeys_map()
        for p in prefixes:
            assert len(p) == 1


class TestMakeRuntimeInfo:
    """make_runtime_info returns JSON-serializable dict."""

    def test_returns_required_keys(self, app):
        from ttrss.ui.init_params import make_runtime_info
        with app.app_context():
            result = make_runtime_info(owner_uid=1)
        assert "max_feed_id" in result
        assert "num_feeds" in result
        assert "last_article_id" in result
        assert "daemon_is_running" in result

    def test_daemon_is_running_always_true(self, app):
        """daemon_is_running is always True — Celery Beat replaces file-based daemon check.

        New: no PHP equivalent — Celery Beat is the scheduler (ADR-0011).
        """
        from ttrss.ui.init_params import make_runtime_info
        with app.app_context():
            result = make_runtime_info(owner_uid=1)
        assert result["daemon_is_running"] is True

    def test_json_serializable(self, app):
        from ttrss.ui.init_params import make_runtime_info
        with app.app_context():
            result = make_runtime_info(owner_uid=1)
        json.dumps(result)


class TestMakeInitParams:
    """make_init_params returns JSON-serializable dict; hooks fire."""

    def test_fires_hook_toolbar_button(self, app):
        """make_init_params fires HOOK_TOOLBAR_BUTTON.

        Source: ttrss/index.php:213 — run_hooks(HOOK_TOOLBAR_BUTTON)
        """
        from ttrss.ui.init_params import make_init_params

        mock_pm = MagicMock()
        mock_pm.hook.hook_toolbar_button = MagicMock(return_value=[])
        mock_pm.hook.hook_action_item = MagicMock(return_value=[])
        mock_pm.hook.hook_hotkey_map = MagicMock(return_value=[])

        with app.app_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.prefs.ops.get_user_pref", return_value=""):
                make_init_params(owner_uid=1)
        mock_pm.hook.hook_toolbar_button.assert_called_once()

    def test_fires_hook_action_item(self, app):
        """make_init_params fires HOOK_ACTION_ITEM.

        Source: ttrss/index.php:252 — run_hooks(HOOK_ACTION_ITEM)
        """
        from ttrss.ui.init_params import make_init_params

        mock_pm = MagicMock()
        mock_pm.hook.hook_toolbar_button = MagicMock(return_value=[])
        mock_pm.hook.hook_action_item = MagicMock(return_value=[])
        mock_pm.hook.hook_hotkey_map = MagicMock(return_value=[])

        with app.app_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.prefs.ops.get_user_pref", return_value=""):
                make_init_params(owner_uid=1)
        mock_pm.hook.hook_action_item.assert_called_once()

    def test_json_serializable(self, app):
        from ttrss.ui.init_params import make_init_params

        mock_pm = MagicMock()
        mock_pm.hook.hook_toolbar_button = MagicMock(return_value=[])
        mock_pm.hook.hook_action_item = MagicMock(return_value=[])
        mock_pm.hook.hook_hotkey_map = MagicMock(return_value=[])

        with app.app_context():
            with patch("ttrss.plugins.manager.get_plugin_manager", return_value=mock_pm), \
                 patch("ttrss.prefs.ops.get_user_pref", return_value=""):
                result = make_init_params(owner_uid=1)
        json.dumps(result)
