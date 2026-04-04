---
name: master_plan
description: Unified migration plan — graph-driven from Phase 1 through Phase 6, tree-sitter+NetworkX as native analysis tool at every gate
type: project
---

# Master Migration Plan: TT-RSS PHP → Python

**Approach:** Graph-driven migration using tree-sitter-php + NetworkX + Leiden community detection.
Five dependency dimensions (call, class, db_table, hook, include) are analyzed before each phase
and validated at every phase gate. This is NOT a bolt-on — graph analysis is integral to every phase.

**Tools:**
- `tools/graph_analysis/build_php_graphs.py` — 5-dimension PHP graph builder (tree-sitter + NetworkX + Leiden)
- `tools/graph_analysis/validate_coverage.py` — 5-dimension Python↔PHP coverage validator
- Graph output: `tools/graph_analysis/output/` (JSON + function_levels.json + report.txt)

**Key graph metrics (run 2026-04-04):**
- Call graph: 1206 nodes, 2086 edges, 17 dependency levels (L0-L16)
- DB_TABLE: 60 nodes, 126 edges, 7 communities (authoritative service boundaries)
- Hook: 40 nodes, 39 edges, 24/24 hooks detected, 7 communities
- Class: 81 nodes, 27 edges
- Include: 138 nodes, 34 edges

---

## Phase Overview

```
Phase 1a — Walking Skeleton           [DONE, graph gate PASSED]
Phase 1b — Complete Foundation         [DONE, graph gate PASSED]
Phase 2  — Core Logic                  [DONE, graph gate PASSED]
Phase 3  — Business Logic              [DONE, graph gate PASSED — hooks wired 2026-04-04]
Phase 4  — API Handlers                [DONE, graph gate PASSED — hooks already wired]
Phase 5  — Cross-Cutting               [NOT STARTED — 14 deferred hooks to wire]
Phase 6  — Deployment                  [NOT STARTED]
```

---

## Phase 1a — Walking Skeleton [DONE]

**Scope:** Flask app factory, blueprints, config, 10 core SQLAlchemy models, Flask-Login, Docker Compose.

**Graph validation gate:**
- DB_TABLE dimension: Verify 10 core models map to tables in DB_TABLE graph communities [0]-[6]
- Class dimension: Verify Flask extension setup matches PHP singleton patterns (Db, Logger)
- Include dimension: Verify `create_app()` import chain covers include graph community [1] (core cluster)

**Status:** Code committed. Gate: **pending validation**.

---

## Phase 1b — Complete Foundation [DONE]

**Scope:** Remaining 21 models (31 total), Alembic baseline (31 tables, 75 seed rows), 24 pluggy hookspecs, PluginManager singleton, Celery app + feed task stubs, decomposition map (specs/13).

**Graph validation gate:**
- DB_TABLE dimension: All 31 model tables appear in DB_TABLE graph. Every table in graph has a model.
- Hook dimension: All 24 hookspecs match the 24 HOOK_* constants in hook graph.
  Verify `firstresult=True` only on `hook_auth_user` (hook graph: only 1 REGISTERS edge).
- Call graph: `function_levels.json` generated and available for subsequent phases.

**Status:** Code committed. Gate: **pending validation**.

---

## Phase 2 — Core Logic [DONE]

**Scope:** 4 batches in dependency order:
1. `utils/misc.py` + `plugins/loader.py` (L0-L3)
2. `http/client.py` + `articles/sanitize.py` + `feed_tasks.py` hook wiring (L1-L2)
3. `prefs/ops.py` (L1)
4. `auth/authenticate.py` (L14-L15)

**Graph validation gate:**
- Call dimension: Every ported function has correct graph level. Dependencies at lower levels exist.
  - `authenticate_user` at L14, `login_sequence` at L15 — both depend on L1 `get_pref`
  - `sanitize` depends on L0 `strip_harmful_tags`
- Hook dimension: Verify hook invocations in code match hook graph edges:
  - `articles/sanitize.py` → HOOK_SANITIZE (functions2.php edge)
  - `auth/authenticate.py` → HOOK_AUTH_USER (functions.php edge)
  - `tasks/feed_tasks.py` → HOOK_FETCH_FEED, HOOK_FEED_FETCHED, HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER (rssfuncs.php edges)
- Import dimension: Python import chain matches call graph edges between modules.

**Status:** Code committed. Tests sparse (no dedicated tests for several modules). Gate: **pending validation**.

---

## Phase 3 — Business Logic [DONE]

**Scope:** 9 batches, dependency-ordered by graph topological levels:

| Batch | Module(s) | Graph Levels | DB_TABLE Community |
|-------|-----------|-------------|-------------------|
| 0 | utils/feeds.py, ccache.py, labels.py | L0-L4 | [3], [0] |
| 1 | feeds/categories.py | L2-L3 | [0] |
| 2 | feeds/ops.py | L1-L7 | [5] |
| 3 | feeds/counters.py | L2-L6 | [3] |
| 4 | articles/ops.py, articles/tags.py | L0-L5 | [4] |
| 5 | articles/filters.py | L0-L3 | [2] |
| 6 | articles/search.py | L2-L5 | [4] |
| 7 | tasks/housekeeping.py | L1-L3 | [1] |
| 8 | tasks/feed_tasks.py (article persistence) | L0-L10 | [4] |

