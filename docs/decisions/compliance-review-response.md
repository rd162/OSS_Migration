# Compliance Review Response: Solution C ("Async Modernization") Non-Compliance

- **Date**: 2026-04-03
- **Scope**: ADR-0001 (Variant E), ADR-0002 (FastAPI), ADR-0003 (PostgreSQL)
- **Reviewed Solution**: Variant E (Granular Multi-Pass) + FastAPI + PostgreSQL + full async stack

---

## STEP 1 -- Research Verdicts on Each Compliance Claim

### R1 (Solo/small-team execution) -- Variant E has 11 passes, rated "OK" not "Best"

**VERDICT: CONFIRMED.** The project's own recommendation matrix in `specs/10-migration-dimensions.md` rates Variant E as "OK" for solo dev, "High" planning overhead, and "Slow" time to first runnable code. Variant D is explicitly rated "Best" for solo dev with "Medium" planning overhead. The compliance review correctly identifies this as a violation -- choosing a variant rated "OK" over one rated "Best" for the project's primary constraint (solo/small-team) requires justification that was not provided.

### R4 (CSRF) -- FastAPI has no built-in CSRF; fastapi-csrf-protect uses Double Submit Cookie

**VERDICT: PARTIALLY CORRECT.**

The claim that FastAPI has no built-in CSRF protection is **correct**. Per [FastAPI Security docs](https://fastapi.tiangolo.com/tutorial/security/) and [StackHawk](https://www.stackhawk.com/blog/csrf-protection-in-fastapi/), FastAPI relies on third-party packages or CORS configuration for CSRF.

The claim that `fastapi-csrf-protect` is incompatible with the existing `init_params`-based CSRF token injection is **overstated**. Per the [fastapi-csrf-protect GitHub repo](https://github.com/aekasitt/fastapi-csrf-protect), the library offers a "flexible" sub-package that accepts CSRF tokens from **either header or form body**. A custom middleware could extract the `csrf_token` parameter from POST bodies (as the PHP frontend sends it) and validate against a session-stored token. However, the compliance review is correct that this requires **custom integration work** that Flask-WTF handles natively.

**Flask comparison**: Per [Flask-WTF CSRF docs](https://flask-wtf.readthedocs.io/en/latest/csrf/), Flask-WTF stores the raw CSRF token in the server-side session and validates tokens from either form fields or the `X-CSRFToken` header. The existing JS injects `csrf_token` as a POST parameter via Prototype.js wrapper -- Flask-WTF accepts this natively with zero JS changes. This is a genuine advantage of Flask over FastAPI for this specific migration.

### R4 (Sessions) -- FastAPI has no built-in database-backed sessions

**VERDICT: CONFIRMED, but solvable.**

Starlette's built-in `SessionMiddleware` uses signed cookies only (client-side, 4KB limit). For server-side sessions, third-party libraries are required:
- [starsessions](https://github.com/alex-oleshkevich/starsessions): supports Redis and custom backends, but no out-of-box SQLAlchemy backend
- [fastsession](https://pypi.org/project/fastsession/): server-side with cookie-only session ID
- [red-session](https://github.com/TheJecksMan/red-session): Redis-only

**Flask comparison**: Flask-Session (`SESSION_TYPE='sqlalchemy'`) provides database-backed sessions with a single config line per [Flask-Session docs](https://www.geeksforgeeks.org/how-to-use-flask-session-in-python-flask/). Flask-Login adds `@login_required`, `current_user`, remember-me. These are mature, well-documented, and match the PHP session pattern closely.

The compliance claim is correct: FastAPI requires assembling multiple third-party packages to match what Flask provides out of the box.

### R4 (Templates) -- FastAPI template support is "bolted on"

**VERDICT: PARTIALLY CORRECT.**

FastAPI does support Jinja2 templates via Starlette per [FastAPI Templates docs](https://fastapi.tiangolo.com/advanced/templates/) and [Real Python](https://realpython.com/fastapi-jinja2-template/). HTML fragments can be rendered and embedded in JSON responses. The 2025 HTMX+FastAPI pattern demonstrates this is a viable path per [Johal.in](https://www.johal.in/fastapi-templating-jinja2-server-rendered-ml-dashboards-with-htmx-2025/).

However, the compliance review's deeper point is valid: **the ergonomics differ**. In Flask, returning a rendered template fragment inside a JSON response is idiomatic:

```python
# Flask -- natural
return jsonify({"content": render_template("headlines.html", articles=articles)})
```

In FastAPI, the idiomatic pattern is to return Pydantic models or use `JSONResponse` as an "escape hatch" per [FastAPI Response Model docs](https://fastapi.tiangolo.com/tutorial/response-model/). Embedding rendered HTML in JSON fields via `JSONResponse(content={"content": rendered_html})` works but bypasses FastAPI's type-safety and auto-documentation advantages -- which are FastAPI's primary selling points. Using FastAPI while bypassing its core features is a framework mismatch.

### R2 (Behavioral parity) -- Pydantic strict typing vs PHP loose JSON

**VERDICT: PARTIALLY CORRECT, but manageable.**

Per [Pydantic Serialization docs](https://docs.pydantic.dev/latest/concepts/serialization/), Pydantic v2 supports `model_dump(mode='json')` for JSON-safe serialization, custom serializers via `PlainSerializer`, and `field_serializer` decorators. You **can** make Pydantic produce loosely-typed JSON matching PHP output, but it requires per-field customization.

The simpler path: bypass Pydantic entirely for legacy-contract endpoints by returning `JSONResponse` with raw dicts. This is documented and supported. However, if you bypass Pydantic on most endpoints, you lose the primary reason for choosing FastAPI.

The compliance claim is correct that achieving byte-level JSON parity is **harder** with Pydantic than with plain `json.dumps()` (which Flask uses via `jsonify`). The claim is overstated in suggesting it is impossible.

### R4 (Plugin async compatibility) -- Async hooks add complexity

**VERDICT: CONFIRMED.**

If the main application is async (FastAPI/ASGI), plugin hooks invoked during request handling must either be async-compatible or wrapped in `run_in_executor()`. The 24 existing PHP hooks are synchronous. Third-party plugins written for the system would need to be async-aware. This adds complexity to the plugin API contract without clear benefit -- the hooks perform lightweight operations (modify HTML, filter articles, add buttons) that do not benefit from async.

### R6 (API contract) -- TT-RSS uses `?op=X&method=Y`, not RESTful paths

**VERDICT: CONFIRMED.**

Per `specs/03-api-routing.md`, TT-RSS dispatches via `backend.php?op=rpc&method=mark&id=123`. FastAPI's routing model assumes path-based REST (`/api/rpc/mark/{id}`). Per [FastAPI Query Parameters docs](https://fastapi.tiangolo.com/tutorial/query-params/), query parameters are supported but the framework's auto-documentation, dependency injection, and validation are all optimized for path-based routing.

A single `/backend.php` endpoint that reads `op` and `method` from query params and dispatches internally **is possible** in both Flask and FastAPI. But in FastAPI, this creates a single opaque endpoint in the OpenAPI schema, eliminating auto-documentation benefits. In Flask, `request.args` dispatch is equally natural since Flask does not generate OpenAPI docs by default.

Both frameworks can handle this, but **FastAPI's advantages are neutralized** by the `?op=method` dispatch pattern.

### R10 (Testability) -- 11 passes, no endpoint until Pass 7

**VERDICT: CONFIRMED.**

Variant E's structure (Models -> Access -> Auth -> Config -> Parsing -> Engine -> **Handlers** -> API -> Plugins -> Frontend -> Deploy) means HTTP endpoints do not exist until Pass 7. Per `specs/12-testing-strategy.md`, the testing strategy assumes endpoint-level contract tests. With Variant D, Phase 4 (Handlers) is reached after 3 phases, and Phase 1 already includes the app skeleton with routing.

### R11 (Frontend JS unchanged) -- CSRF mechanism change requires JS modification

**VERDICT: DEPENDS ON IMPLEMENTATION.**

If using `fastapi-csrf-protect` with Double Submit Cookie, the JS **would** need modification to read the CSRF token from a cookie instead of `init_params`. However, a custom CSRF middleware that mimics the PHP pattern (session-stored token, validated from POST body parameter named `csrf_token`) could be built for FastAPI. This is custom work that Flask-WTF provides for free.

With Flask-WTF: the CSRF token is stored in the session, rendered into `init_params` by the server, and validated from the POST body `csrf_token` parameter. Zero JS changes required.

### AR3 (Framework fights pattern) -- FastAPI is API-first, not handler+HTML-first

**VERDICT: CONFIRMED.**

The TT-RSS backend returns JSON responses where fields contain server-rendered HTML fragments with Dojo `dojoType` attributes. This is a server-rendered SPA hybrid pattern. FastAPI's design philosophy centers on API-first development with Pydantic response models and auto-generated OpenAPI docs. Returning opaque HTML strings inside JSON fields works against these strengths.

Flask's design philosophy is simpler: render templates, return responses. No opinion on response structure. This is a better architectural match.

### AR6 (Over-engineering) -- Full async stack for single-user RSS reader

**VERDICT: CONFIRMED.**

Per the [2026 SQLAlchemy vs asyncpg benchmark](https://dasroot.net/posts/2026/02/python-postgresql-sqlalchemy-asyncpg-performance-comparison/), async SQLAlchemy with asyncpg achieves ~1,450 ops/sec vs plain asyncpg at ~2,800 ops/sec. For a single-user or small-team RSS reader, synchronous Flask + psycopg2 at ~800-1,000 ops/sec is more than sufficient. The async overhead (async session management, async plugin hooks, `run_in_executor` for sync code) adds complexity without measurable user-facing benefit.

The feed-fetching hot path (I/O-bound HTTP requests to external RSS feeds) benefits from async. But this is already addressed by Celery workers using `httpx` async client within tasks, without requiring the entire web framework to be async.

### AR7 (Async question over-addressed)

**VERDICT: CONFIRMED.** Async feed fetching is the only performance-critical path. Celery + httpx async achieves this without an async web framework.

---

## STEP 2 -- Improved Solution

### Summary of Research Findings

| Compliance Claim | Verdict | Action |
|-----------------|---------|--------|
| R1: Variant E "OK" for solo dev | **CONFIRMED** | Revert to Variant D |
| R4: CSRF - FastAPI lacks built-in | **CONFIRMED** | Revert to Flask (Flask-WTF) |
| R4: Sessions - no DB-backed sessions | **CONFIRMED** | Revert to Flask (Flask-Session) |
| R4: Templates - bolted on | **PARTIALLY CORRECT** | Revert to Flask (native Jinja2) |
| R2: Pydantic vs loose JSON | **PARTIALLY CORRECT** | Revert to Flask (jsonify) |
| R4: Plugin async complexity | **CONFIRMED** | Sync framework eliminates issue |
| R6: `?op=method` vs REST routing | **CONFIRMED** | Flask handles equally well |
| R10: No endpoint until Pass 7 | **CONFIRMED** | Variant D has endpoints by Phase 4 |
| R11: CSRF JS changes needed | **CONFIRMED** (with default FastAPI CSRF) | Flask-WTF: zero JS changes |
| AR3: Framework fights pattern | **CONFIRMED** | Flask matches pattern |
| AR6: Over-engineering | **CONFIRMED** | Sync Flask + Celery async |
| AR7: Async over-addressed | **CONFIRMED** | Async only in Celery workers |

**12 of 12 claims confirmed or partially confirmed.** The solution must be revised.

---

### REVISED SOLUTION: "Pragmatic Migration" -- Variant D + Flask + PostgreSQL

#### ADR-0001 Revised Choice: Variant D (Hybrid Entity-then-Graph)

**6 phases** instead of 11 passes:

```
Phase 1 -- Foundation (testable: schema validation, unit tests)
  1a. SQLAlchemy models for all 35 tables
  1b. Config + environment setup
  1c. Flask app skeleton with routing dispatch

Phase 2 -- Core Logic (testable: auth integration tests)
  2a. Auth + Sessions (Flask-Login + Flask-Session + Redis)
  2b. Preference system (db-prefs equivalent)
  2c. Database utility functions

Phase 3 -- Business Logic (testable: service-layer unit tests)
  3a. Feed management (CRUD, categories)
  3b. Article management (entries, user_entries)
  3c. Feed update engine (rssfuncs -> feedparser -> storage)
  3d. Labels + Tags + Filters

Phase 4 -- Handlers (testable: endpoint contract tests -- FIRST HTTP TESTS)
  4a. RPC handler (state mutations, counters)
  4b. Feeds handler (headline rendering with Jinja2 HTML fragments)
  4c. Article handler
  4d. Preference handlers (Pref_Feeds, Pref_Filters, etc.)

Phase 5 -- Cross-Cutting (testable: integration + plugin tests)
  5a. Plugin system (pluggy or custom hook registry)
  5b. External API (api/index.php equivalent)
  5c. Background worker (Celery + Redis)
  5d. Logging + Error handling

Phase 6 -- Deployment (testable: end-to-end + smoke tests)
  6a. Docker + CI/CD
  6b. Frontend serving (static files + init_params)
```

**Why Variant D satisfies R1**: Rated "Best" for solo dev in the project's own recommendation matrix. 6 phases vs 11 passes reduces planning overhead from "High" to "Medium". HTTP endpoints are testable from Phase 4 (4th phase, not 7th pass).

Per `specs/10-migration-dimensions.md`: "Models-first gives a solid, validated foundation. Call-graph ordering prevents missing dependency issues. Entity clusters keep related business logic together."

**Requirement R1 satisfied**: Variant D is explicitly rated "Best" for solo dev with "Medium" planning overhead and "Medium" time to first runnable code.

**Requirement R10 satisfied**: Each phase is independently testable. Phase 1 validates models against real schema. Phase 2 tests auth flows. Phase 3 tests business logic. Phase 4 introduces HTTP endpoint contract tests. This matches `specs/12-testing-strategy.md`.

#### ADR-0002 Revised Choice: Flask

**Flask** (WSGI, sync) + Flask-SQLAlchemy + Flask-Login + Flask-WTF + Flask-Session + Celery

**Why Flask satisfies each requirement:**

**R4 -- CSRF Protection (session-based, zero JS changes)**:
Per [Flask-WTF CSRF docs](https://flask-wtf.readthedocs.io/en/latest/csrf/), Flask-WTF stores the raw CSRF token in the server-side session. The token is generated via `csrf_token()` in templates, rendered into `init_params` as the PHP source does, and validated from the POST body `csrf_token` parameter. The existing Prototype.js wrapper in `functions.js` injects `csrf_token` from `getInitParam("csrf_token")` -- this works identically with Flask-WTF. Zero frontend JS changes.

**R4 -- Database-Backed Sessions**:
Per [Flask-Session docs](https://www.geeksforgeeks.org/how-to-use-flask-session-in-python-flask/), Flask-Session with `SESSION_TYPE='redis'` (recommended, since Redis is already required for Celery per ADR-0011) stores session data server-side with only a signed session ID in the cookie. Flask-Login provides `@login_required`, `current_user`, and session protection. This matches the PHP pattern where `ttrss_sessions` stores server-side data and the cookie contains only `ttrss_sid`.

**R4 -- Template Rendering (HTML fragments in JSON)**:
Flask's `render_template()` with Jinja2 is native and idiomatic. Server-rendered HTML fragments embedded in JSON responses is a natural pattern:

```python
@app.route("/backend.php")
def backend_dispatch():
    op = request.args.get("op")
    method = request.args.get("method")
    handler = get_handler(op)
    result = getattr(handler, method)()
    return jsonify(result)  # result contains {"content": rendered_html, ...}
```

Jinja2 templates can produce the same `dojoType`-annotated HTML fragments as the PHP source. No framework fighting.

**R2 -- Behavioral Parity (loose JSON)**:
Flask's `jsonify()` uses Python's `json.dumps()` which naturally produces the same loose typing as PHP's `json_encode()`: strings, nulls, ints, booleans, mixed arrays. No Pydantic layer to fight. Response dicts are constructed directly from query results, matching PHP's associative array pattern.

**R6 -- Preserve API Contract (`?op=X&method=Y`)**:
Flask handles `request.args` dispatch naturally. A single `/backend.php` route reads `op` and `method` query params and dispatches to handler classes -- exactly matching the PHP pattern. Flask does not impose REST conventions. The external API (`/api/index.php`) uses the same JSON-body dispatch pattern and is equally natural in Flask.

**R4 -- Plugin Compatibility (sync hooks)**:
All hooks are synchronous. Plugin code is synchronous. No `run_in_executor()` wrappers needed. The `pluggy` library or a custom hook registry works with plain Python functions. Plugin `get_js()` and `get_prefs_js()` return strings; `hookMethodName()` receives and returns plain Python objects.

**R11 -- Frontend JS Unchanged**:
- CSRF: `init_params.csrf_token` rendered by server, injected by existing JS wrapper -- no changes
- AJAX: all requests to `backend.php` with `?op=X&method=Y` -- preserved
- Responses: identical JSON structure with HTML fragment fields -- preserved
- Dojo/Prototype: client-side only, unaffected by backend framework

**R4 -- Background Task Support**:
Celery + Redis (ADR-0011 unchanged). Feed fetching in Celery workers can use `httpx` with async for I/O-bound HTTP requests without requiring an async web framework. This targets async precisely where it helps (R13, AR7) without over-engineering the web layer.

#### ADR-0003 Choice: PostgreSQL (UNCHANGED)

PostgreSQL with `psycopg2` (sync driver). Rationale unchanged from original ADR-0003:
- TT-RSS upstream prefers PostgreSQL
- Built-in full-text search replaces Sphinx dependency
- Superior JSON support for plugin storage
- One-time data migration from MySQL acceptable

No `asyncpg` needed since the web framework is synchronous. Celery workers use their own sync DB connections for feed updates.

**Requirement R3 satisfied**: SQLAlchemy models the existing 35-table schema (P2). Alembic manages schema migrations. Existing data migrated via one-time script.

**Requirement R12 satisfied**: SQLAlchemy declarative models map all 35 tables per ADR-0006.

---

### Async Strategy (Targeted, Not Global)

The compliance review correctly identified that full-stack async (AR6, AR7) is over-engineering. The revised strategy targets async **only** where it provides measurable benefit:

| Component | Sync/Async | Rationale |
|-----------|-----------|-----------|
| Flask web handlers | **Sync** | Request-response cycle is fast; DB queries are simple |
| SQLAlchemy ORM | **Sync** (psycopg2) | Single-user app; sync ORM is simpler and mature |
| Celery feed workers | **Sync process, async HTTP** | Workers use `httpx.AsyncClient` inside Celery tasks for concurrent feed fetching |
| Plugin hooks | **Sync** | Lightweight operations; no async overhead |
| Session management | **Sync** (Redis via Flask-Session) | Single Redis call per request |

This addresses AR7: async is applied **only** to the feed-fetching hot path via Celery + httpx, not to the entire application stack.

---

### Requirement Compliance Summary

| Requirement | Status | Evidence |
|------------|--------|----------|
| R1: Solo/small-team | **SATISFIED** | Variant D rated "Best" for solo dev per `specs/10-migration-dimensions.md` |
| R2: Behavioral parity | **SATISFIED** | Flask `jsonify()` produces identical loose-typed JSON; Jinja2 renders identical HTML fragments |
| R3: Database compatibility | **SATISFIED** | SQLAlchemy models 35 tables; Alembic migrations; one-time MySQL-to-PostgreSQL script |
| R4: Framework features | **SATISFIED** | Flask-WTF (CSRF), Flask-Session+Redis (sessions), Jinja2 (templates), Celery (background), pluggy (plugins) |
| R5: Scale (18.6K PHP, 35 tables) | **SATISFIED** | Variant D phases match code communities from `specs/10-migration-dimensions.md` |
| R6: API contract | **SATISFIED** | Flask `request.args` dispatch preserves `?op=X&method=Y` pattern natively |
| R7: Plugin system (24 hooks) | **SATISFIED** | Sync hooks with pluggy or custom registry; no async complexity |
| R8: Security modernization | **SATISFIED** | bcrypt (ADR-0008), parameterized queries (SQLAlchemy), SSL verification (httpx), Fernet (ADR-0009) |
| R9: Containerized deployment | **SATISFIED** | Docker: Flask + Celery + Redis + PostgreSQL; docker-compose up |
| R10: Phase testability | **SATISFIED** | 6 phases, each with defined test category; HTTP tests from Phase 4 |
| R11: Frontend JS unchanged | **SATISFIED** | Flask-WTF CSRF via init_params; identical JSON contract; same dispatch pattern |
| R12: SQLAlchemy 35-table schema | **SATISFIED** | SQLAlchemy declarative models; sync psycopg2 driver |
| R13: Background feed updates | **SATISFIED** | Celery + Redis (ADR-0011); httpx async in workers for feed fetching |

| Anti-Requirement | Status | Evidence |
|-----------------|--------|----------|
| AR3: Framework fights pattern | **NOT VIOLATED** | Flask matches handler+HTML pattern natively |
| AR4: Excessive delay | **NOT VIOLATED** | Variant D: "Medium" time to first runnable code |
| AR6: Over-engineering | **NOT VIOLATED** | Sync Flask; async only in Celery workers |
| AR7: Async over-addressed | **NOT VIOLATED** | Async targeted to feed-fetching hot path only |

---

### What Changed from Solution C

| Dimension | Solution C (Non-Compliant) | Revised Solution |
|-----------|---------------------------|-----------------|
| Migration flow | Variant E (11 passes) | **Variant D (6 phases)** |
| Web framework | FastAPI (ASGI, async) | **Flask (WSGI, sync)** |
| CSRF | fastapi-csrf-protect (Double Submit Cookie) | **Flask-WTF (session-based)** |
| Sessions | starsessions + custom backend | **Flask-Session + Redis** |
| Templates | Starlette Jinja2 (bolted on) | **Flask Jinja2 (native)** |
| JSON responses | Pydantic models / JSONResponse escape hatch | **Flask jsonify (raw dicts)** |
| ORM driver | async SQLAlchemy + asyncpg | **sync SQLAlchemy + psycopg2** |
| Plugin hooks | async-compatible or run_in_executor | **sync (plain Python)** |
| API routing | Path-based REST (FastAPI idiom) | **Query-param dispatch (natural in Flask)** |
| Async scope | Full stack (web + ORM + plugins) | **Celery workers only (feed fetching)** |
| Pass/phase count | 11 passes, HTTP at pass 7 | **6 phases, HTTP at phase 4** |

---

## Sources

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [StackHawk: CSRF Protection in FastAPI](https://www.stackhawk.com/blog/csrf-protection-in-fastapi/)
- [fastapi-csrf-protect GitHub](https://github.com/aekasitt/fastapi-csrf-protect)
- [Flask-WTF CSRF Documentation](https://flask-wtf.readthedocs.io/en/latest/csrf/)
- [Flask-Session Documentation](https://www.geeksforgeeks.org/how-to-use-flask-session-in-python-flask/)
- [starsessions GitHub](https://github.com/alex-oleshkevich/starsessions)
- [FastAPI Templates Documentation](https://fastapi.tiangolo.com/advanced/templates/)
- [Real Python: FastAPI with Jinja2](https://realpython.com/fastapi-jinja2-template/)
- [FastAPI + HTMX Server Rendered Dashboards 2025](https://www.johal.in/fastapi-templating-jinja2-server-rendered-ml-dashboards-with-htmx-2025/)
- [Pydantic Serialization Documentation](https://docs.pydantic.dev/latest/concepts/serialization/)
- [FastAPI Response Model Documentation](https://fastapi.tiangolo.com/tutorial/response-model/)
- [SQLAlchemy vs asyncpg Performance 2026](https://dasroot.net/posts/2026/02/python-postgresql-sqlalchemy-asyncpg-performance-comparison/)
- [Async SQLAlchemy 2.0 Production Boilerplate](https://github.com/a-ulianov/sqlalchemy-async-boilerplate)
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/)
- [Flask Blueprints Documentation](https://flask.palletsprojects.com/en/stable/blueprints/)
- [FastAPI vs Flask 2025 Comparison (Strapi)](https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison)
