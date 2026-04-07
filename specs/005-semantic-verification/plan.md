---
id: 005
title: Phase 5 Implementation Plan — Cross-Cutting + Semantic Verification
status: done
selection: Phase 5 — Condorcet winner Candidate A' (Hook-Community Topological Drain, Revised). Phase 5b — v3 deep methodology (v2 had correct inventory, inadequate taxonomy).
date: 2026-04-04
---

# Plan 005 — Phase 5: Cross-Cutting + Semantic Verification

---

## Constitution Check

*Gate: Must pass before A0 begins. Re-evaluated at A6 final gate.*

| Principle | Requirement | Satisfied |
|-----------|-------------|-----------|
| P1 Library-First | structlog configured once in app factory; rate limiter wired as extension; no logging scattered across modules | ✓ — single configure() call in `__init__.py` |
| P2 Test-First | 537+ tests pass at every batch gate; no batch committed without full test suite green | ✓ — A0–A6 gates all require 537+ pass |
| P3 Source Traceability | `# Source:` on all new code; AR-7 hook placement constraint documented | ✓ — Rule 10a per batch |
| P5 Behavioral Parity | All 14 deferred hook sites match PHP source line anchors exactly | ✓ — A6 final gate: 0 missing |
| ADR-0012 Logging | structlog stdlib wrapper only; no direct `logging.getLogger` in new modules | ✓ — enforced in A0 |

---

## Part A — Phase 5: Cross-Cutting Infrastructure

### Core Principle

7 batches gated on hook-graph community evidence. Plugin system + structlog in A0 (first batch). Each batch closes exactly one hook-graph community or one infrastructure concern before proceeding.

### Hook Routing Table

| Hook | PHP source | Line | Python target |
|------|-----------|------|--------------|
| HOOK_UPDATE_TASK | update.php + handler/public.php | 190 + 421 | tasks/feed_tasks.py + tasks/housekeeping.py |
| HOOK_RENDER_ARTICLE_CDM | classes/feeds.php | 517 | articles/ops.py — CDM branch |
| HOOK_HEADLINE_TOOLBAR_BUTTON | classes/feeds.php | 138 | articles/ops.py — format_headlines_list |
| HOOK_HOTKEY_MAP | include/functions2.php | 186 | ttrss/ui/init_params.py |
| HOOK_HOTKEY_INFO | include/functions2.php | 110 | ttrss/ui/init_params.py |
| HOOK_TOOLBAR_BUTTON | index.php | 213 | ttrss/ui/init_params.py (make_init_params) |
| HOOK_ACTION_ITEM | index.php | 252 | ttrss/ui/init_params.py (make_init_params) |
| HOOK_PREFS_TABS | prefs.php | 139 | blueprints/prefs/views.py |
| HOOK_PREFS_TAB (×6 sites) | pref/feeds.php, filters.php, labels.php, prefs.php, system.php, users.php | multiple | blueprints/prefs/*.py |
| HOOK_PREFS_TAB_SECTION (×3 sites) | pref/feeds.php ×2, prefs.php, users.php | multiple | blueprints/prefs/*.py |
| HOOK_PREFS_EDIT_FEED | pref/feeds.php | 748 | blueprints/prefs/feeds.py |
| HOOK_PREFS_SAVE_FEED | pref/feeds.php | 981 | blueprints/prefs/feeds.py |

**Critical AR-7 constraint:** HOOK_RENDER_ARTICLE_CDM and HOOK_HEADLINE_TOOLBAR_BUTTON are feeds.php-sourced rendering hooks → articles/ops.py only. They must NOT appear in ui/init_params.py.

### Batch Overview

| Batch | Scope | Hooks closed | Graph gate |
|-------|-------|-------------|-----------|
| A0 | Plugin system + structlog | — (auth_internal hookimpl) | Class community [8]; 537 tests pass |
| A1 | HOOK_UPDATE_TASK | 2 sites (feed_tasks + housekeeping) | Community [2] HOOK_UPDATE_TASK = 0 |
| A2 | CDM + toolbar rendering hooks | HOOK_RENDER_ARTICLE_CDM, HOOK_HEADLINE_TOOLBAR_BUTTON | Community [0] rendering = 0 |
| A3 | Flask-Limiter | — | 537 pass + rate-limit smoke |
| A4 | ui/init_params.py + UI hooks | HOOK_HOTKEY_MAP/INFO, HOOK_TOOLBAR_BUTTON/ACTION_ITEM | Communities [0]+[5] = 0 |
| A5 | Celery Beat + Flower + retry | — | Infrastructure: beat_schedule + retry policy |
| A6 | Prefs blueprints (6 sub-handlers) | HOOK_PREFS_TABS + PREFS_TAB/SECTION/EDIT_FEED/SAVE_FEED | FINAL: all 14 deferred hooks = 0 |

### A0 Gate
- Class dimension: `Plugin → AuthInternal` hierarchy in class graph community [8]
- `pm.hook.hook_auth_user` returns non-None user_id in test
- All 537 existing tests pass

### A6 Gate (Phase 5 FINAL)
- `validate_coverage.py` reports all 14 deferred hooks = 0 missing
- Class dimension community [8] = 0 missing
- AR-2 audit: 0 direct DB calls in blueprints/prefs/
- AR-5 audit: 0 new ORM models in blueprints/prefs/

---

## Part B — Phase 5b: Semantic Verification (v3 Deep Methodology)

### Why v3 Was Required

v2 improved inventory (472 functions listed) but the verification methodology remained superficial:
- D1-D18 taxonomy too narrow: concrete sampling found 15+ uncovered discrepancy categories
- Semantic traps table had only 15 rows; PHP codebase has 50+ translation-hostile patterns
- No cross-function verification: caller/callee contract mismatches invisible
- No integration pipeline checks: 12-step feed update pipeline; error in step 4 breaks step 7
- No complexity triage: 5-line and 200-line functions treated identically

### v3 Methodology

**40-category discrepancy taxonomy (D01-D40)** — organized by domain:
- A: SQL & Query Semantics (D01-D10)
- B: Type System & Coercion (D11-D16)
- C: Data Flow & Content (D17-D22)
- D: Session, Config & State (D23-D28)
- E: Return Value & API Contract (D29-D33)
- F: Feature & Behavior (D34-D40)

**8 Integration Pipelines verified end-to-end:**
1. Feed Update (12 steps, CRITICAL) — GUID construction, content priority, transaction boundary
2. Article Search (8 steps, HIGH) — virtual feed IDs, label_base_index conversion
3. API Request Lifecycle (6 steps, HIGH) — seq echoing, API_E_* codes
4. Auth Flow (5 steps, HIGH) — hook_auth_user signature, session variables
5. Counter Cache Update (4 steps, MEDIUM) — post-commit invalidation
6. OPML Import/Export Roundtrip (6 steps, MEDIUM) — recursive category hierarchy
7. Digest Generation (4 steps, MEDIUM) — truncate + strip_tags + timezone
8. Plugin Lifecycle (3 steps, MEDIUM) — load_data storage round-trip

**Complexity Triage:** 52 Tier 1 deep, ~150 Tier 2 standard, ~270 Tier 3 spot-check, 37 models

### Outcome

- 105+ discrepancies identified and fixed
- 598 tests passing
- 0 coverage gaps
