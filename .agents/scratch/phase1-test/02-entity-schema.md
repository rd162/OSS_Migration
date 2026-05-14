---
dimension: entity-schema
spec-number: "02"
slug: entity-schema
title: "Entity / Schema Graph"
graph-artifact: tools/graph_analysis/output/db_table_graph.json
source-file: source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql
status: complete
phase: "∆8 synthesis"
date: 2025-01-27
---

# 02 — Entity / Schema Graph

## 1. Purpose

This dimension captures the relational data model of TT-RSS:
all 35 PostgreSQL tables,
their foreign-key dependency graph,
and the migration bootstrap order derived from that graph.

**Why it matters for modernisation:**

- The schema is the **lowest-level dependency** in the migration stack.
  SQLAlchemy models must be written before any business logic.
- The FK DAG determines the **order of model generation and Alembic migration scripts**.
  Level-0 tables must exist before Level-1 tables can be created.
- Two critical security findings live in this layer:
  SHA1 password hashing and mcrypt AES-128-CBC credential encryption.
  Both must be remediated as part of model construction, not deferred.
- The counter-cache subsystem (`ttrss_counters_cache`, `ttrss_cat_counters_cache`)
  uses a DB-level upsert pattern that maps to a specific SQLAlchemy idiom.
- Magic-number constants (`LABEL_BASE_INDEX = -1024`, `PLUGIN_FEED_BASE_INDEX = -128`)
  are embedded throughout application logic;
  they originate here and must be carried forward.

---

## 2. Graph structure

**Source artifact:** `tools/graph_analysis/output/db_table_graph.json`

| Metric | Value |
|--------|-------|
| Node type | Database table (one node per table) |
| Edge type | Foreign-key constraint (child_table → parent_table) |
| Node count | 60 (35 app tables + 25 file/class co-location nodes from graph builder) |
| Edge count | 126 |
| Community count | 6 |
| Graph type | Directed Acyclic Graph (DAG) after SCC condensation |

Extraction method:
parse `DROP TABLE` / `CREATE TABLE` / `REFERENCES` statements in
`source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`
via the `build_php_graphs.py` reference implementation.

Note: the 25 non-table nodes in the graph artifact are PHP file/class nodes
that co-locate with table access patterns in the call graph.
For this dimension spec only the 35 table nodes are relevant.

---

## 3. Communities

Six communities detected by Leiden algorithm (resolution ≈ 1.0).
Community labels assigned from dominant table semantics.

### Community 0 — Core Feed + Entry

| Table | FK level | Purpose |
|-------|---------|---------|
| `ttrss_users` | L0 | User accounts (login, pwd_hash, salt, otp_enabled, access_level=0/10) |
| `ttrss_feed_categories` | L1 | Feed categories; self-referential `parent_cat` FK |
| `ttrss_feeds` | L2 | Feed subscriptions (url, auth_pass, auth_pass_encrypted, pubsub_state) |
| `ttrss_archived_feeds` | L2 | Soft-deleted feeds retained for orphan-entry history |
| `ttrss_entries` | L3 | Global article store (guid UNIQUE, content, content_hash) |
| `ttrss_user_entries` | L4 | Per-user article state (read, starred, published, score, note) |
| `ttrss_access_keys` | L3 | Per-feed RSS sharing keys (UUID) |
| `ttrss_settings_profiles` | L1 | Named user settings profiles |

Characteristic pattern:
**global content + per-user projection**.
`ttrss_entries` stores article content once;
`ttrss_user_entries` stores per-user read/starred/score state,
keyed by `(ref_id → entries, feed_id → feeds, owner_uid → users)`.

### Community 1 — Labels + Tags + Enclosures

| Table | FK level | Purpose |
|-------|---------|---------|
| `ttrss_labels2` | L2 | Label definitions (caption, fg_color, bg_color, owner_uid) |
| `ttrss_user_labels2` | L4 | Per-user article↔label assignments (many-to-many join) |
| `ttrss_tags` | L4 | Free-form user tags on articles |
| `ttrss_enclosures` | L4 | Podcast/media enclosures on entries |

