"""DB service layer for filter preferences CRUD operations.

Source: ttrss/classes/pref/filters.php (Pref_Filters handler, 1054 lines)
Adapted: All db.session calls extracted from the pref/filters blueprint
         so that blueprint files remain free of direct DB access (AR-2).
"""
from __future__ import annotations

import json
import re

from sqlalchemy import delete as sa_delete, func, select, update

from ttrss.extensions import db
from ttrss.models.filter import (
    TtRssFilter2,
    TtRssFilter2Action,
    TtRssFilter2Rule,
    TtRssFilterAction,
    TtRssFilterType,
)
from ttrss.models.entry import TtRssEntry
from ttrss.models.feed import TtRssFeed
from ttrss.models.user_entry import TtRssUserEntry


# ---------------------------------------------------------------------------
# Filter tree
# ---------------------------------------------------------------------------


def get_filter_rows(owner_uid: int) -> list:
    """Return all TtRssFilter2 rows for *owner_uid*, ordered by order_id, title.

    Source: ttrss/classes/pref/filters.php:getfiltertree (line 159)
    """
    return db.session.execute(
        select(TtRssFilter2)
        .where(TtRssFilter2.owner_uid == owner_uid)
        .order_by(TtRssFilter2.order_id, TtRssFilter2.title)
    ).scalars().all()


def get_rule_reg_exps_for_filter(filter_id: int) -> list[str]:
    """Return list of reg_exp strings for a filter's rules (used for search matching).

    Source: ttrss/classes/pref/filters.php:getfiltertree (line 180-191)
    """
    return db.session.execute(
        select(TtRssFilter2Rule.reg_exp)
        .where(TtRssFilter2Rule.filter_id == filter_id)
    ).scalars().all()


def get_filter_name(filter_id: int) -> tuple[str, str]:
    """Return (title_with_rule_count, actions_summary) for display.

    Source: ttrss/classes/pref/filters.php:Pref_Filters::getRuleName (lines 398-421)
    Source: ttrss/classes/pref/filters.php:Pref_Filters::getActionName (lines 427-437)
    Source: ttrss/classes/pref/filters.php:getFilterName (line 944)
    """
    row = db.session.execute(
        select(
            TtRssFilter2.title,
            func.count(TtRssFilter2Rule.id.distinct()).label("num_rules"),
            func.count(TtRssFilter2Action.id.distinct()).label("num_actions"),
        )
        .outerjoin(TtRssFilter2Rule, TtRssFilter2Rule.filter_id == TtRssFilter2.id)
        .outerjoin(TtRssFilter2Action, TtRssFilter2Action.filter_id == TtRssFilter2.id)
        .where(TtRssFilter2.id == filter_id)
        .group_by(TtRssFilter2.title)
    ).one_or_none()

    if row is None:
        return ("[Unknown]", "")

    title = row.title or "[No caption]"
    num_rules = row.num_rules
    title = f"{title} ({num_rules} rule{'s' if num_rules != 1 else ''})"

    # Source: ttrss/classes/pref/filters.php:getFilterName — first action description
    first_action = db.session.execute(
        select(TtRssFilter2Action, TtRssFilterAction.description)
        .join(TtRssFilterAction, TtRssFilterAction.id == TtRssFilter2Action.action_id)
        .where(TtRssFilter2Action.filter_id == filter_id)
        .order_by(TtRssFilter2Action.id)
        .limit(1)
    ).one_or_none()

    actions_str = ""
    if first_action:
        actions_str = first_action.description or ""
        if first_action[0].action_id in (4, 6, 7):
            actions_str += f": {first_action[0].action_param}"

        remaining = row.num_actions - 1
        if remaining > 0:
            actions_str += f" (+{remaining} action{'s' if remaining != 1 else ''})"

    return (title, actions_str)


# ---------------------------------------------------------------------------
# Create / update filter
# ---------------------------------------------------------------------------


