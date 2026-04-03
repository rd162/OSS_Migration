"""ttrss_tags — article tags (spec/02-database.md, R04)."""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssTag(Base):
    __tablename__ = "ttrss_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_uid: Mapped[int] = mapped_column(Integer, nullable=False)
    tag_name: Mapped[str] = mapped_column(String(250), nullable=False)
    post_int_id: Mapped[int] = mapped_column(Integer, nullable=False)
