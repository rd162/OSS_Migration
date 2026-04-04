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
| `login_sequence()` | functions.php | 830+ | Login flow controller |
| `logout_user()` | functions.php | 807+ | Session teardown |
| `initialize_user()` | functions.php | 796+ | New user setup; delegates initialize_user_prefs() to ttrss/prefs/ops.py |

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

### `ttrss/ccache.py` ← Phase 3 (before feeds/counters.py — counters reads it)

**Graph evidence:** DB_TABLE community [3] (ccache.php + functions.php → ttrss_counters_cache, ttrss_cat_counters_cache). Call graph levels 1-4.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `ccache_zero_all()` | ccache.php:8-13 | L1 | Deletes all counter cache rows for owner_uid |
| `ccache_remove()` | ccache.php:16-27 | L1 | Deletes specific feed/cat counter cache row |
| `ccache_find()` | ccache.php:56-91 | L4 | Reads cached counter value; calls ccache_update on miss |
| `ccache_update_all()` | ccache.php:29-53 | L4 | Recalculates all counters for owner_uid |
| `ccache_update()` | ccache.php:94-191 | L4 | Recalculates counter for one feed/category |
| `_count_feed_articles()` | — (inlined) | — | Inlines getFeedArticles logic to break circular ccache↔counters dependency (R18) |

---

### `ttrss/labels.py` ← Phase 3 (before articles/ops.py and feeds/counters.py)

**Graph evidence:** DB_TABLE community [0] (labels.php → ttrss_labels2, ttrss_user_labels2, ttrss_user_entries, ttrss_access_keys). Call graph levels 1-3.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `label_find_id()` | labels.php:2-12 | L2 | Find label ID by caption and owner_uid |
| `label_find_caption()` | labels.php:60-70 | L2 | Find label caption by ID and owner_uid |
| `get_all_labels()` | labels.php:72-82 | L2 | Return all labels for owner_uid |
| `get_article_labels()` | labels.php:14-57 | L2 | Return labels for a specific article |
| `label_update_cache()` | labels.php:84-97 | L2 | Update label_cache column in ttrss_user_entries |
| `label_clear_cache()` | labels.php:99-103 | L1 | Clear label_cache for an article |
| `label_add_article()` | labels.php:121-143 | L3 | Assign label to article (INSERT ttrss_user_labels2) |
| `label_remove_article()` | labels.php:106-119 | L3 | Remove label from article (DELETE ttrss_user_labels2) |
| `label_create()` | labels.php:177-199 | L2 | Create new label |
| `label_remove()` | labels.php:145-175 | L2 | Delete label + cascade |

**Note:** `label_to_feed_id()` and `feed_to_label_id()` moved to `ttrss/utils/feeds.py` (ID conversion utilities).

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
**Note: Line ranges marked (approx) are approximate — verify against actual PHP source before implementing.**

| PHP function | Source file | Lines | Notes |
|---|---|---|---|
| `format_article()` | functions2.php | 200-300 | Article HTML rendering |
| `format_article_enclosures()` | functions2.php | 1847 | Enclosure HTML; calls format_inline_player() |
| `format_inline_player()` | functions2.php | 1157 | Embed media player HTML; called from format_article_enclosures() |
| `format_article_labels()` | functions2.php | ~1608 (approx) | Label badge HTML; depends on ttrss/labels.py |
| `format_article_note()` | functions2.php | ~1650 (approx) | Article note HTML |
| `format_tags_string()` | functions2.php | ~1680 (approx) | Tags display HTML |
| `get_article_enclosures()` | functions2.php | ~1715 (approx) | DB query: enclosures |
| `get_article_tags()` | functions2.php | ~1750 (approx) | DB query: tags |
| `catchupArticlesById()` | functions2.php | ~1780 (approx) | Mark articles read by IDs |
| `catchup_feed()` | functions.php | 1094-1237 | Mark all articles in feed read |
| `getLastArticleId()` | functions2.php | ~1943 (approx) | Max entry id query |

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
| `getFeedCatTitle()` | functions.php | — | Returns category name for a category ID; used by counters and feed handlers |
| `getFeedTitle()` | functions.php | — | Returns display name for a feed ID (including virtual feed IDs); used by counters and feed handlers |
| `getArticleFeed()` | functions.php | — | Returns feed_id for a given article_id |
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
| `initialize_user_prefs()` | db-prefs.php | — | Populate user_prefs from defaults; canonical home here — authenticate.py delegates to this module |
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

### `ttrss/utils/feeds.py` ← Phase 3 (constants + ID conversions)

**Graph evidence:** Pure utility, no DB access. Call graph level 0. Used by ccache.py, labels.py, counters.py, articles/search.py.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `LABEL_BASE_INDEX` | functions2.php | — | Constant: -1024 |
| `PLUGIN_FEED_BASE_INDEX` | pluginhost.php | — | Constant: -128 |
| `label_to_feed_id()` | functions2.php:2400-2401 | L0 | Label ID → virtual feed ID |
| `feed_to_label_id()` | functions2.php:2404-2405 | L0 | Virtual feed ID → label ID |
| `pfeed_to_feed_id()` | pluginhost.php:381-382 | L0 | Plugin feed ID → feed ID |
| `feed_to_pfeed_id()` | pluginhost.php:385-386 | L0 | Feed ID → plugin feed ID |
| `classify_feed_id()` | — (inferred) | L0 | Classify feed ID as real/virtual/label/plugin |

