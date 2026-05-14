# Dimension: call-graph · Community: CG-1 — Core App / Handlers

## Members

Merged from: call-community-0 (175M), call-community-1 partial, include-community-0 (14M),
class-community-0 (13M), class-community-1 (4M), PluginHost singleton methods (comms 105–120),
Handler singleton methods (comms 84–96), Pref_* singleton methods (comms 120–131).

| File / Symbol | Level | Est. LOC | Role |
|---|---|---|---|
| `include/functions.php` | bootstrap | ~1 200 | Global function library — auth, dates, DB wrappers, purge, fetch |
| `include/functions2.php` | bootstrap | ~800 | Sanitize, feed helper functions |
| `classes/db.php` | level-0 | ~80 | DB singleton dispatcher + global wrapper fns |
| `include/db.php` | level-0 | ~30 | Procedural db_* function shims delegating to Db singleton |
| `classes/pluginhost.php` | level-1 | ~400 | Hook registry — 24 HOOK_* constants, add_hook, run_hooks |
| `classes/handler.php` | level-1 | ~60 | Abstract Handler base class (before/after/csrf_ignore) |
| `classes/handler/protected.php` | level-2 | ~30 | ProtectedHandler — requires authenticated session |
| `classes/backend.php` | level-2 | ~200 | Backend handler — main SPA AJAX dispatcher (op= routing) |
| `classes/api.php` | level-2 | ~600 | JSON API class — 20+ methods |
| `classes/feeds.php` | level-2 | ~800 | Feeds handler — view, format_headlines_list, generate_*_feed |
| `classes/rpc.php` | level-2 | ~400 | RPC handler — article mark/score/tag, counter updates |
| `classes/article.php` | level-2 | ~300 | Article handler — create_published, label ops, CSRF |
| `classes/pref/feeds.php` | level-3 | ~600 | Prefs: feed management CRUD |
| `classes/pref/filters.php` | level-3 | ~400 | Prefs: filter rule CRUD |
| `classes/pref/labels.php` | level-3 | ~200 | Prefs: label CRUD |
| `classes/pref/prefs.php` | level-3 | ~300 | Prefs: user preferences CRUD |
| `classes/pref/system.php` | level-3 | ~150 | Prefs: system/admin tab |
| `classes/pref/users.php` | level-3 | ~300 | Prefs: user management (admin only) |
| `classes/pluginhandler.php` | level-3 | ~50 | PluginHandler — dispatches to loaded plugin methods |
| `classes/dlg.php` | level-3 | ~300 | Dialog snippets (tag cloud, feed select, pubOPML) |
| `backend.php` | entry | ~100 | Front-controller: instantiates handler class from op= param |
| `index.php` | entry | ~120 | SPA shell: login_sequence() → Dojo bootstrap HTML |
| `prefs.php` | entry | ~50 | Preferences page entry |

---

## Representative constructs

### Dispatch pattern (backend.php)

```php
// backend.php — hand-rolled front controller
$op = $_REQUEST["op"];
$method = $_REQUEST["method"];
// op maps to class name; method maps to method name
$handler = new $op();
if ($handler instanceof Handler) {
    $handler->before($method);
    $handler->$method();
    $handler->after($method);
}
```

### CSRF guard (Handler base class)

```php
// classes/handler.php
function before($method) {
    if (!$this->csrf_ignore($method)) {
        if (!validate_csrf($_REQUEST["csrf_token"])) {
            die("CSRF check failed.");
        }
    }
}
```

### PluginHost singleton + hook invocation

```php
// classes/pluginhost.php
static function getInstance() {
    if (self::$instance == null) {
        self::$instance = new self();
    }
    return self::$instance;
}

function run_hooks($hook, &$params) {
    foreach ($this->hooks[$hook] as $hook_obj) {
        $hook_obj->hook_method($params);  // by reference
    }
}
```

### Session auth check (include/functions.php)

```php
function login_sequence() {
    if (SINGLE_USER_MODE) {
        // auto-login as admin user id=1
        authenticate_user("admin", null);
        return;
    }
    if (!$_SESSION["uid"]) {
        // show login form or redirect
    }
}
```

---

## Research findings

**[TRAINING — no web search available this session]**

### PHP front-controller dispatch (op= pattern)

- TT-RSS's `op=ClassName&method=methodName` pattern is a minimal hand-rolled
  dispatcher equivalent to an MVC front controller.
- PHP class name lookup (`new $op()`) means any public class in the autoload
  path is reachable — an attack surface if `op=` is not allowlisted.
- `Handler::before()` CSRF check provides the security gate.
- No URL routing library used; the dispatcher is entirely procedural.

### Handler hierarchy

```
Handler (abstract — before/after/csrf_ignore)
  └─ Handler_Protected (requires $_SESSION['uid'])
       └─ Article, Feeds, Opml, Dlg, RPC, Backend
            └─ Pref_Feeds, Pref_Filters, Pref_Labels, Pref_Prefs, Pref_System, Pref_Users
  └─ Handler_Public (no auth)
       └─ API (session-key auth)
  └─ PluginHandler (delegates to plugin instance)
```

- `Handler_Protected::before()` calls `Handler::before()` then checks
  `$_SESSION['uid']` — fails with JSON error if not set.
