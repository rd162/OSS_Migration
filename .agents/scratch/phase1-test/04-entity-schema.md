# 04 — Entity Schema

**Dimension**: `entity-schema`
**Artifact**: `tools/graph_analysis/output/db_table_graph.json`
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The entity schema graph captures **foreign-key dependency edges** between the
31 PostgreSQL tables in `ttrss_schema_pgsql.sql`.
Each node is a table name; each directed edge is a `REFERENCES` constraint
(child table → parent table).
The graph also includes source files that query those tables
(derived from the db_table extractor's query-access edges).

For the PHP → Python modernization this dimension:

- Defines the **SQLAlchemy ORM model class order** —
  tables with no FK parents must be defined first
- Provides the **Alembic migration ordering** —
  level-0 tables created first, level-4 tables last
- Surfaces **FK cascade behaviours** (`ON DELETE CASCADE`, `ON DELETE SET NULL`)
  that must be replicated in SQLAlchemy `relationship()` declarations
- Identifies **entity clusters** that form natural **bounded contexts**
  for service decomposition (if ever needed)
- Seeds the counter-cache and pref-storage divergence catalogue entries

---

## Graph structure

| Metric | Value |
|---|---|
| Nodes (tables + query-source files) | 60 |
| Edges (FK references + query-access) | 126 |
| Raw Leiden communities | 6 |
| Grouped research passes (∆5) | 6 (no grouping needed — all ≥ 2 nodes, well-separated) |
| Isolated singletons | 0 |
| Artifact | `tools/graph_analysis/output/db_table_graph.json` |

The low community count (6) relative to 31 tables reflects the tightly
interconnected FK structure of TT-RSS's schema: almost every table ultimately
references `ttrss_users`, creating a star-like dependency topology with
`ttrss_users` at the centre.

The graph includes both table→table FK edges and file→table query-access edges
(which is why node count is 60 rather than 31: 29 source files are included
as additional nodes representing query access patterns).

---

## Communities

### C0 — Feed core cluster (13 nodes)

**Table members**:
`ttrss_archived_feeds`, `ttrss_feeds`, `ttrss_feed_categories`,
`ttrss_entries`, `ttrss_settings_profiles`, `ttrss_access_keys`

**File members** (access pattern):
`classes/api.php`, `classes/feeds.php`, `classes/handler/public.php`,
`classes/pref/feeds.php`, `classes/pref/filters.php` (partial)

**Characterisation**:
The primary read/write tables for feed subscription management and article storage.
`ttrss_feeds` is the hub: it references `ttrss_users` (owner) and
`ttrss_feed_categories` (folder), and is itself referenced by
`ttrss_user_entries`, `ttrss_access_keys`, `ttrss_counters_cache`.
`ttrss_entries` is the global article store (deduplicated by GUID across users);
`ttrss_archived_feeds` stores soft-deleted feed metadata for orphan-entry attribution.

**FK relationships within cluster**:
```
ttrss_users ──→ ttrss_feed_categories (owner_uid, ON DELETE CASCADE)
ttrss_users ──→ ttrss_feeds (owner_uid, ON DELETE CASCADE)
ttrss_feed_categories ──→ ttrss_feeds (cat_id, ON DELETE SET NULL)
ttrss_feed_categories ──→ ttrss_feed_categories (parent_cat, self-FK, ON DELETE SET NULL)
ttrss_feeds ──→ ttrss_feeds (parent_feed, self-FK, ON DELETE SET NULL)
ttrss_users ──→ ttrss_settings_profiles (owner_uid, ON DELETE CASCADE)
ttrss_users ──→ ttrss_access_keys (owner_uid)
ttrss_feeds ──→ ttrss_access_keys (feed_id, ON DELETE CASCADE)
```

**SQLAlchemy models**:
- `Feed` — `__tablename__ = "ttrss_feeds"`; `owner = relationship("User")`,
  `category = relationship("FeedCategory")`, `parent = relationship("Feed")`
- `FeedCategory` — `__tablename__ = "ttrss_feed_categories"`;
  `parent = relationship("FeedCategory")` (self-referential)
- `Entry` — `__tablename__ = "ttrss_entries"` (global, no owner FK)
- `ArchivedFeed` — `__tablename__ = "ttrss_archived_feeds"`
- `SettingsProfile` — `__tablename__ = "ttrss_settings_profiles"`
- `AccessKey` — `__tablename__ = "ttrss_access_keys"`

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_feeds` (line ~38)
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_feed_categories` (line ~10)
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_entries` (line ~60)

**Research note**: `research/GRP-03-database-layer.md`

---

### C1 — User / Auth / Session cluster (13 nodes)

**Table members**:
`ttrss_error_log`, `ttrss_sessions`, `ttrss_version`,
`ttrss_users`

**File members** (access pattern):
`classes/auth/base.php`, `classes/dbupdater.php`,
`classes/pref/users.php`, `include/sessions.php`,
`install/index.php`, `plugins/auth_internal/init.php`,
`register.php`, `update.php`, (partial others)

**Characterisation**:
The user identity and infrastructure tables.
`ttrss_users` is the root anchor for the entire schema (every per-user table
references it). `ttrss_sessions` stores PHP session data (DB-backed session handler).
`ttrss_version` is a single-row table holding `schema_version`.
`ttrss_error_log` accumulates application errors per user.

**Key columns**:
- `ttrss_users`: `id`, `login`, `pwd_hash`, `email`, `access_level` (0=user, 10=admin),
  `last_login`, `created_at`, `salt`
- `ttrss_sessions`: `id` (session token), `data` (base64-encoded PHP-serialised array),
  `expire` (Unix timestamp)
- `ttrss_version`: `schema_version` (single integer row)
- `ttrss_error_log`: `id`, `owner_uid`, `errno`, `errstr`, `filename`, `lineno`, `context`

**FK relationships**:
```
ttrss_users ──→ ttrss_error_log (owner_uid, ON DELETE CASCADE)
```
`ttrss_sessions`, `ttrss_version` have no FK parents — they are independent tables.

**SQLAlchemy models**:
- `User` — `__tablename__ = "ttrss_users"`;
  `access_level: int`, `pwd_hash: str` (migrated to argon2id — see ADR-0008)
- `Session` — `__tablename__ = "ttrss_sessions"` (decommissioned in Python target;
  replaced by Flask-Login + Redis. Schema preserved for pgloader migration compatibility.)
- `SchemaVersion` — `__tablename__ = "ttrss_version"` (replaced by `alembic_version`)
- `ErrorLog` — `__tablename__ = "ttrss_error_log"`

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_users`
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_sessions`
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_version`
- `source-repos/ttrss-php/ttrss/include/sessions.php` — DB session handler callbacks

**Research note**: `research/GRP-06-auth-session.md`

---

### C2 — Filter + Label cluster (12 nodes)

**Table members**:
`ttrss_filters`, `ttrss_filter_types`, `ttrss_filter_actions`,
`ttrss_labels2`, `ttrss_filters2`, `ttrss_filters2_rules`,
`ttrss_filters2_actions`, `ttrss_user_labels2`

**File members** (access pattern):
`classes/pref/filters.php`, `classes/pref/labels.php`, `include/rssfuncs.php`

**Characterisation**:
The article-filtering and labelling subsystem.
Note: `ttrss_filters` is the legacy (v1) filter table — the active system
is `ttrss_filters2` (v2) with `ttrss_filters2_rules` and `ttrss_filters2_actions`.
The v1 `ttrss_filters` table may still contain data in migrated databases.
`ttrss_labels2` defines user-created labels; `ttrss_user_labels2` is the M2M
assignment table linking labels to article entries.

**FK relationships**:
```
ttrss_users ──→ ttrss_labels2 (owner_uid, ON DELETE CASCADE)
ttrss_users ──→ ttrss_filters2 (owner_uid, ON DELETE CASCADE)
ttrss_filter_types ──→ ttrss_filters2_rules (filter_type FK)
ttrss_filters2 ──→ ttrss_filters2_rules (filter_id, ON DELETE CASCADE)
ttrss_filter_actions ──→ ttrss_filters2_actions (action_id FK)
ttrss_filters2 ──→ ttrss_filters2_actions (filter_id, ON DELETE CASCADE)
ttrss_feeds ──→ ttrss_filters2_rules (feed_id, ON DELETE CASCADE, nullable)
ttrss_feed_categories ──→ ttrss_filters2_rules (cat_id, ON DELETE CASCADE, nullable)
ttrss_labels2 ──→ ttrss_user_labels2 (label_id)
ttrss_user_entries ──→ ttrss_user_labels2 (article_id = ref_id in user_entries)
```

**Filter type enum** (`ttrss_filter_types`):
title, content, both, link, date, author, tag, article_age, random, score, feed_title

**Filter action enum** (`ttrss_filter_actions`):
mark read, add star, assign label, stop processing, set score, assign category,
delete article

**SQLAlchemy models**:
- `FilterType` — `__tablename__ = "ttrss_filter_types"` (enum seed data)
- `FilterAction` — `__tablename__ = "ttrss_filter_actions"` (enum seed data)
- `Filter` — `__tablename__ = "ttrss_filters2"`;
  `rules = relationship("FilterRule", cascade="all, delete-orphan")`
- `FilterRule` — `__tablename__ = "ttrss_filters2_rules"`;
  `filter = relationship("Filter")`, `filter_type = relationship("FilterType")`
- `FilterActionEntry` — `__tablename__ = "ttrss_filters2_actions"`
- `Label` — `__tablename__ = "ttrss_labels2"`
- `UserLabel` — `__tablename__ = "ttrss_user_labels2"` (M2M association table)
- `LegacyFilter` — `__tablename__ = "ttrss_filters"` (preserve for migration, mark deprecated)

**Special consideration — label negative ID encoding**:
The TT-RSS API encodes label IDs as negative feed IDs: `label_feed_id = -(label.id + 11)`.
This formula is used throughout `classes/api.php`, `include/labels.php`,
and the JavaScript frontend. It MUST be preserved exactly.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_filters2`
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_labels2`
- `source-repos/ttrss-php/ttrss/include/labels.php` — label utility functions
- `source-repos/ttrss-php/ttrss/classes/pref/filters.php:101` — HOOK_QUERY_HEADLINES invocation

**Research note**: `research/GRP-04-prefs-filters.md`

---

### C3 — Preference + Counter cache cluster (10 nodes)

**Table members**:
`ttrss_user_labels2`, `ttrss_user_prefs`, `ttrss_counters_cache`,
`ttrss_cat_counters_cache`, `ttrss_prefs`,
`ttrss_prefs_types`, `ttrss_prefs_sections`

**File members** (access pattern):
`include/ccache.php`, `include/db-prefs.php`, `classes/db/prefs.php`

**Characterisation**:
The user-preference storage and read-count caching subsystem.
`ttrss_prefs` defines the global preference schema (all valid pref names,
their data types, and default values). `ttrss_user_prefs` stores per-user
overrides. `ttrss_counters_cache` and `ttrss_cat_counters_cache` store
computed unread-article counts per feed and per category respectively.

**Note**: `ttrss_user_labels2` appears in both C2 and C3 due to FK edges
to both cluster sets. Its primary identity is in C2 (filter/label cluster).

**FK relationships**:
```
ttrss_prefs_types ──→ ttrss_prefs (pref_type FK)
ttrss_prefs_sections ──→ ttrss_prefs (section_id FK)
ttrss_prefs ──→ ttrss_user_prefs (pref_name FK)
ttrss_users ──→ ttrss_user_prefs (owner_uid, ON DELETE CASCADE)
```
`ttrss_counters_cache` and `ttrss_cat_counters_cache` have NO FK constraints —
they are application-level caches with (feed_id, owner_uid) as composite key.

**Preference type enum** (`ttrss_prefs_types`):
`1` = bool, `2` = integer, `3` = string (stored as VARCHAR regardless)

**Preference section enum** (`ttrss_prefs_sections`):
General, Interface, Advanced, System

**Counter cache columns**:
- `ttrss_counters_cache`: `(feed_id INT, owner_uid INT, value INT, updated TIMESTAMP)`
- `ttrss_cat_counters_cache`: `(feed_id INT, owner_uid INT, value INT, updated TIMESTAMP)`
  (feed_id here refers to category_id — naming is misleading)
- 15-minute freshness window before recompute (`updated > NOW() - INTERVAL '15 minutes'`)
- No FK constraints — orphaned rows are cleaned by `ccache_remove()`

**SQLAlchemy models**:
- `PrefType` — `__tablename__ = "ttrss_prefs_types"` (enum seed)
- `PrefSection` — `__tablename__ = "ttrss_prefs_sections"` (enum seed)
- `PrefDefinition` — `__tablename__ = "ttrss_prefs"` (schema, seeded at migration)
- `UserPref` — `__tablename__ = "ttrss_user_prefs"`; `get(name, uid)` classmethod
- `CounterCache` — `__tablename__ = "ttrss_counters_cache"` (or Redis replacement)
- `CatCounterCache` — `__tablename__ = "ttrss_cat_counters_cache"` (or Redis replacement)

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_prefs`
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_counters_cache`
- `source-repos/ttrss-php/ttrss/include/ccache.php` — ccache_update(), ccache_find()
- `source-repos/ttrss-php/ttrss/include/db-prefs.php` — get_pref(), set_pref()

**Research note**: `research/GRP-04-prefs-filters.md`

---

### C4 — User-entry + Article state cluster (10 nodes)

**Table members**:
`ttrss_user_entries`, `ttrss_tags`, `ttrss_feedbrowser_cache`,
`ttrss_linked_feeds`, `ttrss_enclosures`, `ttrss_entry_comments`

**File members** (access pattern):
`classes/article.php`, `classes/feeds.php`, `classes/rpc.php`

**Characterisation**:
The per-user article state tables.
`ttrss_user_entries` is the pivot table between `ttrss_entries` (global)
and `ttrss_users` (per-user state): it records `unread`, `marked` (starred),
`published`, `score`, and `note` for each article per user.
This is the most write-heavy table in normal operation.
`ttrss_tags` stores per-article user-defined tag strings.
`ttrss_enclosures` stores podcast/media attachment metadata.
`ttrss_entry_comments` stores user-added comments on articles.
`ttrss_feedbrowser_cache` caches the public feed directory.
`ttrss_linked_feeds` stores cross-instance feed references (federation feature).

**FK relationships**:
```
ttrss_entries ──→ ttrss_user_entries (ref_id, ON DELETE CASCADE)
ttrss_feeds ──→ ttrss_user_entries (feed_id, ON DELETE CASCADE, nullable)
ttrss_archived_feeds ──→ ttrss_user_entries (orig_feed_id, ON DELETE SET NULL, nullable)
ttrss_users ──→ ttrss_user_entries (owner_uid, ON DELETE CASCADE)
ttrss_user_entries ──→ ttrss_tags (post_int_id FK)
ttrss_users ──→ ttrss_tags (owner_uid, ON DELETE CASCADE)
ttrss_entries ──→ ttrss_enclosures (post_id FK)
ttrss_entries ──→ ttrss_entry_comments (ref_id FK)
ttrss_users ──→ ttrss_entry_comments (owner_uid, ON DELETE CASCADE)
ttrss_linked_instances ──→ ttrss_linked_feeds (instance_id FK)
```

**ttrss_user_entries key columns**:
- `ref_id` → ttrss_entries.id (the global article)
- `feed_id` → ttrss_feeds.id (the subscription, nullable for archived)
- `orig_feed_id` → ttrss_archived_feeds.id (attribution after feed deletion)
- `owner_uid` → ttrss_users.id
- `unread BOOL` — unread state (drives counter cache)
- `marked BOOL` — starred/favourited
- `published BOOL` — re-shared to public feed
- `score INT` — article score (used by filter scoring actions)
- `note TEXT` — user-attached note
- `tag_cache TEXT` — denormalised comma-separated tag list (redundant with ttrss_tags)
- `label_cache TEXT` — denormalised label list (redundant with ttrss_user_labels2)

**Special consideration — tag and label denormalisation**:
`ttrss_user_entries.tag_cache` and `label_cache` are denormalised redundant copies
of the tag and label data maintained by the application layer.
These must be kept in sync during migrations. Python target should consider
whether to preserve this denormalisation or replace with computed properties.

**SQLAlchemy models**:
- `UserEntry` — `__tablename__ = "ttrss_user_entries"`;
  `entry = relationship("Entry")`, `feed = relationship("Feed")`,
  `owner = relationship("User")`
- `Tag` — `__tablename__ = "ttrss_tags"`
- `Enclosure` — `__tablename__ = "ttrss_enclosures"`
- `EntryComment` — `__tablename__ = "ttrss_entry_comments"`
- `FeedBrowserCache` — `__tablename__ = "ttrss_feedbrowser_cache"`
- `LinkedFeed` — `__tablename__ = "ttrss_linked_feeds"`

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_user_entries`
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_tags`
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_enclosures`
- `source-repos/ttrss-php/ttrss/classes/rpc.php` — mark-read, star, publish RPC ops
- `source-repos/ttrss-php/ttrss/classes/article.php` — article display + tag ops

**Research note**: `research/GRP-03-database-layer.md`

---

### C5 — Plugin storage cluster (2 nodes)

**Table members**: `ttrss_plugin_storage`

**File members**: `classes/pluginhost.php`

**Characterisation**:
Single-table cluster for plugin-specific persistent data.
`ttrss_plugin_storage` provides a simple per-plugin, per-user
key-value JSON store.

**Schema**:
```sql
create table ttrss_plugin_storage (
  id       serial primary key,
  name     varchar(250) not null,   -- plugin name (class name)
  owner_uid int not null references ttrss_users(id) ON DELETE CASCADE,
  content  text                     -- JSON-encoded PHP array
);
```

**Usage pattern**: `PluginHost::load_data($plugin)` / `save_data($plugin)` —
reads/writes the `content` column as `json_encode()` / `json_decode()` round-trip.
A unique index on `(name, owner_uid)` ensures one row per plugin per user.

**SQLAlchemy model**:
- `PluginStorage` — `__tablename__ = "ttrss_plugin_storage"`;
  `content = Column(JSON)` (PostgreSQL native JSON or JSONB)

**Migration note**: PHP `json_encode()` of PHP arrays and Python `json.dumps()`
of Python dicts produce compatible JSON for string/number/boolean values.
PHP integer-keyed arrays serialise as JSON objects `{"0": ..., "1": ...}` —
this edge case must be tested if any plugin uses integer-keyed arrays.

**Source cross-references**:
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` — `create table ttrss_plugin_storage`
- `source-repos/ttrss-php/ttrss/classes/pluginhost.php` — load_data() / save_data()

**Research note**: `research/GRP-05-plugin-system.md`

---

## Full table inventory and migration order

Migration must proceed from level 0 (no FK parents) to level 4 (maximum FK depth).
Alembic revisions must be written in this order.

### Level 0 — no FK parents (migrate first)

| Table | Purpose |
|---|---|
| `ttrss_users` | User accounts — root anchor for all per-user tables |
| `ttrss_version` | Single-row schema version counter |
| `ttrss_prefs_types` | Preference value type enum (seed data) |
| `ttrss_prefs_sections` | Preference section enum (seed data) |
| `ttrss_filter_types` | Filter condition type enum (seed data) |
| `ttrss_filter_actions` | Filter action type enum (seed data) |
| `ttrss_archived_feeds` | Archived/deleted feed metadata (no FK to active tables) |
| `ttrss_entries` | Global article store (GUID-deduplicated, no user FK) |
| `ttrss_sessions` | DB-backed PHP sessions (decommissioned in Python target) |
| `ttrss_counters_cache` | Feed unread count cache (no FK constraints) |
| `ttrss_cat_counters_cache` | Category unread count cache (no FK constraints) |
| `ttrss_feedbrowser_cache` | Public feed directory cache (no FK) |
| `ttrss_linked_instances` | Federation instance registry (no FK) |

### Level 1 — one FK hop from level 0

| Table | FK parents |
|---|---|
| `ttrss_feed_categories` | `ttrss_users` + self (parent_cat) |
| `ttrss_prefs` | `ttrss_prefs_types`, `ttrss_prefs_sections` |
| `ttrss_settings_profiles` | `ttrss_users` |
| `ttrss_labels2` | `ttrss_users` |
| `ttrss_filters2` | `ttrss_users` |
| `ttrss_enclosures` | `ttrss_entries` |
| `ttrss_entry_comments` | `ttrss_entries`, `ttrss_users` |
| `ttrss_linked_feeds` | `ttrss_linked_instances` |
| `ttrss_plugin_storage` | `ttrss_users` |
| `ttrss_error_log` | `ttrss_users` |

### Level 2 — two FK hops

| Table | FK parents |
|---|---|
| `ttrss_feeds` | `ttrss_users`, `ttrss_feed_categories`, `ttrss_feeds` (self) |
| `ttrss_user_prefs` | `ttrss_prefs`, `ttrss_users` |
| `ttrss_filters2_rules` | `ttrss_filters2`, `ttrss_filter_types`, `ttrss_feeds`?, `ttrss_feed_categories`? |
| `ttrss_filters2_actions` | `ttrss_filters2`, `ttrss_filter_actions` |

### Level 3 — three FK hops

| Table | FK parents |
|---|---|
| `ttrss_user_entries` | `ttrss_entries`, `ttrss_feeds`, `ttrss_archived_feeds`, `ttrss_users` |
| `ttrss_access_keys` | `ttrss_users`, `ttrss_feeds` |

### Level 4 — four FK hops (migrate last)

| Table | FK parents |
|---|---|
| `ttrss_user_labels2` | `ttrss_labels2`, `ttrss_user_entries` |
| `ttrss_tags` | `ttrss_user_entries`, `ttrss_users` |

---

## FK cascade behaviour inventory

Every `ON DELETE CASCADE` and `ON DELETE SET NULL` must be declared in
SQLAlchemy `relationship()` and `ForeignKey()` definitions.

| FK edge | Cascade behaviour |
|---|---|
| `ttrss_feed_categories.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_feed_categories.parent_cat` → `ttrss_feed_categories.id` | `SET NULL` |
| `ttrss_feeds.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_feeds.cat_id` → `ttrss_feed_categories.id` | `SET NULL` |
| `ttrss_feeds.parent_feed` → `ttrss_feeds.id` | `SET NULL` |
| `ttrss_user_entries.ref_id` → `ttrss_entries.id` | `CASCADE` |
| `ttrss_user_entries.feed_id` → `ttrss_feeds.id` | `CASCADE` |
| `ttrss_user_entries.orig_feed_id` → `ttrss_archived_feeds.id` | `SET NULL` |
| `ttrss_user_entries.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_filters2.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_filters2_rules.filter_id` → `ttrss_filters2.id` | `CASCADE` |
| `ttrss_filters2_actions.filter_id` → `ttrss_filters2.id` | `CASCADE` |
| `ttrss_labels2.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_access_keys.owner_uid` → `ttrss_users.id` | (implied CASCADE) |
| `ttrss_access_keys.feed_id` → `ttrss_feeds.id` | `CASCADE` |
| `ttrss_plugin_storage.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_error_log.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_tags.owner_uid` → `ttrss_users.id` | `CASCADE` |
| `ttrss_user_labels2.label_id` → `ttrss_labels2.id` | (implied) |
| `ttrss_user_labels2.article_id` → `ttrss_user_entries.ref_id` | (implied) |

---

## Modernization impact

### SQLAlchemy ORM model generation order
Following the FK dependency levels above, Alembic revisions and
SQLAlchemy model definitions must follow this sequence:

```
Revision 001: Level-0 tables (13 tables — no FK dependencies)
Revision 002: Level-1 tables (10 tables)
Revision 003: Level-2 tables (4 tables)
Revision 004: Level-3 tables (2 tables)
Revision 005: Level-4 tables (2 tables)
Revision 006+: Index creation, seed data (enum tables), counter cache triggers
```

### Forced adaptations

1. **`ttrss_sessions` decommission**:
   PHP DB-backed sessions → Flask-Login + Redis.
   The `ttrss_sessions` table is preserved in the Alembic schema for
   pgloader migration compatibility but is never written to by the Python app.
   A decommission revision drops the table after cut-over confirmation.
   Source: `source-repos/ttrss-php/ttrss/include/sessions.php:130`

2. **`ttrss_version` → `alembic_version`**:
   PHP's `DbUpdater` reads/writes `ttrss_version.schema_version`.
   Python target uses Alembic's `alembic_version` table exclusively.
   `ttrss_version` is preserved read-only to support the `validate_session()`
   compatibility check during dual-stack cutover if needed.
   Source: `source-repos/ttrss-php/ttrss/classes/dbupdater.php`

3. **`ttrss_user_entries` write patterns**:
   The unread/marked/published state columns are updated atomically via
   `BEGIN`/`COMMIT` in rssfuncs.php. Python SQLAlchemy uses session-scoped
   transactions — equivalent semantics but explicit `db.session.commit()` required.
   Source: `source-repos/ttrss-php/ttrss/include/rssfuncs.php`

4. **Counter cache tables vs Redis**:
   `ttrss_counters_cache` and `ttrss_cat_counters_cache` have no FK constraints
   and no indexes beyond the implicit PK. They are effectively application-managed
   cache tables. Python target has two options:
   a) Preserve as SQLAlchemy models with `SELECT FOR UPDATE` locking
   b) Replace with Redis `INCR`/`DECR` operations keyed by `(feed_id, owner_uid)`
   Architecture decision needed (ADR candidate).
   Source: `source-repos/ttrss-php/ttrss/include/ccache.php`

