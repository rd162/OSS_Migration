"""Tests for plugin loader — load_user_plugins calls load_plugin_data after each load cycle.

Source: ttrss/include/functions.php:load_user_plugins (lines 818-828)
        ttrss/classes/pluginhost.php:PluginHost::load_data (lines 214-225)
New: Python test suite.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest


class TestLoadUserPlugins:
    """load_user_plugins wires plugin loading + storage hydration per PHP line 824."""

    def test_load_plugin_data_called_after_user_plugins_load(self, app):
        """load_user_plugins calls load_plugin_data after loading user plugins.

        Source: ttrss/include/functions.php:824 — PluginHost::load_data() after KIND_USER load
        """
        from ttrss.plugins.loader import load_user_plugins

        # get_user_pref and load_plugin_data are lazy-imported inside load_user_plugins;
        # patch at their source modules so the local import picks up the mock.
        with app.app_context():
            with patch("ttrss.prefs.ops.get_user_pref", return_value="some_plugin"):
                with patch("ttrss.plugins.loader._load_plugin", return_value=True):
                    with patch("ttrss.plugins.storage.load_plugin_data") as mock_load_data:
                        load_user_plugins(owner_uid=1)

        # load_plugin_data must be called once after the loading loop
        assert mock_load_data.call_count == 1

    def test_storage_failure_does_not_abort_load(self, app):
        """Storage hydration failure must not block auth/login flow.

        Source: ttrss/include/functions.php lines 818-828 — PHP has no error handling
                around load_data(); Python wraps it defensively.
        """
        from ttrss.plugins.loader import load_user_plugins

        with app.app_context():
            with patch("ttrss.prefs.ops.get_user_pref", return_value="some_plugin"):
                with patch("ttrss.plugins.loader._load_plugin", return_value=True):
                    with patch("ttrss.plugins.storage.load_plugin_data",
                               side_effect=Exception("storage error")):
                        # Must not raise
                        load_user_plugins(owner_uid=1)

    def test_empty_enabled_plugins_skips_load(self, app):
        """load_user_plugins exits early when _ENABLED_PLUGINS pref is empty.

        Source: ttrss/include/functions.php:820 — guard on empty get_pref result
        """
        from ttrss.plugins.loader import load_user_plugins

        with app.app_context():
            with patch("ttrss.prefs.ops.get_user_pref", return_value=""):
                with patch("ttrss.plugins.loader._load_plugin") as mock_load:
                    load_user_plugins(owner_uid=1)

        mock_load.assert_not_called()

    def test_unavailable_prefs_skips_load(self, app):
        """load_user_plugins exits gracefully when prefs.ops raises.

        Source: ttrss/include/functions.php:820 — Python guards against prefs.ops failure
        """
        from ttrss.plugins.loader import load_user_plugins

        with app.app_context():
            with patch("ttrss.prefs.ops.get_user_pref",
                       side_effect=Exception("db error")):
                with patch("ttrss.plugins.loader._load_plugin") as mock_load:
                    # Must not raise
                    load_user_plugins(owner_uid=1)

        mock_load.assert_not_called()
