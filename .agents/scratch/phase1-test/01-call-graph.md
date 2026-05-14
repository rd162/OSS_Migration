# 01 — Call Graph

**Dimension**: `call-graph`
**Artifact**: `tools/graph_analysis/output/call_graph.json`
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The call graph captures **caller → callee** directed edges between PHP
functions and methods across the entire TT-RSS source.
It reveals the functional decomposition of the application,
identifies hub functions called from many sites,
and provides the primary ordering signal for migration phases:
leaf callees must be ported before their callers.

For the PHP → Python modernization this dimension:

- Orders the migration of function groups (leaf-first)
- Surfaces hub functions that block the most callers if missing
- Identifies isolated subsystems that can be ported independently
- Exposes third-party library call clusters that should be replaced wholesale

---

## Graph structure

| Metric | Value |
|---|---|
| Nodes (qualified callables) | 1 206 |
| Edges (call-site references) | 2 086 |
| Raw Leiden communities | 305 |
| Grouped research passes (∆5) | 10 |
| Isolated singletons (size = 1) | 273 |
| Artifact | `tools/graph_analysis/output/call_graph.json` |
| Levels artifact | `tools/graph_analysis/output/function_levels.json` |

Node label format: `ClassName::method` for class methods,
`filename::function` for file-level functions.

Edge format: `{"from": "Caller::m", "to": "Callee::m", "line": N}`
(line number is the call site in the source file).

---

## Communities (after ∆5 grouping — 10 research groups)

| GRP | Label | Dominant nodes | Size (raw) | Research note |
|---|---|---|---|---|
| GRP-01 | Core API | `API::wrap`, `API::login`, `API::getFeeds`, `API::getHeadlines` | C0(175)+C1(107) | `research/GRP-01-core-api.md` |
| GRP-02 | Feed engine + daemon | `Feeds::view`, `Handler_Public::generate_syndicated_feed`, `Backend::digestTest` | C7(54) | `research/GRP-02-feed-engine.md` |
| GRP-03 | Database layer | `Db_Pgsql::connect`, `Db_PDO::connect`, `Db_Mysqli::connect`, `Db::get` | C6(54) | `research/GRP-03-database-layer.md` |
| GRP-04 | Prefs + filters | `Pref_Prefs::otpenable`, various `Pref_*` methods | C8(51) partial | `research/GRP-04-prefs-filters.md` |
| GRP-05 | Plugin system | `PluginHost::run_hooks`, `PluginHost::add_hook`, `PluginHost::load` | C8(51) partial | `research/GRP-04-prefs-filters.md` |
| GRP-06 | Auth + session | `Auth_Base::auto_create_user`, `DbUpdater::getSchemaVersion` | C2(77) | `research/GRP-04-prefs-filters.md` |
| GRP-07 | Email + digest | `ttrssMailer::__construct`, `PHPMailer::Send`, `PHPMailer::SmtpConnect` | C4(76) | `research/GRP-04-prefs-filters.md` |
| GRP-08 | Bootstrap + core | `sanitize()`, `catchup_feed()`, `getFeedArticles()`, `__()` | C8(51) partial | `research/GRP-04-prefs-filters.md` |
| GRP-09 | 3rd-party libs | `QRcode::*` (77), `Text_LanguageDetect::*` (33) | C3(77)+C9(33) | `research/GRP-04-prefs-filters.md` |
| GRP-10 | Public handler | `Handler_Public::*`, `Opml::opml_export`, `Opml::opml_import` | C5(75) partial | `research/GRP-04-prefs-filters.md` |

**Singleton handling (273 nodes)**: absorbed into nearest larger community
by shared-file heuristic (Heuristic 2 in `references/community-research-budget.md`).
Singletons are overwhelmingly leaf functions called from one site — they
migrate with their caller's community.

---

## Dependency levels (topological order)

Levels computed by SCC condensation + topological sort of the DAG.
See `tools/graph_analysis/output/function_levels.json` for per-node assignments.

Representative level anchors:

| Level | Representative callables | Migration order |
|---|---|---|
| 0 (leaves) | Utility functions with no outgoing calls: `boolval()`, `sql_bool_to_bool()`, `db_escape_string()` wrappers, `_debug()` | Port first |
| 1 | One-call-deep utilities: `db_query()`, `db_fetch_assoc()`, `get_pref()`, `ccache_find()` | Port second |
| 2 | Single-function orchestrators: `ccache_update()`, `label_update_cache()`, individual Pref_* ops | Port third |
| 3 | Multi-step orchestrators: `update_rss_feed()`, `sanitize()`, `format_article()` | Port fourth |
| 4+ | Entry-point dispatchers: `API::getHeadlines()`, `Feeds::view()`, `Handler_Public::generate_syndicated_feed()` | Port last |

---

## Key hub functions (high in-degree)

These are called from many sites; blocking until they are ported
stalls the most callers.

| Callable | Estimated call sites | Significance |
|---|---|---|
| `db_query()` (`include/db.php`) | >500 | Every DB operation |
| `db_fetch_assoc()` (`include/db.php`) | >300 | Every result iteration |
| `get_pref()` (`include/db-prefs.php`) | ~150 | User preference reads |
| `_debug()` (`include/functions.php`) | ~100 | Debug/log output |
| `Db::get()` (`classes/db.php:44`) | ~80 | Direct DB singleton access |
| `sanitize()` (`include/functions2.php`) | ~40 | HTML cleaning on every article |
| `PluginHost::getInstance()` | ~30 | Plugin dispatch sites |
| `run_hooks($type, ...)` | 39 (hook edges) | All plugin extension points |

