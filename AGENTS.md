# AGENTS.md — PHP-to-Python Migration Project

## Mission

Migrate Tiny Tiny RSS (TT-RSS) from PHP to Python, fully preserving all specs, design, and behavior of the source project.

## Project Layout

Managed with **specify-cli** (GitHub Spec-Kit). Install: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`

```
OSS_Migration/
├── AGENTS.md                    ← Project rules & conventions (this file)
├── CLAUDE.md                    ← Umbrella: points here
├── constitution.md              ← Governing principles (spec-kit root doc)
│
├── specs/                       ← Spec-kit feature specs (non-flat)
│   ├── architecture/            ← System reference specs (stable, read-only)
│   │   ├── 00-project-charter.md
│   │   ├── 01-architecture.md … 14-semantic-discrepancies.md
│   ├── 001-foundation/          ← Phase 1  [DONE]  spec.md · plan.md · tasks.md
│   ├── 002-core-logic/          ← Phase 2  [DONE]  spec.md · plan.md · tasks.md
│   ├── 003-business-logic/      ← Phase 3  [DONE]  spec.md · plan.md · tasks.md
│   ├── 004-api-handlers/        ← Phase 4  [DONE]  spec.md · plan.md · tasks.md
│   ├── 005-semantic-verification/ ← Phase 5 [DONE]  spec.md · plan.md · tasks.md
│   └── 006-deployment/          ← Phase 6  [DONE]   spec.md · plan.md · tasks.md
│
├── docs/
│   ├── decisions/               ← ADRs 0001-0016 (MADR 4.0)
│   │   └── README.md
│   └── reports/                 ← Completed analysis reports
│       └── semantic-verification.md
│
├── memory/                      ← Cross-session context (Claude extension)
│   ├── MEMORY.md                ← Index (loaded every session)
│   ├── sessions/                ← Per-session notes
│   │   ├── 2026-04-03.md
│   │   ├── 2026-04-04.md
│   │   └── 2026-04-05.md
│   ├── feedback/                ← Behavioral rules for Claude
│   │   ├── consistency-rule.md
│   │   └── spec-consultation.md
│   ├── project/                 ← Project-level context
│   │   └── setup.md
│   ├── test_coverage_uplift_plan.md  ← DONE: coverage uplift to ≥95%
│   └── archive/                 ← Superseded plans (audit trail)
│
├── rules/                       ← Supplementary verification rules
├── source-repos/                ← READ-ONLY: PHP source
└── target-repos/                ← Python migration output
```

## Spec-Kit Conventions (MANDATORY)

This project uses **GitHub Spec-Kit** (`specify-cli` v0.5.1, MIT) for Spec-Driven Development.
Install: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`
CLI: `specify init`, `specify check`, `specify extension`, `specify integration`

Spec-Kit defines 6 phases: **Constitution → Specification → Planning → Tasks → Execution → Validation**

### Spec-Kit Workflow (MANDATORY for all phases)

**Every phase and feature MUST follow the full spec-kit skill workflow from inception:**

1. `/speckit-specify <feature description>` — creates feature branch + `spec.md`
2. `/speckit-plan` — generates `plan.md`, `research.md`, `data-model.md` on the feature branch
3. `/speckit-tasks` — generates `tasks.md` from plan artifacts
4. `/speckit-implement` — implements from tasks
5. `/speckit-analyze` or `/speckit-checklist` — validate completeness before merge

Each phase gets its own git branch (`NNN-feature-name`). The `speckit-specify` script auto-numbers branches sequentially from `.specify/init-options.json`.

### Tooling Rule

`specify` must be available (installed via `uv tool`). Verify with:
```
specify check
```

### Directory Purpose Rules (STRICT)

This project was initialized before spec-kit; its structure maps to spec-kit as follows:

| This project | Spec-Kit equivalent | Purpose | Rule |
|---|---|---|---|
| `specs/` | `specs/` | Stable architectural specifications | No plans, no decisions, no session notes |
| `docs/decisions/` | project-root ADRs | Architecture Decision Records | Immutable once accepted; MADR 4.0 format |
| `docs/` | `docs/` | Completed artefacts and reports | No active plans; no ADRs |
| `memory/` | *(Claude extension)* | Cross-session context, active plans | Session notes, work-in-progress, active plans |
| `.claude/commands/` | `.claude/commands/` | Claude Code skill files | Skills only; no specs or memory |
| `specs/00-project-charter.md` | `constitution.md` | Governing principles | Supersedes all other practices |

**The routing rule — one question determines where a file goes:**

> *"Is this work still in progress, or is it a settled record?"*

