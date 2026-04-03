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


@pytest.fixture(scope="session")
def app():
    """
    Session-scoped Flask app for integration tests.
    Uses real Postgres (TEST_DATABASE_URL) — no SQLite (AR07).
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

    from redis import Redis

    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": test_db_url,
            "SESSION_REDIS": Redis.from_url(test_redis_url),
            "FEED_CRYPT_KEY": _TEST_FERNET_KEY.encode(),
            "WTF_CSRF_ENABLED": False,  # disabled in test client; CSRF tested separately
        }
    )

    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield _db.session
        _db.session.rollback()