Special consideration:
labels act as **virtual feeds** with IDs starting at `LABEL_BASE_INDEX = -1024`.
This magic number permeates the API, feed-tree, and counter logic.

### Community 2 — User + Session

| Table | FK level | Purpose |
|-------|---------|---------|
| `ttrss_users` | L0 | (anchor — also in Community 0) |
| `ttrss_sessions` | L1 | DB-backed PHP session storage (to be replaced by Redis in Python) |
| `ttrss_settings_profiles` | L1 | (also in Community 0) |

Security note:
`ttrss_users.pwd_hash` stores `SHA1:<hex>` or `SHA1:<sha1(salt+pass)>`.
The admin seed row in the schema (`SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8`)
is SHA1 of the string `"password"` — with no salt.

### Community 3 — Filters

| Table | FK level | Purpose |
|-------|---------|---------|
| `ttrss_filter_types` | L0 | Enum: title(1), content(2), both(3), link(4), date(5), author(6), tag(7) |
| `ttrss_filter_actions` | L0 | Enum: filter(1), catchup(2), mark(3), tag(4), publish(5), score(6), label(7), stop(8) |
| `ttrss_filters2` | L1 | Filter definitions (match_any_rule, inverse, enabled, order_id) |
| `ttrss_filters2_rules` | L2 | Rule conditions (reg_exp PCRE, feed_id?, cat_id?, cat_filter) |
| `ttrss_filters2_actions` | L2 | Rule actions (action_id, action_param TEXT) |
| `ttrss_filters` | — | Legacy table (superseded by filters2; kept for migration path) |

Note:
`ttrss_filters2_rules.reg_exp` stores **PHP PCRE syntax** regular expressions.
Python `re` is not fully PCRE-compatible;
use the `regex` PyPI package for full compatibility.

### Community 4 — Preferences

| Table | FK level | Purpose |
|-------|---------|---------|
| `ttrss_prefs_types` | L0 | Type enum: bool(1), string(2), integer(3) |
| `ttrss_prefs_sections` | L0 | Sections: General(1), Interface(2), Advanced(3), Digest(4) |
| `ttrss_prefs` | L1 | Pref definitions (pref_name PK, type_id, section_id, def_value, access_level) |
| `ttrss_user_prefs` | L2 | Per-user pref overrides (owner_uid, pref_name, profile_id nullable, value TEXT) |

Pref access pattern:
`get_pref(pref_name, owner_uid)` queries `ttrss_user_prefs` first;
falls back to `ttrss_prefs.def_value`.
Result is typed by `type_id`: bool, int, or raw string.

Selected preference definitions:

| pref_name | type | default | Role |
|-----------|------|---------|------|
| `PURGE_OLD_DAYS` | int | 60 | Article retention window |
| `DEFAULT_UPDATE_INTERVAL` | int | 30 | Feed poll interval (minutes) |
| `ENABLE_FEED_CATS` | bool | true | Category mode toggle |
| `STRIP_UNSAFE_TAGS` | bool | true | HTML sanitization depth |
| `ENABLE_API_ACCESS` | bool | false | JSON API per-user gate |
| `FRESH_ARTICLE_MAX_AGE` | int | 24 | "Fresh" article window (hours) |
| `DIGEST_ENABLE` | bool | false | Email digest feature |
| `COMBINED_DISPLAY_MODE` | bool | true | CDM vs split-pane view |

Prefix `_` on pref names (e.g., `_DEFAULT_VIEW_MODE`) marks internal prefs;
these are not exposed in the preferences UI.
This is a naming convention, not enforced by a DB constraint.

### Community 5 — Infrastructure / Misc

