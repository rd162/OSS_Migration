"""Pref_Filters handler — filter preferences, HOOK_PREFS_TAB.

Source: ttrss/classes/pref/filters.php (Pref_Filters handler, 1054 lines)
Adapted: PHP handler class replaced by Flask Blueprint routes.
         Delegation to filters_crud per AR-2 (no direct SQL here).
         HTML output eliminated — endpoints return JSON (R13).
"""
from __future__ import annotations

import structlog
from flask import jsonify, request
from flask_login import current_user, login_required

from ttrss.blueprints.prefs.views import prefs_bp
from ttrss.prefs import filters_crud

logger = structlog.get_logger(__name__)


def _owner_uid() -> int:
    """Return the current user's ID safely."""
    return getattr(current_user, "id", None) or 0


# ---------------------------------------------------------------------------
# Filter list (tab content)
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters", methods=["GET"])
@login_required
def filters():
    """Return filter list and plugin-provided content for the filters preferences tab.

    Source: ttrss/classes/pref/filters.php:159 — getfiltertree
            ttrss/classes/pref/filters.php:695 — run_hooks(HOOK_PREFS_TAB)
    Adapted: HTML tab content replaced by JSON payload.
    """
    from ttrss.plugins.manager import get_plugin_manager

    owner_uid = _owner_uid()
    pm = get_plugin_manager()

    # Source: ttrss/classes/pref/filters.php:159 — getfiltertree — return all filters
    filter_rows = filters_crud.get_filter_rows(owner_uid)
    filter_list = []
    for f in filter_rows:
        reg_exps = filters_crud.get_rule_reg_exps_for_filter(f.id)
        title, actions_str = filters_crud.get_filter_name(f.id)
        filter_list.append({
            "id": f.id,
            "title": title,
            "actions": actions_str,
            "enabled": f.enabled,
            "match_any_rule": f.match_any_rule,
            "inverse": f.inverse,
            "reg_exps": list(reg_exps),
        })

    # Source: ttrss/classes/pref/filters.php:695 — HOOK_PREFS_TAB (fire-and-forget, collecting)
    plugin_tab_content = pm.hook.hook_prefs_tab()

    return jsonify({
        "filters": filter_list,
        "plugin_tab_content": plugin_tab_content,
    })


# ---------------------------------------------------------------------------
# Filter edit data
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters/<int:filter_id>", methods=["GET"])
@login_required
def edit_filter(filter_id: int):
    """Return filter row, rules, and actions for the edit dialog.

    Source: ttrss/classes/pref/filters.php:234 — edit
    """
    owner_uid = _owner_uid()

    f = filters_crud.fetch_filter(filter_id, owner_uid)
    if f is None:
        return jsonify({"error": "filter_not_found"}), 404

    rules = filters_crud.fetch_filter_rules(filter_id)
    actions = filters_crud.fetch_filter_actions(filter_id)

    return jsonify({
        "id": f.id,
        "title": f.title,
        "enabled": f.enabled,
        "match_any_rule": f.match_any_rule,
        "inverse": f.inverse,
        "rules": [
            {
                "id": r.id,
                "reg_exp": r.reg_exp,
                "filter_type": r.filter_type,
                "feed_id": r.feed_id,
                "cat_id": r.cat_id,
                "cat_filter": r.cat_filter,
                "inverse": r.inverse,
            }
            for r in rules
        ],
        "actions": [
            {
                "id": a.id,
                "action_id": a.action_id,
                "action_param": a.action_param,
            }
            for a in actions
        ],
    })


# ---------------------------------------------------------------------------
# Create / update filter
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters", methods=["POST"])
@login_required
def add_filter():
    """Create a new filter with rules and actions.

    Source: ttrss/classes/pref/filters.php:Pref_Filters::newfilter (lines 702-793)
    Source: ttrss/classes/pref/filters.php:581 — add
    """
    owner_uid = _owner_uid()

    enabled = request.form.get("enabled", "true").lower() in ("1", "true", "on")
    match_any_rule = request.form.get("match_any_rule", "false").lower() in ("1", "true", "on")
    inverse = request.form.get("inverse", "false").lower() in ("1", "true", "on")
    title = request.form.get("title", "").strip()

    # Source: ttrss/classes/pref/filters.php:581-583 — INSERT new filter row
    new_filter = filters_crud.create_filter(
        owner_uid,
        enabled=enabled,
        match_any_rule=match_any_rule,
        inverse=inverse,
        title=title,
    )

    # Source: ttrss/classes/pref/filters.php:477 — saveRulesAndActions
    rules_json = request.form.getlist("rule")
    actions_json = request.form.getlist("action")
    filters_crud.save_rules_and_actions(new_filter.id, rules_json, actions_json)
    filters_crud.commit_filter()

    return jsonify({"status": "ok", "filter_id": new_filter.id})


