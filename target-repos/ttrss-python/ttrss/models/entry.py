"""ttrss_entries — shared article content (spec/02-database.md, R04)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssEntry(Base):
    __tablename__ = "ttrss_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(Text)
    link: Mapped[Optional[str]] = mapped_column(String(250))
    content: Mapped[Optional[str]] = mapped_column(Text)
    content_hash: Mapped[Optional[str]] = mapped_column(String(250))
    cached_content: Mapped[Optional[str]] = mapped_column(Text)
    updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    date_entered: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    date_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    guid: Mapped[Optional[str]] = mapped_column(String(250))
    num_comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    author: Mapped[Optional[str]] = mapped_column(String(250))
