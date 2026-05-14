# 00 — Project Charter

**Document type**: Mission / Goals / Premises / Constraints (MGPC)
**Project**: TT-RSS PHP → Python Modernization
**Phase 1 output**: Source knowledge extraction (this document)
**Status**: synthesised from dimension specs 01–10 + community research GRP-01–10
**Research**: DEGRADED (web search unavailable; training-knowledge-only for external citations)

---

## Mission

Migrate Tiny Tiny RSS (TT-RSS) from PHP to Python, fully preserving all
specifications, design decisions, and observable behaviour of the source project.

The migration targets: **Flask** (web framework) · **SQLAlchemy** (ORM) ·
**Celery** (background tasks) · **pluggy** (plugin system) · **PostgreSQL** (DB)

---

## Goals

### G-01 — Functional parity
Every user-visible feature of TT-RSS PHP must be reproducible with the Python target
under the same configuration. Differences in behaviour are permitted only where:
a) an intentional security improvement is made (SHA1 → argon2id, mcrypt → Fernet),
b) a documented semantic divergence is accepted by design (see `12-semantic-discrepancies.md`),
or c) a source-side bug is explicitly corrected.

### G-02 — API client compatibility
The JSON API (API_LEVEL = 8) must remain byte-compatible with existing third-party
clients (mobile apps, Miniflux, integration scripts). The response envelope
`{"seq": N, "status": 0|1, "content": {...}}` must be preserved exactly.

### G-03 — Plugin ecosystem continuity
The 24-hook pluggy hookspec must provide equivalent extension points to the PHP
`PluginHost` hook registry. Existing plugin authors must be able to port their
plugins with predictable semantics (no silent hook removal or semantic changes
without documented breaking-change notes).

### G-04 — Security improvement
The migration is an opportunity to remediate 10 known security findings identified
in dimension `09-security-surface.md`. SF-01 (SQL injection), SF-02 (SHA1 passwords),
SF-03 (mcrypt credentials) are mandatory remediations. Others are recommended.

### G-05 — Source traceability
Every Python function, class, model, route, and constant must carry a traceability
comment linking it to its PHP source origin (file:line or table:column).
This enables semantic verification and audit.

### G-06 — Test coverage gate
The Python target must achieve ≥95% test coverage (measured by `pytest --cov`).
Every test must cite its PHP source via docstring. No `pytest.mark.skip` permitted.

---

## Premises (with risk assessment)

### P-01 — Source is the ground truth
The PHP source in `source-repos/ttrss-php/` is treated as read-only authoritative
specification. Deviations must be documented in `12-semantic-discrepancies.md`.
Risk: LOW. Source is available and readable.

### P-02 — PostgreSQL is the target DB
ADR-0003 selects PostgreSQL as the only supported database for the Python target.
MySQL support is dropped. The MySQL-specific code paths in PHP (`Db_Mysql`, `Db_Mysqli`,
`MYSQL_CHARSET`) have no Python equivalent.
Risk: LOW if existing deployments use PostgreSQL (default since TT-RSS 1.8).
Risk: MEDIUM if any production deployment uses MySQL.

### P-03 — Celery + Redis replaces PCNTL daemon
ADR-0011 selects Celery with Redis broker to replace `update_daemon2.php`.
The PCNTL fork model is Unix-only and has no Python equivalent.
Celery provides better observability, retry logic, and distributed execution.
Risk: MEDIUM — Celery configuration complexity; Redis adds an infrastructure dependency.

### P-04 — pluggy replaces PluginHost
The 24 hooks in `PluginHost` are translated to pluggy hookspecs.
Value-returning hooks (6 of 24) use `firstresult=True`.
HOOK_QUERY_HEADLINES is redesigned as a structured filter API (breaking change).
Risk: HIGH for any plugin using HOOK_QUERY_HEADLINES. LOW for all other hooks.

### P-05 — Vanilla JS SPA replaces Dojo frontend
ADR-0017 replaces the Dojo Toolkit SPA with a modern Vanilla JS SPA.
The Python backend is not responsible for porting the frontend JavaScript.
Risk: HIGH complexity (Dojo → Vanilla JS); scoped to a separate work stream.

