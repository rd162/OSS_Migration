# Semantic Trap Catalog — Example Structure

This file shows the structure of a project-specific semantic trap catalog. The actual content
must be tailored to the specific source→target language pair. Build this catalog incrementally
during modernization as you discover traps.

## Purpose

A semantic trap is a code pattern that looks equivalent between source and target languages
but behaves differently. These are the most dangerous modernization bugs because they pass code
review and basic testing while silently producing wrong results for edge cases.

## Catalog Structure

Organize traps into domains. Each trap entry has four fields:

| Field | Purpose |
|-------|---------|
| Source pattern | The source language code pattern |
| Target gotcha | How the target language behaves differently |
| Frequency | Estimated occurrences in this codebase |
| Example | Concrete example from the project |

## Example: PHP→Python Traps (40 categories from reference project)

### Type & Comparison Traps

| # | Source Pattern | Target Gotcha | Frequency |
|---|---------------|---------------|-----------|
| 1 | `empty($x)` — treats "0", 0, "", null, false, [] as empty | Python `not "0"` is False (Python "0" is truthy) | ~50 sites |
| 2 | `intval("abc")` returns 0 silently | Python `int("abc")` raises ValueError | ~30 sites |
| 3 | `isset($x)` checks exists AND not-null | Python `if x` conflates None, 0, "", [] | ~40 sites |
| 4 | `$x ?? $b` (null coalescing) only replaces null | Python `x or b` replaces ALL falsy values | ~25 sites |

### String & Regex Traps

| # | Source Pattern | Target Gotcha | Frequency |
|---|---------------|---------------|-----------|
| 5 | `preg_match()` returns 0 or 1 (int) | Python `re.search()` returns None or Match object | ~20 sites |
| 6 | `explode(",", $s, 2)` — limit=N means N elements | Python `split(",", 1)` — maxsplit is N-1 | ~10 sites |
| 7 | `str_replace(array, array, $s)` cascading | Python has no built-in cascade replacement | ~8 sites |

### Database & ORM Traps

| # | Source Pattern | Target Gotcha | Frequency |
|---|---------------|---------------|-----------|
| 8 | `while ($row = fetch_assoc())` streams rows | ORM `.all()` loads entire result into memory | ~40 sites |
| 9 | `BEGIN`/`COMMIT` per-row (partial success) | ORM single `commit()` per batch (all-or-nothing) | ~5 sites |
| 10 | `affected_rows()` for INSERT ON CONFLICT | ORM `rowcount` may differ for upserts | ~8 sites |

## Discrepancy Taxonomy Structure

Beyond individual traps, organize discovered discrepancies into a formal taxonomy:

### Domain Categories

| Domain | Code Range | What It Covers |
|--------|-----------|----------------|
| SQL & Query Semantics | D01-D10 | Join topology, computation locus, column mismatch, subquery nesting |
| Type System & Coercion | D11-D16 | Type coercion, falsy divergence, null handling, numeric boundaries |
| Data Flow & Content | D17-D22 | Content priority, GUID construction, field truncation, encoding |
| Session & Global State | D23-D28 | Session elimination, config mapping, in-memory cache |
| Return Value & API Contract | D29-D33 | Return shape, materialization, error envelope, HTTP headers |
| Feature & Behavior | D34-D40 | Feature omission, hook mismatch, side effect order, error recovery |

Each category gets a code, name, description, and concrete codebase example.

## Integration Pipeline Contracts

Beyond individual functions, verify multi-step workflows:

**Example pipeline: Feed Update (12 steps)**
```
1. Scheduler triggers update
2. Query due feeds from DB
3. HTTP fetch with conditional GET (ETag/Last-Modified)
4. Parse XML/Atom/RSS
5. Sanitize HTML content
6. Deduplicate articles (GUID matching)
7. Apply user filters
8. Store new articles
9. Update feed metadata (last_updated, last_error)
10. Invalidate counter cache
11. Update category counters
12. Trigger plugin hooks
```

At each boundary (1→2, 2→3, ..., 11→12), verify:
- Data shape passed from step N to step N+1 is identical in source and target
- Side effects happen in the same order
- Error handling follows the same model (log-and-continue vs. raise-and-retry)

## Complexity-Tiered Triage

Not all functions need the same verification depth:

| Tier | Count | Criteria | Depth |
|------|-------|----------|-------|
| 1 (deep) | ~50 | Complex SQL, many branches, cross-cutting callers | Line-by-line + trap checklist |
| 2 (standard) | ~150 | Moderate complexity | Block-level + spot checks |
| 3 (quick) | ~270 | Simple getters/setters/wrappers | Signature + return type |
| 4 (model) | ~37 | ORM models / data classes | Column-by-column schema check |

Tier 1 functions are the highest risk and must be verified first. They typically include:
- Query-building functions with dynamic WHERE clauses
- Authentication and session validation
- Content sanitization and encoding
- Payment/financial calculations
- Data import/export with format conversion
