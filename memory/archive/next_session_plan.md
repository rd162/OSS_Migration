---
name: next_session_plan
description: Phase 4 execution plan (graph-driven) — assumes rework complete, uses validate_coverage.py for continuous validation
type: project
---

# Next Session Plan: Phase 4 Execution (Graph-Driven)

**Pre-condition:** Rework plan (memory/rework_plan.md) fully executed. All 5 streams complete.

## Pre-Flight Checks

1. Run `python tools/graph_analysis/validate_coverage.py` (full scope)
2. Confirm: 0 unmatched, 0 missing_imports, 0 missing_hook_calls, 0 missing_class_hierarchy (excluding eliminated)
3. Confirm: coverage metric ≥ 95% (denominator = PHP functions levels 0-10 minus third-party; numerator = matched + eliminated)
4. Run existing tests: `pytest tests/ -v` → all green

## Phase 4 Execution: 5 Batches, 17 API Ops

Same structure as adversarially-selected Phase 4 plan (Condorcet winner, Solution B).
Enhanced with graph-driven validation at each batch.

### Batch 1: Auth Guards + Read Counters (6 ops)
**Ops:** auth guards, getUnread, getCounters, getPref, getConfig, getLabels
**Graph levels required:** L2-5 (counters, prefs, labels)
**Dependencies:** Phase 3 ccache, counters, labels — all validated by pre-flight
**Workflow:**
1. Write handler code with `# Source:` traceability
2. Run `python tools/graph_analysis/validate_coverage.py --modules blueprints/api`
3. Run tests
4. Rule 10a adversarial self-refine (1-2 rounds)
5. Mark complete

### Batch 2: Category/Feed/Article Read (3 ops)
**Ops:** getCategories, getFeeds, getArticle
**Graph levels required:** L2-3 (categories, counters, article formatting)
**Dependencies:** Phase 3 categories, counters, articles/ops
**Workflow:** same as Batch 1

### Batch 3: Write Operations (4 ops)
**Ops:** updateArticle, catchupFeed, setArticleLabel, updateFeed
**Graph levels required:** L5-6 (articles/ops, labels, ccache update)
**Dependencies:** Phase 3 articles/ops, labels, ccache
**Workflow:** same as Batch 1

### Batch 4: Complex Query/Subscribe (4 ops)
**Ops:** getHeadlines, subscribeToFeed, unsubscribeFeed, shareToPublished
**Graph levels required:** L5-7 (articles/search + queryFeedHeadlines, feeds/ops + subscribe_to_feed)
**Dependencies:** Phase 3 articles/search, feeds/ops
**Workflow:** same as Batch 1

### Batch 5: Feed Tree (1 op)
**Ops:** getFeedTree
**Graph levels required:** Custom BFS (no standard graph level — this is a UI tree builder)
**Dependencies:** Phase 3 categories, counters
**Workflow:** same as Batch 1

## Post-Phase 4 Validation

1. Re-run full graph analysis: `python tools/graph_analysis/build_php_graphs.py`
2. Re-run full validation: `python tools/graph_analysis/validate_coverage.py`
3. Confirm coverage metric ≥ 95%
4. Document any unparseable items in specs/13 "Graph Validation Status" section
5. Run full test suite: `pytest tests/ -v --cov=ttrss`

## Phase 5+ (sketch, not detailed)

After Phase 4 complete:
- Phase 5a: Plugin system (discovery, loading, per-user enable/disable, built-ins)
- Phase 5b: External API rate limiting
- Phase 5c: Celery integration refinement (Beat schedule, Flower monitoring)
- Phase 5d: Logging (structlog) + error handling
- Phase 6: Deployment (Docker, CI/CD, data migration)

Each phase follows the same graph-driven workflow:
write → validate_coverage.py → tests → Rule 10a → commit

## Missing Functions for Phase 4 (to be populated during rework)

This section will be populated by Stream 4 of the rework plan after running the Phase 4 dependency matrix analysis. Any PHP function called by API handlers (graph edges from classes/api.php to target files) that isn't ported and isn't eliminated must be identified here.

Known candidates (from graph research):
- `make_init_params` (functions2.php) → `ttrss/ui/init_params.py` (Phase 4)
- `make_runtime_info` (functions2.php) → `ttrss/ui/init_params.py` (Phase 4)
- `get_hotkeys_map` / `get_hotkeys_info` (functions2.php) → `ttrss/ui/init_params.py` (Phase 4)
- `sql_bool_to_bool` / `bool_to_sql_bool` (functions.php) → trivial Python equivalents, may not need porting
- `format_article_enclosures` (functions2.php) → check if in articles/ops.py
- `format_inline_player` (functions2.php) → deferred per Phase 2 plan
