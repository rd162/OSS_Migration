"""
ttrss_user_entries — per-user article state (spec/02-database.md §Articles, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_entries, lines 156-172)
        + ttrss/classes/rpc.php:RPC::mark (article marking logic)
        + ttrss/include/rssfuncs.php (user_entry creation during feed update)

Columns present: ALL 16 columns from PHP schema.
Indexes: owner_uid (line 175), ref_id (line 176), feed_id (line 177), unread (line 178).
FK: ref_id → ttrss_entries(id) ON DELETE CASCADE
    feed_id → ttrss_feeds(id) ON DELETE CASCADE
    orig_feed_id → ttrss_archived_feeds(id) ON DELETE SET NULL  (Phase 1b: FK deferred until
      ttrss_archived_feeds model exists — column present, constraint pending)
    owner_uid → ttrss_users(id) ON DELETE CASCADE
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_entries, lines 156-172)
class TtRssUserEntry(Base):
    __tablename__ = "ttrss_user_entries"

    # Source: schema line 157 — int_id serial not null primary key
    int_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 158 — ref_id integer not null references ttrss_entries(id) ON DELETE CASCADE
    ref_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Source: schema line 159 — uuid varchar(200) not null
    # UUID assigned during feed entry creation (rssfuncs.php) — NO default in PHP schema
    uuid: Mapped[str] = mapped_column(String(200), nullable=False)
    # Source: schema line 160 — feed_id int references ttrss_feeds(id) ON DELETE CASCADE
    feed_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_feeds.id", ondelete="CASCADE"), index=True
    )
    # Source: schema line 161 — orig_feed_id integer references ttrss_archived_feeds(id) ON DELETE SET NULL
    # Note: FK to ttrss_archived_feeds deferred to Phase 1b (table not yet modeled).
    # Column is present to match schema; FK constraint will be added with archived_feeds model.
    orig_feed_id: Mapped[Optional[int]] = mapped_column(Integer)
    # Source: schema line 162 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Source: schema line 163 — marked boolean not null default false
    # "Starred" state — toggled via RPC::mark (rpc.php line 131)
    marked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 164 — published boolean not null default false
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 165 — tag_cache text not null
    # Denormalized comma-separated tag list (see ttrss_tags for normalized).
    # PHP schema: NOT NULL, no default — application must supply value at insert time.
    tag_cache: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 166 — label_cache text not null
    # Denormalized JSON label list (see ttrss_user_labels2 for normalized).
    # PHP schema: NOT NULL, no default — application must supply value at insert time.
    label_cache: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 167 — last_read timestamp (nullable)
    last_read: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 168 — score int not null default 0
    # Article relevance score — modified by filter actions (filter_actions id=6)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 169 — last_marked timestamp (nullable)
    last_marked: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 170 — last_published timestamp (nullable)
    last_published: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 171 — note text (nullable)
    # User-added annotation on article (see API updateArticle note field)
    note: Mapped[Optional[str]] = mapped_column(Text)
    # Source: schema line 172 — unread boolean not null default true
    unread: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
