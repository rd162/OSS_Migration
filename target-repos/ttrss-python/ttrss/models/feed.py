"""
ttrss_feeds — feed subscriptions with encrypted auth_pass (spec/02-database.md §Feed Management,
ADR-0009, ADR-0006).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds, lines 66-99)
        + ttrss/include/crypt.php:encrypt_string/decrypt_string (auth_pass encryption → Fernet)
        + ttrss/include/functions.php:add_feed (lines 1673-1738, feed subscription creation)
        + ttrss/classes/feeds.php:Feeds (feed display/management handler)

Columns present: ALL 34 columns from PHP schema.
Indexes: owner_uid (line 101), cat_id (line 102).
FK: owner_uid → ttrss_users(id) ON DELETE CASCADE
    cat_id → ttrss_feed_categories(id) ON DELETE SET NULL
    parent_feed → ttrss_feeds(id) ON DELETE SET NULL
Seed data (lines 104-108): 2 default feeds for admin user.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds, lines 66-99)
class TtRssFeed(Base):
    """
    Feed subscription record.
    auth_pass is stored Fernet-encrypted at rest (ADR-0009, R11).
    AR11: Fernet instance is NOT derived here — accessed via current_app.config["FERNET"]
    through ttrss.crypto.fernet helpers.
    """

    __tablename__ = "ttrss_feeds"

    # Source: schema line 66 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 67 — owner_uid integer not null references ttrss_users(id) on delete cascade
    owner_uid: Mapped[int] = mapped_column(
        Integer, ForeignKey("ttrss_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Source: schema line 68 — title varchar(200) not null
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Source: schema line 69 — cat_id integer default null references ttrss_feed_categories(id)
    cat_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_feed_categories.id", ondelete="SET NULL"), index=True
    )
    # Source: schema line 70 — feed_url text not null
    feed_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Source: schema line 71 — icon_url varchar(250) not null default ''
    icon_url: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 72 — update_interval integer not null default 0
    update_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 73 — purge_interval integer not null default 0
    purge_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 74 — last_updated timestamp default null
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 75 — last_error text not null default ''
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Source: schema line 76 — favicon_avg_color varchar(11) default null
    favicon_avg_color: Mapped[Optional[str]] = mapped_column(String(11))
    # Source: schema line 77 — site_url varchar(250) not null default ''
    site_url: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 78 — auth_login varchar(250) not null default ''
    auth_login: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 79 — parent_feed integer default null references ttrss_feeds(id)
    parent_feed: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ttrss_feeds.id", ondelete="SET NULL")
    )
    # Source: schema line 80 — private boolean not null default false
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 81 — auth_pass varchar(250) not null default ''
    # ADR-0009: Fernet-encrypted at rest; property getter/setter handles encrypt/decrypt.
    # Source: ttrss/include/crypt.php:encrypt_string (lines 22-29) → replaced by Fernet.
    _auth_pass: Mapped[str] = mapped_column("auth_pass", String(250), nullable=False, default="")
    # Source: schema line 82 — hidden boolean not null default false
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 83 — include_in_digest boolean not null default true
    include_in_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Source: schema line 84 — rtl_content boolean not null default false
    rtl_content: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 85 — cache_images boolean not null default false
    cache_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 86 — hide_images boolean not null default false
    hide_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 87 — cache_content boolean not null default false
    cache_content: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 88 — last_viewed timestamp default null
    last_viewed: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 89 — last_update_started timestamp default null
    last_update_started: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 90 — update_method integer not null default 0
    update_method: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 91 — always_display_enclosures boolean not null default false
    always_display_enclosures: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 92 — order_id integer not null default 0
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 93 — mark_unread_on_update boolean not null default false
    mark_unread_on_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 94 — update_on_checksum_change boolean not null default false
    update_on_checksum_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 95 — strip_images boolean not null default false
    strip_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 96 — view_settings varchar(250) not null default ''
    view_settings: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 97 — pubsub_state integer not null default 0
    pubsub_state: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 98 — favicon_last_checked timestamp default null
    favicon_last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 99 — auth_pass_encrypted boolean not null default false
    # ADR-0009: In Python all auth_pass values are Fernet-encrypted; this flag tracks
    # whether PHP-era mcrypt encryption was already applied (migration marker).
    auth_pass_encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # New: no PHP equivalent — added for httpx conditional GET support per ADR-0015.
    # Stores the ETag response header value from the last successful feed fetch.
    # Sent as If-None-Match on subsequent requests; 304 response skips parsing.
    last_etag: Mapped[Optional[str]] = mapped_column(String(250))
    # New: no PHP equivalent — added for httpx conditional GET support per ADR-0015.
    # Stores the Last-Modified response header value from the last successful fetch.
    # Sent as If-Modified-Since on subsequent requests; 304 response skips parsing.
    last_modified: Mapped[Optional[str]] = mapped_column(String(250))

    @property
    def auth_pass(self) -> str:
        """
        Decrypt feed password from Fernet-encrypted column (ADR-0009, R11).
        Source: ttrss/include/crypt.php:decrypt_string (lines 2-20) → Fernet.decrypt()
        Returns empty string if column is empty (matches PHP default '').
        """
        if not self._auth_pass:
            return ""
        from ttrss.crypto.fernet import fernet_decrypt

        return fernet_decrypt(self._auth_pass)

    @auth_pass.setter
    def auth_pass(self, value: str | None) -> None:
        """
        Encrypt feed password before writing to column (ADR-0009, R11).
        Source: ttrss/include/crypt.php:encrypt_string (lines 22-29) → Fernet.encrypt()
        Source: ttrss/classes/pref/feeds.php:916-928 — sets auth_pass_encrypted flag alongside password.
        """
        if not value:
            self._auth_pass = ""
            self.auth_pass_encrypted = False
        else:
            from ttrss.crypto.fernet import fernet_encrypt

            self._auth_pass = fernet_encrypt(value)
            # Source: pref/feeds.php:927 — auth_pass_encrypted = true when password is set
            self.auth_pass_encrypted = True
