# 03 — Class Hierarchy

**Dimension**: `class-hierarchy`
**Artifact**: `tools/graph_analysis/output/class_graph.json`
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The class hierarchy graph captures **`extends`** and **`implements`** directed
edges between PHP classes, abstract classes, and interfaces.
Each node is a class or interface name; each edge is an inheritance or
implementation relationship.

For the PHP → Python modernization this dimension:

- Defines the **Python class skeleton** — which classes become Python classes,
  which become ABCs, which become protocols
- Surfaces **template-method patterns** (abstract base + concrete subclasses)
  that Python must preserve for plugin compatibility
- Identifies **interface contracts** (`IDb`, `IHandler`, `IAuthModule`) that
  become Python Protocols or ABCs
- Reveals **single-inheritance chains** that translate cleanly vs.
  **multiple-interface** patterns that require Protocol composition in Python
- Exposes **third-party class hierarchies** that should be replaced wholesale

---

## Graph structure

| Metric | Value |
|---|---|
| Nodes (classes + interfaces) | 81 |
| Edges (extends + implements) | 27 |
| Raw Leiden communities | 55 |
| Grouped research passes (∆5) | 5 |
| Isolated singletons (size = 1) | 46 |
| Artifact | `tools/graph_analysis/output/class_graph.json` |

Node labels are bare class/interface names as declared in PHP source.
Edge type is recorded in the JSON: `{"from": "Child", "to": "Parent", "kind": "extends|implements"}`.

The graph is sparse (density ≈ 0.004) because PHP uses single inheritance;
most classes extend exactly one parent or implement one interface.

---

## Communities (after ∆5 grouping — 5 research groups)

### C0 — Handler hierarchy: protected handlers (13 nodes)

**Members**:
`Article`, `Handler_Protected`, `Dlg`, `Feeds`, `Opml`,
`PluginHandler`, `Pref_Feeds`, `Pref_Filters`, `Pref_Labels`,
`Pref_Prefs`, `Pref_System`, `Pref_Users`, `RPC`

**Characterisation**:
The authenticated handler subtree.
`Handler_Protected` extends `Handler` and adds a session-auth guard.
All application-level handlers extend `Handler_Protected`:
`Feeds`, `Article`, `Dlg`, `Opml`, `RPC` are the main UI operation handlers;
`Pref_*` are the preferences pane handlers;
`PluginHandler` dispatches to plugin-registered AJAX endpoints.

**Inheritance chain**:
```
IHandler (interface)
  └─ Handler (abstract base)
       └─ Handler_Protected
            ├─ Article     (article display + tagging ops)
            ├─ Backend     (see C1 — Backend extends Handler directly)
            ├─ Dlg         (dialog boxes: OPML import, new version)
            ├─ Feeds       (headline list + feed rendering)
            ├─ Opml        (OPML import/export)
            ├─ PluginHandler (plugin AJAX dispatch)
            ├─ Pref_Feeds  (feed subscription management)
            ├─ Pref_Filters (filter CRUD)
            ├─ Pref_Labels  (label CRUD)
            ├─ Pref_Prefs   (user preferences form)
            ├─ Pref_System  (admin system settings)
            ├─ Pref_Users   (user management)
            └─ RPC          (UI RPC operations: mark read, star, etc.)
```

**Python mapping**:
- `IHandler` → `Protocol` or `ABC` with `before()` / `handle()` methods
- `Handler` → Flask `MethodView` base class or Blueprint view function base
- `Handler_Protected` → `@login_required` decorator applied to all subclass views
- Each leaf handler (`Feeds`, `Article`, ...) → Flask Blueprint with typed routes

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/ihandler.php` — IHandler interface
- `source-repos/ttrss-php/ttrss/classes/handler.php` — Handler base
- `source-repos/ttrss-php/ttrss/classes/feeds.php:1` — Feeds handler
- `source-repos/ttrss-php/ttrss/classes/rpc.php:1` — RPC handler
- `source-repos/ttrss-php/ttrss/classes/pref/feeds.php:1` — Pref_Feeds

**Research note**: `research/GRP-05-plugin-system.md` (handler dispatch pattern)

---

### C1 — Handler hierarchy: public-facing handlers (4 nodes)

**Members**: `API`, `Handler`, `Backend`, `Handler_Public`

**Characterisation**:
The unauthenticated and semi-authenticated handler base.
`Handler` is the root abstract class (implements `IHandler`).
`Backend` extends `Handler` directly (not via `Handler_Protected`)
and provides the main UI backend dispatcher.
`Handler_Public` extends `Handler` and serves unauthenticated public routes
(RSS syndication, bookmarklet subscribe, password reset, housekeeping).
`API` extends `Handler` and implements the JSON API — auth is checked
inside `API::before()` rather than by inheriting `Handler_Protected`.

**Inheritance chain**:
```
IHandler (interface)
  └─ Handler (abstract base)
       ├─ Backend         (main UI AJAX dispatcher)
       ├─ Handler_Public  (unauthenticated public routes)
       └─ API             (JSON API, self-managed auth)