def create_filter(
    owner_uid: int,
    *,
    enabled: bool,
    match_any_rule: bool,
    inverse: bool,
    title: str,
) -> TtRssFilter2:
    """INSERT a new TtRssFilter2 row and flush (does NOT commit).

    Source: ttrss/classes/pref/filters.php:add (line 581-583)
    """
    new_filter = TtRssFilter2(
        owner_uid=owner_uid,
        match_any_rule=match_any_rule,
        enabled=enabled,
        title=title,
        inverse=inverse,
    )
    db.session.add(new_filter)
    db.session.flush()
    return new_filter


def update_filter(
    filter_id: int,
    owner_uid: int,
    *,
    enabled: bool,
    match_any_rule: bool,
    inverse: bool,
    title: str,
) -> None:
    """UPDATE core fields of a filter row (does NOT commit).

    Source: ttrss/classes/pref/filters.php:editSave (line 457-462)
    """
    db.session.execute(
        update(TtRssFilter2)
        .where(TtRssFilter2.id == filter_id, TtRssFilter2.owner_uid == owner_uid)
        .values(enabled=enabled, match_any_rule=match_any_rule, inverse=inverse, title=title)
    )


def commit_filter() -> None:
    """Commit the current DB transaction."""
    db.session.commit()


# ---------------------------------------------------------------------------
# Read filter (edit data)
# ---------------------------------------------------------------------------


def fetch_filter(filter_id: int, owner_uid: int):
    """Return TtRssFilter2 ORM object or None if not found / not owned.

    Source: ttrss/classes/pref/filters.php:edit (line 234)
    """
    return db.session.execute(
        select(TtRssFilter2)
        .where(TtRssFilter2.id == filter_id, TtRssFilter2.owner_uid == owner_uid)
    ).scalar_one_or_none()


def fetch_filter_rules(filter_id: int) -> list:
    """Return TtRssFilter2Rule rows for a filter, ordered by reg_exp, id.

    Source: ttrss/classes/pref/filters.php:edit (line 282-301)
    """
    return db.session.execute(
        select(TtRssFilter2Rule)
        .where(TtRssFilter2Rule.filter_id == filter_id)
        .order_by(TtRssFilter2Rule.reg_exp, TtRssFilter2Rule.id)
    ).scalars().all()


def fetch_filter_actions(filter_id: int) -> list:
    """Return TtRssFilter2Action rows for a filter, ordered by id.

    Source: ttrss/classes/pref/filters.php:edit (line 330-344)
    """
    return db.session.execute(
        select(TtRssFilter2Action)
        .where(TtRssFilter2Action.filter_id == filter_id)
        .order_by(TtRssFilter2Action.id)
    ).scalars().all()


# ---------------------------------------------------------------------------
# Delete filter
# ---------------------------------------------------------------------------


def delete_filter(filter_id: int, owner_uid: int) -> None:
    """DELETE a filter row and commit.

    Source: ttrss/classes/pref/filters.php:remove (line 468)
    """
    db.session.execute(
        sa_delete(TtRssFilter2)
        .where(TtRssFilter2.id == filter_id, TtRssFilter2.owner_uid == owner_uid)
    )
    db.session.commit()


# ---------------------------------------------------------------------------
# Save rules and actions
# ---------------------------------------------------------------------------


