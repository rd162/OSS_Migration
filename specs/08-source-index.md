# 08 — Source Code Index

## Overview

- **Total PHP files**: 138 (73 application + 65 third-party)
- **Total SQL files**: 246 (2 schema + 244 migrations)
- **Total JS files**: ~11 application + hundreds of library files
- **Total CSS files**: 7 application
- **Base path**: `source-repos/ttrss-php/`

## Entry Points

| File | Purpose | Spec Refs |
|------|---------|-----------|
| `ttrss/index.php` | Web UI entry (HTML bootstrap) | 00-arch, 02-api |
| `ttrss/backend.php` | AJAX RPC dispatcher | 02-api |
| `ttrss/api/index.php` | REST API endpoint | 02-api |
| `ttrss/public.php` | Public feeds/login | 02-api |
| `ttrss/update.php` | CLI update tool | 06-cache |
| `ttrss/update_daemon2.php` | Background feed updater | 06-cache |
| `ttrss/opml.php` | OPML import/export | 02-api |
| `ttrss/prefs.php` | Preferences UI | 02-api |
| `ttrss/register.php` | User registration | 05-security |
| `ttrss/image.php` | Cached image proxy | 06-cache |
| `ttrss/errors.php` | Error definitions | 00-arch |

## Include Files (Core Business Logic)

| File | Purpose | Lines | Spec Refs |
|------|---------|-------|-----------|
| `ttrss/include/functions.php` | Core utilities, auth, config | ~2000 | 00-arch, 05-security |
| `ttrss/include/functions2.php` | Feed queries, rendering, search | ~2500 | 00-arch, 03-frontend |
| `ttrss/include/rssfuncs.php` | Feed update engine | ~1300 | 06-cache |
| `ttrss/include/sessions.php` | Custom session handlers | ~110 | 05-security |
| `ttrss/include/db.php` | DB wrapper functions | ~35 | 01-db |
| `ttrss/include/db-prefs.php` | Preference get/set | ~50 | 06-cache |
| `ttrss/include/autoload.php` | PSR-0 class autoloader | ~20 | 00-arch |
| `ttrss/include/ccache.php` | Counter cache operations | ~100 | 06-cache |
| `ttrss/include/labels.php` | Label CRUD + cache | ~200 | 01-db |
| `ttrss/include/digest.php` | Email digest generation | ~150 | 00-arch |
| `ttrss/include/crypt.php` | Feed credential encryption | ~50 | 05-security |
| `ttrss/include/colors.php` | Color manipulation (feed icons) | ~100 | 00-arch |
| `ttrss/include/feedbrowser.php` | Feed directory queries | ~80 | 06-cache |
| `ttrss/include/login_form.php` | Login HTML template | ~50 | 05-security |
| `ttrss/include/errorhandler.php` | PHP error handler registration | ~40 | 00-arch |
| `ttrss/include/sanity_check.php` | Startup validation | ~120 | 00-arch |
| `ttrss/include/sanity_config.php` | Config validation definitions | ~30 | 00-arch |
| `ttrss/include/version.php` | Version constants | ~5 | 00-arch |

## Handler Classes

| File | Class | Extends | Purpose | Spec Refs |
|------|-------|---------|---------|-----------|
| `ttrss/classes/handler.php` | Handler | — | Base handler (IHandler) | 00-arch |
| `ttrss/classes/handler/protected.php` | Handler_Protected | Handler | Auth-required handler | 00-arch |
| `ttrss/classes/handler/public.php` | Handler_Public | Handler | Public endpoints | 02-api |
| `ttrss/classes/backend.php` | Backend | Handler | System operations | 02-api |
| `ttrss/classes/api.php` | API | Handler | REST API (~22KB) | 02-api |
| `ttrss/classes/rpc.php` | RPC | Handler_Protected | State mutations (~15KB) | 02-api |
| `ttrss/classes/feeds.php` | Feeds | Handler_Protected | Feed display (~38KB) | 02-api, 03-frontend |
| `ttrss/classes/article.php` | Article | Handler_Protected | Article ops (~10KB) | 02-api |
| `ttrss/classes/dlg.php` | Dlg | Handler_Protected | Dialog HTML fragments | 03-frontend |
| `ttrss/classes/opml.php` | Opml | Handler_Protected | OPML import/export | 02-api |

## Preference Handler Classes

| File | Class | Purpose | Spec Refs |
|------|-------|---------|-----------|
| `ttrss/classes/pref/feeds.php` | Pref_Feeds | Feed/category CRUD | 02-api |
| `ttrss/classes/pref/filters.php` | Pref_Filters | Filter rule management | 02-api |
| `ttrss/classes/pref/labels.php` | Pref_Labels | Label CRUD with colors | 02-api |
| `ttrss/classes/pref/prefs.php` | Pref_Prefs | User preferences | 02-api |
| `ttrss/classes/pref/users.php` | Pref_Users | Admin user management | 02-api, 05-security |
| `ttrss/classes/pref/system.php` | Pref_System | System admin (error log) | 02-api |

