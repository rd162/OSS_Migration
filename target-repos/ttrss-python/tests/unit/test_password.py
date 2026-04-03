"""
Pure function tests for ttrss.auth.password (ADR-0008, R10, AR04).
No database required — these functions operate on strings only.
AR07-compliant: AR07 prohibits SQLite as DB substitute, not the absence of a DB
when none is genuinely needed.

Source coverage:
  ttrss/plugins/auth_internal/init.php:Auth_Internal::authenticate (all hash format branches)
  ttrss/include/functions2.php:encrypt_password (lines 1481-1489)

PHP hash format reference (functions2.php:1481-1489):
  SHA1:<hex>    — sha1($pass), no salt
  SHA1X:<hex>   — sha1("$login:$pass"), login is the "salt", colon separator
  MODE2:<hex>   — hash('sha256', $salt . $pass), salt from ttrss_users.salt column, no separator
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


def test_verify_argon2id_malformed_hash():
    """InvalidHashError path: malformed argon2 string should return False, not raise."""
    assert verify_password("$argon2id$corrupted_data", "password") is False


def test_hash_then_verify_then_no_upgrade():
    """Round-trip: hash → verify → needs_upgrade returns False (full lifecycle)."""
    password = "round-trip-test"
    h = hash_password(password)
    assert verify_password(h, password) is True
    assert needs_upgrade(h) is False


# --- PHP seed data test (schema line 55-56) ---

def test_verify_php_seed_admin_password():
    """
    Verify the PHP default admin password from schema seed data.
    Source: ttrss/schema/ttrss_schema_pgsql.sql lines 55-56:
      INSERT INTO ttrss_users (login,pwd_hash,access_level)
        VALUES ('admin', 'SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', 10);
    The SHA1 hash is sha1("password").
    """
    stored = "SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
    assert verify_password(stored, "password") is True
    assert verify_password(stored, "wrong") is False
    assert needs_upgrade(stored) is True


# --- MODE2 tests (functions2.php:1484: hash('sha256', $salt . $pass)) ---

def test_verify_mode2_correct():
    """MODE2: sha256(salt + password), no separator. Source: functions2.php:1484."""
    salt = "abc123salt"
    password = "hunter2"
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    stored = f"MODE2:{digest}"
    assert verify_password(stored, password, salt=salt) is True


def test_verify_mode2_wrong_password():
    salt = "abc123salt"
    password = "correct"
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    stored = f"MODE2:{digest}"
    assert verify_password(stored, "wrong", salt=salt) is False


def test_verify_mode2_wrong_salt():
    """MODE2: wrong salt must not verify — salt is from ttrss_users.salt column."""
    salt = "correctsalt"
    password = "password"
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    stored = f"MODE2:{digest}"
    assert verify_password(stored, password, salt="wrongsalt") is False


# --- SHA1X tests (functions2.php:1485: sha1("$login:$pass")) ---

def test_verify_sha1x_login_as_salt_with_colon():
    """SHA1X: sha1(login + ':' + password). Source: functions2.php:1485."""
    login = "testuser"
    password = "hunter2"
    digest = hashlib.sha1((login + ":" + password).encode("utf-8")).hexdigest()
    stored = f"SHA1X:{digest}"
    assert verify_password(stored, password, login=login) is True


def test_verify_sha1x_wrong_password():
    login = "testuser"
    password = "correct"
    digest = hashlib.sha1((login + ":" + password).encode("utf-8")).hexdigest()
    stored = f"SHA1X:{digest}"
    assert verify_password(stored, "wrong", login=login) is False


def test_verify_sha1x_wrong_login():
    """SHA1X: wrong login must not verify — login is the salt for SHA1X."""
    login = "correctuser"
    password = "password"
    digest = hashlib.sha1((login + ":" + password).encode("utf-8")).hexdigest()
    stored = f"SHA1X:{digest}"
    assert verify_password(stored, password, login="wronguser") is False


def test_verify_sha1x_no_embedded_salt_in_hash():
    """
    SHA1X hash string is 'SHA1X:{40-hex}' — the salt is NOT embedded in the hash.
    The old implementation wrongly expected 'SHA1X:{salt}:{digest}' (3 parts).
    Source: functions2.php:1485 — return "SHA1X:" . sha1("$login:$pass")
    """
    login = "admin"
    password = "password"
    digest = hashlib.sha1((login + ":" + password).encode("utf-8")).hexdigest()
    stored = f"SHA1X:{digest}"
    # stored has exactly 2 colon-separated parts: prefix and digest
    parts = stored.split(":")
    assert len(parts) == 2, "SHA1X hash must be 'SHA1X:{digest}' — no embedded salt"
    assert verify_password(stored, password, login=login) is True


# --- SHA1 unsalted tests (functions2.php:1487: sha1($pass)) ---

def test_verify_sha1_unsalted():
    """Legacy unsalted SHA1 (oldest TT-RSS installs). Source: functions2.php:1487."""
    password = "legacy"
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest()
    stored = f"SHA1:{digest}"
    assert verify_password(stored, password) is True


def test_verify_sha1_unsalted_wrong():
    password = "legacy"
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest()
    stored = f"SHA1:{digest}"
    assert verify_password(stored, "wrong") is False


# --- needs_upgrade tests ---

def test_needs_upgrade_mode2_returns_true():
    salt = "s"
    digest = hashlib.sha256(("s" + "p").encode()).hexdigest()
    assert needs_upgrade(f"MODE2:{digest}") is True


def test_needs_upgrade_sha1x_returns_true():
    digest = hashlib.sha1(("user:p").encode()).hexdigest()
    assert needs_upgrade(f"SHA1X:{digest}") is True


def test_needs_upgrade_sha1_returns_true():
    digest = hashlib.sha1(b"p").hexdigest()
    assert needs_upgrade(f"SHA1:{digest}") is True


def test_needs_upgrade_argon2id_returns_false():
    h = hash_password("p")
    assert needs_upgrade(h) is False


# --- unknown format rejection ---

def test_verify_unknown_format_rejected():
    assert verify_password("PLAINTEXT:password", "password") is False
    assert verify_password("md5:5f4dcc3b5aa765d61d8327deb882cf99", "password") is False
    assert verify_password("", "password") is False
