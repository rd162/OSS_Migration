# ADR-0001: Migration Flow Variant

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD
- **Depends on**: ADR-0002, ADR-0003

## Context

The PHP→Python migration requires a structured approach for ordering work across ~18,600 lines of application PHP code, 35 database tables, and 11 JavaScript files. Five flow variants were analyzed in `specs/10-migration-dimensions.md`, each driving migration by a different dimension.

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

### D: Hybrid Entity-then-Graph (Recommended)
Phase 1: All SQLAlchemy models + app skeleton.
Phase 2: Core logic in call-graph order (auth → prefs → utilities).
Phase 3: Business logic by entity cluster (feeds → articles → labels → filters).
Phase 4: Handlers preserving frontend contract.
Phase 5: Cross-cutting (plugins, API, worker).
Phase 6: Deployment.
*Balanced: solid foundation, natural ordering, each phase testable.*

### E: Granular Multi-Pass
11 fine-grained passes (models → access → auth → config → parsing → engine → handlers → API → plugins → frontend → deploy).
*Maximum granularity but high coordination overhead.*

## Preliminary Recommendation

**Variant D** — balances foundation quality, testability per phase, and pragmatic ordering for solo/small-team work.

## Decision

**TBD** — to be discussed and accepted before migration begins.

## Consequences

- Chosen variant determines the phase structure for all subsequent work
- Phase breakdown becomes the migration backlog
- Testing strategy aligns to phase boundaries
- If Variant D: Phase 1 (models) is large (~35 models) but parallelizable