## Database Classes

| File | Class | Implements | Purpose | Spec Refs |
|------|-------|------------|---------|-----------|
| `ttrss/classes/db.php` | Db | IDb | Singleton DB factory | 01-db |
| `ttrss/classes/idb.php` | IDb | — | DB adapter interface | 01-db |
| `ttrss/classes/db/pgsql.php` | Db_Pgsql | IDb | PostgreSQL adapter | 01-db |
| `ttrss/classes/db/mysql.php` | Db_Mysql | IDb | Legacy MySQL adapter | 01-db |
| `ttrss/classes/db/mysqli.php` | Db_Mysqli | IDb | MySQLi adapter | 01-db |
| `ttrss/classes/db/pdo.php` | Db_PDO | IDb | PDO adapter | 01-db |
| `ttrss/classes/db/prefs.php` | Db_Prefs | — | Preference cache singleton | 06-cache |
| `ttrss/classes/db/stmt.php` | Db_Stmt | — | Statement result wrapper | 01-db |
| `ttrss/classes/dbupdater.php` | DbUpdater | — | Schema migration runner | 01-db |

## Feed Processing Classes

| File | Class | Purpose | Spec Refs |
|------|-------|---------|-----------|
| `ttrss/classes/feedparser.php` | FeedParser | XML/RSS/Atom detection + parsing | 00-arch |
| `ttrss/classes/feeditem.php` | FeedItem | Base feed entry class | 00-arch |
| `ttrss/classes/feeditem/common.php` | FeedItem_Common | Shared extraction logic | 00-arch |
| `ttrss/classes/feeditem/atom.php` | FeedItem_Atom | Atom entry extraction | 00-arch |
| `ttrss/classes/feeditem/rss.php` | FeedItem_RSS | RSS item extraction | 00-arch |
| `ttrss/classes/feedenclosure.php` | FeedEnclosure | Media attachment data | 00-arch |

## Plugin System Classes

| File | Class | Purpose | Spec Refs |
|------|-------|---------|-----------|
| `ttrss/classes/pluginhost.php` | PluginHost | Plugin manager singleton (~400 lines) | 04-plugin |
| `ttrss/classes/plugin.php` | Plugin | Base plugin class | 04-plugin |
| `ttrss/classes/pluginhandler.php` | PluginHandler | HTTP routing to plugins | 04-plugin |
| `ttrss/classes/iauthmodule.php` | IAuthModule | Auth plugin interface | 04-plugin |
| `ttrss/classes/ihandler.php` | IHandler | Handler interface | 00-arch |
| `ttrss/plugins/auth_internal/init.php` | Auth_Internal | Internal auth plugin | 04-plugin, 05-security |

## Logging & Utility Classes

| File | Class | Purpose | Spec Refs |
|------|-------|---------|-----------|
| `ttrss/classes/logger.php` | Logger | Logging facade (singleton) | 00-arch |
| `ttrss/classes/logger/sql.php` | Logger_SQL | Log to ttrss_error_log table | 00-arch |
| `ttrss/classes/logger/syslog.php` | Logger_Syslog | Log to syslog | 00-arch |
| `ttrss/classes/ttrssmailer.php` | ttrssMailer | Email (extends PHPMailer) | 00-arch |
| `ttrss/classes/auth/base.php` | Auth_Base | Auth base class | 05-security |

## JavaScript Files

| File | Purpose | Spec Refs |
|------|---------|-----------|
| `ttrss/js/tt-rss.js` | Main app init + state | 03-frontend |
| `ttrss/js/viewfeed.js` | Article/headline display | 03-frontend |
| `ttrss/js/feedlist.js` | Feed sidebar management | 03-frontend |
| `ttrss/js/functions.js` | Global utilities + CSRF | 03-frontend, 05-security |
| `ttrss/js/prefs.js` | Preferences UI | 03-frontend |
| `ttrss/js/FeedTree.js` | Feed tree dijit widget | 03-frontend |
| `ttrss/js/PrefFeedTree.js` | Pref feed tree | 03-frontend |
| `ttrss/js/PrefFilterTree.js` | Filter tree widget | 03-frontend |
| `ttrss/js/PrefLabelTree.js` | Label tree widget | 03-frontend |
| `ttrss/js/PluginHost.js` | Client-side plugin host | 03-frontend, 04-plugin |
| `ttrss/js/deprecated.js` | Backward compat shims | 03-frontend |

## CSS Files