```

**Python mapping**:
- `Backend` → Flask Blueprint `backend` (authenticated AJAX ops)
- `Handler_Public` → Flask Blueprint `public` (unauthenticated routes)
- `API` → Flask Blueprint `api` (JSON API with its own auth guard)

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/handler.php` — Handler base class
- `source-repos/ttrss-php/ttrss/classes/backend.php:1` — Backend handler
- `source-repos/ttrss-php/ttrss/classes/handler/public.php:1` — Handler_Public
- `source-repos/ttrss-php/ttrss/classes/api.php:1` — API (extends Handler, API_LEVEL = 8)

**Research note**: `research/GRP-01-core-api.md`

---

### C2 — FeedItem hierarchy (4 nodes)

**Members**: `FeedItem_Atom`, `FeedItem_Common`, `FeedItem`, `FeedItem_RSS`

**Characterisation**:
The feed-item value-object hierarchy used during feed parsing.
`FeedItem` is the abstract base interface (accessors: `get_title()`,
`get_guid()`, `get_content()`, `get_link()`, `get_date()`, etc.).
`FeedItem_Common` provides shared concrete implementations.
`FeedItem_Atom` and `FeedItem_RSS` are format-specific subclasses
that wrap an Atom `<entry>` or RSS `<item>` DOM node respectively.
Used only during feed update; discarded after article is stored.

**Inheritance chain**:
```
FeedItem (abstract interface-like base)
  └─ FeedItem_Common (shared implementations)
       ├─ FeedItem_Atom  (Atom 1.0 entries)
       └─ FeedItem_RSS   (RSS 2.0 / RDF items)
```

**Python mapping**:
- `FeedItem` → Python `dataclass` or `@attrs` class with typed fields
- `FeedItem_Common` / `FeedItem_Atom` / `FeedItem_RSS` →
  replaced by `feedparser.FeedParserDict` entry objects + adapter functions
- No need to port this hierarchy; `feedparser` (PyPI) provides the equivalent
  parsed structure. A thin adapter layer normalises `feedparser` output to
  the fields expected by the article storage logic.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/feeditem.php` — FeedItem base
- `source-repos/ttrss-php/ttrss/classes/feeditem/common.php` — FeedItem_Common
- `source-repos/ttrss-php/ttrss/classes/feeditem/atom.php` — FeedItem_Atom
- `source-repos/ttrss-php/ttrss/classes/feeditem/rss.php` — FeedItem_RSS
- `source-repos/ttrss-php/ttrss/classes/feedparser.php` — FeedParser (produces FeedItems)

**Research note**: `research/GRP-02-feed-engine.md`

---

### C3 — OTP / TOTP hierarchy (3 nodes) + Auth plugin (2 nodes) + Auth_Base (1 node)

**Members (merged into one research group)**:
`HOTP`, `OTP`, `TOTP` (C4) + `Plugin`, `Auth_Internal` (C8) + `Auth_Base` (C9)

**Characterisation**:

**OTP cluster (C4)**:
```
OTP (abstract base — HOTP algorithm core)
  ├─ HOTP (counter-based OTP)
  └─ TOTP (time-based OTP, RFC 6238 — used by TT-RSS)
```
`lib/otphp/lib/otp.php`, `lib/otphp/lib/totp.php`.
Used only by `plugins/auth_internal/init.php` for TOTP enrollment/validation.

**Plugin hierarchy (C8)**:
```
Plugin (abstract base — all plugins extend this)
  └─ Auth_Internal (built-in auth plugin — implements IAuthModule too)
