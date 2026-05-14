# 11 — Modernization Dimensions

**Synthesis artifact** · Phase 1 · TT-RSS PHP → Python
**Status**: synthesised ✓ · graph evidence ✓ · research DEGRADED (no web access)

---

## Discovered dimensions

| NN | Slug | Artifact | Purpose for modernization |
|---|---|---|---|
| 01 | call-graph | `call_graph.json` | Migration ordering signal; hub function identification |
| 02 | include-graph | `include_graph.json` | Bootstrap sequence; Python module mapping |
| 03 | class-hierarchy | `class_graph.json` | Python class skeleton; interface → ABC/Protocol |
| 04 | entity-schema | `db_table_graph.json` | SQLAlchemy ORM order; Alembic revision order |
| 05 | plugin-hook-graph | `hook_graph.json` | pluggy hookspec skeleton; 24 hook classification |
| 06 | api-route-surface | (derived) | Flask Blueprint + route skeleton; API contract |
| 07 | session-auth-surface | (derived) | Auth plugin parity; session migration; crypto migration |
| 08 | background-daemon | (derived) | Celery task topology; feed update pipeline |
| 09 | security-surface | (derived) | 10 security findings; SF-01 (SQL injection) is pervasive |
| 10 | configuration-surface | (derived) | pydantic Settings model; ttrss_prefs seed migration |

**Dimension count**: 10 (target: 6–12 for mid-scale app — within range)
**Source evidence**: all 10 dimensions grounded in concrete source constructs (see individual specs)

---

## Application archetype

**Primary**: Web application + Daemon/background-job + Plugin host

| Archetype | Evidence |
|---|---|
| Web application | `index.php`, `backend.php`, `api/index.php`, `public.php` HTTP entry points; SPA frontend in `js/` |
| Daemon | `update_daemon2.php` PCNTL fork-based feed update daemon |
| Plugin host | `classes/pluginhost.php` with 24 hooks; `plugins/` directory; `IAuthModule`, `IHandler` plugin interfaces |

**Scale**: 138 PHP files, ~44kLOC (mid-scale) — 10 dimensions appropriate.

---

## Graph metrics summary

| Dimension | Nodes | Edges | Raw communities | Grouped passes |
|---|---|---|---|---|
| call-graph | 1206 | 2086 | 305 | 10 |
| include-graph | 139 | 66 | 85 | 7 |
| class-hierarchy | 81 | 27 | 55 | 5 |
| entity-schema | 60 | 126 | 6 | 6 |
| plugin-hook-graph | 40 | 39 | 7 | 7 |
| **Total raw** | | | **458** | **35 → 10 cross-dim merged** |

∆5 grouping: 458 raw communities → 10 research groups (well within 50 cap).
Primary grouping heuristics applied: Heuristic 4 (cap by dimension, top 10 by size),
Heuristic 1 (cross-dimension co-location merge), Heuristic 3 (subsystem semantic label).

---

## Inter-dimension coupling

| Coupling | Cross-dimension connection | Significance |
|---|---|---|
| call-graph ↔ entity-schema | `db_query()` (500+ call sites) touches every entity | DB layer is the central hub |
| call-graph ↔ hook-graph | 39 `run_hooks()` call sites distributed across callers | Hooks pervade every subsystem |
| call-graph ↔ include-graph | Autoloader connects 81 classes to include-graph bootstrap | Bootstrap order = call-graph level 0 |
| entity-schema ↔ session-auth | `ttrss_users` is the FK root of 90% of tables | User model must be first model defined |
| hook-graph ↔ plugin-system | 24 hooks define the complete plugin API surface | pluggy hookspec = hook-graph translation |
| include-graph ↔ config-surface | `include/autoload.php` bootstraps after `include/db.php` which needs config | Config must initialise before any other module |
| security-surface ↔ entity-schema | SF-01 (SQL injection) affects every DB operation | Parameterised queries = ORM adoption covers all |
| background-daemon ↔ hook-graph | Daemon fires 6 of 24 hooks | Celery tasks must emit hook calls at equivalent points |

