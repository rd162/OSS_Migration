# Dimension: call-graph + class-hierarchy + db_table-graph + include-graph · Community: GRP-03 — Database layer + schema

⚠ RESEARCH MODE: DEGRADED — web search unavailable; training-knowledge-only.
All findings from source corpus reads + training knowledge. No T1 URL citations.

---

## Members

### Primary files
- `classes/db.php` (~50 LOC) — Db singleton, adapter factory
- `classes/idb.php` (~20 LOC) — IDb interface contract
- `classes/db/pgsql.php` — Db_Pgsql adapter
- `classes/db/mysqli.php` — Db_Mysqli adapter
- `classes/db/mysql.php` — Db_Mysql (legacy) adapter
- `classes/db/pdo.php` — Db_PDO adapter (optional, gated by `_ENABLE_PDO`)
- `classes/db/prefs.php` — Db_Prefs: DB-stored preference accessor
- `include/db.php` — global procedural wrappers (`db_query()`, `db_fetch_assoc()`, ...)
- `include/db-prefs.php` — procedural preference helpers (`get_pref()`, `set_pref()`)
- `classes/dbupdater.php` (~80 LOC) — schema version + incremental migration runner
- `schema/ttrss_schema_pgsql.sql` — canonical PostgreSQL DDL (31 tables)
- `schema/ttrss_schema_mysql.sql` — MySQL DDL mirror
- `schema/versions/` — incremental SQL migration scripts

### Call communities merged into GRP-03
- call C6 (54 nodes): Db_Mysql::connect, Db_Mysqli::connect, Db_PDO::connect,
  Db_Pgsql::connect, Db_PDO::last_error, Db_Pgsql::query, Db_Mysqli::query,
  DbUpdater::getSchemaVersion, DbUpdater::isUpdateRequired,
  DbUpdater::performUpdateTo, Pref_Prefs::otpenable, ...

### Class communities
- class C0 partial (db-related): Db, IDb, Db_Pgsql, Db_Mysqli, Db_PDO

### DB_TABLE communities (all 6)
- db_table C0 (13 nodes): ttrss_archived_feeds, ttrss_feeds, ttrss_feed_categories,
  ttrss_entries, ttrss_settings_profiles, ttrss_access_keys — feed core cluster
- db_table C1 (13 nodes): ttrss_error_log, ttrss_sessions, ttrss_version,
  ttrss_users, classes/auth/base.php — user/auth cluster
- db_table C2 (12 nodes): ttrss_filters, ttrss_filter_types, ttrss_filter_actions,
  ttrss_labels2, ttrss_filters2, ttrss_filters2_rules, ttrss_filters2_actions — filter cluster
- db_table C3 (10 nodes): ttrss_user_labels2, ttrss_user_prefs, ttrss_counters_cache,
  ttrss_cat_counters_cache, ttrss_prefs, ttrss_prefs_types, ttrss_prefs_sections — pref cluster
- db_table C4 (10 nodes): ttrss_user_entries, ttrss_tags, ttrss_feedbrowser_cache,
  ttrss_linked_feeds, ttrss_enclosures, ttrss_entry_comments — article/user-entry cluster
- db_table C5 (2 nodes): ttrss_plugin_storage, classes/pluginhost.php — plugin cluster

### Include community
- include C0 (14 nodes): classes/db.php, errors.php, include/autoload.php,
  include/functions.php, include/ccache.php, include/db-prefs.php, include/db.php,
  include/errorhandler.php, lib/accept-to-gettext.php, lib/gettext/gettext.inc,
  include/version.php, include/labels.php, lib/pubsubhubbub/publisher.php,
  include/sessions.php — bootstrap + core cluster

---

## Representative constructs

- `Db::get()` — singleton access point for DB connection
  (`source-repos/ttrss-php/ttrss/classes/db.php:44`)
- `IDb::query($sql)`, `IDb::fetch_assoc($result)` — adapter interface
  (`source-repos/ttrss-php/ttrss/classes/idb.php`)
- `db_query($sql)` — global wrapper: `Db::get()->query($sql)`
  (`source-repos/ttrss-php/ttrss/include/db.php`)
