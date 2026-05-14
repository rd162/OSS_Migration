# 05 — Plugin Hook Graph

**Dimension**: `plugin-hook-graph`
**Artifact**: `tools/graph_analysis/output/hook_graph.json`
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The plugin hook graph captures **INVOKES** and **REGISTERS** directed edges between
source files and the 24 hook constants defined in `PluginHost`.
Each node is either a hook constant (`HOOK_*`) or a source file that invokes
or registers that hook; each directed edge is one call to `run_hooks()` or one
call to `add_hook()`.

For the PHP → Python modernization this dimension:

- Defines the **pluggy hookspec skeleton** — one hookspec method per HOOK_*
  constant, with the correct `firstresult` flag for value-returning hooks
- Classifies each hook as **void dispatch** vs. **value-returning**
  (critical distinction — see Divergences section)
- Identifies which hooks are invoked from the **web request path** vs. the
  **daemon / background path** (affects whether they can be async Celery hooks)
- Surfaces **hook invocation sites** in the source that must emit the
  equivalent pluggy call in the Python target
- Provides the **extension-point parity contract**: any migrated Python codebase
  must fire every hook at the same logical point as the PHP source fires it
- Seeds the divergence catalogue with the HOOK_QUERY_HEADLINES SQL-fragment
  incompatibility — the highest-severity hook-related divergence

---

## Graph structure

| Metric | Value |
|---|---|
| Nodes (hook constants + invoking/registering files) | 40 |
| Edges (INVOKES + REGISTERS call-site references) | 39 |
| Raw Leiden communities | 7 |
| Grouped research passes (∆5) | 7 (no grouping — all ≥ 2 nodes, all meaningful) |
| Isolated singletons | 0 |
| Artifact | `tools/graph_analysis/output/hook_graph.json` |

Node types:
- **Hook constants**: `HOOK_ARTICLE_BUTTON`, `HOOK_FEED_PARSED`, … (24 nodes)
- **Source files**: the PHP file that calls `run_hooks()` or `add_hook()` (16 nodes)

Edge types (recorded in JSON `kind` field):
- `INVOKES` — `run_hooks(HOOK_X, ...)` call in a source file
- `REGISTERS` — `add_hook(HOOK_X, $this)` call in a plugin file

Edge format: `{"from": "classes/feeds.php", "to": "HOOK_RENDER_ARTICLE", "kind": "INVOKES", "line": N}`

---

## Communities (all 7 retained — no grouping needed)

### C0 — Article render + UI decoration hooks (10 nodes)

**Hook members**:
`HOOK_SANITIZE`, `HOOK_HEADLINE_TOOLBAR_BUTTON`, `HOOK_HOTKEY_MAP`,
`HOOK_ARTICLE_BUTTON`, `HOOK_HOTKEY_INFO`, `HOOK_ARTICLE_LEFT_BUTTON`,
`HOOK_RENDER_ARTICLE`, `HOOK_RENDER_ARTICLE_CDM`

**File members** (invocation sites):
`classes/feeds.php`, `include/functions2.php`

**Characterisation**:
The article-display and UI-decoration hook cluster.
All hooks in this community are invoked from `classes/feeds.php` (the headline/article
renderer) or `include/functions2.php` (the HTML sanitiser).
They allow plugins to:
- Inject extra buttons into the article toolbar (HOOK_ARTICLE_BUTTON, HOOK_ARTICLE_LEFT_BUTTON)
- Override article HTML rendering (HOOK_RENDER_ARTICLE, HOOK_RENDER_ARTICLE_CDM)
- Override HTML sanitisation (HOOK_SANITIZE — value-returning)
- Add keyboard shortcuts (HOOK_HOTKEY_MAP, HOOK_HOTKEY_INFO)
- Add buttons to the headline list toolbar (HOOK_HEADLINE_TOOLBAR_BUTTON)

**Dispatch path**: web request → `Feeds::view()` → `run_hooks(HOOK_RENDER_ARTICLE, ...)`

**Value-returning hooks in this community**:
- `HOOK_SANITIZE`: the hook's return value replaces the input HTML string.
  Python: `firstresult=True` on the hookspec. A plugin returning `None`
  means "pass through to next plugin or default sanitizer."