---

### `ttrss/articles/tags.py` ← Phase 3 (tag cache + CRUD)

**Graph evidence:** DB_TABLE community [4] (ttrss_tags). Call graph levels 0-2.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `tag_is_valid()` | functions2.php:1107-1115 | L0 | Tag name validation |
| `sanitize_tag()` | functions2.php:991-1000 | L0 | Tag name normalization |
| `get_article_tags()` | functions2.php:1055-1099 | L2 | DB query for article's tags |
| `setArticleTags()` | article.php | L2 | Write tag_cache + insert/delete ttrss_tags |
| `format_tags_string()` | functions2.php:~1680 | L0 | Format tags for display |

---

### `ttrss/articles/filters.py` ← Phase 3 (shared filter module)

**Graph evidence:** Used by BOTH articles/search.py (queryFeedHeadlines) AND tasks/feed_tasks.py (article persistence). Extracted as shared module to prevent coupling.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `load_filters()` | functions2.php:1491-1563 | L3 | Load filter rules for a feed |
| `filter_to_sql()` | functions2.php:2082-2165 | L3 | Filter rule → SQLAlchemy clause |
| `get_article_filters()` | rssfuncs.php:1272-1348 | L0 | Match article against filter rules |
| `find_article_filter()` | rssfuncs.php:1350-1357 | L0 | Find first matching filter |
| `find_article_filters()` | rssfuncs.php:1359-1368 | L0 | Find all matching filters |
| `calculate_article_score()` | rssfuncs.php:1370-1379 | L0 | Sum filter score adjustments |

---

### `ttrss/articles/persist.py` ← Phase 3 (article persistence in feed update pipeline)

**Graph evidence:** Call graph levels 0-6. Part of rssfuncs.php::update_rss_feed decomposition. Handles GUID generation, content hashing, N-gram dedup, enclosure storage.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `make_guid_from_title()` | rssfuncs.php:550-560 | L0 | GUID generation from title |
| `build_entry_guid()` | rssfuncs.php:550-621 | L1 | Full GUID construction with hash |
| `content_hash()` | rssfuncs.php:707 | L0 | SHA1 of content for dedup |
| `persist_article()` | rssfuncs.php:545-1117 | L6 | Full article upsert pipeline |
| `upsert_entry()` | rssfuncs.php:720-750 | L2 | INSERT/UPDATE ttrss_entries |
| `upsert_user_entry()` | rssfuncs.php:887-894 | L2 | INSERT/UPDATE ttrss_user_entries |
| `persist_enclosures()` | rssfuncs.php:982-1020 | L1 | INSERT ttrss_enclosures |
| `apply_filter_actions()` | rssfuncs.php:812-863 | L2 | Execute matched filter actions |

---

### `ttrss/tasks/housekeeping.py` ← Phase 3 (background cleanup tasks)

**Graph evidence:** Hook graph community [0] — HOOK_HOUSE_KEEPING invoked by rssfuncs.php and handler/public.php. Call graph level 1.

| PHP function | Source file | Graph Level | Notes |
|---|---|---|---|
| `expire_cached_files()` | rssfuncs.php:~1395-1414 | L1 | Delete stale cache files |
| `expire_error_log()` | rssfuncs.php:~1380-1393 | L1 | Purge old error_log rows |
| `update_feedbrowser_cache()` | rssfuncs.php:~1330-1370 | L1 | Refresh feedbrowser_cache |
| `cleanup_tags()` | rssfuncs.php:~1370-1380 | L1 | Remove orphaned tags |
| `housekeeping_common()` | rssfuncs.php:1415-1430 | L3 | Orchestrator; calls above + HOOK_HOUSE_KEEPING |

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
| `render_login_form()` | Server-rendered PHP template; Flask route handles |
| `print_feed_cat_select()` / `print_feed_select()` / `print_label_select()` | Server-rendered HTML <select> helpers |
| `stylesheet_tag()` / `javascript_tag()` / `get_minified_js()` / `T_js_decl()` | Frontend asset helpers; not needed |
| `format_warning()` / `format_notice()` / `format_error()` (HTML helpers) | PHP server-rendered HTML; replaced by Flask flash |
| `implements_interface()` | PHP reflection; Python uses isinstance/Protocol |
| `startup_gettext()` / `init_js_translations()` | Flask-Babel handles i18n |
| `print_user_stylesheet()` | CSS generation; eliminated or stub |
| `calculate_dep_timestamp()` | UI caching timestamp; not reproduced |
| `stripslashes_deep()` | PHP magic_quotes compat; not needed in Python |
| `gzdecode()` | Python: `gzip.decompress()` or httpx handles |

---

## Graph Validation Status

**Tool:** `tools/graph_analysis/validate_coverage.py` (5-dimension validator)
**Graph data:** `tools/graph_analysis/output/` (run 2026-04-04, enhanced script with get_hooks() detection)

| Metric | Value |
|--------|-------|
| Call graph nodes (levels 0-10, excluding third-party) | TBD (run validator) |
| Functions matched to Python | TBD |
| Functions explicitly eliminated | TBD |
| Coverage percentage | TBD |
| Hook invocations covered (of 24) | TBD |
| Missing imports | TBD |

**Last validated:** Not yet run. Run `python tools/graph_analysis/validate_coverage.py` to populate.
