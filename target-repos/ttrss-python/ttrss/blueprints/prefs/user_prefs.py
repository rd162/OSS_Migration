"""Pref_Prefs handler — user preferences, HOOK_PREFS_TAB_SECTION ×3 + HOOK_PREFS_TAB.

Source: ttrss/classes/pref/prefs.php (Pref_Prefs handler, 1129 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         Delegation to user_prefs_crud per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations

import structlog
from flask import jsonify, request
from flask_login import current_user, login_required

from ttrss.blueprints.prefs.views import prefs_bp
from ttrss.prefs import user_prefs_crud

logger = structlog.get_logger(__name__)


def _owner_uid() -> int:
    """Return the current user's ID safely."""
    return getattr(current_user, "id", None) or 0


# ---------------------------------------------------------------------------
# User preferences tab content
# ---------------------------------------------------------------------------


@prefs_bp.route("/user", methods=["GET"])
@login_required
def user_prefs():
    """Return current user preferences with plugin-added sections.

    Source: ttrss/classes/pref/prefs.php:435 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/prefs.php:661 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/prefs.php:697 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/prefs.php:863 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML preference form replaced by JSON payload; AR-2 delegates to user_prefs_crud.
    """
    from ttrss.plugins.manager import get_plugin_manager
    from ttrss.prefs.ops import get_user_pref

    owner_uid = _owner_uid()
    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/prefs.php:435 — HOOK_PREFS_TAB_SECTION (section 1 of 3)
    # Source: ttrss/classes/pref/prefs.php:661 — HOOK_PREFS_TAB_SECTION (section 2 of 3)
    # Source: ttrss/classes/pref/prefs.php:697 — HOOK_PREFS_TAB_SECTION (section 3 of 3)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/prefs.php:863 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    # Source: ttrss/classes/pref/prefs.php:1014 — pref profile list
    # Guard: owner_uid must be a real int (not MagicMock in tests) before hitting DB
    profile_list = []
    if isinstance(owner_uid, int) and owner_uid > 0:
        profiles = user_prefs_crud.list_pref_profiles(owner_uid)
        profile_list = [{"id": p.id, "title": p.title} for p in profiles]

    return jsonify({
        "plugin_sections": plugin_sections,
        "plugin_tab_content": plugin_tab_content,
        "profiles": profile_list,
    })


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------


@prefs_bp.route("/user/password", methods=["POST"])
@login_required
def change_password():
    """Change the current user's password.

    Source: ttrss/classes/pref/prefs.php:62 — changepassword
    """
    owner_uid = _owner_uid()
    old_password = request.form.get("old_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not new_password:
        return jsonify({"error": "new_password_required"}), 400
    if new_password != confirm_password:
        return jsonify({"error": "passwords_do_not_match"}), 400

    # Source: ttrss/classes/pref/prefs.php:83-89 — verify old password
    user = user_prefs_crud.get_user_for_password_change(owner_uid)
    if user is None:
        return jsonify({"error": "user_not_found"}), 404

    from ttrss.auth.password import check_password
    if not check_password(old_password, user.pwd_hash, getattr(user, "salt", "")):
        return jsonify({"error": "incorrect_password"}), 403

    # Source: ttrss/classes/pref/prefs.php:62 — hash update, clear salt, disable OTP
    user_prefs_crud.save_password_change(owner_uid, new_password)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Change email and display name
# ---------------------------------------------------------------------------


@prefs_bp.route("/user/email", methods=["POST"])
@login_required
def change_email():
    """Update user's email and full name.

    Source: ttrss/classes/pref/prefs.php:153 — changeemail
    """
    owner_uid = _owner_uid()
    email = request.form.get("email", "").strip()
    full_name = request.form.get("full_name", "").strip()

    # Source: ttrss/classes/pref/prefs.php:153-154 — UPDATE ttrss_users SET email, full_name
    user_prefs_crud.save_email_and_name(owner_uid, email, full_name)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Save / reset config
# ---------------------------------------------------------------------------


@prefs_bp.route("/user/config", methods=["POST"])
@login_required
def save_config():
    """Save user preference key/value and handle special cases (e.g. DIGEST_PREFERRED_TIME).

    Source: ttrss/classes/pref/prefs.php:106 — saveconfig
    """
    from ttrss.prefs.ops import set_user_pref

    owner_uid = _owner_uid()
    pref_name = request.form.get("pref_name", "").strip()
    value = request.form.get("value", "").strip()

    if not pref_name:
        return jsonify({"error": "pref_name_required"}), 400

    # Source: ttrss/classes/pref/prefs.php:106-112 — DIGEST_PREFERRED_TIME special case
    if pref_name == "DIGEST_PREFERRED_TIME":
        user_prefs_crud.clear_digest_sent_time(owner_uid)

    set_user_pref(owner_uid, pref_name, value)
    return jsonify({"status": "ok"})


@prefs_bp.route("/user/config/reset", methods=["POST"])
@login_required
def reset_config():
    """Delete all user preference overrides and re-initialize from defaults.

    Source: ttrss/classes/pref/prefs.php:161 — resetconfig
    """
    owner_uid = _owner_uid()
    profile_raw = request.form.get("profile")
    profile = int(profile_raw) if profile_raw and profile_raw.lstrip("-").isdigit() else None

    # Source: ttrss/classes/pref/prefs.php:170-174 — DELETE prefs then reinitialize defaults
    user_prefs_crud.reset_user_prefs(owner_uid, profile=profile)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# OTP management
# ---------------------------------------------------------------------------


@prefs_bp.route("/user/otp/enable", methods=["POST"])
@login_required
def otp_enable():
    """Enable OTP for the current user.

    Source: ttrss/classes/pref/prefs.php:896 — otpenable
    """
    owner_uid = _owner_uid()
    # Source: ttrss/classes/pref/prefs.php:920-921 — set otp_enabled = True
    user_prefs_crud.set_otp_enabled(owner_uid, enabled=True)
    return jsonify({"status": "ok"})


@prefs_bp.route("/user/otp/disable", methods=["POST"])
@login_required
def otp_disable():
    """Disable OTP for the current user.

    Source: ttrss/classes/pref/prefs.php:933 — otpdisable
    """
    owner_uid = _owner_uid()
    # Source: ttrss/classes/pref/prefs.php:940-941 — set otp_enabled = False
    user_prefs_crud.set_otp_enabled(owner_uid, enabled=False)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Plugin data
# ---------------------------------------------------------------------------


@prefs_bp.route("/user/plugin_data/clear", methods=["POST"])
@login_required
def clear_plugin_data():
    """Delete all stored data for a named plugin belonging to the current user.

    Source: ttrss/classes/pref/prefs.php:962 — clearplugindata
    """
    owner_uid = _owner_uid()
    plugin_name = request.form.get("plugin", "").strip()
    if not plugin_name:
        return jsonify({"error": "plugin_required"}), 400

    # Source: ttrss/classes/pref/prefs.php:962 — DELETE FROM ttrss_plugin_storage
    user_prefs_crud.clear_plugin_data(owner_uid, plugin_name)
    return jsonify({"status": "ok"})
