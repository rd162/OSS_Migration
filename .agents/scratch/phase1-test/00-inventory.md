---
step: ∆1
title: Source Inventory — TT-RSS PHP
date: 2025-01-01
status: complete
---

# ∆1 — Source Inventory: TT-RSS PHP

## Repository path

`source-repos/ttrss-php/ttrss/` (read-only)

---

## File counts by type

| Extension | Count | Notes |
|-----------|-------|-------|
| `.php` | 138 | Application + vendored libs |
| `.sql` | 246 | Schema versions (MySQL + PostgreSQL) |
| `.js` | 832 | Dojo toolkit + application JS |
| `.css` | ~10 | Stylesheet bundle |
| `.po`/`.mo` | 28 | GNU gettext message catalogs (14 languages) |
| Other | ~1100 | Locale binaries, gitkeep, htaccess, icons |
| **Total** | **~2376** | |

---

## Application archetype

**Web application + Daemon** (mixed)

| Archetype component | Evidence |
|--------------------|----------|
| Web application | `index.php` (login + SPA shell), `backend.php` (AJAX handler), `api/index.php` (JSON API), `prefs.php`, `public.php`, `opml.php` |
| Daemon / background job | `update_daemon2.php` (pcntl_fork master+workers), `update.php` (single-run update) |
| Plugin host | `classes/pluginhost.php` (24 hooks), `plugins/auth_internal/` |

---

## Entry points

| File | Role |
|------|------|
| `index.php` | Main SPA entry — login sequence → Dojo shell |
| `backend.php` | AJAX back-end handler dispatch (op= parameter) |
| `api/index.php` | JSON API front-controller (`?op=login`, etc.) |
| `prefs.php` | Preferences page entry |
| `public.php` | Unauthenticated public entry (RSS sharing, pubsub) |
| `opml.php` | OPML import/export handler |
| `register.php` | Self-registration (optional feature) |
| `image.php` | Proxied image endpoint |
| `errors.php` | Error display page |
| `update_daemon2.php` | Background feed update daemon (PCNTL) |
| `update.php` | Single-shot feed updater (CLI) |

---

## Key PHP source directories

| Directory | Purpose | PHP files |
|-----------|---------|-----------|
| `classes/` | Core class library (handlers, models, plugin system) | ~40 |
| `classes/db/` | DB adapter implementations (mysql, mysqli, pdo, pgsql) | 5 |
| `classes/feeditem/` | Feed item implementations (RSS, Atom, Common) | 3 |
| `classes/pref/` | Preference tab handlers (feeds, filters, labels, prefs, system, users) | 6 |
| `classes/logger/` | Logger implementations (SQL, syslog) | 2 |
| `classes/auth/` | Auth base class | 1 |
| `include/` | Procedural function libraries | ~18 |
| `lib/` | Vendored third-party libraries | ~80 |
| `plugins/` | Built-in plugin (`auth_internal`) | 1 |
| `install/` | Web-based installer | 1 |

---

## Schema

| File | Purpose |
|------|---------|
| `schema/ttrss_schema_pgsql.sql` | **Canonical schema** — 35 tables, FK constraints, seed data |
| `schema/ttrss_schema_mysql.sql` | MySQL variant |
| `schema/versions/pgsql/NNN.sql` | Incremental migration patches (up to version 124) |
| `schema/versions/mysql/NNN.sql` | MySQL migration patches |

### Table inventory (35 tables from PostgreSQL schema)

| # | Table | Purpose |
|---|-------|---------|
| 1 | `ttrss_users` | User accounts (login, pwd_hash SHA1, email, otp_enabled) |
| 2 | `ttrss_feed_categories` | Feed categories (hierarchical via parent_cat self-FK) |
| 3 | `ttrss_feeds` | Feed subscriptions (url, auth, update settings, pubsub) |
| 4 | `ttrss_archived_feeds` | Deleted feeds retained for history |
| 5 | `ttrss_counters_cache` | Per-feed unread count cache |
| 6 | `ttrss_cat_counters_cache` | Per-category unread count cache |
| 7 | `ttrss_entries` | Global article store (guid unique, content, hash) |
| 8 | `ttrss_user_entries` | Per-user article state (read/starred/published/score) |
| 9 | `ttrss_entry_comments` | Article comments |
| 10 | `ttrss_filter_types` | Enum: title, content, both, link, date, author, tag |
| 11 | `ttrss_filter_actions` | Enum: filter, catchup, mark, tag, publish, score, label, stop |
| 12 | `ttrss_filters2` | Filter definitions (match_any_rule, inverse, enabled) |
| 13 | `ttrss_filters2_rules` | Filter rule conditions (regex, feed/cat scope) |
| 14 | `ttrss_filters2_actions` | Filter rule actions (action_id + action_param) |
| 15 | `ttrss_tags` | User-assigned tags on articles |
| 16 | `ttrss_version` | Schema version tracking (current: 124) |
| 17 | `ttrss_enclosures` | Podcast/media enclosures on articles |
| 18 | `ttrss_settings_profiles` | Named settings profiles per user |
| 19 | `ttrss_prefs_types` | Pref type enum (bool=1, string=2, integer=3) |
| 20 | `ttrss_prefs_sections` | Pref sections (General, Interface, Advanced, Digest) |
| 21 | `ttrss_prefs` | Preference definitions + defaults (50+ prefs) |
| 22 | `ttrss_user_prefs` | Per-user pref overrides |
| 23 | `ttrss_labels2` | Article label definitions |
| 24 | `ttrss_user_labels2` | Per-user label visibility |
| 25 | `ttrss_feedbrowser_cache` | Popular feeds cache (for feed browser feature) |
| 26 | `ttrss_sessions` | DB-backed PHP sessions |
| 27 | `ttrss_themes` | Theme definitions |
| 28 | `ttrss_error_log` | Application error log table |
| 29 | `ttrss_plugin_storage` | Plugin persistent data store |
| 30 | `ttrss_linked_feeds` | Linked TT-RSS instances (federation) |
| 31 | `ttrss_linked_instances` | Remote TT-RSS instance registry |
| 32 | `ttrss_access_keys` | Per-feed RSS sharing keys |
| 33 | `ttrss_scheduled_updates` | Queued feed updates |
| 34 | `ttrss_filters` | Legacy filter table (superseded by filters2) |
| 35 | `ttrss_labels` | Legacy label table |

