# ADR-0001: Migration Flow Variant

- **Status**: accepted
- **Date proposed**: 2026-04-03
- **Date accepted**: 2026-04-03
- **Deciders**: Project lead (adversarial review, unanimous convergence)
- **Depends on**: ADR-0002, ADR-0003

## Context

The PHP→Python migration requires a structured approach for ordering work across ~18,600 lines of application PHP code, 35 database tables, and 11 JavaScript files. Five flow variants were analyzed in `specs/10-migration-dimensions.md`, each driving migration by a different dimension.

**Spec references**: `specs/10-migration-dimensions.md` (6 dimensions, 5 flow variants, recommendation matrix), `specs/01-architecture.md` (application layers, handler hierarchy), `specs/09-source-index.md` (138-file inventory), `specs/00-project-charter.md` (goals G1-G6, constraints C1-C7).

The choice of variant determines:
- What gets built first
- When we get first runnable code
- How much refactoring risk we carry
- Whether work can be parallelized

## Options

### A: Entity-First (Bottom-Up)
Models first → DB access → utilities → handlers → plugins → frontend → deploy.
*Good foundation but slow to first runnable code.*

### B: Call-Graph-First (Top-Down)
Entry points → routing → handlers (with stubs) → DB layer → engine → polish.
*Fast skeleton but high refactoring risk when stubs replaced.*

### C: Vertical Slice (Feature-First)
Auth slice → Feeds slice → Articles slice → etc. Each end-to-end.
*Great for teams but cross-cutting concerns need early extraction.*

### D: Hybrid Entity-then-Graph — Revised (Recommended)
Phase 1a: Walking skeleton — Flask app + 10 core models + login endpoint + Docker Compose (1-2 days).
Phase 1b: Complete foundation — remaining 25 models (via sqlacodegen) + Alembic + pluggy hook specs.
Phase 2: Core logic in call-graph order (auth → prefs → utilities) with hook invocation points.
Phase 3: Business logic by entity cluster (feeds → articles → labels → filters); feed engine designed for Celery (pure functions, explicit params).
Phase 4: Handlers preserving frontend contract; contract tests against PHP JSON responses.
Phase 5: Cross-cutting (plugin loading, external API, Celery decorator integration, logging).
Phase 6: Deployment (Gunicorn+gevent, Celery workers, pgloader data migration, CI/CD).
*Walking skeleton in days, not weeks. Each phase has entry/exit criteria and test suite.*

### E: Granular Multi-Pass
11 fine-grained passes (models → access → auth → config → parsing → engine → handlers → API → plugins → frontend → deploy).
*Maximum granularity but high coordination overhead.*

## Preliminary Recommendation

**Variant D-revised** — walking skeleton addresses "time to first runnable code" concern while preserving Variant D's foundation-first benefits. Key improvements over original Variant D:

1. **Walking skeleton (Phase 1a)** delivers runnable app in 1-2 days, not weeks
2. **sqlacodegen** automates bulk model generation for Phase 1b (35 tables in minutes, review in hours)
3. **Hook specs defined early** (Phase 1b), invocation points placed in Phases 3-4 — no Phase 5 refactoring
4. **Feed engine designed for Celery** from Phase 3c — pure functions, decorator-only integration in Phase 5c
5. **Explicit async strategy**: Gunicorn+gevent for web, Celery+httpx async for feed fetching
6. **Phase-by-phase security remediation** aligned to spec 06 findings
7. **pgloader** for MySQL-to-PostgreSQL data migration
8. **functions.php decomposition map** — domain-based split with phase assignments

See `compliance-review-response.md` for full analysis of compliance findings and resolutions.

## Decision

**Variant D-revised** — accepted after compliance review confirmed Variant E violates R1 (solo dev suitability), R10 (testability), AR4 (excessive delay). See `compliance-review-response.md`.

## Consequences

- Chosen variant determines the phase structure for all subsequent work
- Phase breakdown becomes the migration backlog
- Testing strategy aligns to phase boundaries
- If Variant D-revised: Phase 1a walking skeleton is achievable in 1-2 days for a solo developer
- If Variant D-revised: sqlacodegen reduces Phase 1b model effort from days to hours (generation) + hours (review)
- If Variant D-revised: pluggy hook specs in Phase 1b create documented contracts for all 24 hooks before business logic is written
- If Variant D-revised: Feed engine (Phase 3c) is Celery-ready by design — Phase 5c is decorator-only integration
