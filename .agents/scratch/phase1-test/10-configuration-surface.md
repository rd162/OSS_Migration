# 10 — Configuration Surface

**Dimension**: `configuration-surface`
**Derivation**: Cross-cutting — `config.php-dist`, `include/sanity_config.php`,
`include/sanity_check.php`, `include/db-prefs.php` (DB-stored prefs),
include-graph C6 (sanity_check + sanity_config)
**Phase**: Phase 1
**Status**: extracted ✓ · research DEGRADED (no web access)

---

## Purpose

Captures all configuration constants, DB-stored preferences, and runtime
configuration validation. Drives the Python `pydantic Settings` model design
and the `ttrss_prefs` seed-data migration.

---

## Configuration layers

TT-RSS has two configuration layers:

1. **File-based constants** (`config.php` — `define()` calls) — deploy-time settings
2. **DB-stored preferences** (`ttrss_user_prefs`, `ttrss_prefs`) — per-user runtime settings

---

## Layer 1: File-based configuration constants

All defined in `config.php-dist` (operator copies to `config.php` and edits).
Source: `source-repos/ttrss-php/ttrss/config.php-dist`

### Database
| Constant | Default | Purpose |
|---|---|---|
| `DB_TYPE` | `"pgsql"` | Database engine: pgsql or mysql |
| `DB_HOST` | `"localhost"` | DB server hostname |
| `DB_USER` | `"fox"` | DB username |
| `DB_NAME` | `"fox"` | DB name |
| `DB_PASS` | `"XXXXXX"` | DB password |
| `DB_PORT` | `''` | DB port (5432 for pgsql, 3306 for mysql) |
| `MYSQL_CHARSET` | `'UTF8'` | MySQL connection charset |

### Application
| Constant | Default | Purpose |
|---|---|---|
| `SELF_URL_PATH` | (required) | Full URL of tt-rss installation |
| `FEED_CRYPT_KEY` | `''` | AES key for feed credential encryption (blank = no encryption) |
| `SINGLE_USER_MODE` | `false` | Disable multi-user, bypass auth |
| `SIMPLE_UPDATE_MODE` | `false` | Browser-triggered feed update (no daemon) |

### Files and directories
| Constant | Default | Purpose |
|---|---|---|
| `PHP_EXECUTABLE` | `/usr/bin/php` | PHP CLI path |
| `LOCK_DIRECTORY` | `'lock'` | Lock file directory |
| `CACHE_DIR` | `'cache'` | Feed content cache directory |
| `ICONS_DIR` / `ICONS_URL` | `"feed-icons"` | Feed favicon storage |

### Authentication
| Constant | Default | Purpose |
|---|---|---|
| `AUTH_AUTO_CREATE` | `true` | Auto-create users on external auth success |

### Session
| Constant | Default | Purpose |
|---|---|---|
| `SESSION_COOKIE_LIFETIME` | (required) | Session cookie lifetime (0 = browser session) |
| `SESSION_CHECK_ADDRESS` | `0` | IP-prefix session validation (0=none, 1=class-C, 2=class-B) |

### Update daemon
| Constant | Default | Purpose |
|---|---|---|
| `DAEMON_SLEEP_INTERVAL` | (int) | Daemon master loop sleep interval |
| `UPDATE_INTERVAL` | `3600` | Global feed update interval (seconds) |
| `DAEMON_FEED_LIMIT` | (int) | Max feeds per daemon child pass |

### SMTP
| Constant | Default | Purpose |
|---|---|---|
| `SMTP_SERVER` | `''` | SMTP server:port |
| `SMTP_LOGIN` | `''` | SMTP username |
| `SMTP_PASSWORD` | `''` | SMTP password |
| `SMTP_SECURE` | `''` | TLS mode: 'ssl', 'tls', or blank |
| `SMTP_FROM_NAME` | `'Tiny Tiny RSS'` | From name |
| `SMTP_FROM_ADDRESS` | `'noreply@...'` | From email address |
| `DIGEST_SUBJECT` | `'[tt-rss] News digest'` | Email digest subject prefix |

### Plugins
| Constant | Default | Purpose |
|---|---|---|
| `SYSTEM_PLUGINS` | `'auth_internal, note'` | Space/comma-separated system plugin names |

### PubSubHubbub
| Constant | Default | Purpose |
|---|---|---|
| `PUBSUBHUBBUB_HUB` | `''` | Hub URL for PubSubHubbub push (blank = polling only) |
| `PUBSUBHUBBUB_ENABLED` | `false` | Enable WebSub push |

---

## Layer 2: DB-stored user preferences (ttrss_prefs schema)

`ttrss_prefs` table defines ~50 preference keys. Selected key prefs:

| Pref name | Type | Default | Purpose |
|---|---|---|---|
| `ENABLE_API_ACCESS` | BOOL | false | Enable JSON API for this user |
| `USER_LANGUAGE` | STRING | `'auto'` | i18n locale |
| `ENABLE_FEED_CATS` | BOOL | true | Enable feed categories |
| `SORT_HEADLINES_BY_FEED_DATE` | BOOL | false | Sort by feed-reported date |
| `DIGEST_ENABLE` | BOOL | false | Enable email digest for this user |
| `DIGEST_CATCHUP` | BOOL | false | Mark digested articles as read |
| `OTP_SECRET_KEY` | STRING | `''` | TOTP secret for 2FA |
| `_ENABLED_PLUGINS` | STRING | `''` | Comma-separated user plugin names |
| `MARK_UNREAD_ON_UPDATE` | BOOL | false | Mark updated articles as unread |
| `PURGE_OLD_DAYS` | INTEGER | 60 | Days before article purge |
| `HIDE_READ_FEEDS` | BOOL | true | Hide feeds with no unread items |
| `FRESH_ARTICLE_MAX_AGE` | INTEGER | 24 | Hours threshold for "fresh" articles |

