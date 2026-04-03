"""
ttrss_sessions — PHP session storage table (varchar PK, text data, integer expire).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_sessions, lines 375-377)
        + ttrss/include/sessions.php (PHP session handler: open/close/read/write/destroy/gc)

Columns present: ALL 3 columns from PHP schema.
Index: expire (line 379)
No FK constraints.

Note: In the Python migration, sessions are managed by Flask-Login + Redis (ADR-0007).
This SQL table is retained for schema completeness and potential PHP→Python session
migration during the transition period. Flask does NOT read/write this table.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_sessions, lines 375-377)
# Inferred from: ttrss/include/sessions.php (PHP session handler)
# Note: Flask-Login + Redis (ADR-0007) handles sessions in Python — this table is for
# schema completeness and PHP migration compatibility only.
class TtRssSession(Base):
    """
    PHP session storage. PK is session ID (varchar), not serial.
    Retained for schema completeness; Python uses Redis sessions per ADR-0007.
    """

    __tablename__ = "ttrss_sessions"
    __table_args__ = (
        # Source: schema line 379 — ttrss_sessions_expire_index
        Index("ttrss_sessions_expire_index", "expire"),
    )

    # Source: schema line 375 — id varchar(250) unique not null primary key
    id: Mapped[str] = mapped_column(String(250), primary_key=True)
    # Source: schema line 376 — data text
    data: Mapped[Optional[str]] = mapped_column(Text)
    # Source: schema line 377 — expire integer not null
    expire: Mapped[int] = mapped_column(Integer, nullable=False)
