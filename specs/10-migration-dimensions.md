# 10 — Migration Dimensions Analysis

## Purpose

This document defines the **analysis dimensions** for driving the PHP→Python migration, and proposes **multi-dimensional migration flow variants** to be discussed and selected before starting the actual migration work.

## Analysis Dimensions

### Dimension 1: Call Graph Dependencies

The call graph captures which files/functions call which other files/functions. This determines the **compilation order** — you can't migrate a function until its dependencies exist.

#### Key Dependency Chains

```
Entry Points → Bootstrap → Handlers → Business Logic → Database
                                    → Plugin System
                                    → Feed Processing
```

**Core bootstrap chain** (must be migrated first in any flow):
```
autoload.php → config.php → db.php → functions.php → db-prefs.php
```

**Handler dependency chain**:
```
Handler (base) → Handler_Protected → {RPC, Feeds, Article, Pref_*}
              → Handler_Public
              → API
```

**Feed processing chain**:
```
rssfuncs.php → functions.php → db.php
             → FeedParser → FeedItem_Common → FeedItem_Atom / FeedItem_RSS
             → FeedEnclosure
             → ccache.php → labels.php
```

#### Call Graph Communities (candidates for NetworkX + Leiden detection)

| Community | Files | Description |
|-----------|-------|-------------|
| **Core** | functions.php, functions2.php, db.php, config.php, autoload.php | Foundation — everything depends on this (bootstrap chain: autoload.php→config.php→db.php→functions.php→db-prefs.php; sessions.php is NOT in this chain; db-prefs.php bootstrap role is cross-cutting — primary community is Preferences) |
| **Feed Engine** | rssfuncs.php, feedparser.php, feeditem/*.php | Feed update pipeline (ccache.php removed — primarily coupled with counter functions, not the feed pipeline) |
| **Counters + Caching** | ccache.php | Counter cache (ttrss_counters_cache + ttrss_cat_counters_cache); bidirectionally coupled with functions.php counter functions (getAllCounters, getFeedCounters, getCategoryCounters) |
| **Labels** | labels.php | Label operations (ttrss_labels2 + ttrss_user_labels2); called from rssfuncs.php (article labeling), article.php, and rpc.php (label toggle) |
| **User Interface** | feeds.php, article.php, rpc.php, dlg.php + JS files | Frontend-serving handlers |
| **Preferences** | pref/*.php, db-prefs.php | User/admin settings |
| **Plugin** | pluginhost.php, plugin.php, pluginhandler.php | Extension system |
| **API** | api.php, api/index.php | External API |
| **Auth** | sessions.php, auth/base.php, iauthmodule.php, auth/*.php | Authentication and session management; auth functions (authenticate_user line 706, login_sequence line 830, logout_user line 807, initialize_user line 796, load_user_plugins line 818) are sourced from functions.php (Core community) — these are function citations, not community membership claims |
| **Infrastructure** | logger/*.php, dbupdater.php, ttrssmailer.php, crypt.php | Cross-cutting services |

### Dimension 2: Entity / Database Relationships

The entity dimension maps source code to the database tables it operates on. This determines which **data models** need to exist before business logic can be migrated.

#### Entity Clusters

| Cluster | Tables | Operating Code | Graph Evidence (DB_TABLE community) |
|---------|--------|----------------|--------------------------------------|
| **User Core** | ttrss_users, ttrss_sessions, ttrss_access_keys | sessions.php, functions.php (auth), auth_internal | Community [1]: Auth/System — ttrss_users, ttrss_sessions, ttrss_error_log, ttrss_version |
| **Feed Management** | ttrss_feeds, ttrss_feed_categories, ttrss_archived_feeds | pref/feeds.php, rssfuncs.php, feeds.php | Community [0]: Feed/API — ttrss_feed_categories, ttrss_archived_feeds; Community [5]: ttrss_feeds, ttrss_linked_feeds |
| **Article Content** | ttrss_entries, ttrss_user_entries, ttrss_enclosures, ttrss_entry_comments | rssfuncs.php, article.php, feeds.php, functions2.php | Community [4]: Articles/Tags — ttrss_enclosures, ttrss_entries, ttrss_tags |
| **Tagging & Labels** | ttrss_tags, ttrss_labels2, ttrss_user_labels2 | labels.php, article.php, rpc.php | Split: ttrss_tags in [4] (Articles); ttrss_user_labels2 in [0] (Feed/API) and [3] (Counters/Prefs) |
| **Filtering** | ttrss_filters2, ttrss_filters2_rules, ttrss_filters2_actions, ttrss_filter_types, ttrss_filter_actions | pref/filters.php, rssfuncs.php | Community [2]: Filters — all 6 filter tables + pref/filters.php, pref/labels.php, opml.php |
| **Preferences** | ttrss_prefs, ttrss_user_prefs, ttrss_prefs_types, ttrss_prefs_sections, ttrss_settings_profiles | db-prefs.php, pref/prefs.php | Community [3]: Counters+Prefs — ttrss_prefs, ttrss_user_prefs (co-located with counter caches) |
| **Caching** | ttrss_counters_cache, ttrss_cat_counters_cache, ttrss_feedbrowser_cache | ccache.php, feedbrowser.php | Community [3]: ttrss_counters_cache, ttrss_cat_counters_cache; Community [5]: ttrss_feedbrowser_cache |
| **Plugin** | ttrss_plugin_storage | pluginhost.php | Community [6]: Plugin — isolated (pluginhost.php only) |
| **System** | ttrss_version, ttrss_themes, ttrss_error_log | dbupdater.php, logger/sql.php | Community [1]: Auth/System — ttrss_version, ttrss_error_log |
| **Federation** | ttrss_linked_instances, ttrss_linked_feeds | (minimal code — low priority) | Community [5]: ttrss_linked_feeds (co-located with ttrss_feeds) |

#### Entity Dependency Order

```
Level 0 (no FK deps):  ttrss_prefs_types, ttrss_prefs_sections, ttrss_filter_types,
                        ttrss_filter_actions, ttrss_themes, ttrss_version, ttrss_entries

Level 1 (depends on L0): ttrss_users, ttrss_prefs, ttrss_linked_instances

Level 2 (depends on L1): ttrss_feeds, ttrss_feed_categories, ttrss_sessions,
                          ttrss_settings_profiles, ttrss_access_keys, ttrss_labels2,
                          ttrss_filters2, ttrss_user_prefs, ttrss_plugin_storage,
                          ttrss_error_log, ttrss_linked_feeds,
                          ttrss_counters_cache, ttrss_cat_counters_cache
                          (note: counters/cat_counters feed_id has NO FK constraint —
                           only owner_uid → ttrss_users; verified ttrss_schema_pgsql.sql)

Level 3 (depends on L2): ttrss_user_entries, ttrss_archived_feeds,
                          ttrss_filters2_rules, ttrss_filters2_actions

Level 4 (depends on L3): ttrss_tags, ttrss_user_labels2, ttrss_enclosures,
                          ttrss_entry_comments, ttrss_feedbrowser_cache
```

### Dimension 3: Frontend / Backend Coupling

This dimension maps which backend code serves which frontend components.

| Frontend Component | JS File(s) | Backend Handler(s) | Coupling Level |
|-------------------|------------|---------------------|----------------|
| Feed sidebar tree | FeedTree.js, feedlist.js | Pref_Feeds::getfeedtree, RPC::getAllCounters | HIGH — custom Dojo store |
| Headlines panel | viewfeed.js | Feeds::view (server-rendered HTML) | HIGH — HTML fragments |
| Article view | viewfeed.js | Article::view | MEDIUM — JSON data |
| Preferences | prefs.js, PrefFeed/Filter/LabelTree.js | Pref_* handlers | HIGH — server HTML + Dojo stores |
| Dialogs | functions.js | Dlg, various handlers | HIGH — server HTML |
| Toolbar/actions | tt-rss.js | RPC::mark/publ/delete/archive | LOW — simple JSON |
| Search | viewfeed.js | Feeds::search | MEDIUM |
| API | (external clients) | API class | LOW — pure JSON |

### Dimension 4: Coupling / Cohesion Quality

| Component | Cohesion | Coupling | Assessment |
|-----------|----------|----------|------------|
| `functions.php` | LOW (kitchen sink) | HIGH (everything imports it) | Split into modules by domain |
| `functions2.php` | LOW (continuation of above) | HIGH | Split into modules by domain |
| Handler classes | MEDIUM (grouped by feature) | MEDIUM (share DB, session) | Good migration units |
| Database adapters | HIGH (single responsibility) | LOW (via interface) | Clean migration |
| Feed parser | HIGH (parsing only) | LOW | Clean migration |
| Plugin system | HIGH | LOW (hook-based) | Migrate as unit |
| Session/auth | MEDIUM | HIGH (session globals) | Refactor during migration |

### Dimension 5: Complexity Hotspots

Files ranked by migration complexity (considering size, coupling, and criticality):

| Rank | File | Why Complex |
|------|------|-------------|
| 1 | `include/functions.php` | 2000+ lines, core of everything, auth + config + utils |
| 2 | `include/functions2.php` | 2500+ lines, query building, HTML rendering, search |
| 3 | `include/rssfuncs.php` | 1300+ lines, feed engine, daemon logic |
| 4 | `classes/feeds.php` | 38KB, server-rendered HTML, complex queries |
| 5 | `classes/api.php` | 22KB, must maintain backward compatibility |
| 6 | `classes/rpc.php` | 15KB, state mutations, counter updates |
| 7 | `classes/pluginhost.php` | Cross-cutting, singleton, design decision |
| 8 | `classes/pref/feeds.php` | Complex tree building, batch operations |
| 9 | `classes/pref/filters.php` | Complex rule/action CRUD |
| 10 | `include/sessions.php` | Security-critical, session validation |

### Dimension 6: PHP-Specific Patterns Requiring Translation

| PHP Pattern | Python Equivalent | Affected Files |
|-------------|-------------------|----------------|
| `$_SESSION` globals | Flask session / Django middleware | 50+ files |
| `$_REQUEST` superglobal | `request.args` / `request.form` | All handlers |
| `include_once` / `require_once` | Python `import` | All files |
| `__autoload()` | Python module system (automatic) | autoload.php |
| `$this->dbh->query("SQL...")` | SQLAlchemy session.execute() | 200+ locations |
| `db_escape_string()` | Parameterized queries (automatic) | 200+ locations |
| `json_encode()` / `json_decode()` | `json.dumps()` / `json.loads()` | Many handlers |
| `preg_match()` / `preg_replace()` | `re.match()` / `re.sub()` | functions*.php |
| `htmlspecialchars()` | Jinja2 auto-escape | Many handlers |
| `date()` / `strtotime()` | `datetime` module | Many files |
| Singleton pattern | Module-level instance or dependency injection | Db, PluginHost |
| PHP error handler | Python logging + exception handling | errorhandler.php |

---

## Migration Flow Variants

### Variant A: Entity-First (Bottom-Up)

**Strategy**: Migrate database models first, then build business logic on top.

```
Pass 1: SQLAlchemy models + Alembic migrations (all 35 tables)
Pass 2: Database access layer (repository pattern or direct ORM)
Pass 3: Core utilities (config, auth, session, preferences)
Pass 4: Feed engine (parser, updater, cache)
Pass 5: API handlers (RPC, Feeds, Article, Pref_*)
Pass 6: Plugin system
Pass 7: Frontend adaptation (or keep existing)
Pass 8: Deployment (Docker, CI/CD)
```

**Pros**:
- Clean foundation — models drive everything
- Can validate schema early with real data
- Natural for SQLAlchemy-centric development

**Cons**:
- Long time before any runnable code
- Hard to test without handlers
- Models may need revision when business logic reveals patterns

### Variant B: Call-Graph-First (Top-Down)

**Strategy**: Migrate along the call graph, starting from entry points and working inward.

```
Pass 1: Entry points + bootstrap (Flask app, config, routing)
Pass 2: Handler base classes + dispatch logic
Pass 3: Core handlers (Feeds, Article, RPC) with stub DB
Pass 4: Database layer (replace stubs with real ORM)
Pass 5: Feed engine
Pass 6: Preference handlers
Pass 7: Plugin system
Pass 8: Polish + deployment
```

**Pros**:
- Runnable skeleton early
- Natural for agile/incremental development
- Can use stubs to test routing before DB is ready

**Cons**:
- Stub management overhead
- May need to refactor handlers when DB layer solidifies
- Risk of building on wrong abstractions

### Variant C: Vertical Slice (Feature-First)

**Strategy**: Migrate complete vertical slices — one feature at a time, including its models, logic, API, and frontend.

```
Slice 1: Auth + Users (models + session + login + user mgmt)
Slice 2: Feeds + Categories (models + CRUD + display)
Slice 3: Articles + Headlines (models + view + mark/star)
Slice 4: Feed Update Engine (parser + daemon + cache)
Slice 5: Labels + Tags (models + CRUD + assignment)
Slice 6: Filters (models + rules + actions)
Slice 7: Preferences + Profiles
Slice 8: Plugin System
Slice 9: API (external)
Slice 10: Deployment
```

**Pros**:
- Each slice is testable end-to-end
- Parallel development possible (different slices)
- Natural for team-based migration

**Cons**:
- Cross-cutting concerns (sessions, config) must be established early
- Shared utilities need early extraction from functions.php
- Slices have dependencies (Articles need Feeds need Users)

### Variant D: Graph-Driven Migration (tree-sitter + NetworkX native)

**Strategy**: Walking skeleton first, then entity models, then follow the **tree-sitter-
parsed call graph** for business logic ordering. Every phase uses five dependency dimensions
(call, class, db_table, hook, include) for ordering decisions and gate validation.

**Graph tools** (run before Phase 1b, re-run when PHP source changes):
- `tools/graph_analysis/build_php_graphs.py` — 5-dimension PHP graph (tree-sitter + NetworkX + Leiden)
- `tools/graph_analysis/validate_coverage.py` — 5-dimension Python↔PHP coverage validator
- Output: `tools/graph_analysis/output/` (call_graph.json, function_levels.json, hook_graph.json, db_table_graph.json, class_graph.json, communities_summary.json, report.txt)

**Phase gate workflow** (every phase):
```
1. build_php_graphs.py → fresh graph data
2. validate_coverage.py → coverage report (call, import, db_table, hook, class)
3. Fix gaps: missing imports, missing hook invocations, missing Source comments
4. Re-validate → 0 unmatched for in-scope modules
5. Tests green → commit
```

```
Phase 1a — Walking Skeleton:
  - Flask app factory + Blueprints + config from env
  - 10 core SQLAlchemy models (sqlacodegen + review)
  - Flask-Login + session + POST /api/ op=login + GET /api/status
  - Docker Compose: Flask + PostgreSQL + Redis
  - Security: bcrypt, parameterized queries, CSRF, Jinja2 autoescape
  - Gate: docker compose up → login works → tests green
  - Graph gate: models map to DB_TABLE graph communities [0]-[6]

Phase 1b — Complete Foundation:
  - Remaining 21 models (31 total active tables)
  - Alembic baseline migration (31 tables, 75 seed rows, schema_version=124)
  - Pluggy hookspecs for all 24 hooks (matches 24 HOOK_* in hook graph)
  - PluginManager singleton with specs registered
  - Decomposition map (specs/13) with graph levels + DB_TABLE communities
  - Gate: 31 tables, alembic clean, 24 hookspecs, tests green
  - Graph gate: all models vs DB_TABLE graph, all hookspecs vs hook graph

Phase 2 — Core Logic (call graph levels L0-L15):
  2a. utils/misc.py + plugins/loader.py (L0-L3)
  2b. http/client.py + articles/sanitize.py + feed_tasks.py hooks (L1-L2)
  2c. prefs/ops.py (L1 — get_pref is most-depended function, 30+ callers)
  2d. auth/authenticate.py (L14-L15 — depends on all of 2a-2c)
  Gate: Rule 10a traceability, tests green
  Graph gate: call dimension + hook dimension (HOOK_SANITIZE, HOOK_AUTH_USER,
    HOOK_FETCH_FEED, HOOK_FEED_FETCHED, HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER)

Phase 3 — Business Logic (9 batches, graph dependency DAG, L0-L10):
  3.0 utils/feeds.py + ccache.py + labels.py (L0-L4, DB communities [0],[3])
  3.1 feeds/categories.py (L2-L3, DB community [0])
  3.2 feeds/ops.py (L1-L7, DB community [5])
  3.3 feeds/counters.py (L2-L6, DB community [3])
  3.4 articles/ops.py + articles/tags.py (L0-L5, DB community [4])
  3.5 articles/filters.py (L0-L3, DB community [2])
  3.6 articles/search.py (L2-L5, DB community [4])
  3.7 tasks/housekeeping.py (L1-L3, DB community [1])
  3.8 tasks/feed_tasks.py article persistence (L0-L10, DB community [4])
  Gate: Rule 10a, 80% coverage per module, no circular imports, tests green
  Graph gate: all 5 dimensions — call + import + db_table + hook + class

Phase 4 — API Handlers (5 batches, 17 ops):
  4.1 Auth guards + getUnread/getCounters/getPref/getConfig/getLabels (L2-L5)
  4.2 getCategories/getFeeds/getArticle (L2-L3)
  4.3 updateArticle/catchupFeed/setArticleLabel/updateFeed (L5-L6)
  4.4 getHeadlines/subscribeToFeed/unsubscribeFeed/shareToPublished (L5-L7)
  4.5 getFeedTree (BFS, custom)
  Gate: Rule 10a, JSON contract tests, tests green
  Graph gate: call dimension (api.php edges), hook dimension
    (HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_API)

Phase 5 — Cross-Cutting:
  5a. Plugin system (discovery, loading, per-user enable/disable, built-ins)
      Graph: class community [8] (Auth_Internal+Plugin), call levels L2-L3
  5b. External API (REST, rate limiting)
  5c. Celery refinement (Beat schedule, Flower, retry policies)
  5d. Logging (structlog) + error handling
  5e. UI support: init_params.py (L2-L3, hooks: HOOK_HOTKEY_MAP, HOOK_HOTKEY_INFO,
      HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM, HOOK_PREFS_TAB/SECTION/TABS,
      HOOK_PREFS_EDIT_FEED, HOOK_PREFS_SAVE_FEED, HOOK_UPDATE_TASK)
  Gate: all remaining hook invocations wired, tests green
  Graph gate: full 5-dimension validation → ≥95% coverage metric

Phase 6 — Deployment:
  6a. Production Docker (Gunicorn+gevent, Celery worker, Celery Beat)
  6b. CI/CD pipeline (includes validate_coverage.py in CI)
  6c. MySQL-to-PostgreSQL data migration via pgloader
  6d. Frontend asset serving
  Gate: docker compose up → full stack operational
  Graph gate: final coverage metric confirmed ≥95%
```

**Pros**:
- Walking skeleton gives runnable app in 1-2 days (addresses AR4)
- sqlacodegen automates bulk model generation (addresses R1 solo-dev concern)
- Hook specs early, invocation points in Phases 3-4 (addresses R7 plugin gap)
- Feed engine designed for Celery from Phase 3c (addresses R13 refactoring concern)
- Explicit async strategy: Gunicorn+gevent for web, Celery+httpx for feeds (addresses AR7)
- Each phase has entry/exit criteria and test suite (addresses R10)
- Security remediation aligned to phase boundaries

**Cons**:
- More planning overhead (mitigated by this detailed phase plan)
- Phase 1b still has 25 models (mitigated by sqlacodegen automation)

### Variant E: Granular Multi-Pass

**Strategy**: Multiple fine-grained passes, each addressing one dimension.

```
Pass 1 — Models:     All SQLAlchemy models (entity dimension)
Pass 2 — Access:     Repository/service layer for each entity cluster
Pass 3 — Auth:       Authentication + authorization + sessions
Pass 4 — Config:     Configuration + environment + preferences
Pass 5 — Parsing:    Feed parser + item extractors (isolated, testable)
Pass 6 — Engine:     Feed update engine + caching + daemon
Pass 7 — Handlers:   All handler classes (one per iteration)
Pass 8 — API:        External REST API
Pass 9 — Plugins:    Plugin system + hook framework
Pass 10 — Frontend:  Adapt or rewrite frontend
Pass 11 — Deploy:    Docker + CI/CD + monitoring
```

**Pros**: Maximum granularity, each pass is small and focused
**Cons**: Many passes, slower overall, more integration testing needed

---

## Graph Analysis Findings (tree-sitter + NetworkX evidence)

Script: `tools/graph_analysis/build_php_graphs.py` (run 2026-04-04 against source-repos/ttrss-php).
Five dimensions analysed: **include**, **call**, **class**, **db_table**, **hook**.
Raw output: `tools/graph_analysis/output/` (JSON + report.txt).

### Include Graph (138 nodes, 34 edges, Leiden → 106 communities)

**Community [1]** is the authoritative "core include cluster" — 11 files that are
always included together via the main entry points (backend.php, index.php, prefs.php):

```
autoload.php, ccache.php, db-prefs.php, db.php, errorhandler.php,
functions.php, functions2.php, labels.php, login_form.php, sessions.php
+ sanity_check.php
```

Evidence updates:
- `ccache.php` and `labels.php` confirmed as core-level includes — they are loaded
  alongside functions.php from every entry point, not only from rssfuncs.php.
  This validates placing them at Phase 3a before feeds/counters (Phase 3c).
- `sessions.php` is in the core include cluster (it is the PHP session handler,
  registered via `session_set_save_handler`). This is consistent with its Auth
  community membership; its auth-function citations (authenticate_user etc.)
  remain in functions.php (Core community), as corrected in the community table above.

### Call Graph (1206 nodes, 2100 edges, Leiden → 303 communities)

303 communities because Leiden at default resolution partitions isolated third-party
libraries (QRcode, PHPMailer, SphinxClient) into single-member communities. The 12
large communities (>10 members) are the meaningful ones.

**Dependency levels** (Level 0 = leaf with no callees; Level N = depends on Level N-1):

| Level | Count | Key nodes |
|-------|-------|-----------|
| 0 | 552 | auth/base stubs, all leaf utility methods |
| 1-8 | 649 | Application handler methods, build up progressively |
| 9 | 4 | `send_headlines_digests`, `QRrawcode::__construct` |
| 10 | 2 | `rssfuncs.php::update_daemon_common`, `QRcode::encodeInput` |
| 13 | 6 | `Auth_Internal::authenticate`, `Pref_Prefs::otpenable` |
| **14** | **2** | **`authenticate_user`** (functions.php), `QRcode::png` |
| **15** | **5** | **`login_sequence`** (functions.php), `API::login`, `Handler_Public::login/rss`, `ttrss/backend.php` |
| **16** | **4** | **Entry points**: `ttrss/index.php`, `ttrss/prefs.php`, `Handler_Public::sharepopup`, `Handler_Public::subscribe` |

Evidence updates:
- `authenticate_user` (Level 14) → `login_sequence` (Level 15) → entry points (Level 16)
  confirms the migration order: authenticate_user must exist before login_sequence, which
  must exist before any handler entry point. Validates Phase 2a ordering.
- `update_daemon_common` at Level 10 is the deepest non-QR node, confirming feed engine
  is the most dependency-heavy business logic chain. Validates Phase 3c ordering.

### DB_Table Graph (60 nodes, 126 edges, Leiden → 7 communities)

7 clean communities provide authoritative service-boundary evidence:

| Community | Code files | Tables |
|-----------|-----------|--------|
| **[0] Feed/API access** | api.php, feeds.php, handler/public.php, pref/feeds.php, rpc.php, digest.php, labels.php, opml.php | ttrss_access_keys, ttrss_archived_feeds, ttrss_entry_comments, ttrss_feed_categories, ttrss_headlines_read, ttrss_user_feeds, ttrss_user_labels2, ttrss_user_read, ttrss_user_starred |
| **[1] Auth/System** | auth/base.php, dbupdater.php, logger/sql.php, pref/system.php, sanity_check.php, sessions.php, plugins/auth_internal/init.php, register.php | ttrss_error_log, ttrss_sessions |
| **[2] Filters** | opml.php, pref/filters.php, pref/labels.php, update.php | ttrss_filter_actions, ttrss_filter_types, ttrss_filters, ttrss_filters2, ttrss_filters2_actions, ttrss_filters2_rules |
| **[3] Counters+Prefs** | db/prefs.php, pref/prefs.php, **ccache.php**, **functions.php** | ttrss_cat_counters_cache, ttrss_counters_cache, ttrss_prefs, ttrss_user_labels2, ttrss_user_prefs |
| **[4] Articles/Tags** | article.php, dlg.php, functions2.php, rssfuncs.php | ttrss_enclosures, ttrss_entries, ttrss_tags |
| **[5] Feeds/Users** | pref/users.php, feedbrowser.php, install/index.php | ttrss_feedbrowser_cache, ttrss_feeds, ttrss_linked_feeds |
| **[6] Plugin** | pluginhost.php | ttrss_plugin_storage |

Evidence updates:
- **DB community [3]** places `ccache.php` and `functions.php` in the same community
  alongside counter cache and prefs tables — confirms the bidirectional coupling noted in
  the Call Graph Communities table above. `ccache.php` does NOT belong in the Feed Engine
  community (it accesses the same tables as functions.php counter functions).
- **DB community [4]** (`ttrss_entries, ttrss_enclosures, ttrss_tags`) groups rssfuncs.php,
  functions2.php, article.php, dlg.php — confirms articles/ops.py scope (Phase 3d).
- **DB community [6]** (pluginhost.php → ttrss_plugin_storage only) confirms plugin storage
  is fully isolated; can be the last business-logic module before handlers.

### Hook Graph (40 nodes, 39 edges, Leiden → 7 communities)

**ENHANCED 2026-04-04**: Script fix added `get_hooks()` detection alongside `add_hook()`/`run_hooks()`.
All 24 hooks now detected (was 8). 23 `get_hooks()` invocations discovered.

| Community | Hooks | Invokers |
|-----------|-------|----------|
| **[0] Feed pipeline** | HOOK_ARTICLE_FILTER, HOOK_FEED_FETCHED, HOOK_FEED_PARSED, HOOK_FETCH_FEED, HOOK_HOUSE_KEEPING | rssfuncs.php (5 hooks), handler/public.php (HOUSE_KEEPING + UPDATE_TASK), update.php (UPDATE_TASK) |
| **[1] Article rendering** | HOOK_ARTICLE_BUTTON, HOOK_ARTICLE_LEFT_BUTTON, HOOK_RENDER_ARTICLE, HOOK_SANITIZE, HOOK_HOTKEY_INFO, HOOK_HOTKEY_MAP | functions2.php (6 hooks) |
| **[2] Headline display** | HOOK_HEADLINE_TOOLBAR_BUTTON, HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_CDM | feeds.php (5 hooks), api.php (2), handler/public.php (QUERY_HEADLINES), pref/filters.php (QUERY_HEADLINES) |
| **[3] Pref sections** | HOOK_PREFS_TAB, HOOK_PREFS_TAB_SECTION | pref/feeds.php, pref/filters.php, pref/labels.php, pref/prefs.php, pref/system.php, pref/users.php |
| **[4] Feed editing** | HOOK_PREFS_EDIT_FEED, HOOK_PREFS_SAVE_FEED | pref/feeds.php |
| **[5] Auth** | HOOK_AUTH_USER | functions.php (INVOKES), plugins/auth_internal/init.php (sole REGISTERS) |
| **[6] API rendering** | HOOK_RENDER_ARTICLE_API | api.php |
| **[7] UI chrome** | HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM, HOOK_PREFS_TABS | index.php, prefs.php |

Evidence updates:
- `functions.php` INVOKES `HOOK_AUTH_USER` via `get_hooks()` (line 711) — this is the
  authentication loop, confirmed: `foreach (PluginHost::getInstance()->get_hooks(PluginHost::HOOK_AUTH_USER) as $plugin)`.
- `functions2.php` is the primary article-rendering hook invoker (6 hooks), confirming
  that articles/ops.py and articles/sanitize.py need hook invocations for SANITIZE,
  RENDER_ARTICLE, ARTICLE_BUTTON, ARTICLE_LEFT_BUTTON, HOTKEY_INFO, HOTKEY_MAP.
- `rssfuncs.php` invokes 5 hooks in the feed pipeline: FETCH_FEED → FEED_FETCHED →
  FEED_PARSED → ARTICLE_FILTER → HOUSE_KEEPING. This matches the feed_tasks.py hook ordering.
- `feeds.php` invokes 5 hooks — these are Phase 4 handler hooks.
- `api.php` invokes QUERY_HEADLINES + RENDER_ARTICLE_API — Phase 4 API handler hooks.
- Only 1 REGISTERS edge in entire codebase: auth_internal/init.php → HOOK_AUTH_USER.
  All other hooks have zero REGISTERS (they are registered dynamically by plugins at runtime,
  not statically in the source code being analyzed).

### Class Graph (81 nodes, 27 edges, Leiden → 55 communities)

Key evidence from class hierarchy:
- Community [0] (13 members: Article, Dlg, Feeds, Handler_Protected, Opml, PluginHandler,
  Pref_Feeds, Pref_Filters, Pref_Labels, Pref_Prefs, Pref_System, Pref_Users, RPC) —
  all extend Handler_Protected; confirms a single Handler base class chain.
- Community [8]: `Auth_Internal` and `Plugin` in the same community — Auth_Internal
  extends both Plugin and IAUthModule (it is a plugin that implements auth).
- All DB adapters (Db_Mysql, Db_Mysqli, Db_PDO, Db_Pgsql) are isolated singletons —
  confirm clean adapter pattern, no shared state between adapters.

---

## Recommendation Matrix

| Criterion | Variant A | Variant B | Variant C | Variant D (Graph-Driven) | Variant E |
|-----------|-----------|-----------|-----------|-------------------|-----------|
| Time to first runnable code | Slow | Fast | Medium | **Fast (1-2 days)** | Slow |
| Refactoring risk | Low | High | Medium | Low | Low |
| Testability per phase | Medium | Low | High | **High (exit criteria)** | High |
| Parallel development | Low | Low | High | Medium | Medium |
| Dependency management | Easy | Hard | Medium | Easy | Easy |
| Planning overhead | Low | Low | Medium | Medium | High |
| Best for solo dev | Good | OK | Harder | **Best** | OK |
| Best for team | OK | Harder | **Best** | Good | Good |
| Async strategy | N/A | N/A | N/A | **Explicit (Celery+httpx — ADR-0011/0015 accepted 2026-04-04)** | N/A |
| Plugin hook timing | Late | Early (stubs) | Per-slice | **Specs early, invocations mid** | Late |
| Stub/mock debt | High | High | Low | **Low (walking skeleton)** | Medium |

### Recommendation: **Variant D (Graph-Driven Migration)**

Rationale:
1. Walking skeleton (Phase 1a) delivers runnable app in 1-2 days — addresses AR4
2. sqlacodegen automates bulk model generation — addresses R1 solo-dev concern
3. **tree-sitter + NetworkX graph analysis** drives batch ordering via topological levels (L0-L16)
4. **5-dimension graph validation** at every phase gate (call, class, db_table, hook, include)
5. Hook specifications defined early (Phase 1b), validated against hook graph (24/24 hooks)
6. Feed engine designed for Celery from Phase 3 — addresses R13 refactoring concern
7. Explicit async strategy: Gunicorn+gevent for web, Celery+httpx for feeds — addresses AR7
8. **Automated coverage metric**: validate_coverage.py confirms ≥95% at Phase 6 gate
7. Each phase has entry/exit criteria and dedicated test suite — addresses R10
8. functions.php/functions2.php decomposition map with phase assignments
9. pgloader for MySQL-to-PostgreSQL data migration
10. Phase-by-phase security remediation aligned to spec 06 findings

**Accepted after compliance review. See `docs/decisions/0001-compliance-review-response.md`.**

---

## Next Steps

1. **Choose migration variant** (this document provides the options)
2. **Set up Python project skeleton** in `target-repos/`
3. **Build automated call graph** using NetworkX from PHP source
4. **Validate entity clusters** against actual SQL query patterns
5. **Create per-phase migration tickets** based on chosen variant
6. **Establish testing strategy** (unit tests per phase, integration tests per slice)
