"""
ttrss_counters_cache — per-feed unread article count cache per user.
ttrss_cat_counters_cache — per-category unread article count cache per user.

Both tables use the same structure: (feed_id, owner_uid) as a composite logical key
(no declared PK in schema — compound uniqueness is managed by the application).

Source: ttrss/schema/ttrss_schema_pgsql.sql
        ttrss_counters_cache     (lines 116-124)
        ttrss_cat_counters_cache (lines 126-132)
        + ttrss/include/ccache.php (counter cache read/write logic)
        + ttrss/include/functions.php:ccache_update_all (lines ~1400-1450)

IMPORTANT: feed_id has NO foreign key constraint in the PostgreSQL schema.
It is a bare integer column with an index only. Do NOT add ForeignKey("ttrss_feeds.id").
This is intentional — counters_cache rows can outlive feed deletions during
housekeeping cleanup cycles (ccache.php:cleanup_counters_cache).
Verified against ttrss_schema_pgsql.sql lines 116-120: no REFERENCES clause on feed_id.

FK (actual): owner_uid → ttrss_users(id) ON DELETE CASCADE
Indexes: feed_id (counters_cache only), owner_uid (both), value (counters_cache only)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_counters_cache, lines 116-124)
class TtRssCountersCache(Base):
    """
    Feed unread count cache per user. Keyed by (feed_id, owner_uid).
    feed_id is a bare integer — no FK to ttrss_feeds (see module docstring).
    Inferred from: ttrss/include/ccache.php (counter cache management)
    """

    __tablename__ = "ttrss_counters_cache"
    __table_args__ = (
        # Source: schema line 122 — ttrss_counters_cache_feed_id_idx
        Index("ttrss_counters_cache_feed_id_idx", "feed_id"),
        # Source: schema line 123 — ttrss_counters_cache_owner_uid_idx
        Index("ttrss_counters_cache_owner_uid_idx", "owner_uid"),
        # Source: schema line 124 — ttrss_counters_cache_value_idx
        Index("ttrss_counters_cache_value_idx", "value"),
    )

    # Source: schema line 116 — feed_id integer not null (NO FK — see module docstring)
    # Inferred from: ttrss/include/ccache.php:update_cache (feed_id is a logical key,
    # not a referential integrity constraint; allows orphan rows during cleanup cycles)
    feed_id: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    # Source: schema line 117 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ttrss_users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    # Source: schema line 118 — updated timestamp not null
    updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Source: schema line 119 — value integer not null default 0
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_cat_counters_cache, lines 126-132)
class TtRssCatCountersCache(Base):
    """
    Category unread count cache per user. Keyed by (feed_id, owner_uid).
    Here feed_id semantically refers to a category id — the column name is
    inherited from the shared cache pattern in ccache.php.
    feed_id is a bare integer — no FK (same pattern as ttrss_counters_cache).
    Inferred from: ttrss/include/ccache.php (category counter cache management)
    """

    __tablename__ = "ttrss_cat_counters_cache"
    __table_args__ = (
        # Source: schema line 132 — ttrss_cat_counters_cache_owner_uid_idx
        Index("ttrss_cat_counters_cache_owner_uid_idx", "owner_uid"),
    )

    # Source: schema line 126 — feed_id integer not null (NO FK — see TtRssCountersCache note)
    # Inferred from: ttrss/include/ccache.php — feed_id here is a category_id in context
    feed_id: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True)
    # Source: schema line 127 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ttrss_users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    # Source: schema line 128 — updated timestamp not null
    updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Source: schema line 129 — value integer not null default 0
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
