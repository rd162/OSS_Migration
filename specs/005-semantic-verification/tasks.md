---
id: 005
title: Phase 5 Tasks — Cross-Cutting + Semantic Verification
status: done
---

# Tasks 005 — Phase 5: Cross-Cutting + Semantic Verification

All tasks DONE. Phase 5 all-14-hooks gate passed. Phase 5b: 105+ discrepancies fixed, 598 tests, 0 coverage gaps.

## Phase 5 — Cross-Cutting Infrastructure

### A0 — Plugin System Foundation + Structlog

- [x] Create `ttrss/plugins/auth_internal/__init__.py` — AuthInternal(Plugin), KIND=KIND_SYSTEM, hook_auth_user delegates to verify_password `# Source: plugins/auth_internal/init.php`
- [x] Create `ttrss/plugins/storage.py` — TtRssPluginStorage accessor: get/set/get_all/clear; JSON serialization `# Source: pluginhost.php:200-240`
- [x] Modify `ttrss/plugins/loader.py` — complete load_user_plugins() stub; call get_all after each plugin load `# Source: pluginhost.php:load_data (lines 214-225)`
- [x] Modify `ttrss/__init__.py` — structlog.configure() with stdlib ProcessorFormatter wrapper
- [x] Add `plugin_manager_with_auth` autouse fixture to `tests/conftest.py`
- [x] A0 Gate: Plugin → AuthInternal community [8] = 0 missing; 537 tests pass

### A1 — HOOK_UPDATE_TASK (community [2])

- [x] `ttrss/tasks/feed_tasks.py` — add 2 HOOK_UPDATE_TASK call sites (before + after dispatch loop) `# Source: update.php:161,190`
- [x] `ttrss/tasks/housekeeping.py` — add 2 HOOK_UPDATE_TASK call sites `# Source: handler/public.php:411,421`
- [x] Convert logging.getLogger to structlog.get_logger in both task files
- [x] A1 Gate: HOOK_UPDATE_TASK = 0 missing in validator; 537+ tests pass

### A2 — HOOK_RENDER_ARTICLE_CDM + HOOK_HEADLINE_TOOLBAR_BUTTON (community [0])

- [x] `ttrss/articles/ops.py` — add HOOK_RENDER_ARTICLE_CDM in format_article() CDM branch `# Source: classes/feeds.php:517` (AR-7: not in ui/)
- [x] `ttrss/articles/ops.py` — add HOOK_HEADLINE_TOOLBAR_BUTTON in format_headlines_list() `# Source: classes/feeds.php:138` (AR-7)
- [x] A2 Gate: both hooks = 0 missing; CDM hook not called on non-CDM path; 537+ tests pass

### A3 — Flask-Limiter

- [x] `ttrss/extensions.py` — add Limiter(key_func=get_remote_address) `# New: no PHP equivalent`
- [x] `ttrss/__init__.py` — limiter.init_app(app)
- [x] `ttrss/blueprints/api/views.py` — @limiter.limit("60 per minute") on op handlers
- [x] Test config — RATELIMIT_ENABLED=False
- [x] A3 Gate: all 537 tests pass; 429 on 61st request when RATELIMIT_ENABLED=True

### A4 — ui/init_params.py (communities [0]+[5])

- [x] Create `ttrss/ui/__init__.py`
- [x] Create `ttrss/ui/init_params.py` — get_hotkeys_info(), get_hotkeys_map(), make_runtime_info(), make_init_params() all return JSON-serializable dicts `# Source: functions2.php:90-200; index.php:180-260`
- [x] make_init_params fires HOOK_TOOLBAR_BUTTON and HOOK_ACTION_ITEM `# Source: index.php:213,252`
- [x] A4 Gate: 4 hooks = 0 missing; make_init_params output passes json.dumps(); no HTML in output

### A5 — Celery Beat + Flower + Retry Policies

- [x] `ttrss/celery_app.py` — beat_schedule: dispatch_feed_updates every 5 min, run_housekeeping every 3600s `# Source: rssfuncs.php (daemon timing); handler/public.php (housekeeping trigger)`
- [x] `ttrss/celery_app.py` — update_feed: max_retries=3, retry_backoff=True, retry_backoff_max=600, retry_jitter=True `# New: no PHP equivalent — Celery retry policy (ADR-0011)`
- [x] docker-compose.yml — Flower service added `# New: no PHP equivalent`
- [x] A5 Gate: beat_schedule entries verified; retry_backoff==True; 537+ tests pass

### A6 — Prefs Blueprints (communities [1]+[6]) — FINAL GATE

- [x] `ttrss/blueprints/prefs/__init__.py` — Blueprint package `# Source: prefs.php`
- [x] `ttrss/blueprints/prefs/views.py` — GET /prefs fires HOOK_PREFS_TABS `# Source: prefs.php:139`
- [x] `ttrss/blueprints/prefs/feeds.py` — HOOK_PREFS_EDIT_FEED (748), HOOK_PREFS_SAVE_FEED (981), HOOK_PREFS_TAB_SECTION (1434,1475), HOOK_PREFS_TAB (1480) `# Source: pref/feeds.php`
- [x] `ttrss/blueprints/prefs/filters.py` — HOOK_PREFS_TAB at 695 `# Source: pref/filters.php`
- [x] `ttrss/blueprints/prefs/labels.py` — HOOK_PREFS_TAB at 322 `# Source: pref/labels.php`
- [x] `ttrss/blueprints/prefs/user_prefs.py` — HOOK_PREFS_TAB_SECTION (×3) + HOOK_PREFS_TAB at 863 `# Source: pref/prefs.php`
- [x] `ttrss/blueprints/prefs/system.py` — HOOK_PREFS_TAB at 83 `# Source: pref/system.php`
- [x] `ttrss/blueprints/prefs/users.py` — HOOK_PREFS_TAB_SECTION at 354 + HOOK_PREFS_TAB at 449 `# Source: pref/users.php`
- [x] A6 Gate (FINAL): all 14 deferred hooks = 0 missing; community [8] = 0 missing; AR-2/AR-5 audits clean

---

## Phase 5b — Semantic Verification

### Taxonomy Application

- [x] 40-category taxonomy (D01-D40) defined and documented
- [x] 52 Tier 1 functions deep-audited (queryFeedHeadlines, update_rss_feed, sanitize, catchup_feed, etc.)
- [x] ~150 Tier 2 functions standard-audited
- [x] ~270 Tier 3 functions spot-checked
- [x] 37 ORM models verified against DDL + relationship semantics

### Integration Pipeline Verification

- [x] Pipeline 1: Feed Update (12 steps) — GUID construction, content priority inversion, transaction boundary, field truncation
- [x] Pipeline 2: Article Search (8 steps) — virtual feed paths, label_base_index conversion
- [x] Pipeline 3: API Request Lifecycle (6 steps) — seq echoing, API_E_* codes
- [x] Pipeline 4: Auth Flow (5 steps) — hook_auth_user signature, session variables
- [x] Pipeline 5: Counter Cache Update (4 steps) — post-commit invalidation order
- [x] Pipeline 6: OPML Import/Export Roundtrip (6 steps) — recursive category hierarchy
- [x] Pipeline 7: Digest Generation (4 steps)
- [x] Pipeline 8: Plugin Lifecycle (3 steps)

### Fixes Applied

- [x] 105+ discrepancies fixed (D01-D40 across all categories)

### Final State

- [x] 598 tests passing
- [x] 0 coverage gaps
- [x] Phase 5b DONE
