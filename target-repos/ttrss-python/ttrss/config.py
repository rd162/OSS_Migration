"""
Application configuration (R03, ADR-0002, AR01).
All values read from environment variables via os.environ.get().
Set env vars BEFORE importing this module (Config class attributes are
evaluated at class definition / import time).
"""
import os

from redis import Redis


class Config:
    """Production / development configuration."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {"pool_pre_ping": True}

    # Feed credential Fernet key (ADR-0009) — stored as bytes for Fernet()
    FEED_CRYPT_KEY: bytes = os.environ.get("FEED_CRYPT_KEY", "").encode()

    # Flask-Session — Redis backend (ADR-0007, R07, CG-07)
    SESSION_TYPE: str = "redis"
    SESSION_REDIS: Redis = Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    )
    SESSION_USE_SIGNER: bool = True   # R07 — prevents session ID forgery
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_LIFETIME: int = int(
        os.environ.get("SESSION_COOKIE_LIFETIME", "86400")
    )

    # Flask-WTF CSRF (R13, ADR-0002)
    WTF_CSRF_ENABLED: bool = True
    # X-CSRFToken header enables CSRF for AJAX RPC calls (A-NC-05, CG-05)
    WTF_CSRF_HEADERS: list = ["X-CSRFToken", "X-CSRF-Token"]
