---
name: memory-index
description: Cross-session project index — spec-kit structure, active plan pointers, session history, rules
type: reference
---

# Memory Index

## Project Structure

```
OSS_Migration/
├── constitution.md               ← specs/architecture/00-project-charter.md
├── specs/
│   ├── architecture/             (14 reference specs — stable, read-only)
│   │   ├── 00-project-charter.md
│   │   ├── 01-architecture.md
│   │   ├── 02-database.md
│   │   ├── 03-api-routing.md
│   │   ├── 04-frontend.md
│   │   ├── 05-plugin-system.md
│   │   ├── 06-security.md
│   │   ├── 07-caching-performance.md
│   │   ├── 08-deployment.md
│   │   ├── 09-source-index.md
│   │   ├── 10-migration-dimensions.md
│   │   ├── 11-business-rules.md
│   │   ├── 12-testing-strategy.md
│   │   ├── 13-decomposition-map.md
│   │   └── 14-semantic-discrepancies.md
│   ├── 001-foundation/           (DONE) spec.md + plan.md + tasks.md
│   ├── 002-core-logic/           (DONE) spec.md + plan.md + tasks.md
│   ├── 003-business-logic/       (DONE) spec.md + plan.md + tasks.md
│   ├── 004-api-handlers/         (DONE) spec.md + plan.md + tasks.md
│   ├── 005-semantic-verification/ (DONE) spec.md + plan.md + tasks.md
│   └── 006-deployment/           (DONE) spec.md + plan.md + tasks.md
├── memory/
│   ├── MEMORY.md                 ← This file
│   ├── phase4_plan_2026-04-04.md ← Source for specs/004-api-handlers/
│   ├── phase5_plan_2026-04-04.md ← Source for specs/005-semantic-verification/ (Phase 5)
│   ├── phase6_plan_2026-04-04.md ← Source for specs/006-deployment/
│   ├── semantic_verification_plan.md ← Source for specs/005-semantic-verification/ (5b)
│   ├── test_coverage_uplift_plan.md  ← Source for specs/006-deployment/tasks.md (coverage uplift)
│   ├── session_2026-04-03.md
│   ├── session_2026-04-04.md
│   └── session_2026-04-05.md
└── docs/
    ├── decisions/                (ADRs 0001-0016, MADR 4.0 format)
    └── reports/
```

## Project Status: PHASE 6 COMPLETE — READY TO SHIP

All 6 phases of the PHP→Python migration are done. Phase 6 deployment gates B1–B6 are ALL complete.

**[specs/006-deployment/tasks.md](../specs/006-deployment/tasks.md)** — Phase 6 Deployment (**DONE**)

| Batch | Status | Deliverable |
|-------|--------|-------------|
| B1 CI Foundation | **DONE** | 4 CI jobs (lint/test/build/coverage-gate) on master push |
| B2 Validator Calibration | **DONE** | Coverage gap = 0; ≥95% confirmed |
| B3 Gunicorn + Docker | **DONE** | gunicorn.conf.py (gthread, post_fork dispose), multi-stage Dockerfile |
| B4 Production Compose + nginx | **DONE** | docker-compose.prod.yml, nginx/nginx.conf, .env.production.example |
| B5 Data Migration Scripts | **DONE** | pre_migration_audit.sh, pgloader.load, convert_php_serialized.py |
| B6 Coverage Gate Lock | **DONE** | continue-on-error removed; .github/workflows/deploy.yml on tag push |

**Test Coverage Uplift** — **DONE** — 89.3% overall, 1275 unit/integration tests, 0 gaps

**SME Review Track (2026-04-06)** — **DONE** — spec-15 + ADR-0017/18/19; 10 frontend features; 67/68 E2E pass

**Next action: Tag `v1.0.0` to trigger deploy.yml, OR continue with Phase 7 deferred items.**

See [Phase 7 plan](project/phase7-plan.md) for deferred backlog.

## Spec-Kit Phase Summary