- **In progress / active** → `memory/` (plans, current phase, blockers)
- **Settled decision** → `docs/decisions/` as ADR
- **Stable spec** → `specs/`
- **Completed report** → `docs/`

### ADR Format (MADR 4.0 — MANDATORY)

Every ADR in `docs/decisions/` MUST use this exact structure:

```markdown
---
status: proposed | accepted | deprecated | superseded by [NNNN]
date: YYYY-MM-DD
decision_makers: [list]
consulted: [list]
informed: [list]
---

# NNNN — Title as Present-Tense Verb Phrase

## Context and Problem Statement
Why this decision is needed.

## Decision Drivers
- Driver 1

## Considered Options
1. Option A — one line
2. Option B — one line

## Decision
Chosen: **Option X**, because [rationale].

## Consequences
### Positive
### Negative

## Confirmation
How to verify this decision is implemented in code.
```

Naming: `NNNN-verb-noun.md`. Numbers sequential, never reused.

### Spec-Kit Template Shapes (for new work)

When starting new features, use spec-kit templates:
- `constitution.md` — project principles (already: `specs/00-project-charter.md`)
- `spec-template.md` → user stories, FR-NNN requirements, acceptance criteria
- `plan-template.md` → technical context, constitution check gate, structure
- `tasks-template.md` → phased tasks with [P] parallel markers, US# story refs, checkboxes

### Memory File Rules (MANDATORY)

Every `memory/*.md` MUST have YAML frontmatter:
```yaml
---
name: descriptive-slug
description: One-line — used to decide relevance in future sessions
type: project | feedback | user | reference
---
```

`project` = active plans/status | `feedback` = behavioral rules | `user` = user profile | `reference` = external pointers

### Test Traceability Rule (MANDATORY)

Every unit test docstring MUST cite its PHP source:
```python
def test_sanitize_empty_string():
    """
    Source: ttrss/include/functions2.php:sanitize line 834
    PHP: $res = trim($str); if (!$res) return ''
    Assert: sanitize("") returns empty string.
    """
```

No test without PHP source citation may be committed.

## Critical Rules

