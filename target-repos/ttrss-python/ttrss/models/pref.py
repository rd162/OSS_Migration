"""
Preference system tables: type reference, section reference, preference definitions,
settings profiles, and per-user preference overrides.

Source: ttrss/schema/ttrss_schema_pgsql.sql
  ttrss_prefs_types          (lines 280-281)  — 3 seed rows (lines 283-285)
  ttrss_prefs_sections       (lines 287-289)  — 4 seed rows (lines 291-294)
  ttrss_prefs                (lines 296-300)  — ~51 seed rows (lines 302-352)
                                                 + access_level UPDATE (lines 354-362)
  ttrss_settings_profiles    (lines 275-277)
  ttrss_user_prefs           (lines 364-367)  — indexes (lines 369-371)

Operating code:
  ttrss/include/db-prefs.php    (preference read/write helpers)
  ttrss/classes/pref/prefs.php  (preference UI handler)

FK ordering: prefs_types (L0) + prefs_sections (L0)
           → prefs (L1, varchar PK)
           → settings_profiles (L2, depends on ttrss_users)
           → user_prefs (L3, depends on prefs + settings_profiles + ttrss_users)
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_prefs_types, lines 280-281)
# Seed data: 3 rows (lines 283-285) — bool(1), string(2), integer(3)
class TtRssPrefsType(Base):
    """
    Reference table for preference value data types.
    Source: ttrss/include/db-prefs.php (type coercion on pref read/write)
    """

    __tablename__ = "ttrss_prefs_types"

    # Source: schema line 280 — id integer not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # Source: schema line 281 — type_name varchar(100) not null
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_prefs_sections, lines 287-289)
# Seed data: 4 rows (lines 291-294) — General(1,0), Interface(2,1), Advanced(3,3), Digest(4,2)
class TtRssPrefsSection(Base):
    """
    Reference table for preference UI sections (General, Interface, Advanced, Digest).
    Source: ttrss/classes/pref/prefs.php (section tabs in preferences UI)
    """

    __tablename__ = "ttrss_prefs_sections"

    # Source: schema line 287 — id integer not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # Source: schema line 288 — order_id integer not null
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # Source: schema line 289 — section_name varchar(100) not null
    section_name: Mapped[str] = mapped_column(String(100), nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_prefs, lines 296-300)
# Seed data: ~51 INSERT rows (lines 302-352) + UPDATE access_level (lines 354-362)
# Note: PK is pref_name (varchar), NOT a serial integer.
class TtRssPref(Base):
    """
    System preference definitions. Each row defines one preference with its
    default value, data type, and UI section. Per-user overrides live in
    ttrss_user_prefs.
    Source: ttrss/include/db-prefs.php:get_pref (reads def_value as fallback)
    """

    __tablename__ = "ttrss_prefs"
    __table_args__ = (
        # Source: schema line 301 — ttrss_prefs_pref_name_idx (redundant with PK but present in DDL)
        Index("ttrss_prefs_pref_name_idx", "pref_name"),
    )

    # Source: schema line 296 — pref_name varchar(250) not null primary key
    pref_name: Mapped[str] = mapped_column(String(250), primary_key=True)
    # Source: schema line 297 — type_id integer not null references ttrss_prefs_types(id)
    type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_prefs_types.id"), nullable=False
    )
    # Source: schema line 298 — section_id integer not null default 1 references ttrss_prefs_sections(id)
    section_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_prefs_sections.id"), nullable=False, default=1
    )
    # Source: schema line 299 — access_level integer not null default 0
    # Updated to 1 for 8 prefs in lines 354-362
    access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 300 — def_value text not null
    def_value: Mapped[str] = mapped_column(Text, nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_settings_profiles, lines 275-277)
class TtRssSettingsProfile(Base):
    """
    Named preference profile — users can create multiple profiles and switch between them.
    Source: ttrss/classes/pref/prefs.php:Pref_Prefs (profile management UI)
    """

    __tablename__ = "ttrss_settings_profiles"

    # Source: schema line 275 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 276 — title varchar(250) not null
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 277 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_prefs, lines 364-367)
# Note: PHP schema has NO declared PK. The logical key is (owner_uid, pref_name, profile)
# where profile=NULL means the default (no-profile) setting.
# Bug fix: original Python model put profile in primary_key=True, which Postgres enforces as
# NOT NULL — making profile=NULL impossible and breaking set_user_pref() for the default profile.
# Fix: PK is (owner_uid, pref_name) only; profile is a regular nullable column.
# Consequence: only one row per (owner_uid, pref_name) is supported via session.merge(),
# which covers 100% of current app usage (default profile only). Multi-profile support
# would require explicit SQL or a separate UNIQUE NULLS NOT DISTINCT index (Postgres 15+).
class TtRssUserPref(Base):
    """
    Per-user preference override. If absent, the system default from ttrss_prefs.def_value applies.
    Source: ttrss/include/db-prefs.php:get_pref (user override lookup)
           ttrss/include/db-prefs.php:set_pref (user override write)
    """

    __tablename__ = "ttrss_user_prefs"
    __table_args__ = (
        # Source: schema line 369 — ttrss_user_prefs_owner_uid_index
        Index("ttrss_user_prefs_owner_uid_index", "owner_uid"),
        # Source: schema line 370 — ttrss_user_prefs_pref_name_idx
        Index("ttrss_user_prefs_pref_name_idx", "pref_name"),
    )

    # Source: schema line 364 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ttrss_users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    # Source: schema line 365 — pref_name varchar(250) not null references ttrss_prefs(pref_name) ON DELETE CASCADE
    pref_name: Mapped[str] = mapped_column(
        String(250),
        ForeignKey("ttrss_prefs.pref_name", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    # Source: schema line 366 — profile integer references ttrss_settings_profiles(id) ON DELETE CASCADE
    # Nullable — NULL means the default (no-profile) setting.
    # Not part of PK: Postgres PK columns are implicitly NOT NULL, which would forbid profile=NULL.
    profile: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ttrss_settings_profiles.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    # Source: schema line 367 — value text not null
    value: Mapped[str] = mapped_column(Text, nullable=False)
