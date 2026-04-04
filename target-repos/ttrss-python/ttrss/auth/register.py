"""
User self-registration logic.

Source: ttrss/register.php (lines 1-368 — registration form processing, user creation, email)
Adapted: Server-side logic extracted; HTML form replaced by Jinja2 template.
"""
from __future__ import annotations

import secrets
import structlog
from sqlalchemy import func, text
from sqlalchemy.orm import Session as DbSession

logger = structlog.get_logger(__name__)


# Source: ttrss/register.php line 74-91 — action=check: verify username availability
def check_username_available(db: DbSession, login: str) -> bool:
    """Check if a login name is available for registration."""
    from ttrss.models.user import TtRssUser
    exists = db.query(TtRssUser).filter(
        func.lower(TtRssUser.login) == func.lower(login.strip())
    ).first()
    return exists is None


# Source: ttrss/register.php lines 60-68 — cleanup stale registrations
def cleanup_stale_registrations(db: DbSession) -> int:
    """
    Remove users who never logged in within 24h of registration.
    Source: ttrss/register.php lines 62-68
    Note: MySQL branch eliminated per ADR-0003 (PostgreSQL only).
    """
    result = db.execute(
        text(
            "DELETE FROM ttrss_users WHERE last_login IS NULL "
            "AND created < NOW() - INTERVAL '1 day' AND access_level = 0"
        )
    )
    db.commit()
    return result.rowcount


# Source: ttrss/register.php lines 247-351 — do_register action
def register_user(
    db: DbSession,
    login: str,
    email: str,
    *,
    reg_max_users: int = 0,
    enable_registration: bool = True,
) -> dict:
    """
    Register a new user account.

    Source: ttrss/register.php lines 247-351 (do_register action)
    Returns dict with 'success' bool and 'error' or 'user_id' keys.

    Note: ttrss/register.php line 260 — PHP checks captcha "four"/"4".
          Captcha validation should be done by the caller before invoking this.
    Note: ttrss/register.php line 274 — PHP calls make_password() for random temp password.
          Python uses secrets.token_urlsafe() (no PHP equivalent).
    Note: ttrss/register.php lines 276-278 — PHP uses encrypt_password($password, $salt, true).
          Python uses argon2id per ADR-0008. hash_password() returns an argon2id string
          (salt is embedded in the hash; no separate salt column needed for new users).
    """
    from ttrss.models.user import TtRssUser
    from ttrss.auth.password import hash_password

    if not enable_registration:
        return {"success": False, "error": "registration_disabled"}

    login = login.strip().lower()
    email = email.strip()

    if not login or not email:
        return {"success": False, "error": "incomplete_data"}

    # Source: register.php lines 262-266 — check username taken
    if not check_username_available(db, login):
        return {"success": False, "error": "username_taken"}

    # Source: register.php line 203-206 — check max users
    if reg_max_users > 0:
        user_count = db.query(func.count(TtRssUser.id)).scalar()
        if user_count >= reg_max_users:
            return {"success": False, "error": "max_users_reached"}

    # Source: register.php line 274 — make_password()
    # Adapted: secrets.token_urlsafe instead of PHP make_password()
    temp_password = secrets.token_urlsafe(16)

    # Source: register.php lines 276-278 — encrypt_password($password, $salt, true)
    # Adapted: argon2id per ADR-0008; hash_password() returns a single string
    # with the salt embedded (argon2id format), so no separate salt column is needed.
    pwd_hash = hash_password(temp_password)

    # Source: register.php lines 279-281 — INSERT INTO ttrss_users
    new_user = TtRssUser(
        login=login,
        pwd_hash=pwd_hash,
        access_level=0,
        email=email,
        created=func.now(),
    )
    db.add(new_user)
    db.flush()

    # Source: register.php lines 293-295 — initialize_user($new_uid)
    from ttrss.auth.authenticate import initialize_user
    initialize_user(new_user.id)

    db.commit()

    logger.info("register_user: created user %s (id=%d)", login, new_user.id)

    return {
        "success": True,
        "user_id": new_user.id,
        "temp_password": temp_password,
        "login": login,
        "email": email,
    }


# Source: ttrss/register.php lines 24-57 — format=feed: Atom feed of registration slots
def registration_slots_feed(db: DbSession, *, enable_registration: bool, reg_max_users: int, self_url: str) -> str:
    """
    Generate Atom feed showing available registration slots.
    Source: ttrss/register.php lines 24-57
    """
    from ttrss.models.user import TtRssUser

    if enable_registration and reg_max_users > 0:
        num_users = db.query(func.count(TtRssUser.id)).scalar()
        available = max(0, reg_max_users - num_users)
        suffix = "enabled"
    else:
        available = 0
        suffix = "disabled" if not enable_registration else "unlimited"

    # Source: register.php lines 26-55 — Atom XML output
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<feed xmlns="http://www.w3.org/2005/Atom">'
        f'<id>{self_url}/register</id>'
        f'<title>Tiny Tiny RSS registration slots</title>'
        f'<link rel="self" href="{self_url}/register?format=feed"/>'
        f'<link rel="alternate" href="{self_url}"/>'
        f'<entry>'
        f'<id>{self_url}/register?{available}</id>'
        f'<link rel="alternate" href="{self_url}/register"/>'
        f'<title>{available} slots are currently available, registration {suffix}</title>'
        f'<summary>{available} slots are currently available, registration {suffix}</summary>'
        f'</entry>'
        f'</feed>'
    )
