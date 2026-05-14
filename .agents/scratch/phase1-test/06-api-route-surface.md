# 06 — API Route Surface

**Dimension**: `api-route-surface`
**Derivation**: Cross-cutting — derived from call-graph communities GRP-01 (API, C0+C1),
class-hierarchy C1 (API, Handler, Backend, Handler_Public), and hook-graph C3
(HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_API)
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The API route surface captures every **inbound HTTP entry point** in TT-RSS —
the full set of operations exposed to external callers (JSON API clients,
mobile apps, third-party integrations) and to the browser SPA.

For the PHP → Python modernization this dimension:

- Defines the **Flask Blueprint + route skeleton** — one route per PHP entry
  point or `op` value
- Ensures **API contract preservation** — the JSON envelope format, `API_LEVEL`,
  response codes, and error strings must be byte-identical for existing clients
- Surfaces the **op-parameter dispatch anti-pattern** that must be replaced
  with explicit URL-per-operation routes in Flask
- Identifies **auth guards** per endpoint type (public vs. session-auth
  vs. token-auth)
- Seeds the divergence catalogue with `$_REQUEST` superglobal, method-string
  dispatch, and session-statefulness entries

---

## Graph structure (derived)

No separate JSON artifact — derived from call-graph (`call_graph.json`)
and include-graph (`include_graph.json`) communities.

| Entry point | PHP file | Handler class | Auth type |
|---|---|---|---|
| JSON API | `api/index.php` | `API extends Handler` | Session (login op bypasses) |
| Main UI AJAX | `backend.php` | `Backend extends Handler` | Session required |
| Public routes | `public.php` | `Handler_Public extends Handler` | None / access-key |
| Preferences page | `prefs.php` | (entry — delegates to Pref_*) | Session required |
| Main SPA | `index.php` | (entry — renders page shell) | Session required |
| OPML import/export | `opml.php` | `Opml extends Handler_Protected` | Session required |
| User registration | `register.php` | (entry) | None |
| Error page | `errors.php` | (entry) | None |
| Feed icon proxy | `image.php` | (entry) | None |

---

## JSON API operations (API_LEVEL = 8)

All operations POST/GET to `api/index.php` with `op` parameter.

| `op` value | Handler method | Auth required | Description |
|---|---|---|---|
| `login` | `API::login()` | None | Create session, return session_id |
| `logout` | `API::logout()` | Session | Destroy session |
| `isLoggedIn` | `API::isLoggedIn()` | None | Check session validity |
| `getVersion` | `API::getVersion()` | Session | Return VERSION string |
| `getApiLevel` | `API::getApiLevel()` | Session | Return API_LEVEL = 8 |
| `getFeeds` | `API::getFeeds()` | Session | Feed list with unread counts |
| `getCategories` | `API::getCategories()` | Session | Category tree |
| `getHeadlines` | `API::getHeadlines()` | Session | Article list (filtered) |
| `getArticle` | `API::getArticle()` | Session | Article content by ID(s) |
| `getConfig` | `API::getConfig()` | Session | Server config values |
| `updateFeed` | `API::updateFeed()` | Session | Trigger feed update |
| `updateArticle` | `API::updateArticle()` | Session | Set unread/starred/published/note |
| `getArticle` | `API::getArticle()` | Session | Article body + metadata |
| `getUnread` | `API::getUnread()` | Session | Total unread count |
| `getCounters` | `API::getCounters()` | Session | Per-feed unread counters |
| `subscribeToFeed` | `API::subscribeToFeed()` | Session | Add feed subscription |
| `unsubscribeFeed` | `API::unsubscribeFeed()` | Session | Remove feed subscription |
| `getFeedTree` | `API::getFeedTree()` | Session | Full feed+category tree (BFS) |
| `getLabels` | `API::getLabels()` | Session | User label list |
| `setArticleLabel` | `API::setArticleLabel()` | Session | Assign/remove label |
| `shareToPublished` | `API::shareToPublished()` | Session | Publish article to public feed |
| `catchupFeed` | `API::catchupFeed()` | Session | Mark feed/category as read |
| `getPref` | `API::getPref()` | Session | Read single user preference |
| `markAllFeeds` | `API::markAllFeeds()` | Session | Mark all feeds as read |

