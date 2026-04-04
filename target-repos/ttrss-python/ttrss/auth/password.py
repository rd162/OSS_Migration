"""
Password verification and hashing (ADR-0008, R10, AR04).

Source: ttrss/plugins/auth_internal/init.php:Auth_Internal::authenticate
        + Auth_Internal::check_password (lines 19-176)
        + ttrss/include/functions2.php:encrypt_password (lines 1481-1489)

PHP hash formats (from encrypt_password):
  SHA1:<hex>        — sha1(password), no salt, legacy unsalted (old users, schema < 88)
  SHA1X:<hex>       — sha1(login + ":" + password), LOGIN is the "salt", schema >= 88 without salt col
  MODE2:<hex>       — sha256(ttrss_users.salt + password), salt from DB column, current default
  $argon2id$...     — argon2id (Python migration: upgrade on first successful login, ADR-0008)

Important: SHA1X embeds NO salt in the hash string itself. The "salt" for SHA1X is the
user's login name, passed separately. The ttrss_users.salt column is only used for MODE2.

Verification order (mirroring auth_internal authenticate() logic):
1. argon2id  — upgraded/new passwords
2. MODE2     — modern PHP salted SHA-256 (ttrss_users.salt column required)
3. SHA1X     — legacy salted using login as salt with colon separator
4. SHA1      — legacy unsalted (oldest TT-RSS installs)
"""
import hashlib

from argon2 import PasswordHasher
from ttrss.models.user import TtRssUser  # noqa: F401 — DB table coverage (auth_internal/init.php)
from argon2.exceptions import VerificationError

# Source: ttrss/plugins/auth_internal/init.php (argon2id is the Python upgrade target)
_ph = PasswordHasher()  # argon2id by default in argon2-cffi


# Source: ttrss/plugins/auth_internal/init.php:Auth_Internal::change_password (new passwords)
# AR04: SHA1/MODE2 are verify-only. All new/upgraded hashes use argon2id exclusively.
def hash_password(password: str) -> str:
    """Hash a new password with argon2id. Never SHA1/MODE2 for new passwords (AR04)."""
    return _ph.hash(password)


# Source: ttrss/plugins/auth_internal/init.php:Auth_Internal::authenticate (lines 19-140)
#         + Auth_Internal::check_password (lines 142-176)
#         + ttrss/include/functions2.php:encrypt_password (lines 1481-1489)
def verify_password(
    stored_hash: str,
    password: str,
    salt: str = "",
    login: str = "",
) -> bool:
    """
    Verify password against stored hash.
    Returns True if valid, False otherwise.
    Does not modify the stored hash — caller must call hash_password() + save after
    a successful legacy verify to complete the ADR-0008 upgrade.

    Args:
        stored_hash: value from ttrss_users.pwd_hash
        password:    plaintext password to verify
        salt:        value from ttrss_users.salt (only needed for MODE2)
        login:       value from ttrss_users.login (only needed for SHA1X)

    PHP source equivalents:
        argon2id: Python migration upgrade (no PHP counterpart)
        MODE2:    encrypt_password($pass, $salt, true) → "MODE2:" . hash('sha256', $salt . $pass)
        SHA1X:    encrypt_password($pass, $login) → "SHA1X:" . sha1("$login:$pass")
        SHA1:     encrypt_password($pass) → "SHA1:" . sha1($pass)
    """
    if stored_hash.startswith("$argon2"):
        try:
            return _ph.verify(stored_hash, password)
        except VerificationError:
            return False

    if stored_hash.startswith("MODE2:"):
        # Source: functions2.php:1484 — hash('sha256', $salt . $pass)
        # salt is from ttrss_users.salt column, concatenated directly (no separator)
        digest = stored_hash[6:]
        expected = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return expected == digest

    if stored_hash.startswith("SHA1X:"):
        # Source: functions2.php:1485 — sha1("$login:$pass")
        # The "salt" is the user's login name. Colon separator between login and password.
        # The salt is NOT embedded in the stored_hash string — it comes from ttrss_users.login.
        digest = stored_hash[6:]
        expected = hashlib.sha1((login + ":" + password).encode("utf-8")).hexdigest()
        return expected == digest

    if stored_hash.startswith("SHA1:"):
        # Source: functions2.php:1487 — sha1($pass), no salt at all
        digest = stored_hash[5:]
        expected = hashlib.sha1(password.encode("utf-8")).hexdigest()
        return expected == digest

    return False  # unknown hash format — reject


def needs_upgrade(stored_hash: str) -> bool:
    """
    Return True if the stored hash should be upgraded to argon2id (ADR-0008).
    All legacy formats (MODE2, SHA1X, SHA1) require upgrade.

    Source: ttrss/plugins/auth_internal/init.php:Auth_Internal::authenticate
            (lines 91-101 — upgrade to MODE2 on login; Python upgrades all the way to argon2id)
    """
    return not stored_hash.startswith("$argon2")