```
`classes/plugin.php`, `plugins/auth_internal/init.php`.

**Auth_Base (C9)**:
```
IAuthModule (interface — auth plugin contract)
  └─ Auth_Base (abstract: provides auto_create_user())
       └─ Auth_Internal (concrete: DB username/password auth)
```
`classes/iauthmodule.php`, `classes/auth/base.php`,
`plugins/auth_internal/init.php`.

Note: `Auth_Internal` extends both `Plugin` (for the plugin lifecycle)
AND inherits from `Auth_Base` (for auth utilities). PHP allows this via
concrete base class + interface; Python uses multiple inheritance or mixin.

**Python mapping**:
- `OTP` / `HOTP` / `TOTP` → `pyotp.TOTP(secret).now()` (PyPI)
- `Plugin` abstract base → Python ABC `ttrss.plugins.base.Plugin`
- `IAuthModule` → `Protocol` `AuthModule` with `authenticate()`, `get_login()`, `logout()`
- `Auth_Base` → mixin class `AuthBaseMixin` providing `auto_create_user()`
- `Auth_Internal` → `ttrss/plugins/auth_internal/__init__.py` class implementing both

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/lib/otphp/lib/otp.php` — OTP base
- `source-repos/ttrss-php/ttrss/lib/otphp/lib/totp.php` — TOTP
- `source-repos/ttrss-php/ttrss/classes/plugin.php` — Plugin abstract base
- `source-repos/ttrss-php/ttrss/classes/iauthmodule.php` — IAuthModule interface
- `source-repos/ttrss-php/ttrss/classes/auth/base.php` — Auth_Base
- `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` — Auth_Internal

**Research note**: `research/GRP-06-auth-session.md`

---

### C5 — Third-party class hierarchies (7 nodes across C3, C5, C6, C7)

**Members (merged)**:
`ttrssMailer`, `PHPMailer` (C5);
`StringReader`, `CachedFileReader` (C6);
`Text_LanguageDetect_Parser`, `Text_LanguageDetect` (C7);
`Text_LanguageDetect_Exception`, `Exception`, `phpmailerException` (C3)

**Characterisation**:
All third-party library class hierarchies bundled in `lib/`.

```
PHPMailer (bundled PHPMailer 5.x)
  └─ ttrssMailer  (TT-RSS wrapper: reads SMTP_* config constants)

Exception (PHP built-in)
  ├─ phpmailerException  (PHPMailer error)
  └─ Text_LanguageDetect_Exception  (LanguageDetect error)

Text_LanguageDetect (PEAR Text_LanguageDetect)
  └─ Text_LanguageDetect_Parser  (internal parser component)

StringReader (gettext polyfill)
  └─ CachedFileReader  (gettext .mo file reader)
```