5. **`ttrss_filters` legacy table**:
   `ttrss_filters` (v1, non-2) appears in the schema. The active system is
   `ttrss_filters2`. Legacy rows may exist in production DBs.
   Python target should preserve the table in Alembic but mark the
   corresponding model as `LegacyFilter` with a deprecation warning.
   No new code should write to it.

6. **Tag and label denormalisation**:
   `ttrss_user_entries.tag_cache` and `label_cache` are redundant cached
   copies. Python ORM should maintain them via SQLAlchemy events
   (`@event.listens_for`) or explicit update in tag/label mutation operations.
   Alternatively, evaluate dropping the cache columns if the query cost
   of joining `ttrss_tags` is acceptable.

### Divergences seeded
- Counter cache race condition (see `12-semantic-discrepancies.md` D-06)
- Label negative-ID encoding formula (see `12-semantic-discrepancies.md` D-07)
- Session table decommission (see `12-semantic-discrepancies.md` D-03)
- Tag/label denormalisation synchronisation (see `12-semantic-discrepancies.md` D-08)
- Pref type coercion from VARCHAR (see `12-semantic-discrepancies.md` D-09)

---

## Source cross-references

| Construct | Source | Line(s) |
|---|---|---|
| Full PostgreSQL DDL | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | full |
| MySQL DDL (secondary) | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_mysql.sql` | full |
| Incremental migrations | `source-repos/ttrss-php/ttrss/schema/versions/` | numbered .sql files |
| `ttrss_feeds` table | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | ~38–72 |
| `ttrss_user_entries` table | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | ~90–120 |
| `ttrss_sessions` table | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | ~140–145 |
| `ttrss_plugin_storage` table | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | ~230–235 |
| `ttrss_filters2` table | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` | ~165–185 |
| DB adapter singleton | `source-repos/ttrss-php/ttrss/classes/db.php` | 1–50 |
| Schema version check | `source-repos/ttrss-php/ttrss/classes/dbupdater.php` | full |
| Counter cache logic | `source-repos/ttrss-php/ttrss/include/ccache.php` | full |
| Label negative-ID formula | `source-repos/ttrss-php/ttrss/include/labels.php` | `label_find_id()` |
| Pref read/write | `source-repos/ttrss-php/ttrss/include/db-prefs.php` | full |
| Tag cache update | `source-repos/ttrss-php/ttrss/classes/article.php` | `setArticleTags()` |

