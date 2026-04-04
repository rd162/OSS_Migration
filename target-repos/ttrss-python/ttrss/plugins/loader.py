"""
Plugin discovery and loading — importlib directory scan.

Source: ttrss/include/functions2.php:init_plugins (lines 1583-1587)
        ttrss/include/functions.php:load_user_plugins (lines 818-828)
        ttrss/classes/pluginhost.php:PluginHost::load (lines 131-180)
Adapted: PHP directory scan + class instantiation replaced by importlib + pluggy.register().
         KIND constants map directly (pluginhost.php:43-45): KIND_ALL=1, KIND_SYSTEM=2, KIND_USER=3.
"""
from __future__ import annotations

import importlib
import logging
import os
from typing import Optional

from ttrss.plugins.manager import KIND_ALL, KIND_USER, get_plugin_manager

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.

# Source: ttrss/config.php-dist line 200 — define('PLUGINS', 'auth_internal, note, updater')
# Adapted: environment variable replaces PHP constant for 12-factor config.  Default
#          value is 'auth_internal' only; note and updater plugins are not yet ported.
_DEFAULT_PLUGINS = os.environ.get("TTRSS_PLUGINS", "auth_internal")  # Source: ttrss/config.php-dist line 200. Adapted: env var replaces PHP define; only 'auth_internal' by default.


def _load_plugin(name: str, kind: int, owner_uid: Optional[int] = None) -> bool:
    """
    Import plugin module ``ttrss.plugins.<name>`` and register with PluginManager.

    Source: ttrss/classes/pluginhost.php:PluginHost::load (lines 131-180)
    Adapted: PHP require_once + class instantiation replaced by importlib.import_module
             + pluggy.PluginManager.register().  KIND filtering guards user-only plugins
             from being loaded as system plugins and vice versa.
    Note: ttrss/classes/pluginhost.php line 134 — $this->owner_uid = (int) $owner_uid.
          Python does not assign owner_uid onto the PluginManager; owner_uid is passed
          through for logging only.  Per-user context is available via Flask's session.
    Note: ttrss/classes/pluginhost.php lines 140-142 — PHP checks that plugins/$class_file
          is a directory and that init.php exists before require_once.  Python performs
          neither filesystem check; importlib raises ImportError if the module is absent,
          which is caught and logged below.
    """
    pm = get_plugin_manager()
    module_path = f"ttrss.plugins.{name}"

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:  # Source: ttrss/classes/pluginhost.php lines 140-142 — PHP checks init.php exists; Python equivalent is ImportError on missing module.
        logger.warning("loader: cannot import plugin %r: %s", name, exc)
        return False

    # Source: ttrss/classes/pluginhost.php lines 147-148 — class_exists($class) &&
    #         is_subclass_of($class, "Plugin") after require_once of init.php.
    # Adapted: PHP class-existence check replaced by module attribute lookup.  Python
    #          plugins must expose a ``plugin_class`` attribute (preferred) or a class
    #          named ``Plugin`` as the entry point.
    plugin_cls = getattr(module, "plugin_class", None) or getattr(module, "Plugin", None)
    if plugin_cls is None:  # Source: ttrss/classes/pluginhost.php lines 147-148 — class_exists() + is_subclass_of() gate; non-conforming class skipped.
        logger.warning("loader: plugin %r exposes no plugin_class / Plugin", name)
        return False

    # Note: ttrss/classes/pluginhost.php lines 150-155 — $plugin->api_version() < API_VERSION check not reproduced.
    #       Python plugins do not yet implement an api_version() protocol; all registered
    #       plugins are assumed compatible.

    # KIND guard — skip if plugin's declared kind doesn't match the requested load kind.
    # Source: ttrss/classes/pluginhost.php lines 159-176 — KIND_SYSTEM/KIND_USER/KIND_ALL
    #         switch using is_system($plugin) (which reads $plugin->about()[3]).
    # Adapted: PHP is_system() introspects about()[3]; Python uses a class attribute KIND
    #          set by each plugin module (KIND_USER by default).  This avoids requiring
    #          plugins to implement an about() method solely for KIND routing.
    plugin_kind = getattr(plugin_cls, "KIND", KIND_USER)
    if kind != KIND_ALL and plugin_kind != kind:  # Source: ttrss/classes/pluginhost.php lines 159-176 — KIND switch; non-matching kind is skipped.
        return False

    try:
        instance = plugin_cls()
        pm.register(instance, name=name)
        logger.debug("loader: registered plugin %r (kind=%d uid=%s)", name, plugin_kind, owner_uid)
        return True
    except ValueError:  # Adapted: pluggy raises ValueError on duplicate registration; PHP line 144 guards before instantiation (if (!isset($this->plugins[$class]))), not via exception — structurally different control flow, same idempotency intent.
        logger.debug("loader: plugin %r already registered, skipping", name)
        return True
    except Exception as exc:  # New: no PHP equivalent — defensive catch for unexpected registration errors.
        logger.error("loader: failed to register plugin %r: %s", name, exc, exc_info=True)
        return False


