---
phase: "∆6"
title: "DB-Table Communities — Research Notes"
dimension: entity-schema
communities: [DB-0, DB-1, DB-2, DB-3, DB-4, DB-5]
method: "training-knowledge + source corpus reads"
status: "DEGRADED — no web search; training knowledge only"
date: 2025-01-27
---

# Dimension: entity-schema · Communities DB-0 through DB-5

⚠ DEGRADED: No web search available. Findings draw on direct source
corpus reads (`schema/ttrss_schema_pgsql.sql`, `include/ccache.php`,
`include/functions.php`, `include/db-prefs.php`) and training knowledge.
All [TRAINING] claims should be verified against current SQLAlchemy /
Alembic / Flask-SQLAlchemy docs before Phase 2 ADR drafting.

---

## DB-0 — Core Feed + Entry cluster

### Members

| Table | Level | Purpose |
|-------|-------|---------|
| `ttrss_users` | 0 (root) | User accounts — login, pwd_hash, salt, otp_enabled, access_level |
| `ttrss_feed_categories` | 1 | Feed categories — owner_uid FK to users; self-referential parent_cat |
| `ttrss_feeds` | 2 | Feed subscriptions — owner_uid, cat_id, feed_url, auth_pass_encrypted |
| `ttrss_archived_feeds` | 2 | Soft-deleted feeds retained for orphan-entry history |
| `ttrss_entries` | 3 | Global article store — guid UNIQUE, content, content_hash |
| `ttrss_user_entries` | 4 | Per-user article state — ref_id FK to entries, feed_id FK to feeds |
| `ttrss_access_keys` | 3 | Per-feed RSS sharing keys — feed_id FK to feeds |
| `ttrss_settings_profiles` | 1 | Named settings profiles per user |

**Dependency levels (from FK DAG):**

```text
ttrss_users (L0 — root; no FKs pointing out)
  ├─ ttrss_feed_categories (L1, self-ref parent_cat)
  │    └─ ttrss_feeds (L2) ─────────────────────┐
  │         └─ ttrss_user_entries (L4) ◄──────┐  │
  ├─ ttrss_archived_feeds (L2)                │  │
  ├─ ttrss_settings_profiles (L1)             │  │
  └─ ttrss_entries (L3, no user FK) ──────────┘  │
       └─ ttrss_user_entries (L4) ◄──────────────┘
```

Bootstrap order: users → feed_categories → feeds + archived_feeds → entries → user_entries.

### Representative constructs

- `ttrss_users.pwd_hash` stores `SHA1:<hex>` or `SHA1:<sha1(salt+pass)>` — see security-surface.
- `ttrss_feeds.auth_pass` is feed HTTP Basic Auth password; `auth_pass_encrypted` boolean
  signals whether it is encrypted via `include/crypt.php:encrypt_string()` (mcrypt AES-128-CBC).
- `ttrss_entries.guid` has `UNIQUE` constraint — deduplication key on feed re-fetch.
- `ttrss_user_entries` is the per-user "projection" of global entries onto feeds;
  it holds read/starred/published/score/note state per (user, entry) pair.
- `ttrss_feed_categories.parent_cat` self-referential FK allows arbitrary nesting
  but UI constrains to 2 levels in practice.
- `ttrss_access_keys` maps (feed_id, owner_uid) → UUID key for public RSS sharing.

### Research findings [TRAINING]

**Source-side patterns:**
- The global-entry / per-user-projection pattern (ttrss_entries + ttrss_user_entries) is a
  classic "shared content, per-user state" table split seen in multi-user feed readers.
  It avoids content duplication when multiple users subscribe to the same feed.
- `ttrss_user_entries.uuid` is distinct from `ttrss_entries.guid` — the uuid is for
  public sharing links; the guid is the feed-provided deduplication key.
- Self-referential FK on `ttrss_feed_categories.parent_cat` creates a tree structure
  requiring adjacency-list traversal; TT-RSS does not use nested-sets.

**Target-side mapping [TRAINING]:**
- SQLAlchemy `relationship("FeedCategory", remote_side="FeedCategory.id",
  back_populates="children")` for the self-referential parent_cat.
- `relationship("UserEntry", back_populates="entry")` on Entry;
  `relationship("UserEntry", back_populates="feed")` on Feed.
- `ttrss_archived_feeds` maps to a separate `ArchivedFeed` model (not soft-delete flag
  on feeds — the original schema uses a separate table to avoid FK cascade issues
  while preserving entry history).