---

## Notes and caveats

- **Dual SQL engines**: The project ships both `ttrss_schema_pgsql.sql`
  and `ttrss_schema_mysql.sql`. The schemas are structurally equivalent
  but differ in syntax (`SERIAL` vs `AUTO_INCREMENT`, `BOOLEAN` vs `TINYINT(1)`,
  timestamp functions). The Python target standardises on PostgreSQL (ADR-0003);
  the MySQL schema is reference-only.

- **No explicit FOREIGN KEY constraint syntax**: The PostgreSQL DDL uses
  inline `references parent_table(id)` syntax rather than separate
  `CONSTRAINT ... FOREIGN KEY` blocks. The `REFERENCES` keyword was
  not found by case-sensitive grep — use case-insensitive grep
  (`grep -i references`) to enumerate all FK edges. All 126 edges in
  the graph were extracted correctly by `build_php_graphs.py`'s SQL parser.

- **`ttrss_linked_instances` / `ttrss_linked_feeds`**: Federation feature.
  Unclear if actively maintained. Audit invocation sites in PHP source
  before deciding whether to port or deprecate in Python target.

- **Research mode**: ∆6 community research ran in DEGRADED mode (no external
  web search). SQLAlchemy model design guidance from training knowledge only.
  Phase 2 should review current SQLAlchemy 2.x best practices (mapped classes,
  `DeclarativeBase`, `relationship()` with `back_populates`) before finalising
  the ORM model skeleton.

- **`ttrss_filters` legacy**: The schema contains both `ttrss_filters` (v1,
  columns: `id`, `owner_uid`, `filter_type`, `reg_exp`, `enabled`, `match_on`,
  `action_id`, `action_param`, `inverse`, `feed_id`, `cat_id`, `cat_filter`)
  AND `ttrss_filters2` (v2, normalised). All application code uses v2.
  The v1 table exists only for backward-compatibility data retention.
