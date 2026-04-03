"""
ttrss_archived_feeds — historical record of feeds a user was subscribed to.
Retained after unsubscription so that ttrss_user_entries.orig_feed_id can still
reference the origin feed for articles ingested before unsubscription.

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_archived_feeds, lines 110-114)
        + ttrss/include/functions.php:archive_feed (feed archival on unsubscribe)
        + ttrss/classes/feeds.php:Feeds::unsubscribeFeed (lines ~200-240)

Columns present: ALL 5 columns from PHP schema.
FK: owner_uid → ttrss_users(id) ON DELETE CASCADE
    Referenced by: ttrss_user_entries.orig_feed_id ON DELETE SET NULL
Note: PK is plain integer (not serial) — PHP inserts the old feed id explicitly.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_archived_feeds, lines 110-114)
class TtRssArchivedFeed(Base):
    """
    Archived feed record — persisted after a user unsubscribes so that
    previously-ingested articles retain a reference to their origin feed.
    """

    __tablename__ = "ttrss_archived_feeds"

    # Source: schema line 110 — id integer not null primary key (NOT serial — explicit insert)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # Source: schema line 111 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 112 — title varchar(200) not null
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Source: schema line 113 — feed_url text not null
    feed_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 114 — site_url varchar(250) not null default ''
    site_url: Mapped[str] = mapped_column(String(250), nullable=False, default="")
