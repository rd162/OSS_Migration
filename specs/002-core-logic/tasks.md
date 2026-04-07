# Tasks 002 — Core Logic

**Status:** ALL DONE  
**Completed:** 2026-04-04  
**Spec ref:** specs/002-core-logic/spec.md  
**Plan ref:** specs/002-core-logic/plan.md

---

## Batch 1 — Utils + Plugin Loader (L0-L3) **[US-2a]**

> **Story:** As a developer, I need the plugin loader and utility functions available so that all subsequent modules can load plugins and call shared utilities without stubs.

- [x] [P] [US-2a] Implement `ttrss/utils/misc.py` — all L0-L3 shared utility functions  
  _Source: include/functions.php + include/functions2.php (utility sections)_
- [x] [P] [US-2a] Implement `ttrss/plugins/loader.py` — plugin discovery and loading  
  _Source: classes/pluginhost.php (KIND constants, directory discovery)_
- [x] [US-2a] Verify `KIND_ALL=1`, `KIND_SYSTEM=2`, `KIND_USER=3` match PHP constants  
  _Source: classes/pluginhost.php:KIND_* constants_
- [x] [P] [US-2a] Write unit tests with PHP source citations in docstrings  
  _AGENTS.md test traceability rule_
- [x] [US-2a] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] pytest green | [x] loader available before auth in import graph

---

## Batch 2 — HTTP Client + Sanitizer + Hook Wiring (L1-L2) **[US-2b]**

> **Story:** As a developer, I need the HTTP client, HTML sanitizer, and all four feed task hook invocations so that feed fetching and article sanitization work correctly.

- [x] [P] [US-2b] Implement `ttrss/http/client.py` — sync URL utilities + async fetch_file_contents (Celery-only)  
  _Source: include/functions.php:fetch_file_contents (lines 197-365), include/functions2.php (lines 1210-1310)_
- [x] [US-2b] Confirm `_fetch_feed_async` stays in feed_tasks.py (ETag-specific logic, not moved)  
  _Architectural decision — see plan.md_
- [x] [P] [US-2b] Implement `ttrss/articles/sanitize.py` with HOOK_SANITIZE pipeline  
  _Source: include/functions2.php:sanitize (lines 831-965)_
- [x] [US-2b] Verify HOOK_SANITIZE fires BEFORE `strip_harmful_tags()` (check line numbers)  
  _Source: include/functions2.php lines 919-931_
- [x] [US-2b] Verify `strip_harmful_tags(doc, allowed_elements, disallowed_attributes)` is standalone callable  
  _Source: include/functions2.php:strip_harmful_tags (lines 967+)_
- [x] [US-2b] Verify `format_inline_player()` absent from sanitize.py  
  _Eliminated: belongs to Phase 3 article rendering path_
- [x] [US-2b] Wire HOOK_FETCH_FEED in feed_tasks.py BEFORE feedparser.parse()  
  _Source: include/rssfuncs.php:270_
- [x] [US-2b] Wire HOOK_FEED_PARSED in feed_tasks.py AFTER feedparser.parse()  
  _Source: include/rssfuncs.php:394_
- [x] [US-2b] Wire HOOK_ARTICLE_FILTER in feed_tasks.py per entry inside entry loop  
  _Source: include/rssfuncs.php:687_
- [x] [US-2b] Delete `_sanitize_html` stub — replace with call to `articles.sanitize.sanitize()`  
  _Closes TODO Phase 2 #4_
- [x] [US-2b] Confirm grep "TODO Phase 2" returns 0  
  _QG exit criterion_
- [x] [P] [US-2b] Write unit tests for sanitize.py including hook ordering test  
  _AGENTS.md test traceability rule_
- [x] [US-2b] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] 4 TODOs closed | [x] hook order correct | [x] format_inline_player absent | [x] pytest green

---

## Batch 3 — Preferences (L1) **[US-2c]**

> **Story:** As a developer, I need `initialize_user_prefs` and `get_pref`/`set_pref` so that auth and subsequent phases can read and write user preferences.

- [x] [US-2c] Implement `ttrss/prefs/ops.py` — initialize_user_prefs, get_pref, set_pref  
  _Source: include/functions.php:initialize_user_prefs (lines 639-688)_
- [x] [US-2c] Verify NULL profile path uses `WHERE profile IS NULL` (not `= NULL`)  
  _Source: include/functions.php — SQL idiom correctness_
- [x] [US-2c] Verify function iterates `ttrss_prefs` rows (not `ttrss_user_prefs`) for preference discovery  
  _Source: include/functions.php — table selection_
- [x] [US-2c] Verify idempotent behavior — inserts only missing rows  
  _Behavioral parity requirement (P5)_
- [x] [P] [US-2c] Write unit tests for both SQL paths (NULL profile, named profile)  
  _AGENTS.md test traceability rule_
- [x] [US-2c] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] IS NULL check | [x] correct table | [x] pytest green

---

## Batch 4 — Authentication (L14-L15) **[US-2d]**

> **Story:** As a developer, I need the full authentication flow including single-user mode, plugin auth, session management, and user initialization so that the application can authenticate real users.

- [x] [US-2d] Implement `ttrss/auth/authenticate.py` — authenticate_user, logout_user, initialize_user  
  _Source: include/functions.php:authenticate_user (lines 706-771), logout_user (lines 807-812), initialize_user (lines 796-805)_
- [x] [US-2d] Verify SINGLE_USER_MODE path: `session["auth_module"] = False`, uid=1, no hook call  
  _Source: include/functions.php:authenticate_user_
- [x] [US-2d] Verify normal path: `pm.hook.hook_auth_user(login, password)` firstresult  
  _Source: include/functions.php:authenticate_user — ADR-0010_
- [x] [US-2d] Verify post-login sequence: update last_login → session fields → `initialize_user_prefs(uid)` → `load_user_plugins(uid)`  
  _Source: include/functions.php:authenticate_user (post-auth block)_
- [x] [US-2d] Verify `session["auth_module"]` set to plugin class name on every auth path  
  _Exit criterion #8_
- [x] [US-2d] Verify `initialize_user` inserts exactly 2 real feed rows with canonical URLs  
  _Source: include/functions.php:initialize_user lines 796-805 — exact URLs required_
- [x] [US-2d] Verify `logout_user` calls `flask_login.logout_user()` + `session.clear()` + `session.modified=True`  
  _Source: include/functions.php:logout_user — Redis key deletion_
- [x] [P] [US-2d] Write unit tests for all auth paths (SINGLE_USER_MODE, normal, plugin failure)  
  _AGENTS.md test traceability rule_
- [x] [US-2d] Rule 10a adversarial self-refine — 0 traceability violations  
  _AGENTS.md Rule 10a_
- [x] [US-2d] Verify `pytest --cov --cov-fail-under=80` green on PostgreSQL backend  
  _QG-1 gate_

**Gate:** [x] session["auth_module"] on all paths | [x] 2 exact feed rows | [x] Redis key deleted | [x] pytest green

---

## Summary

| Batch | Tasks | Completed | Gate |
|-------|-------|-----------|------|
| 1 — Utils + Loader | 5 | 5 | PASSED 2026-04-04 |
| 2 — HTTP + Sanitize + Hooks | 13 | 13 | PASSED 2026-04-04 |
| 3 — Preferences | 6 | 6 | PASSED 2026-04-04 |
| 4 — Authentication | 10 | 10 | PASSED 2026-04-04 |
| **Total** | **34** | **34** | **ALL DONE** |
