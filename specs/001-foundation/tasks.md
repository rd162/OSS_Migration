# Tasks 001 — Foundation

**Status:** ALL DONE  
**Completed:** 2026-04-03 (1a), 2026-04-04 (1b)  
**Spec ref:** specs/001-foundation/spec.md  
**Plan ref:** specs/001-foundation/plan.md

> **Heritage note:** Implemented on `main` before the `speckit-specify` branch workflow. `[US#]` and `[P]` markers added retroactively for spec-kit compatibility.

---

## Phase 1a — Walking Skeleton **[US-1a]**

> **Story:** As a developer, I need a runnable Flask application with core models and authentication so that the project has a working skeleton to build upon.

- [x] [US-1a] Create Flask app factory `ttrss/__init__.py` with `create_app()`  
  _Source: ttrss/classes/db.php + ttrss/include/init.php_
- [x] [P] [US-1a] Create `ttrss/config.py` — environment-based config, no secrets in repo  
  _New: no PHP equivalent (Flask config pattern)_
- [x] [P] [US-1a] Create `ttrss/extensions.py` — Flask extension instances (db, login_manager, celery_app)  
  _Source: ttrss/classes/db.php:Db (singleton → Flask extension)_
- [x] [P] [US-1a] Implement 10 core SQLAlchemy models (ttrss_feeds, ttrss_entries, ttrss_users, ttrss_user_entries, ttrss_categories, ttrss_tags, ttrss_labels, ttrss_user_labels2, ttrss_prefs, ttrss_prefs_users)  
  _Source: ttrss/schema/ttrss_schema_pgsql.sql_
- [x] [US-1a] Wire Flask-Login + Redis server-side sessions  
  _Source: ttrss/classes/sessions.php (ADR-0007)_
- [x] [P] [US-1a] Implement argon2id dual-hash password upgrade  
  _Source: ttrss/include/functions.php:authenticate_user (ADR-0008)_
- [x] [P] [US-1a] Implement Fernet feed credential encryption  
  _Source: ttrss/include/functions.php feed auth (ADR-0009)_
- [x] [P] [US-1a] Add Flask-Talisman security headers  
  _New: security improvement (ADR-0002)_
- [x] [P] [US-1a] Add Flask-WTF CSRF protection  
  _New: security improvement (ADR-0002)_
- [x] [P] [US-1a] Create Docker Compose development environment (PostgreSQL + Redis + Flask + Celery)  
  _New: no PHP equivalent_
- [x] [P] [US-1a] Create Celery app + feed task stubs (`dispatch_feed_updates`, `update_feed`)  
  _Source: ttrss/update.php + ttrss/include/rssfuncs.php (ADR-0011)_
- [x] [P] [US-1a] Write 33 unit tests with PHP source citations in docstrings  
  _AGENTS.md test traceability rule_
- [x] [US-1a] Rule 10a adversarial self-refine cycle — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] `pytest` 33 tests green | [x] app starts without error | [x] Docker Compose up

---

## Phase 1b — Complete Foundation **[US-1b]**

> **Story:** As a developer, I need all 31 ORM models, all 24 plugin hookspecs, an Alembic baseline migration, and Celery task stubs so that Phase 2 can implement business logic against a complete foundation.

- [x] [P] [US-1b] Implement remaining 21 SQLAlchemy models to reach 31 total  
  _Source: ttrss/schema/ttrss_schema_pgsql.sql (all active tables)_
- [x] [P] [US-1b] Verify 4 deprecated pre-v124 tables correctly excluded  
  _Source: ttrss/schema/ttrss_schema_pgsql.sql (version history comments)_
- [x] [P] [US-1b] Create 24 pluggy hookspecs in `ttrss/plugins/hookspecs.py`  
  _Source: ttrss/classes/pluginhost.php (HOOK_* constants)_
- [x] [US-1b] Set `firstresult=True` only on `hook_auth_user`  
  _Source: ttrss/classes/pluginhost.php (REGISTERS edge count in hook graph)_
- [x] [US-1b] Create PluginManager Flask extension in `ttrss/plugins/manager.py`  
  _Source: ttrss/classes/pluginhost.php:PluginHost (ADR-0010)_
- [x] [US-1b] Create Alembic baseline migration (31 tables, 75 seed rows)  
  _New: no PHP equivalent (Alembic infrastructure)_
- [x] [US-1b] Verify Alembic `upgrade head` runs cleanly on clean PostgreSQL instance  
  _QG-1 gate_
- [x] [P] [US-1b] Commit decomposition map `specs/13-decomposition-map.md`  
  _Project planning artifact_
- [x] [US-1b] Run `validate_coverage.py` — DB_TABLE gate: 31/31 models matched  
  _QG-2 gate_
- [x] [US-1b] Run `validate_coverage.py` — Hook gate: 24/24 hookspecs matched  
  _QG-2 gate_
- [x] [US-1b] Rule 10a adversarial self-refine cycle — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] DB_TABLE 31/31 | [x] Hook 24/24 | [x] Alembic baseline | [x] pytest green

---

## Summary

| Phase | Tasks | Completed | Gate |
|-------|-------|-----------|------|
| 1a — Walking Skeleton | 13 | 13 | PASSED 2026-04-03 |
| 1b — Complete Foundation | 11 | 11 | PASSED 2026-04-04 |
| **Total** | **24** | **24** | **ALL DONE** |
