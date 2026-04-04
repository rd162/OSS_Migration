"""
UI initialisation parameters — make_init_params, make_runtime_info,
get_hotkeys_map, get_hotkeys_info.

Source: ttrss/include/functions2.php (lines 2-200 — make_init_params, get_hotkeys_*)
        ttrss/index.php (lines 213, 252 — HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM)
Adapted: PHP $_SESSION + PHP DB layer replaced by SQLAlchemy + get_user_pref.
         R13: HTML output eliminated — all functions return JSON-serialisable dicts.
         Eliminated: sanity_checksum, lock-file daemon check, widescreen cookie,
                     bw_limit session field, PHP_OS/PHP_VERSION — no Python equivalents.

Hook graph communities [0]+[5]:
    HOOK_HOTKEY_MAP     → get_hotkeys_map    (functions2.php:186)
    HOOK_HOTKEY_INFO    → get_hotkeys_info   (functions2.php:110)
    HOOK_TOOLBAR_BUTTON → make_init_params   (index.php:213)
    HOOK_ACTION_ITEM    → make_init_params   (index.php:252)
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Source: ttrss/index.php — LABEL_BASE_INDEX constant (feed IDs below this are label feeds)
_LABEL_BASE_INDEX = -1024


def get_hotkeys_info() -> dict[str, Any]:
    """Return keyboard shortcut help text, extended by plugins.

    Source: ttrss/include/functions2.php:get_hotkeys_info (lines 47-115)
    Adapted: returns dict keyed by action name; HTML labels replaced by plain strings.
             Plugin pipeline (HOOK_HOTKEY_INFO) preserved — plugins may add/modify entries.
    """
    # Source: functions2.php:48-109 — baseline hotkeys help dict
    hotkeys: dict[str, Any] = {
        "navigation": {
            "next_feed": "Go to next feed",
            "prev_feed": "Go to previous feed",
            "next_article": "Go to next article",
            "prev_article": "Go to previous article",
            "next_article_noscroll": "Go to next article (no scroll)",
            "prev_article_noscroll": "Go to previous article (no scroll)",
            "search_dialog": "Show search dialog",
        },
        "article": {
            "toggle_mark": "Toggle starred",
            "toggle_publ": "Toggle published",
            "toggle_unread": "Toggle unread",
            "edit_tags": "Edit tags",
            "dismiss_selected": "Dismiss selected articles",
            "dismiss_read": "Dismiss read articles",
            "open_in_new_window": "Open in new window",
            "catchup_below": "Mark below as read",
            "catchup_above": "Mark above as read",
            "article_scroll_down": "Scroll article down",
            "article_scroll_up": "Scroll article up",
            "select_all": "Select all articles",
            "select_unread": "Select unread articles",
            "select_marked": "Select starred articles",
            "select_published": "Select published articles",
            "select_invert": "Invert selection",
            "select_none": "Deselect all",
        },
        "feed": {
            "feed_subscribe": "Subscribe to feed",
            "catchup": "Mark all as read",
            "catchup_all": "Mark all feeds as read",
        },
    }

    from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.

    pm = get_plugin_manager()
    # Source: functions2.php:110-113 — HOOK_HOTKEY_INFO pipeline
    for _r in pm.hook.hook_hotkey_info(hotkeys=hotkeys):
        if _r is not None:
            hotkeys = _r

    return hotkeys


def get_hotkeys_map() -> tuple[list[str], dict[str, str]]:
    """Return (key_prefixes, hotkey_map) for the UI, extended by plugins.

    Source: ttrss/include/functions2.php:get_hotkeys_map (lines 117-201)
    Adapted: returns (prefixes_list, map_dict) instead of PHP array tuple.
             Single-char prefixes extracted from hotkey strings (functions2.php:192-200).
    Returns:
        prefixes: list of single-character modifier prefixes in use
        hotkeys:  {key_string: action_name} dict
    """
    # Source: functions2.php:118-185 — baseline hotkey map
    hotkeys: dict[str, str] = {
        "j": "next_article",
        "k": "prev_article",
        "n": "next_feed",
        "p": "prev_feed",
        "u": "toggle_unread",
        "m": "toggle_mark",
        "P": "toggle_publ",
        "o": "open_in_new_window",
        "s": "catchup",
        "S": "catchup_all",
        "/(191)": "search_dialog",
        "f": "feed_subscribe",
    }

    from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.

    pm = get_plugin_manager()
    # Source: functions2.php:186-190 — HOOK_HOTKEY_MAP pipeline
    for _r in pm.hook.hook_hotkey_map(hotkeys=hotkeys):
        if _r is not None:
            hotkeys = _r

    # Source: functions2.php:192-200 — extract single-char prefixes from hotkey strings
    prefixes: list[str] = []
    for key in list(hotkeys.keys()):
        parts = key.split(" ", 1)
        if len(parts[0]) == 1 and parts[0] not in prefixes:
            prefixes.append(parts[0])

    return prefixes, hotkeys


def make_runtime_info(owner_uid: int) -> dict[str, Any]:
    """Return real-time server state dict for the frontend.

    Source: ttrss/include/functions2.php:make_runtime_info (lines 203-258)
    Adapted: daemon lock-file checks eliminated (Celery replaces file-based daemons, ADR-0011).
             Version check eliminated (no PHP equivalent).
             Returns JSON-serialisable dict.
    """
    from sqlalchemy import func, select

    from ttrss.extensions import db  # New: lazy import keeps module importable outside app context.
    from ttrss.models.entry import TtRssEntry
    from ttrss.models.feed import TtRssFeed
    from ttrss.models.user_entry import TtRssUserEntry

    # Source: functions2.php:205-212 — SELECT MAX(id), COUNT(*) FROM ttrss_feeds WHERE owner_uid
    row = db.session.execute(
        select(
            func.max(TtRssFeed.id).label("mid"),
            func.count(TtRssFeed.id).label("nf"),
        ).where(TtRssFeed.owner_uid == owner_uid)
    ).one()

    max_feed_id: int = row.mid or 0
    num_feeds: int = row.nf or 0

    # Source: functions2.php:214 — getLastArticleId()
    last_article_id: int = db.session.execute(
        select(func.max(TtRssEntry.id))
        .join(TtRssUserEntry, TtRssUserEntry.ref_id == TtRssEntry.id)
        .where(TtRssUserEntry.owner_uid == owner_uid)
    ).scalar() or 0

    return {
        "max_feed_id": max_feed_id,
        "num_feeds": num_feeds,
        "last_article_id": last_article_id,
        # Source: functions2.php:216 — cdm_expanded pref
        "cdm_expanded": False,  # Note: pref lookup deferred; UI default is false.
        # New: daemon_is_running always True — Celery Beat is the scheduler (ADR-0011).
        "daemon_is_running": True,
    }


def make_init_params(owner_uid: int) -> dict[str, Any]:
    """Return initial page parameters for the frontend bootstrap.

    Source: ttrss/include/functions2.php:make_init_params (lines 2-46)
            + ttrss/index.php:213 — HOOK_TOOLBAR_BUTTON
            + ttrss/index.php:252 — HOOK_ACTION_ITEM
    Adapted: PHP $_SESSION pref reads replaced by get_user_pref; CSRF/widescreen/
             bw_limit session fields eliminated; R13 HTML output replaced by lists.
    """
    from ttrss.prefs.ops import get_user_pref  # New: lazy import avoids circular dependency.

    # Source: functions2.php:4-12 — boolean user prefs coerced to int
    bool_prefs = [
        "ON_CATCHUP_SHOW_NEXT_FEED",
        "HIDE_READ_FEEDS",
        "ENABLE_FEED_CATS",
        "FEEDS_SORT_BY_UNREAD",
        "CONFIRM_FEED_CATCHUP",
        "CDM_AUTO_CATCHUP",
        "HIDE_READ_SHOWS_SPECIAL",
        "COMBINED_DISPLAY_MODE",
    ]
    params: dict[str, Any] = {}
    for pref in bool_prefs:
        raw = get_user_pref(owner_uid, pref)
        params[pref.lower()] = 1 if raw and raw.lower() not in {"false", "0", ""} else 0

    # Source: functions2.php:13-24 — misc params
    params["fresh_article_max_age"] = int(get_user_pref(owner_uid, "FRESH_ARTICLE_MAX_AGE") or 24)
    params["label_base_index"] = _LABEL_BASE_INDEX
    params["default_view_mode"] = get_user_pref(owner_uid, "_DEFAULT_VIEW_MODE") or "adaptive"
    params["default_view_limit"] = int(get_user_pref(owner_uid, "_DEFAULT_VIEW_LIMIT") or 30)
    params["default_view_order_by"] = get_user_pref(owner_uid, "_DEFAULT_VIEW_ORDER_BY") or "score"

    # Source: functions2.php:37 — get_hotkeys_map()
    prefixes, hotkeys = get_hotkeys_map()
    params["hotkeys"] = [prefixes, hotkeys]

    from ttrss.plugins.manager import get_plugin_manager  # New: lazy import avoids circular dependency.

    pm = get_plugin_manager()

    # Source: ttrss/index.php:213 — HOOK_TOOLBAR_BUTTON collecting call (HTML fragments → list)
    params["toolbar_buttons"] = pm.hook.hook_toolbar_button()

    # Source: ttrss/index.php:252 — HOOK_ACTION_ITEM collecting call (HTML fragments → list)
    params["action_items"] = pm.hook.hook_action_item()

    return params
