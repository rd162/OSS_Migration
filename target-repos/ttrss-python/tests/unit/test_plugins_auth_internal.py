"""NEW tests for AuthInternal plugin — covering cases not in test_auth_internal.py.

Source PHP: ttrss/plugins/auth_internal/init.php (Auth_Internal class, lines 1-176)
New: Python test suite — no direct PHP equivalent.

NOT duplicated from test_auth_internal.py:
  - valid credentials → user id        (already in TestAuthInternalHookImpl)
  - wrong password → None              (already covered)
  - unknown user → None                (already covered)
  - empty login / empty password       (already covered)
  - plugin_class attribute             (already covered)

New coverage added here:
  - argon2id upgrade path (needs_upgrade=False → no re-hash)
  - OTP enabled + correct TOTP code → user.id returned
  - OTP enabled + empty otp code → None
  - Legacy MODE2 hash verified correctly
"""
from __future__ import annotations

import base64
import hashlib
import time
import struct
import hmac

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _totp_code(b32_secret: str, t: int | None = None, step: int = 30) -> str:
    """Generate current TOTP code — mirrors auth_internal._totp_code logic.

    Source: ttrss/plugins/auth_internal/init.php lines 43-55 (OTP verification).
    """
    if t is None:
        t = int(time.time())
    counter = struct.pack(">Q", t // step)
    padding = (-len(b32_secret)) % 8
    key = base64.b32decode(b32_secret.upper() + "=" * padding)
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def _mode2_hash(salt: str, password: str) -> str:
    """Produce a MODE2 hash identical to PHP encrypt_password($pass, $salt, true).

    Source: ttrss/include/functions2.php:encrypt_password (lines 1481-1489)
    PHP: 'MODE2:' . hash('sha256', $salt . $pass)
    """
    return "MODE2:" + hashlib.sha256((salt + password).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def argon2_user(app, db_session):
    """Create a user whose pwd_hash is already argon2id (no upgrade needed).

    Source: ttrss/plugins/auth_internal/init.php lines 91-101 — upgrade logic;
    if already argon2id, needs_upgrade() returns False and no re-hash occurs.
    """
    from ttrss.auth.password import hash_password
    from ttrss.models.user import TtRssUser

    with app.app_context():
        user = TtRssUser(
            login="argon2_user_ai",
            pwd_hash=hash_password("secret123"),
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        db_session.delete(user)
        db_session.commit()


@pytest.fixture()
def otp_user(app, db_session):
    """Create a user with otp_enabled=True and a known salt so TOTP can be computed.

    Source: ttrss/plugins/auth_internal/init.php lines 25-75 (OTP verification block).
    PHP derives OTP secret as base32_encode(sha1($salt)); Python mirrors this.
    """
    from ttrss.auth.password import hash_password
    from ttrss.models.user import TtRssUser

    salt = "knownsalt42"
    with app.app_context():
        user = TtRssUser(
            login="otp_user_ai",
            pwd_hash=hash_password("mypassword"),
            salt=salt,
            otp_enabled=True,
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        db_session.delete(user)
        db_session.commit()


@pytest.fixture()
def mode2_user(app, db_session):
    """Create a user whose pwd_hash uses the legacy MODE2 (SHA-256 + salt) format.

    Source: ttrss/include/functions2.php:encrypt_password (lines 1481-1489)
    PHP: 'MODE2:' . hash('sha256', $salt . $pass)
    """
    from ttrss.models.user import TtRssUser

    salt = "legacysalt99"
    password = "legacypass"
    with app.app_context():
        user = TtRssUser(
            login="mode2_user_ai",
            pwd_hash=_mode2_hash(salt, password),
            salt=salt,
            access_level=0,
        )
        db_session.add(user)
        db_session.commit()
        yield user
        db_session.delete(user)
        db_session.commit()


# ---------------------------------------------------------------------------
# Test: argon2id upgrade path — needs_upgrade=False → hash_password NOT called
# ---------------------------------------------------------------------------


class TestArgon2UpgradePath:
    """Source: ttrss/plugins/auth_internal/init.php lines 91-101 (upgrade block).
    PHP upgrades MODE2→argon2id on successful login. Python skips upgrade when already
    argon2id (needs_upgrade returns False).
    """

    def test_argon2id_hash_not_re_hashed_on_login(self, app, argon2_user):
        """Valid argon2id password → user.id returned; hash_password NOT called (no upgrade).

        Source: ttrss/plugins/auth_internal/init.php lines 91-101
        Adapted: needs_upgrade() returns False for argon2id hashes; Python skips re-hash.
        """
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            with patch("ttrss.auth.password.hash_password") as mock_hash:
                result = plugin.hook_auth_user(
                    login="argon2_user_ai", password="secret123"
                )
        assert result is not None
        assert isinstance(result, int)
        assert result > 0
        mock_hash.assert_not_called()


# ---------------------------------------------------------------------------
# Test: OTP enabled + correct TOTP code → user.id
# ---------------------------------------------------------------------------


class TestOTPVerification:
    """Source: ttrss/plugins/auth_internal/init.php lines 25-75 (OTP block).
    PHP derives OTP secret as base32_encode(sha1($salt)) and validates with TOTP library.
    Python uses stdlib hmac + struct to generate/verify the same code.
    """

    def test_otp_enabled_correct_code_returns_user_id(self, app, otp_user):
        """OTP enabled + correct TOTP code → user.id returned.

        Source: ttrss/plugins/auth_internal/init.php lines 43-55 (TOTP verification).
        Adapted: PHP OTP secret = base32_encode(sha1($salt)); Python mirrors derivation.
        Flask request context is required to read the otp field; test uses test_request_context.
        """
        from ttrss.plugins.auth_internal import AuthInternal

        # Derive OTP secret the same way auth_internal does.
        salt_sha1 = hashlib.sha1(otp_user.salt.encode()).digest()
        otp_secret = base64.b32encode(salt_sha1).decode()
        valid_code = _totp_code(otp_secret)

        plugin = AuthInternal()
        with app.app_context():
            # Provide OTP via Flask test request context (form data)
            with app.test_request_context(
                "/api/",
                method="POST",
                data={"otp": valid_code},
            ):
                result = plugin.hook_auth_user(
                    login="otp_user_ai", password="mypassword"
                )
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_otp_enabled_empty_code_returns_none(self, app, otp_user):
        """OTP enabled but empty otp code → None (OTP required but not provided).

        Source: ttrss/plugins/auth_internal/init.php lines 115-117
        PHP: if (!$otp_code) return false — OTP field present but blank is rejected.
        """
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            with app.test_request_context(
                "/api/",
                method="POST",
                data={"otp": ""},
            ):
                result = plugin.hook_auth_user(
                    login="otp_user_ai", password="mypassword"
                )
        assert result is None


# ---------------------------------------------------------------------------
# Test: Legacy MODE2 hash still verified correctly
# ---------------------------------------------------------------------------


class TestMode2LegacyHash:
    """Source: ttrss/plugins/auth_internal/init.php:check_password (lines 142-176).
    PHP delegates to encrypt_password() for MODE2 verification.
    Python wraps all formats in verify_password() (auth/password.py).
    """

    def test_mode2_hash_verified_correctly(self, app, mode2_user):
        """Correct password against MODE2 hash → user.id returned.

        Source: ttrss/include/functions2.php:encrypt_password (lines 1481-1489)
        PHP: 'MODE2:' . hash('sha256', $salt . $pass)
        Adapted: Python verify_password() handles MODE2 prefix natively.
        """
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(
                login="mode2_user_ai", password="legacypass"
            )
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_mode2_wrong_password_returns_none(self, app, mode2_user):
        """Wrong password against MODE2 hash → None.

        Source: ttrss/plugins/auth_internal/init.php line 88
        PHP: if (!$this->check_password(...)) return false
        """
        from ttrss.plugins.auth_internal import AuthInternal

        plugin = AuthInternal()
        with app.app_context():
            result = plugin.hook_auth_user(
                login="mode2_user_ai", password="wrongpassword"
            )
        assert result is None
