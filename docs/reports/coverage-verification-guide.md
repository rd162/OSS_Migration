# Coverage Verification Guide

Two complementary verification modes exist for the PHP→Python migration.
Run them together for a complete picture: migration coverage first, then semantic
coverage for the highest-risk functions.

---

## Mode 1 — Migration Coverage Check

**What it does:** Counts how many PHP functions (from the static call graph) have
an explicit `Source:` traceability citation in the Python codebase.  A function
is *covered* only if:

1. Its name appears in a `# Source:` comment **or** docstring `Source:` line, OR
2. It is in `ELIMINATED_FUNCTIONS` (intentionally not ported — documented with ADR).

File-level matching ("the PHP file has some Python mapping") is **not accepted**.
Every function must be cited individually.

### How to run

```bash
python tools/graph_analysis/validate_coverage.py \
    --graph-dir tools/graph_analysis/output \
    --python-dir target-repos/ttrss-python/ttrss
```

### Output buckets

| Bucket | Meaning | Action |
|---|---|---|
| **Matched (explicit cite)** | PHP function has a `Source:` citation by name | ✅ No action |
| **Needs explicit citation** | PHP file is mapped, function is not cited | Add `# Source: file.php:function` to Python code |
| **Eliminated (spec 13)** | Intentionally not ported (UI rendering, DB wrappers, etc.) | ✅ No action |
| **Unmatched (no mapping)** | PHP file has no Python mapping at all | Investigate — may be a true gap |

### Acceptable coverage threshold

≥ 95% (`--min-coverage 0.95` flag).

### Report location

`tools/graph_analysis/output/validation_report.json` (JSON) plus terminal output.

---

## Mode 2 — Semantic Coverage Verification

**What it does:** For each Python function that has a `Source:` citation, reads
the cited PHP source and verifies that the Python implementation is semantically
correct — same logic, same edge cases, same security properties.

This is a **deep adversarial review**, not automated static analysis.

### When to run

- After any significant change to business logic (articles, filters, feeds, auth)
- Before a release cut
- When the user asks `"run semantic coverage check"`

### How to run

1. **Identify the target set.** From the validation report, take the
   "Matched (explicit cite)" list. Focus on levels 0–5 (most-called functions)
   and any functions in:
   - `ttrss/articles/` — sanitize, search, filters, ops
   - `ttrss/auth/` — authenticate, password, csrf
   - `ttrss/feeds/` — ops, categories, opml
   - `ttrss/prefs/` — ops, user_prefs_crud, feeds_crud
   - `ttrss/blueprints/api/` — all API handlers

2. **Per-function verification.** For each function, use the following prompt
   pattern (invoke as a sub-agent or `/adversarial-self-refine`):

   ```
   Verify that the Python function <function_name> in <python_file>
   is a correct migration of <PHP_function> in <php_file> (lines N-M).

   PHP source:
   <paste PHP code>

   Python code:
   <paste Python code>

   Check:
   1. All branches/conditions are preserved (or intentional changes documented)
   2. All edge cases handled the same way (empty inputs, nulls, limits)
   3. Security properties preserved or improved (no new XSS/SQLi vectors)
   4. Any intentional deviations are in the traceability comment
   5. Return value / side effects match PHP semantics

   Report: PASS | FAIL + findings
   ```

3. **Prioritised starting list** (highest risk, run these first):

   | Python file | PHP source | Why critical |
   |---|---|---|
   | `articles/sanitize.py:sanitize()` | `functions2.php:sanitize` | XSS gateway |
   | `articles/sanitize.py:strip_harmful_tags()` | `functions2.php:strip_harmful_tags` | XSS gateway |
   | `auth/authenticate.py:authenticate_user()` | `functions.php:authenticate_user` | Auth bypass risk |
   | `auth/password.py:verify_password()` | `plugins/auth_internal/init.php:check_password` | Credential security |
   | `articles/filters.py:filter_to_sql()` | `functions2.php:filter_to_sql` | SQL injection risk |
   | `articles/search.py:search_to_sql()` | `functions2.php:search_to_sql` | SQL injection risk |
   | `articles/search.py:queryFeedHeadlines()` | `functions2.php:queryFeedHeadlines` | Core feed display |
   | `feeds/ops.py:subscribe_to_feed()` | `functions.php:subscribe_to_feed` | Feed subscription |
   | `feeds/opml.py:import_opml()` | `classes/opml.php:opml_import` | Data import |
   | `prefs/ops.py:get_pref()` / `set_pref()` | `include/db-prefs.php` | User preferences |

4. **Known intentional deviations** (do NOT flag these as bugs):

   - Password hashing: `sha1(salt+pass)` → `argon2id` (ADR-0008, security improvement)
   - HTML output: all PHP `print` / HTML-generating functions → JSON dict responses (R13)
   - Session handling: PHP custom session → Flask-Login + Redis (ADR-0007)
   - DB queries: raw PHP SQL → SQLAlchemy ORM (ADR-0006)
   - Feed fetching: PHP `file_get_contents` / curl → httpx async in Celery (ADR-0015)
   - Article note: `strip_tags` removed (PHP did not strip) → Python strips HTML for XSS safety

5. **Output format.** For each verified function record:
   ```
   FUNCTION: <python_file>:<function_name>
   PHP:      <php_file>:<function_name> (lines N-M)
   STATUS:   PASS | FAIL | DEVIATION_DOCUMENTED
   NOTES:    <any findings>
   ```

### Automation note

For a full scan, the `/adversarial-self-refine` skill can be used on each
function pair. The `docs/reports/semantic-verification.md` report from Phase 5
(specs/005-semantic-verification) contains the D01–D40 taxonomy of known
discrepancy categories — use it as the reference taxonomy for classifying findings.

---

## Running both modes

```bash
# Step 1: Migration coverage check
python tools/graph_analysis/validate_coverage.py \
    --graph-dir tools/graph_analysis/output \
    --python-dir target-repos/ttrss-python/ttrss

# Step 2: For each function in "Needs explicit citation" list, either:
#   a) Add explicit # Source: comment to Python code
#   b) Add to ELIMINATED_FUNCTIONS with ADR reference in validate_coverage.py

# Step 3: Semantic check on top-10 priority functions (see table above)
# Use /adversarial-self-refine or manual review with the prompt template above
```