---

## Community overlap map

Communities that span multiple dimensions (Heuristic 1 — merged into one research group):

| Research group | call comm | class comm | db comm | hook comm | include comm |
|---|---|---|---|---|---|
| GRP-01 API | C0+C1 | C1 | — | C3 | C2(partial) |
| GRP-02 Feed engine | C7 | C2 | C0(partial) | C2 | C2(partial) |
| GRP-03 DB layer | C6 | — | C0+C4 | — | C0 |
| GRP-04 Prefs/filters | C8(partial) | C0(partial) | C2+C3 | C1+C6 | — |
| GRP-05 Plugin system | — | C8 | C5 | C0+C5+C6 | — |
| GRP-06 Auth/session | C2 | C9+C4 | C1 | C4 | C0+C5 |
| GRP-07 Email/digest | C4 | C5 | — | — | C3 |
| GRP-08 Bootstrap | C8(partial) | — | — | — | C0+C4+C6 |
| GRP-09 3rd-party libs | C3+C9 | C3+C6+C7 | — | — | C1+C5(partial) |
| GRP-10 Public/frontend | C7(partial) | C1(partial) | — | C5 | C3+C4(partial) |

---

## Flow variants

Three modernization flow variants are derived from the community structure and
inter-dimension couplings above. Each variant prioritises a different ordering signal.

---

### Variant A: Entity-first (DB-layer-first)

**Ordering signal**: entity-schema dependency levels (table FK hierarchy)

**Migration order**:
```
Phase 1a: SQLAlchemy models (level-0 tables first → level-4 last)
Phase 1b: DB layer (db_query → SQLAlchemy session)
Phase 2: Auth + session (ttrss_users model → Flask-Login)
Phase 3: Core business logic (preferences, filters, ccache)
Phase 4: API handlers (bottom-up from call-graph levels)
Phase 5: Feed pipeline + daemon (Celery tasks)
Phase 6: Plugin system (pluggy hookspecs)
Phase 7: Frontend (SPA replacement)
```

**Pros**:
- Every phase builds on a complete, tested DB layer
- Alembic migrations reflect the actual FK ordering
- SQL injection (SF-01) eliminated earliest — highest-risk finding addressed first
- ORM model parity verifiable via database inspection at any point

**Cons**:
- API is unverifiable until Phase 4 — integration testing delayed
- Feed pipeline (the most visible user-facing feature) is last among backend phases
- Auth not working until Phase 2 — no end-to-end login until later

**Recommended for**: Projects where data integrity and security take priority;
teams with strong SQL/ORM experience.

---

### Variant B: API-contract-first

**Ordering signal**: call-graph levels 4+ (top-level entry points) + API route surface

**Migration order**:
```
Phase 1a: JSON API contract skeleton (stubs returning hardcoded responses)
Phase 1b: Auth + login (ttrss_users + Flask-Login)
Phase 2: SQLAlchemy models + DB layer (supports Phase 3 queries)
Phase 3: API read operations (getFeeds, getCategories, getHeadlines, getArticle)
Phase 4: API write operations (updateArticle, subscribeToFeed, catchupFeed)
Phase 5: Core business logic (prefs, filters, ccache)
Phase 6: Feed pipeline + daemon (Celery)
Phase 7: Plugin system
Phase 8: Frontend
```

**Pros**:
- Third-party API clients (mobile apps, Miniflux) testable from Phase 3
- Login and session verified early — blocks no downstream integration test
- API_LEVEL = 8 compatibility verified continuously

**Cons**:
- Stubs in Phase 1a create false confidence (tests pass against hardcoded data)
- DB layer deferred to Phase 2 — Phase 1 stubs must be replaced with real queries
- Feed pipeline deferred — no live data until Phase 6

