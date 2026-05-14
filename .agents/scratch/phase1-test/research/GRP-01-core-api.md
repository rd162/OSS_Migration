# Dimension: call-graph + class-hierarchy + include-graph · Community: GRP-01 — Core API subsystem

⚠ RESEARCH MODE: DEGRADED — web search unavailable; training-knowledge-only.
All findings from source corpus reads + training knowledge. No T1 URL citations.

---

## Members

### Primary files
- `classes/api.php` (level 1, ~792 LOC) — main API dispatch class
- `api/index.php` (level 1, ~30 LOC) — HTTP entry point for API
- `classes/handler.php` (level 0, ~80 LOC) — Handler base class
- `classes/backend.php` (level 0, ~120 LOC) — Backend handler (UI AJAX)
- `classes/handler/public.php` (level 1, ~1006 LOC) — public-facing handler
- `classes/rpc.php` (level 1, ~654 LOC) — RPC handler (UI operations)

### Call communities merged into GRP-01
- call C0 (175 nodes): API::wrap, API::getVersion, API::getApiLevel, API::login,
  API::isLoggedIn, API::getFeeds, API::getCategories, API::getHeadlines,
  API::getArticle, API::getConfig, API::updateFeed, API::logout, ...
- call C1 (107 nodes): API::getUnread, API::getCounters, API::getLabels,
  API::setArticleLabel, API::api_get_feeds, API::subscribeToFeed,
  API::unsubscribeFeed, API::getFeedTree, ...

### Class community
- class C1 (4 nodes): API, Handler, Backend, Handler_Public

### Hook community
- hook C3 (4 nodes): HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_API,
  classes/api.php, classes/pref/filters.php

---

## Representative constructs

- `API::wrap($status, $reply)` — JSON envelope emitter
  (`source-repos/ttrss-php/ttrss/classes/api.php:36`)
- `API::before($method)` — pre-dispatch auth guard
  (`source-repos/ttrss-php/ttrss/classes/api.php:12`)
- `API::login()` — session creation + password check
  (`source-repos/ttrss-php/ttrss/classes/api.php:55`)
- `Handler::before($method)` — base pre-dispatch hook
  (`source-repos/ttrss-php/ttrss/classes/handler.php`)
- `PluginHost->run_hooks(HOOK_QUERY_HEADLINES, ...)` — query extension point
  (`source-repos/ttrss-php/ttrss/classes/api.php:648`)
- `PluginHost->run_hooks(HOOK_RENDER_ARTICLE_API, ...)` — render extension point
  (`source-repos/ttrss-php/ttrss/classes/api.php:712`)
- `const API_LEVEL = 8` — version contract constant
  (`source-repos/ttrss-php/ttrss/classes/api.php:5`)

---

## Research findings (training-knowledge-only — DEGRADED)

### TT-RSS API protocol
- JSON-over-HTTP, single endpoint `/api/` with `op` parameter selecting operation.
- Stateful: requires `login` call first; session maintained via PHP native sessions
  stored in `ttrss_sessions` DB table.
- Response envelope: `{"seq": N, "status": 0|1, "content": {...}}`.
- `seq` field echoes client's sequence number for multi-request correlation.
- API_LEVEL 8 = version discriminator clients check via `getApiLevel`.
- ENABLE_API_ACCESS user preference gates access — opt-in per user.
- SINGLE_USER_MODE bypasses login, hardcodes `admin` user.

### Handler dispatch pattern
- PHP does not have a framework router; dispatch is method-based:
  `api/index.php` → `Handler::handle()` → `$handler->$method($args)`.
- `before($method)` is a pre-dispatch hook — auth check, content-type set.
- No URL routing table; the `op` POST/GET parameter maps directly to PHP methods.
- `PluginHost` can add `api_methods` that extend the method dispatch.

### Auth guard behaviour
- `API::before()` checks `$_SESSION["uid"]` — session-based auth.
- `login` and `isloggedin` are the only ops that bypass the session check.
- Password check uses SHA1-family hash stored in `ttrss_users.pwd_hash`
  (discovered from sessions.php + auth/base.php pattern).
- No CSRF token on API — relies on same-origin + session cookie.

### Known PHP → Python divergences (training knowledge)
- PHP sessions → Flask-Login / JWT: stateful session semantics must be
  preserved or explicitly redesigned (TT-RSS apps rely on session continuity).
- Method dispatch via string → Python view functions / class-based views:
  the `op` → method pattern can map to Flask route dispatch or a dict dispatch.
- `$_REQUEST` superglobal → `flask.request.form / .args / .json`:
  TT-RSS merges GET+POST; Flask separates them — consolidation needed.
- `json_encode()` → `flask.jsonify()`: near-equivalent but Flask sets
  Content-Type automatically; PHP sets it manually (`header()`).
- `before($method)` pattern → Flask `@before_request` or Blueprint
  `before_request` decorator — semantically equivalent.

---

## Target-side mapping

| PHP construct | Python/Flask equivalent | Notes |
|---|---|---|
| `api/index.php` entry point | Blueprint route `POST /api/` | Single endpoint, `op` dispatch |
| `API::before()` auth guard | `@login_required` or `before_request` | Must handle API_DISABLED check |
| `API::wrap()` envelope | `jsonify({"seq":..., "status":..., "content":...})` | Identical shape |
| `$_SESSION["uid"]` | `flask_login.current_user.id` | Session → Login user |
| `API_LEVEL = 8` | Class constant or config | Preserve value |
| HOOK_QUERY_HEADLINES | pluggy hookspec `query_headlines` | Same semantics |
| HOOK_RENDER_ARTICLE_API | pluggy hookspec `render_article_api` | Same semantics |
| Method dispatch on `op` | `dispatch_table = {"getFeeds": get_feeds, ...}` | Dict-based or Blueprint routes |

---

## Divergences spotted

1. **Session statefulness**: PHP API is session-based; Python modernization
   must decide session (Flask-Login + Redis) vs. token (JWT) — impacts all
   API clients. Frequency: every API call. High impact.

2. **`$_REQUEST` merge**: TT-RSS reads from `$_REQUEST` which merges
   `$_GET`, `$_POST`, `$_COOKIE`. Flask splits these. Grep count:
   ~47 occurrences of `$_REQUEST` in classes/api.php alone. Medium impact.

3. **Method-name dispatch**: PHP reflection dispatch (`$handler->$method`)
   is dynamic; Python must explicitly enumerate valid operations to avoid
   security issues. All operations must be whitelisted. Medium impact.

4. **Password hashing on login**: `classes/api.php:login()` builds raw SQL
   with `$dbh->escape_string()` — SQL injection risk + SHA1 hash.
   Python target must use parameterised queries + argon2id. High security impact.

5. **SINGLE_USER_MODE**: hardcodes `$login = "admin"` — must be preserved
   as a config option in Python. Low complexity, high compat impact.

6. **seq field**: client sends sequence number; API echoes it. Flask has
   no built-in seq tracking — must implement in view. Low complexity.

---

## Open questions

1. Should the Python API preserve the same JSON envelope exactly
   (for client compatibility) or version-bump to a cleaner shape?
2. Token vs. session auth — ADR needed before implementing login().
3. How do existing TT-RSS Android/iOS clients use API_LEVEL?
   (Determines whether we can change API_LEVEL.)
4. HOOK_QUERY_HEADLINES modifies SQL — how does this translate to
   SQLAlchemy ORM queries? (May require raw-SQL escape hatch.)
