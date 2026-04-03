"""
ttrss_entries — shared article content (spec/02-database.md §Articles, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_entries, lines 134-149)
        + ttrss/include/rssfuncs.php (feed parser writes entries)
        + ttrss/classes/article.php:Article (article display/management)

Columns present: ALL 15 columns from PHP schema.
Indexes: guid (line 151), date_entered (line 153), updated (line 154).
Note: guid is UNIQUE NOT NULL — feed deduplication depends on this constraint
  (see rssfuncs.php GUID-based duplicate checking).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_entries, lines 134-149)
class TtRssEntry(Base):
    __tablename__ = "ttrss_entries"

    # Source: schema line 134 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 135 — title text not null
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 136 — guid text not null unique
    # Critical: GUID uniqueness enforces feed deduplication (rssfuncs.php)
    guid: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    # Source: schema line 137 — link text not null
    link: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 138 — updated timestamp not null
    updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    # Source: schema line 139 — content text not null
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 140 — content_hash varchar(250) not null
    # Used for update_on_checksum_change feed option (rssfuncs.php)
    content_hash: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 141 — cached_content text (nullable)
    cached_content: Mapped[Optional[str]] = mapped_column(Text)
    # Source: schema line 142 — no_orig_date boolean not null default false
    # Set when feed parser cannot determine article date (rssfuncs.php)
    no_orig_date: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 143 — date_entered timestamp not null
    # Note: PHP schema has NO server default; application must supply value at insert time.
    date_entered: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    # Source: schema line 144 — date_updated timestamp not null
    date_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Source: schema line 145 — num_comments integer not null default 0
    num_comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 146 — comments varchar(250) not null default ''
    comments: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 147 — plugin_data text (nullable)
    # Stores plugin-injected metadata as serialized data (see plugin hook HOOK_ARTICLE_FILTER)
    plugin_data: Mapped[Optional[str]] = mapped_column(Text)
    # Source: schema line 148 — lang varchar(2) (nullable)
    # ISO 639-1 language code, detected during feed parsing
    lang: Mapped[Optional[str]] = mapped_column(String(2))
    # Source: schema line 149 — author varchar(250) not null default ''
    author: Mapped[str] = mapped_column(String(250), nullable=False, default="")
