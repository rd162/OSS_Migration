"""ttrss_feeds — feed subscriptions with encrypted auth_pass (spec/02-database.md, R04, ADR-0009, R11)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ttrss.models.base import Base


class TtRssFeed(Base):
    """
    Feed subscription record.
    auth_pass is stored Fernet-encrypted at rest (ADR-0009, R11).
    AR11: Fernet instance is NOT derived here — accessed via current_app.config["FERNET"]
    through ttrss.crypto.fernet helpers.
    """

    __tablename__ = "ttrss_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_uid: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    feed_url: Mapped[str] = mapped_column(String(250), nullable=False)
    site_url: Mapped[Optional[str]] = mapped_column(String(250))
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    update_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cat_id: Mapped[Optional[int]] = mapped_column(Integer)
    auth_login: Mapped[Optional[str]] = mapped_column(String(250))
    _auth_pass: Mapped[Optional[str]] = mapped_column("auth_pass", Text)
    last_error: Mapped[Optional[str]] = mapped_column(String(250))
    cache_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pubsub_state: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @property
    def auth_pass(self) -> Optional[str]:
        """Decrypt feed password from Fernet-encrypted column (ADR-0009, R11)."""
        if self._auth_pass is None:
            return None
        from ttrss.crypto.fernet import fernet_decrypt

        return fernet_decrypt(self._auth_pass)

    @auth_pass.setter
    def auth_pass(self, value: Optional[str]) -> None:
        """Encrypt feed password before writing to column (ADR-0009, R11)."""
        if value is None:
            self._auth_pass = None
        else:
            from ttrss.crypto.fernet import fernet_encrypt

            self._auth_pass = fernet_encrypt(value)
