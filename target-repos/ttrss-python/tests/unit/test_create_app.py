"""Tests for the Flask application factory (ttrss/__init__.py:create_app).

Inferred from: ttrss/index.php (bootstrap sequence)
               ttrss/include/autoload.php
               ttrss/include/sanity_config.php (config validation)
Adapted: Flask factory pattern — no direct PHP equivalent.
New: create_app() factory with test_config override (no PHP equivalent).
"""
from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_test_config() -> dict:
    """Minimal config dict accepted by create_app(test_config=...)."""
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": os.environ.get(
            "DATABASE_URL",
            "postgresql://ttrss_test:ttrss_test@localhost:5433/ttrss_test",
        ),
        "SECRET_KEY": "test-secret",
        "FEED_CRYPT_KEY": Fernet.generate_key(),
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
        # Suppress Flask-Session Redis requirement in test mode
        "SESSION_TYPE": "filesystem",
    }


# ---------------------------------------------------------------------------
# Test 1: create_app returns Flask app
# ---------------------------------------------------------------------------


def test_create_app_returns_flask_app():
    """create_app({'TESTING': True, ...}) returns a Flask application instance.

    Inferred from: ttrss/index.php (bootstrap) — adapted as Flask app factory (R01).
    New: factory pattern (no PHP equivalent); creates Flask instance for each test run.
    """
    from flask import Flask
    from ttrss import create_app

    app = create_app(_base_test_config())
    assert isinstance(app, Flask)


# ---------------------------------------------------------------------------
# Test 2: Missing SECRET_KEY in non-testing mode raises RuntimeError
# ---------------------------------------------------------------------------


def test_create_app_without_secret_key_raises():
    """create_app with TESTING=False and no SECRET_KEY raises RuntimeError.

    Source: ttrss/include/sanity_config.php — PHP validates config before serving.
    Adapted: Python raises RuntimeError to fail loudly rather than silently.
    """
    from ttrss import create_app

    cfg = _base_test_config()
    cfg["TESTING"] = False
    cfg["SECRET_KEY"] = ""  # intentionally empty

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(cfg)


# ---------------------------------------------------------------------------
# Test 3: Empty FEED_CRYPT_KEY → FERNET is None
# ---------------------------------------------------------------------------


def test_create_app_empty_feed_crypt_key_sets_fernet_none():
    """create_app({'FEED_CRYPT_KEY': b''}) stores FERNET=None in app.config.

    Source: ttrss/include/crypt.php:encrypt_string/decrypt_string
            (mcrypt replaced by Fernet, ADR-0009).
    Adapted: empty key means no Fernet instance — will fail at encrypt/decrypt,
             acceptable for skeleton; caller must provide a valid key in production.
    """
    from ttrss import create_app

    cfg = _base_test_config()
    cfg["FEED_CRYPT_KEY"] = b""

    app = create_app(cfg)
    assert app.config["FERNET"] is None


# ---------------------------------------------------------------------------
# Test 4: All blueprints registered (URL map contains expected paths)
# ---------------------------------------------------------------------------


def test_create_app_blueprints_registered():
    """All blueprints registered: /api/, /prefs/, /backend.php present in URL map.

    Source: ttrss/api/index.php + ttrss/backend.php + ttrss/prefs.php
    Adapted: PHP dispatcher files replaced by Flask blueprints (ADR-0001, R08, R13).
    """
    from ttrss import create_app

    app = create_app(_base_test_config())

    url_rules = {rule.rule for rule in app.url_map.iter_rules()}

    # /api/ blueprint
    assert any(r.startswith("/api") for r in url_rules), (
        "/api/ blueprint not registered"
    )
    # /prefs/ blueprint
    assert any(r.startswith("/prefs") for r in url_rules), (
        "/prefs/ blueprint not registered"
    )
    # backend.php blueprint
    assert any("backend.php" in r for r in url_rules), (
        "/backend.php blueprint not registered"
    )
