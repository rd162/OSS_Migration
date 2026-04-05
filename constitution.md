# Constitution — TT-RSS PHP-to-Python Migration

**Version:** 1.0  
**Ratified:** 2026-04-04  
**Ratifiers:** Project Charter (specs/architecture/00-project-charter.md), AGENTS.md  
**Supersedes:** All informal conventions established before this document.

---

## 1. Core Principles

These principles are ordered by priority. When principles conflict, the higher-ranked principle wins.

### P1 — Library-First: Service Module Architecture

Every migrated function belongs in a named service module, not a monolithic god-file.

- PHP `functions.php` / `functions2.php` (3000+ line monoliths) are decomposed by domain: `feeds/ops.py`, `articles/ops.py`, `auth/authenticate.py`, etc.
- No Python module may exceed ~500 lines without domain-justified decomposition.
- Singletons (`Db`, `PluginHost`) are replaced with Flask extensions and dependency injection.

### P2 — Test-First: Coverage is a Gate, Not a Metric

No migration phase is complete without passing its test gate.

- Minimum coverage: **>80% per module** (`pytest --cov-fail-under=80`).
- 598+ unit tests must pass before any phase is marked DONE.
- Zero coverage validator gaps: `tools/graph_analysis/validate_coverage.py` must report 0 unmatched in-scope functions.
- Contract tests for every API endpoint are required before Phase 4 is closed.

### P3 — Source Traceability: Every Element Has a PHP Ancestor

Every meaningful code element in `target-repos/` must be traceable to its PHP source.

- **Direct:** `# Source: ttrss/include/functions.php:authenticate_user (lines 706-771)`
- **Schema:** `# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds)`
- **Inferred:** `# Inferred from: ttrss/include/sessions.php (session validation pattern)`
- **New:** `# New: no PHP equivalent (Alembic migration infrastructure)`
- Code without a traceability comment must not be committed (AGENTS.md Rule 10, hard constraint).

### P4 — Security-by-Default: Improve, Never Regress

Migration is an opportunity to fix known vulnerabilities; regressions are forbidden.

- SHA1 passwords → argon2id (dual-hash gradual upgrade on login, ADR-0008).
- All DB queries via SQLAlchemy ORM/Core — no raw SQL string concatenation (ADR-0006).
- Fernet symmetric encryption for feed credentials with key rotation (ADR-0009).
- Flask-Talisman (security headers) + Flask-WTF (CSRF) active from Phase 1a.
- SSL verification enforced for all outbound HTTP (httpx, ADR-0015).
- No secrets in repository — all config via environment variables (C5).

### P5 — Behavioral Parity: Same Input, Same Output

The Python application must produce identical outputs to the PHP application for all inputs.

- All 35 DB tables (31 active) modeled identically in SQLAlchemy (ADR-0006).
- All 24 plugin hooks preserved via pluggy with identical hook IDs (ADR-0010).
- All RPC endpoints return identical JSON structures (G2).
- Gold-plating during migration is forbidden — improvements come after the migration is complete (C3).
- Dead PHP code (e.g., MySQL branches, TTL in `ccache_find`, `expire_lock_files`) is eliminated, not ported.

---

## 2. PHP Source Law

These rules govern the relationship with the PHP source code. They are hard constraints — violation triggers immediate correction, not a penalty.

### Law 1 — Source Repos Are Read-Only (C1)

`source-repos/` must never be modified. It is a reference, not a working directory. Any commit that touches `source-repos/` is rejected.

### Law 2 — Every Function Has a Source Comment (C7, Rule 10)

Every function, class, method, model, and route in `target-repos/` must carry a traceability comment before it is committed. The comment must use one of the six recognized match levels (Direct, Method-level, File-level, Multi-file, Schema-level, Inferred, New).

### Law 3 — Graph Analysis Governs Migration Order

Migration order is determined by topological levels in the PHP call graph, not by human intuition. The dependency dimensions are: call, class, db_table, hook, include.

- `tools/graph_analysis/build_php_graphs.py` — authoritative 5-dimension graph builder.
- `tools/graph_analysis/validate_coverage.py` — Python↔PHP coverage validator.
- Every phase gate requires the coverage validator to report 0 unmatched for in-scope modules.

### Law 4 — PostgreSQL Only (ADR-0003)

MySQL compatibility branches in PHP source are eliminated, never ported. This includes `DB_TYPE` checks, `DATE_SUB`, and MySQL `REGEXP` syntax. PostgreSQL equivalents (`NOW() - INTERVAL`, `~` regex) are used throughout.

### Law 5 — No HTML from Python Business Logic (R13)

PHP server-rendered HTML functions (`print_feed_cat_select`, `print_feed_select`, etc.) are eliminated. Python business logic returns dicts/lists; rendering is handled by Jinja2 templates or the existing JS frontend.

