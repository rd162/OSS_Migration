# 02 — Database Spec

## Overview

- **Schema version**: 124 (tracked in `ttrss_version.schema_version`)
- **Supported engines**: MySQL 5.5+ and PostgreSQL (parallel schemas)
- **Migration system**: Incremental SQL files in `schema/versions/{mysql,pgsql}/`
- **Access pattern**: Raw SQL via `db_query()` — no ORM, no prepared statements

## Schema Files

| File | Purpose |
|------|---------|
| `ttrss/schema/ttrss_schema_mysql.sql` | Complete MySQL schema (CREATE TABLE + seed data) |
| `ttrss/schema/ttrss_schema_pgsql.sql` | Complete PostgreSQL schema |
| `ttrss/schema/versions/mysql/{3-124}.sql` | 124 MySQL migration scripts |
| `ttrss/schema/versions/pgsql/{3-124}.sql` | 122 PostgreSQL migration scripts |
| `ttrss/classes/dbupdater.php` | Migration runner (DbUpdater class) |

All paths relative to `source-repos/ttrss-php/`.

## Complete Table Inventory (35 tables)

### Core User Management

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_users` | User accounts | id, login, pwd_hash, access_level, last_login, salt, otp_enabled |
| `ttrss_sessions` | Session storage | id, data (base64), expire |
| `ttrss_access_keys` | API keys per user | id, access_key, feed_id, owner_uid |
| `ttrss_user_prefs` | Per-user preference overrides | owner_uid, pref_name, value, profile |
| `ttrss_settings_profiles` | Named preference profiles | id, title, owner_uid |

### Feed Management

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_feeds` | Feed subscriptions | id, owner_uid, title, feed_url, site_url, last_updated, update_interval, cat_id, auth_login, auth_pass, cache_images, pubsub_state |
| `ttrss_feed_categories` | Feed categories (hierarchical) | id, owner_uid, title, parent_cat |
| `ttrss_archived_feeds` | Historical feed records | id, owner_uid, title, feed_url, site_url |

### Article/Entry Management

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_entries` | Article content (shared) | id, title, link, guid, updated, content, content_hash, date_entered, date_updated, num_comments, author |
| `ttrss_user_entries` | User-specific article state | int_id, ref_id, owner_uid, feed_id, unread, marked, published, score, tag_cache, label_cache, last_read, note, orig_feed_id |
| `ttrss_entry_comments` | Article comments | id, ref_id, owner_uid, comment_type, updated |
| `ttrss_enclosures` | Media attachments | id, post_id, content_url, content_type, title, duration, width, height |

### Tagging & Labeling

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_tags` | Article tags | owner_uid, tag_name, post_int_id |
| `ttrss_labels2` | User labels with colors | id, owner_uid, caption, fg_color, bg_color |
| `ttrss_user_labels2` | Label-to-article mapping | label_id, article_id |

### Filtering System

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_filters2` | Filter rules | id, owner_uid, match_any_rule, enabled, inverse, title |
| `ttrss_filters2_rules` | Filter conditions | id, filter_id, reg_exp, inverse, filter_type, feed_id, cat_id, cat_filter |
| `ttrss_filters2_actions` | Filter actions | id, filter_id, action_id, action_param |
| `ttrss_filter_types` | Reference: filter types | id, name, description |
| `ttrss_filter_actions` | Reference: filter actions | id, name, description |

### Caching & Performance

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_counters_cache` | Feed unread count cache | feed_id, owner_uid, value, updated |
| `ttrss_cat_counters_cache` | Category unread count cache | feed_id, owner_uid, value, updated |
| `ttrss_feedbrowser_cache` | Public feed directory cache | feed_url, site_url, title, subscribers |

### Configuration

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_prefs` | System preference definitions | pref_name, type_id, def_value, section_id, short_desc, help_text |
| `ttrss_prefs_types` | Preference data types | id, type_name (bool, string, integer) |
| `ttrss_prefs_sections` | Preference UI sections | id, order_id |
| `ttrss_themes` | UI themes | id, theme_name |
| `ttrss_version` | Schema version tracking | schema_version |

### Plugin System

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_plugin_storage` | Plugin persistent data | id, owner_uid, name, content |