- `db_fetch_assoc($result)` — global wrapper: `Db::get()->fetch_assoc($result)`
  (`source-repos/ttrss-php/ttrss/include/db.php`)
- `DbUpdater::getSchemaVersion()` — reads `ttrss_version.schema_version`
  (`source-repos/ttrss-php/ttrss/classes/dbupdater.php`)
- `DbUpdater::performUpdateTo($target)` — runs SQL migration scripts sequentially
  (`source-repos/ttrss-php/ttrss/classes/dbupdater.php`)
- `get_pref($pref_name, $owner_uid)` — reads from `ttrss_user_prefs`
  (`source-repos/ttrss-php/ttrss/include/db-prefs.php`)
- `set_pref($pref_name, $value, $owner_uid)` — writes `ttrss_user_prefs`
  (`source-repos/ttrss-php/ttrss/include/db-prefs.php`)

---

## Full table inventory (31 tables from DDL)

| Table | Purpose | FK parents | Level |
|---|---|---|---|
| `ttrss_users` | User accounts (login, pwd_hash, email, access_level) | — | 0 |
| `ttrss_version` | Single-row schema version tracker | — | 0 |
| `ttrss_prefs_types` | Preference value type enum | — | 0 |
| `ttrss_prefs_sections` | Preference section enum | — | 0 |
| `ttrss_filter_types` | Filter condition type enum | — | 0 |
| `ttrss_filter_actions` | Filter action type enum | — | 0 |
| `ttrss_feed_categories` | Feed folder/category (owner_uid FK, parent_cat self-FK) | ttrss_users | 1 |
| `ttrss_prefs` | Global pref schema (pref_name PK, type, section) | ttrss_prefs_types, ttrss_prefs_sections | 1 |
| `ttrss_feeds` | Feed subscriptions (owner_uid, cat_id, parent_feed self-FK) | ttrss_users, ttrss_feed_categories | 2 |
| `ttrss_archived_feeds` | Soft-deleted feed archive | — | 0 |
| `ttrss_entries` | Global article store (guid, title, content, date_entered) | — | 0 |
| `ttrss_user_entries` | Per-user article state (ref_id→entries, feed_id→feeds) | ttrss_entries, ttrss_feeds, ttrss_archived_feeds, ttrss_users | 3 |
| `ttrss_user_prefs` | Per-user pref values (pref_name→prefs, owner_uid→users) | ttrss_prefs, ttrss_users | 2 |
| `ttrss_settings_profiles` | Named pref profiles per user | ttrss_users | 1 |
| `ttrss_sessions` | DB-stored PHP sessions (id, data, expire) | — | 0 |
| `ttrss_counters_cache` | Per-feed unread count cache (feed_id, owner_uid, value) | — | 0 |
| `ttrss_cat_counters_cache` | Per-category unread count cache | — | 0 |
| `ttrss_labels2` | User-defined article labels (owner_uid FK) | ttrss_users | 1 |
| `ttrss_user_labels2` | Label↔article assignment (label_id, article_id) | ttrss_labels2, ttrss_user_entries | 4 |
| `ttrss_filters2` | Filter definitions (owner_uid FK) | ttrss_users | 1 |
| `ttrss_filters2_rules` | Filter rule conditions (filter_id, filter_type) | ttrss_filters2, ttrss_filter_types | 2 |
| `ttrss_filters2_actions` | Filter action bindings (filter_id, action_id) | ttrss_filters2, ttrss_filter_actions | 2 |
| `ttrss_tags` | Per-article tags (post_int_id→user_entries, owner_uid) | ttrss_user_entries, ttrss_users | 4 |
| `ttrss_enclosures` | Podcast/media attachments (post_id→entries) | ttrss_entries | 1 |
| `ttrss_entry_comments` | Article comments (ref_id→entries, owner_uid) | ttrss_entries, ttrss_users | 1 |
| `ttrss_feedbrowser_cache` | Feed discovery cache (URL, subscribers, feed_url) | — | 0 |
| `ttrss_linked_instances` | Federated instance registry | — | 0 |
| `ttrss_linked_feeds` | Cross-instance feed references | ttrss_linked_instances | 1 |
| `ttrss_access_keys` | Per-user feed access tokens (owner_uid, feed_id) | ttrss_users, ttrss_feeds | 3 |
| `ttrss_plugin_storage` | Plugin key-value store (name, owner_uid, content JSON) | ttrss_users | 1 |
| `ttrss_error_log` | Application error log (owner_uid, errno, errstr) | ttrss_users | 1 |

