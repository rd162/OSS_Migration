"""
ttrss_feedbrowser_cache — public feed directory cache for the feed browser.

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feedbrowser_cache, lines 383-386)
        + ttrss/classes/feedbrowser.php (public feed directory listing)

Columns present: ALL 4 columns from PHP schema.
No FK constraints (standalone cache table).
PK is feed_url (text), not serial.
"""
from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feedbrowser_cache, lines 383-386)
class TtRssFeedbrowserCache(Base):
    """
    Public feed directory cache — aggregates known feed URLs with subscriber counts.
    Used by the feed browser feature for discovering popular feeds.
    Source: ttrss/classes/feedbrowser.php:FeedBrowser (directory listing)
    """

    __tablename__ = "ttrss_feedbrowser_cache"

    # Source: schema line 383 — feed_url text not null primary key
    feed_url: Mapped[str] = mapped_column(Text, primary_key=True)
    # Source: schema line 384 — title text not null
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 385 — site_url text not null
    site_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 386 — subscribers integer not null
    subscribers: Mapped[int] = mapped_column(Integer, nullable=False)
