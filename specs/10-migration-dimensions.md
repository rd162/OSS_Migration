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

| Cluster | Tables | Operating Code |
|---------|--------|----------------|
| **User Core** | ttrss_users, ttrss_sessions, ttrss_access_keys | sessions.php, functions.php (auth), auth_internal |
| **Feed Management** | ttrss_feeds, ttrss_feed_categories, ttrss_archived_feeds | pref/feeds.php, rssfuncs.php, feeds.php |
| **Article Content** | ttrss_entries, ttrss_user_entries, ttrss_enclosures, ttrss_entry_comments | rssfuncs.php, article.php, feeds.php, functions2.php |
| **Tagging & Labels** | ttrss_tags, ttrss_labels2, ttrss_user_labels2 | labels.php, article.php, rpc.php |
| **Filtering** | ttrss_filters2, ttrss_filters2_rules, ttrss_filters2_actions, ttrss_filter_types, ttrss_filter_actions | pref/filters.php, rssfuncs.php |
| **Preferences** | ttrss_prefs, ttrss_user_prefs, ttrss_prefs_types, ttrss_prefs_sections, ttrss_settings_profiles | db-prefs.php, pref/prefs.php |
| **Caching** | ttrss_counters_cache, ttrss_cat_counters_cache, ttrss_feedbrowser_cache | ccache.php, feedbrowser.php |
| **Plugin** | ttrss_plugin_storage | pluginhost.php |
| **System** | ttrss_version, ttrss_themes, ttrss_error_log | dbupdater.php, logger/sql.php |
| **Federation** | ttrss_linked_instances, ttrss_linked_feeds | (minimal code — low priority) |

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

### Variant D: Hybrid Entity-then-Graph (Revised after compliance review)

**Strategy**: Walking skeleton first, then entity models, then follow call graph for business logic.

```
Phase 1a — Walking Skeleton (1-2 days):
  - Flask app factory + Blueprints + config from env
  - 10 core SQLAlchemy models (via sqlacodegen, then reviewed):
    ttrss_users, ttrss_sessions, ttrss_feeds, ttrss_feed_categories,
    ttrss_entries, ttrss_user_entries, ttrss_prefs, ttrss_user_prefs,
    ttrss_access_keys, ttrss_version
  - Flask-Login + session + POST /api/ op=login + GET /api/status
  - Docker Compose: Flask + PostgreSQL + Redis
  - Security: bcrypt, parameterized queries, CSRF, Jinja2 autoescape
  - Exit: docker compose up → login works → tests green

Phase 1b — Complete Foundation:
  - Remaining 25 models (sqlacodegen + review)
  - Alembic baseline migration
  - Pluggy hook specifications (@hookspec) for all 24 hooks
  - PluginManager singleton with specs registered
  - functions.php/functions2.php decomposition map finalized

Phase 2 — Core Logic (call graph order):
  2a. Auth + Sessions (deepest dependency) + HOOK_AUTH_USER invocation
  2b. Preference system
  2c. Utility modules (decomposed from functions.php/functions2.php)

Phase 3 — Business Logic (dependency DAG order):
  3a. ccache.py + labels.py (no inter-dependencies between these two;
      ccache.py must precede feeds/counters.py; labels.py must precede
      articles/ops.py and feeds/counters.py getLabelCounters)
  3b. feeds/categories.py (must precede feeds/ops.py — subscribe_to_feed
      creates categories)
  3c. feeds/ops.py + feeds/counters.py (counters depends on ccache + labels)
  3d. articles/ops.py (depends on labels.py for format_article_labels)
  3e. articles/search.py
  3f. tasks/housekeeping.py + utils/digest.py
  Hook invocations: HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER, etc. (inert)

Phase 4 — Handlers (frontend-backend contract):
  4a. RPC handler (state mutations)
  4b. Feeds handler (headline rendering via Jinja2)
  4c. Article handler
  4d. Preference handlers
  Hook invocations: HOOK_RENDER_ARTICLE, HOOK_PREFS_TAB, etc.
  Contract tests: JSON shapes match PHP originals for ~40 endpoints

Phase 5 — Cross-Cutting:
  5a. Plugin system (discovery, loading, per-user enable/disable, built-ins)
  5b. External API (REST, rate limiting)
  5c. Celery integration (@celery.task decorators on Phase 3c functions,
      Beat schedule, Flower monitoring)
  5d. Logging (structlog) + error handling

Phase 6 — Deployment:
  6a. Production Docker (Gunicorn+gevent, Celery worker, Celery Beat)
  6b. CI/CD pipeline
  6c. MySQL-to-PostgreSQL data migration via pgloader
  6d. Frontend asset serving
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

## Proposed Analysis Tools

### NetworkX + Leiden Community Detection

Use Python graph analysis to validate and refine the dimension analysis:

```python
import networkx as nx
from leidenalg import find_partition
import igraph

# Build call graph
G = nx.DiGraph()
# Add nodes: PHP files/functions
# Add edges: require/include/function calls
# Run Leiden community detection to find natural module boundaries

# Build entity graph
E = nx.Graph()
# Add nodes: database tables
# Add edges: foreign key relationships
# Run Leiden to find entity clusters

# Build coupling graph
C = nx.Graph()
# Add nodes: PHP classes
# Add edges: weighted by shared function calls / imports
# Run Leiden to find tightly coupled components
```

This can be automated by parsing the PHP source and building the graphs programmatically.

---

## Recommendation Matrix

| Criterion | Variant A | Variant B | Variant C | Variant D-revised | Variant E |
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

### Recommendation: **Variant D-revised (Walking Skeleton + Hybrid Entity-then-Graph)**

Rationale:
1. Walking skeleton (Phase 1a) delivers runnable app in 1-2 days — addresses AR4
2. sqlacodegen automates bulk model generation — addresses R1 solo-dev concern
3. Call-graph ordering prevents "missing dependency" issues
4. Hook specifications defined early (Phase 1b), invocation points placed when code is written (Phases 3-4) — addresses R7
5. Feed engine designed for Celery from Phase 3c — addresses R13 refactoring concern
6. Explicit async strategy: Gunicorn+gevent for web, Celery+httpx for feeds — addresses AR7
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