| Spec | Phase | Status | Key deliverable |
|------|-------|--------|----------------|
| [001-foundation](../specs/001-foundation/) | 1 | DONE | Models, auth, DB, Alembic, app factory |
| [002-core-logic](../specs/002-core-logic/) | 2 | DONE | Feed parsing, counter cache, filters, labels, sanitize |
| [003-business-logic](../specs/003-business-logic/) | 3 | DONE | Prefs CRUD, digests, OPML, backend blueprint |
| [004-api-handlers](../specs/004-api-handlers/) | 4 | DONE | 17 API ops; 2-guard auth; getFeedTree BFS |
| [005-semantic-verification](../specs/005-semantic-verification/) | 5/5b | DONE | 14 hooks wired; 40-cat taxonomy; 105+ fixes; 598 tests; 0 gaps |
| [006-deployment](../specs/006-deployment/) | 6 | **DONE** | CI, Docker, nginx, pgloader, coverage gate ≥95%, deploy.yml |

## Integration Tests (as of 2026-04-05)

**[memory/integration_test_plan.md](integration_test_plan.md)** — ~100 integration tests across 7 files

Files created:
- `tests/integration/conftest.py` — shared fixtures (seed_prefs, api_user, logged_in_client, test_feed, test_entry_pair)
- `tests/integration/test_api_login.py` — updated (seed_prefs dependency added)
- `tests/integration/test_api_meta.py` — getVersion, getApiLevel, isLoggedIn, logout, NOT_LOGGED_IN, seq echo
- `tests/integration/test_api_counters.py` — getUnread, getCounters, getPref, getConfig, getLabels, API_DISABLED
- `tests/integration/test_api_feeds.py` — getFeeds, getCategories, subscribeToFeed, unsubscribeFeed, getFeedTree, updateFeed
- `tests/integration/test_api_articles.py` — getHeadlines, getArticle, updateArticle, catchupFeed, setArticleLabel, shareToPublished
- `tests/integration/test_models.py` — User/Feed/Entry/UserEntry/Category/Label/PluginStorage CRUD + cascade deletes
- `tests/integration/test_auth_flow.py` — full auth cycle, session persistence, hash upgrade, base64 fallback
- `tests/integration/test_security.py` — pwd_hash leak prevention, NOT_LOGGED_IN on all ops, user isolation, no traceback

Run: `just test-int` (requires docker compose services on :5433/:6380)

## Key Numbers (as of 2026-04-06)

| Metric | Value |
|--------|-------|
| Tests passing | 598 unit/integration + 67 E2E |
| E2E tests | 67 passed / 68 total (1 skipped — PHP Dojo JS compat) |
| Coverage gaps | 0 |
| Hooks wired | 14 of 14 |
| Discrepancies fixed (Phase 5b) | 105+ |
| Files below 80% coverage | 32 (pre-uplift baseline) |
| CI coverage (strict, with B2 calibration) | ≥95% |
| SME review items implemented | 10 new frontend features (tags, publish, mark-unread, categories, filters, OPML, category assignment, update interval, force refresh) |

## Session History

- [2026-04-03](sessions/2026-04-03.md) — Spec-kit built, P0+P1 ADRs accepted, Phase 1a complete
- [2026-04-04](sessions/2026-04-04.md) — Phases 1b-4 complete; graph analysis built + enhanced
- [2026-04-05 morning](session_2026-04-05.md) — Semantic verification 105+ fixes; spec-kit refactor; justfile + coverage gate
- [2026-04-05 full](session_2026-04-05.md) — Integration tests (115), SPA frontend (ADR-0017), PHP UI faithful clone, E2E automation (51 Playwright), DB isolation fix
- [2026-04-06](sessions/2026-04-06.md) — SME review ingested; ADR-0017/18/19 + spec-15; 10 frontend features added; 67/68 E2E pass

## Rules (MANDATORY)

- [Consistency Rule](feedback/consistency-rule.md) — Update ALL referencing locations on any status/decision change
- [Spec Consultation](feedback/spec-consultation.md) — Read relevant specs/ before planning any phase
- [No-Skip Rule](feedback/no-skip-rule.md) — NEVER skip a test; fix the code or implement the missing feature

## ADR Index