These hubs must be ported as **priority-zero** items — before any code
that calls them can be verified.

---

## Modernization impact

### Migration ordering signal
The call graph's topological levels provide the definitive migration order:

```
Level 0-1 (DB wrappers, utils) →
Level 2 (pref/cache ops) →
Level 3 (business logic) →
Level 4+ (request handlers)
```

This is the **entity-first / DB-layer-first** flow variant recommended
by this graph. See `11-modernization-dimensions.md` for alternatives.

### Forced adaptations
1. **`db_query()` global → SQLAlchemy session**:
   The most pervasive adaptation. Every call to `db_query(string)` becomes
   `db.session.execute(text(sql), params)` with bound parameters.
   Source: `source-repos/ttrss-php/ttrss/include/db.php`

2. **`PluginHost::run_hooks()` → pluggy dispatch**:
   Dynamic PHP `$hook->$method($args)` dispatch becomes typed pluggy
   hookspec calls. Hook return-value semantics must be classified per hook.
   Source: `source-repos/ttrss-php/ttrss/classes/pluginhost.php:93`

3. **`$_REQUEST` reads → `flask.request`**:
   PHP's merged GET+POST superglobal appears in ~50 sites within the
   call graph's high-level nodes. Flask separates `request.form` / `request.args`.
   Explicit consolidation needed at each call site.

4. **Method-name dispatch → explicit route map**:
   PHP's dynamic `$handler->$method()` dispatch (Handler base class) has
   no Python equivalent that is safe. Must enumerate all valid operations
   and map to explicit view functions.

5. **Third-party library communities (C3, C9) → Python packages**:
   QRcode → `qrcode`/`segno` (PyPI);
   LanguageDetect → `langdetect`/`lingua` (PyPI).
   These communities are fully self-contained and can be replaced wholesale.

### Divergences seeded
- SQL injection surface: `escape_string()` pattern (>500 call sites) →
  parameterised queries required.
- Method-level `$_REQUEST` access — see `12-semantic-discrepancies.md` D-series.
- Third-party lib behavioural differences (LanguageDetect output format,
  QRcode pixel rendering) — test-parity needed.

---

## Source cross-references

| Construct | Source | Line(s) |
|---|---|---|
| `db_query()` global wrapper | `source-repos/ttrss-php/ttrss/include/db.php` | ~1-30 |
| `Db::get()` singleton | `source-repos/ttrss-php/ttrss/classes/db.php` | 44 |
| `PluginHost::run_hooks()` | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 93 |
| `PluginHost::add_hook()` | `source-repos/ttrss-php/ttrss/classes/pluginhost.php` | 102 |
| `API::before()` auth guard | `source-repos/ttrss-php/ttrss/classes/api.php` | 12 |
| `API::wrap()` envelope | `source-repos/ttrss-php/ttrss/classes/api.php` | 36 |
| `sanitize()` HTML cleaner | `source-repos/ttrss-php/ttrss/include/functions2.php` | ~834 |
| `catchup_feed()` | `source-repos/ttrss-php/ttrss/include/functions.php` | ~1094 |
| `update_rss_feed()` | `source-repos/ttrss-php/ttrss/include/rssfuncs.php` | ~190 |
| `reap_children()` daemon | `source-repos/ttrss-php/ttrss/update_daemon2.php` | 42 |
| Handler dispatch pattern | `source-repos/ttrss-php/ttrss/classes/handler.php` | full |
| `const API_LEVEL = 8` | `source-repos/ttrss-php/ttrss/classes/api.php` | 5 |
| QRcode entry | `source-repos/ttrss-php/ttrss/lib/phpqrcode/phpqrcode.php` | full |
| LanguageDetect entry | `source-repos/ttrss-php/ttrss/lib/languagedetect/LanguageDetect.php` | full |

---

## Graph artifact schema

```json
{
  "graph_type": "call",
  "node_count": 1206,
  "edge_count": 2086,
  "community_count": 305,
  "nodes": { "<qualified_name>": { "community": N, "level": N } },
  "edges": [{ "from": "...", "to": "...", "line": N }],
  "communities": { "<node>": <community_id> },
  "levels": { "<node>": <level_id> },
  "community_members": { "<community_id>": ["<node>", ...] }
}
```

---

## Notes and caveats

- **273 singletons**: The high singleton count (273/305 communities) reflects
  PHP's flat procedural style in `functions.php` / `functions2.php`.
  Many functions are called from only one site; Leiden assigns each its own
  community. These are NOT isolated modules — they are leaves of the larger
  call tree and should be ported with their callers.

- **Third-party library isolation**: `lib/phpqrcode/` (C3, 77 nodes) and
  `lib/languagedetect/` (C9, 33 nodes) form fully isolated call clusters.
  They do not call application code and are called only from specific sites.
  Replace wholesale with Python equivalents; do not port line-by-line.

- **Research mode**: ∆6 community research ran in DEGRADED mode (no external
  web search). Target-side pattern guidance from training knowledge only.
  Phase 2 ADR drafting should verify against current Python ecosystem.

- **Graph extraction tool**: `build_php_graphs.py` with tree-sitter PHP parser.
  Some dynamic calls (`$obj->$method()`) are not resolved; actual call count
  may be slightly higher than 2086. Dynamic dispatch sites are flagged in
  the handler base class.
