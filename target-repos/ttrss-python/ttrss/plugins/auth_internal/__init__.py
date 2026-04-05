"""
Auth_Internal plugin — database-backed user authentication.

Source: ttrss/plugins/auth_internal/init.php (Auth_Internal class, lines 1-176)
Adapted: PHP class Auth_Internal extends Plugin replaced by Python class with pluggy @hookimpl.
         PHP authenticate() → hook_auth_user() hookimpl (firstresult=True on the spec).
         PHP upgrade-to-MODE2 (lines 91-101) extended to upgrade-to-argon2id (ADR-0008).

Class graph community [8]: Plugin → AuthInternal (maps PHP is_subclass_of Plugin check).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time

from ttrss.plugins.hookspecs import KIND_SYSTEM, hookimpl


def _totp_code(b32_secret: str, t: int | None = None, step: int = 30) -> str:
    """Generate a 6-digit TOTP code for the given base32 secret.

    Source: ttrss/plugins/auth_internal/init.php lines 43-55 (OTP verification).
    PHP uses the TOTP algorithm (RFC 6238) via an external library.
    Python implements the same algorithm using stdlib hmac/struct/base64.
    """
    if t is None:
        t = int(time.time())
    counter = struct.pack(">Q", t // step)
    # Pad base32 to multiple of 8
    padding = (-len(b32_secret)) % 8
    key = base64.b32decode(b32_secret.upper() + "=" * padding)
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def _verify_totp(b32_secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code within ±window steps (default ±30 seconds)."""
    t = int(time.time())
    for delta in range(-window, window + 1):
        if hmac.compare_digest(_totp_code(b32_secret, t + delta * 30), code.strip()):
            return True
    return False


class AuthInternal:
    """
    Built-in authentication plugin. Verifies credentials against ttrss_users.pwd_hash.

    Source: ttrss/plugins/auth_internal/init.php:Auth_Internal
    Class dimension: Plugin → AuthInternal (class_graph community [8])
    """

    # Source: ttrss/classes/pluginhost.php:is_system() — auth_internal declared KIND_SYSTEM
    # (pluginhost.php lines 159-176: system plugins loaded via KIND_SYSTEM, not KIND_USER)
    KIND = KIND_SYSTEM

    @hookimpl
    def hook_auth_user(self, login: str, password: str):
        """
        Verify login/password against ttrss_users.pwd_hash.
        Returns user.id (int > 0) on success, None on failure.
        firstresult=True on spec: first truthy return wins (mirrors PHP break-on-truthy, line 715).

        Source: ttrss/plugins/auth_internal/init.php:Auth_Internal::authenticate (lines 19-140)
        Adapted: PHP PDO query replaced by SQLAlchemy ORM lookup; hash verification and
                 argon2id upgrade path preserved (ADR-0008 — upgrade on successful login).
        """
        from ttrss.auth.password import hash_password, needs_upgrade, verify_password
        from ttrss.extensions import db
        from ttrss.models.user import TtRssUser

        # Source: auth_internal/init.php line 25 — if (!$login || !$password) return false
        if not login or not password:
            return None

        # Source: auth_internal/init.php lines 27-30 — SELECT login, pwd_hash, salt FROM ttrss_users
        user = db.session.query(TtRssUser).filter_by(login=login).first()
        if user is None:  # Source: auth_internal/init.php line 32 — if (!$row) return false
            return None

        # Source: auth_internal/init.php:check_password (lines 142-176)
        # Adapted: PHP delegates to encrypt_password() for MODE2/SHA1X/SHA1 verification;
        #          Python wraps all formats in verify_password() (auth/password.py).
        ok = verify_password(
            stored_hash=user.pwd_hash,
            password=password,
            salt=user.salt or "",
            login=login,
        )
        if not ok:  # Source: auth_internal/init.php line 88 — if (!$this->check_password(...)) return false
            return None

        # Source: auth_internal/init.php lines 25-75 — OTP verification (schema >= 96)
        # If user has OTP enabled, require a valid TOTP code in the request.
        # PHP derives OTP secret as base32_encode(sha1($salt)).
        # Python reads OTP from Flask request (form or JSON payload, field "otp").
        if user.otp_enabled and user.salt:
            try:
                from flask import request as _req
                # Support form POST, JSON body, and query string (matches PHP $_REQUEST)
                _otp_code = (
                    _req.form.get("otp")
                    or (_req.get_json(silent=True, force=True) or {}).get("otp", "")
                    or _req.args.get("otp", "")
                )
            except RuntimeError:
                # No request context (e.g., CLI / tests) — deny OTP-enabled accounts
                return None

            if not _otp_code:
                # OTP required but not provided
                return None

            # Source: auth_internal/init.php line 43 — OTP secret = base32_encode(sha1($salt))
            _salt_sha1 = hashlib.sha1(user.salt.encode()).digest()
            _otp_secret = base64.b32encode(_salt_sha1).decode()
            if not _verify_totp(_otp_secret, _otp_code):
                return None

        # Source: auth_internal/init.php lines 91-101 — upgrade legacy hash to MODE2 on login
        # Adapted: Python upgrades all the way to argon2id (ADR-0008; MODE2 is intermediate in PHP).
        if needs_upgrade(user.pwd_hash):
            user.pwd_hash = hash_password(password)
            db.session.commit()

        # Source: auth_internal/init.php line 108 — return $owner_uid (truthy int stops pluggy iteration)
        return user.id


# Loader entry point: ttrss/plugins/loader.py looks for plugin_class attribute first.
# Source: ttrss/classes/pluginhost.php lines 147-148 — class_exists + is_subclass_of Plugin gate.
plugin_class = AuthInternal