### Storage Rules
1. **NEVER** write files into `~/.claude/projects/*/memory/` — all memory goes to `./memory/`
2. **NEVER** modify anything inside `source-repos/` — it is read-only reference
3. **NEVER** store project specs, memory, or rules in `.claude/` — that dir is only for Claude-specific config (settings, skills)
4. All specs, memory, rules, and artifacts go in the **project root** under their respective directories
5. This ensures cross-platform portability (not tied to Claude's home directory)

### Migration Rules
6. Target Python code goes into `target-repos/` — this is where the migrated project grows
7. Every spec document in `specs/` must cross-reference source files by relative path (e.g., `source-repos/ttrss-php/ttrss/classes/db.php`) rather than duplicating source code
8. Specs may include **reasonable code examples** to highlight important architectural decisions, but must not be a copy of the source
9. When migrating, always verify behavior parity against the source spec before marking a component complete

### Source Traceability Rule (MANDATORY)
10. **Every meaningful code element** (function, class, method, model, route, constant) in `target-repos/` **MUST** have a traceability comment linking it to its PHP source origin. This is a hard constraint — code without traceability comments must not be committed.

    **Traceability comment format** (use the most specific match available):

    ```python
    # Source: ttrss/classes/feeds.php:Feeds::view (lines 45-120)
    def view_feed(feed_id: int, view_mode: str) -> dict:
        ...

    # Source: ttrss/include/functions.php:catchup_feed (lines 1094-1237)
    def catchup_feed(feed_id: int, cat_view: bool, ...) -> None:
        ...

    # Source: ttrss/classes/db.php:Db (singleton pattern)
    # Python equivalent: SQLAlchemy engine via Flask-SQLAlchemy extension
    db = SQLAlchemy(model_class=Base)

    # Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_feeds, lines 38-72)
    class Feed(Base):
        __tablename__ = "ttrss_feeds"
        ...
    ```

    **Match levels** (use the most specific that applies):
    - **Direct**: `function → function` or `class → class` (e.g., `Feeds::view` → `view_feed()`)
    - **Method-level**: `Class::method` → Python method (e.g., `RPC::mark` → `rpc.mark_article()`)
    - **File-level**: When a Python module aggregates logic from a single PHP file (e.g., `# Source: ttrss/include/ccache.php`)
    - **Multi-file**: When a Python module synthesizes logic from multiple PHP files (e.g., `# Source: ttrss/include/functions.php + ttrss/include/functions2.php (query building)`)
    - **Schema-level**: For models derived from SQL schema (e.g., `# Source: ttrss/schema/ttrss_schema_pgsql.sql (table ttrss_user_entries)`)
    - **Inferred**: When Python code has no direct PHP equivalent but was inferred from PHP patterns (e.g., `# Inferred from: ttrss/include/sessions.php (session validation pattern, adapted for Flask-Login)`)
    - **New**: When code is genuinely new with no PHP source (e.g., `# New: no PHP equivalent (Alembic migration infrastructure)`)

### Traceability Verification Rule (MANDATORY)
10a. **After generating or modifying target code**, run the traceability & correctness verification workflow defined in `rules/traceability-verification.md`. This is also required **between major phases** (e.g., Phase 1a→1b, 1b→2). The workflow uses adversarial self-refine with isolated CRITIC/AUTHOR agents to catch schema mismatches, missing traceability comments, phantom columns/defaults, and logic divergence from PHP source.

### Analysis Rules
10. Use deep web research for any complicated architectural topic (PHP patterns, 3-tier architecture, ORM vs transactional script, etc.)
11. For source code analysis dimensions (call graph, entity graph, etc.), consider using NetworkX and Leiden community detection
12. Migration flow is driven by dimensions documented in `specs/10-migration-dimensions.md` — discuss and choose flow before starting migration

### Quality Rules
13. Preserve all functional behavior from the PHP source
14. Fix known security issues during migration (SHA1→argon2id, prepared statements, etc.) — document deviations in specs
15. Maintain spec-to-code traceability throughout the migration

### No-Skip Rule (HARD PROHIBITION)
16. **NEVER skip a test, and NEVER write a workaround that causes a test to skip.** This is a hard constraint with zero exceptions.

    **Prohibited patterns:**
    - `@pytest.mark.skip` / `@pytest.mark.skipif`
    - `pytest.skip()` calls inside test bodies or fixtures (except infrastructure fast-fail: DB/Redis unreachable)
    - `unittest.skip` decorators
    - `MISSING_PORT`, `TODO`, or any other rationale — not acceptable
    - Patching in the wrong namespace so the test passes silently (e.g. `patch("flask_login.login_user")` instead of `patch("ttrss.blueprints.public.views.login_user")`)

    **Required instead:**
    - If a function is missing from the Python codebase → implement it, then write the test.
    - If a test relies on infrastructure (DB, Redis) → fix the environment, not the test.
    - If a test is failing due to a real bug → fix the bug.

    **Gate:** `pytest` must exit with 0 skips. Any skip in CI is a build failure.

### Consistency Rule (MANDATORY)
16. **When any status, decision, or phase changes**, update ALL locations that reference it in the same commit. This is a hard constraint — partial status updates create contradictions that compound across sessions.

    **Mandatory update checklist** (run mentally before every status change):
    - [ ] `AGENTS.md` — Architecture Decisions table (status column)
    - [ ] `docs/decisions/README.md` — Decision Index table (status + priority columns)
    - [ ] `docs/decisions/XXXX-*.md` — the ADR itself (Status, Date accepted, Deciders, Decision section)
    - [ ] `specs/00-project-charter.md` — Solution Space table (decision + status columns)
    - [ ] `specs/00-project-charter.md` — Requirements Traceability Matrix (status column)
    - [ ] `specs/00-project-charter.md` — Cross-Reference table (if new ADR linkages discovered)
    - [ ] `specs/10-migration-dimensions.md` — Recommendation Matrix (if flow variant affected)
    - [ ] `memory/session_*.md` — session memory (current state for next session)

    **Applies to**: ADR acceptance/rejection, phase completion, security finding remediation, requirement status changes, any table row that tracks status or decisions.

## Spec-Kit Phase Index

| Phase spec | Status | Contents |
|-----------|--------|----------|
| `specs/001-foundation/` | DONE | Flask skeleton, 31 models, 24 hookspecs, Alembic |
| `specs/002-core-logic/` | DONE | Feed parsing, sanitize, counter cache, auth |
| `specs/003-business-logic/` | DONE | Prefs CRUD, digests, OPML, backend blueprint |
| `specs/004-api-handlers/` | DONE | 17 API ops, 2-guard auth, getFeedTree BFS |
| `specs/005-semantic-verification/` | DONE | 40-cat taxonomy, 8 pipelines, 105+ fixes, 598 tests, 0 gaps |
| `specs/006-deployment/` | DONE | CI, coverage gate ≥95%, Docker, nginx, pgloader, deploy.yml |

## Architecture Reference Index

All under `specs/architecture/` — stable, read-only reference:

| File | Contents |
|------|----------|
| `00-project-charter.md` | Mission, Goals, Premises, Constraints, traceability matrix |
| `01-architecture.md` | Application layers, design patterns, request lifecycle |
| `02-database.md` | 35 tables, FK map, migration system, seed data |
| `03-api-routing.md` | Entry points, handler dispatch, RPC endpoints |
| `04-frontend.md` | JS files, AJAX patterns |
| `05-plugin-system.md` | 24 hooks, plugin lifecycle, system vs user plugins |
| `06-security.md` | 10 findings by severity, auth flow, encryption |
| `07-caching-performance.md` | Counter cache, HTTP caching, daemon architecture |
| `08-deployment.md` | Docker, Nginx, CI/CD, environment config |
| `09-source-index.md` | Complete PHP file inventory with annotations |
| `10-migration-dimensions.md` | Call graph, entity graph, migration flow variants |
| `11-business-rules.md` | 20 business rules with exact PHP line refs |
| `12-testing-strategy.md` | Parity verification, 5 test categories, fixtures |
| `13-decomposition-map.md` | functions.php decomposition into Python modules |
| `14-semantic-discrepancies.md` | D01-D40 taxonomy, traps, 8 pipeline contracts |

## Architecture Decisions (docs/decisions/)

| ADR | Title | Status |
|-----|-------|--------|
| 0001 | Migration Flow Variant | **accepted** — P0, Variant D-revised |
| 0002 | Python Web Framework | **accepted** — P0, Flask |
| 0003 | Database Engine Choice | **accepted** — P0, PostgreSQL + psycopg2 |
| 0004 | Frontend Migration Strategy | proposed — P1, Tier 3 (Phase 2 exit) |
| 0005 | Automated Call Graph Analysis | **accepted** — P1, Option B (manual) |
| 0006 | ORM vs Raw SQL | **accepted** — P1, SQLAlchemy ORM (hybrid Core) |
| 0007 | Session Management | **accepted** — P1, Flask-Login + Redis |
| 0008 | Password Hash Migration | **accepted** — P1, Dual-hash gradual (argon2id) |
| 0009 | Feed Credential Encryption | **accepted** — P1, Fernet |
| 0010 | Plugin System Implementation | **accepted** — P2, pluggy + importlib directory discovery |
| 0011 | Background Worker Architecture | **accepted** — P1, Celery + Redis (two-task fan-out) |
| 0012 | Logging Strategy | proposed — P2 |
| 0013 | i18n Approach | proposed — P2 |
| 0014 | Feed Parsing Library | **accepted** — P1, feedparser + lxml sanitization |
| 0015 | HTTP Client | **accepted** — P1, httpx async in Celery workers only |
| 0016 | Semantic Verification Methodology | **accepted** — P0, 40-cat taxonomy + pipelines + triage |
| 0017 | Frontend: Vanilla JS SPA | **accepted** — P1, replaces Dojo toolkit (ADR-0004 resolved) |
| 0018 | Drag-Drop Category Assignment | **accepted** — P2, deferred; dropdown used instead |
| 0019 | Preferences Modal Pattern | **accepted** — P1, simplified tabbed in-app modal |

See `docs/decisions/README.md` for decision dependencies. ADR format follows [MADR](https://adr.github.io/madr/) convention.

## Skills (`.claude/skills/`)

**Spec-Kit skills** (installed via `specify init --ai claude`, ready to use):

| Skill | Slash command | Purpose |
|-------|--------------|---------|
| speckit-constitution | `/speckit-constitution` | Establish / review project principles |
| speckit-specify | `/speckit-specify` | Create a new feature specification |
| speckit-plan | `/speckit-plan` | Generate implementation plan from spec |
| speckit-tasks | `/speckit-tasks` | Break plan into actionable tasks |
| speckit-implement | `/speckit-implement` | Execute implementation from tasks |
| speckit-clarify | `/speckit-clarify` | De-risk ambiguous areas before planning |
| speckit-analyze | `/speckit-analyze` | Cross-artifact consistency report |
| speckit-checklist | `/speckit-checklist` | Validate requirements completeness |

**Additional recommended skills** (install manually if needed):

- **inferring-requirements** — requirements discovery before each migration phase
- **deep-research-t1** — research Python equivalents for PHP patterns
- **document-ingestion** — if external specs/docs need processing
- **continuation-and-handoff** — multi-session migration continuity
- **adversarial-self-refine** — iterative quality improvement of migrated code
- **selecting-pe-methods** — choose optimal reasoning strategy per migration task
