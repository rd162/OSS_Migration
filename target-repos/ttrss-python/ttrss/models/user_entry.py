"""ttrss_user_entries — per-user article state (spec/02-database.md, R04)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssUserEntry(Base):
    __tablename__ = "ttrss_user_entries"

    int_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    owner_uid: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    feed_id: Mapped[Optional[int]] = mapped_column(Integer)
    unread: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    tag_cache: Mapped[Optional[str]] = mapped_column(Text)
    label_cache: Mapped[Optional[str]] = mapped_column(Text)
    last_read: Mapped[Optional[datetime]] = mapped_column(DateTime)
    note: Mapped[Optional[str]] = mapped_column(String(250))
    orig_feed_id: Mapped[Optional[int]] = mapped_column(Integer)