- `ttrss_entries.guid` → `Column(Text, unique=True, nullable=False)`.
- `content_hash` (varchar 250) → `Column(String(250))` used for update-on-change detection.

### Divergences spotted

| D# | PHP pattern | Python gotcha |
|----|-------------|---------------|
| D1 | `bool_to_sql_bool` / `sql_bool_to_bool` functions convert 't'/'f' (pgsql) and '1'/'0' (mysql) | SQLAlchemy Boolean columns return Python `True`/`False` directly — these conversion functions must be removed |
| D2 | `ttrss_feeds.update_method` integer enum (0=default, 1=feed-defined, 2=feed_browser) | Map to Python `enum.IntEnum` or SQLAlchemy `Enum` type |
| D3 | `ttrss_user_entries.tag_cache` and `label_cache` are TEXT fields storing comma-separated tag/label names (denormalised cache) | Keep as String columns; cache invalidation logic must be replicated in Python |
| D4 | `ttrss_feed_categories.parent_cat` self-FK with `ON DELETE SET NULL` | SQLAlchemy `ForeignKey("ttrss_feed_categories.id", ondelete="SET NULL")` + `nullable=True` |
| D5 | `ttrss_user_entries.score` default 0; article scoring system via filters | Map to `Integer(default=0)` — no ORM-level validation needed |

### Open questions

- Should `ttrss_archived_feeds` be migrated as a separate model or merged into `Feed`
  with a `is_archived` boolean? (The PHP schema keeps them separate — recommend same in Python
  to preserve FK constraint semantics.) → ADR candidate.
- The `ttrss_user_entries.orig_feed_id` references `ttrss_archived_feeds(id)` ON DELETE SET NULL.
  This means when a feed is archived the user_entry retains the orig_feed_id pointer.
  SQLAlchemy relationship must be `nullable=True` with `passive_deletes=True`.

---

## DB-1 — Labels + Tags + Enclosures cluster

### Members

| Table | Level | Purpose |
|-------|-------|---------|
| `ttrss_labels2` | 2 | Label definitions — owner_uid, caption, fg_color, bg_color |
| `ttrss_user_labels2` | 4 | Per-user article↔label assignments (label_id FK, article_id FK to user_entries) |
| `ttrss_tags` | 4 | User-assigned tags on articles (tag_name, owner_uid, post_int_id FK to user_entries) |
| `ttrss_enclosures` | 4 | Media enclosures on articles (content_url, type, title, duration, post_id FK to entries) |

**Dependency levels:** users(L0) → labels2(L2) → user_labels2(L4) via user_entries.
Tags and enclosures at L4 (both depend on user_entries and entries respectively).

### Representative constructs

- `LABEL_BASE_INDEX = -1024`: labels appear as "virtual feeds" with negative IDs in the
  feed tree. `feed_id < 0` logic is pervasive in `include/functions.php` and `classes/feeds.php`.
- `ttrss_labels2.fg_color` / `bg_color` are varchar(11) storing CSS color strings.
- `ttrss_tags.tag_name` is not a FK to a tag table — tags are free-form strings.
  Tag uniqueness is enforced at application level, not DB level.
- `ttrss_enclosures.duration` is TEXT not INTERVAL — stores raw podcast duration string.

### Research findings [TRAINING]

**Source-side patterns:**
- Labels-as-virtual-feeds pattern: labels are displayed in the feed tree alongside
  real feeds. The `LABEL_BASE_INDEX` constant (-1024) is a magic number distinguishing
  label IDs from real feed IDs throughout the codebase.
- `ttrss_user_labels2` stores (label_id, article_id) pairs where article_id is
  `ttrss_user_entries.int_id` — it is a many-to-many join table.

**Target-side mapping [TRAINING]:**
- `Label` model with `owner: relationship("User")`.
- `UserLabel` as explicit many-to-many join table model (not SQLAlchemy `secondary=`
  because the join table has its own int PK and may acquire future columns).
- `Tag` model: `tag_name`, `owner_uid`, `post_int_id` — consider adding a unique
  constraint `(tag_name, owner_uid, post_int_id)` not present in PHP schema but
  implied by application-level deduplication.
- `Enclosure` model: `duration = Column(Text)` — do not attempt to parse as interval.

### Divergences spotted

