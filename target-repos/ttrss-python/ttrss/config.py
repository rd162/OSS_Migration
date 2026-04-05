"""
Application configuration (R03, ADR-0002, AR01).
All values read from environment variables via os.environ.get().
Set env vars BEFORE importing this module (Config class attributes are
evaluated at class definition / import time).

Inferred from: ttrss/config.php-dist (TTRSS_SELF_URL_PATH, DB_HOST, DB_NAME, DB_PASS,
               SESSION_COOKIE_LIFETIME, SESSION_CHECK_ADDRESS, FEED_CRYPT_KEY, etc.)
               Adapted for 12-factor env var pattern — no static PHP constants.
# Inferred from: ttrss/include/sanity_config.php (config validation constants — merged into Config class)
# Eliminated: ttrss/classes/db/mysql.php, ttrss/classes/db/mysqli.php — MySQL DB_TYPE dropped (ADR-0003)
New: Config class with os.environ.get() (no direct PHP equivalent)
"""
import os

from redis import Redis


# Inferred from: ttrss/config.php-dist (all DEFINE constants), adapted for Flask + 12-factor
class Config:
    """Production / development configuration."""

    # New: Flask requires SECRET_KEY for session signing — no PHP equivalent
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")

    # Inferred from: ttrss/config.php-dist:DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_TYPE (lines 6-11)
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "")
    # New: Flask-SQLAlchemy setting — disables modification tracking for performance
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # New: SQLAlchemy pool_pre_ping ensures stale connections are recycled
    SQLALCHEMY_ENGINE_OPTIONS: dict = {"pool_pre_ping": True}

    # Inferred from: ttrss/config.php-dist:FEED_CRYPT_KEY (line 27, same constant name)
    # Stored as bytes for Fernet() constructor (ADR-0009)
    FEED_CRYPT_KEY: bytes = os.environ.get("FEED_CRYPT_KEY", "").encode()

    # Flask-Session — Redis backend (ADR-0007, R07, CG-07)
    # Inferred from: ttrss/include/sessions.php (PHP native sessions replaced by Redis)
    # New: SESSION_TYPE="redis" — PHP used custom DB-backed sessions (ttrss_sessions table)
    SESSION_TYPE: str = "redis"
    SESSION_REDIS: Redis = Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    )
    # New: session signing prevents session ID forgery (no PHP equivalent)
    SESSION_USE_SIGNER: bool = True
    # New: HttpOnly prevents JS access to session cookie (spec/06-security.md F10)
    SESSION_COOKIE_HTTPONLY: bool = True
    # New: SameSite=Lax prevents CSRF via cross-origin requests (spec/06-security.md)
    SESSION_COOKIE_SAMESITE: str = "Lax"
    # Inferred from: ttrss/config.php-dist:SESSION_COOKIE_LIFETIME (line 144, default 86400)
    # Flask uses PERMANENT_SESSION_LIFETIME (timedelta), not SESSION_COOKIE_LIFETIME.
    PERMANENT_SESSION_LIFETIME: int = int(
        os.environ.get("SESSION_COOKIE_LIFETIME", "86400")
    )

    # Flask-WTF CSRF (R13, ADR-0002)
    # New: CSRF tokens replace PHP custom uniqid() tokens (spec/06-security.md F6)
    WTF_CSRF_ENABLED: bool = True
    # New: X-CSRFToken header enables CSRF for AJAX RPC calls (backend.php equivalent)
    WTF_CSRF_HEADERS: list = ["X-CSRFToken", "X-CSRF-Token"]

    # Inferred from: ttrss/config.php-dist (ICONS_DIR / ICONS_URL PHP constants)
    # PHP: define("ICONS_DIR", "feed-icons"); define("ICONS_URL", "feed-icons");
    ICONS_DIR: str = os.environ.get("TTRSS_ICONS_DIR", "feed-icons")
    ICONS_URL: str = os.environ.get("TTRSS_ICONS_URL", "feed-icons")

    # New: Flask-Limiter toggle — read from env so `RATELIMIT_ENABLED=False flask run` works.
    # Prevents rate-limit false-positives in development and testing.
    RATELIMIT_ENABLED: bool = os.environ.get("RATELIMIT_ENABLED", "true").lower() != "false"

    # New: HTTPS redirect toggle for Talisman.
    # Default False: apps behind a reverse proxy should let the proxy handle HTTPS.
    # Set FORCE_HTTPS=true only when Flask is directly internet-facing without a proxy.
    FORCE_HTTPS: bool = os.environ.get("FORCE_HTTPS", "false").lower() == "true"