---

## 3. Quality Gates

These gates must pass before any phase is marked DONE. Gates compound: Phase N's gate includes all Phase N-1 gates.

| Gate | Criterion | Tool |
|------|-----------|------|
| QG-1 | `pytest --cov-fail-under=80` green per module | pytest-cov |
| QG-2 | 0 coverage validator gaps for in-scope modules | `validate_coverage.py` |
| QG-3 | 598+ unit tests passing (global) | pytest |
| QG-4 | 0 `# Source:` comment violations (grep check) | traceability-verification.md |
| QG-5 | 0 MySQL branches (grep `DB_TYPE`, `DATE_SUB` = 0) | grep |
| QG-6 | 0 circular imports (`python -c` import check for all modules) | python |
| QG-7 | Rule 10a adversarial self-refine cycle passed for each batch | AGENTS.md Rule 10a |

### Phase-Specific Gates

- **Phase 1 exit:** 31/31 models mapped, 24/24 hookspecs detected, Alembic baseline runs.
- **Phase 2 exit:** 15 criteria — see `specs/002-core-logic/spec.md`.
- **Phase 3 exit:** 18 criteria — see `specs/003-business-logic/spec.md`.
- **Phase 5b exit:** 100% exact function coverage, 598 tests pass.
- **Phase 6 exit:** `validate_coverage.py` ≥95% (L0-L10 functions, matched + eliminated).

---

## 4. Architecture Decisions

Sixteen ADRs narrow the solution space. All P0 ADRs are binding immediately; P1+ ADRs are binding from their phase.

| ADR | Decision | Priority | Status |
|-----|----------|----------|--------|
| 0001 | Migration flow: Variant D-revised (Walking Skeleton + Hybrid Entity-then-Graph) | P0 | accepted |
| 0002 | Web framework: Flask | P0 | accepted |
| 0003 | Database engine: PostgreSQL only (psycopg2 sync) | P0 | accepted |
| 0016 | Semantic verification: 40-category taxonomy, 8 integration pipelines | P0 | accepted |
| 0006 | ORM: SQLAlchemy ORM (hybrid Core for complex queries) | P1 | accepted |
| 0007 | Session management: Flask-Login + Redis | P1 | accepted |
| 0008 | Password migration: argon2id dual-hash gradual | P1 | accepted |
| 0009 | Feed credential encryption: Fernet + MultiFernet key rotation | P1 | accepted |
| 0011 | Background worker: Celery + Redis (two-task fan-out) | P1 | accepted |
| 0014 | Feed parsing: feedparser + lxml sanitization | P1 | accepted |
| 0015 | HTTP client: httpx async in Celery workers only | P1 | accepted |
| 0005 | Call graph: manual analysis (8 communities, 10 clusters) | P1 | accepted |
| 0010 | Plugin system: pluggy + importlib directory discovery | P2 | accepted |
| 0004 | Frontend: keep existing JS, serve from Flask | P1 | proposed |
| 0012 | Logging: structlog | P2 | proposed |
| 0013 | i18n: Python gettext with existing .po/.mo files | P2 | proposed |

Full rationale for each ADR is in `docs/decisions/`.

---

## 5. Anti-Patterns (Forbidden)

| Anti-Pattern | Consequence | Mitigation |
|-------------|-------------|------------|
| Raw SQL string concatenation | SQL injection | SQLAlchemy ORM/Core only (ADR-0006) |
| `$_SESSION` global access pattern | Untestable coupling | Flask `g` / Flask-Login `current_user` |
| Dual-DB SQL branches (MySQL + PostgreSQL) | Dead code | PostgreSQL only (ADR-0003) |
| Missing `htmlspecialchars()` equivalents | XSS | Jinja2 autoescape (on by default) |
| God-file modules (functions.php pattern) | Untestable | Split by domain (P1 principle) |
| Singleton `Db` / `PluginHost` pattern | Hidden global state | Flask extensions + DI (ADR-0010) |
| Gold-plating during migration | Breaks behavioral parity | Strict parity constraint (C3) |
| N+1 query patterns in counters/ccache | Performance regression | Bulk GROUP BY queries |
| Circular imports | ImportError at runtime | Module boundary discipline |
| Server-rendered HTML from business logic | Dead code | Return dicts; render in templates |

---

## 6. Directory Routing Rule

> *"Is this work still in progress, or is it a settled record?"*

- **In progress / active** → `memory/` (plans, current phase, blockers)
- **Settled decision** → `docs/decisions/` as ADR (MADR 4.0 format)
- **Stable spec** → `specs/`
- **Completed report** → `docs/`
- **Target Python code** → `target-repos/`
- **PHP source reference** → `source-repos/` (read-only, never modify)
