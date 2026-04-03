"""
ttrss_entry_comments — user comments on feed articles (internal comment system).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_entry_comments, lines 180-187)
        + ttrss/classes/article.php:Article (comment display logic)
        + ttrss/classes/rpc.php:RPC::savecomment (lines ~420-450, comment save RPC)

Columns present: ALL 5 columns from PHP schema.
FK: ref_id    → ttrss_entries(id)  ON DELETE CASCADE
    owner_uid → ttrss_users(id)    ON DELETE CASCADE
Index: ref_id (line 186)
Note: The owner_uid index is commented out in the PHP schema (line 187) — not created.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_entry_comments, lines 180-185)
class TtRssEntryComment(Base):
    """
    User comment on a feed article. Linked to the shared entry record (ref_id)
    and the commenting user (owner_uid). Private flag controls visibility.
    Source: ttrss/classes/article.php:Article + ttrss/classes/rpc.php:RPC::savecomment
    """

    __tablename__ = "ttrss_entry_comments"
    __table_args__ = (
        # Source: schema line 186 — ttrss_entry_comments_ref_id_index
        # (owner_uid index at line 187 is commented out in PHP schema — intentionally omitted)
        Index("ttrss_entry_comments_ref_id_index", "ref_id"),
    )

    # Source: schema line 180 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 181 — ref_id integer not null references ttrss_entries(id) ON DELETE CASCADE
    ref_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_entries.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 182 — owner_uid integer not null references ttrss_users(id) ON DELETE CASCADE
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False
    )
    # Source: schema line 183 — private boolean not null default false
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 184 — date_entered timestamp not null
    date_entered: Mapped[datetime] = mapped_column(DateTime, nullable=False)
