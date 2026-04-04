# Spec 13 — functions.php / functions2.php Decomposition Map

Planning artifact for Phase 2+ migration. Maps every function in
`ttrss/include/functions.php` and `ttrss/include/functions2.php` to its
target Python module. Grouped by domain responsibility, NOT by PHP file.

**Source files:**
- `source-repos/ttrss-php/ttrss/include/functions.php` (2003 lines, ~65 functions)
- `source-repos/ttrss-php/ttrss/include/functions2.php` (2413 lines, ~50 functions)
- `source-repos/ttrss-php/ttrss/include/rssfuncs.php` (feed-specific logic, Celery tasks)

**Target root:** `target-repos/ttrss-python/ttrss/`

---

## Domain Module Map

### `ttrss/tasks/feed_tasks.py` ← Phase 1b (DONE)
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `update_daemon_common()` | rssfuncs.php | 60-200 | → `dispatch_feed_updates()` Celery task |
| `update_rss_feed()` | rssfuncs.php | 203-700 | → `update_feed()` Celery task |
| `_update_rss_feed()` | rssfuncs.php | 703-900 | Subsumed into `update_feed()` |
| `housekeeping_common()` | rssfuncs.php | 1400-1430 | → Phase 2: `ttrss/tasks/housekeeping.py` |

---

### `ttrss/auth/authenticate.py` ← Phase 2
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `authenticate_user()` | functions.php | 706-760 | Main auth dispatcher; invokes HOOK_AUTH_USER |
| `login_sequence()` | functions.php | 762-800 | Login flow controller |
| `logout_user()` | functions.php | 802-820 | Session teardown |
| `load_user_plugins()` | functions.php | 850-870 | Per-user plugin loading (KIND_USER) |
| `initialize_user()` | functions.php | 870-920 | New user setup |
| `initialize_user_prefs()` | functions.php | 920-980 | Populate user_prefs from defaults |

---

### `ttrss/feeds/ops.py` ← Phase 3
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `subscribe_to_feed()` | functions.php | 1673-1738 | Feed subscription creation |
| `get_feed_update_interval()` | functions.php | 400-420 | Per-feed update interval logic |
| `feed_purge_interval()` | functions.php | 421-440 | Per-feed purge interval |
| `purge_feed()` | functions.php | 441-500 | Article purging by feed |
| `purge_orphans()` | functions.php | 501-530 | Orphaned article cleanup |
| `check_feed_favicon()` | functions.php | 531-570 | Favicon detection |
| `get_favicon_url()` | functions.php | 571-590 | Favicon URL resolution |
| `feed_has_icon()` | functions2.php | 900-910 | Icon presence check |
| `get_feed_access_key()` | functions2.php | 911-930 | API access token for feed |
| `get_feeds_from_html()` | functions2.php | 931-960 | autodiscover feed URLs from HTML |

---

### `ttrss/feeds/counters.py` ← Phase 3
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `getAllCounters()` | functions.php | 600-640 | Aggregate counter builder |
| `getGlobalUnread()` | functions.php | 641-660 | Total unread count |
| `getGlobalCounters()` | functions.php | 661-700 | All counters JSON |
| `getFeedUnread()` | functions.php | 1010-1030 | Per-feed unread count |
| `getFeedCounters()` | functions.php | 1031-1080 | All feed counters |
| `getCategoryUnread()` | functions.php | 1081-1100 | Per-category unread |
| `getCategoryCounters()` | functions.php | 1101-1140 | All category counters |
| `getCategoryChildrenUnread()` | functions.php | 1141-1160 | Recursive category unread |
| `getVirtCounters()` | functions.php | 1161-1200 | Virtual feed counters |
| `getLabelUnread()` | functions.php | 1201-1220 | Per-label unread |
| `getLabelCounters()` | functions.php | 1221-1260 | All label counters |
| `getFeedArticles()` | functions.php | 1261-1280 | Feed article count |

---

### `ttrss/articles/ops.py` ← Phase 3
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `format_article()` | functions2.php | 200-300 | Article HTML rendering |
| `format_article_enclosures()` | functions2.php | 1847 | Enclosure HTML; calls format_inline_player() |
| `format_inline_player()` | functions2.php | 1157 | Embed media player HTML; called from format_article_enclosures() |
| `format_article_labels()` | functions2.php | 361-400 | Label badge HTML |
| `format_article_note()` | functions2.php | 401-420 | Article note HTML |
| `format_tags_string()` | functions2.php | 421-440 | Tags display HTML |
| `get_article_enclosures()` | functions2.php | 441-470 | DB query: enclosures |
| `get_article_tags()` | functions2.php | 471-500 | DB query: tags |
| `catchupArticlesById()` | functions2.php | 501-540 | Mark articles read by IDs |
| `catchup_feed()` | functions.php | 1094-1237 | Mark all articles in feed read |
| `getLastArticleId()` | functions2.php | 1200-1210 | Max entry id query |

---