### P-06 — Alembic manages schema migrations
`DbUpdater` (sequential SQL scripts) → Alembic (transactional revisions on PostgreSQL).
The 31-table schema is migrated in FK dependency order (levels 0–4 from dimension 04).
Risk: LOW — Alembic is well-tested; PostgreSQL is transactional on DDL.

### P-07 — OTP (TOTP) parity preserved
The TOTP enrollment flow (QR code → `OTP_SECRET_KEY` pref → login verification) is
preserved using `pyotp` + `qrcode` (Python). The `OTP_SECRET_KEY` pref key name is preserved.
Risk: LOW — RFC 6238 TOTP is standardised; `pyotp` is the de-facto Python library.

---

## Constraints

### C-01 — Source read-only
`source-repos/ttrss-php/` must not be modified. All analysis is read-only.
Source: AGENTS.md project rules.

### C-02 — No-skip rule
`pytest.mark.skip` and `pytest.skip()` are prohibited. Every test must pass.
Source: AGENTS.md rule #16.

### C-03 — Traceability mandatory
Every code element in `target-repos/` must have a traceability comment.
Source: AGENTS.md rule #10.

### C-04 — API backward compatibility
`API_LEVEL = 8` must be preserved. The JSON envelope format must not change.
Source: G-02 + D-AC-03.

### C-05 — HOOK_QUERY_HEADLINES is a breaking change
The structured filter API replacing the SQL-fragment hook is acknowledged as
a breaking change for PHP plugins using this hook. This constraint is accepted:
security and correctness outweigh compatibility for this one hook.
Source: D-PH-01, dimension `05-plugin-hook-graph.md`.

### C-06 — mcrypt migration before Python goes live
`ttrss_feeds.auth_pass` rows encrypted with mcrypt must be re-encrypted with Fernet
before the Python app serves any feed update requests for authenticated feeds.
Source: D-SE-03, ADR-0009.

### C-07 — SHA1 migration progressive
SHA1 passwords must be upgradeable to argon2id on first login (dual-hash).
New passwords always use argon2id. No forced reset unless deployment policy requires it.
Source: D-SE-02, ADR-0008.

### C-08 — Test traceability mandatory
Every unit test docstring must cite its PHP source (file:function:line).
Source: AGENTS.md rule (test traceability).

---

## Requirements Traceability Matrix (RTM)

