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
│   └── 006-deployment/           (ACTIVE) spec.md + plan.md + tasks.md
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

## Active Plan (CURRENT)

**[specs/006-deployment/tasks.md](../specs/006-deployment/tasks.md)** — Phase 6 Deployment (IN PROGRESS)

Status of deployment batches:
- B1 CI Foundation: **DONE** — all 4 CI jobs running on master push
- B2 Validator Calibration: **DONE** — coverage gate 0 gaps; ≥95% confirmed
- B3 Gunicorn + Docker: PENDING
- B4 Production Compose + nginx: PENDING
- B5 Data Migration Scripts: PENDING
- B6 Coverage Gate Lock: PENDING

**[memory/test_coverage_uplift_plan.md](test_coverage_uplift_plan.md)** — Test Coverage Uplift (COMPLETE)

- Coverage Uplift B1–B5: **ALL DONE** — 89.3% overall, 1275 unit/integration tests, 0 gaps

**SME Review Track (2026-04-06 — COMPLETE)**
- Ingested: demo video (90 cadres), transcription, test spreadsheet
- Created: spec-15, ADR-0017/18/19
- Implemented: 10 new frontend features (tags, publish, mark-unread, categories, filters, OPML, category assignment, update interval, force refresh)
- E2E: 67/68 tests pass (↑ from 51/52)

Next action: Phase 6 B3 — Gunicorn config + multi-stage Dockerfile.

## Spec-Kit Phase Summary

| Spec | Phase | Status | Key deliverable |
|------|-------|--------|----------------|
| [001-foundation](../specs/001-foundation/) | 1 | DONE | Models, auth, DB, Alembic, app factory |
| [002-core-logic](../specs/002-core-logic/) | 2 | DONE | Feed parsing, counter cache, filters, labels, sanitize |
| [003-business-logic](../specs/003-business-logic/) | 3 | DONE | Prefs CRUD, digests, OPML, backend blueprint |
| [004-api-handlers](../specs/004-api-handlers/) | 4 | DONE | 17 API ops; 2-guard auth; getFeedTree BFS |
| [005-semantic-verification](../specs/005-semantic-verification/) | 5/5b | DONE | 14 hooks wired; 40-cat taxonomy; 105+ fixes; 598 tests; 0 gaps |
| [006-deployment](../specs/006-deployment/) | 6 | ACTIVE | CI, Docker, nginx, pgloader, coverage gate ≥95% |

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

## ADR Index

| ADR | Decision | Status |
|-----|----------|--------|
| [0001](../docs/decisions/0001-migration-flow-variant.md) | Migration flow variant (D-revised) | accepted |
| [0002](../docs/decisions/0002-python-framework.md) | Python framework (Flask) | accepted |
| [0003](../docs/decisions/0003-database-engine.md) | Database engine (PostgreSQL) | accepted |
| [0004](../docs/decisions/0004-frontend-strategy.md) | Frontend strategy | proposed |
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
