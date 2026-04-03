# Traceability & Correctness Verification Workflow

**When to run**: After generating/modifying target code, OR periodically between major phases.
**Invocation**: `/adversarial-self-refine` with argument: `run traceability-verification per rules/traceability-verification.md`

---

## Purpose

Bi-directionally verify that ALL target Python code in `target-repos/ttrss-python/`:
1. Matches the PHP source schema and logic EXACTLY
2. Has complete traceability comments (AGENTS.md Rule 10)
3. Aligns with specs and ADR decisions
4. Contains no phantom columns, phantom defaults, or type mismatches

---

## Workflow Steps

### Step 1: Full State Capture (parallel)

Launch 3 parallel Explore agents:

**Agent A — Read ALL target files:**
- Every `.py` file in `target-repos/ttrss-python/ttrss/` (models, auth, crypto, blueprints, config, extensions, errors, __init__)
- Every `.py` file in `target-repos/ttrss-python/tests/`
- `target-repos/ttrss-python/alembic/env.py`

**Agent B — Read ALL PHP source files:**
- `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql` (AUTHORITATIVE for column types/sizes/nullability/defaults/FKs/indexes)
- `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` (password authentication)
- `source-repos/ttrss-php/ttrss/include/functions.php` (authenticate_user, login_sequence, session setup)
- `source-repos/ttrss-php/ttrss/include/functions2.php` (encrypt_password lines 1481-1489)
- `source-repos/ttrss-php/ttrss/include/sessions.php` (validate_session)
- `source-repos/ttrss-php/ttrss/classes/api.php` (API dispatch, login, response format)
- `source-repos/ttrss-php/ttrss/classes/rpc.php` (RPC methods)
- `source-repos/ttrss-php/ttrss/classes/db.php` (DB singleton)
- `source-repos/ttrss-php/ttrss/classes/pref/users.php` (user/password management)
- `source-repos/ttrss-php/ttrss/config.php-dist` (configuration constants)
- `source-repos/ttrss-php/ttrss/backend.php` (backend dispatch)
- `source-repos/ttrss-php/ttrss/public.php` (public handler)
- `source-repos/ttrss-php/ttrss/include/crypt.php` (encryption)
- Any other PHP files referenced by the target code's `# Source:` comments

**Agent C — Read ALL specs and ADRs:**
- `specs/01-architecture.md` through `specs/12-testing-strategy.md` (focus on sections relevant to target code)
- All ACCEPTED ADRs in `docs/decisions/` (currently 0001-0009)
- `memory/session_*.md` (latest session state)

### Step 2: Bi-directional Cross-Verification

Build a verification matrix covering these dimensions:

#### 2a. Schema Correctness (PHP SQL → Python Models)
For EVERY table modeled in Python, verify column-by-column against `ttrss_schema_pgsql.sql`:

| Check | Rule |
|-------|------|
| Column name | Must match PHP exactly |
| Column type | `varchar(N)` → `String(N)`, `text` → `Text`, `boolean` → `Boolean`, `integer`/`int` → `Integer`, `serial` → `Integer primary_key=True`, `timestamp` → `DateTime` |
| Column size | `String(N)` must match PHP `varchar(N)` exactly |
| Nullability | PHP `NOT NULL` → `nullable=False`; PHP no NOT NULL → `Optional` / nullable |
| Default | PHP `default X` → `default=X`; NO phantom defaults (defaults not in PHP) |
| Unique | PHP `UNIQUE` → `unique=True` |
| ForeignKey | PHP `references table(col)` → `ForeignKey("table.col")` |
| ondelete | PHP `ON DELETE CASCADE` → `ondelete="CASCADE"`; PHP `ON DELETE SET NULL` → `ondelete="SET NULL"` |
| Indexes | Every PHP `CREATE INDEX` → corresponding `index=True` on the column |
| No phantom columns | Every Python column MUST exist in PHP schema |
| No missing columns | Every PHP column SHOULD exist in Python (note Phase 1b deferrals explicitly) |

#### 2b. Code Logic Correctness (PHP Functions → Python Functions)
For EVERY function/method in target code, verify against PHP source:

| Check | Rule |
|-------|------|
| Password hashing | `encrypt_password()` logic in functions2.php:1481-1489 must match `verify_password()` exactly |
| API response format | `{"seq": N, "status": 0\|1, "content": {...}}` — seq MUST be echoed |
| API CSRF | API blueprint must be CSRF-exempt (PHP API has no CSRF) |
| Session handling | Only `user_id` in session, NEVER `pwd_hash` (AR05) |
| Fernet encryption | Matches ADR-0009 (MultiFernet, key from config, no key in model code) |
| Config mapping | Every PHP config constant must map to correct Flask config key |
| Error responses | Must include seq field for API paths |
| Request parameter reading | Must match PHP `$_REQUEST` merge behavior (GET+POST) |