| Requirement | Source dimension | Source construct | Target artifact |
|---|---|---|---|
| R-01: All 31 DB tables as SQLAlchemy models | 04-entity-schema | `ttrss_schema_pgsql.sql` | `target-repos/ttrss/models/*.py` |
| R-02: FK cascade behaviour preserved | 04-entity-schema | `references ... ON DELETE CASCADE/SET NULL` | `relationship(cascade=...)` in models |
| R-03: Alembic revisions in FK level order | 04-entity-schema | FK dependency levels 0–4 | `target-repos/migrations/versions/` |
| R-04: All 24 hooks as pluggy hookspecs | 05-plugin-hook-graph | `pluginhost.php:18–41` | `target-repos/ttrss/plugins/hookspec.py` |
| R-05: firstresult on 6 value-returning hooks | 05-plugin-hook-graph | hook classification table | hookspec `firstresult=True` |
| R-06: Auth_Internal hookimpl with dual-hash | 07-session-auth | `plugins/auth_internal/init.php` | `target-repos/ttrss/plugins/auth_internal/` |
| R-07: JSON API envelope preserved (seq, status, content) | 06-api-route-surface | `classes/api.php:36` | `target-repos/ttrss/blueprints/api/views.py` |
| R-08: API_LEVEL = 8 preserved | 06-api-route-surface | `classes/api.php:5` | Constant in api blueprint |
| R-09: All API ops implemented (24 listed) | 06-api-route-surface | `classes/api.php` methods | API Blueprint routes |
| R-10: All backend ops implemented | 06-api-route-surface | `classes/backend.php`, `classes/rpc.php` | Backend Blueprint routes |
| R-11: Public routes implemented | 06-api-route-surface | `classes/handler/public.php` | Public Blueprint routes |
| R-12: Fernet replaces mcrypt | 07-session-auth | `include/crypt.php` | `target-repos/ttrss/utils/crypt.py` |
| R-13: argon2id replaces SHA1 | 07-session-auth | `plugins/auth_internal/init.php` | `verify_password()` + `hash_password()` |
| R-14: Flask-Login + Redis replaces DB sessions | 07-session-auth | `include/sessions.php` | Flask-Login config + Redis |
| R-15: validate_session() checks in before_request | 07-session-auth | `include/sessions.php:38` | `@before_request` function |
| R-16: Celery replaces PCNTL daemon | 08-background-daemon | `update_daemon2.php` | `target-repos/ttrss/tasks/feed_update.py` |
| R-17: Feed update pipeline hooks at correct points | 08-background-daemon | `include/rssfuncs.php` | Celery task + hook dispatch |
| R-18: ETag/Last-Modified conditional GET preserved | 08-background-daemon | `fetch_url()` | `httpx` conditional GET headers |
| R-19: get_pref() / set_pref() ORM equivalents | 10-configuration-surface | `include/db-prefs.php` | `UserPref.get()` / `UserPref.set()` |
| R-20: ttrss_prefs seed data in Alembic | 10-configuration-surface | `install/index.php` | Alembic data migration |
| R-21: pydantic Settings for all config constants | 10-configuration-surface | `config.php-dist` | `target-repos/ttrss/config.py` |
| R-22: sanitize() HTML allowlist preserved | 09-security-surface | `include/functions2.php:~834` | `bleach.clean()` configured allowlist |
| R-23: HOOK_QUERY_HEADLINES as structured filter API | 05-plugin-hook-graph | `classes/api.php:648` | hookspec + SQLAlchemy Select |
| R-24: Label negative-ID encoding preserved | 04-entity-schema | `include/labels.php` | `label_feed_id = -(label.id + 11)` |
| R-25: TOTP verification with pyotp | 07-session-auth | `lib/otphp/lib/totp.php` | `pyotp.TOTP(secret).verify(code)` |
| R-26: Access key token auth | 07-session-auth | `ttrss_access_keys` + handler/public.php | `verify_token()` + decorator |
| R-27: Counter cache upsert with locking | 04-entity-schema | `include/ccache.php` | SELECT FOR UPDATE or Redis INCR |
| R-28: Function decomposition from functions.php | 01-call-graph | `include/functions.php` (~2003 LOC) | Split into `ttrss/utils/*.py` modules |
| R-29: Test coverage ≥95% | all dimensions | AGENTS.md rule | pytest-cov gate in CI |
| R-30: All code with source traceability comments | all dimensions | AGENTS.md rule #10 | Code review gate |

---

## Source inventory summary

| Metric | Value |
|---|---|
| PHP source files | 138 |
| Total LOC (PHP) | ~44,000 |
| DB tables | 31 |
| Hook constants | 24 |
| Config constants (file-based) | ~35 |
| Pref constants (DB-stored) | ~50 |
| Third-party libraries bundled | 13 |
| Entry points (HTTP) | 9 |
| Plugin slot | 1 (auth_internal built-in) |
| Test files in source | 0 (no PHP test suite) |

---

## Phase index

| Phase | Spec | Status |
|---|---|---|
| Phase 1 — Foundation | `specs/001-foundation/` | DONE (prior work) |
| Phase 2 — Core logic | `specs/002-core-logic/` | DONE (prior work) |
| Phase 3 — Business logic | `specs/003-business-logic/` | DONE (prior work) |
| Phase 4 — API handlers | `specs/004-api-handlers/` | DONE (prior work) |
| Phase 5 — Semantic verification | `specs/005-semantic-verification/` | DONE (prior work) |
| Phase 6 — Deployment | `specs/006-deployment/` | DONE (prior work) |

**Note**: This Phase 1 clean-room extraction (`phase1-test/`) is a retroactive
verification run to validate that the specs-extractor skill produces results
consistent with the prior hand-executed Phase 1 analysis. See `PHASE1-SUMMARY.md`.
