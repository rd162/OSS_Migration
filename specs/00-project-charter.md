# 00 — Project Charter

Mission, Goals, Premises (Assumptions That Must Hold), and Constraints for the TT-RSS PHP→Python migration.

## Phase 0: Bottom-Up Requirements Saturation

### CoK Triple Expansion

**L5 — Topics** (explicit and implied):
```
Explicit:  PHP-to-Python migration, TT-RSS, RSS aggregator, behavioral preservation
Implied:   web framework selection, ORM mapping, feed parsing, authentication,
           plugin architecture, background processing, database migration,
           deployment modernization, security hardening, API compatibility,
           frontend adaptation, i18n preservation, testing strategy
```

**L4 — Areas** (solution patterns):
```
(PHP migration, belongs_to, language_migration)
(language_migration, has_pattern, {strangler_fig, big_bang, parallel_run, incremental_rewrite})
(RSS aggregator, belongs_to, content_aggregation)
(content_aggregation, has_pattern, {feed_polling, push_notification, pub_sub})
(behavioral_preservation, belongs_to, system_equivalence)
(system_equivalence, has_pattern, {contract_testing, shadow_traffic, regression_suite})
```

**L3 — Fields** (delivery mechanisms):
```
(language_migration, implements_via, {web_frameworks, ORMs, task_queues, containerization})
(content_aggregation, implements_via, {HTTP_clients, XML_parsers, scheduling_engines})
(system_equivalence, implements_via, {integration_tests, API_contract_tests, diff_testing})
```

**L2 — Disciplines** (cross-cutting concerns):
```
(web_frameworks, grounded_in, software_engineering)
(software_engineering, mandates, {security, testing, observability, documentation})
(ORMs, grounded_in, data_engineering)
(data_engineering, mandates, {schema_integrity, migration_safety, backup_strategy})
(containerization, grounded_in, devops)
(devops, mandates, {CI_CD, reproducibility, environment_parity})
```

**L1 — Domains**:
```
(software_engineering, part_of, technology) ✓
(data_engineering, part_of, technology) ✓
(devops, part_of, technology) ✓
Disjoint from: arts, humanities, natural_sciences ✓
```

### Saturation Output

```
L5 → {PHP migration, Python, TT-RSS, RSS, feed parsing, auth, plugins, daemon,
       DB migration, deploy, security, API, frontend, i18n, testing}
L4 → [language_migration]+{strangler_fig, incremental_rewrite}
      [content_aggregation]+{feed_polling, pub_sub}
      [system_equivalence]+{contract_testing, regression_suite}
L3 → [web_frameworks]+{Flask, FastAPI, Django}
      [ORMs]+{SQLAlchemy, Alembic}
      [task_queues]+{Celery, asyncio}
      [containerization]+{Docker, docker-compose}
L2 → [software_engineering]+{security, testing, observability}
      [data_engineering]+{schema_integrity, migration_safety}
      [devops]+{CI_CD, reproducibility}
L1 → [technology] ✓

Requirements:
  L4: behavioral preservation via contract testing, incremental migration strategy
  L3: framework + ORM + task queue + container decisions
  L2: security hardening mandatory, CI/CD mandatory, testing mandatory
Solution Space: {Flask+SQLAlchemy+Celery, FastAPI+SQLAlchemy+ARQ, Django+DjangoORM+Celery}
```

---

## Phase 1: Top-Down Intent Inference

### "Why?" Recursion (W-Functor)

```
"Migrate TT-RSS from PHP to Python"
→ why? "To modernize the technology stack"
→ why? "To improve maintainability, security, and developer productivity"
→ why? "To ensure long-term viability and reduce operational risk"
→ why? "To deliver reliable, secure software that serves its users"
→ why? "Reliable, secure software is intrinsically valuable"
         ← tautology = Mission
```

---

## Charter Specification (Mission, Goals, Premises, Constraints)

### M — Mission

**Deliver a reliable, secure, and maintainable RSS aggregation platform by migrating TT-RSS from PHP to Python, preserving all functional behavior while improving the technology foundation.**

