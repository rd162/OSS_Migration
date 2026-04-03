"""ttrss_version — schema version tracking (spec/02-database.md, R04, CG-01)."""
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssVersion(Base):
    """
    Single-row table tracking the current schema version.
    Used by sanity checks and Alembic migration baseline.
    See spec/02-database.md: "Schema version: 124 (tracked in ttrss_version.schema_version)".
    """

    __tablename__ = "ttrss_version"

    schema_version: Mapped[int] = mapped_column(Integer, primary_key=True)