---

## Key constants

| Constant | Value | Significance |
|----------|-------|-------------|
| `SCHEMA_VERSION` | 124 | Current schema version — migrate must reach 124 |
| `EXPECTED_CONFIG_VERSION` | 26 | Config.php version gate |
| `LABEL_BASE_INDEX` | -1024 | Magic number: label feed IDs start at -1024 |
| `PLUGIN_FEED_BASE_INDEX` | -128 | Magic number: plugin feed IDs start at -128 |
| `COOKIE_LIFETIME_LONG` | 86400×365 | Persistent session lifetime (1 year) |
| `DAEMON_SLEEP_INTERVAL` | 120 | Daemon poll interval seconds |
| `MAX_JOBS` | 2 | Max concurrent update worker processes |
| `MAX_CHILD_RUNTIME` | 1800 | Child watchdog timeout (seconds) |

---

## Vendored third-party libraries (lib/)

| Library | Purpose | Modernization note |
|---------|---------|-------------------|
| `phpmailer/` | SMTP email sending | Replace with Python `smtplib` or `aiosmtplib` |
| `phpqrcode/` | QR code generation | Replace with Python `qrcode` |
| `otphp/` | TOTP/HOTP for OTP | Replace with Python `pyotp` |
| `languagedetect/` | Article language detection | Replace with `langdetect` |
| `Mobile_Detect.php` | Mobile browser detection | Replace with `user-agents` or drop |
| `MiniTemplator.class.php` | Simple template engine | Superseded by Jinja2 |
| `gettext/` | GNU gettext PHP runtime | Replace with Python `gettext`/Flask-Babel |
| `jshrink/` | JS minifier | Build tool concern (webpack/esbuild) |
| `pubsubhubbub/` | PubSubHubbub subscriber | Replace with `aiohttp` webhook handler |
| `sphinxapi.php` | Sphinx full-text search API | Optional; replace with Elasticsearch client |
| `accept-to-gettext.php` | Accept-Language header parsing | Replace with `langcodes` |
| `floIcon.php`, `jimIcon.php` | ICO favicon parser | Replace with `Pillow` |

---

## Frontend surface

| Directory | Technology | LOC estimate |
|-----------|-----------|-------------|
| `js/` (832 files) | Dojo Toolkit 1.x + custom widgets | ~25 kLOC |
| `css/` | Custom CSS + Dijit CSS | ~3 kLOC |

The frontend is a Dojo-based single-page application with:
- `js/tt-rss.js` — main SPA controller
- `js/FeedList.js`, `js/Article.js`, etc. — widget modules
- AJAX calls to `backend.php?op=<handler>` and `api/index.php`

---

## LOC estimates (first-party PHP only — excluding lib/)

| Subsystem | Files | Est. LOC |
|-----------|-------|---------|
| `classes/*.php` | ~25 | ~5 kLOC |
| `include/*.php` | ~18 | ~8 kLOC |
| `plugins/auth_internal/` | 1 | ~200 LOC |
| Entry points | ~10 | ~500 LOC |
| **First-party total** | **~55** | **~13-14 kLOC** |

Source is in the **mid-scale** range (10–50 kLOC).
CoK saturation can be done inline (∆7 inline mode — no formal knowledge-management invocation needed).

---

## Critical security observations (∆1 surface scan)

| Finding | Location | Severity |
|---------|----------|---------|
| SHA1 password hashing | `schema/ttrss_schema_pgsql.sql` line 7 (`SHA1:5baa...`) | HIGH |
| PHP `mcrypt` for AES-128-CBC credential encryption | `include/crypt.php` | HIGH — mcrypt removed PHP 7.2+ |
| SQL string interpolation (direct string injection into queries) | `include/ccache.php`, `include/rssfuncs.php` | HIGH |
| DB-backed sessions (ttrss_sessions) | `include/sessions.php` | MED |
| Missing prepared statements in many DB calls | `include/*.php` | HIGH |

---

## Provisional application classification

```
TT-RSS = self-hosted RSS aggregator
  └─ Web UI: Dojo SPA → backend.php (AJAX) + api/index.php (JSON API)
  └─ Auth: multi-user, session-based, OTP optional, plugin-auth hook
  └─ Feed engine: daemon (update_daemon2.php) + manual update.php
  └─ DB: PostgreSQL primary, MySQL supported
  └─ Plugin system: 24 named hooks, directory-scanned plugins
  └─ i18n: GNU gettext, 14 languages
```
