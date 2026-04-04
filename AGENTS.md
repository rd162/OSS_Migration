# AGENTS.md — PHP-to-Python Migration Project

## Mission

Migrate Tiny Tiny RSS (TT-RSS) from PHP to Python, fully preserving all specs, design, and behavior of the source project.

## Project Layout

```
OSS_Migration/
├── AGENTS.md              ← This file (project rules & conventions)
├── CLAUDE.md              ← Umbrella pointing here
├── specs/                 ← Spec-kit: charter, architecture, DB, API, etc.
│   ├── 00-project-charter.md  ← Mission, Goals, Premises, Constraints (governs all specs)
│   ├── 01-architecture.md
│   ├── 02-database.md
│   ├── 03-api-routing.md
│   ├── 04-frontend.md
│   ├── 05-plugin-system.md
│   ├── 06-security.md
│   ├── 07-caching-performance.md
│   ├── 08-deployment.md
│   ├── 09-source-index.md
│   ├── 10-migration-dimensions.md
│   ├── 11-business-rules.md
│   └── 12-testing-strategy.md
├── docs/decisions/        ← Architecture Decision Records (MADR convention)
│   ├── README.md          ← Decision index + dependency graph
│   ├── 0001-migration-flow-variant.md
│   ├── 0002-python-framework.md
│   ├── 0003-database-engine.md
│   ├── 0004-frontend-strategy.md
│   ├── 0005-call-graph-analysis.md
│   ├── 0006-orm-strategy.md
│   ├── 0007-session-management.md
│   ├── 0008-password-migration.md
│   ├── 0009-feed-credential-encryption.md
│   ├── 0010-plugin-system.md
│   ├── 0011-background-worker.md
│   ├── 0012-logging-strategy.md
│   ├── 0013-i18n-approach.md
│   ├── 0014-feed-parsing-library.md
│   └── 0015-http-client.md
├── memory/                ← Project memory (cross-session context)
├── rules/                 ← Supplementary rules if needed
├── source-repos/          ← READ-ONLY: PHP source (ttrss-php/)
│   └── ttrss-php/
└── target-repos/          ← Python migration target (grows here)
```

## Critical Rules

