---
id: 006
title: Deployment — CI, Docker, Data Migration, Coverage Gate
status: in-progress
phase: 6
source: memory/phase6_plan_2026-04-04.md
---

# Spec 006 — Phase 6: Deployment

## User Stories

| ID | Story |
|----|-------|
| US-001 | As a developer, CI runs lint + test + build + coverage-gate on every master push |
| US-002 | As an operator, the Docker image is multi-stage (builder/runtime) with no secrets baked in and no build tools in runtime |
| US-003 | As an operator, all 3 service roles (web, worker, beat) run from the same image via docker-compose.prod.yml |
| US-004 | As an operator, nginx serves /static/ and /feed-icons/ and proxies / to the Flask app |
| US-005 | As a migrator, pgloader migrates MySQL → PostgreSQL with zero-date handling, tinyint→boolean, and all 18 sequences reset |
| US-006 | As a migrator, PHP serialize() blobs in ttrss_plugin_storage are converted to JSON |
| US-007 | As a team, the coverage gate is hard at ≥95% from B6 onward |

## Functional Requirements

| ID | Requirement | Source/Rule |
|----|-------------|-------------|
| FR-001 | CI job lint: ruff check + mypy + alembic upgrade head + alembic check | R08, R10, AR05 |
| FR-002 | CI job test: postgres:15-alpine + redis:7-alpine service containers; alembic upgrade head; pytest with JUnit XML; fail if failures+errors > 9 | R08, R09, R19 |
| FR-003 | CI job build: multi-stage Docker build with GHA cache; push=false | R05, R11 |
| FR-004 | CI coverage-gate: continue-on-error: true (B1-B5); removed in B6 | R18 |
| FR-005 | validate_coverage.py: SOURCE_COMMENT_RE matches all 6 Source comment forms; HANDLER_CLASS_MAP includes all 18 PHP handler classes | — |
| FR-006 | gunicorn.conf.py: worker_class=gthread (not gevent); post_fork disposes DB pool | R01, R02, R04 |
| FR-007 | celery_app.py: worker_process_init signal disposes DB pool | R03 |
| FR-008 | Dockerfile: 2-stage (builder: gcc+libpq-dev; runtime: libpq5 only); no ARG/ENV secrets; CMD = gunicorn | R05, R06, AR02, AR10 |
| FR-009 | docker-compose.prod.yml: web/worker/beat from same image; worker healthcheck uses bare celery inspect ping | R05, R07 |
| FR-010 | nginx serves /static/ with 1y cache + immutable header; /feed-icons/ with 7d cache | R20 |
| FR-011 | pre_migration_audit.sh: timezone check, zero-date count, 4-byte emoji check with --allow-emoji gate | R12, R13, R16 |
| FR-012 | pgloader.load: ZERO DATES TO NULL in WITH block; tinyint(1)→boolean; datetime→timestamp; 18 explicit AFTER LOAD DO setval; reset sequences OMITTED (pgloader bug #1598) | R12-R17, AR02, AR08, AR09 |
| FR-013 | convert_php_serialized.py: deserialize PHP-serialized rows to JSON; exits non-zero if any row fails | R14, AR07 |
| FR-014 | B6: remove continue-on-error from coverage-gate; deploy.yml runs pgloader + blob conversion on tag push | — |

## Constraints

- AR-04: CI uses postgres:15-alpine service container (not docker-compose up)
- AR-05: alembic check requires alembic upgrade head first
- AR-07: convert_php_serialized.py exits non-zero on any deserialization failure
- AR-08: pgloader reset sequences omitted (bug #1598) — use AFTER LOAD DO setval instead
- AR-09: zero-date handling in WITH block only; no duplicate CAST rule for zero dates
- AR-10: no baked-in secrets in Dockerfile ARG or ENV

## Acceptance Criteria

### B1 Gate
- [ ] All 4 CI jobs run on master push
- [ ] lint/test/build pass; coverage-gate runs but does not block (continue-on-error: true)
- [ ] Baseline coverage ~41.7% recorded in CI logs

### B2 Gate
- [ ] validate_coverage.py reports ≥95% locally
- [ ] CI coverage-gate job exits 0
- [ ] All tests still pass, ≤9 failures

### B3 Gate
- [ ] CI build succeeds with cache hit on second run
- [ ] `docker history` shows no SECRET/PASSWORD/DATABASE in image layers
- [ ] gcc not in runtime image; psycopg2 importable

### B4 Gate
- [ ] All services healthy (docker-compose ps)
- [ ] Worker healthcheck passes (bare celery inspect ping)
- [ ] nginx serves /static/ HTTP 200
- [ ] No 5xx from web on curl /api/

### B5 Gate
- [ ] pre_migration_audit.sh exits 0
- [ ] pgloader --dry-run exits 0
- [ ] convert_php_serialized.py exits 0 on sample data
- [ ] All 18 sequences aligned post-migration

### B6 Gate (FINAL — all hard)
- [ ] CI coverage-gate exits 0 at ≥95% (no continue-on-error)
- [ ] alembic upgrade head && alembic check exits 0 in lint job
- [ ] JUnit XML: failures+errors ≤9
- [ ] nginx serves /static/ HTTP 200
- [ ] Worker healthcheck healthy
- [ ] pgloader dry-run clean
- [ ] convert_php_serialized.py exits 0 on sample data

## Status

**IN PROGRESS** — B1 done, B2 coverage gate DONE (0 gaps), B3-B6 pending. Test coverage uplift active (32 files, ~250 tests, 5 batches).
