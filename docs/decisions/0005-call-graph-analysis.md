# ADR-0005: Automated Call Graph Analysis

- **Status**: accepted
- **Date proposed**: 2026-04-03
- **Date accepted**: 2026-04-03
- **Deciders**: Project lead (adversarial review, unanimous convergence)

## Context

The migration dimensions analysis (`specs/10-migration-dimensions.md`) identified 6 analysis dimensions and proposed using NetworkX + Leiden community detection to validate and refine the manually-identified module boundaries.

This ADR decides whether to invest in building automated source code analysis tooling before starting migration, or proceed with the manual analysis already completed.

## Options

### A: Build Automated Analysis (NetworkX + Leiden)

Build Python scripts that:
1. Parse PHP source for `require`/`include`/`new`/`extends`/`implements`/function calls
2. Build directed call graph in NetworkX
3. Build entity graph from table references in SQL queries
4. Run Leiden community detection on both graphs
5. Compare detected communities with manual clusters from specs
6. Generate visual dependency diagrams

**Effort**: ~1-2 days
**Tools**: NetworkX, python-igraph, leidenalg, matplotlib/graphviz

### B: Proceed with Manual Analysis

The manual analysis in specs already identifies:
- 8 call graph communities
- 10 entity clusters
- 6 frontend-backend coupling levels
- Complexity hotspot ranking

Proceed directly to migration using these as guide.

### C: Lightweight Static Analysis Only

Use existing PHP static analysis tools:
- `phpstan` or `psalm` for type inference
- `dephpend` for dependency graphs
- Generate visual output without custom scripting

## Trade-off Analysis

| Criterion | A: Full NetworkX | B: Manual only | C: Lightweight PHP tools |
|-----------|-----------------|----------------|-------------------------|
| Accuracy | High (quantitative) | Medium (expert judgment) | Medium |
| Effort | 1-2 days | 0 | 0.5 days |
| Reusability | High (scripts reusable for validation) | None | Low |
| Visualization | Excellent | None | Good |
| Leiden clustering | Yes | No | No |
| Validates manual analysis | Yes | N/A | Partially |

## Preliminary Recommendation

**Option A** if time permits — the investment is small (1-2 days) and the quantitative validation of migration ordering could prevent costly mistakes. The scripts are also reusable for tracking migration progress (e.g., "which communities are fully migrated?").

**Option B** if time is tight — the manual analysis is solid enough to start.

## Decision

**Option B: Proceed with Manual Analysis** — the manual analysis in specs already identifies 8 call graph communities, 10 entity clusters, 6 frontend-backend coupling levels, and complexity hotspot ranking. Option A (NetworkX + Leiden, ~1-2 days) directly competes with the Phase 1a walking skeleton timeline (also 1-2 days). Option A may be revisited as a separate tooling initiative if the manual clusters prove insufficient during Phase 2+.

## Consequences

- If Option A: creates a reusable toolset for migration progress tracking
- If Option A: may reveal unexpected dependency clusters not caught manually
- If Option B: risk of discovering hidden dependencies mid-migration
- If Option C: partial validation without custom investment
