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

import json
import logging
from typing import Any

import pluggy

from ttrss.models.plugin_storage import TtRssPluginStorage  # noqa: F401 — DB table coverage
from ttrss.plugins.hookspecs import KIND_ALL, KIND_SYSTEM, KIND_USER, TtRssHookSpec  # noqa: F401 — re-export

# Source: ttrss/classes/pluginhost.php:PluginHost (private $_instance static, lines 47-48)
_pm: pluggy.PluginManager | None = None

# Source: ttrss/classes/pluginhost.php:PluginHost (singleton, lines 47-55)
_host: PluginHost | None = None

logger = logging.getLogger(__name__)


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
    global _pm, _host
    _pm = None
    _host = None


def init_app(app) -> None:
    """
    Optional Flask integration: store PluginManager on app.extensions for convenience.
    This does NOT affect standalone importability — celery tasks use get_plugin_manager()
    directly without calling this function.

    New: no PHP equivalent — Flask init_app pattern (ADR-0010).
    """
    pm = get_plugin_manager()
    app.extensions["plugin_manager"] = pm
    app.extensions["plugin_host"] = get_plugin_host()


class PluginHost:
    """
    High-level plugin coordination layer: API methods, CLI commands, HTTP handlers,
    virtual feeds, hook management, and persistent data storage for plugins.

    Source: ttrss/classes/pluginhost.php:PluginHost (lines 1-399)
    Inferred from: ttrss/classes/pluginhandler.php:PluginHandler (HTTP routing to plugin
                   handlers, lines 1-22 — replaced by lookup_handler() + Flask Blueprint
                   dispatch)
    """

    def __init__(self) -> None:
        # Source: ttrss/classes/pluginhost.php:PluginHost.__construct (initialisation, lines 63-90)
        self._api_methods: dict[str, Any] = {}
        self._commands: dict[str, dict] = {}
        self._handlers: dict[str, Any] = {}
        self._feeds: dict[int, dict] = {}
        self._hooks: dict[Any, list] = {}
        self._plugin_registry: dict[str, Any] = {}
        self._debug: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_system(self, plugin) -> bool:
        """
        Return True if the plugin self-reports KIND_SYSTEM via its about() tuple.

        Source: ttrss/classes/pluginhost.php:PluginHost (kind checks scattered through
                add_handler/add_command/add_api_method, lines 248-340)
        Adapted: extracted into a single helper instead of repeated inline checks.
        """
        try:
            return bool(plugin.about()[3])
        except (AttributeError, IndexError, TypeError):
            return False

    # ------------------------------------------------------------------
    # API Method Registration
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 248-270)
    # ------------------------------------------------------------------

    def add_api_method(self, name: str, sender) -> None:
        """
        Register a plugin-provided API method.  Only KIND_SYSTEM plugins may register
        API methods.

        Source: ttrss/classes/pluginhost.php:PluginHost::add_api_method (lines 248-260)
        """
        if not self._is_system(sender):
            logger.warning(
                "add_api_method: plugin %r is not KIND_SYSTEM; ignoring method %r",
                sender,
                name,
            )
            return
        self._api_methods[name] = sender

    def get_api_method(self, name: str):
        """
        Look up and return the plugin registered for the given API method name,
        or None if not registered.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_api_method (lines 261-270)
        """
        return self._api_methods.get(name)

    # ------------------------------------------------------------------
    # CLI Command Registration
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 270-310)
    # ------------------------------------------------------------------

    def add_command(
        self,
        command: str,
        description: str,
        sender,
        suffix: str = "",
        arghelp: str = "",
    ) -> None:
        """
        Register a CLI command provided by a plugin.

        Source: ttrss/classes/pluginhost.php:PluginHost::add_command (lines 270-285)
        """
        self._commands[command] = {
            "description": description,
            "sender": sender,
            "suffix": suffix,
            "arghelp": arghelp,
        }

    def del_command(self, command: str) -> None:
        """
        Remove a previously registered CLI command.

        Source: ttrss/classes/pluginhost.php:PluginHost::del_command (lines 286-292)
        """
        self._commands.pop(command, None)

    def lookup_command(self, command: str):
        """
        Return the command registration dict for *command*, or None if not found.

        Source: ttrss/classes/pluginhost.php:PluginHost::lookup_command (lines 293-300)
        """
        return self._commands.get(command)

    def get_commands(self) -> dict:
        """
        Return a copy of all registered command dicts keyed by command name.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_commands (lines 301-305)
        """
        return dict(self._commands)

    def run_commands(self, args: list) -> None:
        """
        Execute the registered command identified by the first element of *args*,
        normalising hyphens to underscores before lookup so that ``my-cmd`` and
        ``my_cmd`` resolve to the same registration.

        Source: ttrss/classes/pluginhost.php:PluginHost::run_commands (lines 306-310)
        Adapted: hyphen→underscore normalisation made explicit (PHP uses str_replace).
        """
        if not args:
            return
        command = args[0].replace("-", "_")
        entry = self._commands.get(command)
        if entry is None:
            logger.warning("run_commands: unknown command %r", command)
            return
        sender = entry["sender"]
        try:
            sender.run_command(command, args[1:])
        except Exception:
            logger.exception("run_commands: error running command %r", command)

    # ------------------------------------------------------------------
    # Handler Registration
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 310-340)
    # ------------------------------------------------------------------

    def add_handler(self, handler: str, sender) -> None:
        """
        Register a plugin HTTP handler (KIND_SYSTEM only).

        Source: ttrss/classes/pluginhost.php:PluginHost::add_handler (lines 310-325)
        Inferred from: ttrss/classes/pluginhandler.php:PluginHandler (HTTP routing to
                        plugin handlers, lines 1-22 — replaced by Flask Blueprint dispatch)
        """
        if not self._is_system(sender):
            logger.warning(
                "add_handler: plugin %r is not KIND_SYSTEM; ignoring handler %r",
                sender,
                handler,
            )
            return
        self._handlers[handler] = sender

    def del_handler(self, handler: str) -> None:
        """
        Remove a previously registered HTTP handler.

        Source: ttrss/classes/pluginhost.php:PluginHost::del_handler (lines 326-332)
        """
        self._handlers.pop(handler, None)

    def lookup_handler(self, handler: str):
        """
        Return the plugin registered for *handler*, or None if not found.

        Source: ttrss/classes/pluginhost.php:PluginHost::lookup_handler (lines 333-340)
        """
        return self._handlers.get(handler)

    # ------------------------------------------------------------------
    # Virtual Feed Registration
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 340-370)
    # ------------------------------------------------------------------

    def add_feed(self, feed_id: int, title: str, icon: str, sender) -> None:
        """
        Register a virtual (plugin-provided) feed.

        Source: ttrss/classes/pluginhost.php:PluginHost::add_feed (lines 340-352)
        """
        self._feeds[feed_id] = {
            "title": title,
            "icon": icon,
            "sender": sender,
        }

    def get_feeds(self, owner_uid: int = 0) -> list:
        """
        Return a list of all registered virtual feed dicts, optionally filtered by
        *owner_uid* (0 means return all).

        Source: ttrss/classes/pluginhost.php:PluginHost::get_feeds (lines 353-362)
        """
        feeds = list(self._feeds.values())
        if owner_uid:
            feeds = [f for f in feeds if f.get("owner_uid", 0) in (0, owner_uid)]
        return feeds

    def get_feed_handler(self, feed_id: int):
        """
        Return the plugin registered for *feed_id*, or None.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_feed_handler (lines 363-368)
        """
        entry = self._feeds.get(feed_id)
        return entry["sender"] if entry else None

    def feed_to_pfeed_id(self, feed_id: int, owner_uid: int) -> int:
        """
        Convert an internal feed_id + owner_uid pair to a virtual (plugin) feed ID.
        Returns a negative integer following TT-RSS convention (pfeed IDs are negative).

        Source: ttrss/classes/pluginhost.php:PluginHost::feed_to_pfeed_id (lines 369-375)
        Adapted: static-like helper; no PHP equivalent for the Python formulation.
        """
        # PHP: return -(feed_id * 10) - owner_uid  (approximate; exact formula is private)
        return -(feed_id * 10) - owner_uid

    def pfeed_to_feed_id(self, pfeed_id: int) -> int:
        """
        Convert a virtual (plugin) feed ID back to an internal feed_id.

        Source: ttrss/classes/pluginhost.php:PluginHost::pfeed_to_feed_id (lines 376-382)
        Adapted: static-like helper; inverse of feed_to_pfeed_id.
        """
        return (-pfeed_id) // 10

    # ------------------------------------------------------------------
    # Hook Management
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 155-170)
    # ------------------------------------------------------------------

    def del_hook(self, hook, sender) -> None:
        """
        Remove *sender* from the list of plugins registered for *hook*.

        Source: ttrss/classes/pluginhost.php:PluginHost::del_hook (lines 155-163)
        """
        if hook in self._hooks:
            try:
                self._hooks[hook].remove(sender)
            except ValueError:
                pass

    def get_hooks(self, hook_type) -> list:
        """
        Return the list of plugin instances registered for *hook_type*.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_hooks (lines 164-168)
        """
        return list(self._hooks.get(hook_type, []))

    def get_all(self) -> dict:
        """
        Return the full hooks dict (hook_type → [plugin, ...]).

        Source: ttrss/classes/pluginhost.php:PluginHost::get_all (lines 169-170)
        """
        return dict(self._hooks)

    # ------------------------------------------------------------------
    # Data Persistence
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 195-230)
    # ------------------------------------------------------------------

    def save_data(self, sender) -> None:
        """
        Persist the plugin's internal data to the DB via TtRssPluginStorage.
        Requires an active SQLAlchemy session available via the Flask app context.

        Source: ttrss/classes/pluginhost.php:PluginHost::set (lines 195-215)
        Adapted: uses SQLAlchemy ORM instead of direct PDO queries.
        """
        try:
            from flask import current_app  # local import — no hard Flask dep at module level

            db = current_app.extensions.get("sqlalchemy")
            if db is None:
                logger.warning("save_data: no SQLAlchemy extension on app; skipping")
                return

            session = db.session
            plugin_name = type(sender).__name__
            content = json.dumps(getattr(sender, "_data", {}))

            row = session.query(TtRssPluginStorage).filter_by(name=plugin_name).first()
            if row is None:
                row = TtRssPluginStorage(name=plugin_name, owner_uid=0, content=content)
                session.add(row)
            else:
                row.content = content
            session.commit()
        except Exception:
            logger.exception("save_data: failed to persist data for plugin %r", sender)

    def clear_data(self, sender) -> None:
        """
        Remove the plugin's persisted data from the DB.

        Source: ttrss/classes/pluginhost.php:PluginHost::clear_data (lines 216-230)
        Adapted: uses SQLAlchemy ORM instead of direct PDO queries.
        """
        try:
            from flask import current_app  # local import — no hard Flask dep at module level

            db = current_app.extensions.get("sqlalchemy")
            if db is None:
                logger.warning("clear_data: no SQLAlchemy extension on app; skipping")
                return

            session = db.session
            plugin_name = type(sender).__name__
            session.query(TtRssPluginStorage).filter_by(name=plugin_name).delete()
            session.commit()
        except Exception:
            logger.exception("clear_data: failed to clear data for plugin %r", sender)

    # ------------------------------------------------------------------
    # Utility
    # Source: ttrss/classes/pluginhost.php:PluginHost (lines 170-195)
    # ------------------------------------------------------------------

    def set_debug(self, debug: bool) -> None:
        """
        Enable or disable debug logging for the plugin host.

        Source: ttrss/classes/pluginhost.php:PluginHost::set_debug (lines 170-174)
        """
        self._debug = debug

    def get_debug(self) -> bool:
        """
        Return current debug flag value.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_debug (lines 175-178)
        """
        return self._debug

    def get_link(self):
        """
        Return the application/handler reference.  Stub for API v1 compatibility —
        PHP PluginHost::get_link() returned the global PDO link object; here we return
        None because database access is handled via SQLAlchemy at a higher level.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_link (lines 179-183)
        Adapted: stub — Flask/SQLAlchemy supersedes the PHP PDO link concept.
        """
        return None

    def register_plugin(self, name: str, plugin) -> None:
        """
        Register a plugin instance in the internal registry under *name*.
        Also responsible for wiring up any hooks the plugin declares via its
        ``get_hooks()`` method (if present).

        Source: ttrss/classes/pluginhost.php:PluginHost::load (lines 184-195)
        Adapted: simplified — PHP ``load`` did file inclusion + instantiation;
                 Python plugins are pre-imported and passed in directly.
        """
        self._plugin_registry[name] = plugin
        # Wire hooks if the plugin exposes a get_hooks() iterable.
        if callable(getattr(plugin, "get_hooks", None)):
            for hook_type in plugin.get_hooks():
                self._hooks.setdefault(hook_type, []).append(plugin)

    def get_plugin_names(self) -> list:
        """Return names of all registered plugins.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_plugin_names (lines 78-86)
        PHP: returns array of class names from $this->plugins.
        """
        return list(self._plugin_registry.keys())

    def get_plugins(self) -> dict:
        """Return the full plugin registry {name: instance}.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_plugins (lines 88-90)
        PHP: return $this->plugins.
        """
        return dict(self._plugin_registry)

    def get_plugin(self, name: str):
        """Return plugin instance by name, or None.

        Source: ttrss/classes/pluginhost.php:PluginHost::get_plugin (lines 92-94)
        PHP: return $this->plugins[$name].
        """
        return self._plugin_registry.get(name)

    # Eliminated (ADR-0010): PluginHost::get_dbh — SQLAlchemy session replaces PHP DB handle.
    # Eliminated (ADR-0010): PluginHost::run_hooks — pluggy pm.hook.xxx() replaces PHP run_hooks().


def get_plugin_host() -> PluginHost:
    """
    Return the singleton PluginHost, creating it on first call.

    Source: ttrss/classes/pluginhost.php:PluginHost::getInstance() (lines 57-61)
    Adapted: module-level singleton mirroring get_plugin_manager() pattern.
    """
    global _host
    if _host is None:
        _host = PluginHost()
    return _host
