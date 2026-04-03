"""
ttrss_access_keys — per-user API access keys for published/shared feed access.

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_access_keys, lines 401-405)
        + ttrss/classes/pref/feeds.php:Pref_Feeds (access key management)
        + ttrss/include/functions.php:get_feeds_from_html (uses access keys for sharing)

Columns present: ALL 5 columns from PHP schema.
FK: owner_uid → ttrss_users(id) ON DELETE CASCADE
Note: feed_id is varchar(250), NOT an integer FK to ttrss_feeds. It stores a string
identifier that can represent special feeds (negative IDs like "-1" for starred,
"-2" for published) or regular feed IDs as strings.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_access_keys, lines 401-405)
class TtRssAccessKey(Base):
    """
    API access key for published/shared feed access. Grants unauthenticated
    read access to specific feeds via a unique key.
    Source: ttrss/classes/pref/feeds.php:Pref_Feeds (key generation and management)
    """

    __tablename__ = "ttrss_access_keys"

    # Source: schema line 401 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 402 — access_key varchar(250) not null
    access_key: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 403 — feed_id varchar(250) not null
    # Note: varchar, NOT integer FK — stores string IDs including special feeds ("-1", "-2")
    feed_id: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 404 — is_cat boolean not null default false
    is_cat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 405 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
