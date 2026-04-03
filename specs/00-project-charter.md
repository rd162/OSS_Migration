# 00 — Project Charter

Mission, Goals, Premises, Constraints, and Traceability for the TT-RSS PHP-to-Python migration.

## Requirements Discovery

Bottom-up analysis of the TT-RSS PHP codebase was performed across ten dimensions: architecture (spec 01), database schema (02), API/routing (03), frontend (04), plugin system (05), security (06), caching/performance (07), deployment (08), source inventory (09), and migration dimensions (10). Business rules were extracted in spec 11 and the testing strategy defined in spec 12. Findings from all twelve specs feed directly into the goals, premises, and constraints below.

---

## Mission Derivation

Migrating TT-RSS from PHP to Python serves a terminal value: **reliable, secure, maintainable software that serves its users**. Python is the vehicle for achieving improved maintainability, security posture, and developer productivity — not an end in itself.

---

## Charter Specification (Mission, Goals, Premises, Constraints)

### M — Mission

**Deliver a reliable, secure, and maintainable RSS aggregation platform by migrating TT-RSS from PHP to Python, preserving all functional behavior while improving the technology foundation.**

### G — Goals

| ID | Goal | Litmus Test (changing it changes solution type) |
|----|------|------------------------------------------------|
| G1 | **Complete functional migration** — all TT-RSS features work identically in Python | If removed → no migration needed |
| G2 | **Preserve API contract** — existing REST API and frontend-backend JSON contract unchanged | If removed → can break clients, different project |
| G3 | **Preserve database schema** — existing data remains accessible without data migration (or with automated migration) | If removed → greenfield rewrite, not migration |
| G4 | **Modernize security** — fix known vulnerabilities (SHA1, no prepared statements, SSL, etc.) | If removed → just a port, not an improvement |
| G5 | **Containerized deployment** — Docker-based, CI/CD-ready | If removed → manual deployment, different ops model |
| G6 | **Plugin system parity** — plugin architecture preserved with equivalent hook system | If removed → no extensibility, different product |

### P — Premises (assumptions that must hold)

| ID | Premise | If false → consequence |
|----|---------|----------------------|
| P1 | **Python ecosystem has adequate RSS parsing libraries** (feedparser, lxml) | Goal G1 impossible — need custom parser |
| P2 | **SQLAlchemy can model the existing 35-table schema** | Goal G3 impossible — need different ORM or raw SQL |
| P3 | **Existing frontend JS can work with any backend that returns identical JSON** | Goal G2 impossible — frontend tightly coupled to PHP |
| P4 | **Team has Python web development competence** | All goals delayed — need training first |
| P5 | **Source code is complete and representative** (no hidden dependencies outside repo) | Goal G1 at risk — missing behavior |
| P6 | **The application's transactional script pattern can be preserved or improved in Python** | Goal G1 requires significant redesign |
| P7 | **Background feed updates can be handled by Celery or equivalent** | Goal G1 (daemon) at risk |
| P8 | **Existing .po/.mo locale files are compatible with Python gettext** | i18n breaks — need conversion |

### C — Constraints

#### Hard Constraints (violation = rejection)