- `HOOK_RENDER_ARTICLE` / `HOOK_RENDER_ARTICLE_CDM`: plugins return HTML
  string or `None` (use default). Python: `firstresult=True`.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/feeds.php:138` — HOOK_HEADLINE_TOOLBAR_BUTTON
- `source-repos/ttrss-php/ttrss/classes/feeds.php:517` — HOOK_RENDER_ARTICLE_CDM
- `source-repos/ttrss-php/ttrss/classes/feeds.php:686` — HOOK_ARTICLE_LEFT_BUTTON
- `source-repos/ttrss-php/ttrss/classes/feeds.php:723` — HOOK_ARTICLE_BUTTON
- `source-repos/ttrss-php/ttrss/include/functions2.php` — HOOK_SANITIZE invocation

**Research note**: `research/GRP-05-plugin-system.md`

---

### C1 — Preferences panel hooks (9 nodes)

**Hook members**:
`HOOK_PREFS_TAB`, `HOOK_PREFS_TAB_SECTION`,
`HOOK_PREFS_SAVE_FEED`, `HOOK_PREFS_EDIT_FEED`

**File members** (invocation sites):
`classes/pref/feeds.php`, `classes/pref/labels.php`,
`classes/pref/prefs.php`, `classes/pref/system.php`, `classes/pref/users.php`

**Characterisation**:
The preferences-UI extension hook cluster.
These hooks allow plugins to:
- Add custom tabs to the preferences dialog (HOOK_PREFS_TAB, HOOK_PREFS_TABS)
- Add subsections within existing pref tabs (HOOK_PREFS_TAB_SECTION)
- Add extra fields to the feed-edit dialog (HOOK_PREFS_EDIT_FEED)
- React to a feed being saved in the pref UI (HOOK_PREFS_SAVE_FEED)

**Dispatch path**: web request → `Pref_*::*()` handlers → `run_hooks(HOOK_PREFS_TAB, ...)`

All hooks in this community are **void dispatch** (return values ignored).
Python: standard pluggy hookspec without `firstresult`.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/pref/feeds.php:748` — HOOK_PREFS_EDIT_FEED
- `source-repos/ttrss-php/ttrss/classes/pref/feeds.php:981` — HOOK_PREFS_SAVE_FEED
- `source-repos/ttrss-php/ttrss/classes/pref/feeds.php:1475` — HOOK_PREFS_TAB_SECTION
- `source-repos/ttrss-php/ttrss/classes/pref/feeds.php:1480` — HOOK_PREFS_TAB
- `source-repos/ttrss-php/ttrss/classes/pref/prefs.php:697` — HOOK_PREFS_TAB_SECTION
- `source-repos/ttrss-php/ttrss/classes/pref/prefs.php:863` — HOOK_PREFS_TAB
- `source-repos/ttrss-php/ttrss/classes/pref/labels.php:322` — HOOK_PREFS_TAB
- `source-repos/ttrss-php/ttrss/classes/pref/system.php:83` — HOOK_PREFS_TAB

**Research note**: `research/GRP-05-plugin-system.md`

---

### C2 — Feed fetch / parse / update hooks (9 nodes)

**Hook members**:
`HOOK_FEED_FETCHED`, `HOOK_FETCH_FEED`, `HOOK_FEED_PARSED`,
`HOOK_ARTICLE_FILTER`, `HOOK_HOUSE_KEEPING`, `HOOK_UPDATE_TASK`

**File members** (invocation sites):
`classes/handler/public.php`, `include/rssfuncs.php`, `update.php`

**Characterisation**:
The feed-update pipeline hook cluster.
This is the most operationally critical hook family — it fires during every
feed update cycle in the daemon. Hooks allow plugins to:
- Override the raw fetched content before parsing (HOOK_FETCH_FEED — value-returning)
- Process the raw response after fetch (HOOK_FEED_FETCHED — void)
- Process parsed feed items before storage (HOOK_FEED_PARSED — void)
- Filter individual articles (HOOK_ARTICLE_FILTER — void)
- Run periodic background tasks (HOOK_UPDATE_TASK — void, fired per update cycle)
- Run housekeeping cleanup tasks (HOOK_HOUSE_KEEPING — void, fired from web path)

**Dispatch path** (daemon path):
`update_daemon2.php` → `update_rss_feed()` (rssfuncs.php) →
`run_hooks(HOOK_FETCH_FEED, ...)` → fetch → `run_hooks(HOOK_FEED_FETCHED, ...)` →
parse → `run_hooks(HOOK_FEED_PARSED, ...)` → per-article → `run_hooks(HOOK_ARTICLE_FILTER, ...)`

**Dispatch path** (housekeeping):
`Handler_Public::*()` → `run_hooks(HOOK_HOUSE_KEEPING, ...)` (line 415)
`Handler_Public::*()` → `run_hooks(HOOK_UPDATE_TASK, ...)` (line 421)

**Value-returning hooks in this community**:
- `HOOK_FETCH_FEED`: plugin may return replacement feed content (raw bytes/string)
  to override what would be fetched from the URL. If returned, HTTP fetch is skipped.
  Python: `firstresult=True` on hookspec.

**Void hooks in this community**:
`HOOK_FEED_FETCHED`, `HOOK_FEED_PARSED`, `HOOK_ARTICLE_FILTER`,
`HOOK_UPDATE_TASK`, `HOOK_HOUSE_KEEPING` — all void dispatch.