@prefs_bp.route("/filters/<int:filter_id>", methods=["POST"])
@login_required
def save_filter(filter_id: int):
    """Update an existing filter's core fields, rules, and actions.

    Source: ttrss/classes/pref/filters.php:457 — editSave
    """
    owner_uid = _owner_uid()

    enabled = request.form.get("enabled", "true").lower() in ("1", "true", "on")
    match_any_rule = request.form.get("match_any_rule", "false").lower() in ("1", "true", "on")
    inverse = request.form.get("inverse", "false").lower() in ("1", "true", "on")
    title = request.form.get("title", "").strip()

    # Source: ttrss/classes/pref/filters.php:457-462 — UPDATE filter core fields
    filters_crud.update_filter(
        filter_id,
        owner_uid,
        enabled=enabled,
        match_any_rule=match_any_rule,
        inverse=inverse,
        title=title,
    )

    # Source: ttrss/classes/pref/filters.php:477 — saveRulesAndActions
    rules_json = request.form.getlist("rule")
    actions_json = request.form.getlist("action")
    filters_crud.save_rules_and_actions(filter_id, rules_json, actions_json)
    filters_crud.commit_filter()

    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Delete filter
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters/<int:filter_id>", methods=["DELETE"])
@login_required
def delete_filter(filter_id: int):
    """Delete a filter and its rules/actions.

    Source: ttrss/classes/pref/filters.php:468 — remove
    """
    owner_uid = _owner_uid()
    filters_crud.delete_filter(filter_id, owner_uid)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Filter order
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters/order", methods=["POST"])
@login_required
def save_filter_order():
    """Update order_id for each filter in the given sequence.

    Source: ttrss/classes/pref/filters.php:28 — savefilterorder
    """
    owner_uid = _owner_uid()
    payload = request.get_json(force=True, silent=True) or {}
    filter_ids = [int(fid) for fid in payload.get("ids", []) if str(fid).lstrip("-").isdigit()]
    filters_crud.save_filter_order(owner_uid, filter_ids)
    return jsonify({"status": "ok"})


@prefs_bp.route("/filters/order/reset", methods=["POST"])
@login_required
def reset_filter_order():
    """Set order_id=0 on all filters for current user.

    Source: ttrss/classes/pref/filters.php:11 — filtersortreset
    """
    owner_uid = _owner_uid()
    filters_crud.reset_filter_order(owner_uid)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Join (merge) filters
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters/join", methods=["POST"])
@login_required
def join_filters():
    """Move rules/actions from merge_ids into base_id and delete merged filters.

    Source: ttrss/classes/pref/filters.php:979 — join
    """
    owner_uid = _owner_uid()
    base_id = int(request.form.get("base_id", 0))
    merge_ids_raw = request.form.getlist("merge_ids[]") or request.form.getlist("merge_ids")
    merge_ids = [int(mid) for mid in merge_ids_raw if str(mid).lstrip("-").isdigit()]
    if not base_id or not merge_ids:
        return jsonify({"error": "base_id and merge_ids required"}), 400
    filters_crud.join_filters(owner_uid, base_id, merge_ids)
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Test filter
# ---------------------------------------------------------------------------


@prefs_bp.route("/filters/test", methods=["POST"])
@login_required
def test_filter():
    """Test filter rules against recent articles and return matching article titles.

    Source: ttrss/classes/pref/filters.php:56 — testFilter
    """
    import json as _json
    import re

    owner_uid = _owner_uid()

    # Source: ttrss/classes/pref/filters.php:56-84 — load filter type map
    type_map = filters_crud.fetch_filter_type_map()

    # Source: ttrss/classes/pref/filters.php:86-88 — recent articles
    articles = filters_crud.fetch_recent_articles_for_test(owner_uid)

    rules_json = request.form.getlist("rule")
    matched = []
    for row in articles:
        for r_json in rules_json:
            try:
                rule = _json.loads(r_json)
            except (_json.JSONDecodeError, TypeError):
                continue
            filter_type = int(rule.get("filter_type", 1))
            reg_exp = (rule.get("reg_exp") or "").strip()
            if not reg_exp:
                continue
            field_name = type_map.get(filter_type, "title")
            field_value = getattr(row, field_name, "") or ""
            try:
                if re.search(reg_exp, field_value, re.IGNORECASE):
                    matched.append({
                        "title": row.title,
                        "feed_title": row.feed_title,
                    })
                    break
            except re.error:
                pass

    return jsonify({"matched": matched, "total": len(articles)})
