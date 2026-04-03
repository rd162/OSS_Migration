"""
Pure function tests for ttrss.auth.password (ADR-0008, R10, AR04).
No database required — these functions operate on strings only.
AR07-compliant: AR07 prohibits SQLite as DB substitute, not the absence of a DB
when none is genuinely needed.

CG-03 regression: SHA1X salt MUST be prepended (sha1(salt+password)), not appended.
"""
import hashlib

from ttrss.auth.password import hash_password, needs_upgrade, verify_password


def test_hash_password_produces_argon2id():
    h = hash_password("testpassword")
    assert h.startswith("$argon2id$"), "hash_password must produce argon2id hash (AR04)"


def test_verify_argon2id_correct():
    h = hash_password("correcthorse")
    assert verify_password(h, "correcthorse") is True


def test_verify_argon2id_wrong():
    h = hash_password("correcthorse")
    assert verify_password(h, "wrongpassword") is False


def test_verify_sha1x_salt_prepended():
    """CG-03: SHA1X — salt MUST be prepended: sha1(salt + password)."""
    salt = "abc123salt"
    password = "hunter2"
    correct_digest = hashlib.sha1((salt + password).encode("utf-8")).hexdigest()
    stored = f"SHA1X:{salt}:{correct_digest}"
    assert verify_password(stored, password) is True


def test_verify_sha1x_salt_not_appended():
    """Regression: salt appended instead of prepended MUST NOT verify (CG-03)."""
    salt = "abc123salt"
    password = "hunter2"
    wrong_digest = hashlib.sha1((password + salt).encode("utf-8")).hexdigest()
    stored = f"SHA1X:{salt}:{wrong_digest}"
    assert verify_password(stored, password) is False, (
        "Salt-appended hash must NOT verify — salt must be prepended (CG-03)"
    )


def test_verify_sha1x_wrong_password():
    salt = "s"
    password = "correct"
    digest = hashlib.sha1((salt + password).encode()).hexdigest()
    stored = f"SHA1X:{salt}:{digest}"
    assert verify_password(stored, "wrong") is False


def test_verify_sha1_unsalted():
    """Legacy unsalted SHA1 (older TT-RSS versions)."""
    password = "legacy"
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest()
    stored = f"SHA1:{digest}"
    assert verify_password(stored, password) is True


def test_verify_sha1_unsalted_wrong():
    password = "legacy"
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest()
    stored = f"SHA1:{digest}"
    assert verify_password(stored, "wrong") is False


def test_needs_upgrade_sha1x_returns_true():
    salt = "s"
    digest = hashlib.sha1(("s" + "p").encode()).hexdigest()
    assert needs_upgrade(f"SHA1X:{salt}:{digest}") is True


def test_needs_upgrade_argon2id_returns_false():
    h = hash_password("p")
    assert needs_upgrade(h) is False


def test_verify_unknown_format_rejected():
    assert verify_password("PLAINTEXT:password", "password") is False
    assert verify_password("md5:5f4dcc3b5aa765d61d8327deb882cf99", "password") is False
    assert verify_password("", "password") is False
