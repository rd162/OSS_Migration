# 01 — Architecture Spec

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

## Sequence Diagrams

### 1. Sequence Diagram: Feed Update Flow (text-based, mermaid-compatible)

```
sequenceDiagram
    participant D as update_daemon2.php
    participant R as rssfuncs.php
    participant F as fetch_file_contents()
    participant P as FeedParser
    participant DB as Database
    participant C as ccache.php
    participant PH as PluginHost

    D->>DB: Query feeds needing update (last_updated + interval check)
    DB-->>D: Feed list
    loop Each feed
        D->>DB: SET last_update_started = NOW()
        D->>R: update_rss_feed($feed_id)
        R->>F: fetch_file_contents($feed_url, auth)
        F-->>R: XML data (or error)
        alt Fetch failed
            R->>DB: UPDATE feeds SET last_error = $error
        else Fetch succeeded
            R->>PH: run_hooks(HOOK_FEED_FETCHED)
            R->>P: new FeedParser($xml)
            P-->>R: Parsed items
            loop Each article
                R->>DB: SELECT by GUID (dedup check)
                alt New article
                    R->>DB: INSERT ttrss_entries
                    R->>DB: INSERT ttrss_user_entries
                    R->>R: get_article_filters() → calculate_article_score()
                    R->>PH: run_hooks(HOOK_ARTICLE_FILTER)
                else Existing article
                    R->>DB: UPDATE date_updated
                end
            end
            R->>C: ccache_update($feed_id)
            R->>DB: UPDATE feeds SET last_updated = NOW(), last_error = ''
        end
    end
    D->>PH: run_hooks(HOOK_UPDATE_TASK)
    D->>R: housekeeping_common() [expire cache, locks, error log]
```

### 2. Sequence Diagram: AJAX Request Lifecycle

```
sequenceDiagram
    participant Browser as Browser (JS)
    participant BE as backend.php
    participant H as Handler class
    participant DB as Database
    participant PH as PluginHost

    Browser->>BE: POST backend.php?op=feeds&method=view&feed=5
    BE->>BE: Load bootstrap (autoload→sessions→functions→config)
    BE->>PH: init_plugins()
    BE->>BE: login_sequence() / validate_session()
    BE->>PH: lookup_handler("feeds", "view")
    alt Plugin override
        PH-->>BE: Plugin handler
    else Default handler
        BE->>H: new Feeds($_REQUEST)
    end
    BE->>BE: validate_csrf($_REQUEST['csrf_token'])
    BE->>H: before("view")
    BE->>H: view()
    H->>DB: queryFeedHeadlines($feed, $limit, $view_mode...)
    DB-->>H: Article rows
    H->>H: format_headlines_list() → server-rendered HTML
    H-->>BE: JSON {headlines, counters, runtime-info}
    BE->>H: after()
    BE-->>Browser: Content-Type: text/json (gzipped if enabled)
```

### 3. Sequence Diagram: Login Flow

```
sequenceDiagram
    participant Browser
    participant PHP as index.php
    participant F as functions.php
    participant PH as PluginHost
    participant DB as Database
    participant S as sessions.php

    Browser->>PHP: POST login (user, password)
    PHP->>F: login_sequence()
    F->>F: authenticate_user($login, $password)
    F->>PH: run_hooks(HOOK_AUTH_USER)
    PH->>DB: SELECT pwd_hash, salt FROM ttrss_users
    DB-->>PH: User record
    PH->>PH: Verify password hash (SHA1/SHA256)
    alt Auth success
        PH-->>F: user_id
        F->>S: Create session (uid, csrf_token, ip, user_agent, pwd_hash)
        F->>DB: UPDATE ttrss_users SET last_login = NOW()
        F->>F: load_user_plugins($uid)
        F-->>PHP: Authenticated
        PHP-->>Browser: Redirect to main UI
    else Auth failure
        PH-->>F: false
        F-->>PHP: Login error
        PHP-->>Browser: Show login form with error
    end
```

### 4. Data Flow Diagram: Article Lifecycle