**Plugin-contributed API methods**: plugins can register additional op values
via `PluginHost::add_api_method($name, $sender)`. These are dispatched from
`API` class after the built-in ops are checked.
Source: `source-repos/ttrss-php/ttrss/classes/api.php`

---

## JSON response envelope (must be preserved byte-identical)

```json
{
  "seq": <int>,      // client-supplied sequence number, echoed back
  "status": 0 | 1,  // 0 = OK, 1 = ERR
  "content": { ... } // operation-specific payload
}
```

Constants:
- `API::STATUS_OK = 0` (`source-repos/ttrss-php/ttrss/classes/api.php:7`)
- `API::STATUS_ERR = 1` (`source-repos/ttrss-php/ttrss/classes/api.php:8`)
- `API::API_LEVEL = 8` (`source-repos/ttrss-php/ttrss/classes/api.php:5`)

Error strings (must be preserved for client compatibility):
- `NOT_LOGGED_IN` — session check failed (line 16)
- `API_DISABLED` — user pref ENABLE_API_ACCESS is false (line 22)
- `INCORRECT_USAGE` — wrong parameters
- `LOGIN_ERROR` — bad credentials
- `FEED_NOT_FOUND`, `CATEGORY_NOT_FOUND` — resource errors

---

## Backend AJAX operations (UI path)

`backend.php` dispatches to `Backend::*()` methods.
Representative ops (not exhaustive — derived from `classes/backend.php`
and `classes/rpc.php`):

| `op` | Handler | Description |
|---|---|---|
| `feeds` | `Feeds::view()` | Headline list HTML + counters |
| `rpc` | `RPC::*()` | Mark read, star, publish, get-article |
| `prefs` | `Pref_*::*()` | Preference CRUD AJAX |
| `dlg` | `Dlg::*()` | Dialog content rendering |
| `article` | `Article::*()` | Article edit (tags, note) |
| `opml` | `Opml::*()` | OPML import/export |
| `backend` | `Backend::*()` | Misc (digest test, help) |
| `pluginhandler` | `PluginHandler::*()` | Plugin-registered AJAX endpoints |

---

## Public routes (unauthenticated)

`public.php` → `Handler_Public::$op()`:

| `op` | Description | Auth |
|---|---|---|
| `rss` | Syndicated feed via access key (`key` param) | Access key (ttrss_access_keys) |
| `subscribe` | Bookmarklet feed subscription | None (form submit) |
| `forgotpass` | Password reset request | None |
| `globalUpdateFeeds` | Trigger feed update (SIMPLE_UPDATE_MODE) | None (config-gated) |
| `housekeeping` | Trigger housekeeping tasks | None (config-gated) |
| `generateFeedKey` | Generate RSS access key for user | Session |

Source: `source-repos/ttrss-php/ttrss/classes/handler/public.php`

---

## Auth guard types

| Guard type | PHP implementation | Python equivalent |
|---|---|---|
| **Session auth** | `API::before()` checks `$_SESSION["uid"]` | `@login_required` (Flask-Login) |
| **Handler_Protected** | `Handler_Protected` abstract base, all subclasses | Blueprint `before_request` + `@login_required` |
| **Access key auth** | `ttrss_access_keys` table lookup by `key` param | `verify_token(key)` function + `@token_required` decorator |
| **No auth** | Entry points reachable without session | No decorator (Flask default) |
| **Admin check** | `$_SESSION["access_level"] >= 10` check | `User.access_level >= 10` custom decorator |
| **API_DISABLED** | `get_pref('ENABLE_API_ACCESS')` per-user check | Custom `@api_access_required` decorator |

---

## Dependency levels (migration order)

| Level | What to port | Rationale |
|---|---|---|
| 0 (first) | JSON envelope helper, auth guards, `before()` equivalent | All routes depend on these |
| 1 | Login / logout / isLoggedIn ops | No business logic dependencies |
| 2 | `getVersion`, `getApiLevel`, `getConfig` | Read-only, no complex queries |
| 3 | `getFeeds`, `getCategories`, `getCounters`, `getUnread` | Requires Feed + Counter models |
| 4 | `getHeadlines`, `getArticle` (read paths) | Requires UserEntry, Entry models + filter logic |
| 5 | `updateArticle`, `catchupFeed`, `markAllFeeds` (write paths) | Requires write + ccache invalidation |
| 6 | `subscribeToFeed`, `unsubscribeFeed`, `getFeedTree` | Requires Feed management + BFS tree walk |
| 7 (last) | Plugin-contributed API methods | Requires pluggy machinery |

