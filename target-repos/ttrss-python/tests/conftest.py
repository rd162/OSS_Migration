"""
Test fixtures (R15, AR07, specs/12-testing-strategy.md).

AR07 (HARD PROHIBITION): No SQLite in tests.
This project has explicit prior history of mock/prod divergence that masked a
broken migration. All ORM-touching tests use real Postgres via docker-compose.test.yml.

Setup:
  docker compose -f docker-compose.test.yml up -d
  export TEST_DATABASE_URL=postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test
  export TEST_REDIS_URL=redis://localhost:6380/1
  pytest
"""
import os
import socket

from cryptography.fernet import Fernet

# Generate a stable test Fernet key before importing ttrss modules.
# Config class attributes are evaluated at import time, so env vars must be set first.
_TEST_FERNET_KEY = Fernet.generate_key().decode()

# Set test env vars before any ttrss import.
# setdefault preserves values already set in the environment (e.g. from CI).
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("FEED_CRYPT_KEY", _TEST_FERNET_KEY)
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test",
    ),
)
os.environ.setdefault(
    "REDIS_URL",
    os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/1"),
)

import pytest  # noqa: E402

from ttrss import create_app  # noqa: E402
from ttrss.extensions import db as _db  # noqa: E402


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Fast TCP probe — returns False in ≤timeout seconds if service is down."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


@pytest.fixture(scope="session")
def app():
    """
    Session-scoped Flask app for integration tests.
    Uses real Postgres (TEST_DATABASE_URL) — no SQLite (AR07).
    Fails fast (≤2s) if Postgres or Redis is unreachable.
    """
    test_db_url = os.environ.get(
        "TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", ""),
    )
    if not test_db_url or "sqlite" in test_db_url:
        pytest.skip(
            "TEST_DATABASE_URL must point to a real Postgres test database (AR07). "
            "Run: docker compose -f docker-compose.test.yml up -d"
        )

    test_redis_url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/1")

    # Fast-fail: probe Postgres and Redis TCP ports before attempting connections
    # that would otherwise hang for minutes on default socket timeouts.
    if not _port_open("localhost", 5433):
        pytest.skip(
            "PostgreSQL not reachable on localhost:5433. "
            "Run: docker compose -f docker-compose.test.yml up -d"
        )
    if not _port_open("localhost", 6380):
        pytest.skip(
            "Redis not reachable on localhost:6380. "
            "Run: docker compose -f docker-compose.test.yml up -d"
        )

    from redis import Redis

    # Fast-fail: verify Redis is actually responding (not just port-open).
    try:
        _test_redis = Redis.from_url(
            test_redis_url, socket_timeout=3, socket_connect_timeout=3
        )
        _test_redis.ping()
    except Exception as exc:
        pytest.skip(f"Redis not responding on {test_redis_url}: {exc}")

    # Append connect_timeout to Postgres URL so SQLAlchemy doesn't hang.
    _sep = "&" if "?" in test_db_url else "?"
    test_db_url_with_timeout = f"{test_db_url}{_sep}connect_timeout=5"

    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": test_db_url_with_timeout,
            "SESSION_REDIS": _test_redis,
            "FEED_CRYPT_KEY": _TEST_FERNET_KEY.encode(),
            "WTF_CSRF_ENABLED": False,  # disabled in test client; CSRF tested separately
        }
    )

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield _db.session
        _db.session.rollback()


@pytest.fixture(autouse=True)
def plugin_manager_with_auth():
    """
    Ensure a clean PluginManager with AuthInternal registered for every test.

    Without this fixture, pm.hook.hook_auth_user() returns None (no implementors),
    causing authenticate_user() to silently fail for any test that exercises auth.
    AuthInternal is KIND_SYSTEM and does not require an owner_uid to load.

    New: no PHP equivalent — PHP PluginHost is process-scoped; tests need clean state.
    Source: ttrss/plugins/auth_internal/init.php (Auth_Internal class)
            ttrss/classes/pluginhost.php:reset_plugins (test helper not present in PHP)
    """
    from ttrss.plugins.auth_internal import AuthInternal
    from ttrss.plugins.manager import get_plugin_manager, reset_plugin_manager

    reset_plugin_manager()
    pm = get_plugin_manager()
    pm.register(AuthInternal(), name="auth_internal")
    yield
    reset_plugin_manager()
