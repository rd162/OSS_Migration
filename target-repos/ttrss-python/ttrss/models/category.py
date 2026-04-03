"""ttrss_feed_categories — hierarchical feed categories (spec/02-database.md, R04)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssFeedCategory(Base):
    __tablename__ = "ttrss_feed_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_uid: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    parent_cat: Mapped[Optional[int]] = mapped_column(Integer)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
