"""
Authentication helpers — user authentication, session management, login sequence.

Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
        ttrss/include/functions.php:initialize_user (lines 796-805)
        ttrss/include/functions.php:logout_user (lines 807-812)
        ttrss/include/functions.php:login_sequence (lines 830-881)
Adapted: PHP session-based auth replaced by Flask-Login (ADR-0007); PHP PluginHost
         HOOK_AUTH_USER replaced by pluggy hook_auth_user (firstresult=True); PHP global
         constants (SINGLE_USER_MODE, AUTH_AUTO_LOGIN) replaced by Flask config keys.
Note: ttrss/include/functions.php:load_user_plugins (lines 818-828) is ported in
      ttrss/plugins/loader.py rather than here; authenticate.py delegates to that module.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)  # New: no PHP equivalent — Python logging setup.


def authenticate_user(
    # Source: ttrss/include/functions.php:authenticate_user — $login parameter (line 706)
    login: Optional[str],
    # Source: ttrss/include/functions.php:authenticate_user — $password parameter (line 706)
    password: Optional[str],
    # Source: ttrss/include/functions.php:authenticate_user — $check_only = false parameter (line 706)
    check_only: bool = False,
) -> bool:
    """
    Authenticate a user via HOOK_AUTH_USER plugins or SINGLE_USER_MODE bypass.

    Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
    Adapted: PHP $_SESSION state (uid, version, name, csrf_token) replaced by Flask-Login
             login_user(); PHP PluginHost::HOOK_AUTH_USER loop replaced by pluggy
             hook_auth_user (firstresult=True mirrors PHP break-on-truthy at line 715).
             PHP SINGLE_USER_MODE PHP constant replaced by Flask config key SINGLE_USER_MODE.
    Note: ttrss/include/functions.php lines 724-726 — PHP sets $_SESSION["uid"], ["version"],
          ["name"], ["access_level"], ["csrf_token"].  Python: Flask-Login stores only user_id;
          csrf_token is handled by Flask-WTF; name/access_level loaded on demand from DB.
    Note: ttrss/include/functions.php line 739 — PHP stores $_SESSION["pwd_hash"].
          AR05: Python NEVER stores pwd_hash in the session (specs/06-security.md F10).
    Note: ttrss/include/functions.php lines 737-738 — PHP stores ip_address and sha1(user_agent)
          in session.  Python: Redis session handles request freshness; these fields are not
          reproduced.
    Note: ttrss/include/functions.php line 741 — PHP sets $_SESSION["last_version_check"] = time().
          Python: package versioning machinery handles version checking; not reproduced.
    Note: ttrss/include/functions.php line 716 — PHP sets $_SESSION["auth_module"] in both
          SINGLE_USER_MODE (line 759, false) and normal path (line 716, strtolower(class)).
          Python: auth_module identity is not stored; all auth is handled by HOOK_AUTH_USER plugins.
    Note: ttrss/include/functions.php lines 752-768 — SINGLE_USER_MODE path sets uid=1, name="admin",
          hide_hello, hide_logout, csrf_token (lines 761-763), ip_address (line 765).
          Python: hide_hello/hide_logout are UI-only flags not reproduced; csrf_token handled by
          Flask-WTF; ip_address handled by Redis session; admin user (id=1) logged in via Flask-Login.
    """
    from flask import current_app  # New: no PHP equivalent — lazy import keeps module importable outside Flask context.
    from flask_login import login_user  # New: no PHP equivalent — lazy import avoids top-level Flask-Login dependency at module load.

    from ttrss.extensions import db  # New: no PHP equivalent — lazy import keeps module importable outside Flask context.
    from ttrss.models.user import TtRssUser  # New: no PHP equivalent — lazy import avoids circular import at module level.
    from ttrss.prefs.ops import initialize_user_prefs  # New: no PHP equivalent — lazy import avoids circular dependency.

    # Source: ttrss/include/functions.php line 708 — if (!SINGLE_USER_MODE)
    # Adapted: PHP SINGLE_USER_MODE is a compile-time PHP constant; Python reads Flask config key.
    if not current_app.config.get("SINGLE_USER_MODE", False):
        # Source: ttrss/include/functions.php lines 709-719 — $user_id = false; foreach HOOK_AUTH_USER
        # Adapted: PHP foreach+break on truthy; pluggy firstresult=True mirrors that exact semantic.
        from ttrss.plugins.manager import get_plugin_manager  # New: no PHP equivalent — lazy import avoids circular dependency.

        pm = get_plugin_manager()
        # Source: ttrss/include/functions.php line 713 — $user_id = (int) $plugin->authenticate($login, $password)
        user_id = pm.hook.hook_auth_user(login=login, password=password)

        # Source: ttrss/include/functions.php line 721 — if ($user_id && !$check_only)
        if user_id and not check_only:
            # Source: ttrss/include/functions.php lines 727-731 — SELECT login, access_level, pwd_hash FROM ttrss_users
            user = db.session.get(TtRssUser, int(user_id))
            if user is None:  # New: no PHP equivalent — guard against plugin returning stale user_id not in DB.
                # New: no PHP equivalent — diagnostic logging for stale plugin-returned user_id.
                logger.warning(
                    "authenticate_user: plugin returned user_id=%s but no matching user found",
                    user_id,
                )
                return False

            # Source: ttrss/include/functions.php line 734 — UPDATE ttrss_users SET last_login = NOW()
            # Adapted: PHP raw SQL UPDATE; Python uses SQLAlchemy ORM attribute assignment.
            user.last_login = datetime.now(tz=timezone.utc)
            # New: no PHP equivalent — SQLAlchemy requires explicit commit; PHP auto-commits via PDO default.
            db.session.commit()

            # Source: ttrss/include/functions.php line 722 — @session_start(); $_SESSION["uid"] = $user_id
            # Adapted: PHP uses $_SESSION; Python uses Flask-Login login_user() (ADR-0007).
            login_user(user)

            # Source: ttrss/include/functions.php line 743 — initialize_user_prefs($_SESSION["uid"])
            initialize_user_prefs(user.id)

            return True  # Source: ttrss/include/functions.php line 745 — return true

        return False  # Source: ttrss/include/functions.php line 748 — return false

    else:
        # Source: ttrss/include/functions.php lines 750-770 — SINGLE_USER_MODE branch
        # Adapted: PHP sets $_SESSION["uid"]=1, name="admin", access_level=10 directly;
        #          Python looks up TtRssUser(id=1) and logs in via Flask-Login.
        # Note: ttrss/include/functions.php line 752-754 — name="admin" and access_level=10 are
        #       no longer written at login time; Flask-Login loads these from the DB on demand.
        admin_user = db.session.get(TtRssUser, 1)  # Source: ttrss/include/functions.php line 752 — $_SESSION["uid"] = 1
        if admin_user is None:  # New: no PHP equivalent — PHP assumes admin user always exists; Python guards against missing seed data.
            # New: no PHP equivalent — diagnostic logging for missing admin seed data.
            logger.error(
                "authenticate_user: SINGLE_USER_MODE enabled but admin user (id=1) not found in DB"
            )
            return False

        # Source: ttrss/include/functions.php lines 752-754 — uid=1, name="admin", access_level=10
        # Adapted: PHP sets session fields directly; Python uses Flask-Login login_user().
        login_user(admin_user)

        # Source: ttrss/include/functions.php line 767 — initialize_user_prefs($_SESSION["uid"])
        initialize_user_prefs(admin_user.id)

        return True  # Source: ttrss/include/functions.php line 769 — return true


def initialize_user(
    # Source: ttrss/include/functions.php:initialize_user — $uid parameter (line 796)
    # Adapted: renamed from $uid to owner_uid for consistency with other Python auth functions.
    owner_uid: int,
) -> None:
    """
    Seed default feeds for a newly created user.

    Source: ttrss/include/functions.php:initialize_user (lines 796-805)
    Adapted: PHP raw SQL INSERT replaced by SQLAlchemy ORM session.add().
    Note: ttrss/include/functions.php lines 791-795 — PHP comment states: called once after user
          is created to initialize default feeds/labels; user preferences are checked on every
          login, not here.  Python follows the same contract: called once at registration, not
          on login.
    Note: ttrss/include/functions.php lines 798-804 — PHP hard-codes TT-RSS release and forum
          feed URLs.  Python preserves these verbatim.
    """
    from ttrss.extensions import db  # New: no PHP equivalent — lazy import keeps module importable outside Flask context.
    from ttrss.models.feed import TtRssFeed  # New: no PHP equivalent — lazy import avoids circular import at module level.

    # Source: ttrss/include/functions.php lines 798-800 — INSERT ttrss_feeds ... 'Tiny Tiny RSS: New Releases'
    db.session.add(
        TtRssFeed(
            owner_uid=owner_uid,
            title="Tiny Tiny RSS: New Releases",
            feed_url="http://tt-rss.org/releases.rss",
        )
    )
    # Source: ttrss/include/functions.php lines 802-804 — INSERT ttrss_feeds ... 'Tiny Tiny RSS: Forum'
    db.session.add(
        TtRssFeed(
            owner_uid=owner_uid,
            title="Tiny Tiny RSS: Forum",
            feed_url="http://tt-rss.org/forum/rss.php",
        )
    )
    # New: no PHP equivalent — SQLAlchemy requires explicit commit; PHP auto-commits via PDO default.
    db.session.commit()


def logout_user() -> None:
    """
    Destroy the current user session.

    Source: ttrss/include/functions.php:logout_user (lines 807-812)
    Adapted: PHP session_destroy() + setcookie() replaced by Flask-Login logout_user().
    Note: ttrss/include/functions.php lines 809-811 — PHP deletes the session cookie manually
          via setcookie(..., time()-42000).  Flask-Login logout_user() clears the cookie via
          the HTTP response; explicit cookie expiry not reproduced.
    """
    # New: no PHP equivalent — lazy import; alias avoids name collision with this function.
    from flask_login import logout_user as _flask_logout

    # Source: ttrss/include/functions.php line 808 — session_destroy()
    # Adapted: PHP session_destroy(); Python uses Flask-Login logout_user() (ADR-0007).
    _flask_logout()


def login_sequence() -> bool:
    """
    Run the login sequence: authenticate if needed, load user plugins, bump last_login.
    Returns True if the current user is authenticated after the sequence; False otherwise.

    Source: ttrss/include/functions.php:login_sequence (lines 830-881)
    Adapted: PHP session_start(), render_login_form(), and exit replaced by bool return value
             (True = authenticated, False = unauthenticated); callers redirect on False.
             PHP $_SESSION manipulation replaced by Flask-Login current_user.
    Note: ttrss/include/functions.php login_sequence — PHP has no return value; callers are
          expected to handle redirect after this function (exit is called inline).  Python
          returns bool; every caller must branch on the return value.
    Note: ttrss/include/functions.php line 859 — PHP sets $_SESSION["last_login_update"] = time()
          on already-authenticated visits; Python does not reproduce this session field.
    Note: ttrss/include/functions.php line 834 — PHP calls startup_gettext() for i18n.
          Python: Flask-Babel locale setup is handled per-request in the blueprint layer;
          not reproduced here.
    Note: ttrss/include/functions.php lines 837-838 — PHP calls validate_session() to reject
          stale sessions.  Python: Flask-Login session validation is handled by the session
          interface; current_user.is_authenticated reflects a valid session.
    Note: ttrss/include/functions.php lines 841-845 — PHP AUTH_AUTO_LOGIN constant enables
          auto-login plugins (e.g. browser auth).  Python: controlled by Flask config key
          AUTH_AUTO_LOGIN (default False); authenticate_user(None, None) invokes hook plugins.
    Note: ttrss/include/functions.php lines 847-853 — PHP calls render_login_form() then exit.
          Python: returns False; the calling Flask route handles redirect.
    Note: ttrss/include/functions.php lines 866-876 — PHP cleans ttrss_counters_cache and
          ttrss_cat_counters_cache for rows whose parent feed/category has been deleted.
          Python: ON DELETE CASCADE on ORM FK constraints handles orphaned cache rows;
          explicit cleanup not reproduced.
    Note: ttrss/include/functions.php line 863 — PHP calls startup_gettext() inside the
          authenticated branch before load_user_plugins.  Python: Flask-Babel handles i18n;
          not reproduced inline.
    """
    from flask import current_app  # New: no PHP equivalent — lazy import avoids top-level Flask dependency at module load.
    from flask_login import current_user  # New: no PHP equivalent — lazy import avoids top-level Flask-Login dependency.

    from ttrss.plugins.loader import load_user_plugins  # New: no PHP equivalent — lazy import avoids circular dependency.

    if current_app.config.get("SINGLE_USER_MODE", False):
        # Source: ttrss/include/functions.php lines 831-835 — SINGLE_USER_MODE: authenticate + load plugins
        # Inferred from: ttrss/include/functions.php login_sequence (SINGLE_USER_MODE branch, line 831)
        #   PHP calls authenticate_user unconditionally; Python guards against redundant login_user() calls.
        if not current_user.is_authenticated:
            authenticate_user("admin", None)
        # Source: ttrss/include/functions.php line 835 — load_user_plugins($_SESSION["uid"])
        load_user_plugins(current_user.id)
        return True

    # Source: ttrss/include/functions.php line 837 — if (!validate_session()) $_SESSION["uid"] = false
    # Adapted: Flask-Login session validation via current_user.is_authenticated.
    if not current_user.is_authenticated:
        # Source: ttrss/include/functions.php lines 841-845 — AUTH_AUTO_LOGIN branch
        # Adapted: PHP AUTH_AUTO_LOGIN is a PHP constant; Python reads Flask config key.
        if current_app.config.get("AUTH_AUTO_LOGIN", False):
            # Source: ttrss/include/functions.php line 842 — authenticate_user(null, null)
            authenticate_user(None, None)

        if not current_user.is_authenticated:
            # Source: ttrss/include/functions.php lines 847-853 — session_destroy + setcookie + login form
            # Adapted: PHP renders login form and exits; Python returns False for caller to redirect.
            return False

    else:
        # Source: ttrss/include/functions.php lines 856-860 — bump last_login for already-authenticated visit
        # Adapted: PHP runs raw SQL UPDATE; Python uses SQLAlchemy ORM attribute assignment.
        from ttrss.extensions import db  # New: no PHP equivalent — lazy import avoids circular import at module level.
        from ttrss.models.user import TtRssUser  # New: no PHP equivalent — lazy import avoids circular import at module level.

        user = db.session.get(TtRssUser, current_user.id)
        if user is not None:  # New: no PHP equivalent — PHP runs UPDATE unconditionally; Python guards against missing user row.
            user.last_login = datetime.now(tz=timezone.utc)  # Source: ttrss/include/functions.php line 857 — UPDATE last_login = NOW()
            # New: no PHP equivalent — SQLAlchemy requires explicit commit; PHP auto-commits via PDO default.
            db.session.commit()

    # Source: ttrss/include/functions.php line 864 — load_user_plugins($_SESSION["uid"])
    load_user_plugins(current_user.id)

    # New: no PHP equivalent — PHP login_sequence() has no return value; Python returns bool for caller flow control.
    return True
