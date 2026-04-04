"""
Auth_Internal plugin — database-backed user authentication.

Source: ttrss/plugins/auth_internal/init.php (Auth_Internal class, lines 1-176)
Adapted: PHP class Auth_Internal extends Plugin replaced by Python class with pluggy @hookimpl.
         PHP authenticate() → hook_auth_user() hookimpl (firstresult=True on the spec).
         PHP upgrade-to-MODE2 (lines 91-101) extended to upgrade-to-argon2id (ADR-0008).

Class graph community [8]: Plugin → AuthInternal (maps PHP is_subclass_of Plugin check).
"""
from __future__ import annotations

from ttrss.plugins.hookspecs import KIND_SYSTEM, hookimpl


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
