"""
ttrss_feed_categories — hierarchical feed categories (spec/02-database.md §Feed Management, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feed_categories, lines 58-64)
        + ttrss/classes/pref/feeds.php:Pref_Feeds (category CRUD operations)

Columns present: ALL 6 columns from PHP schema.
FK: owner_uid → ttrss_users(id) ON DELETE CASCADE
    parent_cat → ttrss_feed_categories(id) ON DELETE SET NULL (self-referencing for hierarchy)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feed_categories, lines 58-64)
class TtRssFeedCategory(Base):
    __tablename__ = "ttrss_feed_categories"

    # Source: schema line 58 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 59 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 60 — collapsed boolean not null default false
    # UI state: whether category is collapsed in feed tree (pref/feeds.php:toggleCollapse)
    collapsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 61 — order_id integer not null default 0
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 62 — view_settings varchar(250) not null default ''
    view_settings: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 63 — parent_cat integer references ttrss_feed_categories(id) on delete set null
    parent_cat: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_feed_categories.id", ondelete="SET NULL")
    )
    # Source: schema line 64 — title varchar(200) not null
    title: Mapped[str] = mapped_column(String(200), nullable=False)
