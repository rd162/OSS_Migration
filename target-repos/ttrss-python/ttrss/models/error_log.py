"""
ttrss_error_log — application error log stored in the database.

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_error_log, lines 428-435)
        + ttrss/classes/logger/sql.php:Logger_SQL (error handler writing to this table)

Columns present: ALL 8 columns from PHP schema.
FK: owner_uid → ttrss_users(id) ON DELETE SET NULL (nullable — system errors have no owner)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_error_log, lines 428-435)
class TtRssErrorLog(Base):
    """
    Application error log — stores PHP errors with file/line context.
    owner_uid is nullable because system-level errors have no associated user.
    Source: ttrss/classes/logger/sql.php:Logger_SQL (PHP error handler)
    """

    __tablename__ = "ttrss_error_log"

    # Source: schema line 428 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 429 — owner_uid integer references ttrss_users(id) ON DELETE SET NULL
    owner_uid: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="SET NULL")
    )
    # Source: schema line 430 — errno integer not null
    errno: Mapped[int] = mapped_column(Integer, nullable=False)
    # Source: schema line 431 — errstr text not null
    errstr: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 432 — filename text not null
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 433 — lineno integer not null
    lineno: Mapped[int] = mapped_column(Integer, nullable=False)
    # Source: schema line 434 — context text not null
    context: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 435 — created_at timestamp not null
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