```
External RSS Feed
    │
    ▼
fetch_file_contents() ──→ [HTTP 304?] ──→ Skip (no change)
    │
    ▼
FeedParser.parse() ──→ [Invalid XML?] ──→ Store error, skip
    │
    ▼
For each FeedItem:
    │
    ├──→ GUID construction (item_id → feed_link → title hash)
    ├──→ Content hash (SHA1 of content)
    ├──→ Dedup check (GUID match in ttrss_entries)
    │       │
    │       ├── EXISTS → Update date_updated only
    │       └── NEW → INSERT ttrss_entries
    │
    ├──→ INSERT ttrss_user_entries (per subscribed user)
    ├──→ Filter evaluation → Score calculation
    │       │
    │       ├── score < -500 → mark as read
    │       ├── score > 1000 → mark as starred
    │       ├── "catchup" action → mark as read
    │       ├── "publish" action → mark as published
    │       └── "label" action → add label
    │
    ├──→ ccache_update(feed) → ccache_update(category)
    └──→ Plugin hooks: HOOK_ARTICLE_FILTER
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

## Configuration Constants (config.php-dist)

| Constant | Default | Type | Description |
|----------|---------|------|-------------|
| DB_TYPE | "pgsql" | string | Database engine |
| DB_HOST | "localhost" | string | Database host |
| DB_USER | "fox" | string | Database user |
| DB_NAME | "fox" | string | Database name |
| DB_PASS | "XXXXXX" | string | Database password |
| DB_PORT | "" | string | Database port |
| MYSQL_CHARSET | "UTF8" | string | MySQL charset |
| SELF_URL_PATH | "http://example.org/tt-rss/" | string | Installation URL |
| FEED_CRYPT_KEY | "" | string | 24-char AES key for feed passwords |
| SINGLE_USER_MODE | false | bool | Single-user mode (bypasses auth) |
| SIMPLE_UPDATE_MODE | false | bool | Browser-based feed updates |
| PHP_EXECUTABLE | "/usr/bin/php" | string | PHP CLI path |
| LOCK_DIRECTORY | "lock" | string | Lock file directory |
| CACHE_DIR | "cache" | string | Cache directory |
| ICONS_DIR | "feed-icons" | string | Feed icon directory |
| ICONS_URL | "feed-icons" | string | Feed icon URL path |
| AUTH_AUTO_CREATE | true | bool | Auto-create users from external auth |
| AUTH_AUTO_LOGIN | true | bool | Auto-login for external auth |
| FORCE_ARTICLE_PURGE | 0 | int | Force purge after N days (0=user choice) |
| PUBSUBHUBBUB_HUB | "" | string | PuSH hub URL |
| PUBSUBHUBBUB_ENABLED | false | bool | Enable PuSH |
| SPHINX_ENABLED | false | bool | Enable Sphinx search |
| SPHINX_SERVER | "localhost:9312" | string | Sphinx server |
| SPHINX_INDEX | "ttrss, delta" | string | Sphinx index names |
| ENABLE_REGISTRATION | false | bool | Allow self-registration |
| REG_NOTIFY_ADDRESS | "user@your.domain.dom" | string | Admin email for registrations |
| REG_MAX_USERS | 10 | int | Max registered users |
| SESSION_COOKIE_LIFETIME | 86400 | int | Cookie lifetime (seconds) |
| SESSION_CHECK_ADDRESS | 1 | int | IP validation strictness (0-3) |
| SMTP_FROM_NAME | "Tiny Tiny RSS" | string | Email sender name |
| SMTP_FROM_ADDRESS | "noreply@your.domain.dom" | string | Email sender address |
| DIGEST_SUBJECT | "[tt-rss] New headlines for last 24 hours" | string | Digest email subject |
| SMTP_SERVER | "" | string | SMTP server (blank=system MTA) |
| SMTP_LOGIN | "" | string | SMTP username |
| SMTP_PASSWORD | "" | string | SMTP password |
| SMTP_SECURE | "" | string | SMTP security (ssl/tls/blank) |
| CHECK_FOR_NEW_VERSION | true | bool | Auto-check for updates |
| DETECT_ARTICLE_LANGUAGE | false | bool | Language detection |
| ENABLE_GZIP_OUTPUT | false | bool | Gzip responses |
| PLUGINS | "auth_internal, note, updater" | string | Enabled plugins |
| LOG_DESTINATION | "sql" | string | Log target (sql/syslog/blank) |
| CONFIG_VERSION | 26 | int | Config version |

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
