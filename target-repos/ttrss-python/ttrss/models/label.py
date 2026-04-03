"""ttrss_labels2 and ttrss_user_labels2 — labels and label-article mapping (spec/02-database.md, R04)."""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssLabel2(Base):
    __tablename__ = "ttrss_labels2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_uid: Mapped[int] = mapped_column(Integer, nullable=False)
    caption: Mapped[str] = mapped_column(String(250), nullable=False)
    fg_color: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    bg_color: Mapped[str] = mapped_column(String(10), nullable=False, default="")


class TtRssUserLabel2(Base):
    """Label-to-article assignment (tightly coupled to TtRssLabel2 — co-located by design)."""

    __tablename__ = "ttrss_user_labels2"

    label_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(Integer, primary_key=True)
