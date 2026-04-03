# ADR-0012: Logging Strategy

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase has a `Logger` class (`classes/logger.php`) with two backends:
- `Logger_SQL`: writes log entries to the `ttrss_error_log` table (columns: `errno`, `errstr`, `filename`, `lineno`, `context`, `owner`, `created_at`)
- `Logger_Syslog`: writes to syslog via `syslog()` with `LOG_USER` facility

The active backend is selected via `LOG_DESTINATION` in `config.php`. Error and warning messages are logged from feed updates, plugin loading, authentication failures, and database errors. The `ttrss_error_log` table is viewable in the admin preferences panel.

The Python replacement must support:
- Structured logging for machine-parseable output (container/cloud environments)
- Optional database logging for admin UI compatibility
- Contextual information (user, feed ID, request ID) attached to log entries
- Multiple output destinations (stdout, file, syslog, database)
- Log levels consistent with Python conventions

## Options

### A: structlog (JSON Structured Logging)

Use `structlog` for structured, contextual logging with JSON output. Processors transform log entries through a pipeline. Can wrap the standard `logging` module for compatibility.

- JSON output ideal for log aggregation (ELK, Loki, CloudWatch)
- Contextual binding (`log = log.bind(feed_id=42)`) propagates through call chain
- Processor pipeline for filtering, formatting, enrichment
- Integrates with standard `logging` as final output

### B: Python Standard logging Module

Use the built-in `logging` module with custom formatters and handlers. Add a custom `DBHandler` for database logging. Use `logging.config.dictConfig()` for configuration.

- No external dependencies
- Well-understood by all Python developers
- Custom handlers for DB, syslog, file
- Less ergonomic for structured/contextual logging
- Thread-safe by default

### C: Python logging to DB (Port PHP Pattern)

Replicate the PHP approach: write a custom logging handler that inserts into a `ttrss_error_log`-equivalent table. Primary output is the database; optional file/syslog secondary.

- Direct port of PHP behavior
- Admin UI can query logs from DB
- DB writes on every log entry (performance concern at high volume)
- Log loss if DB is unreachable
- Not suitable for container environments (stdout preferred)

## Trade-off Analysis

| Criterion | A: structlog | B: Standard logging | C: DB-Primary logging |
|-----------|-------------|--------------------|-----------------------|
| Structured output (JSON) | Native | Requires custom formatter | Manual |
| Contextual binding | Excellent (bind/unbind) | Limited (LoggerAdapter) | Manual |
| Container/cloud readiness | Excellent (stdout JSON) | Good (stdout text) | Poor (DB primary) |
| Admin UI log viewing | Optional DB sink | Optional DB handler | Native |
| External dependency | Yes (structlog) | None | None |
| Performance at high volume | Good (async-capable) | Good | Poor (DB write per entry) |
| Developer ergonomics | Excellent | Good | Fair |
| Integration with third-party libs | Via stdlib wrapper | Native | Via stdlib wrapper |
| Configuration flexibility | Processor pipeline | dictConfig / fileConfig | Custom |

## Preliminary Recommendation

**Option A (structlog)** with JSON output to stdout/stderr as the primary sink, plus an optional database sink for admin UI compatibility.

Architecture:
1. **structlog** as the logging front-end — all application code uses `structlog.get_logger()`
2. **JSON processor** for structured output in production; **console renderer** for development
3. **Standard logging integration**: structlog wraps `logging` so third-party libraries (SQLAlchemy, Celery, Flask) also produce structured output
4. **Optional DB handler**: a custom `logging.Handler` that writes to an `error_log` table, enabled via configuration for installations that want admin UI log viewing
5. **Request ID binding**: middleware binds a unique request ID to the structlog context on each HTTP request

## Decision

**TBD**

## Consequences

- If Option A: adds `structlog` dependency but gains excellent structured logging
- If Option A: JSON logs integrate seamlessly with modern log aggregation stacks
- If Option A: optional DB sink preserves admin UI log viewing without making it mandatory
- If Option B: no dependency but loses contextual binding ergonomics
- If Option C: closest to PHP but unsuitable for containerized deployments
- All options: log levels and categories should be documented for operators