| D# | PHP pattern | Python gotcha |
|----|-------------|---------------|
| D6 | `LABEL_BASE_INDEX = -1024` magic number used in conditional `feed_id < LABEL_BASE_INDEX` | Must carry same constant into Python; label IDs in feed tree API responses use the same negative-ID scheme |
| D7 | Tags are free-form strings; no normalisation table | Direct string storage — do NOT introduce a Tag normalisation table (changes API contract) |
| D8 | Enclosure duration is TEXT (e.g., "01:23:45") | Keep as Text; do not coerce to Python `timedelta` — existing clients may depend on string format |

---

## DB-2 — User + Session cluster

### Members

| Table | Level | Purpose |
|-------|-------|---------|
| `ttrss_users` | 0 | (also in DB-0 — core anchor) |
| `ttrss_sessions` | 1 | DB-backed PHP session storage (session key, data, expire) |
| `ttrss_settings_profiles` | 1 | Named settings profiles (title, owner_uid) |

### Representative constructs

- `ttrss_sessions` schema (from sessions.php inspection): `(id, data, expire)` columns
  used by PHP custom session handler `ttrss_open` / `ttrss_close` / `ttrss_write` / `ttrss_read`.
- `ttrss_users.resetpass_token` — password reset token stored in DB; expires not tracked
  in DB (token checked by email time heuristic in code).
- `ttrss_users.twitter_oauth` — legacy OAuth token column (unused in recent code).
- `ttrss_users.access_level` integer (0=user, 10=admin) used for access control.
- `ttrss_users.otp_enabled` boolean — TOTP second factor.

### Research findings [TRAINING]

**Source-side patterns:**
- PHP custom session handler writes serialised session data to `ttrss_sessions`;
  session ID is the PHP session key. Garbage collected by `session.gc_probability`.
- `ttrss_users.salt` is used only for the "salted" SHA1 variant; admin user's
  initial password (`5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8` = SHA1 of "password")
  has no salt.

**Target-side mapping [TRAINING]:**
- `ttrss_sessions` → DROP TABLE in Python migration. Flask-Login + Redis handles
  sessions; no DB session table needed.
  If DB sessions are required (no Redis): Flask-Session with SQLAlchemy backend,
  but the `ttrss_sessions` table schema does not need to be preserved.
- `User` model: `access_level` → `Column(Integer, default=0)`.
  Consider Python enum `AccessLevel(enum.IntEnum)` with `USER=0`, `ADMIN=10`.
- `otp_enabled` → `Column(Boolean, default=False)`.
- Password migration: `pwd_hash` field preserved during transition;
  dual-hash check on login; re-hash to argon2id; clear `salt` once migrated.

### Divergences spotted

| D# | PHP pattern | Python gotcha |
|----|-------------|---------------|
| D9 | `ttrss_sessions` DB table | Drop in Python; replaced by Flask-Login + Redis or cookie sessions |
| D10 | `SINGLE_USER_MODE` constant bypasses all auth checks | Must be implemented as app-config flag that skips `@login_required`; affects ~50 auth check sites |
| D11 | `access_level = 10` for admin (magic number) | Define `AccessLevel` enum to avoid magic numbers in Python code |
| D12 | `pwd_hash` column stores both salted and unsalted SHA1 (prefix `SHA1:`) | `pwd_hash` must remain varchar(250) to store argon2id hashes during transition; argon2id hashes are ~95 chars |

---

## DB-3 — Filters cluster

### Members

| Table | Level | Purpose |
|-------|-------|---------|
| `ttrss_filter_types` | 0 | Enum table: title(1), content(2), both(3), link(4), date(5), author(6), tag(7) |
| `ttrss_filter_actions` | 0 | Enum table: filter(1), catchup(2), mark(3), tag(4), publish(5), score(6), label(7), stop(8) |
| `ttrss_filters2` | 1 | Filter definition (owner_uid, match_any_rule, inverse, title, order_id, enabled) |
| `ttrss_filters2_rules` | 2 | Rule conditions (filter_id, reg_exp, inverse, filter_type, feed_id?, cat_id?) |
| `ttrss_filters2_actions` | 2 | Rule actions (filter_id, action_id, action_param) |
| `ttrss_filters` | — | Legacy table (superseded by filters2; must be preserved for migration) |

**Dependency levels:** filter_types + filter_actions (L0) → filters2 (L1) → rules + actions (L2).

### Representative constructs

- `ttrss_filters2.match_any_rule` boolean: if true, OR-semantics; if false, AND-semantics.
- `ttrss_filters2_rules.reg_exp` is a PHP regex string (PCRE syntax).
  ⚠ PHP PCRE → Python `re` has compatibility differences (named groups, some flags).
