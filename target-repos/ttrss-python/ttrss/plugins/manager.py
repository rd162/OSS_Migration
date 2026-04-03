"""
PluginManager singleton — accessible from Flask app AND Celery workers (R8, ADR-0010).

Source: ttrss/classes/pluginhost.php:PluginHost (singleton pattern, lines 47-55)
        ttrss/classes/pluginhost.php:getInstance() (lines 57-61)
        Adapted: pluggy.PluginManager replaces PHP PluginHost global singleton.

get_plugin_manager() has NO Flask dependency and can be called from:
  - Flask request handlers (via app.extensions["plugin_manager"] or directly)
  - Celery task functions (import this module directly — no app context needed)

New: no PHP equivalent for pluggy integration layer.
"""
from __future__ import annotations

import pluggy

from ttrss.plugins.hookspecs import KIND_ALL, KIND_SYSTEM, KIND_USER, TtRssHookSpec  # noqa: F401 — re-export

# Source: ttrss/classes/pluginhost.php:PluginHost (private $_instance static, lines 47-48)
_pm: pluggy.PluginManager | None = None


def get_plugin_manager() -> pluggy.PluginManager:
    """
    Return the singleton PluginManager with all 24 hookspecs registered.
    Creates on first call; subsequent calls return the same instance.

    Source: ttrss/classes/pluginhost.php:getInstance() (lines 57-61)
    Adapted: module-level singleton instead of PHP static class variable.
    """
    global _pm
    if _pm is None:
        _pm = pluggy.PluginManager("ttrss")
        _pm.add_hookspecs(TtRssHookSpec)
    return _pm


def reset_plugin_manager() -> None:
    """
    Reset the singleton (for testing only).
    New: no PHP equivalent — PHP singleton is process-scoped; tests need clean state.
    """
    global _pm
    _pm = None


def init_app(app) -> None:
    """
    Optional Flask integration: store PluginManager on app.extensions for convenience.
    This does NOT affect standalone importability — celery tasks use get_plugin_manager()
    directly without calling this function.

    New: no PHP equivalent — Flask init_app pattern (ADR-0010).
    """
    pm = get_plugin_manager()
    app.extensions["plugin_manager"] = pm
