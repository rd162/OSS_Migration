---
id: 005
title: Cross-Cutting Implementation + Semantic Verification
status: done
phases: 5, 5b
source: memory/phase5_plan_2026-04-04.md, memory/semantic_verification_plan.md
---

# Spec 005 — Phase 5: Cross-Cutting + Semantic Verification

## Scope

Two sub-phases, both DONE:

- **Phase 5** — Cross-cutting infrastructure: plugin system, structlog, 14 hooks, Flask-Limiter, Celery Beat, Prefs blueprints
- **Phase 5b (Semantic Verification)** — Deep PHP→Python semantic audit: 40-category taxonomy, 8 integration pipelines, 105+ discrepancies fixed, 598 tests, 0 coverage gaps

## User Stories (Phase 5)

| ID | Story |
|----|-------|
| US-001 | As a plugin author, I can implement hookspecs and have them called at all 14 hook sites |
| US-002 | As an operator, all Python logs are structured JSON (structlog) without modifying existing files |
| US-003 | As an API consumer, the API rate-limits to 60 req/min per IP (Flask-Limiter) |
| US-004 | As an operator, Celery Beat runs feed updates every 5 min and housekeeping every 60 min |
| US-005 | As a user, all prefs blueprints (6 sub-handlers) return JSON-only responses (AR-1) |

## Functional Requirements (Phase 5)

| ID | Requirement | Hook/Source |
|----|-------------|-------------|
| FR-001 | AuthInternal plugin implements hook_auth_user; delegates to ttrss.auth.password.verify_password | auth_internal/init.php |
| FR-002 | TtRssPluginStorage accessor: get/set/get_all/clear; JSON serialization (replaces PHP serialize) | pluginhost.php:200-240 |
| FR-003 | load_user_plugins() calls get_all after each plugin load | pluginhost.php:load_data |
| FR-004 | structlog stdlib wrapper in app factory; all Phase 5 modules use structlog.get_logger | ADR-0012 |
| FR-005 | HOOK_UPDATE_TASK fires at 2 sites in feed_tasks.py and 2 sites in housekeeping.py | update.php:161,190; handler/public.php:411,421 |
| FR-006 | HOOK_RENDER_ARTICLE_CDM in articles/ops.py CDM branch only (AR-7: not in ui/init_params.py) | classes/feeds.php:517 |
| FR-007 | HOOK_HEADLINE_TOOLBAR_BUTTON in articles/ops.py format_headlines_list (AR-7) | classes/feeds.php:138 |
| FR-008 | Flask-Limiter: 60 per minute on API blueprint; RATELIMIT_ENABLED=False in test config | api.php (no PHP equiv) |
| FR-009 | get_hotkeys_info, get_hotkeys_map, make_runtime_info, make_init_params in ttrss/ui/init_params.py | functions2.php:90-200; index.php:180-260 |
| FR-010 | make_init_params fires HOOK_TOOLBAR_BUTTON and HOOK_ACTION_ITEM; all return JSON-serializable dicts | index.php:213,252 |
| FR-011 | Celery Beat: dispatch_feed_updates every 5 min, run_housekeeping every 3600s | rssfuncs.php (daemon timing) |
| FR-012 | update_feed task: max_retries=3, retry_backoff=True, retry_backoff_max=600, retry_jitter=True | ADR-0011 |
| FR-013 | Prefs blueprint views.py: HOOK_PREFS_TABS at /prefs GET | prefs.php:139 |
| FR-014 | Prefs blueprint feeds.py: HOOK_PREFS_EDIT_FEED (748), HOOK_PREFS_SAVE_FEED (981), HOOK_PREFS_TAB_SECTION (×2), HOOK_PREFS_TAB | pref/feeds.php |
| FR-015 | Prefs blueprints filters/labels/system/user_prefs/users: each fires HOOK_PREFS_TAB and/or HOOK_PREFS_TAB_SECTION at correct call sites | pref/*.php |

## Functional Requirements (Phase 5b — Semantic Verification)

| ID | Requirement |
|----|-------------|
| FR-101 | 40-category discrepancy taxonomy (D01-D40) applied to all 472 functions + 37 ORM models |
| FR-102 | 8 integration pipelines verified end-to-end (Feed Update, Article Search, API Lifecycle, Auth, Counter Cache, OPML, Digest, Plugin) |
| FR-103 | Complexity-tiered triage: 52 Tier 1 deep, ~150 Tier 2, ~270 Tier 3, 37 models |
| FR-104 | 105+ discrepancies fixed across all taxonomy categories |
| FR-105 | 598 tests passing, 0 coverage gaps |

## Discrepancy Taxonomy (40 Categories)

See `memory/semantic_verification_plan.md` for full definitions. Categories:

- **SQL & Query Semantics (D01-D10):** join topology, computation locus, column mismatch, subquery nesting, WHERE conditions, ORDER BY/LIMIT, dialect remnants, transaction boundary, SQL validation, parameter type
- **Type System & Coercion (D11-D16):** systemic type coercion, PHP falsy divergence, null/empty/isset, numeric boundary, intval divergence, array/dict semantics
- **Data Flow & Content (D17-D22):** content priority inversion, GUID construction, field truncation, timestamp validation, encoding normalization, string interpolation
- **Session, Config & State (D23-D28):** session state elimination, session fallback, config constant mapping, profile-aware queries, global variables, in-memory cache elimination
- **Return Value & API Contract (D29-D33):** return shape divergence, return materialization, error envelope, HTTP response headers, JSON response structure
- **Feature & Behavior (D34-D40):** feature absent, hook argument mismatch, hook call site missing, side effect order, error recovery model, DOM/parsing model, transactional semantics

## Acceptance Criteria

### Phase 5 Final Gate (A6)

- [ ] All 14 deferred hooks = 0 missing in validate_coverage.py
- [ ] Class dimension: Plugin → AuthInternal community [8] = 0 missing
- [ ] AR-2: 0 direct DB calls in blueprints/prefs/
- [ ] AR-5: 0 new ORM models in blueprints/prefs/
- [ ] All 537 + new tests pass

### Phase 5b Final Gate

- [ ] 105+ discrepancies fixed
- [ ] 598 tests passing
- [ ] 0 coverage gaps

## Status

**DONE** — Phase 5: all 14 hooks wired, all 7 batch gates passed, 537+ tests passing.
**DONE** — Phase 5b: 105+ discrepancies fixed, 598 tests, 0 coverage gaps.
