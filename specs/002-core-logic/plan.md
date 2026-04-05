# Plan 002 — Core Logic

**Status:** DONE  
**Completed:** 2026-04-04  
**Spec ref:** specs/002-core-logic/spec.md  
**Method:** Adversarial thinking pipeline — 3 candidates, Condorcet vote. Candidate A (Dependency-First) won 2-0.  
**Constitution check:** P1 ✓ P2 ✓ P3 ✓ P5 ✓

---

## Technical Context

### Why Candidate A Won

Strict topological ordering — no stubs, no shims, every batch is independently correct at commit time. The rejected Candidate B placed auth in Batch 1 with a `load_user_plugins` no-op, which meant auth was tested without a real loader (partial validation only). Condorcet voters: A beat B 2-0.

### Critical Architectural Decisions

**articles/sanitize.py**
- `sanitize(html_str, ...) -> str`: pipeline = (1) parse lxml, (2) HOOK_SANITIZE via pm.hook (collecting), (3) strip_harmful_tags(), (4) serialize
- HOOK_SANITIZE fires BEFORE strip_harmful_tags — matches PHP functions2.php lines 919-931
- `strip_harmful_tags(doc, allowed_elements, disallowed_attributes) -> doc` is a separate top-level callable
- `format_inline_player()` is absent — belongs to article rendering path in Phase 3

**feed_tasks.py (4 TODOs closed)**
1. HOOK_FETCH_FEED (rssfuncs.php:270): collecting pipeline on raw bytes, BEFORE feedparser.parse()
2. HOOK_FEED_PARSED (rssfuncs.php:394): fire-and-forget collecting, AFTER feedparser.parse()
3. HOOK_ARTICLE_FILTER (rssfuncs.php:687): collecting pipeline per entry, inside entry loop
4. `_sanitize_html` stub deleted — delegates to `articles.sanitize.sanitize()`

**http/client.py**
- Two sections: sync URL utilities (Flask-safe) + `async fetch_file_contents()` (Celery-only, ADR-0015)
- `_fetch_feed_async` NOT moved here — has ETag-specific logic that stays in feed_tasks.py

**prefs/ops.py**
- `initialize_user_prefs(uid, profile_id=None)`: dual SQL path
  - `profile_id=None` → `WHERE profile IS NULL` (global prefs)
  - `profile_id=N` → `WHERE profile = :id` (named profile)
- Iterates `ttrss_prefs` rows; inserts missing rows only (idempotent)

**auth/authenticate.py**
- `authenticate_user`: SINGLE_USER_MODE sets uid=1, skips hook. Normal path: `pm.hook.hook_auth_user` (firstresult). After success: update last_login → session fields → `initialize_user_prefs(uid)` → `load_user_plugins(uid)`
- `logout_user`: `flask_login.logout_user()` + `session.clear()` + `session.modified=True` → Redis key deleted
- `initialize_user`: inserts exactly 2 real feed rows with canonical URLs (`http://tt-rss.org/releases.rss`, `http://tt-rss.org/forum/rss.php`)

---

## Batch Structure

| Batch | Files | Graph Levels | PHP Source |
|-------|-------|-------------|-----------|
| 1 | `ttrss/utils/misc.py`, `ttrss/plugins/loader.py` | L0-L3 | functions.php, pluginhost.php |
| 2 | `ttrss/http/client.py`, `ttrss/articles/sanitize.py`, `ttrss/tasks/feed_tasks.py` (modify) | L1-L2 | functions.php:197-365, functions2.php:831-965, rssfuncs.php |
| 3 | `ttrss/prefs/ops.py` | L1 | functions.php:639-688 |
| 4 | `ttrss/auth/authenticate.py` | L14-L15 | functions.php:706-812 |

---

## Graph Gate: Call + Hook Dimensions

### Call Dimension

- `authenticate_user` at L14, `login_sequence` at L15 — both depend on L1 `get_pref`
- `sanitize` depends on L0 `strip_harmful_tags`
- All functions at their declared graph level; all callees at lower levels must exist before committing the batch

### Hook Dimension

| Hook | Module | PHP Source Edge |
|------|--------|----------------|
| HOOK_SANITIZE | articles/sanitize.py | functions2.php |
| HOOK_AUTH_USER | auth/authenticate.py | functions.php |
| HOOK_FETCH_FEED | tasks/feed_tasks.py | rssfuncs.php |
| HOOK_FEED_PARSED | tasks/feed_tasks.py | rssfuncs.php |
| HOOK_ARTICLE_FILTER | tasks/feed_tasks.py | rssfuncs.php |

### Import Dimension

Python import chain must match call graph cross-module edges. Batch N may not import from Batch M where M > N.

---

## Per-Batch Rule 10a Checkpoints

**Batch 1:** loader.py KIND constants match PHP (KIND_ALL=1, KIND_SYSTEM=2, KIND_USER=3); every function has `# Source` comment.

**Batch 2:** HOOK_SANITIZE line # < strip_harmful_tags call line # in sanitize.py; format_inline_player absent; all 4 TODOs closed (grep "TODO Phase 2" = 0); HOOK_FETCH_FEED before feedparser.parse() in feed_tasks.py.

**Batch 3:** initialize_user_prefs uses `IS NULL` (not `= NULL`) for null profile path; iterates ttrss_prefs (not ttrss_user_prefs).

**Batch 4:** `session["auth_module"]` set on every auth path; initialize_user inserts real feeds with exact URLs; logout_user deletes Redis key.

---

## Validation Workflow

```bash
# After each batch:
python tools/graph_analysis/validate_coverage.py \
    --graph-dir tools/graph_analysis/output \
    --python-dir target-repos/ttrss-python/ttrss
pytest --cov=ttrss.utils.misc --cov=ttrss.plugins.loader --cov-fail-under=80
# (adjust module paths per batch)
```

---

## Status: DONE

All 4 batches committed. 15 exit criteria met. Graph gates passed. Tests sparse on some modules — Phase 5b coverage verification addressed remaining gaps.
