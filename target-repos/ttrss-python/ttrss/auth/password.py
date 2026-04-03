"""
Dual-hash password verification (ADR-0008, R10, AR04).

Verification order:
1. argon2id  — modern hash; new passwords and upgraded legacy passwords
2. SHA1X:<salt>:<hex>  — legacy salted SHA1 (TT-RSS PHP format)
3. SHA1:<hex>          — legacy unsalted SHA1 (older TT-RSS versions)

CG-03: SHA1X salt is PREPENDED — sha1(salt + password), NOT sha1(password + salt).
AR04: SHA1 is verify-only. All new/upgraded hashes use argon2id exclusively.
"""
import hashlib

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_ph = PasswordHasher()  # argon2id by default in argon2-cffi


def hash_password(password: str) -> str:
    """Hash a new password with argon2id. Never SHA1 for new passwords (AR04)."""
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """
    Verify password against stored hash.
    Returns True if valid, False otherwise.
    Does not modify the stored hash — call upgrade_hash() after a successful SHA1 verify.

    SHA1X salt is extracted from the stored_hash string itself (not passed separately).
    CG-03: sha1(SALT + password) — salt is PREPENDED.
    """
    if stored_hash.startswith("$argon2"):
        try:
            return _ph.verify(stored_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False

    if stored_hash.startswith("SHA1X:"):
        # Format: SHA1X:<salt>:<hex_digest>
        parts = stored_hash.split(":", 2)
        if len(parts) != 3:
            return False
        _, salt, digest = parts
        # CG-03: salt PREPENDED — sha1(salt + password)
        expected = hashlib.sha1((salt + password).encode("utf-8")).hexdigest()
        return expected == digest

    if stored_hash.startswith("SHA1:"):
        # Unsalted SHA1 (older TT-RSS)
        digest = stored_hash[5:]
        expected = hashlib.sha1(password.encode("utf-8")).hexdigest()
        return expected == digest

    return False  # unknown hash format — reject


def needs_upgrade(stored_hash: str) -> bool:
    """Return True if the stored hash should be upgraded to argon2id (ADR-0008)."""
    return not stored_hash.startswith("$argon2")
