"""
Plugin storage accessor — per-user, per-plugin persistent key-value store.

Source: ttrss/classes/pluginhost.php:PluginHost::set/get/load_data (lines 200-240)
Adapted: PHP serialize/unserialize replaced by JSON. PHP PluginHost instance methods
         replaced by module-level functions taking an explicit SQLAlchemy session.
         Content column stores a JSON-encoded dict of {key: value} pairs per plugin per user.

Usage:
    from ttrss.plugins import storage
    data = storage.get_data(session, owner_uid=1, plugin_name="my_plugin")
    storage.set_data(session, owner_uid=1, plugin_name="my_plugin", data={"key": "value"})
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_data(session: Session, owner_uid: int, plugin_name: str) -> dict[str, Any]:
    """
    Load all stored key-value pairs for (owner_uid, plugin_name).
    Returns empty dict if no storage row exists.

    Source: ttrss/classes/pluginhost.php:PluginHost::get (line 202-215)
    Adapted: PHP unserialize() replaced by json.loads(); missing row returns {}.
    """
    from ttrss.models.plugin_storage import TtRssPluginStorage

    row = (
        session.query(TtRssPluginStorage)
        .filter_by(owner_uid=owner_uid, name=plugin_name)
        .first()
    )
    if row is None:
        return {}
    try:
        return json.loads(row.content)
    except (json.JSONDecodeError, TypeError):
        logger.warning(
            "storage: malformed JSON for plugin=%r uid=%d, returning empty dict",
            plugin_name,
            owner_uid,
        )
        return {}


def set_data(
    session: Session, owner_uid: int, plugin_name: str, data: dict[str, Any]
) -> None:
    """
    Persist key-value dict for (owner_uid, plugin_name). Creates or updates the row.

    Source: ttrss/classes/pluginhost.php:PluginHost::set (lines 217-235)
    Adapted: PHP serialize() replaced by json.dumps(); upsert via ORM merge().
    Note: caller is responsible for session.commit().
    """
    from ttrss.models.plugin_storage import TtRssPluginStorage

    row = (
        session.query(TtRssPluginStorage)
        .filter_by(owner_uid=owner_uid, name=plugin_name)
        .first()
    )
    content = json.dumps(data)
    if row is None:
        session.add(
            TtRssPluginStorage(
                owner_uid=owner_uid, name=plugin_name, content=content
            )
        )
    else:
        row.content = content


def clear_data(session: Session, owner_uid: int, plugin_name: str) -> None:
    """
    Delete all stored data for (owner_uid, plugin_name).

    Source: ttrss/classes/pluginhost.php — implicit on plugin disable/uninstall.
    """
    from ttrss.models.plugin_storage import TtRssPluginStorage

    session.query(TtRssPluginStorage).filter_by(
        owner_uid=owner_uid, name=plugin_name
    ).delete()


def load_plugin_data(session: Session, pm, owner_uid: int) -> None:
    """
    Hydrate per-user storage into all registered plugins that implement load_data().
    Called by load_user_plugins() after all KIND_USER plugins are registered.

    Source: ttrss/classes/pluginhost.php:PluginHost::load_data (lines 200-240)
    Adapted: PHP calls $plugin->load_data($data) for each registered plugin;
             Python calls plugin.load_data(data) only if the method exists (optional protocol).
    """
    for name, plugin in pm.list_name_plugin():
        # Source: pluginhost.php load_data — queries ttrss_plugin_storage by plugin name + owner_uid
        data = get_data(session, owner_uid, name)
        if data and hasattr(plugin, "load_data"):
            try:
                plugin.load_data(data)
            except Exception:
                logger.warning(
                    "storage: load_data failed for plugin=%r uid=%d",
                    name,
                    owner_uid,
                    exc_info=True,
                )
