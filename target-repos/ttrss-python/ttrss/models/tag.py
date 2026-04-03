"""
ttrss_tags — article tags (spec/02-database.md §Tagging/Labeling, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_tags, lines 254-257)
        + ttrss/include/functions2.php:format_tags_string (line 1589, tag display)
        + ttrss/classes/article.php:Article::editArticleTags (tag editing)

Columns present: ALL 4 columns from PHP schema.
Indexes: owner_uid (line 259), post_int_id (line 260).
FK: owner_uid → ttrss_users(id) ON DELETE CASCADE
    post_int_id → ttrss_user_entries(int_id) ON DELETE CASCADE
"""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_tags, lines 254-257)
class TtRssTag(Base):
    __tablename__ = "ttrss_tags"

    # Source: schema line 254 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 255 — tag_name varchar(250) not null
    tag_name: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 256 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Source: schema line 257 — post_int_id integer references ttrss_user_entries(int_id) ON DELETE CASCADE not null
    post_int_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_user_entries.int_id", ondelete="CASCADE"), nullable=False, index=True
    )