def init_plugins(app=None) -> None:
    """
    Load all plugins listed in TTRSS_PLUGINS env var (KIND_ALL — system + user).
    Called once at application startup.

    Source: ttrss/include/functions2.php:init_plugins (lines 1583-1587)
            → PluginHost::getInstance()->load(PLUGINS, KIND_ALL)
    Adapted: PHP PLUGINS constant replaced by TTRSS_PLUGINS env var; importlib replaces
             PHP require_once/class instantiation.
    Note: ttrss/include/functions2.php line 1586 — PHP init_plugins() returns true.
          Python returns None; the boolean return value is not used by any caller.
    """
    plugin_names = [p.strip() for p in _DEFAULT_PLUGINS.split(",") if p.strip()]
    loaded = 0
    for name in plugin_names:
        if _load_plugin(name, KIND_ALL):
            loaded += 1
    logger.info("init_plugins: loaded %d/%d plugins", loaded, len(plugin_names))

    if app is not None:  # New: no PHP equivalent — Flask app binding for plugin introspection.
        app.extensions.setdefault("loaded_plugins", plugin_names)


def load_user_plugins(owner_uid: int) -> None:
    """
    Load per-user plugins for ``owner_uid``.  Called after successful login.

    Source: ttrss/include/functions.php:load_user_plugins (lines 818-828)
            → get_pref("_ENABLED_PLUGINS", $owner_uid)
            → PluginHost::getInstance()->load($plugins, KIND_USER, $owner_uid)
            → PluginHost::getInstance()->load_data()
    Adapted: PHP PluginHost::load(..., KIND_USER) replaced by importlib + pm.register().
             load_data() equivalent (plugin storage) is not yet wired; see note below.
    Note: ttrss/include/functions.php line 819 — guard: owner_uid AND SCHEMA_VERSION >= 100.
          Python always runs schema v124 (Alembic baseline), so SCHEMA_VERSION guard is
          always true.
    Note: ttrss/include/functions.php lines 824-826 — PluginHost::load_data() persists
          and restores per-plugin storage from ttrss_plugin_storage.  The ORM model is in
          place but the load_data() call equivalent is not yet wired here.
    """
    # Source: ttrss/include/functions.php line 820 — get_pref("_ENABLED_PLUGINS", $owner_uid)
    try:
        from ttrss.prefs.ops import get_user_pref
        plugins_str = get_user_pref(owner_uid, "_ENABLED_PLUGINS")
    except Exception:  # New: no PHP equivalent — PHP line 820 calls get_pref() directly with no error handling; Python guards against prefs.ops import failure (circular import, DB unavailable).
        logger.debug("load_user_plugins: _ENABLED_PLUGINS unavailable for uid=%d", owner_uid)
        return

    if not plugins_str:  # New: no PHP equivalent — PHP line 820 uses get_pref() result directly without an empty-string guard.
        return

    # Source: ttrss/include/functions.php line 822 — PluginHost::load($plugins, KIND_USER, $owner_uid)
    # PHP PLUGINS string is comma-separated plugin names.
    plugin_names = [p.strip() for p in plugins_str.split(",") if p.strip()]
    for name in plugin_names:
        _load_plugin(name, KIND_USER, owner_uid)