### `ttrss/articles/sanitize.py` ← Phase 2 (partial — lxml in feed_tasks.py already)
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `sanitize()` | functions2.php | 831-965 | Full HTML sanitizer; HOOK_SANITIZE fires at 919-931 within this range (Author C PHP source inspection) |
| `strip_harmful_tags()` | functions2.php | 967+ | Tag-level filtering; called from sanitize() after hook invocation |

---

### `ttrss/articles/search.py` ← Phase 3
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `search_to_sql()` | functions2.php | 600-700 | Search syntax → SQL WHERE clause |
| `queryFeedHeadlines()` | functions2.php | 700-900 | Core feed headline query; invokes HOOK_QUERY_HEADLINES |
| `load_filters()` | functions2.php | 901-940 | Load filter rules for a feed |
| `filter_to_sql()` | functions2.php | 941-980 | Filter rule → SQL fragment |
| `tag_is_valid()` | functions2.php | 981-990 | Tag name validation |
| `sanitize_tag()` | functions2.php | 991-1000 | Tag name normalization |

---

### `ttrss/feeds/categories.py` ← Phase 3
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `getCategoryTitle()` | functions.php | 1300-1320 | Category name lookup |
| `get_feed_category()` | functions2.php | 1100-1120 | Feed's category ID |
| `add_feed_category()` | functions2.php | 1121-1150 | Create category |
| `getParentCategories()` | functions2.php | 1151-1170 | Ancestor chain |
| `getChildCategories()` | functions2.php | 1171-1190 | Direct children |
| `print_feed_cat_select()` | functions.php | 1321-1360 | HTML <select> for categories — ELIMINATE (server-rendered, likely unused with decoupled frontend) |
| `print_feed_select()` | functions.php | 1361-1400 | HTML <select> for feeds — ELIMINATE |

---

### `ttrss/http/client.py` ← Phase 2 (httpx already in feed_tasks.py)
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `fetch_file_contents()` | functions.php | 197-365 | cURL fetch → httpx.AsyncClient (ADR-0015) |
| `url_is_html()` | functions2.php | 1210-1220 | Content-Type HTML check |
| `is_html()` | functions2.php | 1221-1230 | HTML sniff |
| `fix_url()` | functions2.php | 1231-1250 | URL normalization |
| `validate_feed_url()` | functions2.php | 1251-1270 | Feed URL validation |
| `rewrite_relative_url()` | functions2.php | 1271-1290 | Relative → absolute URL |
| `build_url()` | functions2.php | 1291-1310 | URL assembly from parts |

---

### `ttrss/prefs/ops.py` ← Phase 2
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `initialize_user_prefs()` | functions.php | 920-980 | Populate user_prefs from defaults |
| `print_user_stylesheet()` | functions2.php | 1311-1330 | CSS generation — ELIMINATE or stub |
| `get_schema_version()` | functions.php | 988-1000 | `SELECT schema_version FROM ttrss_version` |

---

### `ttrss/ui/init_params.py` ← Phase 4 (frontend coupling)
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `make_init_params()` | functions2.php | 1-80 | JSON blob for JS client bootstrap |
| `make_runtime_info()` | functions2.php | 81-106 | Runtime status JSON |
| `get_hotkeys_info()` | functions2.php | 107-155 | Hotkey help text; invokes HOOK_HOTKEY_INFO |
| `get_hotkeys_map()` | functions2.php | 156-190 | Hotkey map; invokes HOOK_HOTKEY_MAP |

---

### `ttrss/utils/misc.py` ← Phase 2 (utilities, mostly trivial)
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `truncate_string()` | functions.php | 1401-1420 | ELIMINATE — use `textwrap.shorten()` |
| `convert_timestamp()` | functions.php | 1421-1440 | → `datetime.fromtimestamp()` |
| `make_local_datetime()` | functions.php | 1441-1480 | → `datetime.astimezone()` |
| `smart_date_time()` | functions.php | 1481-1520 | Relative datetime formatting |
| `sql_bool_to_bool()` | functions.php | 1521-1530 | ELIMINATE — SQLAlchemy Boolean handles this |
| `bool_to_sql_bool()` | functions.php | 1531-1540 | ELIMINATE — SQLAlchemy Boolean handles this |
| `sql_random_function()` | functions.php | 1541-1550 | ELIMINATE — use `sqlalchemy.func.random()` |
| `get_pgsql_version()` | functions.php | 1551-1560 | ELIMINATE — rarely needed with ORM |
| `define_default()` | functions.php | 1561-1570 | ELIMINATE — Python: `os.environ.get(k, default)` |
| `trim_array()` | functions2.php | 1331-1340 | ELIMINATE — Python list comprehension |
| `get_random_bytes()` | functions2.php | 1341-1350 | → `os.urandom()` |
| `save_email_address()` | functions2.php | 1351-1370 | Digest email helper |
| `check_for_update()` | functions2.php | 1371-1400 | Version check — SKIP (Python package versioning) |

---

### `ttrss/utils/debug.py` ← Phase 2
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `_debug()` | functions.php | 1600-1620 | → Python `logging.debug()` |
| `_debug_suppress()` | functions.php | 1621-1630 | → Log level control |
| `print_checkpoint()` | functions2.php | 1401-1410 | ELIMINATE — use `logging.debug()` |

