"""
TT-RSS Python — application factory (ADR-0001 Variant D-revised, ADR-0002 Flask).

Inferred from: ttrss/index.php (bootstrap sequence) + ttrss/include/autoload.php
               + ttrss/include/db.php (DB init) + ttrss/include/sessions.php (session init)
               Adapted for Flask factory pattern — no direct PHP equivalent.
New: create_app() factory with test_config override (no PHP equivalent)
# Inferred from: ttrss/include/errorhandler.php (PHP error handler registration — replaced by Python logging + structlog, ADR-0012)
# Inferred from: ttrss/include/sanity_config.php (config validation definitions — inlined in ttrss/config.py)
"""
import logging
import logging.config
import os

import structlog
from cryptography.fernet import Fernet, MultiFernet
from flask import Flask

import ttrss.models  # noqa: F401 — registers all 10 mappers with Base.metadata


def _configure_structlog() -> None:
    """
    Route existing stdlib logging.getLogger() calls through structlog processors.
    Zero modifications to existing modules — the stdlib ProcessorFormatter intercepts
    all records emitted by logging.getLogger() and re-renders them as structured output.

    New: no PHP equivalent — structlog stdlib wrapper (Phase 5a, ADR-0004 logging).
    Only called in non-test mode; test mode preserves pytest's native log capture.
    """
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # foreign_pre_chain handles records from stdlib logging.getLogger() callers
        foreign_pre_chain=shared_processors,
        processor=structlog.dev.ConsoleRenderer(colors=False),
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "root": {"handlers": [], "level": "INFO"},
        }
    )
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)


# Inferred from: ttrss/index.php (bootstrap) — adapted as Flask app factory (R01)
def create_app(test_config: dict | None = None) -> Flask:
    """
    Application factory (R01).
    test_config: optional dict to override config for tests (e.g. SQLALCHEMY_DATABASE_URI).
    """
    app = Flask(__name__)
    app.config.from_object("ttrss.config.Config")

    if test_config is not None:
        app.config.from_mapping(test_config)

    # Security: validate critical config at startup (fail loudly rather than silently).
    # Source: ttrss/include/sanity_config.php — PHP validates config before serving.
    if not app.testing:
        _configure_structlog()
        _secret = app.config.get("SECRET_KEY", "")
        if not _secret:
            raise RuntimeError(
                "SECRET_KEY must be set to a long random string. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

    # Fernet — instantiated ONCE here, stored in app.config (R11, ADR-0009, AR11).
    # MultiFernet supports key rotation per ADR-0009.
    # Source: ttrss/include/crypt.php:encrypt_string/decrypt_string (mcrypt replaced by Fernet)
    raw_key: bytes = app.config.get("FEED_CRYPT_KEY", b"")
    if raw_key:
        app.config["FERNET"] = MultiFernet([Fernet(raw_key)])
    else:
        app.config["FERNET"] = None  # will fail at encrypt/decrypt; acceptable for skeleton

    # Extensions — init_app pattern avoids circular imports (AR02)
    from ttrss.extensions import db, login_manager, sess, csrf, limiter
    from flask_talisman import Talisman  # New: security headers (spec/06-security.md F7)
    db.init_app(app)
    login_manager.init_app(app)
    sess.init_app(app)
    csrf.init_app(app)
    # Instantiated locally (not as module-level singleton) so each create_app() call
    # gets its own Talisman instance; prevents test create_app() calls from overwriting
    # force_https on the shared singleton (FLAW 1 fix).
    talisman = Talisman()
    talisman.init_app(app, content_security_policy=False, force_https=not app.testing)
    limiter.init_app(app)  # New: rate limiting; disabled in tests via RATELIMIT_ENABLED=False.

    # Blueprints — imported inside factory to prevent circular imports (AR02)
    from ttrss.blueprints.api import api_bp
    from ttrss.blueprints.backend import backend_bp
    from ttrss.blueprints.prefs import prefs_bp
    from ttrss.blueprints.public import public_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(backend_bp)
    app.register_blueprint(prefs_bp)
    app.register_blueprint(public_bp)

    from ttrss.errors import register_error_handlers
    register_error_handlers(app)

    return app
