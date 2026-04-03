"""
ttrss_plugin_storage — persistent key-value storage for plugins.

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_plugin_storage, lines 423-426)
        + ttrss/classes/pluginhost.php:PluginHost::set/get (storage read/write)

Columns present: ALL 4 columns from PHP schema.
FK: owner_uid → ttrss_users(id) ON DELETE CASCADE
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_plugin_storage, lines 423-426)
class TtRssPluginStorage(Base):
    """
    Per-user persistent key-value storage for plugins. Plugins store serialized
    data (JSON/PHP serialize) keyed by plugin name.
    Source: ttrss/classes/pluginhost.php:PluginHost::set/get
    """

    __tablename__ = "ttrss_plugin_storage"

    # Source: schema line 423 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 424 — name varchar(100) not null
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Source: schema line 425 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 426 — content text not null
    content: Mapped[str] = mapped_column(Text, nullable=False)
