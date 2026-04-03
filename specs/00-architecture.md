# 00 — Architecture Spec

## Application Identity

- **Name**: Tiny Tiny RSS (TT-RSS)
- **Type**: Self-hosted web-based RSS/Atom feed aggregator
- **Version**: 1.12.x (schema version 124)
- **Language**: PHP 5.3+ (procedural + OOP hybrid)
- **Frontend**: Prototype.js + Dojo Toolkit (dijit)
- **Database**: MySQL 5.5+ / PostgreSQL (dual support via adapter pattern)
- **Deployment**: Docker (Nginx + PHP-FPM or Apache), background update daemon

## Architectural Style

**Server-rendered SPA hybrid** with RPC-based AJAX communication.

The application is NOT a clean MVC. It is a **handler-based architecture** where:
- PHP handler classes act as controllers
- Database queries are embedded directly in handlers (no ORM, no repository layer)
- HTML is rendered server-side and injected into client-side DOM via AJAX
- Frontend manages widget state via Dojo stores and Prototype.js DOM manipulation

### Pattern Classification

| Pattern | Used? | Details |
|---------|-------|---------|
| MVC | Partial | Handlers ≈ controllers, no explicit model layer |
| ORM | No | Raw SQL with escape-string sanitization |
| Transactional Script | Yes | Business logic in handler methods with inline SQL |
| Singleton | Yes | `Db::get()`, `PluginHost::getInstance()` |
| Adapter | Yes | Database adapters (MySQL, MySQLi, PostgreSQL, PDO) |
| Hook/Observer | Yes | Plugin system with 24 hook types |
| Repository | No | No data access abstraction layer |

## Application Layers

```
┌─────────────────────────────────────────────────────┐
│  ENTRY POINTS                                        │
│  index.php | backend.php | api/index.php             │
│  public.php | update_daemon2.php | opml.php          │
├─────────────────────────────────────────────────────┤
│  BOOTSTRAP CHAIN                                     │
│  autoload.php → sessions.php → functions.php         │
│  → config.php → db.php → db-prefs.php               │
├─────────────────────────────────────────────────────┤
│  HANDLER LAYER (request dispatch)                    │
│  Handler → Handler_Protected → {RPC, Feeds, Article, │
│            Pref_*, Dlg, Opml, PluginHandler}         │
│  Handler → Handler_Public                            │
│  Handler → Backend, API                              │
├─────────────────────────────────────────────────────┤
│  BUSINESS LOGIC (mixed into handlers + includes)     │
│  include/functions.php (1000+ lines)                 │
│  include/functions2.php (1000+ lines)                │
│  include/rssfuncs.php (feed update engine)           │
│  include/labels.php, ccache.php, digest.php, etc.    │
├─────────────────────────────────────────────────────┤
│  PLUGIN SYSTEM                                       │
│  PluginHost (singleton) → Plugin instances            │
│  24 hooks, handler/command/API registration           │
├─────────────────────────────────────────────────────┤
│  DATA ACCESS (no abstraction — raw SQL)              │
│  db_query() → Db::get() → Adapter (IDb)             │
│  Adapters: Db_Pgsql, Db_Mysql, Db_Mysqli, Db_PDO    │
├─────────────────────────────────────────────────────┤
│  DATABASE                                            │
│  35 tables, 124 schema versions                      │
│  MySQL 5.5+ or PostgreSQL                            │
└─────────────────────────────────────────────────────┘
```

## Class Hierarchy

### Handler Tree (implements IHandler)

```
Handler (base)
├── Handler_Protected (requires authenticated session)
│   ├── RPC            — State mutations (mark, delete, archive, catchup)
│   ├── Feeds          — Feed listing, headlines, search
│   ├── Article        — Article view, tags, labels, scoring
│   ├── Dlg            — Dialog HTML fragments
│   ├── Opml           — OPML import/export
│   ├── PluginHandler  — Routes to plugin methods
│   ├── Pref_Feeds     — Feed/category CRUD
│   ├── Pref_Filters   — Filter rule management
│   ├── Pref_Labels    — Label CRUD with colors
│   ├── Pref_Prefs     — User preference management
│   ├── Pref_Users     — Admin user management (access_level >= 10)
│   └── Pref_System    — System admin (error log)
├── Handler_Public (no auth required)
├── Backend (system operations)
└── API (REST API — JSON responses, session/API-key auth)
```

### Database Adapter Tree (implements IDb)

```
Db (singleton factory)
├── Db_Pgsql   — pg_* functions
├── Db_Mysql   — mysql_* (deprecated)
├── Db_Mysqli  — mysqli_* extension
└── Db_PDO     — PDO abstraction
```

### Feed Parser Tree

```
FeedItem (base)
└── FeedItem_Common (abstract)
    ├── FeedItem_Atom
    └── FeedItem_RSS
```