| ID | Constraint | Source |
|----|-----------|--------|
| C1 | **Never modify source-repos/** — read-only reference | Project rule (AGENTS.md) |
| C2 | **All migrated code in target-repos/** | Project rule (AGENTS.md) |
| C3 | **Behavioral parity** — same input → same output for all endpoints | Migration definition |
| C4 | **Database compatibility** — must work with existing data (or provide automated migration) | Data preservation requirement |
| C5 | **No secrets in repo** — config via environment variables | Security best practice |
| C6 | **Spec traceability** — every migration phase references specs/ documents | Project rule (AGENTS.md) |

#### Soft Constraints (violation = penalty, not rejection)

| ID | Constraint | Penalty if violated |
|----|-----------|-------------------|
| C7 | **Prefer single database engine** (not dual MySQL+PostgreSQL) | Extra testing, complexity |
| C8 | **Prefer established libraries** over custom implementations | Maintenance burden |
| C9 | **Preserve plugin hook IDs and names** for documentation continuity | Minor confusion |
| C10 | **Keep deployment simple** (single docker-compose up) | Ops complexity |
| C11 | **Incremental migration** (avoid big-bang rewrite) | Risk of partial failure |
| C12 | **Test coverage >= 80%** for migrated code | Quality risk |

---

## Solution Space (narrowed by 15 ADRs)

The solution space was narrowed from broad options to concrete decisions via ADRs 0001-0015:

> **Note:** These are preliminary recommendations from ADR analysis. Final decisions pending acceptance.

| Dimension | Preliminary Recommendation | ADR |
|-----------|----------|-----|
| Migration flow | Granular hybrid (entity-first + vertical slice) | ADR-0001 |
| Web framework | Flask | ADR-0002 |
| Database engine | PostgreSQL only | ADR-0003 |
| Frontend strategy | Keep existing JS, serve from Flask | ADR-0004 |
| Call graph analysis | Automated extraction with NetworkX | ADR-0005 |
| ORM strategy | SQLAlchemy declarative models | ADR-0006 |
| Session management | Flask-Login + server-side sessions | ADR-0007 |
| Password migration | Transparent SHA1-to-bcrypt upgrade on login | ADR-0008 |
| Feed credential encryption | Fernet symmetric encryption | ADR-0009 |
| Plugin system | Entry-point based with hook registry | ADR-0010 |
| Background worker | Celery with Redis broker | ADR-0011 |
| Logging | Python stdlib logging + structured JSON | ADR-0012 |
| i18n | Python gettext with existing .po/.mo files | ADR-0013 |
| Feed parsing | feedparser library | ADR-0014 |
| HTTP client | httpx (async-capable) | ADR-0015 |

---

## Anti-Patterns to Avoid

These are specific to patterns found in the TT-RSS PHP source:

| Anti-Pattern | Why Dangerous | Mitigation |
|-------------|---------------|------------|
| Replicate `db_fetch_assoc` iteration pattern | Verbose, error-prone manual row iteration | Use SQLAlchemy result sets and ORM queries directly (ADR-0006) |
| Replicate `$_SESSION` global access pattern | Untestable, hidden coupling | Use dependency injection or Flask `g` / Flask-Login `current_user` (ADR-0007) |
| Replicate dual-DB SQL branches (MySQL + PostgreSQL) | Double testing burden, divergent behavior | PostgreSQL only (ADR-0003) |
| Replicate `htmlspecialchars()` calls | Easy to miss, leads to XSS | Use Jinja2 autoescape (on by default) |
| Replicate `functions.php` / `functions2.php` monolith | 3000+ line god-files, impossible to test | Split by domain: `feeds.py`, `articles.py`, `users.py`, etc. |
| Replicate singleton pattern for `Db` / `PluginHost` | Hidden global state, blocks testing | Use Flask extensions and dependency injection (ADR-0010) |
| Gold-plating during migration | Adding features breaks behavioral parity | Strict parity constraint (C3); improvements come after migration |
| Frontend rewrite during backend migration | Two moving targets, compounding risk | Keep existing JS in Phase 1 (ADR-0004) |

---

## Cross-Reference to Specs and ADRs

| Charter Element | Primary Spec | Related ADRs |
|-------------|-------------|-------------|
| G1 (functional migration) | 01-architecture, 09-source-index, 11-business-rules | ADR-0001, ADR-0005 |
| G2 (API contract) | 03-api-routing | ADR-0004 |
| G3 (database schema) | 02-database | ADR-0003, ADR-0006 |
| G4 (security) | 06-security | ADR-0008, ADR-0009 |
| G5 (deployment) | 08-deployment | ADR-0011, ADR-0012 |
| G6 (plugin system) | 05-plugin-system | ADR-0010 |
| P1 (RSS parsing) | 07-caching-performance | ADR-0014 |
| P2 (ORM modeling) | 02-database | ADR-0006 |
| P7 (background worker) | 07-caching-performance | ADR-0011 |
| P8 (i18n) | 08-deployment | ADR-0013 |
| C1-C6 (hard constraints) | AGENTS.md | — |
| C7 (single DB engine) | 02-database | ADR-0003 |
| Solution Space | 10-migration-dimensions | ADR-0001 through ADR-0015 |
| Testing strategy | 12-testing-strategy | ADR-0001, ADR-0005 |

---

## Requirements Traceability Matrix

| Requirement | Source | Goal | Constraint | Spec | Status |
|------------|--------|------|-----------|------|--------|
| All 35 DB tables modeled in Python | P2, G3 | G3 | C4 | 02-database | Not started |
| All RPC endpoints preserved | G2 | G2 | C3 | 03-api-routing | Not started |
| REST API backward compatible | G2 | G2 | C3 | 03-api-routing | Not started |
| Feed update daemon equivalent | G1, P7 | G1 | — | 07-caching-performance | Not started |
| 24 plugin hooks preserved | G6 | G6 | C9 | 05-plugin-system | Not started |
| SHA1-to-bcrypt password migration | G4 | G4 | — | 06-security | Not started |
| Prepared statements (no SQL injection) | G4 | G4 | — | 06-security | Not started |
| SSL verification for feed fetching | G4 | G4 | — | 06-security | Not started |
| Feed credential encryption (Fernet) | G4 | G4 | — | 06-security | Not started |
| Docker deployment | G5 | G5 | C10 | 08-deployment | Not started |
| CI/CD pipeline | G5 | G5 | — | 08-deployment | Not started |
| i18n (18+ locales via gettext) | G1, P8 | G1 | — | 08-deployment | Not started |
| Counter cache system | G1 | G1 | — | 07-caching-performance | Not started |
| Session management (Flask-Login) | G1 | G1 | — | 06-security | Not started |
| Frontend serves unchanged | G2, P3 | G2 | — | 04-frontend | Not started |
| Article scoring rules preserved | G1 | G1 | C3 | 11-business-rules | Not started |
| Feed update interval logic preserved | G1 | G1 | C3 | 11-business-rules | Not started |
| Label/filter business rules preserved | G1 | G1 | C3 | 11-business-rules | Not started |
| OPML import/export parity | G1 | G1 | C3 | 11-business-rules | Not started |
| User preference system preserved | G1 | G1 | C3 | 11-business-rules | Not started |
| Test coverage >= 80% | — | — | C12 | 12-testing-strategy | Not started |
| Contract tests for all API endpoints | G2 | G2 | C3 | 12-testing-strategy | Not started |
