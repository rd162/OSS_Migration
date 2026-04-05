# Tasks 001 — Foundation

**Status:** ALL DONE  
**Completed:** 2026-04-03 (1a), 2026-04-04 (1b)  
**Spec ref:** specs/001-foundation/spec.md  
**Plan ref:** specs/001-foundation/plan.md

---

## Phase 1a — Walking Skeleton

> US-1a: Runnable Flask app with 10 core models and auth.

- [x] Create Flask app factory `ttrss/__init__.py` with `create_app()`  
  _Source: ttrss/classes/db.php + ttrss/include/init.php_
- [x] Create `ttrss/config.py` — environment-based config, no secrets in repo  
  _New: no PHP equivalent (Flask config pattern)_
- [x] Create `ttrss/extensions.py` — Flask extension instances (db, login_manager, celery_app)  
  _Source: ttrss/classes/db.php:Db (singleton → Flask extension)_
- [x] Implement 10 core SQLAlchemy models (ttrss_feeds, ttrss_entries, ttrss_users, ttrss_user_entries, ttrss_categories, ttrss_tags, ttrss_labels, ttrss_user_labels2, ttrss_prefs, ttrss_prefs_users)  
  _Source: ttrss/schema/ttrss_schema_pgsql.sql_
- [x] Wire Flask-Login + Redis server-side sessions  
  _Source: ttrss/classes/sessions.php (ADR-0007)_
- [x] Implement argon2id dual-hash password upgrade  
  _Source: ttrss/include/functions.php:authenticate_user (ADR-0008)_
- [x] Implement Fernet feed credential encryption  
  _Source: ttrss/include/functions.php feed auth (ADR-0009)_
- [x] Add Flask-Talisman security headers  
  _New: security improvement (ADR-0002)_
- [x] Add Flask-WTF CSRF protection  
  _New: security improvement (ADR-0002)_
- [x] Create Docker Compose development environment (PostgreSQL + Redis + Flask + Celery)  
  _New: no PHP equivalent_
- [x] Create Celery app + feed task stubs (`dispatch_feed_updates`, `update_feed`)  
  _Source: ttrss/update.php + ttrss/include/rssfuncs.php (ADR-0011)_
- [x] Write 33 unit tests with PHP source citations in docstrings  
  _AGENTS.md test traceability rule_
- [x] Rule 10a adversarial self-refine cycle — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] `pytest` 33 tests green | [x] app starts without error | [x] Docker Compose up

---

## Phase 1b — Complete Foundation

> US-1b: All 31 models, 24 hookspecs, Alembic baseline.

- [x] Implement remaining 21 SQLAlchemy models to reach 31 total  
  _Source: ttrss/schema/ttrss_schema_pgsql.sql (all active tables)_
- [x] Verify 4 deprecated pre-v124 tables correctly excluded  
  _Source: ttrss/schema/ttrss_schema_pgsql.sql (version history comments)_
- [x] Create 24 pluggy hookspecs in `ttrss/plugins/hookspecs.py`  
  _Source: ttrss/classes/pluginhost.php (HOOK_* constants)_
- [x] Set `firstresult=True` only on `hook_auth_user`  
  _Source: ttrss/classes/pluginhost.php (REGISTERS edge count in hook graph)_
- [x] Create PluginManager Flask extension in `ttrss/plugins/manager.py`  
  _Source: ttrss/classes/pluginhost.php:PluginHost (ADR-0010)_
- [x] Create Alembic baseline migration (31 tables, 75 seed rows)  
  _New: no PHP equivalent (Alembic infrastructure)_
- [x] Verify Alembic `upgrade head` runs cleanly on clean PostgreSQL instance  
  _QG-1 gate_
- [x] Commit decomposition map `specs/13-decomposition-map.md`  
  _Project planning artifact_
- [x] Run `validate_coverage.py` — DB_TABLE gate: 31/31 models matched  
  _QG-2 gate_
- [x] Run `validate_coverage.py` — Hook gate: 24/24 hookspecs matched  
  _QG-2 gate_
- [x] Rule 10a adversarial self-refine cycle — 0 traceability violations  
  _AGENTS.md Rule 10a_

**Gate:** [x] DB_TABLE 31/31 | [x] Hook 24/24 | [x] Alembic baseline | [x] pytest green

---

## Summary

| Phase | Tasks | Completed | Gate |
|-------|-------|-----------|------|
| 1a — Walking Skeleton | 13 | 13 | PASSED 2026-04-03 |
| 1b — Complete Foundation | 11 | 11 | PASSED 2026-04-04 |
| **Total** | **24** | **24** | **ALL DONE** |
