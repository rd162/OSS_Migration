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
| [0006](0006-orm-strategy.md) | ORM vs Raw SQL | proposed | P1 — blocks model layer implementation |
| [0007](0007-session-management.md) | Session Management Strategy | proposed | P1 — blocks auth implementation |
| [0008](0008-password-migration.md) | Password Hash Migration | proposed | P1 — blocks user migration |
| [0009](0009-feed-credential-encryption.md) | Feed Credential Encryption | proposed | P1 — blocks feed auth migration |
| [0010](0010-plugin-system.md) | Plugin System Implementation | proposed | P2 — blocks plugin migration |
| [0011](0011-background-worker.md) | Background Worker Architecture | proposed | P1 — blocks feed update daemon |
| [0012](0012-logging-strategy.md) | Logging Strategy | proposed | P2 — informs observability |
| [0013](0013-i18n-approach.md) | Internationalization Approach | proposed | P2 — blocks i18n migration |
| [0014](0014-feed-parsing-library.md) | Feed Parsing Library | proposed | P1 — blocks feed parser migration |
| [0015](0015-http-client.md) | HTTP Client for Feed Fetching | proposed | P1 — blocks feed fetcher migration |

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

0006 (ORM Strategy)
  ├── depends on: 0002 (framework), 0003 (DB engine)
  └── blocks: all model/query code

0007 (Session Management)
  ├── depends on: 0002 (framework)
  └── blocks: authentication, 0011 (shares Redis)

0008 (Password Migration)
  ├── depends on: 0006 (ORM for user model)
  └── blocks: user auth migration

0009 (Feed Credential Encryption)
  ├── depends on: 0006 (ORM for feed model)
  └── blocks: authenticated feed migration

0010 (Plugin System)
  ├── depends on: 0002 (framework)
  └── blocks: plugin migration (Phase 5+)

0011 (Background Worker)
  ├── depends on: 0002 (framework), 0007 (shares Redis)
  └── blocks: feed update daemon, housekeeping tasks

0012 (Logging)
  └── informs: all components (cross-cutting concern)

0013 (i18n)
  ├── depends on: 0002 (framework)
  └── blocks: UI string migration

0014 (Feed Parsing)
  └── blocks: feed update pipeline

0015 (HTTP Client)
  ├── depends on: 0011 (worker architecture)
  └── blocks: feed fetching implementation
```
