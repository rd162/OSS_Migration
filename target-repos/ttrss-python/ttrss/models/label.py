"""
ttrss_labels2 and ttrss_user_labels2 — labels and label-article mapping
(spec/02-database.md §Tagging/Labeling, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_labels2, lines 389-394;
        table ttrss_user_labels2, lines 396-399)
        + ttrss/include/labels.php (label CRUD operations)
        + ttrss/classes/pref/labels.php:Pref_Labels (label management UI)

Columns present: ALL columns from PHP schema for both tables.
FK: ttrss_labels2.owner_uid → ttrss_users(id) ON DELETE CASCADE
    ttrss_user_labels2.label_id → ttrss_labels2(id) ON DELETE CASCADE
    ttrss_user_labels2.article_id → ttrss_entries(id) ON DELETE CASCADE

Note: LABEL_BASE_INDEX = -1024 (functions.php line 5) — virtual feed IDs for labels
  are computed as LABEL_BASE_INDEX - label_id (see include/labels.php).
"""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_labels2, lines 389-394)
class TtRssLabel2(Base):
    __tablename__ = "ttrss_labels2"

    # Source: schema line 389 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 390 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 391 — fg_color varchar(15) not null default ''
    fg_color: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    # Source: schema line 392 — bg_color varchar(15) not null default ''
    bg_color: Mapped[str] = mapped_column(String(15), nullable=False, default="")
    # Source: schema line 393 — caption varchar(250) not null
    caption: Mapped[str] = mapped_column(String(250), nullable=False)


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_labels2, lines 396-399)
class TtRssUserLabel2(Base):
    """Label-to-article assignment. Composite PK (label_id, article_id)."""

    __tablename__ = "ttrss_user_labels2"

    # Source: schema line 397 — label_id integer not null references ttrss_labels2(id) ON DELETE CASCADE
    label_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_labels2.id", ondelete="CASCADE"), primary_key=True
    )
    # Source: schema line 398 — article_id integer not null references ttrss_entries(id) ON DELETE CASCADE
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_entries.id", ondelete="CASCADE"), primary_key=True
    )
