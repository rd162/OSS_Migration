# Architecture Decision Log

This directory contains Architecture Decision Records (ADRs) following [MADR](https://adr.github.io/madr/) conventions.

## Format

Each ADR follows the standard template:
- **Status**: `proposed` → `accepted` / `rejected` / `superseded`
- **Context**: Why this decision is needed
- **Decision**: What was decided
- **Consequences**: What follows from the decision

## Decision Index

| ADR | Title | Status | Priority |
|-----|-------|--------|----------|
| [0001](0001-migration-flow-variant.md) | Migration Flow Variant | proposed | P0 — blocks all migration work |
| [0002](0002-python-framework.md) | Python Web Framework | proposed | P0 — blocks project skeleton |
| [0003](0003-database-engine.md) | Database Engine Choice | proposed | P0 — blocks model layer |
| [0004](0004-frontend-strategy.md) | Frontend Migration Strategy | proposed | P1 — blocks UI work |
| [0005](0005-call-graph-analysis.md) | Automated Call Graph Analysis | proposed | P1 — informs migration ordering |

## Decision Dependencies

```
0001 (Flow Variant)
  ├── depends on: 0002, 0003 (framework + DB inform flow)
  └── blocks: all migration phases

0002 (Framework) + 0003 (DB)
  └── block: 0001 final decision, project skeleton creation

0004 (Frontend)
  └── blocks: Phase 4+ (handler migration)

0005 (Call Graph)
  └── informs: 0001 (validates community detection)
```
