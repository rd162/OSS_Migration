"""DB service layer for user preferences — AR-2 compliant.

All direct db.session calls for the pref/user_prefs blueprint live here.
Blueprint (ttrss/blueprints/prefs/user_prefs.py) MUST NOT import db directly.

Source: ttrss/classes/pref/prefs.php (Pref_Prefs handler, 1129 lines)
"""
from __future__ import annotations

from typing import Optional

import structlog
from sqlalchemy import delete as sa_delete, select, update

from ttrss.extensions import db
from ttrss.models.pref import TtRssSettingsProfile, TtRssUserPref
from ttrss.models.user import TtRssUser

logger = structlog.get_logger(__name__)


def get_user_for_password_change(owner_uid: int) -> Optional[object]:
    """Return the TtRssUser row for password change; None if not found.

    Source: ttrss/classes/pref/prefs.php:changepassword (line 62) — user lookup
    """
    # Source: ttrss/classes/pref/prefs.php:83-89 — load user for auth check
    return db.session.get(TtRssUser, owner_uid)


def save_password_change(owner_uid: int, new_pw: str) -> None:
    """Persist the new argon2id hash, clear legacy salt, disable OTP.

    Source: ttrss/classes/pref/prefs.php:changepassword (line 62) — hash update
    """
    from ttrss.auth.password import hash_password

    user = db.session.get(TtRssUser, owner_uid)
    if user is None:
        return
    user.pwd_hash = hash_password(new_pw)
    user.salt = ""
    user.otp_enabled = False  # Source: changing password disables OTP
    db.session.commit()


def save_email_and_name(owner_uid: int, email: str, full_name: str) -> None:
    """Update user's email and full name.

    Source: ttrss/classes/pref/prefs.php:changeemail (line 153-154)
    """
    # Source: ttrss/classes/pref/prefs.php:153-154 — UPDATE ttrss_users SET email, full_name
    db.session.execute(
        update(TtRssUser)
        .where(TtRssUser.id == owner_uid)
        .values(email=email, full_name=full_name)
    )
    db.session.commit()


def clear_digest_sent_time(owner_uid: int) -> None:
    """Clear last_digest_sent when DIGEST_PREFERRED_TIME preference changes.

    Source: ttrss/classes/pref/prefs.php:saveconfig (line 106-112) — DIGEST_PREFERRED_TIME special case
    """
    # Source: ttrss/classes/pref/prefs.php:109 — UPDATE ttrss_users SET last_digest_sent = NULL
    db.session.execute(
        update(TtRssUser)
        .where(TtRssUser.id == owner_uid)
        .values(last_digest_sent=None)
    )


def reset_user_prefs(owner_uid: int, profile: Optional[int] = None) -> None:
    """Delete all user preference overrides for the given profile and re-initialize from defaults.

    Source: ttrss/classes/pref/prefs.php:resetconfig (line 161-174)
    PHP wraps DELETE + re-initialize in BEGIN/COMMIT (lines 171-174).

    Note: initialize_user_prefs() calls db.session.commit() internally, which makes
    begin_nested() + inner commit conflict (savepoint already released before context exit).
    Solution: flush the DELETE immediately, then let initialize_user_prefs commit everything.
    """
    # Source: ttrss/classes/pref/prefs.php:170-172 — DELETE ttrss_user_prefs WHERE owner_uid AND profile
    q = sa_delete(TtRssUserPref).where(TtRssUserPref.owner_uid == owner_uid)
    if profile is not None:
        q = q.where(TtRssUserPref.profile == profile)
    else:
        q = q.where(TtRssUserPref.profile.is_(None))
    db.session.execute(q)
    db.session.flush()  # Make DELETE visible within session before re-init

    # Source: ttrss/classes/pref/prefs.php:174 — re-initialize defaults (commits internally)
    from ttrss.prefs.ops import initialize_user_prefs
    initialize_user_prefs(owner_uid, profile=profile)


def get_user_for_otp(owner_uid: int) -> Optional[object]:
    """Return the TtRssUser row for OTP operations; None if not found.

    Source: ttrss/classes/pref/prefs.php:otpqrcode (line 873) / otpenable (line 896) / otpdisable (line 933)
    """
    return db.session.get(TtRssUser, owner_uid)


def set_otp_enabled(owner_uid: int, enabled: bool) -> None:
    """Set otp_enabled flag on user row and commit.

    Source: ttrss/classes/pref/prefs.php:otpenable (line 920-921) / otpdisable (line 940-941)
    """
    user = db.session.get(TtRssUser, owner_uid)
    if user is None:
        return
    user.otp_enabled = enabled
    db.session.commit()


def clear_plugin_data(owner_uid: int, plugin_name: str) -> None:
    """Delete all stored data for a plugin belonging to this user.

    Source: ttrss/classes/pref/prefs.php:clearplugindata (line 962) — PluginHost::clear_data
    """
    from ttrss.models.plugin_storage import TtRssPluginStorage

    # Source: ttrss/classes/pref/prefs.php:962 — DELETE FROM ttrss_plugin_storage WHERE name AND owner_uid
    db.session.execute(
        sa_delete(TtRssPluginStorage)
        .where(
            TtRssPluginStorage.name == plugin_name,
            TtRssPluginStorage.owner_uid == owner_uid,
        )
    )
    db.session.commit()


def list_pref_profiles(owner_uid: int) -> list[object]:
    """Return all TtRssSettingsProfile rows for the user, ordered by title.

    Source: ttrss/classes/pref/prefs.php:editPrefProfiles (line 1014)
    """
    # Source: ttrss/classes/pref/prefs.php:1014 — SELECT ... FROM ttrss_settings_profiles WHERE owner_uid
    return db.session.execute(
        select(TtRssSettingsProfile)
        .where(TtRssSettingsProfile.owner_uid == owner_uid)
        .order_by(TtRssSettingsProfile.title)
    ).scalars().all()