Migration order (ascending FK level): level-0 tables first → level-4 last.

---

## DB_TABLE dependency levels

```
Level 0 (no FK parents — migrate first):
  ttrss_users, ttrss_version, ttrss_prefs_types, ttrss_prefs_sections,
  ttrss_filter_types, ttrss_filter_actions, ttrss_archived_feeds,
  ttrss_entries, ttrss_sessions, ttrss_counters_cache,
  ttrss_cat_counters_cache, ttrss_feedbrowser_cache, ttrss_linked_instances

Level 1:
  ttrss_feed_categories, ttrss_prefs, ttrss_settings_profiles,
  ttrss_labels2, ttrss_filters2, ttrss_enclosures, ttrss_entry_comments,
  ttrss_linked_feeds, ttrss_plugin_storage, ttrss_error_log

Level 2:
  ttrss_feeds, ttrss_user_prefs, ttrss_filters2_rules, ttrss_filters2_actions

Level 3:
  ttrss_user_entries, ttrss_access_keys

Level 4 (migrate last):
  ttrss_user_labels2, ttrss_tags
```

---

## Research findings (training-knowledge-only — DEGRADED)

### DB adapter pattern
- `Db` is a Singleton (GoF) wrapping an adapter (`IDb` interface).
- Adapters: `Db_Pgsql` (pg_query/pg_fetch_assoc), `Db_Mysqli` (mysqli_*),
  `Db_Mysql` (legacy mysql_* — removed PHP 7), `Db_PDO` (PDO::prepare/execute,
  gated by `_ENABLE_PDO` constant).
- All application code calls `Db::get()->query($sql)` or the global
  wrapper `db_query($sql)` — no ORM, raw SQL strings throughout.
- String escaping: `Db::get()->escape_string($val)` — NOT prepared statements.
  SQL injection risk is pervasive in the codebase.
- PostgreSQL is the primary/recommended engine; MySQL is secondary.

### Schema migration
- `DbUpdater` reads `ttrss_version.schema_version`, compares to
  `VERSION_STATIC` in `include/version.php`, then runs numbered SQL
  scripts from `schema/versions/NNN.sql` sequentially.
- No transactional rollback on migration failure — partial migrations possible.
- Schema version is also checked in `validate_session()` — session
  invalidated on schema change (forces re-login after migration).

### Pref storage
- `ttrss_prefs` defines the schema (pref_name, type, section, def_value).
- `ttrss_user_prefs` stores per-user overrides (pref_name, owner_uid, value).
- `get_pref($name, $uid)` returns user value or falls back to `def_value`.
- Preferences are typed (INTEGER, STRING, BOOL) via `ttrss_prefs_types`
  but stored as VARCHAR — type coercion happens in PHP.

### Counter cache
- `ttrss_counters_cache` and `ttrss_cat_counters_cache` are write-through
  caches maintained by `include/ccache.php`.
- Cache invalidated by `ccache_remove()` on article state change;
  rebuilt lazily by `ccache_update()`.
- 15-minute freshness window checked before recomputing.

### Known PHP → Python divergences

1. **Raw SQL strings → SQLAlchemy**: Every `db_query("SELECT ...")` call
   must be replaced with parameterised SQLAlchemy Core or ORM queries.
   Grep count: >500 occurrences of `db_query(` across the codebase.
   Severity: HIGH — largest single migration effort.

2. **Db singleton → Flask-SQLAlchemy**: The `Db::get()` singleton pattern
   maps to Flask-SQLAlchemy's `db` application-scoped engine. Connection
   pooling managed by SQLAlchemy engine, not manual adapter.