- `ttrss_filters2_rules.feed_id` and `cat_id` are optional (nullable FKs) — filter can be
  scoped to a specific feed, a category, or global (NULL).
- `ttrss_filters2_rules.cat_filter` boolean distinguishes "match articles in category" vs
  "match articles in specific feed".
- `action_param` is TEXT storing context-dependent values:
  for `score` action → integer string; for `label` action → label name string.

### Research findings [TRAINING]

**Source-side patterns:**
- Filter evaluation runs on every article ingestion in `include/rssfuncs.php`.
- Regex matching uses `preg_match` (PHP PCRE); Python uses `re.search`.
- Filter type enum is a lookup table with ID = integer literal used throughout.
  These integers are hardcoded in application logic (e.g., `$action["id"] == 7` for label).

**Target-side mapping [TRAINING]:**
- `FilterType` and `FilterAction` tables → Python `enum.IntEnum` constants
  OR keep as DB lookup tables (DB approach preserves foreign key constraints).
  Recommend keeping as DB tables for FK integrity; add corresponding Python enums
  as application-side aliases.
- `Filter` model with `rules: relationship("FilterRule")` and
  `actions: relationship("FilterAction")`.
- `FilterRule.reg_exp` → Python `re` compatibility layer needed.
  ⚠ PCRE `(?i)` is `re.IGNORECASE`; PCRE `\p{Lu}` Unicode categories not in `re` stdlib
  → use `regex` (PyPI) for full PCRE compatibility.

### Divergences spotted

| D# | PHP pattern | Python gotcha |
|----|-------------|---------------|
| D13 | PCRE regex in `reg_exp` (PHP `preg_match`) | Python `re` lacks PCRE named conditionals and some extensions; use `regex` PyPI package for full compatibility |
| D14 | `action_param` TEXT with implicit type (string for tag/label, integer string for score) | Add a property that parses `action_param` based on `action_id` — avoids magic string-to-int conversions scattered in application |
| D15 | filter_type and filter_action are DB lookup tables with hardcoded integer IDs | Wrap in Python `IntEnum`; ensure DB seed data matches enum values |

---

## DB-4 — Preferences cluster

### Members

| Table | Level | Purpose |
|-------|-------|---------|
| `ttrss_prefs_types` | 0 | Pref type enum: bool(1), string(2), integer(3) |
| `ttrss_prefs_sections` | 0 | Sections: General(1), Interface(2), Advanced(3), Digest(4) |
| `ttrss_prefs` | 1 | Pref definitions — pref_name PK, type_id, section_id, def_value, access_level |
| `ttrss_user_prefs` | 2 | Per-user overrides — owner_uid, pref_name, profile_id, value |

**Dependency levels:** prefs_types + prefs_sections (L0) → prefs (L1) → user_prefs (L2).

### Representative constructs (50+ pref keys from schema seed data)

Key prefs (selected):

| pref_name | type | default | Significance |
|-----------|------|---------|-------------|
| `PURGE_OLD_DAYS` | int | 60 | Article retention period |
| `DEFAULT_UPDATE_INTERVAL` | int | 30 | Feed poll interval (minutes) |
| `DEFAULT_ARTICLE_LIMIT` | int | 30 | Pagination size |
| `ENABLE_FEED_CATS` | bool | true | Category display toggle |
| `STRIP_UNSAFE_TAGS` | bool | true | XSS protection toggle |
| `ENABLE_API_ACCESS` | bool | false | JSON API enable per user |
| `FRESH_ARTICLE_MAX_AGE` | int | 24 | "Fresh" article window (hours) |
| `COMBINED_DISPLAY_MODE` | bool | true | CDM vs split-pane toggle |
| `DIGEST_ENABLE` | bool | false | Email digest feature |
| `_DEFAULT_VIEW_MODE` | str | adaptive | Feed view mode |

Pref names prefixed `_` are internal (not exposed in UI settings).

- `ttrss_user_prefs` links to `ttrss_settings_profiles` via `profile_id`
  (nullable FK — NULL = default profile).
- Access level integer in `ttrss_prefs.access_level` restricts pref visibility
  (0 = all users; 10 = admin only).

### Research findings [TRAINING]

**Source-side patterns:**
- `get_pref($pref_name, $owner_uid, $profile = false)` is the primary access function
  in `include/db-prefs.php`. It queries `ttrss_user_prefs` with fallback to `ttrss_prefs.def_value`.
- Pref values are always stored as strings; type_id governs parsing
  (`bool` → `sql_bool_to_bool()`; `int` → `intval()`; `string` → raw).