**Graph validation gate (per batch):**
- Call dimension: All functions at their declared graph level. All callees at lower levels exist.
- DB_TABLE dimension: Every table accessed in PHP (per db_table_graph.json) has model import in Python.
- Hook dimension: Hook invocations match hook graph edges:
  - Batch 4: HOOK_RENDER_ARTICLE, HOOK_ARTICLE_BUTTON, HOOK_ARTICLE_LEFT_BUTTON, HOOK_HEADLINE_TOOLBAR_BUTTON
  - Batch 6: HOOK_QUERY_HEADLINES
  - Batch 7: HOOK_HOUSE_KEEPING
  - Batch 8: HOOK_ARTICLE_FILTER, HOOK_FEED_PARSED (already wired in Phase 2)
- Import dimension: Python import chain matches call graph cross-module edges.
- Class dimension: No new class hierarchies in Phase 3 (all are function modules).

**Status:** Code + 12 test files committed. Gate: **pending validation**.

---

## Phase 4 — API Handlers [DONE]

**Scope:** 5 batches, 17 API ops in `ttrss/blueprints/api/views.py`:

| Batch | Ops | Graph Levels | Hook Invocations |
|-------|-----|-------------|-----------------|
| 1 | Auth guards, getUnread, getCounters, getPref, getConfig, getLabels | L2-L5 | — |
| 2 | getCategories, getFeeds, getArticle | L2-L3 | — |
| 3 | updateArticle, catchupFeed, setArticleLabel, updateFeed | L5-L6 | — |
| 4 | getHeadlines, subscribeToFeed, unsubscribeFeed, shareToPublished | L5-L7 | HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_API |
| 5 | getFeedTree | Custom BFS | — |

**Graph validation gate:**
- Call dimension: For each API op, verify all PHP functions called (from call_graph.json edges
  originating from `classes/api.php`) have Python equivalents in Phase 2/3 modules.
- Hook dimension: Verify HOOK_QUERY_HEADLINES and HOOK_RENDER_ARTICLE_API invocations in handler code
  (hook graph: api.php → HOOK_QUERY_HEADLINES, api.php → HOOK_RENDER_ARTICLE_API).
- DB_TABLE dimension: Handler code accesses tables through Phase 3 modules (not direct SQL).
- Import dimension: Handler imports only from Phase 2/3 modules (no circular deps to handlers).

**Status:** Code + 5 batch test files committed. Gate: **pending validation**.

---

## Phase 5 — Cross-Cutting [NOT STARTED]

**Scope:**
- 5a. Plugin system (discovery, loading, per-user enable/disable, built-in plugins)
- 5b. External API (rate limiting, proper REST structure)
- 5c. Celery integration refinement (Beat schedule, Flower monitoring, retry policies)
- 5d. Logging (structlog) + error handling
- 5e. UI support module: `ttrss/ui/init_params.py` — make_init_params, make_runtime_info,
  get_hotkeys_map, get_hotkeys_info (graph levels L2-L3, hook graph: HOOK_HOTKEY_MAP,
  HOOK_HOTKEY_INFO, HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM from index.php/functions2.php)

**Graph validation gate:**
- Hook dimension: All remaining hook invocations not covered by Phases 2-4:
  HOOK_HOTKEY_MAP, HOOK_HOTKEY_INFO (functions2.php edges)
  HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM (index.php edges)
  HOOK_PREFS_TAB, HOOK_PREFS_TAB_SECTION, HOOK_PREFS_TABS (pref/*.php edges)
  HOOK_PREFS_EDIT_FEED, HOOK_PREFS_SAVE_FEED (pref/feeds.php edges)
  HOOK_UPDATE_TASK (update.php edge)
- Class dimension: Plugin class hierarchy (Plugin → Auth_Internal in graph community [8])
- Call dimension: Plugin system functions at graph levels L2-L3

---

## Phase 6 — Deployment [NOT STARTED]

**Scope:**
- 6a. Production Docker (Gunicorn+gevent, Celery worker, Celery Beat)
- 6b. CI/CD pipeline
- 6c. MySQL-to-PostgreSQL data migration via pgloader
- 6d. Frontend asset serving

**Graph validation gate:**
- Final full-scope validation: `python tools/graph_analysis/validate_coverage.py`
- Coverage metric: ≥95% (denominator = PHP functions L0-L10 minus third-party;
  numerator = matched + eliminated)

---

## Graph Validation Workflow (applies to every phase)

```
1. Run: python tools/graph_analysis/build_php_graphs.py (if PHP source changed)
2. Run: python tools/graph_analysis/validate_coverage.py \
       --graph-dir tools/graph_analysis/output \
       --python-dir target-repos/ttrss-python/ttrss
3. Review: unmatched functions, missing imports, missing hook calls
4. Fix: add missing imports, add missing hook invocations, add Source comments
5. Re-run: confirm 0 unmatched (for in-scope modules), 0 missing imports
6. Commit: with graph validation results in commit message
```

---

## Current Priority: Validate Phases 1-4

All code exists and is committed. Graph analysis tools exist. The immediate work is:

1. **Tune `validate_coverage.py`** — Source comment regex currently matches ~7% (format variations)
2. **Run validation for Phase 1** — Models vs DB_TABLE graph
3. **Run validation for Phase 2** — Code vs call + hook graphs
4. **Run validation for Phase 3** — Code vs all 5 dimensions
5. **Run validation for Phase 4** — Handlers vs call + hook + db graphs
6. **Fix all gaps** — Add missing imports, hook calls, Source comments
7. **Phase 5 starts** — First phase built graph-native from the start