| Table | FK level | Purpose |
|-------|---------|---------|
| `ttrss_counters_cache` | L2 | Per-feed unread count cache (no declared PK — app uses composite key) |
| `ttrss_cat_counters_cache` | L2 | Per-category unread count cache (same structure) |
| `ttrss_version` | L0 | Schema version (single row: `schema_version = 124`) |
| `ttrss_feedbrowser_cache` | L0 | Popular feeds browser cache (rebuilt periodically) |
| `ttrss_linked_feeds` | L0 | Federation: feeds from linked TT-RSS instances |
| `ttrss_linked_instances` | L0 | Federation: remote TT-RSS instance registry |
| `ttrss_error_log` | L1 | Application error log (errno, errstr, filename, lineno) |
| `ttrss_plugin_storage` | L1 | Plugin persistent data store (plugin_name, owner_uid, data TEXT JSON) |
| `ttrss_scheduled_updates` | L2 | On-demand feed update queue |
| `ttrss_entry_comments` | L3 | Article comments |

`ttrss_counters_cache` has **no declared primary key** in the SQL schema.
Application logic uses `(feed_id, owner_uid)` as a logical composite key.
SQLAlchemy model must declare `PrimaryKeyConstraint("feed_id", "owner_uid")`.

---

## 4. Dependency levels

Full topological order from FK DAG (Alembic migrations must follow this sequence):

```
Level 0 — No FK dependencies (create first)
  ttrss_users
  ttrss_prefs_types
  ttrss_prefs_sections
  ttrss_filter_types
  ttrss_filter_actions
  ttrss_version
  ttrss_themes
  ttrss_feedbrowser_cache
  ttrss_linked_instances

Level 1 — Depend only on Level 0
  ttrss_feed_categories     (→ users, self-ref parent_cat)
  ttrss_labels2             (→ users)
  ttrss_prefs               (→ prefs_types, prefs_sections)
  ttrss_settings_profiles   (→ users)
  ttrss_sessions            (→ users)
  ttrss_linked_feeds        (→ linked_instances)
  ttrss_error_log           (→ users)
  ttrss_plugin_storage      (→ users)

Level 2 — Depend on Level 0-1
  ttrss_feeds               (→ users, feed_categories)
  ttrss_archived_feeds      (→ users)
  ttrss_filters2            (→ users)
  ttrss_user_prefs          (→ users, prefs, settings_profiles)
  ttrss_counters_cache      (→ users)
  ttrss_cat_counters_cache  (→ users)
  ttrss_scheduled_updates   (→ users)

Level 3 — Depend on Level 0-2
  ttrss_entries             (no user FK — but semantic dep on feeds)
  ttrss_access_keys         (→ feeds, users)
  ttrss_filters2_rules      (→ filters2, filter_types, feeds, feed_categories)
  ttrss_filters2_actions    (→ filters2, filter_actions)

Level 4 — Depend on Level 0-3
  ttrss_user_entries        (→ entries, feeds, archived_feeds, users)
  ttrss_user_labels2        (→ labels2, user_entries)
  ttrss_tags                (→ users, user_entries)
  ttrss_enclosures          (→ entries)
  ttrss_entry_comments      (→ entries, users)
```

Self-referential FK:
`ttrss_feed_categories.parent_cat → ttrss_feed_categories(id) ON DELETE SET NULL`
requires `nullable=True` and SQLAlchemy `remote_side` argument.

---

## 5. Modernisation impact

### Target-side model mapping