- `initialize_user_prefs($uid)` inserts default pref rows on new user creation.

**Target-side mapping [TRAINING]:**
- `Pref` model: `pref_name = Column(String(250), primary_key=True)`.
- `UserPref` model with `(owner_uid, pref_name, profile_id)` composite key.
- `get_pref()` → Python helper `get_pref(pref_name, user_id, profile_id=None)`.
  Returns typed Python value (bool, int, str) based on `Pref.type_id`.
- `initialize_user_prefs` → called in `User.on_create()` event or via SQLAlchemy
  `event.listen(User, 'after_insert', initialize_user_prefs_listener)`.
- Consider caching pref values in Flask `g` for request lifetime to avoid
  repeated `SELECT` per pref access (PHP had `PREFS_NO_CACHE` constant that disabled
  an in-memory cache — replicate cache in Python with `g.prefs_cache`).

### Divergences spotted

| D# | PHP pattern | Python gotcha |
|----|-------------|---------------|
| D16 | Pref values always stored as strings; converted by type_id | Python getter must apply type coercion; raw `value` column must remain `Text` |
| D17 | `sql_bool_to_bool()` converts 'true'/'false' strings | SQLAlchemy will NOT auto-convert TEXT columns storing 'true'/'false' to Python bool — need explicit property |
| D18 | `PREFS_NO_CACHE` constant disables in-memory cache during daemon runs | Python: separate code path for Celery workers (no `g` context) — use a simple dict cache per worker invocation |
| D19 | `_`-prefixed pref names are internal (convention, not enforced) | Document convention; do NOT add DB constraints — schema must match PHP exactly |

---

## DB-5 — Miscellaneous / Infrastructure cluster

### Members

| Table | Level | Purpose |
|-------|-------|---------|
| `ttrss_counters_cache` | 2 | Per-feed unread count cache (feed_id, owner_uid, value, updated) |
| `ttrss_cat_counters_cache` | 2 | Per-category unread count cache (same columns) |
| `ttrss_version` | 0 | Schema version (single row: schema_version = 124) |
| `ttrss_feedbrowser_cache` | — | Popular feeds cache (feed_url, title, site_url, subscribers count) |
| `ttrss_linked_feeds` | — | Linked TT-RSS instance feeds (federation — rarely used) |
| `ttrss_linked_instances` | — | Remote TT-RSS instance registry |
| `ttrss_error_log` | — | Application error log (owner_uid, errno, errstr, filename, lineno) |
| `ttrss_plugin_storage` | 1 | Plugin persistent data (plugin_name, owner_uid, data TEXT JSON) |
| `ttrss_scheduled_updates` | 2 | Queued on-demand feed update requests |
| `ttrss_entry_comments` | 3 | Article comments (ref_id FK entries, owner_uid, date_entered) |

### Representative constructs

- `ttrss_counters_cache` has no primary key — (feed_id, owner_uid) acts as composite key
  but is not declared in schema. ⚠ Python model needs explicit PK or composite unique.
- `ttrss_cat_counters_cache` same structure. feed_id=0 means "uncategorised".
- `ttrss_version` single-row table: `schema_version = 124`.
- `ttrss_plugin_storage.data` is TEXT storing JSON-serialised plugin data.
- `ttrss_error_log` columns correspond to PHP error handler fields
  (`include/errorhandler.php:ttrss_error_handler`).
- `ttrss_feedbrowser_cache` is rebuilt by `include/rssfuncs.php:update_feedbrowser_cache()`.

### Research findings [TRAINING]

**Counter cache subsystem:**
- `include/ccache.php` implements upsert-style cache management
  (`BEGIN` → `SELECT COUNT` → `UPDATE or INSERT` → `COMMIT`).
- Cache invalidation is synchronous (on article mark-read, feed catchup).
- Counter values are integer unread counts; `value = -1` indicates "not yet cached".

**Plugin storage subsystem:**
- `PluginHost::save_data($plugin_name, $owner_uid, $data)` serialises data as JSON
  and stores in `ttrss_plugin_storage.data` TEXT column.
- Query pattern: `WHERE plugin_name = 'X' AND owner_uid = Y` — implicit composite key.

**Target-side mapping [TRAINING]:**
- `CountersCache` + `CatCountersCache`: add explicit composite PK
  `PrimaryKeyConstraint("feed_id", "owner_uid")` in Python model.
- `PluginStorage.data`: `Column(Text)` storing JSON; add Python property
  `data_dict` that parses / serialises JSON for convenience.