3. **Multi-engine support (MySQL/PostgreSQL)**: Python target should
   standardise on PostgreSQL (ADR-0003); MySQL support can be dropped
   if ADR confirms this. Eliminates the adapter layer entirely.

4. **`escape_string()` anti-pattern**: Pervasive use of manual string
   escaping instead of prepared statements. Python SQLAlchemy parameterised
   queries eliminate this entire class of risk.

5. **Pref type coercion**: PHP coerces VARCHAR preference values to int/bool
   silently. SQLAlchemy models must declare correct column types and
   apply explicit coercion in property setters.

6. **Schema migration**: `DbUpdater` sequential-SQL runner → Alembic
   with `autogenerate` + version-stamped migration scripts. Alembic is
   transactional per revision on PostgreSQL — safer than current approach.

7. **Counter cache tables**: `ttrss_counters_cache` and `ttrss_cat_counters_cache`
   are application-level caches. Python target may replace with Redis
   counters or retain the DB cache tables. Architecture decision needed.

8. **`ttrss_sessions` DB session store**: PHP writes serialised session
   data as base64 to this table. Python Flask-Login replaces with
   Redis session store (server-side) or signed cookie (client-side).

---

## Target-side mapping

| PHP construct | Python/SQLAlchemy equivalent | Notes |
|---|---|---|
| `Db::get()` singleton | `db = SQLAlchemy(app)` | Flask-SQLAlchemy app-scoped |
| `db_query($sql)` | `db.session.execute(text(sql), params)` | Parameterised |
| `db_fetch_assoc($r)` | `.mappings().all()` / `Row._mapping` | Dict-like row access |
| `escape_string($val)` | Removed — use bound params | Security improvement |
| `IDb` interface | SQLAlchemy `Engine` / dialect | Abstraction at engine level |
| `DbUpdater` migration runner | Alembic revision runner | Transactional on PG |
| `ttrss_version` | `alembic_version` table | Alembic manages this |
| `get_pref($name, $uid)` | `UserPref.get(name, uid)` model method | ORM lookup |
| `set_pref($name, $val, $uid)` | `UserPref.set(name, val, uid)` | ORM upsert |
| `ccache_update()` | `CounterCache.update()` or Redis INCR | TBD: DB vs Redis |
| `ttrss_sessions` table | Flask-Login + Redis session store | Replace DB sessions |

---

## Divergences spotted

1. **SQL injection surface**: Entire codebase uses `escape_string()` instead
   of prepared statements. Every query is a potential injection point.
   Python target must use parameterised queries throughout.
   Frequency: >500 occurrences. Severity: CRITICAL.

2. **Partial migration risk**: `DbUpdater` has no rollback. Alembic on
   PostgreSQL is transactional per revision. Existing migration scripts
   (schema/versions/*.sql) must be converted to Alembic revisions.
   Frequency: each deployment. Severity: HIGH.

3. **Counter cache consistency**: The ccache is updated in PHP with
   explicit `BEGIN`/`COMMIT` but no locking — concurrent updates can
   produce stale counts. Python target should use SELECT FOR UPDATE
   or Redis atomic INCR. Frequency: every article state change.
   Severity: MEDIUM.

4. **MySQL charset issues**: `MYSQL_CHARSET` config handles legacy charsets.
   Python PostgreSQL-only target eliminates this. Positive divergence.

5. **ttrss_settings_profiles**: Named preference profiles (per user).
   Not widely referenced in the codebase — may be partially implemented.
   Python target should preserve the schema but verify feature completeness.
   Frequency: low. Severity: LOW.

---

## Open questions

1. Confirm: MySQL support dropped in Python target? (ADR-0003 scope.)
2. Counter cache: retain DB tables or migrate to Redis INCR?
3. `ttrss_settings_profiles`: full feature or vestigial? Audit needed.
4. `ttrss_linked_instances` / `ttrss_linked_feeds`: federation feature —
   active or dead code? Grep invocations needed.
5. Alembic autogenerate or hand-write each revision from schema/versions/*.sql?
