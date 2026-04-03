"""
ttrss_enclosures — media attachments (spec/02-database.md §Articles, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_enclosures, lines 266-271)
        + ttrss/classes/feedenclosure.php:FeedEnclosure (feed parsing data class)
        + ttrss/include/rssfuncs.php (enclosure extraction during feed update)

Columns present: ALL 6 columns from PHP schema.
Index: post_id (line 273).
FK: post_id → ttrss_entries(id) ON DELETE CASCADE
"""
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_enclosures, lines 266-271)
class TtRssEnclosure(Base):
    __tablename__ = "ttrss_enclosures"

    # Source: schema line 266 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 267 — content_url text not null
    content_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 268 — content_type varchar(250) not null
    content_type: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 269 — title text not null
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 270 — duration text not null
    duration: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 271 — post_id integer references ttrss_entries(id) ON DELETE cascade NOT NULL
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