**⚠ Architecture divergence**: `HOOK_HOUSE_KEEPING` and `HOOK_UPDATE_TASK` are
invoked from `Handler_Public` — a web-request handler. This is a background
task triggered as a side effect of HTTP traffic (SIMPLE_UPDATE_MODE pattern).
In the Python target, these should be moved to Celery beat periodic tasks,
not triggered from the HTTP path. This is a **deliberate semantic divergence**
to be documented in the Python pluggy hookspec with a deprecation note on
the HTTP-trigger pattern.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/include/rssfuncs.php` — HOOK_FETCH_FEED, HOOK_FEED_FETCHED, HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER
- `source-repos/ttrss-php/ttrss/classes/handler/public.php:415` — HOOK_HOUSE_KEEPING
- `source-repos/ttrss-php/ttrss/classes/handler/public.php:421` — HOOK_UPDATE_TASK
- `source-repos/ttrss-php/ttrss/update.php` — HOOK_UPDATE_TASK

**Research note**: `research/GRP-02-feed-engine.md`, `research/GRP-05-plugin-system.md`

---

### C3 — Query + API render hooks (4 nodes)

**Hook members**:
`HOOK_QUERY_HEADLINES`, `HOOK_RENDER_ARTICLE_API`

**File members** (invocation sites):
`classes/api.php`, `classes/pref/filters.php`

**Characterisation**:
The headline query extension and API article render hooks.
`HOOK_QUERY_HEADLINES` is the most architecturally problematic hook:
it allows plugins to inject raw SQL fragments into the `SELECT` query
used to retrieve headline lists. This hook is invoked from both
`classes/feeds.php` (UI path) and `classes/api.php` (API path).
`HOOK_RENDER_ARTICLE_API` allows plugins to modify the article data
returned by the JSON API before it is encoded.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/api.php:648` — HOOK_QUERY_HEADLINES
- `source-repos/ttrss-php/ttrss/classes/api.php:712` — HOOK_RENDER_ARTICLE_API
- `source-repos/ttrss-php/ttrss/classes/feeds.php:298` — HOOK_QUERY_HEADLINES (UI)
- `source-repos/ttrss-php/ttrss/classes/pref/filters.php:101` — HOOK_QUERY_HEADLINES (filter)

**Value-returning hooks in this community**:
- `HOOK_QUERY_HEADLINES`: returns a raw SQL string fragment (e.g., `" AND unread = true"`).
  This fragment is appended to the WHERE clause of the headline SELECT query.
  Python: **cannot be translated directly to SQLAlchemy ORM**.
  The hookspec must be redesigned as a structured filter API
  (e.g., plugin returns a list of `sqlalchemy.BinaryExpression` objects).
  This is a **breaking change** for any plugin that uses this hook.
  See Divergences section.
  Python: `firstresult=False` (collect all fragments, apply all); but the
  structured API must be defined before the hookspec can be finalised.
- `HOOK_RENDER_ARTICLE_API`: returns modified article dict (or `None`).
  Python: `firstresult=True`.

**Research note**: `research/GRP-01-core-api.md`, `research/GRP-05-plugin-system.md`

---

### C4 — Authentication hook (3 nodes)

**Hook members**: `HOOK_AUTH_USER`

**File members** (invocation + registration):
`include/functions.php` (invocation), `plugins/auth_internal/init.php` (registration)

**Characterisation**:
The authentication challenge hook.
`HOOK_AUTH_USER` is dispatched by `authenticate_user($login, $password)` in
`include/functions.php`. Each registered auth plugin receives the login
credentials and returns a user ID on success, or `false`/`null` on failure.
The first plugin to return a non-false value wins — this is a
**value-returning** (firstresult) hook.

`plugins/auth_internal/init.php` registers for `HOOK_AUTH_USER` in its
`init($host)` method via `$host->add_hook(HOOK_AUTH_USER, $this)`.

The auth plugin system allows replacing the built-in username/password
authentication with LDAP, OAuth, HTTP Auth, or any custom mechanism.
`Auth_Base::auto_create_user()` is called by auth plugins when a successfully
authenticated user does not yet exist in `ttrss_users`.

