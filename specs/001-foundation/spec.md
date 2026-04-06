# Spec 001 — Foundation

**Status:** DONE  
**Completed:** 2026-04-03 (Phase 1a), 2026-04-04 (Phase 1b)  
**Phase:** 1 of 6  
**Constitution ref:** P1 (Library-First), P2 (Test-First), P3 (Source Traceability), P4 (Security-by-Default)

---

## User Stories

### US-1a — Walking Skeleton

> As a developer, I need a runnable Flask application with core models and authentication so that the project has a working skeleton to build upon.

**Acceptance Criteria:**

- [ x ] Flask app factory (`create_app()`) exists and starts without errors
- [ x ] 10 core SQLAlchemy models defined and importable
- [ x ] Flask-Login session management operational (Redis-backed)
- [ x ] Docker Compose development environment runs with `docker-compose up`
- [ x ] argon2id password hashing active (SHA1 dual-hash upgrade on login)
- [ x ] Fernet feed credential encryption wired
- [ x ] Flask-Talisman + Flask-WTF CSRF active
- [ x ] 33 unit tests passing

### US-1b — Complete Foundation

> As a developer, I need all 31 ORM models, all 24 plugin hookspecs, an Alembic baseline migration, and Celery task stubs so that Phase 2 can implement business logic against a complete foundation.

**Acceptance Criteria:**

- [ x ] All 31 active SQLAlchemy models defined (4 deprecated pre-v124 tables excluded by design)
- [ x ] Alembic baseline migration runs cleanly (31 tables, 75 seed rows)
- [ x ] 24 pluggy hookspecs match the 24 `HOOK_*` constants in the PHP hook graph
- [ x ] `firstresult=True` only on `hook_auth_user` (matches hook graph: only 1 REGISTERS edge)
- [ x ] PluginManager singleton wired as Flask extension
- [ x ] Celery app initialized with feed task stubs (`dispatch_feed_updates`, `update_feed`)
- [ x ] Decomposition map (`specs/13-decomposition-map.md`) committed
- [ x ] DB_TABLE graph gate: all 31 model tables appear in db_table_graph.json, every graph table has a model
- [ x ] Hook graph gate: all 24 hookspecs detected by `validate_coverage.py`

---

## Functional Requirements

| ID | Requirement | PHP Source | ADR |
|----|-------------|-----------|-----|
| FR-101 | Flask application factory with blueprints and config | classes/db.php, include/init.php | 0002 |
| FR-102 | 10 core SQLAlchemy models: ttrss_feeds, ttrss_entries, ttrss_users, ttrss_user_entries, ttrss_categories, ttrss_tags, ttrss_labels, ttrss_user_labels2, ttrss_prefs, ttrss_prefs_users | schema/ttrss_schema_pgsql.sql | 0006 |
| FR-103 | Remaining 21 SQLAlchemy models (31 total) | schema/ttrss_schema_pgsql.sql | 0006 |
| FR-104 | Flask-Login integration with Redis-backed server-side sessions | classes/sessions.php | 0007 |
| FR-105 | argon2id dual-hash password upgrade on login | include/functions.php:authenticate_user | 0008 |
| FR-106 | Fernet symmetric encryption for feed credentials | include/functions.php (feed auth) | 0009 |
| FR-107 | Security headers (flask-talisman) + CSRF (Flask-WTF) | include/init.php security setup | 0002 |
| FR-108 | Docker Compose development environment | docker-compose.yml equivalent | 0001 |
| FR-109 | Alembic baseline migration (31 tables, 75 seed rows) | schema/ttrss_schema_pgsql.sql | 0006 |
| FR-110 | 24 pluggy hookspecs matching PHP HOOK_* constants | classes/pluginhost.php | 0010 |
| FR-111 | PluginManager Flask extension (singleton replacement) | classes/pluginhost.php:PluginHost | 0010 |
| FR-112 | Celery app + feed task stubs (dispatch_feed_updates, update_feed) | update.php, include/rssfuncs.php | 0011 |

---

## Non-Functional Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| NFR-101 | All code has `# Source:` traceability comments | AGENTS.md Rule 10 (C7) |
| NFR-102 | PostgreSQL only — no MySQL compatibility code | ADR-0003 |
| NFR-103 | No secrets in repository — config via environment variables | C5 |
| NFR-104 | Unit tests pass (33 minimum at Phase 1a exit) | C13 |
| NFR-105 | DB_TABLE + Hook graph gates pass | Master plan Phase 1b gate |

---

## Acceptance Tests

| Test | Expected | Status |
|------|----------|--------|
| `flask run` starts without error | HTTP 200 on root | PASS |
| 31 models importable from `ttrss.models` | No ImportError | PASS |
| Alembic `upgrade head` on clean DB | 31 tables created, 75 rows seeded | PASS |
| 24 hookspecs detected by validate_coverage.py | 24/24 match hook graph | PASS |
| `pytest` runs 33+ tests | All green | PASS |
| `docker-compose up` starts all services | No container exits | PASS |

---

## Constraints

- Inherits all constitution constraints (read-only source-repos, traceability, PostgreSQL-only).
- Phase 1 establishes the schema contract — models defined here must not have breaking changes in later phases without a new Alembic migration.
- Phase 2 may not start until Phase 1b acceptance tests pass.

---

## Success Criteria

- **SC-001:** Application starts and serves requests without errors within 2 seconds of `flask run`
- **SC-002:** All 31 database tables are created on a clean PostgreSQL instance without manual intervention
- **SC-003:** Authentication rejects 100% of invalid credentials and accepts valid ones with no false negatives
- **SC-004:** The development environment starts all required services with a single `docker-compose up` command
- **SC-005:** Password storage never exposes plaintext or SHA1 hashes after the upgrade path is triggered

## Assumptions

- PostgreSQL is the only target database; MySQL compatibility is explicitly out of scope
- All secrets and credentials are supplied via environment variables, never baked into source
- The PHP schema file (`ttrss_schema_pgsql.sql`) is the authoritative table definition; any deviation is a bug
- Redis is available as both a session store and a Celery broker in all environments

---

> **Heritage note:** This phase was implemented on `main` before the `speckit-specify` branch workflow was established. Spec content is authoritative; it was not generated via `/speckit-specify`.