### Federation

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_linked_instances` | Remote TT-RSS connections | id, last_connected, last_status_in, last_status_out, access_key, access_url |
| `ttrss_linked_feeds` | Feeds from linked instances | feed_url, site_url, title, created, updated, instance_id, subscribers |

### Error Logging

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `ttrss_error_log` | Application errors | id, owner_uid, errno, errstr, filename, lineno, context, created_at |

### Deprecated / Removed (not in version 124 schema)

These tables are referenced in `DROP TABLE IF EXISTS` at the top of `ttrss_schema_pgsql.sql`
but have **no `CREATE TABLE`** in the version 124 base schema. They were removed in earlier
schema migrations and do not exist in production databases at version 124.

| Table | Status | Notes |
|-------|--------|-------|
| `ttrss_labels` | Removed (replaced by ttrss_labels2) | No CREATE TABLE in base schema |
| `ttrss_filters` | Removed (replaced by ttrss_filters2) | No CREATE TABLE in base schema |
| `ttrss_scheduled_updates` | Removed (unused) | No CREATE TABLE in base schema |
| `ttrss_themes` | Removed (dropped in migration v83) | No CREATE TABLE in base schema |

**Actual active table count at schema version 124: 31** (not 35 as originally estimated —
the 4 deprecated/removed tables above do not need SQLAlchemy models or Alembic migrations).

## Entity Relationship Diagram (Key Relationships)

```
ttrss_users (1)
 ├──→ (N) ttrss_feeds ──→ (N) ttrss_user_entries ──→ (1) ttrss_entries
 ├──→ (N) ttrss_feed_categories (self-referencing: parent_cat)
 ├──→ (N) ttrss_user_prefs
 ├──→ (N) ttrss_settings_profiles
 ├──→ (N) ttrss_labels2 ──→ (N) ttrss_user_labels2 ──→ (1) ttrss_entries
 ├──→ (N) ttrss_filters2
 │         ├──→ (N) ttrss_filters2_rules
 │         └──→ (N) ttrss_filters2_actions
 ├──→ (N) ttrss_tags ──→ (1) ttrss_user_entries
 ├──→ (N) ttrss_access_keys
 ├──→ (N) ttrss_plugin_storage
 └──→ (N) ttrss_error_log

ttrss_entries (1)
 ├──→ (N) ttrss_user_entries (bridge to users via feeds)
 ├──→ (N) ttrss_enclosures
 ├──→ (N) ttrss_entry_comments
 └──→ (N) ttrss_user_labels2

ttrss_linked_instances (1)
 └──→ (N) ttrss_linked_feeds
