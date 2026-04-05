---
name: rework_plan
description: Graph-driven rework of Phases 1-3 — enhance existing code with tree-sitter+NetworkX evidence (Candidate B refined, adversarial-thinking pipeline)
type: project
---

# Rework Plan: Graph-Driven Enhancement of Existing Work

**Method:** Adversarial-thinking pipeline (3 candidates, CRITIC, AUTHOR refinement)
**Winner:** Candidate B (Automated Validation Pipeline), refined with 6 CRITIC findings
**Trace:** s₀[3 candidates]→CRITIC[A fails R4/R5/R6/R7, B minor issues, C fails R1/R8/R9/R10/R11+AR1/AR3]→B selected→AUTHOR[6 fixes]→CONVERGE

## Constraint: Additive Only

- NEVER remove already-translated code
- NEVER change adversarially-selected module boundaries (Condorcet winners)
- NEVER re-run Phase 2 traceability verification (already CONVERGED)
- Enhance and augment with graph evidence

## Stream 1 — Script Enhancement (~45 min)

### Fix 1: Hook detection for PluginHost::HOOK_* patterns
- `build_php_graphs.py` currently detects `add_hook()` and `run_hooks()` but misses `get_hooks(PluginHost::HOOK_*)` and class-constant-prefixed invocations
- In `_handle_member_call()` / `_handle_static_call()`: add `get_hooks` to hook-detection set
- In `_regex_fallback()`: update regex to handle `PluginHost::` prefix: `r"\b(?:add_hook|run_hooks|get_hooks)\s*\(\s*(?:PluginHost::)?(HOOK_[A-Z_]+)"`
- Expected: hook graph grows from 18 to ~40+ edges, 8 to ~20+ hooks

### Fix 2: New output `function_levels.json`
- After building call graph, emit `{ "function_qname": level_int, ... }` for every node
- Invert existing `levels` dict: `{level: [nodes]}` → `{node: level}`
- Add to `Reporter.save_graph()` when `dim_name == "call"`

### REMOVED: module_mapping.json
- Authoritative mapping is specs/13 (adversarially selected via Condorcet)
- Automated recommendations would invite confusion if they disagree

## Stream 2 — Build 5-Dimension Validation Tool (~2 hours)

Create `tools/graph_analysis/validate_coverage.py`

### Inputs
- `call_graph.json`, `db_table_graph.json`, `hook_graph.json`, `class_graph.json`, `function_levels.json`
- `target-repos/ttrss-python/ttrss/` (Python source tree)

### Dimension 1 — Call coverage
- For each PHP function at levels 0-10 (excluding third-party): check if Python equivalent exists via `# Source:` comment matching
- Simplified regex for 7 traceability formats (~95% coverage)
- Report `unparseable` entries for human review

### Dimension 2 — Import coverage
- For each call edge (A→B): check Python module for A imports Python module for B
- Report `missing_imports`

### Dimension 3 — DB_TABLE coverage
- For each DB_TABLE edge (file→table): check Python module imports corresponding SQLAlchemy model
- Report `missing_model_imports`

### Dimension 4 — Hook invocation coverage
- For each INVOKES edge in hook_graph.json: verify Python module calls `pm.hook.<hook_name>()`
- Report `missing_hook_calls`

### Dimension 5 — Class hierarchy coverage
- For each extends/implements edge: verify Python inheritance or Protocol implementation
- Report `missing_class_hierarchy` (many eliminated by design, e.g. Db_Mysql)

### Coverage metric
- **Denominator:** PHP functions at levels 0-10, excluding third-party (QRcode, PHPMailer, SphinxClient, gettext, LanguageDetect, MiniTemplator, Mobile_Detect, floIcon/jimIcon, HOTP/OTP/TOTP, Minifier, FrameFiller, Db_Mysql, Db_Mysqli)
- **Numerator:** Functions with Python equivalent (matched) OR explicitly eliminated (specs/13)
- **Unparseable:** Reported separately, not in numerator
- **Target:** ≥ 95%

## Stream 3 — Spec Updates (~1.5 hours)

### specs/13 updates
1. Add 4 missing modules: articles/tags.py, articles/filters.py, articles/persist.py, utils/feeds.py, tasks/housekeeping.py
2. Fix ccache.py function names: ccache_zero_all, ccache_remove, ccache_find, ccache_update, ccache_update_all, _count_feed_articles
3. Fix labels.py function list: label_find_id, label_find_caption, get_all_labels, get_article_labels, label_update_cache, label_clear_cache, label_add_article, label_remove_article, label_create, label_remove
4. Add "Graph Level" column (from function_levels.json)
5. Add "Graph Validation Status" section at bottom

### specs/10 updates
6. Entity Clusters: ADD "Graph Evidence" column (not rewrite) — preserve existing 10-cluster structure
7. Graph Analysis Findings: Note MiniTemplator/digest/syndication cluster (no restructuring)

## Stream 4 — Plan Enhancement (~45 min)

### Phase 3 plan
- Add per-batch validation step: `python tools/graph_analysis/validate_coverage.py --batch N`

### Phase 4 plan
- Add Phase 4 dependency matrix (API op → PHP functions → Python equivalents → status)
- Identify missing functions called by Phase 4 handlers
- Add per-batch validation step

## Exit Criteria

1. Enhanced script re-run produces ≥20 hooks (up from 8)
2. validate_coverage.py runs and reports ≥90% call coverage
3. specs/13 lists all existing Python modules with correct function names
4. specs/10 Entity Clusters has "Graph Evidence" column
5. Phase 3/4 plans have per-batch validation steps
