# ADR-0002: Python Web Framework

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP source uses a custom handler-based dispatch system (`backend.php` routes `?op=X&method=Y` to handler classes). The Python replacement needs:

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

Consider **FastAPI** if async feed fetching performance is a priority.

## Decision

**TBD**

## Consequences

- Framework choice determines project skeleton structure
- Affects ORM choice (Flask is SQLAlchemy-native; Django has its own ORM)
- Affects async strategy (Flask = Celery; FastAPI = native async + Celery)
- Affects testing approach (pytest-flask vs pytest-asyncio vs Django test client)