- `API::before()` uses a different auth mechanism: `sid` (session key from
  `ttrss_access_keys` or `$_SESSION`) rather than `$_SESSION['uid']` directly.

### Global function shims

- `include/db.php` defines global functions `db_query()`, `db_fetch_assoc()`,
  `db_num_rows()`, etc. These are thin wrappers calling `Db::get()->method()`.
- These exist so procedural include files (`functions.php`, `ccache.php`,
  `rssfuncs.php`) can call DB without explicit object references.
- ~200+ call sites use these global shims.

---

## Target-side mapping

| PHP construct | Python / Flask equivalent |
|---|---|
| `backend.php` dispatch (`op=`, `method=`) | Flask Blueprint per handler group: `@backend.route('/backend/<op>/<method>')` or POST-based JSON dispatch |
| `Handler` base class | Python ABC `Handler` with `@abstractmethod before(method)` |
| `Handler_Protected` | Flask-Login `@login_required` decorator on all handler views |
| `CSRF validate_csrf()` | Flask-WTF `CSRFProtect` extension; `{{ csrf_token() }}` in Jinja2 |
| `PluginHost::getInstance()` | Module-level `plugin_host` singleton or Flask `current_app.plugin_host` |
| `PluginHost::run_hooks($hook, &$param)` | `pluggy.PluginManager.hook.hookspec_name(param=val)` — returns list of results |
| `$_SESSION['uid']` | `flask_login.current_user.id` |
| `SINGLE_USER_MODE` | Application config flag; bypass `@login_required` and set `current_user` to admin |
| `db_query()` / global DB shims | SQLAlchemy `db.session.execute()` or ORM calls via `current_app.db` |
| `Pref_*` handler classes | Flask Blueprints under `/prefs/` — one Blueprint per pref section |

### Handler class → Flask Blueprint mapping

```python
# Python equivalent of backend.php dispatch
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

backend_bp = Blueprint('backend', __name__, url_prefix='/backend')

class FeedsHandler:
    @backend_bp.route('/feeds/<method>', methods=['POST'])
    @login_required
    def dispatch(method):
        handler = FeedsHandler()
        return getattr(handler, method)()
```

---

## Divergences spotted

### D-CG1-01: op= string-based dispatch → allowlist required

- **Source**: `backend.php` — `new $op()` is unchecked class instantiation.
- **Target gotcha**: Flask routing is declarative — no dynamic class lookup.
  The allowlist enforcement becomes the route registration itself.
- **Frequency**: Every HTTP request to backend.php.
- **Severity**: MEDIUM — security improvement in target.

### D-CG1-02: Handler::before() reference-param hooks

- **Source**: `run_hooks($hook, &$param)` — PHP passes by reference;
  plugins mutate `$param` in-place.
- **Target gotcha**: Python has no pass-by-reference for scalars;
  pluggy returns new values rather than mutating. Hook callers must
  reassign the return value, not assume in-place mutation.
- **Frequency**: All 24 hooks; critical for HOOK_SANITIZE (sanitize pipeline).
- **Severity**: HIGH — behaviour divergence if not handled.

### D-CG1-03: SINGLE_USER_MODE special paths

- **Source**: `if (SINGLE_USER_MODE) authenticate_user("admin", null)` —
  bypasses all authentication.
- **Target gotcha**: Flask-Login has no built-in SINGLE_USER_MODE.
  Must implement as a custom `LoginManager.request_loader` that
  auto-loads user id=1 when the config flag is set.
- **Frequency**: Every request if enabled.
- **Severity**: MEDIUM — must preserve for existing installs.

### D-CG1-04: $_SESSION global access vs current_user proxy

- **Source**: `$_SESSION['uid']`, `$_SESSION['name']`, `$_SESSION['access_level']`
  accessed directly throughout all handler methods and include functions.
- **Target gotcha**: Every access site must be replaced with
  `current_user.id`, `current_user.login`, `current_user.access_level`.
  ~80+ replacement sites.
- **Frequency**: Very high.
- **Severity**: HIGH — mechanical but voluminous.

### D-CG1-05: Access level integer (0=user, 10=admin)

- **Source**: `ttrss_users.access_level` — integer, 0=regular, 10=admin.
  Checked inline: `if ($_SESSION['access_level'] >= 10)`.
- **Target gotcha**: Flask-Login has no built-in role system.
  Must implement custom `@requires_admin` decorator.
- **Frequency**: ~15 admin-only handler methods.
- **Severity**: LOW — straightforward to implement.

---

## Open questions (Phase 2 ADR items)

1. Should `backend.php` dispatch become a single `/api/backend` JSON endpoint
   (keeping op= semantics) or be decomposed into RESTful Flask routes?
   Current frontend JS uses `op=<Class>&method=<fn>` — REST decomposition
   requires frontend changes too.

2. How should PluginHandler dispatch work in Flask?
   Plugin methods are currently called by the same `op=PluginHandler`
   front-controller path — do we preserve this or route plugins differently?

3. CSRF strategy: Flask-WTF (form-based tokens) vs custom token
   (TT-RSS uses a JSON/AJAX context, not form POST)?
   Flask-WTF supports both; AJAX token via `X-CSRFToken` header is cleaner.

4. Should Pref_* handlers become a separate Flask Blueprint (`/prefs/`)
   or stay co-located under the backend Blueprint?
