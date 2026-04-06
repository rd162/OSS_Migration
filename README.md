# TT-RSS PHP → Python Migration

This repository documents and delivers the full migration of [Tiny Tiny RSS](https://tt-rss.org/) from its original PHP codebase to a modern Python stack.

**Source:** `source-repos/ttrss-php/` — original PHP application  
**Target:** `target-repos/ttrss-python/` — migrated Python application  
**Status:** All 6 migration phases complete. Ready for production release.

## Repository layout

```
OSS_Migration/
├── source-repos/ttrss-php/        Original PHP source (read-only reference)
├── target-repos/ttrss-python/     Migrated Python application
├── specs/
│   ├── architecture/              14 reference specs — stable, read-only
│   └── 001–006/                   Phase specs (spec + plan + tasks per phase)
├── docs/
│   ├── decisions/                 Architecture Decision Records (ADR-0001–0019)
│   └── reports/                   Coverage and audit reports
├── tools/graph_analysis/          PHP call-graph builder + coverage validator
├── scripts/                       Data conversion utilities
├── constitution.md                Project principles and hard rules
└── AGENTS.md                      Agent/AI collaboration rules and conventions
```

## Migration phases

| Phase | Spec | Deliverable | Status |
|-------|------|-------------|--------|
| 1 — Foundation | [001-foundation](specs/001-foundation/) | Models, auth, DB, Alembic, app factory | **DONE** |
| 2 — Core logic | [002-core-logic](specs/002-core-logic/) | Feed parsing, counter cache, filters, labels, sanitise | **DONE** |
| 3 — Business logic | [003-business-logic](specs/003-business-logic/) | Prefs CRUD, digests, OPML, backend blueprint | **DONE** |
| 4 — API handlers | [004-api-handlers](specs/004-api-handlers/) | 17 API operations, 2-guard auth, getFeedTree BFS | **DONE** |
| 5 — Semantic verification | [005-semantic-verification](specs/005-semantic-verification/) | 14 hooks wired, 40-category taxonomy, 105+ fixes, 0 gaps | **DONE** |
| 6 — Deployment | [006-deployment](specs/006-deployment/) | CI, Docker, nginx, pgloader, ≥95% coverage gate, deploy.yml | **DONE** |

## Architecture reference specs

Stable, read-only specifications used across all phases:

| Spec | Topic |
|------|-------|
| [00-project-charter](specs/architecture/00-project-charter.md) | Goals, constraints, success criteria |
| [01-architecture](specs/architecture/01-architecture.md) | System architecture and component map |
| [02-database](specs/architecture/02-database.md) | Schema, ORM strategy, migration approach |
| [03-api-routing](specs/architecture/03-api-routing.md) | TT-RSS API protocol and routing |
| [04-frontend](specs/architecture/04-frontend.md) | Frontend strategy (resolved by ADR-0017) |
| [05-plugin-system](specs/architecture/05-plugin-system.md) | pluggy hook specs |
| [06-security](specs/architecture/06-security.md) | Auth, CSRF, session, encryption |
| [07-caching-performance](specs/architecture/07-caching-performance.md) | Redis caching, counter cache |
| [08-deployment](specs/architecture/08-deployment.md) | Docker, gunicorn, nginx, CI/CD |
| [09-source-index](specs/architecture/09-source-index.md) | PHP source file inventory |
| [10-migration-dimensions](specs/architecture/10-migration-dimensions.md) | What changes, what stays the same |
| [11-business-rules](specs/architecture/11-business-rules.md) | Preserved business rules catalogue |
| [12-testing-strategy](specs/architecture/12-testing-strategy.md) | Test pyramid and coverage gates |
| [13-decomposition-map](specs/architecture/13-decomposition-map.md) | PHP→Python module mapping |
| [14-semantic-discrepancies](specs/architecture/14-semantic-discrepancies.md) | Known behavioural differences |
| [15-sme-review](specs/architecture/15-sme-review.md) | SME demo review — functional inventory and gap list |

## Architecture Decision Records

| ADR | Decision | Status |
|-----|----------|--------|
| [0001](docs/decisions/0001-migration-flow-variant.md) | Migration flow: variant D-revised (schema-first) | accepted |
| [0002](docs/decisions/0002-python-framework.md) | Python framework: Flask | accepted |
| [0003](docs/decisions/0003-database-engine.md) | Database: PostgreSQL (MySQL dropped) | accepted |
| [0004](docs/decisions/0004-frontend-strategy.md) | Frontend strategy → resolved by ADR-0017 | accepted |
| [0005](docs/decisions/0005-call-graph-analysis.md) | PHP call-graph analysis tooling | accepted |
| [0006](docs/decisions/0006-orm-strategy.md) | ORM: SQLAlchemy 2 | accepted |
| [0007](docs/decisions/0007-session-management.md) | Session management: Flask-Login + Redis | accepted |
| [0008](docs/decisions/0008-password-migration.md) | Password migration: argon2id (bcrypt/MD5 upgrade path) | accepted |
| [0009](docs/decisions/0009-feed-credential-encryption.md) | Feed credential encryption: Fernet (replaces mcrypt) | accepted |
| [0010](docs/decisions/0010-plugin-system.md) | Plugin system: pluggy | accepted |
| [0011](docs/decisions/0011-background-worker.md) | Background worker: Celery (replaces pcntl_fork daemon) | accepted |
| [0012](docs/decisions/0012-logging-strategy.md) | Logging: structlog | proposed |
| [0013](docs/decisions/0013-i18n-approach.md) | i18n / localisation | proposed |
| [0014](docs/decisions/0014-feed-parsing-library.md) | Feed parsing: feedparser | accepted |
| [0015](docs/decisions/0015-http-client.md) | HTTP client: httpx | accepted |
| [0016](docs/decisions/0016-semantic-verification.md) | Semantic verification methodology | accepted |
| [0017](docs/decisions/0017-frontend-spa-vanilla-js.md) | Frontend: Vanilla JS SPA (replaces Dojo toolkit) | accepted |
| [0018](docs/decisions/0018-drag-drop-deferred.md) | Drag-drop category assignment deferred; dropdown used | accepted |
| [0019](docs/decisions/0019-preferences-modal-pattern.md) | Simplified tabbed preferences modal | accepted |

## Coverage validation

The `tools/graph_analysis/` toolchain builds a PHP call graph and validates that every in-scope PHP function has a Python counterpart.

```bash
# Build call graphs from PHP source (run once, or after PHP source changes)
python tools/graph_analysis/build_php_graphs.py

# Validate — must report 0 gaps
python tools/graph_analysis/validate_coverage.py \
  --graph-dir tools/graph_analysis/output \
  --python-dir target-repos/ttrss-python/ttrss \
  --min-coverage 0.95
```

Result as of Phase 6: **0 gaps, ≥95% coverage**.

## Key metrics (end of Phase 6)

| Metric | Value |
|--------|-------|
| Unit + integration tests | 598 passing |
| E2E browser tests (Playwright) | 67 / 68 passing |
| Coverage gaps | 0 |
| Plugin hooks wired | 14 / 14 |
| Semantic discrepancies fixed | 105+ |
| CI coverage gate | ≥ 95% (strict — no `continue-on-error`) |

## Release

Tag `v1.0.0` to trigger the deploy pipeline:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

The `.github/workflows/deploy.yml` workflow runs: pgloader migration, PHP-serialized conversion, and health-check verification.

## Governance

- [`constitution.md`](constitution.md) — project principles (P1 library-first, P2 test-first, P3 source traceability)
- [`AGENTS.md`](AGENTS.md) — AI agent collaboration rules and spec-kit conventions
