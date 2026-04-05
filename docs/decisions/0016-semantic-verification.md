# ADR-0016: Semantic Verification Methodology

- **Status**: accepted
- **Date proposed**: 2026-04-05
- **Date accepted**: 2026-04-05
- **Deciders**: rd

## Context

After completing the PHP-to-Python code migration (Phases 1–5), SME review confirmed that the generated Python code contained semantic discrepancies across all modules — functional logic, business rules, and non-functional requirements were lost despite structural and traceability coverage being at 100%.

A systematic verification methodology is needed. The challenge: the codebase has 472 functions + 37 ORM models across 91 Python files, and PHP→Python translation introduces discrepancies at multiple levels:

**Per-function level** — individual functions diverge from PHP semantics:

| Discrepancy pattern | Example |
|---------------------|---------|
| Content priority inversion | `update_rss_feed`: PHP extracts `get_content()` first, summary fallback; Python extracts `summary` first, content fallback — reverses what users see |
| GUID construction divergence | PHP prefixes `owner_uid` + applies SHA1; Python uses raw feedparser ID — breaks dedup model |
| Systemic type coercion | `get_pref` returns native bool/int in PHP, raw string in Python — affects every pref consumer |
| SQL join topology | `catchup_feed` labels: PHP 3-table cross-join; Python 1-table subquery — different result sets |
| SQL computation locus | PHP `NOW() - INTERVAL` (DB server time) vs Python `datetime.now()` (app time) — clock skew risk |
| Transaction granularity | `update_rss_feed`: PHP per-article `BEGIN`/`COMMIT`; Python single commit per feed — partial vs all-or-nothing failure |
| Field truncation | PHP `mb_substr($guid, 0, 245)`; Python: no truncation — DB column overflow |
| Hook argument count | `sanitize`: PHP passes 5 args; Python passes 4 (omits `article_id`) |
| Feature elimination | PubSubHubbub, Sphinx search, favicon refresh, image cache, language detection — absent without flags |
| DOM model | PHP `DOMDocument` full HTML doc; Python `lxml.html.fragment_fromstring` in `<div>` wrapper |
| Error recovery | PHP writes `last_error` and returns; Python raises exception, triggering Celery retry |
| In-memory cache | PHP caches prefs in singleton, feed XML to disk; Python hits DB/network every call |

These 12+ categories were discovered by sampling just 6 function pairs (`catchup_feed`, `sanitize`, `queryFeedHeadlines`, `update_rss_feed`, `make_init_params`, `get_pref`), producing 60+ concrete discrepancies. A naive per-function checklist with a narrow taxonomy would miss most of them.

**Cross-function level** — functions interact with incompatible assumptions:

- Function A builds a GUID; function B uses that GUID for dedup lookup. If GUID construction differs from PHP, ALL dedup breaks — but each function looks correct in isolation.
- `persist_article` commits data; `ccache_update` recounts. If transaction boundary is wrong, cache reads uncommitted data.
- `authenticate_user` sets session variables; 40+ functions read them. Any missing session key silently changes behavior downstream.

**Model level** — ORM classes may have wrong column types, missing FKs, wrong cascade behavior, or incorrect computed properties.

## Options

### A: Per-function audit only

Audit each function individually with a 40-category discrepancy taxonomy. No cross-function or pipeline checks.

- Catches per-function bugs
- Misses data flow issues between functions
- Treats 5-line helpers the same as 200-line critical functions

### B: Taxonomy + integration pipelines + complexity triage

40-category taxonomy for per-function checks, PLUS: 8 integration pipeline checks (tracing data end-to-end), complexity tiers (52 high-risk functions get deep audit, remainder standard/quick), cross-workstream sweeps for systemic patterns, model deep checks.

- Catches per-function bugs AND cross-function data flow issues
- Focuses effort where risk is highest
- Pipeline checks verify end-to-end behavior
- More effort, but catches the ~40% of bugs that per-function audits miss

