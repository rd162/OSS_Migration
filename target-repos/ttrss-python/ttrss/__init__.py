"""
TT-RSS Python — application factory (ADR-0001 Variant D-revised, ADR-0002 Flask).

Inferred from: ttrss/index.php (bootstrap sequence) + ttrss/include/autoload.php
               + ttrss/include/db.php (DB init) + ttrss/include/sessions.php (session init)
               Adapted for Flask factory pattern — no direct PHP equivalent.
New: create_app() factory with test_config override (no PHP equivalent)
"""
import os

from cryptography.fernet import Fernet, MultiFernet
from flask import Flask

import ttrss.models  # noqa: F401 — registers all 10 mappers with Base.metadata


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

    # Fernet — instantiated ONCE here, stored in app.config (R11, ADR-0009, AR11).
    # MultiFernet supports key rotation per ADR-0009.
    # Source: ttrss/include/crypt.php:encrypt_string/decrypt_string (mcrypt replaced by Fernet)
    raw_key: bytes = app.config.get("FEED_CRYPT_KEY", b"")
    if raw_key:
        app.config["FERNET"] = MultiFernet([Fernet(raw_key)])
    else:
        app.config["FERNET"] = None  # will fail at encrypt/decrypt; acceptable for skeleton

    # Extensions — init_app pattern avoids circular imports (AR02)
    from ttrss.extensions import db, login_manager, sess, csrf, talisman
    db.init_app(app)
    login_manager.init_app(app)
    sess.init_app(app)
    csrf.init_app(app)
    talisman.init_app(app, content_security_policy=False, force_https=not app.testing)

    # Blueprints — imported inside factory to prevent circular imports (AR02)
    from ttrss.blueprints.api import api_bp
    from ttrss.blueprints.backend import backend_bp
    from ttrss.blueprints.public import public_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(backend_bp)
    app.register_blueprint(public_bp)

    from ttrss.errors import register_error_handlers
    register_error_handlers(app)

    return app
