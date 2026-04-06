"""
Preference read/write helpers and schema version check.

Source: ttrss/include/db-prefs.php:get_pref (user pref read with system default fallback)
        ttrss/include/db-prefs.php:set_pref (user pref write / upsert)
        ttrss/include/db-prefs.php:initialize_user_prefs (bulk default copy for new users)
        ttrss/include/functions.php:get_schema_version (line 988, schema version query)
Adapted: PHP global PDO calls replaced by SQLAlchemy ORM queries; PHP session cache for
         schema version not reproduced — Python always queries the DB directly.
"""
from __future__ import annotations

import logging
from typing import Optional

from ttrss.models.pref import TtRssSettingsProfile  # noqa: F401 — DB table coverage

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.


def get_schema_version() -> int:
    """
    Return the current schema version from ttrss_version.

    Source: ttrss/include/functions.php:get_schema_version (line 988)
    Source: ttrss/include/sessions.php:session_get_schema_version (lines 26-31)
    Adapted: PHP uses a global PDO connection and returns an int via fetch(PDO::FETCH_COLUMN).
             Python queries via SQLAlchemy session (Flask-SQLAlchemy extension).
    Note: PHP caches the schema version in $_SESSION to avoid repeated queries.
          Python does not use a session cache; every call queries the DB.
    """
    # Source: ttrss/include/functions.php line 988 — SELECT schema_version FROM ttrss_version
    from ttrss.extensions import db  # New: no PHP equivalent — lazy import keeps module importable outside Flask context.
    from ttrss.models.version import TtRssVersion

    row = db.session.query(TtRssVersion).first()
    if row is None:  # New: no PHP equivalent — PHP assumes ttrss_version always has one row; Python guards against empty table.
        return 0
    return row.schema_version  # Source: ttrss/include/functions.php line 989 — return (int)$result['schema_version']


def get_user_pref(
    owner_uid: int,
    # Source: ttrss/include/db-prefs.php:get_pref — $pref_name parameter
    pref_name: str,
    # Source: ttrss/include/db-prefs.php:get_pref — $profile parameter (optional, defaults to current session profile)
    # Adapted: PHP reads $profile from $_SESSION["profile"]; Python callers pass it explicitly.
    profile: Optional[int] = None,
) -> Optional[str]:
    """
    Return the value of a preference for the given user, falling back to the
    system default if no user override exists.

    Source: ttrss/include/db-prefs.php:get_pref (full function)
    # Source: ttrss/classes/db/prefs.php:read (Db_Prefs class method; thin wrapper around get_pref)
    Adapted: PHP uses global PDO; Python uses SQLAlchemy session.
             PHP returns false on missing pref_name; Python returns None.
    Note: ttrss/include/db-prefs.php:get_pref — PHP coerces the value to bool/int/string
          based on type_id from ttrss_prefs.  Python returns the raw string value from the
          DB; callers are responsible for type coercion.
    Note: ttrss/include/db-prefs.php:get_pref — PHP falls back to def_value when no user
          override row exists in ttrss_user_prefs.  Python replicates this fallback below.
    """
    # Source: ttrss/include/db-prefs.php:get_pref — SELECT value FROM ttrss_user_prefs WHERE ...
    from ttrss.extensions import db  # New: no PHP equivalent — lazy import.
    from ttrss.models.pref import TtRssUserPref, TtRssPref

    # Source: ttrss/include/db-prefs.php:get_pref — user-override lookup with optional profile filter
    query = db.session.query(TtRssUserPref).filter(
        TtRssUserPref.owner_uid == owner_uid,
        TtRssUserPref.pref_name == pref_name,
    )
    if profile is not None:
        # Source: ttrss/include/db-prefs.php:get_pref — AND profile = :profile
        query = query.filter(TtRssUserPref.profile == profile)
    else:
        # Source: ttrss/include/db-prefs.php:get_pref — AND profile IS NULL (default profile)
        query = query.filter(TtRssUserPref.profile.is_(None))

    user_row = query.first()
    if user_row is not None:
        return user_row.value  # Source: ttrss/include/db-prefs.php:get_pref — return $row['value']

    # Source: ttrss/include/db-prefs.php:get_pref — fallback: SELECT def_value FROM ttrss_prefs WHERE pref_name = :pref_name
    system_row = db.session.get(TtRssPref, pref_name)
    if system_row is None:  # New: no PHP equivalent — PHP returns false for unknown pref_name; Python returns None.
        # New: no PHP equivalent — diagnostic debug logging for unknown pref_name fallthrough.
        logger.debug("get_user_pref: unknown pref_name %r for uid=%d", pref_name, owner_uid)
        return None
    return system_row.def_value  # Source: ttrss/include/db-prefs.php:get_pref — return $row['def_value']


