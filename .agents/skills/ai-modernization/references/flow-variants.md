# Modernization Flow Variants

Five standard strategies for ordering modernization work. Select based on project characteristics
and document the choice as an ADR.

## Variant A: Entity-First (Bottom-Up)

Models/schemas first, then data access, then business logic, then handlers/UI.

```
Pass 1: Data models / schemas / type definitions
Pass 2: Database access layer (repository pattern or direct ORM)
Pass 3: Core utilities (config, auth, session, preferences)
Pass 4: Business logic (processing engines, algorithms, rules)
Pass 5: API/UI handlers
Pass 6: Extension/plugin system
Pass 7: Frontend adaptation
Pass 8: Deployment
```

**Best for**: Database-heavy applications, systems where the data model is stable and well-defined.
**Risk**: Long time before any runnable code. Models may need revision when business logic reveals patterns.
**Example**: A SQL-trigger-based ETL system where the data model IS the application.

## Variant B: Call-Graph-First (Top-Down)

Entry points and routing first, then handlers with stubs, then fill in business logic.

```
Pass 1: Entry points + bootstrap (app factory, config, routing)
Pass 2: Handler base classes + dispatch logic
Pass 3: Core handlers with stub dependencies
Pass 4: Database layer (replace stubs with real implementation)
Pass 5: Business logic engines
Pass 6: Preference/settings handlers
Pass 7: Extension system
Pass 8: Polish + deployment
```

**Best for**: API-heavy systems, microservices, systems with well-defined entry points.
**Risk**: Stub management overhead. May need to refactor handlers when stubs are replaced.
**Example**: A REST API service where contract preservation is the primary concern.

## Variant C: Vertical Slice (Feature-First)

Complete end-to-end slices: one feature at a time, including its model, logic, API, and UI.

```
Slice 1: Authentication + user management (model + logic + endpoints + UI)
Slice 2: Primary feature A (full stack)
Slice 3: Primary feature B (full stack)
...
Slice N: Extension/plugin system
Slice N+1: Deployment
```

**Best for**: Team-based modernizations with parallel workstreams. Each slice is independently testable.
**Risk**: Cross-cutting concerns (auth, config, sessions) must be established early or duplicated.
**Example**: A large e-commerce platform where different teams own different product areas.

## Variant D: Hybrid Walking Skeleton

Walking skeleton first (minimal runnable app), then complete foundation, then business logic
ordered by call graph, then handlers, then cross-cutting concerns.

```
Phase 1a: Walking skeleton — minimal runnable app + core models + basic auth + dev environment
Phase 1b: Complete foundation — all models, schema migrations, extension hookspecs
Phase 2:  Core logic — auth, preferences, utilities (call graph levels L0-L5)
Phase 3:  Business logic — by entity cluster (call graph levels L0-L10)
Phase 4:  API/UI handlers — preserving frontend contract
Phase 5:  Cross-cutting — plugins, external API, background jobs, logging
Phase 6:  Deployment — production config, CI/CD, data migration
```

**Best for**: Solo developer or small team. Applications with clear layered architecture.
**Key advantage**: Walking skeleton delivers a runnable app in days, not weeks. This dramatically
reduces risk and provides a testbed for all subsequent phases.
**Risk**: More planning overhead, but this is mitigated by the detailed phase plan.
**Example**: A monolithic web application being rewritten in a new language/framework.

## Variant E: Granular Multi-Pass

Multiple fine-grained passes, each addressing one dimension exclusively.

```
Pass 1:  Data models / type definitions only
Pass 2:  Database access layer only
Pass 3:  Authentication only
Pass 4:  Configuration only
Pass 5:  Content parsing only
Pass 6:  Processing engine only
Pass 7:  Request handlers only
Pass 8:  External API only
Pass 9:  Extension system only
Pass 10: Frontend only
Pass 11: Deployment only
```

**Best for**: Large teams with specialists per dimension. Maximum granularity.
**Risk**: Excessive coordination overhead for small teams. Each pass may need its own mini-skeleton.
**Example**: A large platform modernization with dedicated teams for DB, API, frontend, and DevOps.

## Decision Matrix

| Factor | A (Entity) | B (Call-Graph) | C (Slice) | D (Skeleton) | E (Multi-Pass) |
|--------|-----------|---------------|-----------|-------------|----------------|
| Solo dev | Poor | OK | Poor | Best | Poor |
| Large team | OK | OK | Best | OK | Best |
| Stable data model | Best | OK | OK | Good | Good |
| External API consumers | OK | Best | OK | Good | OK |
| Time-to-market pressure | Poor | Good | OK | Best | Poor |
| Maximum thoroughness | Good | OK | OK | Good | Best |
| Legacy system (no tests) | OK | OK | OK | Best | OK |