Full pref list: query `ttrss_prefs` table in a running installation, or read
`source-repos/ttrss-php/ttrss/install/index.php` (seed data for ttrss_prefs).

---

## Sanity check / config validation

`include/sanity_config.php`: validates all required constants are defined.
`include/sanity_check.php`: validates runtime environment:
- DB connectivity (`Db::get()` succeeds)
- Schema version matches `VERSION_STATIC`
- Required PHP extensions: mbstring, pcre, json, xml, curl, gd, iconv
- Writable directories: `CACHE_DIR`, `LOCK_DIRECTORY`, `ICONS_DIR`

Source: `source-repos/ttrss-php/ttrss/include/sanity_config.php`
Source: `source-repos/ttrss-php/ttrss/include/sanity_check.php`

---

## Python configuration model

```python
# ttrss/config.py — pydantic Settings
from pydantic import BaseSettings, validator

class TtrssSettings(BaseSettings):
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    # Application
    SELF_URL_PATH: str               # required
    FEED_CRYPT_KEY: str = ""         # blank = no encryption
    SINGLE_USER_MODE: bool = False
    SIMPLE_UPDATE_MODE: bool = False

    # Session
    SESSION_COOKIE_LIFETIME: int = 0
    SESSION_CHECK_ADDRESS: int = 0   # 0/1/2

    # Auth
    AUTH_AUTO_CREATE: bool = True

    # SMTP
    SMTP_SERVER: str = ""
    SMTP_LOGIN: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SECURE: str = ""            # ssl/tls/blank

    # Plugins
    SYSTEM_PLUGINS: str = "auth_internal, note"

    # Daemon (Celery equivalent)
    UPDATE_INTERVAL: int = 3600
    DAEMON_FEED_LIMIT: int = 100

    class Config:
        env_file = ".env"
        env_prefix = "TTRSS_"

    @validator("FEED_CRYPT_KEY")
    def warn_if_blank_crypt_key(cls, v):
        if not v:
            import warnings
            warnings.warn("FEED_CRYPT_KEY is blank — feed credentials stored unencrypted")
        return v
```

---

## Dependency levels (migration order)

Level 0: `TtrssSettings` model + `.env` loading
Level 1: DB connection config → Flask-SQLAlchemy `SQLALCHEMY_DATABASE_URI`
Level 2: SMTP config → flask-mail `MAIL_*` config
Level 3: Session config → Flask `SESSION_*` + Redis URL
Level 4: Plugin config → `SYSTEM_PLUGINS` loading at app startup
Level 5: Daemon config → Celery beat schedule constants

---

## Key divergences

**D-CF-01 — PHP define() → pydantic Settings** (severity: LOW):
PHP constants are global and immediately available. Python settings require
explicit import and injection (dependency injection pattern or app context).
All code that reads config constants must be refactored to read from settings object.
Frequency: pervasive. Severity: LOW (mechanical refactor).

**D-CF-02 — FEED_CRYPT_KEY blank default** (severity: MEDIUM):
Blank key means no feed credential encryption. Python target should warn or
enforce key presence. Severity: MEDIUM (security posture improvement).

**D-CF-03 — DB-stored pref seed data** (severity: MEDIUM):
`ttrss_prefs` table requires seed data (all valid pref names, types, defaults).
Alembic seed migration must insert ~50 rows. If seed data differs from PHP source,
pref reads will fail with missing key errors.
Source: `source-repos/ttrss-php/ttrss/install/index.php` (seed INSERT statements).

**D-CF-04 — ttrss_prefs varchar type coercion** (severity: MEDIUM):
All pref values stored as VARCHAR regardless of type. PHP coerces silently.
Python SQLAlchemy model must declare `TypeDecorator` or `hybrid_property` for
integer/boolean prefs. Missing coercion causes subtle pref value bugs.
Source: `source-repos/ttrss-php/ttrss/include/db-prefs.php`

---

## Source cross-references

| Construct | Source | Lines |
|---|---|---|
| Full config constants | `source-repos/ttrss-php/ttrss/config.php-dist` | full |
| Config validation | `source-repos/ttrss-php/ttrss/include/sanity_config.php` | full |
| Runtime sanity check | `source-repos/ttrss-php/ttrss/include/sanity_check.php` | full |
| `get_pref()` / `set_pref()` | `source-repos/ttrss-php/ttrss/include/db-prefs.php` | full |
| DB pref schema | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | `create table ttrss_prefs` |
| Pref seed data | `source-repos/ttrss-php/ttrss/install/index.php` | INSERT statements |
| `FEED_CRYPT_KEY` usage | `source-repos/ttrss-php/ttrss/include/crypt.php` | full |
| `SYSTEM_PLUGINS` loading | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | `load()` method |
| `VERSION_STATIC` | `source-repos/ttrss-php/ttrss/include/version.php` | full |
