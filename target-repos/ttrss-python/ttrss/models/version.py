"""
ttrss_version — schema version tracking (spec/02-database.md §Schema, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_version, lines 262-264)
        + ttrss/classes/dbupdater.php:DbUpdater (schema version checking and migration)
        + ttrss/include/sanity_check.php (SCHEMA_VERSION=124 validation)
        + ttrss/include/functions.php:get_schema_version (line 988, runtime check)
        + ttrss/include/sessions.php:session_get_schema_version (line 26, session validation)

Seed data (line 264): INSERT INTO ttrss_version VALUES (124)
  → Python equivalent: Alembic migration baseline (ADR-0006).
"""
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_version, lines 262-264)
# Deviation: schema_version used as primary_key=True because SQLAlchemy requires at least one PK.
# PHP schema defines "schema_version int not null" with no PK — this is a single-row table.
# Inferred from: PHP insert pattern (only one row ever exists) — PK is safe and idempotent.
class TtRssVersion(Base):
    """
    Single-row table tracking the current schema version.
    PHP constant: SCHEMA_VERSION = 124 (functions.php line 3).
    Queried by: get_schema_version() and session_get_schema_version().
    Python: Alembic replaces the PHP version-file upgrade mechanism.
    """

    __tablename__ = "ttrss_version"

    # Source: schema line 262 — schema_version int not null
    # Inferred PK: SQLAlchemy requires a primary key; PHP schema has none (single-row table).
    schema_version: Mapped[int] = mapped_column(Integer, primary_key=True)