### Other Hierarchies

```
Plugin (base) → Auth_Internal (implements IAuthModule)
Logger (base) → Logger_SQL, Logger_Syslog
ttrssMailer extends PHPMailer
```

## Request Lifecycle

### Web UI Request (index.php)

```
1. Check config.php exists (else redirect to installer)
2. Load bootstrap chain: autoload → sessions → functions → config → db-prefs
3. Initialize gettext (i18n)
4. Load Mobile_Detect library
5. init_plugins() → PluginHost::getInstance()->load(PLUGINS, KIND_ALL)
6. Check for digest/mobile plugin overrides
7. login_sequence() → authenticate_user() or validate_session()
8. load_user_plugins($owner_uid)
9. Render HTML shell with JavaScript initialization params
10. Frontend JS takes over → AJAX calls to backend.php
```

### AJAX Request (backend.php)

```
1. Load bootstrap chain
2. init_plugins()
3. login_sequence() / validate_session()
4. Extract $op (handler class) and $method from $_REQUEST
5. Check PluginHost for handler override: lookup_handler($op, $method)
6. Instantiate handler: new $op($_REQUEST)
7. Validate CSRF token (unless csrf_ignore($method))
8. Call handler->before($method) → handler->$method() → handler->after()
9. Return JSON (gzipped if ENABLE_GZIP_OUTPUT)
```

### REST API Request (api/index.php)

```
1. Load bootstrap chain
2. Decode JSON payload
3. Instantiate API handler
4. Authenticate via session or API key
5. Dispatch to API method
6. Return JSON: {seq, status (0=OK, 1=ERR), content}
```

### Feed Update (update_daemon2.php)

```
1. Load bootstrap chain + rssfuncs.php
2. Acquire daemon lock (LOCK_DIRECTORY/update_daemon.lock)
3. Main loop (every DAEMON_SLEEP_INTERVAL=120s):
   a. Query feeds needing update (respecting intervals, user activity)
   b. Lock each feed with last_update_started timestamp
   c. Spawn worker processes (MAX_JOBS=2)
   d. Each worker: fetch RSS → parse → store articles → apply filters
   e. Update counter caches
   f. Run plugin HOOK_UPDATE_TASK hooks
   g. Expire cached files and lock files
```

## Key Design Decisions

### 1. No ORM — Transactional Script Pattern
All database access is raw SQL via `db_query()`. Business logic and data access are co-located in handler methods. This means:
- **Pro**: Simple, no abstraction overhead, full SQL control
- **Con**: SQL duplication, no query builder, DB-specific syntax scattered everywhere
- **Migration implication**: Need to decide on Python ORM (SQLAlchemy) vs raw SQL

### 2. Dual Database Support
MySQL and PostgreSQL supported via adapter pattern. Schema migrations exist in parallel for both. SQL queries use database-specific syntax in places (e.g., `INTERVAL`, `DATE_SUB` vs `NOW() - INTERVAL`).
- **Migration implication**: SQLAlchemy can abstract this, or choose one DB

### 3. Monolithic Include Files
`functions.php` (1000+ lines) and `functions2.php` (1000+ lines) contain most utility/business logic as standalone functions. Not organized by domain.
- **Migration implication**: Decompose into Python modules by domain

### 4. Server-Side HTML Rendering
Headlines, article content, dialog fragments are all rendered as HTML strings in PHP and sent via JSON to the frontend. The frontend injects these into the DOM.
- **Migration implication**: This pattern works with any backend (Flask/Django templates)

### 5. Global State via $_SESSION
Authentication state, user preferences, CSRF tokens stored in `$_SESSION`. Accessed directly throughout codebase.
- **Migration implication**: Map to Flask session or Django middleware

### Source Files

| File | Role | Lines (approx) |
|------|------|----------------|
| `ttrss/index.php` | Web UI entry point | ~300 |
| `ttrss/backend.php` | AJAX dispatcher | ~150 |
| `ttrss/api/index.php` | REST API entry | ~70 |
| `ttrss/update_daemon2.php` | Background updater | ~250 |
| `ttrss/include/functions.php` | Core utilities | ~2000 |
| `ttrss/include/functions2.php` | Additional utilities | ~2500 |
| `ttrss/include/rssfuncs.php` | Feed update engine | ~1300 |
| `ttrss/include/autoload.php` | PSR-0 class loader | ~20 |
| `ttrss/include/sessions.php` | Session handlers | ~110 |
| `ttrss/classes/handler.php` | Base handler class | ~30 |
| `ttrss/classes/db.php` | DB singleton | ~60 |
| `ttrss/classes/pluginhost.php` | Plugin manager | ~400 |
| `ttrss/config.php-dist` | Config template | ~200 |

All paths relative to `source-repos/ttrss-php/`.
