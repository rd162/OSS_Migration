# Community Research Notes — GRP-04 through GRP-10
# Phase 1 · TT-RSS PHP → Python modernization
# RESEARCH MODE: DEGRADED — web search unavailable; training-knowledge-only.
# All findings from source corpus reads + training knowledge. No T1 URL citations.

---

# GRP-04 — User Preferences + Filters + Labels

## Dimensions merged
call-graph + class-hierarchy + db_table-graph + hook-graph

## Members

### Primary files
- `classes/pref/feeds.php` (~1924 LOC) — feed subscription management UI
- `classes/pref/filters.php` (~1053 LOC) — filter rule CRUD + evaluation UI
- `classes/pref/labels.php` (~322 LOC) — label CRUD
- `classes/pref/prefs.php` (~1128 LOC) — user preference form + OTP settings
- `classes/pref/system.php` (~83 LOC) — admin system settings
- `classes/pref/users.php` (~520 LOC) — user management (admin only)
- `classes/db/prefs.php` — Db_Prefs: low-level pref accessor class
- `include/db-prefs.php` — global procedural wrappers: get_pref(), set_pref()
- `include/labels.php` — label utility functions
- `include/ccache.php` — counter-cache: unread count maintenance

### DB_TABLE communities merged
- db_table C2 (12 nodes): ttrss_filters, ttrss_filter_types, ttrss_filter_actions,
  ttrss_labels2, ttrss_filters2, ttrss_filters2_rules, ttrss_filters2_actions,
  ttrss_user_labels2, (plus query-source files)
- db_table C3 (10 nodes): ttrss_user_labels2, ttrss_user_prefs,
  ttrss_counters_cache, ttrss_cat_counters_cache, ttrss_prefs,
  ttrss_prefs_types, ttrss_prefs_sections

### Hook communities merged
- hook C1 (9 nodes): HOOK_PREFS_TAB, HOOK_PREFS_TAB_SECTION,
  HOOK_PREFS_SAVE_FEED, HOOK_PREFS_EDIT_FEED,
  classes/pref/feeds.php, classes/pref/labels.php,
  classes/pref/prefs.php, classes/pref/system.php, classes/pref/users.php
- hook C6 (2 nodes): HOOK_PREFS_TABS, prefs.php

### Class community
- class C0 (13 nodes, partial): Pref_Feeds, Pref_Filters, Pref_Labels,
  Pref_Prefs, Pref_System, Pref_Users, Article, Handler_Protected, Dlg,
  Feeds, Opml, PluginHandler, RPC

---

## Representative constructs

- `get_pref($pref_name, $owner_uid)` — reads ttrss_user_prefs, falls back to def_value
  (`source-repos/ttrss-php/ttrss/include/db-prefs.php`)
- `set_pref($pref_name, $value, $owner_uid)` — upserts ttrss_user_prefs
  (`source-repos/ttrss-php/ttrss/include/db-prefs.php`)
- `Pref_Filters::edit_filter()` — AJAX handler for filter rule form
  (`source-repos/ttrss-php/ttrss/classes/pref/filters.php:~250`)
- `Pref_Prefs::otpenable()` — OTP setup (QR code generation via lib/phpqrcode)
  (`source-repos/ttrss-php/ttrss/classes/pref/prefs.php`)
- `PluginHost->run_hooks(HOOK_PREFS_TAB, ...)` — plugin-contributed preference tabs
  (`source-repos/ttrss-php/ttrss/classes/pref/feeds.php:1480`)
- `PluginHost->run_hooks(HOOK_PREFS_SAVE_FEED, ...)` — plugin actions on feed save
  (`source-repos/ttrss-php/ttrss/classes/pref/feeds.php:981`)
- `PluginHost->run_hooks(HOOK_PREFS_EDIT_FEED, ...)` — plugin UI in feed edit form
  (`source-repos/ttrss-php/ttrss/classes/pref/feeds.php:748`)
- `ccache_update($feed_id, $owner_uid, $is_cat)` — recompute + store unread count
  (`source-repos/ttrss-php/ttrss/include/ccache.php`)
- `ccache_find($feed_id, $owner_uid, $is_cat)` — cached read with 15-min TTL
  (`source-repos/ttrss-php/ttrss/include/ccache.php`)

---

## Research findings (training-knowledge-only — DEGRADED)

### Preference system architecture
- Two-layer: `ttrss_prefs` defines the schema (all valid pref names, types,
  default values); `ttrss_user_prefs` stores per-user overrides.
- `get_pref()` checks `ttrss_user_prefs` first, falls back to `ttrss_prefs.def_value`.
- Pref values stored as VARCHAR in DB regardless of logical type (INTEGER/BOOL/STRING).
  Type coercion happens in PHP at read time (e.g., `(int)get_pref(...)`, `(bool)...`).
- Named settings profiles: `ttrss_settings_profiles` allows multiple pref snapshots
  per user; switching profiles swaps the effective pref set.
  Feature appears partially implemented — used in prefs.php but rarely in other code.

### Filter system architecture
- Filters are 2-level: `ttrss_filters2` (parent, owner_uid) →
  `ttrss_filters2_rules` (one or more conditions) +
  `ttrss_filters2_actions` (one or more actions per match).
- Rule conditions: match_on field (title, content, author, tag, url, etc.),
  filter_type (contains, is, regexp), reg_exp value.
- Actions: mark as read, star, assign label, stop processing, set score, assign category.
- `HOOK_ARTICLE_FILTER` is invoked during feed update for each new article —
  plugins can intercept and short-circuit.
- Filter evaluation is done in rssfuncs.php during feed update, not at read time —
  filters apply only to newly fetched articles, not retroactively.
- `HOOK_QUERY_HEADLINES` lets plugins modify the SQL query that retrieves headlines —
  important semantic divergence from ORM patterns.

### Label system
- Labels are user-defined categories applied to articles.
- `ttrss_labels2`: label definition (caption, fg_color, bg_color, owner_uid).
- `ttrss_user_labels2`: assignment (label_id → article ref_id in ttrss_user_entries).
- Labels are referenced as negative feed IDs in the API (label ID → -(label.id + 11) ).
  This encoding is a non-obvious convention that must be preserved exactly.
- `include/labels.php` provides `label_find_id()`, `label_update_cache()`.

### Counter cache
- `ttrss_counters_cache`: (feed_id, owner_uid, value, updated) — feed unread counts.
- `ttrss_cat_counters_cache`: (feed_id, owner_uid, value, updated) — category counts.
- 15-minute freshness window: stale cache triggers `ccache_update()`.
- `ccache_update()` uses `BEGIN`/`COMMIT` for upsert atomicity but no row-level lock.
- Cascading: updating a feed count may update the parent category count.
- `ccache_zero_all()` called on "mark all as read" operations.

---

## Target-side mapping