| Source table | Python model class | SQLAlchemy notes |
|---|---|---|
| `ttrss_users` | `User` | `pwd_hash` Column(String(250)) — transitional; argon2id on write |
| `ttrss_feed_categories` | `FeedCategory` | self-referential `parent_cat`; `remote_side=[id]` |
| `ttrss_feeds` | `Feed` | `auth_pass` encrypted; `auth_pass_encrypted` bool flag |
| `ttrss_archived_feeds` | `ArchivedFeed` | separate model, not a `Feed` soft-delete flag |
| `ttrss_entries` | `Entry` | `guid` unique constraint; `content_hash` for delta detection |
| `ttrss_user_entries` | `UserEntry` | composite FK to entries+feeds+users; nullable `orig_feed_id` |
| `ttrss_labels2` | `Label` | `LABEL_BASE_INDEX = -1024` constant must be defined in Python |
| `ttrss_user_labels2` | `UserLabel` | explicit join-table model (not SQLAlchemy `secondary=`) |
| `ttrss_tags` | `Tag` | free-form strings; no normalisation; add unique(tag_name, owner_uid, post_int_id) |
| `ttrss_enclosures` | `Enclosure` | `duration` Column(Text) — do NOT coerce to `timedelta` |
| `ttrss_filters2` | `Filter` | `match_any_rule` → Python bool |
| `ttrss_filters2_rules` | `FilterRule` | `reg_exp` PCRE → Python `regex` package |
| `ttrss_filters2_actions` | `FilterAction` | `action_param` TEXT; parse by `action_id` type |
| `ttrss_filter_types` | `FilterType` (+ Python `IntEnum`) | keep DB table for FK; add Python enum alias |
| `ttrss_filter_actions` | `FilterActionType` (+ Python `IntEnum`) | same |
| `ttrss_prefs` | `Pref` | `pref_name` primary key |
| `ttrss_user_prefs` | `UserPref` | typed value access via property |
| `ttrss_counters_cache` | `CountersCache` | explicit `PrimaryKeyConstraint("feed_id", "owner_uid")` |
| `ttrss_cat_counters_cache` | `CatCountersCache` | same |
| `ttrss_plugin_storage` | `PluginStorage` | `data` Column(Text); add `@hybrid_property data_dict` |
| `ttrss_sessions` | *(drop)* | replaced by Flask-Login + Redis session store |
| `ttrss_version` | `SchemaVersion` | single-row; keep as Alembic compatibility shim |
| `ttrss_error_log` | `ErrorLog` | optional — consider Python structured logging instead |

### Security remediations in this layer

| Finding | Source location | Python remediation |
|---------|----------------|-------------------|
| SHA1 password hash | `ttrss_users.pwd_hash` seed: `SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8` | Dual-hash migration: detect `SHA1:` prefix on login → verify → re-hash with argon2id → commit |
| mcrypt AES-128-CBC feed credential encryption | `ttrss_feeds.auth_pass` + `include/crypt.php` | One-time migration: decrypt with `PyCryptodome` AES-128-CBC → re-encrypt with `cryptography.Fernet`; column `auth_pass_encrypted` tracks migration state |
| Direct SQL string interpolation in DB calls | `include/ccache.php`, `include/rssfuncs.php` | Replaced entirely by SQLAlchemy ORM / Core expressions; no raw string interpolation |
| Missing composite PK on cache tables | `ttrss_counters_cache`, `ttrss_cat_counters_cache` | Add `PrimaryKeyConstraint` in SQLAlchemy model |

### Magic constants that must be carried forward

```python
# Source: source-repos/ttrss-php/ttrss/include/functions.php lines 1-10
LABEL_BASE_INDEX: int = -1024   # Label IDs start at -1024; "feed_id < -1024 means label"
PLUGIN_FEED_BASE_INDEX: int = -128  # Plugin virtual feed IDs start at -128
SCHEMA_VERSION: int = 124           # Current schema version; must match DB at startup
EXPECTED_CONFIG_VERSION: int = 26   # Config.php version gate
```

These constants appear in conditional branches throughout `classes/api.php`,
`classes/feeds.php`, and `include/functions.php`.
They **must not be renumbered** — the API contract and DB data depend on them.

### Forced adaptations

1. **`sql_bool_to_bool` / `bool_to_sql_bool` removal:**
   PHP code uses these functions because PostgreSQL returns `'t'`/`'f'` strings
   from boolean columns when accessed via certain drivers.
   SQLAlchemy `Boolean` columns return Python `True`/`False` directly.
   All ~30 call sites in `include/functions.php` and `include/functions2.php`
   must be removed.