The mission is NOT "rewrite in Python" (that's a goal). The mission is the terminal value: reliable, secure, maintainable software that serves users. Python is the vehicle, not the destination.

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
| C12 | **Test coverage ≥ 80%** for migrated code | Quality risk |

### Solution Space

From Phase 0 saturation:

```
Framework:  {Flask+SQLAlchemy+Celery, FastAPI+SQLAlchemy+ARQ, Django+DjangoORM+Celery}
Database:   {MySQL/MariaDB (keep), PostgreSQL (migrate), Dual (both)}
Frontend:   {Keep existing JS, htmx rewrite, React/Vue SPA, Jinja2+htmx+Alpine}
Migration:  {Entity-first, Call-graph-first, Vertical-slice, Hybrid, Granular}
Testing:    {pytest + contract tests, parallel-run validation, shadow traffic}
Deployment: {Docker + docker-compose, Kubernetes, bare metal}
```

Pending ADRs narrow this space: see `docs/decisions/` directory.

---

## Cross-Reference to Specs and ADRs

| Charter Element | Primary Spec | Related ADR |
|-------------|-------------|-------------|
| G1 (functional migration) | 01-architecture, 09-source-index | ADR-0001 (flow variant) |
| G2 (API contract) | 03-api-routing | ADR-0004 (frontend) |
| G3 (database schema) | 02-database | ADR-0003 (DB engine) |
| G4 (security) | 06-security | — |
| G5 (deployment) | 08-deployment | — |
| G6 (plugin system) | 05-plugin-system | — |
| P1-P8 (premises) | All specs | ADR-0002 (framework), ADR-0005 (call graph) |
| C1-C6 (hard constraints) | AGENTS.md | — |
| Solution Space | 10-migration-dimensions | ADR-0001 through ADR-0005 |

---

## Requirements Traceability Matrix

| Requirement | Source | Goal | Constraint | Spec | Status |
|------------|--------|------|-----------|------|--------|
| All 35 DB tables modeled in Python | P2, G3 | G3 | C4 | 02-database | Not started |
| All RPC endpoints preserved | G2 | G2 | C3 | 03-api-routing | Not started |
| REST API backward compatible | G2 | G2 | C3 | 03-api-routing | Not started |
| Feed update daemon equivalent | G1, P7 | G1 | — | 07-caching-performance | Not started |
| 24 plugin hooks preserved | G6 | G6 | C9 | 05-plugin-system | Not started |
| SHA1→bcrypt password migration | G4 | G4 | — | 06-security | Not started |
| Prepared statements (no SQL injection) | G4 | G4 | — | 06-security | Not started |
| SSL verification for feed fetching | G4 | G4 | — | 06-security | Not started |
| Docker deployment | G5 | G5 | C10 | 08-deployment | Not started |
| CI/CD pipeline | G5 | G5 | — | 08-deployment | Not started |
| i18n (18+ locales) | G1, P8 | G1 | — | 08-deployment | Not started |
| Counter cache system | G1 | G1 | — | 07-caching-performance | Not started |
| Session management | G1 | G1 | — | 06-security | Not started |
| Frontend serves unchanged | G2, P3 | G2 | — | 04-frontend | Not started |

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why Dangerous | Mitigation |
|-------------|---------------|------------|
| Big-bang rewrite | High risk of incomplete migration | Use incremental variant (ADR-0001) |
| Gold-plating | Adding features during migration | Strict behavioral parity (C3) |
| Skipping Phase 0 models | Business logic has no foundation | Entity-first or hybrid variant |
| Ignoring security findings | Replicating known vulnerabilities | G4 explicitly requires fixes |
| Over-engineering plugin system | Python's module system is simpler | Keep hooks, simplify discovery |
| Dual-DB support "just in case" | Double testing burden | Decide in ADR-0003 |
| Frontend rewrite during backend migration | Two moving targets | ADR-0004 recommends Phase 1: keep JS |
