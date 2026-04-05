# Spec 002 — Core Logic

**Status:** DONE  
**Completed:** 2026-04-04  
**Phase:** 2 of 6  
**Plan source:** memory/phase2_plan_2026-04-04.md (Candidate A, Condorcet 2-0)  
**Constitution ref:** P1 (Library-First), P2 (Test-First), P3 (Source Traceability), P5 (Behavioral Parity)

---

## User Stories

### US-2a — Plugin Loader + Utilities

> As a developer, I need the plugin loader and utility functions available so that all subsequent modules can load plugins and call shared utilities without stubs.

**Acceptance Criteria:**

- [ x ] `ttrss/utils/misc.py` implemented with all Level 0-3 call-graph utilities
- [ x ] `ttrss/plugins/loader.py` implemented with `KIND_ALL=1`, `KIND_SYSTEM=2`, `KIND_USER=3` matching PHP constants
- [ x ] Plugin loader available before auth — no circular dependency

### US-2b — HTTP Client + Feed Sanitization + Hook Wiring

> As a developer, I need the HTTP client, HTML sanitizer, and all four feed task hook invocations so that feed fetching and article sanitization work correctly.

**Acceptance Criteria:**

- [ x ] `ttrss/http/client.py` implemented: sync URL utilities (Flask-safe) + `async fetch_file_contents()` (Celery-only)
- [ x ] `ttrss/articles/sanitize.py`: `HOOK_SANITIZE` fires BEFORE `strip_harmful_tags()` (matches PHP functions2.php lines 919-931)
- [ x ] `strip_harmful_tags()` importable as standalone callable
- [ x ] `format_inline_player()` absent from sanitize.py (belongs to Phase 3 article rendering)
- [ x ] 4 feed_tasks.py TODO Phase 2 markers closed (grep returns 0)
- [ x ] HOOK_FETCH_FEED fires before `feedparser.parse()`
- [ x ] HOOK_FEED_PARSED fires after `feedparser.parse()`
- [ x ] HOOK_ARTICLE_FILTER fires per entry inside entry loop

### US-2c — Preferences

> As a developer, I need `initialize_user_prefs` and `get_pref`/`set_pref` so that auth and subsequent phases can read and write user preferences.

**Acceptance Criteria:**

- [ x ] `ttrss/prefs/ops.py` implements dual SQL path (NULL profile vs named profile)
- [ x ] `initialize_user_prefs` uses `IS NULL` (not `= NULL`) for null profile path
- [ x ] Iterates `ttrss_prefs` rows (not `ttrss_user_prefs`) for preference discovery

### US-2d — Authentication

> As a developer, I need the full authentication flow including single-user mode, plugin auth, session management, and user initialization so that the application can authenticate real users.

**Acceptance Criteria:**

- [ x ] `ttrss/auth/authenticate.py`: SINGLE_USER_MODE path sets `session["auth_module"] = False`, uid=1
- [ x ] Normal auth path invokes `pm.hook.hook_auth_user` (firstresult)
- [ x ] On success: `session["auth_module"]` = plugin class name; calls `initialize_user_prefs(uid)` + `load_user_plugins(uid)`
- [ x ] `initialize_user` inserts exactly 2 real feed rows with canonical URLs
- [ x ] `logout_user` deletes Redis session key (not just cookie clear)
- [ x ] `session["auth_module"]` stored on every auth path

---

## Functional Requirements

| ID | Requirement | PHP Source | Graph Level |
|----|-------------|-----------|-------------|
| FR-201 | `ttrss/utils/misc.py` — shared utility functions | include/functions.php, include/functions2.php | L0-L3 |
| FR-202 | `ttrss/plugins/loader.py` — plugin discovery + loading | classes/pluginhost.php (KIND constants) | L0-L1 |
| FR-203 | `ttrss/http/client.py` — sync URL utils + async feed fetcher | include/functions.php:fetch_file_contents (lines 197-365), include/functions2.php (lines 1210-1310) | L1-L2 |
| FR-204 | `ttrss/articles/sanitize.py` — HTML sanitization pipeline | include/functions2.php:sanitize (lines 831-965), strip_harmful_tags (lines 967+) | L1-L2 |
| FR-205 | `ttrss/tasks/feed_tasks.py` — 4 hook invocations wired | include/rssfuncs.php (HOOK lines 270, 394, 687) | L1-L5 |
| FR-206 | `ttrss/prefs/ops.py` — initialize_user_prefs, get_pref, set_pref | include/functions.php:initialize_user_prefs (lines 639-688) | L1 |
| FR-207 | `ttrss/auth/authenticate.py` — full auth flow | include/functions.php:authenticate_user (lines 706-771), logout_user (lines 807-812), initialize_user (lines 796-805) | L14-L15 |

---

## Hook Invocation Requirements

| Hook | Fire Point | PHP Source | Status |
|------|-----------|-----------|--------|
| HOOK_SANITIZE | articles/sanitize.py, BEFORE strip_harmful_tags | functions2.php:919-931 | DONE |
| HOOK_FETCH_FEED | feed_tasks.py, BEFORE feedparser.parse() | rssfuncs.php:270 | DONE |
| HOOK_FEED_PARSED | feed_tasks.py, AFTER feedparser.parse() | rssfuncs.php:394 | DONE |
| HOOK_ARTICLE_FILTER | feed_tasks.py, per entry inside entry loop | rssfuncs.php:687 | DONE |
| HOOK_AUTH_USER | auth/authenticate.py, normal auth path | functions.php:authenticate_user | DONE |

---

## Exit Gate (15 Criteria)

1. [x] All 4 batch Rule 10a CRITIC/AUTHOR cycles passed (0 findings)
2. [x] `pytest --cov --cov-fail-under=80` green (PostgreSQL backend)
3. [x] `strip_harmful_tags` importable as standalone callable from articles.sanitize
4. [x] `sanitize()` invokes `pm.hook.hook_sanitize` BEFORE `strip_harmful_tags`
5. [x] `format_inline_player` absent from articles/sanitize.py
6. [x] HOOK_FETCH_FEED fires before `feedparser.parse()`
7. [x] HOOK_FEED_PARSED fires after `feedparser.parse()`
8. [x] `session["auth_module"]` stored in Redis-backed session on every auth path
9. [x] `initialize_user` inserts exactly 2 real rows with canonical URLs
10. [x] `logout_user` deletes Redis session key (not just cookie clear)
11. [x] `initialize_user_prefs` handles NULL profile and named profile via separate SQL
12. [x] All 4 feed_tasks.py TODO Phase 2 markers closed (grep returns 0)
13. [x] Every callable has `# Source:` / `# New:` / `# Inferred from:` comment
14. [x] Per-batch traceability verification records in memory/session_*.md
15. [x] Rule 16 checklist applied to any ADR status changes

---

## Constraints

- Strict topological ordering — no stubs, no shims. Each batch is independently correct at commit time.
- `_fetch_feed_async` in feed_tasks.py is NOT moved to http/client.py — has ETag-specific logic.
- MySQL branches eliminated from all modules in this phase (grep `DB_TYPE` = 0).