| ADR | Decision | Status |
|-----|----------|--------|
| [0001](../docs/decisions/0001-migration-flow-variant.md) | Migration flow variant (D-revised) | accepted |
| [0002](../docs/decisions/0002-python-framework.md) | Python framework (Flask) | accepted |
| [0003](../docs/decisions/0003-database-engine.md) | Database engine (PostgreSQL) | accepted |
| [0004](../docs/decisions/0004-frontend-strategy.md) | Frontend strategy → resolved by ADR-0017 | accepted |
| [0005](../docs/decisions/0005-call-graph-analysis.md) | Call graph analysis | accepted |
| [0006](../docs/decisions/0006-orm-strategy.md) | ORM strategy (SQLAlchemy) | accepted |
| [0007](../docs/decisions/0007-session-management.md) | Session management (Flask-Login) | accepted |
| [0008](../docs/decisions/0008-password-migration.md) | Password migration (argon2id) | accepted |
| [0009](../docs/decisions/0009-feed-credential-encryption.md) | Feed credential encryption (Fernet) | accepted |
| [0010](../docs/decisions/0010-plugin-system.md) | Plugin system (pluggy) | accepted |
| [0011](../docs/decisions/0011-background-worker.md) | Background worker (Celery) | accepted |
| [0012](../docs/decisions/0012-logging-strategy.md) | Logging strategy (structlog) | proposed |
| [0013](../docs/decisions/0013-i18n-approach.md) | i18n approach | proposed |
| [0014](../docs/decisions/0014-feed-parsing-library.md) | Feed parsing library (feedparser) | accepted |
| [0015](../docs/decisions/0015-http-client.md) | HTTP client (httpx) | accepted |
| [0016](../docs/decisions/0016-semantic-verification.md) | Semantic verification methodology | accepted |
| [0017](../docs/decisions/0017-frontend-spa-vanilla-js.md) | Vanilla JS SPA replaces Dojo (ADR-0004 resolved) | accepted |
| [0018](../docs/decisions/0018-drag-drop-deferred.md) | Drag-drop category assignment deferred; dropdown used | accepted |
| [0019](../docs/decisions/0019-preferences-modal-pattern.md) | Simplified in-app preferences modal (tabbed) | accepted |

## Local Dev Startup

- [local-dev-startup](project/local-dev-startup.md) — Flask :5001 + Celery + test DB (:5433/:6380); first-time setup; 3 bugs fixed 2026-04-06

## Phase 7 Backlog

- [Phase 7 plan](project/phase7-plan.md) — All deferred items with backend readiness + effort estimates

| Item | Effort | Priority |
|------|--------|---------|
| Labels CRUD in settings modal | S (~80 lines JS) | P0 |
| Users tab in settings modal (admin) | S (~100 lines JS) | P0 |
| Drag-drop category assignment (ADR-0018) | M (~150 lines JS) | P1 |
| Multi-rule filter builder | M (~120 lines JS) | P1 |
| Keyboard shortcuts | S (~60 lines JS) | P1 |
| Logging strategy (ADR-0012) | S (config) | P2 |
| i18n / localization (ADR-0013) | XL | P2 |
| Plugin UI hooks | varies | P2 |

**Release gate before Phase 7:** `git tag v1.0.0 && git push origin v1.0.0` → triggers deploy.yml

## Coverage Verification

- [Coverage Verification Guide](../docs/reports/coverage-verification-guide.md) — Two modes: (1) Migration coverage check (function-by-function, not file-level); (2) Semantic coverage check (PHP vs Python logic review). Run `python tools/graph_analysis/validate_coverage.py` for mode 1.

## SME Review Artifacts

- [SME Review 2026-04-06](project/sme-review-2026-04-06.md) — Demo walkthrough (7 areas), test scenario matrix (13 categories), gaps: Aggregation/Display, Plugins/Themes, Preferences, i18n
- [spec-15 SME Review](../specs/architecture/15-sme-review.md) — Full functional inventory from demo + test spreadsheet; canonical gap list

## Archive (superseded — kept for audit trail)

Moved to `memory/archive/`. Superseded by spec-kit phase specs (001-006).

| Archived | Superseded by |
|----------|--------------|
| master_plan.md | specs/001-006 plan.md files |
| phase2-6_plan_*.md | specs/002-006 plan.md files |
| semantic_verification_plan.md | specs/005-semantic-verification/plan.md |
| coverage_gap_plan.md | specs/006-deployment/tasks.md §Coverage |
| rework_plan.md, rework_execution.md | Phase 5b complete; 0 gaps confirmed |
| next_session_plan.md | specs/006-deployment/tasks.md |
