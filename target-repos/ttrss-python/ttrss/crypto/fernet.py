"""
Fernet encrypt/decrypt utilities (ADR-0009, R11, AR11).

The Fernet/MultiFernet instance is NOT instantiated here.
It is created ONCE in create_app() from FEED_CRYPT_KEY env var,
stored as app.config["FERNET"] (MultiFernet for key rotation per ADR-0009),
and retrieved here via current_app.config["FERNET"].

This ensures:
- No key derivation in model code (AR11)
- No env var reads at module import time
- Testability via app fixture (pass a test Fernet in create_app(test_config=...))
"""
from flask import current_app


def fernet_encrypt(plaintext: str) -> str:
    """
    Encrypt a string using the app-level MultiFernet instance (R11, ADR-0009).
    Requires an active Flask application context.
    """
    f = current_app.config["FERNET"]
    if f is None:
        raise RuntimeError(
            "FERNET not configured. Set FEED_CRYPT_KEY environment variable."
        )
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def fernet_decrypt(token: str) -> str:
    """
    Decrypt a Fernet token using the app-level MultiFernet instance.
    Raises cryptography.fernet.InvalidToken if the token is invalid or from a different key.
    """
    f = current_app.config["FERNET"]
    if f is None:
        raise RuntimeError(
            "FERNET not configured. Set FEED_CRYPT_KEY environment variable."
        )
    return f.decrypt(token.encode("ascii")).decode("utf-8")