2. **DB-type branching SQL elimination:**
   `include/ccache.php`, `include/rssfuncs.php`, and `include/functions.php`
   contain conditional SQL branches like:
   ```php
   if (DB_TYPE == "pgsql") { $q = "NOW() - INTERVAL '15 minutes'"; }
   else { $q = "DATE_SUB(NOW(), INTERVAL 15 MINUTE)"; }
   ```
   SQLAlchemy's `func.now()` and `timedelta` expressions are dialect-agnostic.
   All ~20 such branches must be replaced with SQLAlchemy expressions.

3. **Manual transaction management replacement:**
   PHP code calls `db_query("BEGIN")` / `db_query("COMMIT")` explicitly
   in `include/ccache.php` and `include/rssfuncs.php`.
   Replace with `db.session.begin()` / `db.session.commit()` context managers
   or the implicit transaction in a Flask request context.

4. **Counter cache upsert:**
   `include/ccache.php::ccache_update()` implements a manual upsert
   (`BEGIN → SELECT → UPDATE or INSERT → COMMIT`).
   Replace with PostgreSQL `INSERT … ON CONFLICT DO UPDATE` via SQLAlchemy:
   ```python
   from sqlalchemy.dialects.postgresql import insert
   stmt = insert(CountersCache).values(feed_id=fid, owner_uid=uid, value=v)
   stmt = stmt.on_conflict_do_update(
       index_elements=["feed_id", "owner_uid"],
       set_={"value": stmt.excluded.value, "updated": func.now()}
   )
   db.session.execute(stmt)
   ```

5. **`ttrss_sessions` table migration:**
   The DB-backed session table is replaced by Flask-Login + Redis.
   During migration: read active sessions from `ttrss_sessions` → import to Redis
   (or force re-login — simpler and safer for a major version upgrade).
   Drop the `ttrss_sessions` table after cutover.

---

## 6. Source cross-references

| Item | Source location |
|------|----------------|
| Full schema (canonical) | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` |
| `ttrss_users` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 19–34 |
| `ttrss_feeds` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 41–78 |
| `ttrss_entries` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 93–112 |
| `ttrss_user_entries` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 113–133 |
| `ttrss_filters2*` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 160–197 |
| `ttrss_prefs*` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 220–270 |
| `ttrss_counters_cache` CREATE TABLE | `schema/ttrss_schema_pgsql.sql` lines 80–92 |
| Counter cache upsert logic | `source-repos/ttrss-php/ttrss/include/ccache.php` lines 40–130 |
| `sql_bool_to_bool` / `bool_to_sql_bool` | `source-repos/ttrss-php/ttrss/include/functions.php` lines 969–986 |
| `get_pref` / pref access | `source-repos/ttrss-php/ttrss/include/db-prefs.php` |
| `LABEL_BASE_INDEX`, `PLUGIN_FEED_BASE_INDEX` | `source-repos/ttrss-php/ttrss/include/functions.php` lines 1–10 |
| `SCHEMA_VERSION` constant | `source-repos/ttrss-php/ttrss/include/functions.php` line 3 |
| SHA1 password seed | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` lines 35–36 |
| mcrypt encryption | `source-repos/ttrss-php/ttrss/include/crypt.php` lines 1–40 |
| `initialize_user_prefs` | `source-repos/ttrss-php/ttrss/include/functions.php` lines 639–688 |
| DB-type branching SQL | `source-repos/ttrss-php/ttrss/include/ccache.php` lines 55–65, `include/rssfuncs.php` lines 3–5 |
| Schema migration versions | `source-repos/ttrss-php/ttrss/schema/versions/pgsql/` (versions 21–124) |
| `DbUpdater` class | `source-repos/ttrss-php/ttrss/classes/dbupdater.php` |
| Graph artifact | `tools/graph_analysis/output/db_table_graph.json` |
| Research notes | `.agents/scratch/phase1-test/research/DB-communities.md` |

---

*Dimension: 02-entity-schema · Phase: ∆8 synthesis · Status: complete*
*Generated from: ∆1 source inventory + ∆4 graph extraction + ∆6 DB community research*
*Next: feeds into `04-class-hierarchy.md` (model class mapping) and `09-security-surface.md` (SHA1/mcrypt remediations)*
