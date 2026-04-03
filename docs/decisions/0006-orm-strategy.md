# ADR-0006: ORM vs Raw SQL

- **Status**: accepted
- **Date proposed**: 2026-04-03
- **Date accepted**: 2026-04-03
- **Deciders**: Project lead (adversarial review, unanimous convergence)

## Context

The PHP codebase uses raw SQL everywhere via a custom `db_query()` wrapper — over 200 call sites across handlers, feed updater, and utility functions. There is no ORM; queries are hand-written with string interpolation (though `db_escape_string` is used for escaping). The 35 database tables have implicit relationships (e.g., `ttrss_entries` ↔ `ttrss_user_entries` ↔ `ttrss_feeds`) that are not enforced by foreign keys in all cases.

A Python migration must decide how to represent the data layer: full ORM mapping, a lighter query-builder approach, or continued raw SQL.

## Options

### A: SQLAlchemy ORM (Declarative Models)

Map all 35 tables to Python classes using SQLAlchemy's declarative model system. Relationships, constraints, and defaults are expressed in Python. All queries use the ORM query API or `select()` constructs.

- Full type-safe model layer
- Relationship loading (lazy/eager) replaces manual JOINs
- Alembic migrations generated from model diffs
- Unit-of-work pattern for transactional consistency

### B: SQLAlchemy Core (Query Builder / Raw Expressions)

Use SQLAlchemy's Core layer (Table objects, `select()`, `insert()`, `update()`) without ORM model classes. Tables are reflected or declared as `Table` objects. Queries are built programmatically but without object-relational mapping.

- Lighter than ORM, closer to raw SQL
- Still parameterized and dialect-agnostic
- No relationship loading or identity map
- Still supports Alembic for migrations

### C: Raw SQL with psycopg2

Continue the PHP pattern: write raw SQL strings, execute via `psycopg2` (or `asyncpg`), manually manage connections and transactions. Queries are nearly 1:1 ports of the PHP originals.

- Fastest to port (copy-paste SQL, adjust syntax)
- No abstraction overhead
- No protection against SQL injection beyond manual parameterization
- No schema-as-code, no generated migrations

## Trade-off Analysis

| Criterion | A: SQLAlchemy ORM | B: SQLAlchemy Core | C: Raw SQL (psycopg2) |
|-----------|-------------------|--------------------|-----------------------|
| Porting effort | High (model all 35 tables) | Medium | Low (copy SQL) |
| Long-term maintainability | Excellent | Good | Poor |
| Type safety | Strong (with mypy plugin) | Moderate | None |
| Query complexity handling | Good (hybrid for complex) | Excellent | Excellent |
| Alembic migration support | Native | Native | Manual |
| SQL injection protection | Built-in | Built-in | Manual parameterization |
| Performance overhead | Slight (identity map) | Minimal | None |
| Relationship traversal | Automatic | Manual JOINs | Manual JOINs |
| Testing (fixtures/factories) | Excellent (factory_boy) | Good | Poor |

## Preliminary Recommendation

**Option A (SQLAlchemy ORM)** for the main data layer — model all 35 tables as declarative classes with proper relationships. This pays for itself in maintainability, test fixtures, and Alembic migration generation.

Use **SQLAlchemy Core** selectively for the handful of complex analytical queries (feed statistics, purge operations, label/score aggregations) where the ORM query builder is awkward.

This hybrid approach gives the best of both worlds: clean model layer for 90% of queries, raw power for the remaining 10%.

## Decision

**Option A: SQLAlchemy ORM (Declarative Models)** with selective use of **SQLAlchemy Core** for complex analytical queries (feed statistics, purge operations, label/score aggregations). Map all 35 tables as declarative classes with proper relationships. sqlacodegen auto-generates initial models from existing schema. Alembic provides automated migration generation. factory_boy enables test fixtures.

## Consequences

- If Option A: requires upfront investment to model 35 tables and their relationships
- If Option A: Alembic provides automated schema migration generation going forward
- If Option A: enables factory_boy or similar for test data, improving test quality
- If Option B: faster initial development but loses relationship convenience
- If Option C: fastest port but accumulates technical debt and SQL injection risk
- Hybrid A+B: requires team discipline on when to use ORM vs Core