---

## Modernization impact

### Forced adaptations

1. **`op`-parameter dispatch → URL-per-route**:
   PHP uses a single endpoint (`api/index.php`, `backend.php`) with an `op`
   parameter to select the operation. Flask must map each `op` to an explicit
   route or Blueprint view function. All `op` values must be enumerated and
   mapped — no dynamic dispatch by string reflection (security requirement).
   Frequency: every API call. Severity: HIGH (completeness risk).

2. **`$_REQUEST` superglobal → `flask.request`**:
   PHP merges GET + POST + COOKIE in `$_REQUEST`. Flask separates
   `request.form` (POST), `request.args` (GET), `request.cookies`.
   TT-RSS sends most ops via POST; some via GET.
   Each call site that reads from `$_REQUEST` must be audited.
   Source: ~47 occurrences in `classes/api.php` alone.
   Frequency: every request. Severity: MEDIUM.

3. **Session `seq` echo**:
   `API::wrap()` echoes `$_REQUEST['seq']` in every response.
   Flask: read from `request.form.get('seq', 0)` and include in `jsonify()`.
   Source: `source-repos/ttrss-php/ttrss/classes/api.php:38`
   Frequency: every API response. Severity: LOW.

4. **`API_LEVEL = 8` constant preservation**:
   Existing mobile clients (FeedMe, Reeder, Miniflux importer, etc.) call
   `getApiLevel` and may require >= 8. Must be preserved.
   Source: `source-repos/ttrss-php/ttrss/classes/api.php:5`
   Frequency: every new client connection. Severity: HIGH (client compatibility).

5. **`SINGLE_USER_MODE` login bypass**:
   `if (SINGLE_USER_MODE) $login = "admin"` in `API::login()`.
   Python target must honour `SINGLE_USER_MODE` config with equivalent bypass.
   Source: `source-repos/ttrss-php/ttrss/classes/api.php:57`
   Frequency: SINGLE_USER_MODE deployments only. Severity: LOW.

6. **Plugin-contributed API ops**:
   `PluginHost::add_api_method($name, $plugin)` registers new ops dynamically.
   Python target: plugins register Flask Blueprints with `/api/plugin/<name>/`
   route prefix, or a plugin-dispatch route is added to the API Blueprint.
   Source: `source-repos/ttrss-php/ttrss/classes/pluginhost.php`
   Frequency: per-plugin. Severity: MEDIUM.

---

## Divergences seeded

- D-AR-01: `$_REQUEST` superglobal merge (→ `12-semantic-discrepancies.md`)
- D-AR-02: Method-string dispatch security (→ `12-semantic-discrepancies.md`)
- D-AR-03: Session statefulness — login op creates PHP session, Python creates
  Flask-Login session. Token/session choice is an ADR item. (→ `12-semantic-discrepancies.md`)
- D-AR-04: `op` dispatch vs URL routing — completeness risk during migration.

---

## Source cross-references

| Construct | Source | Line(s) |
|---|---|---|
| `API::before()` auth guard | `source-repos/ttrss-php/ttrss/classes/api.php` | 12–30 |
| `API::wrap()` envelope | `source-repos/ttrss-php/ttrss/classes/api.php` | 35–39 |
| `API::login()` | `source-repos/ttrss-php/ttrss/classes/api.php` | 55–110 |
| `API::getHeadlines()` | `source-repos/ttrss-php/ttrss/classes/api.php` | ~400 |
| `API_LEVEL = 8` | `source-repos/ttrss-php/ttrss/classes/api.php` | 5 |
| `STATUS_OK / STATUS_ERR` | `source-repos/ttrss-php/ttrss/classes/api.php` | 7–8 |
| `Handler::handle()` dispatch | `source-repos/ttrss-php/ttrss/classes/handler.php` | full |
| `Handler_Public` operations | `source-repos/ttrss-php/ttrss/classes/handler/public.php` | full |
| Plugin API method registration | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | `add_api_method()` |
| Access key table | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | `create table ttrss_access_keys` |
| API entry point | `source-repos/ttrss-php/ttrss/api/index.php` | full |
| Backend entry point | `source-repos/ttrss-php/ttrss/backend.php` | full |
| Public entry point | `source-repos/ttrss-php/ttrss/public.php` | full |
