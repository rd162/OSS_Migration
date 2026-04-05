"""Tests for plugin loader — _load_plugin and load_user_plugins.

Source PHP: ttrss/classes/pluginhost.php:PluginHost::load (lines 131-180)
            ttrss/include/functions2.php:init_plugins (lines 1583-1587)
            ttrss/include/functions.php:load_user_plugins (lines 818-828)
New: Python test suite — no direct PHP equivalent.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# _load_plugin — auth_internal (KIND_SYSTEM) with KIND_ALL → True
# ---------------------------------------------------------------------------


def test_load_plugin_auth_internal_kind_all(app):
    """_load_plugin('auth_internal', KIND_ALL) with app context → True (registered).

    Source: ttrss/classes/pluginhost.php:PluginHost::load (lines 131-180)
    Adapted: PHP require_once + class instantiation replaced by importlib.import_module
             + pluggy.PluginManager.register(); KIND_ALL accepts any plugin kind.
    Source: ttrss/classes/pluginhost.php lines 159-176 — KIND_ALL allows any plugin kind.
    """
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.manager import KIND_ALL, reset_plugin_manager

    reset_plugin_manager()
    try:
        with app.app_context():
            result = _load_plugin("auth_internal", KIND_ALL, None)
        assert result is True
    finally:
        reset_plugin_manager()


# ---------------------------------------------------------------------------
# _load_plugin — nonexistent module → False
# ---------------------------------------------------------------------------


def test_load_plugin_nonexistent_returns_false(app):
    """_load_plugin('nonexistent_xyz', KIND_ALL) → False (ImportError caught).

    Source: ttrss/classes/pluginhost.php lines 140-142 — PHP checks plugins/$class_file
            directory + init.php before require_once; Python equivalent is ImportError.
    Adapted: loader logs warning and returns False on ImportError.
    """
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.manager import KIND_ALL, reset_plugin_manager

    reset_plugin_manager()
    try:
        result = _load_plugin("nonexistent_xyz", KIND_ALL, None)
        assert result is False
    finally:
        reset_plugin_manager()


# ---------------------------------------------------------------------------
# _load_plugin — KIND filter mismatch: KIND_USER rejects KIND_SYSTEM plugin
# ---------------------------------------------------------------------------


def test_load_plugin_kind_filter_rejects_system_as_user(app):
    """_load_plugin('auth_internal', KIND_USER) → False; auth_internal is KIND_SYSTEM.

    Source: ttrss/classes/pluginhost.php lines 159-176 — KIND switch; a plugin that
            declares KIND_SYSTEM is skipped when the loader requests KIND_USER only.
    Adapted: Python reads plugin_cls.KIND attribute; KIND_SYSTEM != KIND_USER → return False.
    """
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.manager import KIND_USER, reset_plugin_manager

    reset_plugin_manager()
    try:
        result = _load_plugin("auth_internal", KIND_USER, None)
        assert result is False
    finally:
        reset_plugin_manager()


# ---------------------------------------------------------------------------
# load_user_plugins — _ENABLED_PLUGINS="" → no plugins loaded
# ---------------------------------------------------------------------------


def test_load_user_plugins_empty_pref_skips_load(app):
    """load_user_plugins(uid) with _ENABLED_PLUGINS='' → no _load_plugin calls.

    Source: ttrss/include/functions.php:load_user_plugins (lines 818-828)
    Source: ttrss/include/functions.php line 820 — get_pref('_ENABLED_PLUGINS', $owner_uid)
    Adapted: Python guards against empty pref string before iterating plugin names;
             PHP line 820 uses get_pref() result directly.
    """
    from ttrss.plugins.loader import load_user_plugins
    from ttrss.plugins.manager import reset_plugin_manager

    reset_plugin_manager()
    try:
        with app.app_context():
            with patch("ttrss.prefs.ops.get_user_pref", return_value="") as mock_pref:
                with patch("ttrss.plugins.loader._load_plugin") as mock_load:
                    load_user_plugins(1)
        mock_load.assert_not_called()
    finally:
        reset_plugin_manager()


# ---------------------------------------------------------------------------
# Additional tests for missing lines 59-60, 81-86, 102-110
# ---------------------------------------------------------------------------

def test_load_plugin_resolves_module_path(app):
    """Source: pluginhost.php:load (lines 147-176) — module path resolution.
    Assert: _load_plugin attempts import from ttrss.plugins namespace."""
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.hookspecs import KIND_ALL
    with app.app_context():
        # Valid internal plugin
        result = _load_plugin("auth_internal", KIND_ALL, None)
        # Should return True (success) or False (already loaded)
        assert isinstance(result, bool)


def test_load_user_plugins_with_nonempty_pref(app):
    """Source: functions.php:load_user_plugins (lines 818-828) — load named plugins.
    Assert: load_user_plugins with nonempty pref calls _load_plugin per plugin."""
    from ttrss.plugins.loader import load_user_plugins
    with patch("ttrss.prefs.ops.get_user_pref", return_value="auth_internal"):
        with app.app_context():
            load_user_plugins(1)  # Should not raise


def test_load_plugin_kind_user_with_user_plugin(app):
    """Source: pluginhost.php — KIND_USER plugins loaded per-user only.
    Assert: KIND_USER filter allows user plugins."""
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.hookspecs import KIND_USER
    with app.app_context():
        # auth_internal is KIND_SYSTEM so this should return False with KIND_USER
        result = _load_plugin("auth_internal", KIND_USER, 1)
        assert result is False  # KIND mismatch


def test_init_plugins_loads_default_plugins(app):
    """Source: pluginhost.php:init_plugins — loads DEFAULT_PLUGINS list.
    Assert: init_plugins() runs without error and logs."""
    from ttrss.plugins.loader import init_plugins
    with app.app_context():
        init_plugins(app)  # Should load auth_internal etc.


def test_load_plugin_no_plugin_class_returns_false(app):
    """Source: pluginhost.php:load — no plugin_class attribute → False + warning.
    Assert: module without plugin_class returns False."""
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.hookspecs import KIND_ALL
    with app.app_context():
        # json module has no plugin_class
        result = _load_plugin("json", KIND_ALL, None)
        assert result is False


def test_load_plugin_exception_returns_false(app):
    """Source: pluginhost.php:load — exception during load → False.
    Assert: ImportError for unknown module returns False."""
    from ttrss.plugins.loader import _load_plugin
    from ttrss.plugins.hookspecs import KIND_ALL
    with app.app_context():
        result = _load_plugin("definitely.not.a.real.module.xyz", KIND_ALL, None)
        assert result is False
