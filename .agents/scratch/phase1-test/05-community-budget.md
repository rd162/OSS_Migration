# ∆5 — Community Research Budget & Grouping Plan

## Raw community counts from ∆4 graphs

| Dimension    | Nodes | Edges | Raw communities |
| ------------ | ----- | ----- | --------------- |
| call         | 1206  | 2086  | 305             |
| include      | 139   | 66    | 85              |
| class        | 81    | 27    | 55              |
| db_table     | 60    | 126   | 6               |
| hook         | 40    | 39    | 7               |
| **Total**    | —     | —     | **458**         |

N = 458 >> 50 → apply all heuristics aggressively.

---

## Heuristic 1 — Cross-dimension co-location merges

Files appearing in multiple dimension communities simultaneously:

| File cluster                                     | call-comm | include-comm | class-comm | → merged group |
| ------------------------------------------------ | --------- | ------------ | ---------- | -------------- |
| `classes/api.php`, `classes/feeds.php`, `classes/backend.php` | 0, 1  | 2    | 0, 1       | CG-1 Core App  |
| `include/functions.php`, `classes/db.php`, `include/db.php`   | 0, 11 | 0    | 16         | CG-1 Core App  |
| `classes/auth/base.php`, `plugins/auth_internal/init.php`     | 2, 6  | 5    | 8, 9       | CG-3 Auth      |
| `lib/phpqrcode/*`                                | 3       | 1            | —          | CG-4 QR lib    |
| `lib/phpmailer/*`                                | 4       | 3            | 5          | CG-5 Mailer    |
| `classes/feeditem/*`, `classes/feedparser.php`   | 5       | 2            | 2          | CG-6 Parsing   |
| `classes/handler/public.php`, `include/digest.php` | 7     | 3            | 1          | CG-7 Digest    |
| `classes/opml.php`                               | 8       | —            | —          | CG-8 OPML      |

## Heuristic 2 — Absorb tiny communities (< 3 nodes)

Call graph communities 20–305 are overwhelmingly 1–2 members.
Actions:
- Singleton Db adapter methods (comm 38–62): absorbed into **CG-12 Infrastructure** (same subsystem prefix `Db_*`).
- Singleton PluginHost methods (comm 105–120): absorbed into **CG-1 Core App**.
- Singleton Handler/Pref methods (comm 120–131): absorbed into **CG-1 Core App**.
- Singleton QR code internals (comm 200–249): absorbed into **CG-4 QR lib**.
- Singleton PHPMailer internals (comm 178–201): absorbed into **CG-5 Mailer**.
- Singleton i18n readers (comm 146–158): absorbed into **CG-11 gettext/i18n**.

Class graph singletons (comm 9–54): absorbed into nearest match:
- Db_*, Db → **CG-12 Infrastructure**
- DbUpdater → **CG-3 Auth** (schema migration path)
- FeedEnclosure, FeedParser → **CG-6 Parsing**

Include graph singletons (comm 6–84): each is a single file.
Actions: absorb into the group that dominates its include chain.

## Heuristic 3 — Subsystem semantic labels

| Shared prefix / label       | Communities merged                  | Target group  |
| --------------------------- | ----------------------------------- | ------------- |
| `Pref_*`, `HOOK_PREFS_*`    | class-comm-0 (Pref_* classes), hook-comm-1 | CG-1 Core / Hook-prefs |
| `Db_*`, `IDb`               | class-comm 10–17, include-comm 12–17 | CG-12 Infrastructure |
| `HOOK_RENDER_*`, `HOOK_HEADLINE_*` | hook-comm 0               | Hook-0 Render |
| `HOOK_FETCH_*`, `HOOK_FEED_*`     | hook-comm 2               | Hook-2 Fetch  |
| `Text_LanguageDetect_*`     | call-comm-9, class-comm-7, include lib | CG-9 LangDetect |

## Heuristic 4 — Cap by dimension (> 15 communities per dim)

- **call graph**: Keep top 12 by size; absorb remainder into nearest larger.
  Kept: comms 0–11. All comms 12+ absorbed into CG-12 Infrastructure.
- **include graph**: Keep top 6 by size (comms 0–5). Singletons absorbed.
- **class graph**: Keep top 8 by size (comms 0–7). Singletons absorbed.

## Heuristic 5 — Cross-cutting infrastructure: one pass

Logging, error handling, DB wrappers, session primitives, config constants:
grouped into single **CG-12 Infrastructure** research pass regardless of
which dimension they appeared in.

---

## Effective research groups (N_eff = 30 ≤ 50 ✓)

### Call-graph derived groups (12)