#### 2c. Traceability Comment Completeness (AGENTS.md Rule 10)
For EVERY meaningful code element (function, class, method, model, route, constant):

| Check | Rule |
|-------|------|
| Has traceability comment | `# Source:`, `# Inferred from:`, or `# New:` prefix |
| Source reference is accurate | File path, class::method, line numbers match actual PHP source |
| Spec/ADR cross-references | Module docstrings reference relevant specs and ADRs |
| Package `__init__.py` files | Must have traceability comment on re-export imports |

#### 2d. Spec/ADR Alignment
For EVERY accepted ADR decision:

| Check | Rule |
|-------|------|
| ADR implemented | The decision is reflected in target code |
| Security findings addressed | Each spec-06 finding mapped to implementation |
| No contradictions | Target code doesn't contradict any spec or ADR |

### Step 3: Adversarial Self-Refine Loop

Use `/adversarial-self-refine` with the following adapted prompts:

**CRITIC prompt template:**
```
REQUIREMENTS:
[Paste the verification matrix results from Step 2]

SOLUTION:
[The current target codebase state — list all files and their contents]

You are a compliance reviewer for a PHP-to-Python migration.
The PHP schema at source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql is AUTHORITATIVE.
Every Python model column must match it EXACTLY.
Every code element must have a traceability comment per AGENTS.md Rule 10.

Identify every point of non-compliance:
1) What is wrong? (type mismatch, size mismatch, nullability, phantom default, etc.)
2) What is missing? (columns, FKs, indexes, traceability comments, etc.)
3) What is over-engineered? (phantom columns, unnecessary abstractions, etc.)
4) What is inappropriate in scope? (Phase 1b work in Phase 1a, etc.)
```

**AUTHOR prompt template:**
```
SOLUTION:
[Current target codebase]

FEEDBACK:
[FULL CRITIC output — never summarize]

This feedback was received on your migration code. Address ALL points.
Generate the revised files. For each changed file, output the complete file content.
```

**Termination signals:**
- DEFENSE: AUTHOR argues the code is correct → STOP (convergence)
- CONVERGE: Round N output ≈ Round N-1 output → STOP
- TIMEOUT: Max 3 rounds → STOP with best

### Step 4: Test Verification

After all corrections applied:
```bash
cd target-repos/ttrss-python
docker compose -f docker-compose.test.yml up -d
.venv/bin/python -m pytest tests/ -v
```

ALL tests must pass. If new columns/FKs break integration tests, update `conftest.py` fixtures.

### Step 5: Memory Update

After verification completes:
1. Update `memory/session_*.md` with verification results
2. Fix any stale descriptions found during verification
3. Note any deferred items for next phase

---

## Quick Checklist (for fast runs between small changes)

If you only changed a few files, run the abbreviated version:

- [ ] Read the changed target files
- [ ] Read the corresponding PHP source files referenced in `# Source:` comments
- [ ] Verify column-by-column against PHP schema SQL
- [ ] Verify every code element has correct traceability comment
- [ ] Run `pytest tests/ -v` — all green
- [ ] Update session memory if needed

---

## Known Gotchas (learned from past verification rounds)

1. **SHA1X format**: `sha1(login + ":" + password)` — the salt is the LOGIN name with colon separator, NOT `sha1(salt + password)`
2. **PHP `NOT NULL default ''`**: Python must use `nullable=False, default=""` — NOT `Optional`/nullable
3. **`ttrss_version` has no PK in PHP**: SQLAlchemy requires one — document the deviation with `# Inferred PK:` comment
4. **Flask config keys**: `PERMANENT_SESSION_LIFETIME` (not `SESSION_COOKIE_LIFETIME`), must be `timedelta` or int seconds
5. **API CSRF exemption**: PHP API has no CSRF — Flask API blueprint must call `csrf.exempt(api_bp)`
6. **`argon2.exceptions.VerificationError`**: Catch the parent class, not just `InvalidHashError` + `VerifyMismatchError`
7. **Phantom defaults**: PHP schema `NOT NULL` without `DEFAULT` means NO default in Python — application must supply value at insert
8. **`orig_feed_id` FK**: References `ttrss_archived_feeds` which may not be modeled yet — column present, FK deferred
9. **PHP `text` type**: Maps to SQLAlchemy `Text`, NOT `String(N)` — `String(N)` is for `varchar(N)` only
10. **PHP `int` vs `integer`**: Both map to SQLAlchemy `Integer` (NOT `SmallInteger`)