```

## Foreign Key Map (CASCADE behavior)

### ON DELETE CASCADE (data removed with parent)
- `ttrss_feeds` → `ttrss_users` (all feeds deleted when user deleted)
- `ttrss_feed_categories` → `ttrss_users`
- `ttrss_user_entries` → `ttrss_users`, `ttrss_feeds`, `ttrss_entries`
- `ttrss_tags` → `ttrss_users`, `ttrss_user_entries`
- `ttrss_labels2` → `ttrss_users`
- `ttrss_user_labels2` → `ttrss_labels2`, `ttrss_entries`
- `ttrss_filters2` → `ttrss_users`
- `ttrss_filters2_rules` → `ttrss_filters2`, `ttrss_filter_types`
- `ttrss_filters2_actions` → `ttrss_filters2`, `ttrss_filter_actions`
- `ttrss_user_prefs` → `ttrss_users`, `ttrss_prefs`
- `ttrss_access_keys` → `ttrss_users`
- `ttrss_plugin_storage` → `ttrss_users`
- `ttrss_enclosures` → `ttrss_entries`
- `ttrss_entry_comments` → `ttrss_entries`, `ttrss_users`
- `ttrss_linked_feeds` → `ttrss_linked_instances`
- `ttrss_settings_profiles` → `ttrss_users`
- `ttrss_user_prefs.profile` → `ttrss_settings_profiles`
- `ttrss_counters_cache` → `ttrss_users` (owner_uid only; `feed_id` is a bare integer with no FK constraint — verified against `ttrss_schema_pgsql.sql` lines 116–120)
- `ttrss_cat_counters_cache` → `ttrss_users` (owner_uid only; `feed_id` is a bare integer with no FK constraint — verified against `ttrss_schema_pgsql.sql` lines 126–130)

### ON DELETE SET NULL
- `ttrss_feeds.cat_id` → `ttrss_feed_categories` (feed becomes uncategorized)
- `ttrss_feeds.parent_feed` → `ttrss_feeds` (self-ref)
- `ttrss_feed_categories.parent_cat` → `ttrss_feed_categories` (self-ref)
- `ttrss_user_entries.orig_feed_id` → `ttrss_archived_feeds`
- `ttrss_error_log.owner_uid` → `ttrss_users`
- `ttrss_filters2_rules.feed_id` → `ttrss_feeds`
- `ttrss_filters2_rules.cat_id` → `ttrss_feed_categories`

## Seed Data

### Default Admin User
```sql
INSERT INTO ttrss_users (login, pwd_hash, access_level, salt)
VALUES ('admin', 'SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8', 10, '');
-- Default password: "password" (SHA1 hash)
```

### Default Feeds
```sql
-- 2 default TT-RSS feeds for the admin user
```

### Reference Data
- **Filter types** (7): title, content, both, link, date, author, tag
- **Filter actions** (8): filter, catchup, mark, tag, publish, score, label, stop
- **Preference types** (3): bool, string, integer
- **Preference sections** (4): General, Interface, Advanced, Digest
- **40+ system preferences** with default values

## Schema Extensions (Python-only columns, no PHP equivalent)

Columns added to existing tables during migration that have no counterpart in the PHP schema.
Each extension carries a `# New:` traceability comment in the model per AGENTS.md Rule 10.

| Table | Column | Type | Purpose | ADR |
|-------|--------|------|---------|-----|
| `ttrss_feeds` | `last_etag` | `varchar(250)` nullable | ETag from last feed fetch; sent as `If-None-Match` on next request | ADR-0015 |
| `ttrss_feeds` | `last_modified` | `varchar(250)` nullable | Last-Modified from last feed fetch; sent as `If-Modified-Since` on next request | ADR-0015 |

---

## Database Access Patterns

### Query Pattern (no prepared statements)
```php
// Typical pattern throughout codebase:
$result = db_query("SELECT id, title FROM ttrss_feeds
    WHERE owner_uid = " . $_SESSION["uid"] . "
    AND cat_id = " . db_escape_string($cat_id));
while ($line = db_fetch_assoc($result)) {
    // process row
}
```

### Transaction Pattern
```php
db_query("BEGIN");
// ... multiple operations ...
db_query("COMMIT");
```

### Multi-tenancy
All user-scoped tables include `owner_uid` column filtered in every query. No row-level security — enforced purely at application layer.

## Migration System (DbUpdater)

See `ttrss/classes/dbupdater.php`:
- Reads current version from `ttrss_version.schema_version`
- Applies sequential SQL files from `schema/versions/{db_type}/{version}.sql`
- Each migration wrapped in BEGIN/COMMIT
- Version 3 through 124 available

## Python Migration Notes

- **Recommended**: SQLAlchemy ORM with Alembic migrations
- **Key model**: `ttrss_user_entries` is the central bridge table — most complex queries involve it
- **Counter caches**: Consider replacing with materialized views or async counter updates
- **Dual DB**: SQLAlchemy abstracts MySQL/PostgreSQL differences
- **Schema migrations**: Alembic replaces the custom DbUpdater