| Group  | Label                        | Source communities      | Members (approx) |
| ------ | ---------------------------- | ----------------------- | ---------------- |
| CG-1   | Core App / Handlers          | call-0,1; include-0; class-0,1; all PluginHost/Handler singletons | ~220 |
| CG-2   | Article / Label / Counter    | call-1 (107M), call-11 (24M) | ~131 |
| CG-3   | Auth / Schema Migration / OTP | call-2 (77M), call-6 (54M), class-8,9, DbUpdater | ~140 |
| CG-4   | External: QR code lib        | call-3 (77M), include-1 (13M) | ~90 |
| CG-5   | External: PHPMailer          | call-4 (76M), class-5 (2M)    | ~78 |
| CG-6   | Feed parsing / sanitize      | call-5 (75M), class-2 (4M), FeedParser | ~80 |
| CG-7   | Digest / MiniTemplator       | call-7 (54M), include-3  | ~62 |
| CG-8   | OPML / Import                | call-8 (51M)            | ~51 |
| CG-9   | Language detection (ext lib) | call-9 (33M), class-7   | ~35 |
| CG-10  | Sphinx search integration    | call-10 (30M)           | ~30 |
| CG-11  | gettext / i18n               | call-12 (18M), include gettext/* | ~25 |
| CG-12  | Infrastructure (DB, logging) | call-13–27+, all Db_* singletons | ~60 |

### DB-table communities (6)

| Group  | Community ID | Key tables                                                  |
| ------ | ------------ | ----------------------------------------------------------- |
| DB-0   | 0            | ttrss_feeds, ttrss_feed_categories, ttrss_archived_feeds, ttrss_entries, ttrss_user_entries, ttrss_access_keys |
| DB-1   | 1            | ttrss_labels2, ttrss_user_labels2, ttrss_tags, ttrss_enclosures |
| DB-2   | 2            | ttrss_users, ttrss_sessions, ttrss_settings_profiles        |
| DB-3   | 3            | ttrss_filters2, ttrss_filters2_rules, ttrss_filters2_actions, ttrss_filter_types, ttrss_filter_actions |
| DB-4   | 4            | ttrss_prefs, ttrss_prefs_types, ttrss_prefs_sections, ttrss_user_prefs |
| DB-5   | 5            | ttrss_counters_cache, ttrss_cat_counters_cache, ttrss_version, ttrss_feedbrowser_cache, ttrss_linked_feeds, ttrss_linked_instances, ttrss_error_log, ttrss_plugin_storage, ttrss_scheduled_updates, ttrss_entry_comments |

### Hook communities (7)

| Group   | Community ID | Key hooks                                                   |
| ------- | ------------ | ----------------------------------------------------------- |
| Hook-0  | 0            | HOOK_SANITIZE, HOOK_HEADLINE_TOOLBAR_BUTTON, HOOK_HOTKEY_MAP, HOOK_ARTICLE_BUTTON, HOOK_HOTKEY_INFO, HOOK_ARTICLE_LEFT_BUTTON, HOOK_RENDER_ARTICLE, HOOK_RENDER_ARTICLE_CDM |
| Hook-1  | 1            | HOOK_PREFS_TAB, HOOK_PREFS_TAB_SECTION, HOOK_PREFS_SAVE_FEED, HOOK_PREFS_EDIT_FEED |
| Hook-2  | 2            | HOOK_FEED_FETCHED, HOOK_FETCH_FEED, HOOK_FEED_PARSED, HOOK_ARTICLE_FILTER, HOOK_HOUSE_KEEPING, HOOK_UPDATE_TASK |
| Hook-3  | 3            | HOOK_QUERY_HEADLINES, HOOK_RENDER_ARTICLE_API               |
| Hook-4  | 4            | HOOK_AUTH_USER                                              |
| Hook-5  | 5            | HOOK_ACTION_ITEM, HOOK_TOOLBAR_BUTTON                       |
| Hook-6  | 6            | HOOK_PREFS_TABS                                             |

### Grep-based surface groups (5)

| Group   | Label                  | Method                                         |
| ------- | ---------------------- | ---------------------------------------------- |
| GS-1    | API / route surface    | grep `function` in `classes/api.php`, `classes/rpc.php`, `backend.php` dispatch |
| GS-2    | Session / auth surface | `include/sessions.php`, `include/functions.php::authenticate_user`, `classes/auth/` |
| GS-3    | Background daemon      | `update_daemon2.php`, `include/rssfuncs.php::update_daemon_common` |
| GS-4    | Security surface       | `include/crypt.php`, `include/functions2.php::sanitize`, auth flow |
| GS-5    | Frontend/backend coupling | `index.php`, `js/*.js`, `backend.php` dispatch, AJAX patterns |

---

## Budget math

```text
CG groups:    12 passes
DB groups:     6 passes
Hook groups:   7 passes
Grep groups:   5 passes
─────────────────────────
Total:        30 passes (≤ 50 hard cap ✓)
```

Each pass: training-knowledge + targeted grep + key file reads
(∆6 DEGRADED: no web search available this session).

Output: one `.agents/scratch/phase1-test/research/<group>.md` per pass.
