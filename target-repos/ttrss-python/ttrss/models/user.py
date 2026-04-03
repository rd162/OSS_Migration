"""ttrss_users — user accounts (spec/02-database.md, R04, ADR-0007)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssUser(UserMixin, Base):
    """
    User account table.
    Flask-Login UserMixin provides: get_id(), is_active, is_authenticated, is_anonymous.
    R07/AR05: pwd_hash is stored here but NEVER placed in the session.
    """

    __tablename__ = "ttrss_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    pwd_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    access_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    salt: Mapped[Optional[str]] = mapped_column(String(256))
    otp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