| PHP construct | Python/Flask equivalent | Notes |
|---|---|---|
| `get_pref($name, $uid)` | `UserPref.get(name, uid)` classmethod | ORM lookup with default fallback |
| `set_pref($name, $val, $uid)` | `UserPref.set(name, val, uid)` | ORM upsert (INSERT ... ON CONFLICT) |
| `ttrss_prefs` schema table | `PrefDefinition` model | Seeded at migration time |
| `ttrss_user_prefs` | `UserPref` model | Per-user overrides |
| `ttrss_filters2` | `Filter` model | Parent filter object |
| `ttrss_filters2_rules` | `FilterRule` model | One-to-many with Filter |
| `ttrss_filters2_actions` | `FilterAction` model | One-to-many with Filter |
| `ttrss_labels2` | `Label` model | User-defined labels |
| `ttrss_user_labels2` | `UserLabel` model | M2M: Label × UserEntry |
| Label negative feed ID encoding | Preserved as integer constant formula | Must match API contract |
| HOOK_PREFS_TAB | pluggy `prefs_tab` hookspec | Plugin-contributed tab |
| HOOK_PREFS_SAVE_FEED | pluggy `prefs_save_feed` hookspec | Feed save event |
| HOOK_PREFS_EDIT_FEED | pluggy `prefs_edit_feed` hookspec | Feed edit UI event |
| `ccache_update()` | `CounterCache.update()` or Redis INCR | Architecture decision needed |
| `ccache_find()` | `CounterCache.find()` with TTL check | 15-min TTL preserved |

---

## Divergences spotted

1. **VARCHAR pref coercion**: PHP silently coerces VARCHAR pref values to int/bool.
   Python SQLAlchemy requires explicit TypeDecorator or hybrid property.
   Frequency: every pref read. Severity: MEDIUM (correctness risk on edge values).

2. **Label negative-ID encoding**: `-(label.id + 11)` is a non-obvious contract
   shared by PHP API and JS frontend. Must be preserved byte-for-byte.
   Frequency: every label API call. Severity: HIGH (API compatibility).

3. **HOOK_QUERY_HEADLINES SQL injection**: Hook receives raw SQL fragment
   to append to SELECT query. Python target must translate to a safer
   pattern (e.g., SQLAlchemy filter callable). Frequency: every headlines
   fetch where plugin is active. Severity: HIGH (security).

4. **Filter applies only to new articles**: Retroactive filtering not supported.
   This is a semantic contract — Python target must preserve this behaviour.
   Frequency: every feed update. Severity: MEDIUM.

5. **Counter cache race condition**: No row-level lock in ccache_update().
   Python target should use SELECT FOR UPDATE or Redis atomic operations.
   Frequency: concurrent multi-user updates. Severity: MEDIUM.

6. **Settings profiles**: Partially implemented feature. Python target may
   choose to complete or formally deprecate. Severity: LOW.

---

## Open questions

1. Should Python target use Redis for counter caching (INCR/DECR) or retain
   the DB-backed ccache tables?
2. HOOK_QUERY_HEADLINES SQL fragment — what is the safe SQLAlchemy equivalent
   that preserves plugin extension capability?
3. Are settings profiles actively used by any known TT-RSS deployment?
4. Should label negative-ID encoding be documented as a breaking-change risk
   if the API is ever versioned?

---
---

# GRP-05 — Plugin System + Hook Registry

## Dimensions merged
call-graph + class-hierarchy + db_table-graph + hook-graph (C0, C5, C6)

## Members

### Primary files
- `classes/pluginhost.php` (~380 LOC) — singleton plugin registry + hook dispatch
- `classes/plugin.php` (~40 LOC) — Plugin abstract base class
- `classes/pluginhandler.php` (~80 LOC) — HTTP handler for plugin AJAX requests
- `classes/handler.php` (~80 LOC) — Handler base (parent of all handlers)
- `classes/ihandler.php` (~20 LOC) — IHandler interface
- `classes/iauthmodule.php` (~20 LOC) — IAuthModule interface (auth plugins)
- `plugins/auth_internal/init.php` (~300 LOC) — built-in auth plugin
- `include/autoload.php` — class autoloader (loads plugins by directory scan)

### DB_TABLE community
- db_table C5 (2 nodes): ttrss_plugin_storage, classes/pluginhost.php

### Hook communities
- hook C0 (10 nodes): HOOK_SANITIZE, HOOK_HEADLINE_TOOLBAR_BUTTON, HOOK_HOTKEY_MAP,
  HOOK_ARTICLE_BUTTON, HOOK_HOTKEY_INFO, HOOK_ARTICLE_LEFT_BUTTON,
  HOOK_RENDER_ARTICLE, HOOK_RENDER_ARTICLE_CDM, classes/feeds.php, include/functions2.php
- hook C5 (3 nodes): HOOK_ACTION_ITEM, HOOK_TOOLBAR_BUTTON, index.php
- hook C6 (2 nodes): HOOK_PREFS_TABS, prefs.php

### Class communities
- class C8 (2 nodes): Plugin, Auth_Internal
- class C1 (partial): Handler, Handler_Public, Backend (all extend Handler)

---

## Representative constructs