### Storage Rules
1. **NEVER** write files into `~/.claude/projects/*/memory/` — all memory goes to `./memory/`
2. **NEVER** modify anything inside `source-repos/` — it is read-only reference
3. **NEVER** store project specs, memory, or rules in `.claude/` — that dir is only for Claude-specific config (settings, skills)
4. All specs, memory, rules, and artifacts go in the **project root** under their respective directories
5. This ensures cross-platform portability (not tied to Claude's home directory)

### Migration Rules
6. Target Python code goes into `target-repos/` — this is where the migrated project grows
7. Every spec document in `specs/` must cross-reference source files by relative path (e.g., `source-repos/ttrss-php/ttrss/classes/db.php`) rather than duplicating source code
8. Specs may include **reasonable code examples** to highlight important architectural decisions, but must not be a copy of the source
9. When migrating, always verify behavior parity against the source spec before marking a component complete

### Source Traceability Rule (MANDATORY)
10. **Every meaningful code element** (function, class, method, model, route, constant) in `target-repos/` **MUST** have a traceability comment linking it to its PHP source origin. This is a hard constraint — code without traceability comments must not be committed.

    **Traceability comment format** (use the most specific match available):

    ```python
    # Source: ttrss/classes/feeds.php:Feeds::view (lines 45-120)
    def view_feed(feed_id: int, view_mode: str) -> dict:
        ...

    # Source: ttrss/include/functions.php:catchup_feed (lines 1094-1237)
    def catchup_feed(feed_id: int, cat_view: bool, ...) -> None:
        ...

    # Source: ttrss/classes/db.php:Db (singleton pattern)
    # Python equivalent: SQLAlchemy engine via Flask-SQLAlchemy extension
    db = SQLAlchemy(model_class=Base)

    # Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds, lines 38-72)
    class Feed(Base):
        __tablename__ = "ttrss_feeds"
        ...
    ```

    **Match levels** (use the most specific that applies):
    - **Direct**: `function → function` or `class → class` (e.g., `Feeds::view` → `view_feed()`)
    - **Method-level**: `Class::method` → Python method (e.g., `RPC::mark` → `rpc.mark_article()`)
    - **File-level**: When a Python module aggregates logic from a single PHP file (e.g., `# Source: ttrss/include/ccache.php`)
    - **Multi-file**: When a Python module synthesizes logic from multiple PHP files (e.g., `# Source: ttrss/include/functions.php + ttrss/include/functions2.php (query building)`)
    - **Schema-level**: For models derived from SQL schema (e.g., `# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_entries)`)
    - **Inferred**: When Python code has no direct PHP equivalent but was inferred from PHP patterns (e.g., `# Inferred from: ttrss/include/sessions.php (session validation pattern, adapted for Flask-Login)`)
    - **New**: When code is genuinely new with no PHP source (e.g., `# New: no PHP equivalent (Alembic migration infrastructure)`)

### Traceability Verification Rule (MANDATORY)
10a. **After generating or modifying target code**, run the traceability & correctness verification workflow defined in `rules/traceability-verification.md`. This is also required **between major phases** (e.g., Phase 1a→1b, 1b→2). The workflow uses adversarial self-refine with isolated CRITIC/AUTHOR agents to catch schema mismatches, missing traceability comments, phantom columns/defaults, and logic divergence from PHP source.

### Analysis Rules
10. Use deep web research for any complicated architectural topic (PHP patterns, 3-tier architecture, ORM vs transactional script, etc.)
11. For source code analysis dimensions (call graph, entity graph, etc.), consider using NetworkX and Leiden community detection
12. Migration flow is driven by dimensions documented in `specs/10-migration-dimensions.md` — discuss and choose flow before starting migration

### Quality Rules
13. Preserve all functional behavior from the PHP source
14. Fix known security issues during migration (SHA1→argon2id, prepared statements, etc.) — document deviations in specs
15. Maintain spec-to-code traceability throughout the migration

### Consistency Rule (MANDATORY)
16. **When any status, decision, or phase changes**, update ALL locations that reference it in the same commit. This is a hard constraint — partial status updates create contradictions that compound across sessions.

    **Mandatory update checklist** (run mentally before every status change):
    - [ ] `AGENTS.md` — Architecture Decisions table (status column)
    - [ ] `docs/decisions/README.md` — Decision Index table (status + priority columns)
    - [ ] `docs/decisions/XXXX-*.md` — the ADR itself (Status, Date accepted, Deciders, Decision section)
    - [ ] `specs/00-project-charter.md` — Solution Space table (decision + status columns)
    - [ ] `specs/00-project-charter.md` — Requirements Traceability Matrix (status column)
    - [ ] `specs/00-project-charter.md` — Cross-Reference table (if new ADR linkages discovered)
    - [ ] `specs/10-migration-dimensions.md` — Recommendation Matrix (if flow variant affected)
    - [ ] `memory/session_*.md` — session memory (current state for next session)

    **Applies to**: ADR acceptance/rejection, phase completion, security finding remediation, requirement status changes, any table row that tracks status or decisions.

## Spec-Kit Index

| Spec | Contents |
|------|----------|
| `00-project-charter.md` | **Project Charter**: Mission, Goals, Premises, Constraints, Solution Space, traceability matrix |
| `01-architecture.md` | Application layers, design patterns, request lifecycle, class hierarchy |
| `02-database.md` | 35 tables, FK map, migration system, seed data, schema patterns |
| `03-api-routing.md` | Entry points, handler dispatch, RPC endpoints, request/response contracts |
| `04-frontend.md` | JS files, AJAX patterns, Dojo/Prototype widgets, server-rendered HTML |
| `05-plugin-system.md` | 24 hooks, plugin lifecycle, storage, system vs user plugins |
| `06-security.md` | 10 findings by severity, auth flow, session management, encryption |
| `07-caching-performance.md` | Counter cache, file cache, HTTP caching, daemon architecture |
| `08-deployment.md` | Docker, Nginx/PHP-FPM, CI/CD, environment config |
| `09-source-index.md` | Complete file inventory with purpose annotations and cross-references |
| `10-migration-dimensions.md` | Call graph, entity graph, frontend/backend dimensions, migration flow variants |
| `11-business-rules.md` | 20 business rules with exact line refs, edge cases, search, digest, OPML, registration |
| `12-testing-strategy.md` | Parity verification, 5 test categories, fixtures, test matrix for top 20 endpoints |

## Architecture Decisions (docs/decisions/)

| ADR | Title | Status |
|-----|-------|--------|
| 0001 | Migration Flow Variant | **accepted** — P0, Variant D-revised |
| 0002 | Python Web Framework | **accepted** — P0, Flask |
| 0003 | Database Engine Choice | **accepted** — P0, PostgreSQL + psycopg2 |
| 0004 | Frontend Migration Strategy | proposed — P1, Tier 3 (Phase 2 exit) |
| 0005 | Automated Call Graph Analysis | **accepted** — P1, Option B (manual) |
| 0006 | ORM vs Raw SQL | **accepted** — P1, SQLAlchemy ORM (hybrid Core) |
| 0007 | Session Management | **accepted** — P1, Flask-Login + Redis |
| 0008 | Password Hash Migration | **accepted** — P1, Dual-hash gradual (argon2id) |
| 0009 | Feed Credential Encryption | **accepted** — P1, Fernet |
| 0010 | Plugin System Implementation | **accepted** — P2, pluggy + importlib directory discovery |
| 0011 | Background Worker Architecture | **accepted** — P1, Celery + Redis (two-task fan-out) |
| 0012 | Logging Strategy | proposed — P2 |
| 0013 | i18n Approach | proposed — P2 |
| 0014 | Feed Parsing Library | **accepted** — P1, feedparser + lxml sanitization |
| 0015 | HTTP Client | **accepted** — P1, httpx async in Celery workers only |

See `docs/decisions/README.md` for decision dependencies. ADR format follows [MADR](https://adr.github.io/madr/) convention.

## Recommended Skills

Skills that should be installed in `.claude/skills/` for this project:

- **inferring-requirements** — requirements discovery before each migration phase
- **deep-research-t1** — research Python equivalents for PHP patterns
- **document-ingestion** — if external specs/docs need processing
- **continuation-and-handoff** — multi-session migration continuity
- **adversarial-self-refine** — iterative quality improvement of migrated code
- **selecting-pe-methods** — choose optimal reasoning strategy per migration task