- `ttrss_version` → Alembic handles schema versions; the table can be kept
  as a compatibility shim for queries like `get_schema_version()` but the
  authoritative version is Alembic's `alembic_version` table.
- `ttrss_error_log` → consider migrating to Python structured logging
  (structlog / loguru) instead of DB table; keep table for backwards compatibility
  with existing monitoring queries.
- `ttrss_feedbrowser_cache` → rebuild logic moves to a Celery periodic task.
- `ttrss_linked_feeds` / `ttrss_linked_instances` → low-priority federation feature;
  keep tables but mark as "feature-parity deferred" in divergence catalogue.

### Divergences spotted

| D# | PHP pattern | Python gotcha |
|----|-------------|---------------|
| D20 | `ttrss_counters_cache` has no declared PK | SQLAlchemy requires PK; add `PrimaryKeyConstraint("feed_id", "owner_uid")` — matches application semantics |
| D21 | Counter cache upsert uses manual `BEGIN … SELECT … UPDATE/INSERT … COMMIT` | Replace with SQLAlchemy `INSERT … ON CONFLICT DO UPDATE` (PostgreSQL `upsert` via `insert().on_conflict_do_update()`) |
| D22 | `ttrss_version` single-row schema version | Keep for backwards compat; Alembic is the authoritative migration tracker |
| D23 | `ttrss_plugin_storage.data` TEXT JSON | Add `@hybrid_property data_dict` parsing JSON; keep raw TEXT column |
| D24 | `ttrss_linked_feeds` / `ttrss_linked_instances` federation tables | Low-use feature — keep tables, defer Python business logic to post-Phase-3 |

---

## Cross-community observations

### FK DAG migration order (strict)

```text
Level 0: ttrss_users, ttrss_prefs_types, ttrss_prefs_sections,
         ttrss_filter_types, ttrss_filter_actions, ttrss_version
Level 1: ttrss_feed_categories, ttrss_labels2, ttrss_prefs,
         ttrss_settings_profiles, ttrss_sessions, ttrss_themes
Level 2: ttrss_feeds, ttrss_archived_feeds, ttrss_filters2,
         ttrss_user_prefs, ttrss_counters_cache, ttrss_cat_counters_cache,
         ttrss_feedbrowser_cache, ttrss_plugin_storage
Level 3: ttrss_entries, ttrss_access_keys,
         ttrss_filters2_rules, ttrss_filters2_actions
Level 4: ttrss_user_entries, ttrss_user_labels2, ttrss_tags,
         ttrss_enclosures, ttrss_entry_comments, ttrss_scheduled_updates
```

Alembic migration scripts must populate in this order to satisfy FK constraints.

### Shared divergences affecting multiple communities

| Issue | Tables | Impact |
|-------|--------|--------|
| `sql_bool_to_bool` / `bool_to_sql_bool` calls | user_entries, user_prefs, feeds, filters2 | Widespread; remove once SQLAlchemy Boolean columns used |
| DB-type branching SQL (`IF DB_TYPE == "pgsql"`) | ccache.php, functions.php, rssfuncs.php | ~20 branch sites; resolved by SQLAlchemy dialect abstraction |
| `db_query("BEGIN") / db_query("COMMIT")` manual transaction management | ccache, rssfuncs | Replace with `db.session.begin()` / `db.session.commit()` |
| Implicit NULL handling in `fetch_result` returning `false` on NULL | All | Python SQLAlchemy returns `None` — `if result:` conditionals need review |

---

## Target-side mapping summary

| DB community | Python model(s) | Key SQLAlchemy features |
|---|---|---|
| DB-0 (Core) | User, FeedCategory, Feed, ArchivedFeed, Entry, UserEntry, AccessKey | self-ref FK, cascade delete, composite FK, lazy relationships |
| DB-1 (Labels/Tags) | Label, UserLabel, Tag, Enclosure | many-to-many join model, free-form tag strings |
| DB-2 (User/Session) | User (extended), SettingsProfile | drop ttrss_sessions; Flask-Login integration |
| DB-3 (Filters) | Filter, FilterRule, FilterAction, FilterType (enum), FilterActionType (enum) | nullable scoped FKs, PCRE→re migration |
| DB-4 (Prefs) | Pref, UserPref | typed value access, request-cache pattern |
| DB-5 (Misc) | CountersCache, CatCountersCache, PluginStorage, FeedbrowserCache, ErrorLog | composite PK, JSON column, upsert pattern |
