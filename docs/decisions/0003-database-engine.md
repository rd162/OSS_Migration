# ADR-0003: Database Engine Choice

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP source supports both MySQL and PostgreSQL via an adapter pattern. The Docker setup uses MariaDB 10.3 for development and MySQL 5.5 for production. Schema files exist in parallel for both engines (246 SQL files total).

Moving to Python with SQLAlchemy, we can:
1. Keep dual-database support (SQLAlchemy abstracts differences)
2. Choose one engine and simplify
3. Migrate to a different engine entirely

## Options

### A: Keep MySQL/MariaDB Only
- Zero data migration needed
- Docker setup already works
- MariaDB 10.3+ is solid
- Some features (JSON columns, window functions) are limited in older versions

### B: Migrate to PostgreSQL Only
- TT-RSS upstream historically preferred PostgreSQL
- Superior full-text search (replaces Sphinx dependency)
- Better JSON support, CTEs, window functions
- Better concurrent write performance
- Requires one-time data migration

### C: Keep Dual Support via SQLAlchemy
- SQLAlchemy dialect system handles differences
- Alembic can generate migrations for both
- More testing surface
- Some queries may need dialect-specific branches

## Trade-off Analysis

| Criterion | MySQL/MariaDB | PostgreSQL | Dual |
|-----------|--------------|------------|------|
| Migration effort | None | One-time schema + data | None |
| Full-text search | Needs Sphinx | Built-in (tsvector) | Complex |
| JSON support | Basic (5.7+) | Excellent (JSONB) | Lowest common |
| Operational familiarity | Current setup | May need new skills | Both |
| SQLAlchemy support | Excellent | Excellent | Excellent |
| Testing burden | 1x | 1x | 2x |
| Future flexibility | Good | Best | Best but costly |

## Preliminary Recommendation

**Option B: PostgreSQL** — simplifies the codebase, eliminates Sphinx dependency via native full-text search, and aligns with upstream TT-RSS preference. One-time migration cost is acceptable.

If team is MySQL-only: **Option A** is fine — SQLAlchemy makes the PHP adapter pattern unnecessary regardless.

## Decision

**TBD**

## Consequences

- If PostgreSQL: need data migration script (schema exists in source)
- If MySQL: keep existing Docker setup, add SQLAlchemy MySQL dialect
- If dual: double the migration testing, some queries need dialect handling
- Choice affects full-text search strategy (Sphinx vs PostgreSQL tsvector vs ElasticSearch)