def save_rules_and_actions(filter_id: int, rules_json_list: list[str], actions_json_list: list[str]) -> None:
    """Replace all rules and actions for a filter from JSON-encoded lists.

    Source: ttrss/classes/pref/filters.php:saveRulesAndActions (line 477)
    Caller must pass request.form.getlist("rule") and request.form.getlist("action").
    Does NOT commit — caller is responsible.

    Uses a savepoint so that if insertions fail after deletions, the filter is not left
    with no rules/actions (PHP wraps in BEGIN/COMMIT: filters.php:577,592).
    """
    import re as _re
    # Wrap in savepoint so deletion + re-insertion is atomic
    with db.session.begin_nested():
        # Source: ttrss/classes/pref/filters.php:479-480 — delete existing
        db.session.execute(sa_delete(TtRssFilter2Rule).where(TtRssFilter2Rule.filter_id == filter_id))
        db.session.execute(sa_delete(TtRssFilter2Action).where(TtRssFilter2Action.filter_id == filter_id))

        # Source: ttrss/classes/pref/filters.php:488-536 — insert rules
        seen_rules: list = []
        for r_json in rules_json_list:
            try:
                rule = json.loads(r_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if not rule or rule in seen_rules:
                continue
            seen_rules.append(rule)

            reg_exp = (rule.get("reg_exp") or "").strip()
            if not reg_exp:
                continue

            # Source: ttrss/classes/pref/filters.php:509 — validate regex before saving
            try:
                _re.compile(reg_exp)
            except _re.error:
                continue  # skip invalid regex silently (matches PHP @preg_match pattern)

            inverse = rule.get("inverse", False)
            filter_type = int(rule.get("filter_type", 1))
            feed_id_val = str(rule.get("feed_id", "")).strip()

            cat_filter = False
            cat_id = None
            feed_id = None

            # Source: ttrss/classes/pref/filters.php:515-528
            if feed_id_val.startswith("CAT:"):
                cat_filter = True
                cat_id_raw = int(feed_id_val[4:]) if feed_id_val[4:] else None
                cat_id = cat_id_raw if cat_id_raw else None
            else:
                feed_id_int = int(feed_id_val) if feed_id_val and feed_id_val.lstrip("-").isdigit() else None
                feed_id = feed_id_int if feed_id_int else None

            db.session.add(TtRssFilter2Rule(
                filter_id=filter_id,
                reg_exp=reg_exp,
                filter_type=filter_type,
                feed_id=feed_id,
                cat_id=cat_id,
                cat_filter=cat_filter,
                inverse=bool(inverse),
            ))

        # Source: ttrss/classes/pref/filters.php:538-560 — insert actions
        seen_actions: list = []
        for a_json in actions_json_list:
            try:
                action = json.loads(a_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if not action or action in seen_actions:
                continue
            seen_actions.append(action)

            action_id = int(action.get("action_id", 1))
            action_param = action.get("action_param", "")
            action_param_label = action.get("action_param_label", "")

            # Source: ttrss/classes/pref/filters.php:545-551
            if action_id == 7:
                action_param = action_param_label
            if action_id == 6:
                action_param = str(int(str(action_param).replace("+", "") or "0"))

            db.session.add(TtRssFilter2Action(
                filter_id=filter_id,
                action_id=action_id,
                action_param=action_param,
            ))


# ---------------------------------------------------------------------------
# Filter order
# ---------------------------------------------------------------------------


def save_filter_order(owner_uid: int, filter_id_order: list[int]) -> None:
    """Update order_id for each filter_id in the given sequence, then commit.

    Source: ttrss/classes/pref/filters.php:savefilterorder (line 28-41)
    """
    for index, filter_id in enumerate(filter_id_order):
        db.session.execute(
            update(TtRssFilter2)
            .where(TtRssFilter2.id == filter_id, TtRssFilter2.owner_uid == owner_uid)
            .values(order_id=index)
        )
    db.session.commit()


def reset_filter_order(owner_uid: int) -> None:
    """Set order_id=0 on all filters for owner_uid, then commit.

    Source: ttrss/classes/pref/filters.php:filtersortreset (line 11)
    """
    db.session.execute(
        update(TtRssFilter2)
        .where(TtRssFilter2.owner_uid == owner_uid)
        .values(order_id=0)
    )
    db.session.commit()


# ---------------------------------------------------------------------------
# Join (merge) filters
# ---------------------------------------------------------------------------


def join_filters(owner_uid: int, base_id: int, merge_ids: list[int]) -> None:
    """Move rules/actions from *merge_ids* into *base_id*, delete merged filters,
    set match_any_rule on base, optimize, then commit.

    Source: ttrss/classes/pref/filters.php:join (line 979)
    """
    if not merge_ids:
        return

    # D01 security: restrict merge_ids to filters owned by owner_uid before moving rules/actions.
    # Without this check, an attacker could move rules from other users' filters into base_id.
    owned_merge_ids_subq = (
        select(TtRssFilter2.id)
        .where(TtRssFilter2.id.in_(merge_ids))
        .where(TtRssFilter2.owner_uid == owner_uid)
        .scalar_subquery()
    )
    # Also verify base_id is owned by owner_uid
    base_owned = db.session.execute(
        select(TtRssFilter2.id)
        .where(TtRssFilter2.id == base_id)
        .where(TtRssFilter2.owner_uid == owner_uid)
    ).scalar_one_or_none()
    if base_owned is None:
        return  # base filter not owned by caller — abort

    # Source: ttrss/classes/pref/filters.php:986-993 — move rules and actions
    db.session.execute(
        update(TtRssFilter2Rule)
        .where(TtRssFilter2Rule.filter_id.in_(owned_merge_ids_subq))
        .values(filter_id=base_id)
    )
    db.session.execute(
        update(TtRssFilter2Action)
        .where(TtRssFilter2Action.filter_id.in_(owned_merge_ids_subq))
        .values(filter_id=base_id)
    )

    # Source: ttrss/classes/pref/filters.php:992 — delete merged filters
    db.session.execute(
        sa_delete(TtRssFilter2)
        .where(TtRssFilter2.id.in_(merge_ids), TtRssFilter2.owner_uid == owner_uid)
    )

    # Source: ttrss/classes/pref/filters.php:993 — set match_any_rule on base
    db.session.execute(
        update(TtRssFilter2)
        .where(TtRssFilter2.id == base_id)
        .values(match_any_rule=True)
    )

    # Source: ttrss/classes/pref/filters.php:997 — optimize (remove duplicates)
    optimize_filter(base_id)

    db.session.commit()


def optimize_filter(filter_id: int) -> None:
    """Remove duplicate rules and actions from a filter (does NOT commit).

    Source: ttrss/classes/pref/filters.php:optimizeFilter (line 1002)
    """
    # Deduplicate actions
    actions = db.session.execute(
        select(TtRssFilter2Action).where(TtRssFilter2Action.filter_id == filter_id)
    ).scalars().all()
    seen: list = []
    dupe_ids = []
    for a in actions:
        key = (a.action_id, a.action_param)
        if key in seen:
            dupe_ids.append(a.id)
        else:
            seen.append(key)
    if dupe_ids:
        db.session.execute(
            sa_delete(TtRssFilter2Action).where(TtRssFilter2Action.id.in_(dupe_ids))
        )

    # Deduplicate rules
    rules = db.session.execute(
        select(TtRssFilter2Rule).where(TtRssFilter2Rule.filter_id == filter_id)
    ).scalars().all()
    seen = []
    dupe_ids = []
    for r in rules:
        key = (r.reg_exp, r.filter_type, r.feed_id, r.cat_id, r.cat_filter, r.inverse)
        if key in seen:
            dupe_ids.append(r.id)
        else:
            seen.append(key)
    if dupe_ids:
        db.session.execute(
            sa_delete(TtRssFilter2Rule).where(TtRssFilter2Rule.id.in_(dupe_ids))
        )


# ---------------------------------------------------------------------------
# Test filter — DB-side data fetching
# ---------------------------------------------------------------------------


def fetch_filter_type_map() -> dict[int, str]:
    """Return mapping of filter_type id -> name from ttrss_filter_types.

    Source: ttrss/classes/pref/filters.php:testFilter (line 56-84)
    """
    rows = db.session.execute(select(TtRssFilterType.id, TtRssFilterType.name)).all()
    return {tr.id: tr.name for tr in rows}


def fetch_recent_articles_for_test(owner_uid: int, limit: int = 30) -> list:
    """Return recent article rows for filter testing.

    Source: ttrss/classes/pref/filters.php:testFilter (line 86-88)
    Each row has: title, content, link, author, date_entered, feed_title.
    """
    return db.session.execute(
        select(
            TtRssEntry.title,
            TtRssEntry.content,
            TtRssEntry.link,
            TtRssEntry.author,
            TtRssEntry.date_entered,
            TtRssFeed.title.label("feed_title"),
        )
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .outerjoin(TtRssFeed, TtRssFeed.id == TtRssUserEntry.feed_id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
        .order_by(TtRssEntry.date_entered.desc())
        .limit(limit)
    ).all()