- `PluginHost::getInstance()` — singleton access
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php:57`)
- `PluginHost::add_hook($type, $sender)` — plugin registers for hook
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php:102`)
- `PluginHost::run_hooks($type, $method, $args)` — dispatch to all registered plugins
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php:93`)
- `PluginHost::load($plugins_str, $kind)` — loads plugins by name from directory
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php`)
- `PluginHost::load_data()` / `save_data()` — per-plugin JSON blob in ttrss_plugin_storage
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php`)
- `Plugin::about()` — version/author metadata (abstract, each plugin implements)
- `Plugin::init($host)` — plugin initialisation, calls $host->add_hook()
- `const KIND_ALL = 1; KIND_SYSTEM = 2; KIND_USER = 3` — plugin scope enum
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php:44-46`)
- `const API_VERSION = 2` — plugin API compatibility version
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php:16`)
- `PluginHost::add_api_method($name, $sender)` — plugin extends JSON API
  (`source-repos/ttrss-php/ttrss/classes/pluginhost.php`)

---

## Full hook registry (24 hooks)

| Hook constant | Value | Invocation site | Purpose |
|---|---|---|---|
| HOOK_ARTICLE_BUTTON | 1 | classes/feeds.php | Add button to article toolbar |
| HOOK_ARTICLE_FILTER | 2 | include/rssfuncs.php | Filter new articles during update |
| HOOK_PREFS_TAB | 3 | classes/pref/*.php | Add tab to preferences dialog |
| HOOK_PREFS_TAB_SECTION | 4 | classes/pref/feeds.php, pref/prefs.php | Add section within a pref tab |
| HOOK_PREFS_TABS | 5 | prefs.php | Add top-level pref tab group |
| HOOK_FEED_PARSED | 6 | include/rssfuncs.php | Post-parse feed item processing |
| HOOK_UPDATE_TASK | 7 | update.php | Periodic background task |
| HOOK_AUTH_USER | 8 | include/functions.php | Authentication challenge |
| HOOK_HOTKEY_MAP | 9 | classes/feeds.php | Add keyboard shortcut |
| HOOK_RENDER_ARTICLE | 10 | classes/feeds.php | Article HTML render (CDM/split view) |
| HOOK_RENDER_ARTICLE_CDM | 11 | classes/feeds.php | Article render in combined-mode |
| HOOK_FEED_FETCHED | 12 | include/rssfuncs.php | Post-fetch raw feed processing |
| HOOK_SANITIZE | 13 | include/functions2.php | HTML sanitisation override |
| HOOK_RENDER_ARTICLE_API | 14 | classes/api.php | Article render via JSON API |
| HOOK_TOOLBAR_BUTTON | 15 | index.php | Add button to main toolbar |
| HOOK_ACTION_ITEM | 16 | index.php | Add item to actions menu |
| HOOK_HEADLINE_TOOLBAR_BUTTON | 17 | classes/feeds.php | Button in headline list toolbar |
| HOOK_HOTKEY_INFO | 18 | classes/feeds.php | Hotkey documentation entry |
| HOOK_ARTICLE_LEFT_BUTTON | 19 | classes/feeds.php | Button left of article title |
| HOOK_PREFS_EDIT_FEED | 20 | classes/pref/feeds.php | Extra fields in feed edit dialog |
| HOOK_PREFS_SAVE_FEED | 21 | classes/pref/feeds.php | Hook on feed save action |
| HOOK_FETCH_FEED | 22 | include/rssfuncs.php | Pre-fetch: override fetched content |
| HOOK_QUERY_HEADLINES | 23 | classes/feeds.php, api.php | Modify SQL query for headlines |
| HOOK_HOUSE_KEEPING | 24 | classes/handler/public.php | Periodic cleanup tasks |

---

## Research findings (training-knowledge-only — DEGRADED)

### Plugin loading
- `PluginHost::load()` accepts a comma-separated string of plugin names.
  It scans `plugins/{name}/init.php` and requires that file.
  The plugin's `init()` method is called with `$this` (the PluginHost).
  Plugins call `$host->add_hook(HOOK_*, $this)` in their `init()`.
- System plugins (KIND_SYSTEM) loaded from `SYSTEM_PLUGINS` config constant.
- User plugins (KIND_USER) loaded from `ttrss_user_prefs` pref `_ENABLED_PLUGINS`.
- KIND_ALL: loaded regardless of user setting.
- `API_VERSION = 2`: plugins can check `$host->get_api_version()` to
  detect incompatible host. Version bump breaks all plugins that check it.

### Hook dispatch mechanics
- `run_hooks($type, $method, $args)` iterates `$this->hooks[$type]` array
  and calls `$hook->$method($args)` on each registered object.
- No error isolation: exception in one plugin propagates to the caller.
  Python target must wrap each plugin call in try/except.
- Hook ordering is registration order (first-registered, first-called).
- Return values are ignored — hooks are fire-and-return, not filter chains,
  EXCEPT for HOOK_FETCH_FEED and HOOK_SANITIZE where the hook's returned
  value replaces the input. This distinction is critical for Python port.

### Plugin storage
- `ttrss_plugin_storage`: (name VARCHAR, owner_uid INT, content TEXT).
  `content` is a JSON-encoded PHP array serialized with `json_encode()`.
  `load_data()` / `save_data()` in PluginHost manage this.
  Per-plugin, per-user key-value store.

### Handler dispatch
- `PluginHandler` dispatches HTTP requests to plugin-registered handlers.
- Plugins can register URL handlers via `$host->add_handler($handler, $method, $obj)`.
- This means plugins can serve their own AJAX endpoints — important for
  feature-complete plugin support in Python.

---

## Target-side mapping

| PHP construct | Python/pluggy equivalent | Notes |
|---|---|---|
| `PluginHost` singleton | `pluggy.PluginManager("ttrss")` | App-level manager |
| `Plugin::init($host)` | `@hookimpl` decorated methods | pluggy convention |
| `add_hook(HOOK_*, $sender)` | `pm.register(plugin)` | pluggy auto-discovers hookimpls |
| `run_hooks($type, $method, $args)` | `pm.hook.method_name(args=args)` | pluggy dispatch |
| `KIND_SYSTEM / KIND_USER` | Plugin metadata + loader filter | Config-driven loading |
| `API_VERSION = 2` | Plugin API version constant | Increment on breaking change |
| `ttrss_plugin_storage` | `PluginStorage` model (JSON col) | 1:1 mapping |
| `load_data()` / `save_data()` | `PluginStorage.load()` / `.save()` | ORM-backed |
| HOOK_FETCH_FEED (returns value) | `pm.hook.fetch_feed(...)` firstresult | pluggy firstresult=True |
| HOOK_SANITIZE (returns value) | `pm.hook.sanitize(...)` firstresult | pluggy firstresult=True |
| All other hooks (void dispatch) | `pm.hook.method(...)` | Standard pluggy broadcast |
| Plugin URL handler | Blueprint route registered by plugin | Flask Blueprint per plugin |
| Error isolation | `try/except` per plugin call wrapper | Not present in PHP source |

---

## Divergences spotted

1. **Return-value hooks vs. void hooks**: PHP uses a single `run_hooks()` for
   both void dispatch and value-returning hooks (HOOK_FETCH_FEED, HOOK_SANITIZE).
   Python pluggy distinguishes via `firstresult=True` on the hookspec.
   Must classify all 24 hooks correctly. Severity: HIGH (semantic correctness).

2. **No exception isolation**: PHP plugin exceptions propagate uncontrolled.
   Python target should isolate with try/except per plugin call — behavioural
   improvement that plugins depending on propagation cannot rely on.
   Severity: MEDIUM.

3. **HOOK_QUERY_HEADLINES SQL fragment**: Hook receives a raw SQL string fragment
   to append/modify. Python target cannot safely pass raw SQL to SQLAlchemy ORM.
   Must provide a structured filter API instead (e.g., list of SQLAlchemy
   filter clauses). Breaking change for any plugin using this hook.
   Severity: HIGH.

4. **Plugin storage JSON**: PHP `json_encode()` of PHP arrays. Python target
   uses `json.dumps()` of Python dicts — compatible for simple structures but
   PHP arrays with integer keys serialize differently from Python dicts.
   Severity: LOW (only affects plugins that store int-keyed arrays).

5. **Plugin file discovery**: PHP scans `plugins/{name}/init.php` at runtime.
   Python target uses importlib + entry-points for plugin discovery.
   Path convention must be maintained or documented as changed.
   Severity: MEDIUM (all plugin authors must update).

---

## Open questions

1. Should Python use pluggy's standard hookspec declaration pattern, or
   a custom event-bus (blinker, PyDispatcher)?
2. How to handle HOOK_QUERY_HEADLINES — the SQL-fragment hook that cannot
   be safely translated to ORM filters?
3. Plugin error isolation policy: fail-open (skip bad plugin, log error)
   or fail-closed (propagate)?
4. Can existing PHP plugins provide any semantic guidance for the Python
   hookspec signatures, or must signatures be derived from PHP source?
5. Plugin URL handler registration: Flask Blueprint per plugin, or a
   shared Blueprint with per-plugin route prefix?

---
---

# GRP-06 — Auth + Session + Security

## Dimensions merged
call-graph + class-hierarchy + db_table-graph + hook-graph + include-graph

## Members

### Primary files
- `classes/auth/base.php` (~200 LOC) — Auth_Base abstract auth handler
- `classes/iauthmodule.php` (~20 LOC) — IAuthModule interface
- `plugins/auth_internal/init.php` (~300 LOC) — built-in username/password auth plugin
- `include/sessions.php` (~160 LOC) — PHP session handler (DB-backed)
- `include/crypt.php` (~40 LOC) — encrypt_string() / decrypt_string() via mcrypt
- `include/functions.php` (~2003 LOC, partial) — login_sequence(), authenticate_user()
- `lib/otphp/lib/otp.php` — HOTP/TOTP base class
- `lib/otphp/lib/totp.php` — TOTP (time-based OTP, Google Authenticator)
- `lib/otphp/vendor/base32.php` — Base32 encoder for TOTP secrets

### Call communities merged
- call C2 (77 nodes): Auth_Base::auto_create_user, DbUpdater::getSchemaVersion,
  DbUpdater::isUpdateRequired, DbUpdater::getSchemaLines,
  DbUpdater::performUpdateTo, (auth + db-update cluster)

### Class communities
- class C9 (1 node): Auth_Base
- class C4 (3 nodes): HOTP, OTP, TOTP
- class C8 (partial): Plugin, Auth_Internal

### DB_TABLE community
- db_table C1 (13 nodes): ttrss_error_log, ttrss_sessions, ttrss_version,
  ttrss_users, classes/auth/base.php

### Hook community
- hook C4 (3 nodes): HOOK_AUTH_USER, include/functions.php, plugins/auth_internal/init.php

### Include community
- include C5 (6 nodes): classes/pref/prefs.php, lib/otphp/vendor/base32.php,
  lib/otphp/lib/otp.php, lib/otphp/lib/totp.php, lib/phpqrcode/phpqrcode.php,
  plugins/auth_internal/init.php

---

## Representative constructs

- `Auth_Base::auto_create_user($login)` — creates ttrss_users row for new OAuth/LDAP users
  (`source-repos/ttrss-php/ttrss/classes/auth/base.php`)
- `IAuthModule` interface — contracts: `get_login()`, `authenticate()`, `logout()`
  (`source-repos/ttrss-php/ttrss/classes/iauthmodule.php`)
- `authenticate_user($login, $password, $check_only)` — calls HOOK_AUTH_USER
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `login_sequence()` — top-level login flow: session init, pref load, validate_session()
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `validate_session()` — checks IP, schema version, user-agent, pwd_hash
  (`source-repos/ttrss-php/ttrss/include/sessions.php:38`)
- `ttrss_open/read/write/destroy/gc` — PHP session handler callbacks
  (`source-repos/ttrss-php/ttrss/include/sessions.php:100+`)
- `encrypt_string($str)` / `decrypt_string($str)` — AES-128 CBC via mcrypt
  (`source-repos/ttrss-php/ttrss/include/crypt.php`)
- `TOTP::generateOTP()` — generates 6-digit TOTP code
  (`source-repos/ttrss-php/ttrss/lib/otphp/lib/totp.php`)
- `ttrss_users.pwd_hash` column — stores password hash (format: `SHA1:hash` or `MODE:hash`)
  (`source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`)
- `ttrss_users.access_level` — 0=regular, 10=admin
  (`source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`)
- `SESSION_CHECK_ADDRESS` config constant — 0/1/2: none/class-C/class-B IP check
  (`source-repos/ttrss-php/ttrss/config.php-dist`)
- `ttrss_access_keys` — per-feed access tokens for RSS-over-URL (no auth required)
  (`source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`)

---

## Research findings (training-knowledge-only — DEGRADED)

### Password hashing
- PHP stores passwords with a prefix indicating scheme: `SHA1:hex_hash`.
  Legacy accounts may have plain SHA1 or salted SHA1 depending on version.
- Auth_Internal computes hash via SHA1 during login and compares to stored value.
- This is a known security weakness (SHA1 is broken for password hashing).
- Python target: argon2id (via `argon2-cffi`) is the modern standard.
- Migration path: dual-hash — accept SHA1 on login, re-hash to argon2id on success.
  New passwords always use argon2id. This is ADR-0008 scope.

### Session architecture
- PHP native sessions are replaced by a custom DB-backed handler (`sessions.php`).
- `session_set_save_handler()` redirects to `ttrss_open/read/write/destroy/gc`.
- Session data is serialised PHP (via PHP's native session serialiser), then
  base64-encoded, stored as TEXT in `ttrss_sessions.data`.
- `validate_session()` runs on every request: checks schema version, IP prefix,
  user-agent SHA1, and pwd_hash. Any change → session invalidated.
- Session name: `ttrss_sid` (or `ttrss_sid_ssl` over HTTPS).
- Configurable expiry: `SESSION_COOKIE_LIFETIME` (0 = browser session).
- GC probability: 75% per request — aggressive session garbage collection.

### Auth module system
- HOOK_AUTH_USER is dispatched with login + password as args.
- Each registered auth plugin (kind=system) can claim the user.
- `Auth_Internal` (built-in) checks `ttrss_users` table.
- External plugins (LDAP, HTTP Auth, OAuth) can be loaded from `plugins/`.
- `IAuthModule`: `get_login()`, `authenticate()`, `logout()`, `check_remember_me()`.
- `AUTH_AUTO_CREATE`: if true, successful auth by external module auto-creates
  a ttrss_users row for the new user.

### TOTP / OTP
- `lib/otphp/`: TOTP (RFC 6238) implementation in PHP.
- User enrolls via QR code (generated by phpqrcode).
- OTP secret stored in... `ttrss_user_prefs` (`OTP_SECRET_KEY` pref).
- OTP validation happens in `plugins/auth_internal/init.php` or `Pref_Prefs`.
- `SESSION_CHECK_ADDRESS` — IP-prefix-based session binding (partial SSRF mitigation).

### Known PHP → Python divergences

1. **PHP mcrypt removed**: `include/crypt.php` uses `mcrypt_encrypt(MCRYPT_RIJNDAEL_128, ...)`.
   `mcrypt` extension removed from PHP 7.2. Python target uses `cryptography`
   library (Fernet or AES-GCM). Existing DB-encrypted feed passwords need migration.
   Severity: CRITICAL — affects any feed with stored credentials.

2. **SHA1 password hash**: Insecure. Python target: argon2id with dual-hash migration.
   Severity: HIGH (security).

3. **DB session store → Flask-Login + Redis**: Python Flask does not support
   PHP-style session serialisation. Flask-Login manages session identity;
   server-side session data stored in Redis (signed cookie points to Redis key).
   `ttrss_sessions` table can be decommissioned after migration.
   Severity: HIGH (architecture change).

4. **validate_session() complexity**: Checks schema version + IP + user-agent + pwd_hash.
   Python Flask-Login's `@login_required` checks only identity. The additional
   checks must be implemented as a custom `before_request` function.
   Severity: MEDIUM.

5. **IAuthModule plugin interface**: PHP interface must be translated to a
   Python pluggy hookspec. Method signatures must be preserved.
   Severity: MEDIUM.

6. **SINGLE_USER_MODE**: hardcodes `login = "admin"`, skips all auth.
   Python target must honour this config and skip Flask-Login checks.
   Severity: LOW.

---

## Target-side mapping

| PHP construct | Python/Flask equivalent | Notes |
|---|---|---|
| `ttrss_sessions` DB store | Flask-Login + Redis session backend | Decommission DB store |
| `validate_session()` | `@before_request` session validator | Custom checks preserved |
| SHA1 pwd_hash | argon2id (dual-hash migration) | ADR-0008 |
| `mcrypt` AES-128 | `cryptography.fernet.Fernet` | Key migration required |
| `IAuthModule` + HOOK_AUTH_USER | pluggy hookspec `auth_user` | Plugin auth preserved |
| `Auth_Base::auto_create_user()` | `User.auto_create(login)` model method | ORM create |
| `TOTP::generateOTP()` | `pyotp.TOTP(secret).now()` | pyotp library |
| QR code (phpqrcode) | `qrcode` Python library | Same output format |
| `ttrss_access_keys` | `AccessKey` model | 1:1 mapping |
| `ttrss_users.access_level` | `User.access_level` column | 0=user, 10=admin |
| `SESSION_CHECK_ADDRESS` | Custom before_request IP check | Config-driven |
| `SINGLE_USER_MODE` | App config + login bypass | Preserved |

---

## Divergences spotted

1. **mcrypt removal**: Highest-severity security divergence. All feed passwords
   encrypted with mcrypt AES-128 in the DB need re-encryption with Fernet.
   Migration script required. Frequency: any feed with stored password.
   Severity: CRITICAL.

2. **SHA1 password hash**: Every existing user account has SHA1 hash.
   Dual-hash migration must run on first successful Python-side login.
   Frequency: every user. Severity: HIGH.

3. **DB session → Redis session**: PHP session data (PHP-serialised arrays)
   cannot be read by Python. All active sessions invalidated on cutover.
   Users must re-login after migration. Frequency: all active sessions.
   Severity: HIGH (UX impact at deployment).

4. **validate_session() pwd_hash check**: If user changes password while logged
   in elsewhere, those sessions are immediately invalidated via pwd_hash check.
   Flask-Login does not do this by default — must be added.
   Frequency: password change events. Severity: MEDIUM.

---

## Open questions

1. What is the migration path for mcrypt-encrypted feed passwords already in DB?
   (Decrypt with mcrypt during migration, re-encrypt with Fernet.)
2. Should TOTP secret (stored in ttrss_user_prefs) use the same OTP_SECRET_KEY pref name?
3. Is `SESSION_CHECK_ADDRESS` feature worth preserving in Python? (Security vs. UX.)
4. What is the exact SHA1 hash format? `SHA1:hex` or `sha1(salt + password)`?
   Need to read `auth_internal/init.php` authenticate() method.

---
---

# GRP-07 — Email + Notifications + Digest

## Dimensions merged
call-graph + class-hierarchy + include-graph

## Members

### Primary files
- `classes/ttrssmailer.php` (~80 LOC) — TT-RSS email wrapper (extends PHPMailer)
- `lib/phpmailer/class.phpmailer.php` (~2826 LOC) — PHPMailer library
- `lib/phpmailer/class.smtp.php` (~1003 LOC) — PHPMailer SMTP transport
- `include/digest.php` (~400 LOC) — email digest builder: HTML + text multipart
- `lib/MiniTemplator.class.php` (~922 LOC) — simple template engine
- `classes/handler/public.php` (~1006 LOC, partial) — forgotpass, email verify flows

### Call communities merged
- call C4 (76 nodes): ttrssMailer::__construct, PHPMailer::mail_passthru,
  PHPMailer::AddAddress, PHPMailer::AddCC, PHPMailer::AddBCC,
  PHPMailer::AddReplyTo, PHPMailer::Send, PHPMailer::SmtpConnect, ...

### Class communities
- class C5 (2 nodes): ttrssMailer, PHPMailer
- class C3 (3 nodes): Text_LanguageDetect_Exception, Exception, phpmailerException

### Include community
- include C3 (8 nodes): classes/handler/public.php, lib/MiniTemplator.class.php,
  classes/ttrssmailer.php, classes/pref/users.php, lib/phpmailer/class.phpmailer.php,
  include/digest.php, lib/phpmailer/class.smtp.php, register.php

---

## Representative constructs

- `ttrssMailer::__construct()` — configures PHPMailer from SMTP_* config constants
  (`source-repos/ttrss-php/ttrss/classes/ttrssmailer.php`)
- `include/digest.php` — `send_headlines_digests()` builds per-user HTML digest
  (`source-repos/ttrss-php/ttrss/include/digest.php`)
- `Handler_Public::forgotpass()` — sends password reset link via ttrssMailer
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php`)
- `Backend::digestTest()` — sends a test digest email to admin
  (`source-repos/ttrss-php/ttrss/classes/backend.php`)
