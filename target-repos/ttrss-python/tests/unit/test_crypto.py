"""
Pure function tests for ttrss.crypto.fernet (ADR-0009, R11, AR11).
Uses a minimal Flask app context with a test Fernet key.
No database required.
AR07-compliant: no SQLite used; no DB needed for Fernet round-trip tests.
"""
import pytest
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask

from ttrss.crypto.fernet import fernet_decrypt, fernet_encrypt


@pytest.fixture(scope="module")
def crypto_app():
    """Minimal Flask app context providing FERNET config — no DB, no Redis required."""
    app = Flask("test_crypto")
    app.config["FERNET"] = Fernet(Fernet.generate_key())
    return app


def test_round_trip(crypto_app):
    with crypto_app.app_context():
        plaintext = "mysecretfeedpassword"
        token = fernet_encrypt(plaintext)
        assert token != plaintext
        assert fernet_decrypt(token) == plaintext


def test_empty_string_round_trip(crypto_app):
    with crypto_app.app_context():
        token = fernet_encrypt("")
        assert fernet_decrypt(token) == ""


def test_unicode_round_trip(crypto_app):
    with crypto_app.app_context():
        plaintext = "pässwörد123"
        token = fernet_encrypt(plaintext)
        assert fernet_decrypt(token) == plaintext


def test_token_is_ascii(crypto_app):
    """Fernet tokens must be ASCII-safe for storage in a Text column."""
    with crypto_app.app_context():
        token = fernet_encrypt("password")
        assert token.isascii(), "Fernet token must be ASCII-safe for DB storage"


def test_wrong_key_raises_invalid_token(crypto_app):
    """Different Fernet key must not decrypt a token from another key."""
    with crypto_app.app_context():
        token = fernet_encrypt("secret")

    other_app = Flask("other_test_crypto")
    other_app.config["FERNET"] = Fernet(Fernet.generate_key())
    with other_app.app_context():
        with pytest.raises(InvalidToken):
            fernet_decrypt(token)


def test_no_fernet_configured_raises():
    """RuntimeError if FERNET is not configured (missing FEED_CRYPT_KEY)."""
    app = Flask("unconfigured")
    app.config["FERNET"] = None
    with app.app_context():
        with pytest.raises(RuntimeError, match="FERNET not configured"):
            fernet_encrypt("test")
