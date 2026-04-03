"""ttrss_enclosures — media attachments (spec/02-database.md, R04)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssEnclosure(Base):
    __tablename__ = "ttrss_enclosures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False)
    content_url: Mapped[Optional[str]] = mapped_column(Text)
    content_type: Mapped[Optional[str]] = mapped_column(String(250))
    title: Mapped[Optional[str]] = mapped_column(Text)
    duration: Mapped[Optional[str]] = mapped_column(String(40))
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
