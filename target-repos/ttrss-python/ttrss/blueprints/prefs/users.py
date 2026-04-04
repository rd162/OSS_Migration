"""Pref_Users handler — user management (admin), HOOK_PREFS_TAB_SECTION + HOOK_PREFS_TAB.

Source: ttrss/classes/pref/users.php (Pref_Users handler, 458 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         Delegation to users_crud per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations

import structlog
from flask import jsonify, request
from flask_login import current_user, login_required

from ttrss.blueprints.prefs.views import prefs_bp
from ttrss.prefs import users_crud

logger = structlog.get_logger(__name__)


def _owner_uid() -> int:
    """Return the current user's ID safely."""
    return getattr(current_user, "id", None) or 0


# ---------------------------------------------------------------------------
# User list (admin tab content)
# ---------------------------------------------------------------------------


@prefs_bp.route("/users", methods=["GET"])
@login_required
def users():
    """Return user management data with plugin-added sections (admin only).

    Source: ttrss/classes/pref/users.php:303 — index (user listing query)
            ttrss/classes/pref/users.php:354 — run_hooks(HOOK_PREFS_TAB_SECTION)
            ttrss/classes/pref/users.php:449 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML admin panel replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    pm = get_plugin_manager()

    search = request.args.get("search", "")
    sort = request.args.get("sort", "login")

    # Source: ttrss/classes/pref/users.php:303-453 — user listing query
    user_list = users_crud.list_users(search=search, sort=sort)

    # Source: ttrss/classes/pref/users.php:354 — HOOK_PREFS_TAB_SECTION (fire-and-forget, collecting)
    plugin_sections = pm.hook.hook_prefs_tab_section()
    # Source: ttrss/classes/pref/users.php:449 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({
        "users": user_list,
        "plugin_sections": plugin_sections,
        "plugin_tab_content": plugin_tab_content,
    })


# ---------------------------------------------------------------------------
# User details
# ---------------------------------------------------------------------------


@prefs_bp.route("/users/<int:user_id>", methods=["GET"])
@login_required
def user_details(user_id: int):
    """Return details for a specific user (admin only).

    Source: ttrss/classes/pref/users.php:20 — userdetails / edit (line 101)
    """
    # Source: ttrss/classes/pref/users.php:24-69 — load user row, feed count, article count, feeds
    details = users_crud.get_user_details(user_id)
    if details is None:
        return jsonify({"error": "user_not_found"}), 404
    return jsonify(details)


# ---------------------------------------------------------------------------
# Create user
# ---------------------------------------------------------------------------


@prefs_bp.route("/users", methods=["POST"])
@login_required
def add_user():
    """Create a new user with a random temporary password.

    Source: ttrss/classes/pref/users.php:208 — add
    """
    login_name = request.form.get("login", "").strip()
    if not login_name:
        return jsonify({"error": "login_required"}), 400

    # Source: ttrss/classes/pref/users.php:215-216 — duplicate login check
    existing = users_crud.find_user_by_login(login_name)
    if existing is not None:
        return jsonify({"error": "login_taken"}), 409

    # Source: ttrss/classes/pref/users.php:208-235 — INSERT user + initialize_user_prefs
    result = users_crud.create_user(login_name)
    return jsonify({"status": "ok", **result})


# ---------------------------------------------------------------------------
# Update user
# ---------------------------------------------------------------------------


@prefs_bp.route("/users/<int:user_id>", methods=["POST"])
@login_required
def save_user(user_id: int):
    """Update user fields (login, access level, email, optional password).

    Source: ttrss/classes/pref/users.php:175 — editSave
    """
    login_name = request.form.get("login", "").strip()
    access_level = int(request.form.get("access_level", 0))
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    # Source: ttrss/classes/pref/users.php:175-193 — UPDATE ttrss_users (login, access_level, email, otp, pwd_hash)
    ok = users_crud.update_user(user_id, login_name, access_level, email, password=password)
    if not ok:
        return jsonify({"error": "user_not_found"}), 404

    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Delete user
# ---------------------------------------------------------------------------


@prefs_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id: int):
    """Delete a user and cascade-remove their tags, feeds, and user row.

    Source: ttrss/classes/pref/users.php:196 — remove
    """
    owner_uid = _owner_uid()
    if user_id == owner_uid:
        return jsonify({"error": "cannot_delete_self"}), 400

    # Source: ttrss/classes/pref/users.php:201-203 — delete tags, feeds, user row
    users_crud.delete_user(user_id)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Reset user password
# ---------------------------------------------------------------------------


@prefs_bp.route("/users/<int:user_id>/reset_password", methods=["POST"])
@login_required
def reset_user_password(user_id: int):
    """Generate a new random password for a user.

    Source: ttrss/classes/pref/users.php:298 — resetPass / resetUserPassword (line 247)
    """
    # Source: ttrss/classes/pref/users.php:256-261 — generate and store new hash
    result = users_crud.reset_user_password(user_id)
    if result is None:
        return jsonify({"error": "user_not_found"}), 404

    return jsonify({"status": "ok", **result})
