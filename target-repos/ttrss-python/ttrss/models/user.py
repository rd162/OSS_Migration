"""
ttrss_users — user accounts (spec/02-database.md §User Management, ADR-0007, ADR-0008).

Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_users, lines 40-53)
        + ttrss/plugins/auth_internal/init.php (pwd_hash/salt column semantics)
        + ttrss/classes/pref/users.php:Pref_Users::editSave (salt generation, lines 183-184)

Seed data (line 55-56): admin / SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8 (= "password")
  → Python migration: seed with argon2id hash instead (ADR-0008).

Columns present: ALL 13 columns from PHP schema (id, login, pwd_hash, last_login, access_level,
  email, full_name, email_digest, last_digest_sent, salt, twitter_oauth, otp_enabled,
  resetpass_token, created).
FK constraints: id is referenced by ttrss_feeds, ttrss_feed_categories, ttrss_user_entries,
  ttrss_tags, ttrss_labels2, ttrss_settings_profiles, ttrss_user_prefs, ttrss_access_keys,
  ttrss_plugin_storage, ttrss_error_log — all with ON DELETE CASCADE.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_users, lines 40-53)
# UserMixin: New (no PHP equivalent — Flask-Login integration for ADR-0007)
class TtRssUser(UserMixin, Base):
    """
    User account table.
    Flask-Login UserMixin provides: get_id(), is_active, is_authenticated, is_anonymous.
    R07/AR05: pwd_hash is stored here but NEVER placed in the session.
    """

    __tablename__ = "ttrss_users"

    # Source: schema line 40 — id serial not null primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Source: schema line 41 — login varchar(120) not null unique
    login: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # Source: schema line 42 — pwd_hash varchar(250) not null
    # ADR-0008: stores SHA1:, SHA1X:, MODE2:, or $argon2id$ formats
    pwd_hash: Mapped[str] = mapped_column(String(250), nullable=False)
    # Source: schema line 43 — last_login timestamp default null
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 44 — access_level integer not null default 0
    # Levels: 0=user, 10=admin (see pref/users.php:before, line 3)
    access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Source: schema line 45 — email varchar(250) not null default ''
    email: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 46 — full_name varchar(250) not null default ''
    full_name: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 47 — email_digest boolean not null default false
    email_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 48 — last_digest_sent timestamp default null
    last_digest_sent: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Source: schema line 49 — salt varchar(250) not null default ''
    # Used by MODE2 hash format: sha256(salt + password). See functions2.php:1481-1489.
    # Generated in pref/users.php:editSave (line 183): substr(bin2hex(get_random_bytes(125)), 0, 250)
    salt: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    # Source: schema line 50 — twitter_oauth text default null
    twitter_oauth: Mapped[Optional[str]] = mapped_column(Text)
    # Source: schema line 51 — otp_enabled boolean not null default false
    otp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Source: schema line 52 — resetpass_token varchar(250) default null
    resetpass_token: Mapped[Optional[str]] = mapped_column(String(250))
    # Source: schema line 53 — created timestamp default null
    created: Mapped[Optional[datetime]] = mapped_column(DateTime)
