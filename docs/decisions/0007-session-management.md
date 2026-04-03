# ADR-0007: Session Management Strategy

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase implements custom database-backed sessions in `include/sessions.php`. Sessions are stored in the `ttrss_sessions` table with custom `open`/`read`/`write`/`destroy`/`gc` handlers registered via `session_set_save_handler()`. The login flow (`authenticate()` in `functions.php`) validates IP address and User-Agent on each request, and sessions have a configurable timeout (`SESSION_EXPIRE_TIME`). API access uses a separate `sid` mechanism with its own session lookup.

The Python replacement must support:
- Web UI sessions (cookie-based, server-side state)
- API sessions (token-based for mobile/third-party clients)
- IP/UA validation (or a modern equivalent)
- Configurable session expiry
- Concurrent session support per user

## Options

### A: Flask-Login + Redis Session Store

Use Flask-Login for authentication state management with Flask-Session backed by Redis for server-side session storage. Redis provides fast reads, built-in TTL for expiry, and atomic operations.

- Flask-Login handles `@login_required`, `current_user`, remember-me
- Redis TTL replaces manual garbage collection
- Session data serialized to Redis (not cookies)
- IP/UA validation as a `before_request` hook

### B: JWT Tokens (Stateless)

Issue signed JWT tokens on login. No server-side session state. Tokens contain user ID and claims, verified on each request.

- Stateless — no session store needed
- Token revocation requires a blocklist (re-introduces state)
- No server-side session data (must store preferences elsewhere)
- Better for API-first / mobile clients
- Token size grows with claims

### C: Database-Backed Sessions (Port PHP Pattern)

Replicate the PHP approach: store sessions in a `sessions` PostgreSQL table with the same `open`/`read`/`write`/`gc` lifecycle. Flask-Session supports SQLAlchemy as a backend.

- Closest to existing behavior
- All session data visible in DB (debugging, admin)
- Slower than Redis for high-traffic reads
- Requires periodic garbage collection (cron or background task)

## Trade-off Analysis

| Criterion | A: Flask-Login + Redis | B: JWT Tokens | C: DB-Backed Sessions |
|-----------|----------------------|---------------|----------------------|
| Performance | Excellent (in-memory) | Excellent (no lookup) | Good (DB query per request) |
| Scalability (multi-instance) | Excellent (shared Redis) | Excellent (stateless) | Good (shared DB) |
| Session revocation | Instant (delete key) | Complex (blocklist needed) | Instant (delete row) |
| Server-side state | Yes | No (or limited) | Yes |
| Operational complexity | Adds Redis dependency | Minimal | Uses existing DB |
| IP/UA validation | Easy (before_request) | In token claims | Easy (session row) |
| API client support | Separate token flow | Native | Separate token flow |
| Debugging / admin visibility | Redis CLI / monitoring | Decode JWT | SQL queries |
| Migration from PHP sessions | Clean break | Clean break | Near-identical pattern |

## Preliminary Recommendation

**Option A (Flask-Login + Redis)** — Redis is already recommended for Celery (ADR-0011), so it adds no new infrastructure. Flask-Login provides battle-tested authentication primitives. Redis TTL eliminates the need for manual session garbage collection. IP/UA validation can be added as a simple `before_request` hook.

For API clients, issue separate API tokens (stored in DB, similar to current `ttrss_api_sessions`) rather than reusing web sessions.

## Decision

**TBD**

## Consequences

- If Option A: Redis becomes a required runtime dependency (shared with Celery)
- If Option A: session data lost on Redis flush (acceptable — users re-login)
- If Option A: Flask-Login ecosystem provides remember-me, fresh-login, and session protection
- If Option B: no server-side session state complicates features like "log out all devices"
- If Option B: token revocation adds complexity that negates the stateless benefit
- If Option C: works but slower than Redis; no additional benefit over Option A