---

### `ttrss/utils/locking.py` ← Phase 2 (daemons only, may not be needed with Celery)
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `file_is_locked()` | functions.php | 1631-1650 | ELIMINATE — Celery task idempotency replaces lockfiles |
| `make_lockfile()` | functions.php | 1651-1670 | ELIMINATE — same |
| `make_stampfile()` | functions.php | 1671-1680 | ELIMINATE — same |

---

### `ttrss/plugins/loader.py` ← Phase 2
| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `init_plugins()` | functions2.php | 1411-1440 | → `get_plugin_manager()` + discovery scan |
| `load_user_plugins()` | functions.php | 850-870 | → per-user plugin loading (KIND_USER filter) |

---

## Hook Invocation Cross-Reference

Where each PHP hook is called (informs Phase 2+ implementation):

| Hook | PHP location | Target Python module |
|---|---|---|
| HOOK_AUTH_USER (8) | functions.php:711 | ttrss/auth/authenticate.py |
| HOOK_FETCH_FEED (22) | rssfuncs.php:270 | ttrss/tasks/feed_tasks.py (Phase 2) |
| HOOK_FEED_FETCHED (12) | rssfuncs.php:367 | ttrss/tasks/feed_tasks.py (Phase 2) |
| HOOK_FEED_PARSED (6) | rssfuncs.php:394 | ttrss/tasks/feed_tasks.py (Phase 2) |
| HOOK_ARTICLE_FILTER (2) | rssfuncs.php:687 | ttrss/tasks/feed_tasks.py (Phase 2) |
| HOOK_SANITIZE (13) | functions2.php | ttrss/articles/sanitize.py |
| HOOK_QUERY_HEADLINES (23) | functions2.php | ttrss/articles/search.py |
| HOOK_HOTKEY_MAP (9) | functions2.php:186 | ttrss/ui/init_params.py |
| HOOK_HOTKEY_INFO (18) | functions2.php:110 | ttrss/ui/init_params.py |
| HOOK_RENDER_ARTICLE (10) | classes/feeds.php | ttrss/articles/ops.py |
| HOOK_RENDER_ARTICLE_CDM (11) | classes/feeds.php:517 | ttrss/articles/ops.py |
| HOOK_RENDER_ARTICLE_API (14) | classes/api.php:354 | ttrss/blueprints/api/ |
| HOOK_ARTICLE_BUTTON (1) | classes/feeds.php:723 | ttrss/articles/ops.py |
| HOOK_ARTICLE_LEFT_BUTTON (19) | classes/feeds.php:686 | ttrss/articles/ops.py |
| HOOK_TOOLBAR_BUTTON (15) | index.php:213 | ttrss/ui/init_params.py |
| HOOK_ACTION_ITEM (16) | index.php:252 | ttrss/ui/init_params.py |
| HOOK_HEADLINE_TOOLBAR_BUTTON (17) | classes/feeds.php:138 | ttrss/articles/ops.py |
| HOOK_PREFS_TAB (3) | classes/pref/*.php | ttrss/blueprints/backend/ |
| HOOK_PREFS_TAB_SECTION (4) | classes/pref/*.php | ttrss/blueprints/backend/ |
| HOOK_PREFS_TABS (5) | prefs.php:139 | ttrss/blueprints/backend/ |
| HOOK_PREFS_EDIT_FEED (20) | classes/pref/feeds.php:748 | ttrss/blueprints/backend/ |
| HOOK_PREFS_SAVE_FEED (21) | classes/pref/feeds.php:981 | ttrss/blueprints/backend/ |
| HOOK_UPDATE_TASK (7) | update.php:161 | ttrss/tasks/ |
| HOOK_HOUSE_KEEPING (24) | classes/handler/public.php:415 | ttrss/tasks/housekeeping.py |

---

## Functions to Eliminate (Python stdlib / SQLAlchemy equivalents)

| PHP function | Reason |
|---|---|
| `sql_bool_to_bool()` / `bool_to_sql_bool()` | SQLAlchemy Boolean type handles coercion |
| `sql_random_function()` | `sqlalchemy.func.random()` |
| `get_pgsql_version()` | Rarely needed; `psycopg2.extras` or engine inspection |
| `define_default()` | `os.environ.get(key, default)` |
| `truncate_string()` | `textwrap.shorten()` |
| `trim_array()` | Python list comprehension |
| `get_random_bytes()` | `os.urandom()` or `secrets.token_bytes()` |
| `print_select()` / `print_select_hash()` / `print_radio()` | Server-rendered HTML; not needed with decoupled frontend |
| `checkbox_to_sql_bool()` | SQLAlchemy Boolean + Flask request parsing |
| `file_is_locked()` / `make_lockfile()` / `make_stampfile()` | Celery task idempotency + Redis locks replace file locks |
| `print_checkpoint()` | `logging.debug()` |
| `_debug()` / `_debug_suppress()` | Python `logging` module |
| `check_for_update()` | Package versioning handles this; skip |