**Value-returning**: `HOOK_AUTH_USER` returns a user ID (integer) on success,
`false` on failure. Python: `firstresult=True` on hookspec.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/include/functions.php` — `authenticate_user()` + HOOK_AUTH_USER invocation
- `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` — HOOK_AUTH_USER registration
- `source-repos/ttrss-php/ttrss/classes/auth/base.php` — `auto_create_user()`
- `source-repos/ttrss-php/ttrss/classes/iauthmodule.php` — IAuthModule interface

**Research note**: `research/GRP-06-auth-session.md`

---

### C5 — UI toolbar + action menu hooks (3 nodes)

**Hook members**: `HOOK_ACTION_ITEM`, `HOOK_TOOLBAR_BUTTON`

**File members** (invocation): `index.php`

**Characterisation**:
The main-UI toolbar and action-menu extension hooks.
Both are invoked from `index.php` (the main SPA entry point) during page
generation. They allow plugins to:
- Add items to the main action menu (HOOK_ACTION_ITEM)
- Add buttons to the main application toolbar (HOOK_TOOLBAR_BUTTON)

Both are **void dispatch** (no return value — plugin outputs HTML directly).
Since the Python target replaces the Dojo SPA frontend with a Vanilla JS SPA
(ADR-0017), the hook invocation mechanism changes: these hooks can no longer
output raw PHP-rendered HTML into the page. The Python hookspec must instead
return structured data (e.g., JSON description of toolbar items) that the
JS frontend renders client-side.

This is a **UI architecture divergence** that affects all plugins using these
hooks. Full compatibility requires either:
a) A server-side template fragment endpoint that plugins can return HTML to, or
b) A structured JSON hook response that the JS frontend interprets.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/index.php` — HOOK_ACTION_ITEM + HOOK_TOOLBAR_BUTTON

**Research note**: `research/GRP-10-public-handler.md`

---

### C6 — Top-level preferences tab hook (2 nodes)

**Hook members**: `HOOK_PREFS_TABS`

**File members** (invocation): `prefs.php`

**Characterisation**:
The top-level preferences tab group hook — distinct from `HOOK_PREFS_TAB`
(which adds individual tabs) in that `HOOK_PREFS_TABS` allows plugins to
add top-level tab categories to the preferences dialog structure.
Invoked once per preferences page load from `prefs.php`.

**Void dispatch**: Python hookspec without `firstresult`.