### C: Golden-file testing only (no manual audit)

Run both PHP and Python against the same inputs and compare outputs (as defined in spec 12, section 3).

- Catches output differences automatically
- Misses internal state differences (wrong DB data, stale caches, different transaction semantics)
- Requires a working PHP instance with identical DB state
- Cannot catch logic bugs that produce the same output for test inputs but diverge on edge cases
- Does not explain WHY outputs differ (no taxonomy for tracking)

## Trade-off Analysis

| Criterion | A: Per-function | B: Full methodology | C: Golden-file |
|-----------|----------------|--------------------|--------------| 
| Catches per-function bugs | Yes (40 codes) | Yes (40 codes) | Some (output-visible only) |
| Catches cross-function bugs | No | Yes (8 pipelines) | Partially |
| Effort on high-risk code | Equal to low-risk | Tier 1 gets 10x more attention | Equal to all |
| Catches model schema bugs | Basic | Deep (FKs, cascades, computed) | Only if exercised |
| Requires PHP instance | No | No | Yes |
| Produces fix taxonomy | Yes | Yes | No (just "output differs") |
| Catches session/state bugs | Partially | Yes (cross-workstream sweep) | Only if test exercises path |

## Decision

**Option B: Full methodology** — 40-category taxonomy, 8 integration pipelines, complexity-tiered triage, cross-function contract verification, model deep check.

The full taxonomy, semantic traps, pipeline contracts, and model checklist are defined in `specs/14-semantic-discrepancies.md`.

### Execution phases

| Phase | What | Targets |
|-------|------|---------|
| **A — Tier 1 deep audit** | Line-by-line comparison against PHP with full D01-D40 checklist | 52 functions: `update_feed`, `queryFeedHeadlines`, `sanitize`, `catchup_feed`, `_handle_getHeadlines`, `_handle_login`, `persist_article`, `dispatch_feed_updates`, `get_feed_tree`, `opml_export_full`, `prepare_headlines_digest`, `make_init_params`, etc. |
| **B — Integration pipelines** | Trace data through all steps; verify contract at each boundary | 8 pipelines: feed update, article search, API lifecycle, auth flow, counter cache, OPML roundtrip, digest generation, plugin lifecycle |
| **C — Tier 2 standard audit** | SQL correctness, return shape, session/config, spot-check branches for PHP falsy issues | ~150 functions |
| **D — Tier 3 quick check** | Return type, SQL tables, traceability comment, no obvious intval/falsy traps | ~270 functions |
| **E — Model deep check** | Per-model checklist: columns, FKs, ON DELETE, cascades, indexes, computed properties, behavioral | 37 ORM classes |
| **F — Cross-workstream sweep** | Verify systemic patterns across all code | `get_user_pref` callers (D11), session reads (D23/D24), GUID construction (D18), cache invalidation order (D37) |

### Deliverable

`docs/semantic_verification_report.md` — per-function/per-model status with D-code classifications, organized by workstream. Success criteria: zero unfixed discrepancies + all baseline pytest tests pass.

## Consequences

- **Effort**: Significantly more than per-function audit or golden-file testing alone. Justified because sampling proved that narrow approaches miss the majority of real discrepancies.
- **Quality**: The 40-category taxonomy (D01-D40) gives a shared vocabulary for classifying and tracking bugs. Integration pipelines catch cross-function issues that per-function audits miss.
- **Triage**: Complexity tiers prevent wasting deep-audit effort on trivial helpers while ensuring the most dangerous functions (200+ lines, complex SQL, security-critical) get thorough line-by-line review.
- **Spec 12 synergy**: This methodology complements (not replaces) spec 12's golden-file and contract testing. Code-level audit catches bugs before they reach output; golden-file testing catches what the audit missed. Both are needed.
- **Reusability**: The taxonomy and pipeline contracts are stable — they apply to any subsequent code changes or new function additions without re-derivation.
