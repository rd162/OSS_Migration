# ADR-0002: Python Web Framework

- **Status**: accepted
- **Date proposed**: 2026-04-03
- **Date accepted**: 2026-04-03
- **Deciders**: Project lead (adversarial review, unanimous convergence)

## Context

The PHP source uses a custom handler-based dispatch system (`backend.php` routes `?op=X&method=Y` to handler classes).

**Spec references**: `specs/01-architecture.md` (handler-based dispatch, class hierarchy), `specs/03-api-routing.md` (entry points, RPC endpoints), `specs/04-frontend.md` (server-rendered HTML fragments, AJAX patterns), `specs/06-security.md` (CSRF — F6, sessions — F10, security headers — F7).

The Python replacement needs:

- HTTP routing with handler/blueprint organization
- JSON response serialization
- Session management (database-backed)
- CSRF protection
- Template rendering (for server-generated HTML fragments)
- Background task support (feed update daemon)
- Plugin/extension system compatibility

## Options

### Flask + Extensions
- **Flask** (WSGI, sync) + Flask-SQLAlchemy + Flask-Login + Flask-WTF + Celery
- Lightweight, matches TT-RSS's simplicity
- Mature ecosystem, well-documented
- Jinja2 templates for HTML fragment rendering
- Blueprints map cleanly to handler classes

### FastAPI + SQLAlchemy
- **FastAPI** (ASGI, async) + SQLAlchemy 2.0 async + Celery/ARQ
- Modern, auto-generated OpenAPI docs
- Async feed fetching could be significantly faster
- Pydantic models for request/response validation
- Less mature for server-rendered HTML patterns

### Django
- **Django** (WSGI) — full-featured with ORM, admin, auth built-in
- Heavier than needed for this project
- Django ORM is different from SQLAlchemy (migration complexity)
- Built-in admin could replace Pref_Users/Pref_System handlers
- Good plugin system (Django apps)

## Trade-off Analysis

| Criterion | Flask | FastAPI | Django |
|-----------|-------|---------|--------|
| Matches source architecture | Best | Good | Over-engineered |
| Async feed fetching | No (needs gevent/celery) | Native | No (needs celery) |
| Server-rendered HTML | Jinja2 (excellent) | Jinja2 (possible) | Django templates |
| Learning curve | Low | Medium | Medium |
| API documentation | Manual/Swagger ext | Auto OpenAPI | DRF needed |
| Background tasks | Celery | Celery/ARQ | Celery |
| Session management | Flask-Login | Custom/Starlette | Built-in |
| Community/maturity | Very high | High | Very high |

## Preliminary Recommendation

**Flask** — closest architectural match, simplest migration path, proven ecosystem.

### Async Strategy (addresses AR7)

Flask is WSGI/synchronous, but async is handled at the infrastructure level:

- **Web serving**: Gunicorn with gevent workers provides cooperative concurrency for thousands of concurrent HTTP connections without code changes. No Flask endpoint performs blocking I/O.
- **Feed fetching**: All feed I/O happens in **Celery workers** (ADR-0011), not in Flask request handlers. Each `update_feed()` task uses `asyncio.run()` + `httpx.AsyncClient` (ADR-0015) for concurrent HTTP fetches within the worker process. For batch operations, `asyncio.gather()` enables fetching multiple feeds concurrently within a single Celery task.
- **Database**: SQLAlchemy with synchronous psycopg2 driver is sufficient — database queries are fast local calls, not the I/O bottleneck. Connection pooling via SQLAlchemy handles concurrency.

This architecture means Flask's synchronous nature is irrelevant to feed fetching performance. FastAPI's native async would only matter if feed fetching happened inside request handlers, which it does not.

## Decision

**Flask** — accepted after compliance review of Solution C (FastAPI + Variant E). See `compliance-review-response.md`.

### Compliance-Informed Rationale

12 compliance claims against FastAPI were researched and confirmed or partially confirmed:

| Requirement | FastAPI Issue | Flask Resolution |
|------------|--------------|-----------------|
| R4 CSRF | No built-in; fastapi-csrf-protect uses Double Submit Cookie (JS changes needed) | Flask-WTF session-based token; zero JS changes |
| R4 Sessions | No built-in DB-backed sessions; requires third-party assembly | Flask-Session + Redis in one config line |
| R4 Templates | Jinja2 bolted on via Starlette; HTML-in-JSON bypasses Pydantic | Jinja2 native; render_template() + jsonify() idiomatic |
| R2 Parity | Pydantic strict typing fights PHP loose JSON | jsonify() uses json.dumps(); matches json_encode() naturally |
| R6 API | Path-based REST idiom; ?op=method neutralizes auto-docs | request.args dispatch natural; no imposed REST conventions |
| R11 Frontend | CSRF mechanism change requires JS modification | Session-based CSRF via init_params; zero JS changes |
| AR3 | API-first framework fights handler+HTML pattern | No framework opinions on response structure |
| AR6/AR7 | Full async stack over-engineers single-user RSS reader | Sync web; async only in Celery workers (httpx) |

## Consequences

- Project skeleton: Flask app factory pattern with Blueprints
- ORM: Flask-SQLAlchemy with sync psycopg2 driver
- Async: Celery + httpx async for feed fetching only (not web layer)
- Testing: pytest-flask with Flask test client
- CSRF: Flask-WTF session-based tokens; zero frontend JS changes
- Sessions: Flask-Session + Redis (shared with Celery broker per ADR-0011)
- Templates: Jinja2 native; HTML fragments in JSON via render_template() + jsonify()