**Python mapping**:
- `PHPMailer` / `ttrssMailer` → `flask-mail` `Message` + `Mail` objects; replace entirely
- `Text_LanguageDetect` hierarchy → `langdetect` or `lingua` (PyPI); replace entirely
- `StringReader` / `CachedFileReader` → Python `gettext` stdlib; replace entirely
- Exception subclasses → Python `Exception` subclasses in respective modules

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/classes/ttrssmailer.php` — ttrssMailer
- `source-repos/ttrss-php/ttrss/lib/phpmailer/class.phpmailer.php` — PHPMailer 5.x
- `source-repos/ttrss-php/ttrss/lib/languagedetect/LanguageDetect.php` — Text_LanguageDetect
- `source-repos/ttrss-php/ttrss/lib/gettext/gettext.inc` — StringReader / CachedFileReader

**Research note**: `research/GRP-09-third-party-libs.md`

---

## Dependency levels

| Level | Characterisation | Representative classes |
|---|---|---|
| 0 (roots — no parent) | Interfaces + standalone bases | `IHandler`, `IDb`, `IAuthModule`, `Plugin`, `FeedItem`, `PHPMailer`, `OTP`, `Exception` |
| 1 | First-generation subclasses | `Handler`, `Auth_Base`, `FeedItem_Common`, `ttrssMailer`, `HOTP`, `TOTP`, `Db` |
| 2 | Second-generation subclasses | `Handler_Protected`, `Auth_Internal`, `FeedItem_Atom`, `FeedItem_RSS`, `Db_Pgsql`, `Db_Mysqli`, `Db_PDO` |
| 3 (leaves — deepest) | Application handler leaves | `Feeds`, `Article`, `RPC`, `Pref_Feeds`, `Pref_Filters`, `Pref_Prefs`, `Pref_System`, `Pref_Users`, `Pref_Labels`, `Dlg`, `Opml`, `PluginHandler` |

Migration rule: **port level-0 interfaces first (as Python ABCs / Protocols)**,
then level-1 bases, then level-2 adapters, then level-3 leaf handlers.

---

## Interface inventory

| Interface | Methods (PHP) | Python translation | Purpose |
|---|---|---|---|
| `IHandler` | `before($method)`, `handle()` | `Protocol` with `before()`, `handle()` | Handler dispatch contract |
| `IDb` | `connect()`, `query()`, `fetch_assoc()`, `fetch_result()`, `num_rows()`, `escape_string()`, `last_error()` | SQLAlchemy `Engine` / `Connection` (replaces) | DB adapter contract |
| `IAuthModule` | `get_login()`, `authenticate()`, `logout()`, `check_remember_me()` | `Protocol` `AuthModule` | Auth plugin contract |

---

## Key design patterns identified

### Template Method (Handler hierarchy)
`Handler::handle()` is the template method:
1. Calls `$this->before($method)` — auth/setup (overridden by subclasses)
2. Dispatches `$this->$method()` — operation implementation (overridden by subclasses)
3. Calls `$this->after()` — cleanup (optional override)

Python equivalent: Flask `MethodView` with `dispatch_request()` as template,
or explicit `before_request` / view function pattern in Blueprints.

### Adapter (Db hierarchy)
`IDb` interface + `Db` singleton + `Db_Pgsql` / `Db_Mysqli` / `Db_PDO` concrete adapters
is the classic Adapter pattern.
Python: replaced wholesale by SQLAlchemy's engine/dialect system.
`IDb` interface has no Python equivalent needed — SQLAlchemy provides the abstraction.

### Strategy (Auth hierarchy)
`IAuthModule` + `Auth_Base` + `Auth_Internal` is a Strategy pattern for authentication:
the host invokes `HOOK_AUTH_USER` and any registered auth plugin can satisfy the check.
Python: pluggy hookspec `auth_user(login, password)` with `firstresult=True`.

### Value Object (FeedItem hierarchy)
`FeedItem_Atom` / `FeedItem_RSS` are value objects wrapping DOM nodes.
Python: `feedparser` library provides equivalent parsed dicts; no class port needed.

---

## Singleton classes (46 nodes absorbed into nearest community)

The 46 singleton classes are:

1. **Db adapter classes** (`Db_Pgsql`, `Db_Mysqli`, `Db_Mysql`, `Db_PDO`) —
   listed as singletons because the graph detected no `extends` edge from `IDb`
   to these (they implement the interface but the AST walk may not have captured
   interface implementation edges for all).
   These belong to the DB layer (GRP-03).

2. **Logger classes** (`Logger`, `Logger_SQL`) — absorbed into GRP-03.

3. **FeedEnclosure** — value object for podcast attachments, absorbed into GRP-02.

4. **PluginHost** — the plugin registry singleton, absorbed into GRP-05.

5. **Remaining PHP library classes** (`QRcode`, various phpqrcode internals) —
   absorbed into GRP-09 (third-party libs).

---

## Modernization impact

### Forced adaptations

1. **PHP single inheritance → Python multiple inheritance / mixins**:
   `Auth_Internal` extends `Plugin` AND inherits `Auth_Base` behaviour.
   In PHP, only one concrete parent is allowed but `Auth_Base` is a
   concrete class, making this a single-inheritance chain where
   `Auth_Internal extends Plugin` and `Auth_Internal extends Auth_Base` are
   resolved differently.
   Python target uses explicit mixin: `class AuthInternal(Plugin, AuthBaseMixin)`.

2. **Handler `before()` pre-dispatch**:
   PHP's template-method dispatch (`$handler->$method()` with `before()` guard)
   becomes Flask route dispatch with `@before_request` or `@login_required`.
   The `before()` method's return-value contract (return `False` to abort)
   maps to Flask's `abort()` pattern.

3. **IDb → SQLAlchemy replacement**:
   The `IDb` adapter interface is entirely superseded by SQLAlchemy.
   No Python translation needed; the abstraction is built into the ORM.
   All `Db_*` concrete classes are obsolete in the Python target.

4. **`$this->dbh` property on handlers**:
   Many Handler subclass methods access `$this->dbh` (the DB connection
   via `Db::get()`). Python equivalents use `db.session` (Flask-SQLAlchemy)
   as a request-scoped session, injected via the app context.

5. **Plugin as abstract base**:
   PHP's `Plugin` class has abstract methods (`about()`, `init()`) that
   concrete plugin classes must implement. Python target defines
   `Plugin` as an ABC with `@abstractmethod` decorators.

### Divergences seeded
- Method-name dispatch via string (`$handler->$method()`) →
  explicit route dispatch (see `12-semantic-discrepancies.md` D-series).
- `IDb::escape_string()` anti-pattern → parameterised queries.
- Third-party class replacement: PHPMailer / Text_LanguageDetect / OTP libs.

---

## Source cross-references

| Construct | Source | Line(s) |
|---|---|---|
| IHandler interface | `source-repos/ttrss-php/ttrss/classes/ihandler.php` | full |
| Handler base class | `source-repos/ttrss-php/ttrss/classes/handler.php` | full |
| Handler_Protected (auth guard) | implied by `Handler_Protected extends Handler` | class/handler/ |
| IDb interface | `source-repos/ttrss-php/ttrss/classes/idb.php` | full |
| Db singleton | `source-repos/ttrss-php/ttrss/classes/db.php` | 1–50 |
| Db_Pgsql adapter | `source-repos/ttrss-php/ttrss/classes/db/pgsql.php` | full |
| IAuthModule interface | `source-repos/ttrss-php/ttrss/classes/iauthmodule.php` | full |
| Auth_Base | `source-repos/ttrss-php/ttrss/classes/auth/base.php` | full |
| Plugin abstract base | `source-repos/ttrss-php/ttrss/classes/plugin.php` | full |
| Auth_Internal plugin | `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` | full |
| FeedItem base | `source-repos/ttrss-php/ttrss/classes/feeditem.php` | full |
| FeedItem_Common | `source-repos/ttrss-php/ttrss/classes/feeditem/common.php` | full |
| FeedItem_Atom | `source-repos/ttrss-php/ttrss/classes/feeditem/atom.php` | full |
| FeedItem_RSS | `source-repos/ttrss-php/ttrss/classes/feeditem/rss.php` | full |
| ttrssMailer | `source-repos/ttrss-php/ttrss/classes/ttrssmailer.php` | full |
| TOTP | `source-repos/ttrss-php/ttrss/lib/otphp/lib/totp.php` | full |
| PluginHost singleton | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | full |
| API_VERSION constant | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 16 |

---

## Notes and caveats

- **High singleton count (46/55)**: The majority of PHP classes in TT-RSS
  either have no explicit `extends`/`implements` keyword (implicit `stdClass`
  inheritance) or implement interfaces that the tree-sitter AST walk did not
  capture as edges (e.g., `implements IDb` in `Db_Pgsql`).
  The actual class hierarchy is somewhat deeper than the 27-edge graph shows.
  Treat singleton classes as belonging to the community of their closest
  named parent (by PHP file path convention).

- **Interface implementation edges**: PHP's `implements` keyword creates
  class–interface edges. The graph builder captures `extends` reliably;
  `implements` may be partially captured depending on tree-sitter grammar version.
  Verify with `grep -r "implements" source-repos/ttrss-php/ttrss/classes/`
  before finalising the Python Protocol/ABC mapping.

- **Db adapter graph position**: `Db_Pgsql`, `Db_Mysqli`, `Db_PDO` should
  logically be children of `IDb` but may appear as singletons in the graph.
  These classes are fully obsolete in the Python target — do not invest
  in tracing their community placement.

- **Research mode**: ∆6 community research ran in DEGRADED mode (no external
  web search). Python class-design guidance from training knowledge only.
  Phase 2 should review current Flask/SQLAlchemy/pluggy best practices
  before committing to the class skeleton.
