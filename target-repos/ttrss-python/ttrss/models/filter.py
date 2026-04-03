"""
Filter system tables: reference types, user-owned filter rules, and filter actions.

Source: ttrss/schema/ttrss_schema_pgsql.sql
  ttrss_filter_types        (lines 188-190)  — 7 seed rows (lines 192-198)
  ttrss_filter_actions      (lines 204-206)  — 8 seed rows (lines 208-230)
  ttrss_filters2            (lines 232-238)
  ttrss_filters2_rules      (lines 240-247)
  ttrss_filters2_actions    (lines 249-252)

Operating code:
  ttrss/classes/pref/filters.php  (filter CRUD UI)
  ttrss/include/rssfuncs.php      (filter evaluation during feed update)

FK ordering within this module:
  filter_types (L0) + filter_actions (L0) → filters2 (L2) → filters2_rules (L3) + filters2_actions (L3)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_filter_types, lines 188-190)
# Seed data: 7 rows (lines 192-198) — title, content, both, link, date, author, tag
class TtRssFilterType(Base):
    """
    Reference table for filter match types (title, content, both, link, date, author, tag).
    Source: ttrss/classes/pref/filters.php (filter type dropdown)
    """

    __tablename__ = "ttrss_filter_types"

    # Source: schema line 188 — id integer not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # Source: schema line 189 — name varchar(120) unique not null
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # Source: schema line 190 — description varchar(250) not null unique
    description: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_filter_actions, lines 204-206)
# Seed data: 8 rows (lines 208-230) — filter, catchup, mark, tag, publish, score, label, stop
class TtRssFilterAction(Base):
    """
    Reference table for filter action types (delete, mark read, star, tag, publish, score, label, stop).
    Source: ttrss/classes/pref/filters.php (filter action dropdown)
    """

    __tablename__ = "ttrss_filter_actions"

    # Source: schema line 204 — id integer not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # Source: schema line 205 — name varchar(120) unique not null
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # Source: schema line 206 — description varchar(250) not null unique
    description: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_filters2, lines 232-238)
class TtRssFilter2(Base):
    """
    User-owned filter rule group. Each filter has N rules (ttrss_filters2_rules)
    and N actions (ttrss_filters2_actions). match_any_rule=True means OR logic
    across rules; False means AND.
    Source: ttrss/classes/pref/filters.php:Pref_Filters (CRUD)
           ttrss/include/rssfuncs.php (filter evaluation during feed update)
    """

    __tablename__ = "ttrss_filters2"

    # Source: schema line 232 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 233 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 234 — match_any_rule boolean not null default false
    match_any_rule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 235 — inverse boolean not null default false
    inverse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 236 — title varchar(250) not null default ''
    title: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 237 — order_id integer not null default 0
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 238 — enabled boolean not null default true
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_filters2_rules, lines 240-247)
class TtRssFilter2Rule(Base):
    """
    Individual filter rule condition. Matches a regex against article content
    of the specified filter_type. Optionally scoped to a feed or category.
    Source: ttrss/include/rssfuncs.php (filter rule evaluation, regex matching)
    """

    __tablename__ = "ttrss_filters2_rules"

    # Source: schema line 240 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 241 — filter_id integer not null references ttrss_filters2(id) on delete cascade
    filter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_filters2.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 242 — reg_exp varchar(250) not null
    reg_exp: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 243 — inverse boolean not null default false
    inverse: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 244 — filter_type integer not null references ttrss_filter_types(id)
    filter_type: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_filter_types.id"), nullable=False
    )
    # Source: schema line 245 — feed_id integer references ttrss_feeds(id) on delete cascade default null
    feed_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_feeds.id", ondelete="CASCADE")
    )
    # Source: schema line 246 — cat_id integer references ttrss_feed_categories(id) on delete cascade default null
    cat_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_feed_categories.id", ondelete="CASCADE")
    )
    # Source: schema line 247 — cat_filter boolean not null default false
    cat_filter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_filters2_actions, lines 249-252)
class TtRssFilter2Action(Base):
    """
    Action to execute when a filter's rules match. action_param provides
    context (e.g., tag name for 'tag' action, score delta for 'score' action).
    Source: ttrss/include/rssfuncs.php (action dispatch after filter match)
    """

    __tablename__ = "ttrss_filters2_actions"

    # Source: schema line 249 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 250 — filter_id integer not null references ttrss_filters2(id) on delete cascade
    filter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_filters2.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 251 — action_id integer not null default 1 references ttrss_filter_actions(id) on delete cascade
    action_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ttrss_filter_actions.id", ondelete="CASCADE"),
        nullable=False,
        default=1,
    )
    # Source: schema line 252 — action_param varchar(250) not null default ''
    action_param: Mapped[str] = mapped_column(String(250), nullable=False, default="")
