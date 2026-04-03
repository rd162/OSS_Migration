"""
Federation tables — linked TT-RSS instances and their shared feeds.

Source: ttrss/schema/ttrss_schema_pgsql.sql
  ttrss_linked_instances   (lines 407-412)
  ttrss_linked_feeds       (lines 414-421)

Operating code: minimal — federation feature is rarely used in practice.

FK ordering: linked_instances (L1, no app FKs) → linked_feeds (L2, FK to instances)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_linked_instances, lines 407-412)
class TtRssLinkedInstance(Base):
    """
    Remote TT-RSS instance that this installation exchanges feeds with.
    Source: (federation feature — minimal PHP code, rarely used)
    """

    __tablename__ = "ttrss_linked_instances"

    # Source: schema line 407 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 408 — last_connected timestamp not null
    last_connected: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Source: schema line 409 — last_status_in integer not null
    last_status_in: Mapped[int] = mapped_column(Integer, nullable=False)
    # Source: schema line 410 — last_status_out integer not null
    last_status_out: Mapped[int] = mapped_column(Integer, nullable=False)
    # Source: schema line 411 — access_key varchar(250) not null unique
    access_key: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    # Source: schema line 412 — access_url text not null
    access_url: Mapped[str] = mapped_column(Text, nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_linked_feeds, lines 414-421)
class TtRssLinkedFeed(Base):
    """
    Feed record from a linked remote TT-RSS instance.
    Source: (federation feature — minimal PHP code, rarely used)
    """

    __tablename__ = "ttrss_linked_feeds"

    # Source: schema line 415 — feed_url text not null
    # Note: No explicit PK in schema; using (feed_url, instance_id) as composite PK.
    feed_url: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    # Source: schema line 416 — site_url text not null
    site_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 417 — title text not null
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 418 — created timestamp not null
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Source: schema line 419 — updated timestamp not null
    updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Source: schema line 420 — instance_id integer not null references ttrss_linked_instances(id) ON DELETE CASCADE
    instance_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ttrss_linked_instances.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    # Source: schema line 421 — subscribers integer not null
    subscribers: Mapped[int] = mapped_column(Integer, nullable=False)