**Recommended for**: Projects integrating with existing API clients;
teams that want continuous API regression testing.

---

### Variant C: Plugin-system-first

**Ordering signal**: hook-graph (all 7 communities); plugin-host architecture

**Migration order**:
```
Phase 1a: PluginHost → pluggy PluginManager skeleton (hooks defined, no implementations)
Phase 1b: Auth plugin system (IAuthModule → hookspec; Auth_Internal hookimpl)
Phase 2: DB layer + entity models (required by most hook implementations)
Phase 3: Feed pipeline hook implementations (HOOK_FETCH_FEED → HOOK_FEED_PARSED → HOOK_ARTICLE_FILTER)
Phase 4: Article render hook implementations (HOOK_SANITIZE, HOOK_RENDER_ARTICLE_*)
Phase 5: API + backend handlers (fire hooks at correct points)
Phase 6: Preference hooks (HOOK_PREFS_TAB, HOOK_PREFS_SAVE_FEED)
Phase 7: UI hooks (HOOK_TOOLBAR_BUTTON, HOOK_ACTION_ITEM — requires frontend)
Phase 8: Frontend (Vanilla JS SPA — ADR-0017)
```

**Pros**:
- Plugin compatibility established earliest — existing PHP plugin authors can start porting
- All 24 hooks classified (firstresult vs. void) in Phase 1a
- HOOK_QUERY_HEADLINES SQL-fragment problem resolved architecturally in Phase 1a
- Every subsequent phase can be verified against the plugin API

**Cons**:
- Most complex starting point — requires understanding all 24 hooks before any user feature works
- No verifiable end-to-end flow until Phase 5 (API + backend)
- HOOK_QUERY_HEADLINES redesign is blocking and hard — requires upfront API design effort

**Recommended for**: Projects where plugin ecosystem compatibility is a primary goal;
teams with strong PHP plugin knowledge who want to maintain plugin authors' trust.

---

## Recommendation matrix

| Criterion | Variant A | Variant B | Variant C |
|---|---|---|---|
| Security risk reduction (earliest) | ★★★ | ★★ | ★ |
| API client compatibility testing | ★ | ★★★ | ★★ |
| Plugin ecosystem continuity | ★★ | ★★ | ★★★ |
| End-to-end testability (early) | ★★ | ★★★ | ★ |
| Team SQL/ORM skill leverage | ★★★ | ★★ | ★★ |
| Feed pipeline delivery speed | ★★ | ★★ | ★★★ |
| Complexity of phase 1 | LOW | MEDIUM | HIGH |

**This project's ADR-0001 selects Variant D-revised** (a hybrid of A and B):
entity-first ordering for DB layer, followed by API contract verification per phase,
with plugin system deferred to Phase 2+ after core handlers are in place.
The three variants above provide the evidence base for that decision.

---

## Notes

- **Singleton flood in call-graph**: 273/305 raw communities are singletons — PHP's
  procedural style in `functions.php` / `functions2.php` dominates the call-graph leaf space.
  This is not a modularity failure; it reflects intentional procedural decomposition.
  All 4000+ LOC of these two files must be decomposed into Python modules by functional group.
  This is the single largest migration labour item.

- **Third-party lib isolation**: call-graph communities C3 (QRcode, 77 nodes) and C9
  (LanguageDetect, 33 nodes) are fully self-contained. Their community isolation
  confirms they can be replaced wholesale with Python equivalents without touching
  application logic.

- **Hook-graph has zero singletons**: Every one of the 24 hooks is connected to at
  least one invocation site. The plugin API is fully active and used throughout the
  codebase. Plugin parity is not optional — it is a first-class migration goal.

- **entity-schema has exactly 6 communities**: The tight FK coupling (ttrss_users
  as root anchor) reduces 31 tables to 6 semantically coherent clusters.
  This validates the table groupings used for Alembic revision ordering.