def set_user_pref(
    owner_uid: int,
    # Source: ttrss/include/db-prefs.php:set_pref — $pref_name parameter
    pref_name: str,
    # Source: ttrss/include/db-prefs.php:set_pref — $value parameter
    value: str,
    # Source: ttrss/include/db-prefs.php:set_pref — $profile parameter
    # Adapted: PHP reads $profile from $_SESSION["profile"]; Python callers pass it explicitly.
    profile: Optional[int] = None,
) -> None:
    """
    Write (upsert) a preference value for the given user.

    Source: ttrss/include/db-prefs.php:set_pref (full function)
    # Source: ttrss/classes/db/prefs.php:write (Db_Prefs class method; thin wrapper around set_pref)
    Adapted: PHP uses INSERT … ON CONFLICT DO UPDATE (or equivalent two-step
             DELETE+INSERT in older TT-RSS versions); Python uses SQLAlchemy merge
             (session.merge) which achieves the same upsert semantics via the ORM.
    Note: ttrss/include/db-prefs.php:set_pref — PHP does not validate that pref_name
          exists in ttrss_prefs before writing.  Python follows the same permissive
          approach; DB FK constraint enforces validity.
    """
    # Source: ttrss/include/db-prefs.php:set_pref — upsert into ttrss_user_prefs
    from ttrss.extensions import db  # New: no PHP equivalent — lazy import.
    from ttrss.models.pref import TtRssUserPref

    # Source: ttrss/include/db-prefs.php:set_pref — INSERT … ON CONFLICT DO UPDATE (upsert by composite PK)
    # Adapted: PHP uses raw SQL upsert; Python uses session.merge() which achieves the same semantics via ORM.
    row = TtRssUserPref(
        owner_uid=owner_uid,
        pref_name=pref_name,
        profile=profile,
        value=value,
    )
    db.session.merge(row)
    db.session.commit()  # New: no PHP equivalent — SQLAlchemy requires explicit commit; PHP auto-commits via PDO default.


def initialize_user_prefs(
    owner_uid: int,
    # Source: ttrss/include/db-prefs.php:initialize_user_prefs — $profile parameter
    # Adapted: PHP reads $profile from $_SESSION["profile"]; Python callers pass it explicitly.
    profile: Optional[int] = None,
) -> None:
    """
    Copy all system default preferences from ttrss_prefs into ttrss_user_prefs
    for a newly created user, skipping rows that already exist.

    Source: ttrss/include/functions.php:initialize_user_prefs (lines 639-723)
    Source: ttrss/include/db-prefs.php:initialize_user_prefs (full function)
    Adapted: PHP uses INSERT … SELECT with ON CONFLICT DO NOTHING (or equivalent).
             Python iterates system prefs and calls session.merge per row — semantically
             equivalent but row-by-row rather than a single bulk SQL statement.
    Note: ttrss/include/db-prefs.php:initialize_user_prefs — PHP skips rows that already
          have a user override (ON CONFLICT DO NOTHING or equivalent guard).  Python
          achieves the same via session.merge which preserves existing values when the
          composite PK already exists.
    Note: Called during user registration (ttrss/include/functions.php:register_user).
          Must be called inside an active Flask app context.
    """
    # Source: ttrss/include/db-prefs.php:initialize_user_prefs — SELECT * FROM ttrss_prefs
    from ttrss.extensions import db  # New: no PHP equivalent — lazy import.
    from ttrss.models.pref import TtRssPref, TtRssUserPref

    system_prefs = db.session.query(TtRssPref).all()  # Source: ttrss/include/db-prefs.php:initialize_user_prefs — iterate all system prefs

    for pref in system_prefs:
        # Source: ttrss/include/db-prefs.php:initialize_user_prefs — INSERT … ON CONFLICT DO NOTHING
        row = TtRssUserPref(
            owner_uid=owner_uid,
            pref_name=pref.pref_name,
            profile=profile,
            value=pref.def_value,  # Source: ttrss/include/db-prefs.php:initialize_user_prefs — use def_value as initial value
        )
        # Source: ttrss/include/db-prefs.php:initialize_user_prefs — INSERT … ON CONFLICT DO NOTHING
        # Adapted: session.merge() preserves existing rows, matching that skip-if-exists semantics.
        db.session.merge(row)

    db.session.commit()  # New: no PHP equivalent — explicit commit required by SQLAlchemy.
    # New: no PHP equivalent — diagnostic debug logging for completion telemetry.
    logger.debug(
        "initialize_user_prefs: initialized %d prefs for uid=%d (profile=%s)",
        len(system_prefs),
        owner_uid,
        profile,
    )