**Note**: This is the smallest community (2 nodes) and clusters separately
because `prefs.php` is a singleton entry point with few include edges.
In practice `HOOK_PREFS_TABS` is semantically related to C1 (pref hooks)
and should be grouped with C1 in Python hookspec organisation.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/prefs.php` — HOOK_PREFS_TABS invocation

**Research note**: `research/GRP-05-plugin-system.md`

---

## Full hook registry

Complete inventory of all 24 hooks with classification for Python migration.

| Const | Val | Invocation site | PHP dispatch | Python hookspec | firstresult? |
|---|---|---|---|---|---|
| `HOOK_ARTICLE_BUTTON` | 1 | `classes/feeds.php:723` | `run_hooks(1, "hook_article_button", $args)` | `hook_article_button(article)` | No |
| `HOOK_ARTICLE_FILTER` | 2 | `include/rssfuncs.php` | `run_hooks(2, "hook_article_filter", $args)` | `hook_article_filter(article)` | No |
| `HOOK_PREFS_TAB` | 3 | `classes/pref/*.php` | `run_hooks(3, "hook_prefs_tab", $args)` | `hook_prefs_tab(params)` | No |
| `HOOK_PREFS_TAB_SECTION` | 4 | `classes/pref/feeds.php`, `pref/prefs.php` | `run_hooks(4, ...)` | `hook_prefs_tab_section(params)` | No |
| `HOOK_PREFS_TABS` | 5 | `prefs.php` | `run_hooks(5, ...)` | `hook_prefs_tabs(params)` | No |
| `HOOK_FEED_PARSED` | 6 | `include/rssfuncs.php` | `run_hooks(6, "hook_feed_parsed", $args)` | `hook_feed_parsed(feed, items)` | No |
| `HOOK_UPDATE_TASK` | 7 | `update.php`, `handler/public.php:421` | `run_hooks(7, "hook_update_task", $args)` | `hook_update_task()` | No |
| `HOOK_AUTH_USER` | 8 | `include/functions.php` | `run_hooks(8, "hook_auth_user", $args)` | `hook_auth_user(login, password)` | **Yes** |
| `HOOK_HOTKEY_MAP` | 9 | `classes/feeds.php` | `run_hooks(9, ...)` | `hook_hotkey_map(hotkeys)` | No |
| `HOOK_RENDER_ARTICLE` | 10 | `classes/feeds.php` | `run_hooks(10, "hook_render_article", $args)` | `hook_render_article(article)` | **Yes** |
| `HOOK_RENDER_ARTICLE_CDM` | 11 | `classes/feeds.php` | `run_hooks(11, ...)` | `hook_render_article_cdm(article)` | **Yes** |
| `HOOK_FEED_FETCHED` | 12 | `include/rssfuncs.php` | `run_hooks(12, "hook_feed_fetched", $args)` | `hook_feed_fetched(feed, content)` | No |
| `HOOK_SANITIZE` | 13 | `include/functions2.php` | `run_hooks(13, "hook_sanitize", $args)` | `hook_sanitize(html, options)` | **Yes** |
| `HOOK_RENDER_ARTICLE_API` | 14 | `classes/api.php:712` | `run_hooks(14, ...)` | `hook_render_article_api(article)` | **Yes** |
| `HOOK_TOOLBAR_BUTTON` | 15 | `index.php` | `run_hooks(15, ...)` | `hook_toolbar_button(params)` | No |
| `HOOK_ACTION_ITEM` | 16 | `index.php` | `run_hooks(16, ...)` | `hook_action_item(params)` | No |
| `HOOK_HEADLINE_TOOLBAR_BUTTON` | 17 | `classes/feeds.php:138` | `run_hooks(17, ...)` | `hook_headline_toolbar_button(params)` | No |
| `HOOK_HOTKEY_INFO` | 18 | `classes/feeds.php` | `run_hooks(18, ...)` | `hook_hotkey_info(hotkeys)` | No |
| `HOOK_ARTICLE_LEFT_BUTTON` | 19 | `classes/feeds.php:686` | `run_hooks(19, ...)` | `hook_article_left_button(article)` | No |
| `HOOK_PREFS_EDIT_FEED` | 20 | `classes/pref/feeds.php:748` | `run_hooks(20, ...)` | `hook_prefs_edit_feed(feed)` | No |
| `HOOK_PREFS_SAVE_FEED` | 21 | `classes/pref/feeds.php:981` | `run_hooks(21, ...)` | `hook_prefs_save_feed(feed)` | No |
| `HOOK_FETCH_FEED` | 22 | `include/rssfuncs.php` | `run_hooks(22, "hook_fetch_feed", $args)` | `hook_fetch_feed(feed, url)` | **Yes** |
| `HOOK_QUERY_HEADLINES` | 23 | `classes/feeds.php:298`, `api.php:648`, `pref/filters.php:101` | `run_hooks(23, ...)` | `hook_query_headlines(query_builder)` | No ⚠ |
| `HOOK_HOUSE_KEEPING` | 24 | `classes/handler/public.php:415` | `run_hooks(24, ...)` | `hook_house_keeping()` | No |

**Hook classification summary**:
- **Value-returning (firstresult=True)**: HOOK_AUTH_USER, HOOK_RENDER_ARTICLE,
  HOOK_RENDER_ARTICLE_CDM, HOOK_SANITIZE, HOOK_RENDER_ARTICLE_API, HOOK_FETCH_FEED
  = **6 hooks**
- **Void dispatch (firstresult=False)**: remaining 18 hooks
- **Special case — HOOK_QUERY_HEADLINES**: collect from all plugins (not firstresult),
  but return type must be redesigned (see Divergences)

---

## Dependency levels

| Level | Characterisation | Hook examples |
|---|---|---|
| 0 (invoked earliest — bootstrap / auth) | Authentication hooks, fired before any content is served | `HOOK_AUTH_USER` |
| 1 (invoked during feed pipeline) | Feed fetch, parse, filter pipeline hooks | `HOOK_FETCH_FEED`, `HOOK_FEED_FETCHED`, `HOOK_FEED_PARSED`, `HOOK_ARTICLE_FILTER` |
| 2 (invoked during content rendering) | Article HTML render hooks | `HOOK_SANITIZE`, `HOOK_RENDER_ARTICLE`, `HOOK_RENDER_ARTICLE_CDM`, `HOOK_RENDER_ARTICLE_API` |
| 3 (invoked during UI build) | Preferences, toolbar, action menu hooks | All `HOOK_PREFS_*`, `HOOK_TOOLBAR_BUTTON`, `HOOK_ACTION_ITEM`, `HOOK_HEADLINE_TOOLBAR_BUTTON` |
| 4 (periodic / housekeeping) | Background and periodic task hooks | `HOOK_UPDATE_TASK`, `HOOK_HOUSE_KEEPING` |

---

## Plugin host architecture summary

```
PluginHost (singleton — classes/pluginhost.php)
│
├── hooks: array[HOOK_ID → array[Plugin, ...]]   ← registered listeners
├── plugins: array[name → Plugin]                ← loaded plugin instances
├── handlers: array[handler → array[method → Plugin]] ← URL handler dispatch
├── api_methods: array[name → Plugin]            ← JSON API extensions
├── storage: array[name → array]                 ← per-plugin in-memory data
│
├── add_hook(HOOK_ID, $plugin)    → appends to hooks[HOOK_ID]
├── del_hook(HOOK_ID, $plugin)    → removes from hooks[HOOK_ID]
├── run_hooks(HOOK_ID, $method, $args) → calls $plugin->$method($args) for each
├── load($names, $kind)           → scans plugins/<name>/init.php, calls init()
├── load_data($plugin)            → reads ttrss_plugin_storage JSON blob
└── save_data($plugin)            → writes ttrss_plugin_storage JSON blob
```

**Kind constants**:
- `KIND_ALL = 1` — loaded for all users regardless of preference
- `KIND_SYSTEM = 2` — loaded from `SYSTEM_PLUGINS` config constant
- `KIND_USER = 3` — loaded from user pref `_ENABLED_PLUGINS`

**API_VERSION = 2** — plugins can check `$host->get_api_version()`.
A version bump breaks all plugins that check it.

---

## Python pluggy hookspec skeleton

```python
# ttrss/plugins/hookspec.py
import pluggy

hookspec = pluggy.HookspecMarker("ttrss")
hookimpl = pluggy.HookimplMarker("ttrss")

class TtrssSpec:
    # --- Authentication (C4) ---
    @hookspec(firstresult=True)
    def hook_auth_user(self, login: str, password: str) -> int | None:
        """Authenticate user. Return user_id on success, None to pass."""

    # --- Feed pipeline (C2) ---
    @hookspec(firstresult=True)
    def hook_fetch_feed(self, feed_id: int, url: str) -> bytes | None:
        """Override feed content. Return bytes to skip HTTP fetch, None to proceed."""

    @hookspec
    def hook_feed_fetched(self, feed_id: int, content: bytes) -> None:
        """Post-fetch processing. Return value ignored."""

    @hookspec
    def hook_feed_parsed(self, feed_id: int, items: list) -> None:
        """Post-parse processing. Return value ignored."""

    @hookspec
    def hook_article_filter(self, article: dict) -> None:
        """Per-article filtering during update. Mutate article dict in place."""

    @hookspec
    def hook_update_task(self) -> None:
        """Periodic background task hook."""

    @hookspec
    def hook_house_keeping(self) -> None:
        """Periodic housekeeping. Prefer Celery beat over HTTP-path trigger."""

    # --- Article rendering (C0, C3) ---
    @hookspec(firstresult=True)
    def hook_sanitize(self, html: str, options: dict) -> str | None:
        """Override HTML sanitisation. Return cleaned HTML or None for default."""

    @hookspec(firstresult=True)
    def hook_render_article(self, article: dict) -> str | None:
        """Override article HTML (split view). Return HTML or None for default."""

    @hookspec(firstresult=True)
    def hook_render_article_cdm(self, article: dict) -> str | None:
        """Override article HTML (combined mode). Return HTML or None."""

    @hookspec(firstresult=True)
    def hook_render_article_api(self, article: dict) -> dict | None:
        """Modify article dict returned by JSON API. Return modified dict or None."""

    # --- Query extension (C3) ---
    @hookspec
    def hook_query_headlines(self, query_builder) -> None:
        """Extend headline query. Mutate query_builder (SQLAlchemy Select) in place.
        NOTE: replaces PHP SQL-fragment pattern. Breaking change from PHP."""

    # --- UI decoration (C0) ---
    @hookspec
    def hook_article_button(self, article: dict) -> None:
        """Contribute article toolbar button spec (JSON/dict, not raw HTML)."""

    @hookspec
    def hook_article_left_button(self, article: dict) -> None:
        """Contribute article left-button spec."""

    @hookspec
    def hook_headline_toolbar_button(self, params: dict) -> None:
        """Contribute headline list toolbar button."""

    @hookspec
    def hook_hotkey_map(self, hotkeys: dict) -> None:
        """Add keyboard shortcuts. Mutate hotkeys dict."""

    @hookspec
    def hook_hotkey_info(self, hotkeys: dict) -> None:
        """Add hotkey documentation entries."""

    # --- Preferences UI (C1, C6) ---
    @hookspec
    def hook_prefs_tab(self, params: dict) -> None:
        """Contribute preferences tab descriptor (JSON, not raw HTML)."""

    @hookspec
    def hook_prefs_tab_section(self, params: dict) -> None:
        """Contribute preferences tab section."""

    @hookspec
    def hook_prefs_tabs(self, params: dict) -> None:
        """Contribute top-level preferences tab group."""

    @hookspec
    def hook_prefs_edit_feed(self, feed: dict) -> None:
        """Add fields to feed-edit dialog."""

    @hookspec
    def hook_prefs_save_feed(self, feed: dict) -> None:
        """React to feed save in preferences."""

    # --- Main UI (C5) ---
    @hookspec
    def hook_toolbar_button(self, params: dict) -> None:
        """Contribute main toolbar button."""

    @hookspec
    def hook_action_item(self, params: dict) -> None:
        """Contribute action menu item."""
```

---

## Modernization impact

### Forced adaptations

1. **`run_hooks($type, $method, $args)` → pluggy `pm.hook.method_name(**kwargs)`**:
   PHP dispatch is triple-indirect (hook type → method name string → args array).
   pluggy uses direct typed method calls on the hook proxy. The `$method` string
   in PHP corresponds directly to the hookspec method name in Python.
   Source: `source-repos/ttrss-php/ttrss/classes/pluginhost.php:93`

2. **`KIND_SYSTEM` / `KIND_USER` → plugin loading config**:
   PHP loads plugins by scanning `plugins/<name>/init.php`.
   Python uses importlib + entry-points or directory scan.
   `KIND_SYSTEM` = loaded from `SYSTEM_PLUGINS` config; `KIND_USER` = loaded from
   user pref `_ENABLED_PLUGINS`. Python `PluginManager` must replicate
   this two-tier loading with equivalent scope semantics.

3. **`add_api_method($name, $sender)` → dynamic API routes**:
   Plugins can register additional JSON API methods in PHP.
   Python equivalent: plugin registers a Blueprint with a `/api/plugin/<name>/`
   route at plugin load time. The `api_methods` registry in PluginHost
   becomes a Flask Blueprint registration hook.

4. **Error isolation**:
   PHP `run_hooks()` has no try/except — plugin exceptions propagate to the
   caller and may crash the request. Python target MUST wrap each plugin call:
   ```python
   for plugin in pm.get_plugins():
       try:
           plugin.hook_method(args)
       except Exception as e:
           logger.exception("Plugin %s hook %s failed", plugin, "hook_method")
   ```
   This is a **deliberate improvement** — PHP behaviour is a bug, not a feature.

5. **Plugin storage format**:
   PHP `save_data()` calls `json_encode($plugin->storage[$name])`.
   Python `PluginStorage.save()` calls `json.dumps(data)`.
   For simple dicts, these are identical. PHP integer-keyed arrays
   differ: `{0: "a", 1: "b"}` in PHP → `{"0": "a", "1": "b"}` in JSON.
   Existing plugin storage rows in `ttrss_plugin_storage` must be validated
   on first Python access.

---

## Divergences catalogue (from this dimension)

### D-PH-01 — HOOK_QUERY_HEADLINES: SQL fragment → structured filter

**Category**: Semantic divergence — hook return-value contract
**Source**: `classes/api.php:648`, `classes/feeds.php:298`, `classes/pref/filters.php:101`
**PHP pattern**: Plugin returns raw SQL string fragment (e.g., `" AND score > 0"`)
appended to the WHERE clause of the headline SELECT query.
**Python gotcha**: Cannot pass raw SQL strings to SQLAlchemy ORM queries safely.
The hookspec must accept a `sqlalchemy.Select` object (the query under construction)
and plugins mutate it via `query_builder = query_builder.where(...)`.
**Estimated frequency**: Every `getHeadlines` API call + every `Feeds::view()` where
any plugin is registered for this hook (could be all requests if the filter plugin
is enabled by default).
**Migration phase**: Phase 4 (API handlers + headline query path).
**Severity**: HIGH — breaking change for all PHP plugins using this hook.

---

### D-PH-02 — HOOK_SANITIZE: return-value semantics

**Category**: Semantic divergence — hook firstresult vs. broadcast
**Source**: `include/functions2.php`
**PHP pattern**: `run_hooks(13, "hook_sanitize", $args)` — the **last** returning
plugin's value is used (PHP array iteration semantics: last write wins).
**Python gotcha**: pluggy `firstresult=True` uses the **first non-None** return.
If multiple plugins register for HOOK_SANITIZE, PHP uses the last one;
Python would use the first. Plugin registration order matters differently.
**Estimated frequency**: Every article rendered (via `sanitize()`).
**Migration phase**: Phase 2 (core logic — sanitize function).
**Severity**: MEDIUM (only affects deployments with multiple sanitize plugins).

---

### D-PH-03 — HOOK_HOUSE_KEEPING / HOOK_UPDATE_TASK from HTTP path

**Category**: Architectural divergence — background task triggered from web request
**Source**: `classes/handler/public.php:415–421`
**PHP pattern**: Background housekeeping and update tasks triggered as side effects
of incoming HTTP requests to `public.php` (SIMPLE_UPDATE_MODE).
**Python gotcha**: Anti-pattern in Python async/Celery architecture.
HTTP handlers should not block on or trigger background tasks inline.
**Target pattern**: Move to Celery beat periodic tasks; HTTP path fires
`task.apply_async()` at most (non-blocking).
**Estimated frequency**: Every public.php request in SIMPLE_UPDATE_MODE.
**Migration phase**: Phase 1 foundation (Celery task setup).
**Severity**: MEDIUM (architecture concern, not a data correctness issue).

---

### D-PH-04 — UI hooks (HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM) output raw HTML

**Category**: Frontend coupling divergence
**Source**: `index.php`
**PHP pattern**: Plugins call `echo "<button>...</button>"` or return HTML strings
for toolbar buttons and action items. The output is interleaved with PHP-rendered
page HTML.
**Python gotcha**: Python target has a Vanilla JS SPA (ADR-0017) that does not
render server-side HTML for UI components. These hooks must return structured JSON
descriptors (button label, icon, action URL) that the JS frontend renders.
**Estimated frequency**: Every page load.
**Migration phase**: Phase 4 (frontend integration).
**Severity**: HIGH for existing PHP plugins; LOW for new Python plugins.

---

### D-PH-05 — No exception isolation in PHP run_hooks()

**Category**: Reliability divergence (improvement in Python)
**Source**: `classes/pluginhost.php:93`
**PHP pattern**: Exception in any plugin propagates uncontrolled to caller.
A buggy plugin crashes the entire request.
**Python target**: Each plugin call is wrapped in try/except with logging.
A buggy plugin logs an error and is skipped.
**Impact**: PHP plugins that rely on exceptions propagating (e.g., to trigger
a fallback in the caller) may behave differently in Python.
Audit all HOOK_AUTH_USER plugins in particular — auth failure via exception
vs. return `false` is a real usage pattern.
**Migration phase**: Phase 5 (semantic verification).
**Severity**: LOW (improvement; edge case for exception-propagating plugins).

---

## Source cross-references

| Construct | Source | Line(s) |
|---|---|---|
| `PluginHost` class full | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | full |
| `run_hooks()` method | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 93 |
| `add_hook()` method | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 102 |
| `load()` method (plugin loading) | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | ~150 |
| 24 HOOK_* constants | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 18–41 |
| `KIND_ALL/SYSTEM/USER` | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 44–46 |
| `API_VERSION = 2` | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 16 |
| `Plugin` abstract base | `source-repos/ttrss-php/ttrss/classes/plugin.php` | full |
| `IAuthModule` interface | `source-repos/ttrss-php/ttrss/classes/iauthmodule.php` | full |
| `Auth_Internal` plugin (HOOK_AUTH_USER registration) | `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` | full |
| HOOK_QUERY_HEADLINES (API path) | `source-repos/ttrss-php/ttrss/classes/api.php` | 648 |
| HOOK_RENDER_ARTICLE_API | `source-repos/ttrss-php/ttrss/classes/api.php` | 712 |
| HOOK_HOUSE_KEEPING | `source-repos/ttrss-php/ttrss/classes/handler/public.php` | 415 |
| HOOK_UPDATE_TASK | `source-repos/ttrss-php/ttrss/classes/handler/public.php` | 421 |
| HOOK_SANITIZE | `source-repos/ttrss-php/ttrss/include/functions2.php` | `sanitize()` |
| HOOK_PREFS_TAB (feeds) | `source-repos/ttrss-php/ttrss/classes/pref/feeds.php` | 1480 |
| HOOK_PREFS_SAVE_FEED | `source-repos/ttrss-php/ttrss/classes/pref/feeds.php` | 981 |
| HOOK_ARTICLE_BUTTON | `source-repos/ttrss-php/ttrss/classes/feeds.php` | 723 |
| HOOK_ARTICLE_LEFT_BUTTON | `source-repos/ttrss-php/ttrss/classes/feeds.php` | 686 |
| HOOK_RENDER_ARTICLE_CDM | `source-repos/ttrss-php/ttrss/classes/feeds.php` | 517 |
| Hook edge JSON | `tools/graph_analysis/output/hook_graph.json` | all |
| Communities summary | `tools/graph_analysis/output/communities_summary.json` | hook section |

---

## Notes and caveats

- **Zero singleton communities**: The hook graph has no singleton communities,
  which validates that the extraction captured meaningful invocation edges.
  All 24 hooks are connected to at least one invocation or registration site.

- **Hook count = exactly 24**: The `build_php_graphs.py` extractor parsed
  the `const HOOK_*` declarations in `pluginhost.php` and cross-referenced
  them to `run_hooks()` call sites. The count of 24 hooks exactly matches
  the constant declarations.

- **REGISTERS edges sparse**: Only `plugins/auth_internal/init.php` generates
  `REGISTERS` edges (HOOK_AUTH_USER). Other plugins are not present in the
  `source-repos/` — they are user-installed at runtime. The hook graph shows
  the invocation contract from the host side; plugin registrations are
  runtime-discovered via `PluginHost::load()`.

- **HOOK_QUERY_HEADLINES is the highest-risk hook**: It appears in 3 separate
  invocation sites, returns SQL fragments, and is fundamentally incompatible
  with SQLAlchemy ORM patterns. Resolution requires careful API design before
  Phase 4. Consider drafting an ADR specifically for this hook's Python API.

- **Research mode**: ∆6 community research ran in DEGRADED mode (no external
  web search). pluggy hookspec design from training knowledge only.
  Phase 2 should verify current pluggy 1.x best practices (hookspec markers,
  firstresult semantics, trylast/tryfirst ordering modifiers) before
  finalising the hookspec skeleton above.

- **`API_VERSION` bump risk**: Incrementing `API_VERSION` in the Python target
  breaks compatibility with PHP plugins that check `$host->get_api_version()`.
  Since the pluggy API is completely different from PHP's, an increment is
  technically warranted — but the migration guide for plugin authors must
  document this clearly.