- `MiniTemplator` — minimal `{$VAR}` template engine used for digest HTML
  (`source-repos/ttrss-php/ttrss/lib/MiniTemplator.class.php`)

---

## Research findings (training-knowledge-only — DEGRADED)

### Digest architecture
- `DIGEST_ENABLE` user pref + `DIGEST_CATCHUP` option drive digest dispatch.
- `send_headlines_digests()` runs from the update daemon on a schedule.
- Builds HTML using MiniTemplator with a `templates/digest_template.txt` file.
- SMTP credentials from `SMTP_SERVER`, `SMTP_LOGIN`, `SMTP_PASSWORD` config constants.
- Supports TLS via `SMTP_SECURE` constant (`ssl`, `tls`, or blank).
- Sender: `SMTP_FROM_NAME` + `SMTP_FROM_ADDRESS`.

### PHPMailer dependency
- PHPMailer 5.x is bundled (not Composer-managed) — dated version.
- Python target: use `smtplib` + `email` stdlib, or `aiosmtplib` for async,
  or higher-level `flask-mail` / `anymail`.
- MiniTemplator → Jinja2 (Flask's built-in template engine).

---

## Target-side mapping

| PHP construct | Python equivalent | Notes |
|---|---|---|
| `ttrssMailer` / `PHPMailer` | `flask-mail` / `aiosmtplib` | Standard Python email |
| `MiniTemplator` | Jinja2 template | `templates/digest_template.html` |
| `send_headlines_digests()` | Celery periodic task | Runs on schedule |
| `forgotpass` handler | Flask route `/api/forgotpass` | Password reset flow |
| SMTP_* config constants | Flask config `MAIL_*` | flask-mail convention |
| `include/digest.php` | `ttrss/tasks/digest.py` | Celery task module |

---

## Divergences spotted

1. **MiniTemplator → Jinja2**: Template variable syntax `{$VAR}` → `{{ var }}`.
   Digest HTML template needs rewriting. Low complexity.

2. **PHPMailer 5.x bundled**: Outdated, no async support. Python uses stdlib or
   modern async email library. Behaviour equivalent for SMTP+TLS.

3. **Digest schedule**: PHP daemon runs `send_headlines_digests()` in the
   update loop. Python: Celery beat periodic task with explicit schedule.

---

## Open questions

1. Should digest template be ported to Jinja2, or replaced with a modern
   HTML email template (MJML, etc.)?
2. Is `forgotpass` the only email flow, or are there others (registration, etc.)?
   Check `register.php` and `pref/users.php`.

---
---

# GRP-08 — Bootstrap + Core Functions + Caching

## Dimensions merged
call-graph + include-graph (bootstrap cluster)

## Members

### Primary files
- `include/autoload.php` (~50 LOC) — PSR-0-style class autoloader
- `include/functions.php` (~2003 LOC) — large mixed-purpose utility library
- `include/functions2.php` (~2413 LOC) — continuation: sanitize(), feed rendering helpers
- `include/errorhandler.php` (~40 LOC) — PHP error-to-exception bridge
- `include/version.php` (~20 LOC) — VERSION, VERSION_STATIC constants
- `include/ccache.php` (already detailed in GRP-04) — counter cache
- `include/labels.php` (~100 LOC) — label utility functions
- `errors.php` (~30 LOC) — HTTP error output
- `index.php` (~100 LOC) — main UI entry point
- `include/login_form.php` (~60 LOC) — login HTML fragment
- `include/sanity_check.php` (~150 LOC) — runtime sanity checks
- `include/sanity_config.php` (~80 LOC) — config constant validation

### Include communities merged
- include C0 (14 nodes, bootstrap): db.php, errors.php, autoload.php, functions.php,
  ccache.php, db-prefs.php, db.php (include/), errorhandler.php,
  lib/accept-to-gettext.php, lib/gettext/gettext.inc, version.php,
  labels.php, lib/pubsubhubbub/publisher.php, sessions.php
- include C4 (7 nodes): include/functions2.php, include/login_form.php,
  lib/sphinxapi.php, lib/jshrink/Minifier.php, index.php,
  lib/Mobile_Detect.php, prefs.php
- include C6 (2 nodes): include/sanity_check.php, include/sanity_config.php

---

## Representative constructs

- `sanitize($str, $force_remove_images, $owner, $site_url)` — HTML sanitizer
  (`source-repos/ttrss-php/ttrss/include/functions2.php:~834`)
- `getFeedArticles($feed_id, $is_cat, $unread_only, $owner_uid)` — article count query
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `catchup_feed($feed_id, $cat_view, $owner_uid, $mode, $search)` — mark as read
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `get_article_filters($filters, $title, $content, $link, $author)` — filter evaluation
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `_debug($msg)` — conditional debug output (stderr for daemon, HTML for web)
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `make_stampede_guard($id)` — file-lock based stampede guard
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `__()` — gettext translation wrapper
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `startup_gettext()` — initialises locale from user pref or browser Accept-Language
  (`source-repos/ttrss-php/ttrss/include/functions.php`)
- `boolval()` — PHP 5.4 polyfill (no longer needed in PHP 7+)
- `sane_preg_match()` — safe regex wrapper
  (`source-repos/ttrss-php/ttrss/include/functions2.php`)
- `resolve_relative_url($base, $url)` — URL resolution for article links
  (`source-repos/ttrss-php/ttrss/include/functions2.php`)

---

## Research findings (training-knowledge-only — DEGRADED)

### functions.php / functions2.php decomposition
- These two files are the largest single PHP files (~2003 + ~2413 LOC) and act
  as a global utility namespace. No class, just procedural functions.
- Major functional groups within functions.php:
  - Auth and session: `login_sequence()`, `authenticate_user()`, `logout_user()`
  - Feed utilities: `getFeedArticles()`, `catchup_feed()`, `get_article_filters()`
  - Debug and error: `_debug()`, `user_error()`
  - i18n: `__()`, `startup_gettext()`, `T_sprintf()`
  - File locking: `make_stampede_guard()`, `file_is_locked()`
  - URL handling: `fetch_file_contents()`, `rewrite_urls()`
  - Misc: `sql_bool_to_bool()`, `checkbox_to_sql_bool()`, `boolval()`
- functions2.php continues with:
  - `sanitize()` — HTML allowlist sanitizer (~300 lines)
  - `format_article()` — full article HTML builder
  - `getFeedUnread()` — unread count with filter integration
  - `getArticleImage()`, `getArticleOgImage()` — Open Graph image extraction
  - `sane_preg_match()`, `resolve_relative_url()` — utilities

### Autoloader
- `include/autoload.php` registers an SPL autoloader:
  maps `ClassName` → `classes/classname.php` and nested paths like
  `Handler_Public` → `classes/handler/public.php` (underscore = directory separator).
  `Auth_Internal` → `plugins/auth_internal/init.php` (special case for plugins).

### Sanity checks
- `include/sanity_check.php` verifies: DB connectivity, schema version,
  required PHP extensions (mbstring, pcre, json, xml, curl, gd),
  writable directories (cache, lock, icons).
- `include/sanity_config.php` validates required config constants are defined.
- Both are loaded at bootstrap time in most entry points.

### i18n bootstrap
- `lib/accept-to-gettext.php` + `lib/gettext/gettext.inc` — PHP gettext polyfill.
- `startup_gettext()` selects locale from user pref `USER_LANGUAGE`.
- `.po`/`.mo` files in `locale/{lang}/LC_MESSAGES/`.
- `__($str)` → `T_gettext($str)` — standard gettext pattern.

---

## Target-side mapping

| PHP construct | Python equivalent | Notes |
|---|---|---|
| `include/autoload.php` | Python import system + `__init__.py` | No equivalent needed |
| `functions.php` (mixed) | Split into `ttrss/utils/auth.py`, `ttrss/utils/feeds.py`, etc. | By functional group |
| `functions2.php::sanitize()` | `bleach.clean()` + `lxml` | allowlist-based HTML clean |
| `functions2.php::format_article()` | Jinja2 template / Python function | HTML builder |
| `__()` gettext | `flask_babel.lazy_gettext()` / `gettext` stdlib | i18n preserved |
| `startup_gettext()` | Flask-Babel `@babel.localeselector` | Locale from user pref |
| `_debug()` | Python `logging.debug()` | stdlib logging |
| `make_stampede_guard()` | Redis lock / `filelock` library | Stampede prevention |
| `sql_bool_to_bool()` | SQLAlchemy Boolean column type | Automatic coercion |
| `fetch_file_contents()` curl | `httpx.get()` | Sync in web context |
| `sanity_check.php` | Flask startup check / `flask check` command | Health gate |
| `resolve_relative_url()` | `urllib.parse.urljoin()` | Stdlib equivalent |

---

## Divergences spotted

1. **Global function namespace**: 4000+ lines of global PHP functions.
   Python requires module decomposition. Decomposition map is the most
   labour-intensive part of Phase 2. Frequency: every module.
   Severity: HIGH (architecture).

2. **`sanitize()` allowlist**: PHP sanitize() has a specific HTML allowlist
   (tags, attributes, CSS properties). Python `bleach` allowlist must be
   configured to match exactly or divergences in article rendering occur.
   Frequency: every article fetch/display. Severity: HIGH (parity).

3. **`make_stampede_guard()` file lock**: Uses PHP `flock()` on files in
   `lock/` directory. Python `filelock` library is equivalent on single-host.
   Distributed (multi-process Celery) requires Redis-based distributed lock.
   Frequency: every feed update cycle. Severity: MEDIUM.

4. **SPL autoloader**: No Python equivalent needed (Python uses package
   imports natively). Only affects migration tooling, not runtime behaviour.

---

## Open questions

1. What is the exact allowlist in `sanitize()` for HTML tags and attributes?
   (Need to read functions2.php:834 fully to configure bleach equivalently.)
2. Should functions.php be decomposed into modules by functional group, or
   should a single `utils.py` module be used initially?
3. `lib/sphinxapi.php` — Sphinx full-text search. Is this feature active in
   a typical deployment? Python: `sphinxapi` Python client or migrate to
   PostgreSQL full-text search.

---
---

# GRP-09 — Third-Party Libraries

## Dimensions merged
call-graph + class-hierarchy + include-graph

## Members

### Primary files
- `lib/phpqrcode/` (13 files, ~4700 LOC total) — QR code generator (PHP port of libqrencode)
- `lib/languagedetect/` (~1708 LOC) — Text_LanguageDetect (PEAR library)
- `lib/otphp/` (3 files) — TOTP/HOTP implementation (already in GRP-06 via auth)
- `lib/phpmailer/` (2 files, ~3829 LOC) — PHPMailer 5.x (email)
- `lib/sphinxapi.php` (~1691 LOC) — Sphinx search client API
- `lib/MiniTemplator.class.php` (~922 LOC) — simple template engine
- `lib/accept-to-gettext.php` (~80 LOC) — Accept-Language → gettext locale mapper
- `lib/gettext/gettext.inc` (~600 LOC) — PHP gettext polyfill
- `lib/pubsubhubbub/publisher.php` (~100 LOC) — PubSubHubbub publisher
- `lib/pubsubhubbub/subscriber.php` (~200 LOC) — PubSubHubbub subscriber
- `lib/floIcon.php` / `lib/jimIcon.php` — favicon/feed-icon discovery
- `lib/Mobile_Detect.php` (~2100 LOC) — mobile user-agent detection
- `lib/jshrink/Minifier.php` — JavaScript minifier (server-side)

### Call communities merged
- call C3 (77 nodes): QRcode library methods (all internal to lib/phpqrcode/)
- call C9 (33 nodes): Text_LanguageDetect methods (all internal to lib/languagedetect/)

### Class communities merged
- class C3 (3 nodes): Text_LanguageDetect_Exception, Exception, phpmailerException
- class C6 (2 nodes): StringReader, CachedFileReader (gettext)
- class C7 (2 nodes): Text_LanguageDetect_Parser, Text_LanguageDetect

### Include communities
- include C1 (13 nodes): lib/phpqrcode/* (self-contained)
- include C5 (partial): lib/otphp/*, lib/phpqrcode/phpqrcode.php

---

## Research findings (training-knowledge-only — DEGRADED)

### Library replacement mapping

| PHP library | Purpose | Python equivalent |
|---|---|---|
| `lib/phpqrcode/` | QR code PNG generation | `qrcode` (PyPI) or `segno` |
| `lib/languagedetect/` | Language ID from text | `langdetect` or `lingua-language-detector` |
| `lib/otphp/` | HOTP/TOTP | `pyotp` (PyPI) |
| `lib/phpmailer/` | SMTP email | `smtplib` stdlib + `email` stdlib |
| `lib/sphinxapi.php` | Sphinx full-text search client | `sphinxapi` (Python) or drop |
| `lib/MiniTemplator.class.php` | Simple template engine | Jinja2 (Flask built-in) |
| `lib/accept-to-gettext.php` | Accept-Language parsing | `babel.parse_accept` / stdlib |
| `lib/gettext/*.inc` | Gettext polyfill | Python `gettext` stdlib / Flask-Babel |
| `lib/pubsubhubbub/` | WebSub push protocol | `aiohttp` webhook route / `websubhub` |
| `lib/floIcon.php` / `jimIcon.php` | Favicon discovery | `favicon` (PyPI) |
| `lib/Mobile_Detect.php` | Mobile UA detection | `user-agents` (PyPI) |
| `lib/jshrink/` | JS minification | Dropped (build tooling handles this) |

### Divergences spotted

1. **Bundled vs. managed dependencies**: All PHP libraries are vendored in `lib/`.
   Python target uses package manager (pip/uv + requirements.txt or pyproject.toml).
   License audit required for all 13+ libraries.

2. **Sphinx search**: `lib/sphinxapi.php` ~1691 LOC. If Sphinx is not deployed
   in practice, this can be dropped. Alternatively, migrate to PostgreSQL
   full-text search. Audit grep usage: `sphinxapi` called from `include/functions.php`.

3. **jshrink JS minification**: Server-side JS minification via PHP.
   Python target should use build tooling (webpack, esbuild) or drop entirely.
   No runtime Python equivalent needed.

4. **MiniTemplator**: Only used for digest email template.
   Replace with Jinja2 — template format must be rewritten.

---

## Open questions

1. Is Sphinx search actively used? Grep invocations in functions.php needed.
2. Which QR code library best matches phpqrcode output format?
   (QR code spec is standard — output format should be pixel-identical.)
3. Language detection: `langdetect` has non-deterministic output due to random
   seed. `lingua` is deterministic. Which is more appropriate for feed language tagging?

---
---

# GRP-10 — Public Handler + Frontend Coupling

## Dimensions merged
call-graph + class-hierarchy + include-graph + hook-graph (C5)

## Members

### Primary files
- `classes/handler/public.php` (~1006 LOC) — unauthenticated public routes
- `public.php` (~30 LOC) — entry point for public routes
- `register.php` (~150 LOC) — user self-registration form
- `opml.php` (~30 LOC) — OPML import/export entry point
- `classes/opml.php` (~523 LOC) — OPML parser + exporter
- `prefs.php` (~80 LOC) — preferences page entry point
- `index.php` (~100 LOC) — main SPA entry point
- `js/` directory — ~832 JS files (Dojo-toolkit-based SPA frontend)
- `templates/` directory — HTML templates for digest + install
- `themes/` directory — CSS themes

### Call community
- call C7 (partial): Handler_Public::generate_syndicated_feed,
  Handler_Public::forgotpass, Handler_Public::subscribe_to_feed, ...

### Include community
- include C3 (partial): classes/handler/public.php, lib/MiniTemplator.class.php,
  classes/ttrssmailer.php, register.php

### Hook community
- hook C5 (3 nodes): HOOK_ACTION_ITEM, HOOK_TOOLBAR_BUTTON, index.php

---

## Representative constructs

- `Handler_Public::generate_syndicated_feed()` — generates RSS/Atom for
  a user's feed as a public URL (using ttrss_access_keys)
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php:~185`)
- `Handler_Public::subscribe_to_feed()` — bookmarklet / one-click subscribe
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php`)
- `Handler_Public::forgotpass()` — password reset request flow
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php`)
- `Opml::opml_export()` — generates OPML XML of user's subscriptions
  (`source-repos/ttrss-php/ttrss/classes/opml.php`)
- `Opml::opml_import()` — parses OPML XML and creates feed subscriptions
  (`source-repos/ttrss-php/ttrss/classes/opml.php`)
- `PluginHost->run_hooks(HOOK_HOUSE_KEEPING, ...)` — cleanup tasks triggered
  on public requests as a side effect
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php:415`)
- `PluginHost->run_hooks(HOOK_UPDATE_TASK, ...)` — update tasks triggered
  from public handler (SIMPLE_UPDATE_MODE integration)
  (`source-repos/ttrss-php/ttrss/classes/handler/public.php:421`)
- JS SPA entry: `js/tt-rss.js` — main Dojo application bootstrapper
  (`source-repos/ttrss-php/ttrss/js/`)

---

## Research findings (training-knowledge-only — DEGRADED)

### Frontend architecture
- TT-RSS SPA is built on Dojo Toolkit (~0.4/1.x era).
- ~832 JS files (many are Dojo library files, not application code).
- Application JS files: `js/tt-rss.js`, `js/FeedTree.js`, `js/Article.js`,
  `js/Headlines.js`, `js/CommonDialogs.js`, `js/dojo/` (toolkit).
- All UI state managed client-side; server is pure JSON API + AJAX handlers.
- `lib/jshrink/` used to minify JS server-side on-demand.

### Public routes
- `public.php` handles unauthenticated routes via `Handler_Public`:
  - `/public.php?op=rss&key=TOKEN` — syndicated feed via access key
  - `/public.php?op=subscribe&feed_url=URL` — bookmarklet subscribe
  - `/public.php?op=forgotpass` — password reset
  - `/public.php?op=globalUpdateFeeds` — trigger update (SIMPLE_UPDATE_MODE)
  - `/public.php?op=housekeeping` — trigger housekeeping tasks
- These are unauthenticated (or token-authenticated) endpoints.

### OPML
- OPML 2.0 import/export for feed subscription portability.
- Import: parses XML, creates `ttrss_feeds` + `ttrss_feed_categories` rows.
- Export: generates OPML XML from user's current subscriptions.
- Both operations use `Opml` class, triggered via `opml.php` entry or
  from prefs dialog AJAX.

### Frontend/backend coupling
- JS sends AJAX `POST /backend.php?op=*` for all authenticated UI operations.
- `POST /api/` for the JSON API (mobile apps, third-party clients).
- `GET /public.php?op=*` for unauthenticated routes.
- No REST routing — all POST to a single dispatcher endpoint.
- The `op` parameter is the only routing discriminant.

---

## Target-side mapping

| PHP construct | Python/Flask equivalent | Notes |
|---|---|---|
| `public.php` + `Handler_Public` | Flask Blueprint `public` | Unauthenticated routes |
| `index.php` (SPA entry) | Flask route `/` serving `index.html` | Static SPA shell |
| `backend.php` + `Backend` | Flask Blueprint `backend` | Authenticated AJAX ops |
| `opml.php` + `Opml` | Flask route `/opml` + `opml.py` module | OPML import/export |
| `register.php` | Flask route `/register` | User self-registration |
| Dojo SPA frontend | Vanilla JS SPA (ADR-0017) | Dojo replaced |
| HOOK_TOOLBAR_BUTTON | pluggy `toolbar_button` hookspec | UI extension point |
| HOOK_ACTION_ITEM | pluggy `action_item` hookspec | UI extension point |
| HOOK_HOUSE_KEEPING (from HTTP) | Celery beat periodic task | Decouple from HTTP path |
| HOOK_UPDATE_TASK (from HTTP) | Celery task trigger | Decouple from HTTP path |
| Access key syndication | `GET /feed/<key>` Flask route | Token-auth RSS endpoint |

---

## Divergences spotted

1. **Dojo Toolkit SPA**: Dojo is a ~2010-era toolkit, no longer maintained.
   Python modernization replaces the frontend entirely (ADR-0017: Vanilla JS SPA).
   This is the largest frontend scope item but does not affect Python backend specs.
   Frequency: all UI interactions. Severity: HIGH (frontend only).

2. **HOOK_HOUSE_KEEPING triggered from HTTP**: A side-effect of web requests
   triggering background cleanup is an anti-pattern. Python target should
   move this to Celery beat. Frequency: every public request.
   Severity: MEDIUM (architecture concern).

3. **HOOK_UPDATE_TASK triggered from HTTP (SIMPLE_UPDATE_MODE)**: Same pattern.
   Python: Celery eager mode or synchronous Celery call for test environments.
   Frequency: SIMPLE_UPDATE_MODE deployments only. Severity: LOW.

4. **OPML XML generation**: PHP uses `DOMDocument` + manual XML building.
   Python: `lxml.etree` or `xml.etree.ElementTree` stdlib. Equivalent semantics.
   Frequency: OPML import/export operations. Severity: LOW.

5. **Single-dispatcher pattern (`op` parameter)**: All requests go to one
   PHP file + class. Python Flask uses URL-per-route. The `op` → route
   mapping must be explicit and complete. Frequency: all UI operations.
   Severity: MEDIUM (completeness risk during migration).

---

## Open questions

1. What is the definitive list of `op` values handled by `backend.php`,
   `public.php`, and `api/index.php`? Need a comprehensive route audit.
2. OPML import: are `ttrss_feed_categories` created if they don't exist?
   What is the duplicate-feed behaviour?
3. Access key syndication format: does it generate RSS 2.0, Atom, or both?
   What headers/content-type does it set?
4. Should the `register.php` flow be preserved, or is self-registration
   gated by a config constant (`ENABLE_REGISTRATION`) that most deployments
   disable?
5. Dojo frontend replacement scope: is the plan to rewrite the entire SPA
   in Vanilla JS, or port only the critical UI paths?