| File | Purpose | Spec Refs |
|------|---------|-----------|
| `ttrss/css/tt-rss.css` | Main app styles | 03-frontend |
| `ttrss/css/layout.css` | Page layout | 03-frontend |
| `ttrss/css/cdm.css` | Combined display mode | 03-frontend |
| `ttrss/css/prefs.css` | Preferences styles | 03-frontend |
| `ttrss/css/utility.css` | Utility classes | 03-frontend |
| `ttrss/css/zoom.css` | Article zoom view | 03-frontend |
| `ttrss/css/dijit.css` | Dojo widget overrides | 03-frontend |

## Schema Files

| File | Purpose | Spec Refs |
|------|---------|-----------|
| `ttrss/schema/ttrss_schema_mysql.sql` | Complete MySQL schema | 01-db |
| `ttrss/schema/ttrss_schema_pgsql.sql` | Complete PostgreSQL schema | 01-db |
| `ttrss/schema/versions/mysql/{3-124}.sql` | MySQL migrations (124 files) | 01-db |
| `ttrss/schema/versions/pgsql/{3-124}.sql` | PostgreSQL migrations (122 files) | 01-db |

## Configuration & Deployment Files

| File | Purpose | Spec Refs |
|------|---------|-----------|
| `ttrss/config.php-dist` | Config template | 00-arch, 07-deploy |
| `Dockerfile` | Legacy Docker image | 07-deploy |
| `Dockerfile.local` | Modern Docker image | 07-deploy |
| `docker-compose.yaml` | Production stack | 07-deploy |
| `docker-compose.override.yml` | Dev override | 07-deploy |
| `docker-entrypoint.sh` | Container init script | 07-deploy |
| `.gitlab-ci.yml` | CI/CD pipeline | 07-deploy |
| `sonar-project.properties` | SonarQube config | 07-deploy |
| `etc/nginx/nginx.conf` | Nginx config | 07-deploy |
| `etc/nginx/sites-enabled/ttrss` | Nginx site config | 07-deploy |
| `etc/php5/fpm/pool.d/www.conf` | PHP-FPM pool config | 07-deploy |
| `etc/rc.local` | Legacy startup script | 07-deploy |
| `etc/apt/sources.list` | APT sources (Ubuntu 14.04) | 07-deploy |
| `service/nginx/run` | runit nginx service | 07-deploy |
| `service/php5-fpm/run` | runit php-fpm service | 07-deploy |
| `service/update-feeds/run` | runit feed updater | 07-deploy |

## Third-Party Libraries (ttrss/lib/)

| Library | Files | Purpose |
|---------|-------|---------|
| Dojo Toolkit | `dojo/`, `dojo-src/` | Frontend framework |
| dijit | `dijit/` (hundreds of files) | UI widgets |
| Prototype.js + Scriptaculous | `scriptaculous/` | DOM/AJAX |
| PHPMailer | `phpmailer/` (30 files) | Email |
| MiniTemplator | `MiniTemplator.class.php` | Templates |
| Mobile_Detect | `Mobile_Detect.php` | Device detection |
| phpqrcode | `phpqrcode/` (17 files) | QR codes |
| OTPlib | `otphp/` (6 files) | TOTP auth |
| Text_LanguageDetect | `languagedetect/` (4 files) | Language detection |
| PubSubHubbub | `pubsubhubbub/` (2 files) | Real-time push |
| SphinxAPI | `sphinxapi.php` | Full-text search |
| JShrink | `jshrink/Minifier.php` | JS minification |
| gettext | `gettext/` (2 files) | i18n |
| floIcon/jimIcon | `floIcon.php`, `jimIcon.php` | Favicon parsing |
| CheckBoxTree | `CheckBoxTree.js` | Dojo tree extension |

## Other Assets

| Directory | Contents |
|-----------|----------|
| `ttrss/images/` | UI icons and images (~30 PNG/GIF) |
| `ttrss/locale/` | 18+ locale directories with .po/.mo files |
| `ttrss/templates/` | MiniTemplator templates (digest emails) |
| `ttrss/themes/` | UI themes (includes feedly theme) |
| `ttrss/cache/` | Runtime cache (images, export, upload, js) |
| `ttrss/lock/` | Daemon lock files |
| `ttrss/feed-icons/` | Cached feed favicons |
| `ttrss/install/` | Web installation wizard |
| `ttrss/utils/` | Utility scripts |

## File Size Summary (Application PHP only)

| Category | Files | Estimated Total Lines |
|----------|-------|-----------------------|
| Entry points | 11 | ~1,000 |
| Include files | 18 | ~7,000 |
| Handler classes | 10 | ~4,500 |
| Pref handler classes | 6 | ~3,000 |
| Database classes | 8 | ~800 |
| Feed processing | 6 | ~1,200 |
| Plugin system | 6 | ~700 |
| Logging/utility | 5 | ~400 |
| **Total application** | **70** | **~18,600** |
