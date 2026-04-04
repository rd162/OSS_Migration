"""Pref_Labels handler — label preferences, HOOK_PREFS_TAB.

Source: ttrss/classes/pref/labels.php (Pref_Labels handler, 331 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         Delegation to labels_crud per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations

import structlog
from flask import jsonify, request
from flask_login import current_user, login_required

from ttrss.blueprints.prefs.views import prefs_bp
from ttrss.prefs import labels_crud

logger = structlog.get_logger(__name__)


def _owner_uid() -> int:
    """Return the current user's ID safely."""
    return getattr(current_user, "id", None) or 0


# ---------------------------------------------------------------------------
# Label list (tab content)
# ---------------------------------------------------------------------------


@prefs_bp.route("/labels", methods=["GET"])
@login_required
def labels():
    """Return label list and plugin-provided content for the labels preferences tab.

    Source: ttrss/classes/pref/labels.php:93 — getlabeltree
            ttrss/classes/pref/labels.php:322 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML tab content replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    owner_uid = _owner_uid()
    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/labels.php:93-96 — fetch all labels ordered by caption
    label_rows = labels_crud.fetch_labels(owner_uid)
    label_list = [
        {
            "id": lbl.id,
            "caption": lbl.caption,
            "fg_color": lbl.fg_color,
            "bg_color": lbl.bg_color,
        }
        for lbl in label_rows
    ]

    # Source: ttrss/classes/pref/labels.php:322 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({
        "labels": label_list,
        "plugin_tab_content": plugin_tab_content,
    })


# ---------------------------------------------------------------------------
# Create label
# ---------------------------------------------------------------------------


@prefs_bp.route("/labels", methods=["POST"])
@login_required
def add_label():
    """Create a new label if it doesn't already exist.

    Source: ttrss/classes/pref/labels.php:224 — add
    """
    owner_uid = _owner_uid()
    caption = request.form.get("caption", "").strip()
    if not caption:
        return jsonify({"error": "caption_required"}), 400

    # Source: ttrss/classes/pref/labels.php:224 — label_create (delegates to label_create helper)
    created = labels_crud.create_label(caption, owner_uid)
    if not created:
        return jsonify({"error": "label_already_exists"}), 409

    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Save (rename + colors)
# ---------------------------------------------------------------------------


@prefs_bp.route("/labels/<int:label_id>", methods=["POST"])
@login_required
def save_label(label_id: int):
    """Rename a label and/or update its colors.

    Source: ttrss/classes/pref/labels.php:176 — save
    """
    owner_uid = _owner_uid()
    new_caption = request.form.get("caption", "").strip()
    fg_color = request.form.get("fg_color", "").strip()
    bg_color = request.form.get("bg_color", "").strip()

    if new_caption:
        # Source: ttrss/classes/pref/labels.php:176-177 — load current caption
        old_caption = labels_crud.fetch_label_caption(label_id, owner_uid)
        if old_caption is None:
            return jsonify({"error": "label_not_found"}), 404

        if new_caption != old_caption:
            # Source: ttrss/classes/pref/labels.php:182-185 — duplicate check
            if labels_crud.check_caption_taken(new_caption, owner_uid):
                return jsonify({"error": "caption_taken"}), 409
            # Source: ttrss/classes/pref/labels.php:187-198 — rename + update filter actions
            labels_crud.rename_label(label_id, owner_uid, old_caption, new_caption)

    # Source: ttrss/classes/pref/labels.php — color update block
    color_fields: dict = {}
    if fg_color:
        color_fields["fg_color"] = fg_color
    if bg_color:
        color_fields["bg_color"] = bg_color
    if color_fields:
        labels_crud.update_label_colors(label_id, owner_uid, **color_fields)

    labels_crud.commit_label()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Delete label
# ---------------------------------------------------------------------------


@prefs_bp.route("/labels/<int:label_id>", methods=["DELETE"])
@login_required
def delete_label(label_id: int):
    """Delete a label and clean up caches.

    Source: ttrss/classes/pref/labels.php:214 — remove
    """
    owner_uid = _owner_uid()
    labels_crud.delete_label(label_id, owner_uid)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Color set / reset
# ---------------------------------------------------------------------------


@prefs_bp.route("/labels/<int:label_id>/color", methods=["POST"])
@login_required
def set_label_color(label_id: int):
    """Set foreground and/or background color for a label.

    Source: ttrss/classes/pref/labels.php:128 — colorset
    """
    owner_uid = _owner_uid()
    kind = request.form.get("kind", "").strip()
    color = request.form.get("color", "").strip()
    fg = request.form.get("fg", "").strip()
    bg = request.form.get("bg", "").strip()

    # Source: ttrss/classes/pref/labels.php:128-143 — colorset: set fg/bg or both, invalidate cache
    labels_crud.set_label_color(label_id, owner_uid, kind=kind, color=color, fg=fg, bg=bg)
    return jsonify({"status": "ok"})


@prefs_bp.route("/labels/<int:label_id>/color/reset", methods=["POST"])
@login_required
def reset_label_color(label_id: int):
    """Reset label colors to empty strings.

    Source: ttrss/classes/pref/labels.php:155 — colorreset
    """
    owner_uid = _owner_uid()
    # Source: ttrss/classes/pref/labels.php:155-164 — reset fg/bg to empty, invalidate cache
    labels_crud.reset_label_color(label_id, owner_uid)
    return jsonify({"status": "ok"})
