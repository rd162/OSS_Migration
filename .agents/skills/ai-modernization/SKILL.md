---
name: ai-modernization
description: >
  Conduct AI-assisted software modernizations between any technology stacks using spec-driven,
  dimension-analyzed, adversarially-verified workflows. Use this skill whenever the user wants
  to migrate a codebase from one language/framework to another, port an application to a new
  platform, modernize a legacy system, or rewrite software while preserving behavior. Triggers
  on: "migrate", "port", "rewrite", "modernize", "convert from X to Y", "translation" of code,
  any mention of source-to-target technology pairs. Also use when the user is mid-modernization and
  needs to resume, run coverage checks, do semantic verification, or create modernization specs.
  Even if the user just says "continue the modernization" or "what's next", use this skill to
  determine the current phase and guide the next step.
---

# AI-Assisted Software Modernization

A spec-driven, multi-session framework for migrating arbitrary software systems while preserving
behavioral equivalence. Works for any source-to-target technology pair and any application type.

## How This Skill Works

This skill guides you through a complete modernization workflow. It detects where you are in the
process and tells you what to do next. The workflow has six phases, each building on the last.

**On first invocation**, assess the project state:

1. Check if `AGENTS.md` exists -- if so, read it to understand where the modernization stands
2. Check if `specs/architecture/` exists -- if so, Phase 0 is done
3. Check if `docs/decisions/` has accepted ADRs -- if so, Phase 2 is done
4. Check if `specs/NNN-*/tasks.md` exist with checkboxes -- assess Phase 4 progress
5. If nothing exists, start from Phase 0

---

## Composition with phase macro-skills

This skill is the **spine** of the AI-Assisted Software Modernization
Architecture. When invoked standalone it carries the full Phase 0 → 5
workflow below. When invoked inside this project (`OSS_Migration`), it
is the shared reference consumed by four phase-specific macro-skills
that handle the heavy lifting for each inception phase:

| Phase | Phase macro-skill        | What it delegates to atomic skills                                                                                       |
| :---: | ------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
|   1   | `specs-extractor`        | `deep-research-t1` + `requirements-extractor` + `knowledge-management`                            |
|   2   | `decisions-generator`    | `adversarial-thinking` + `deep-research-t1`                                                     |
|   3   | `target-specs-generator` | `adversarial-self-refine` + `deep-research-t1` + `requirements-extractor`                                                |
|   4   | `target-code-refiner`    | `ai-modernization` (this file, per-batch loop) + `adversarial-self-refine` + `deep-research-t1` |

The phase macro-skills live in `.agents/skills/<name>/SKILL.md` and carry
no methodology of their own — they sequence atomic skills in a fixed
order against a specific phase input, to produce a specific phase
output. Thin Claude-specific runtime wrappers in `.claude/agents/*.md`
preload each macro-skill plus its composed atomic skills so session-wide
invocation (`@specs-extractor`, `@decisions-generator`, etc.) gets the
full context without discovery round-trips.

**When running against this project**, prefer invoking the matching
phase macro-skill over executing the corresponding phase from this spine
directly — the macro-skills wire in the adversarial-refine and deep-research
calls that this spine describes in prose, and they enforce the project's
loop-back edges (Phase 4 → Phase 2 / Phase 3 when evidence invalidates
upstream artifacts).

**When running against a fresh project** (bootstrap, no macro-skills yet),
execute this spine's Phase 0 → 5 directly; the macro-skills can be
introduced later once the project has stabilised.

For the full pipeline diagram, authoring rules, and cross-platform
portability considerations, see
`docs/ai-assisted-modernization-architecture.md` §"Skill / Agent Composition"
and Appendix I (Agent Integration).

---

## Phase 0: Deep Knowledge Extraction

**Goal**: Understand the source system deeply enough to make informed modernization decisions.

**When to run**: The project has source code but no specs, no dimension analysis, no ADRs.

> **Preferred execution**: this project defines a dedicated Phase-1 macro-skill,
> `specs-extractor`, that carries the authoritative ten-step workflow for this
> phase (research-driven dimension inference, per-dimension graph extraction via
> NetworkX + Leiden, per-community deep research with a budget cap, and
> evidence-based synthesis of the final spec set).
>
> When running inside this project, invoke `specs-extractor` directly
> (`@specs-extractor` or `claude --agent specs-extractor`) instead of executing
> the condensed steps below. The macro-skill produces the same outputs at
> higher fidelity and enforces the exit gate.
>
> The steps below remain as a minimal fallback for runtimes where the
> macro-skill is unavailable.

### Fallback steps (when `specs-extractor` unavailable)

1. **Inventory + archetype detection** — list source files; detect the
   application archetype (web app, CLI, daemon, ETL, protocol, library,
   embedded, plugin host, etc.) from entry points and dependencies.

2. **External knowledge grounding** — invoke `deep-research-t1` (or any web
   research tool) with three fan-outs: source-platform patterns for this
   archetype, target-platform best practices for the same archetype, and
   modernization pitfalls for the specific source→target pair.

3. **Dimension inference** — derive the set of dimensions relevant to this
   specific application from (a) the archetype, (b) research findings,
   (c) source evidence. Do NOT use a fixed slot list.

4. **Per-dimension graph extraction** — build NetworkX graphs (AST-parse
   source, emit typed nodes + edges per dimension). Apply Leiden community
   detection; compute dependency levels via SCC condensation. Reference
   implementation for PHP is at `tools/graph_analysis/build_php_graphs.py`;
   the same pipeline adapts to any source language by swapping the AST parser.

5. **Per-community research** — for each (dimension, community) pair, invoke
   deep research for target-side patterns, known traps, and open-source
   comparables. Group aggressively to stay under a hard cap of 50 research
   passes.

6. **Spec synthesis** — one spec file per discovered dimension, named by the
   dimension (not by a pre-fixed slot). Every non-trivial claim cites a
   source `file:line` or a tier-annotated research URL.

7. **Modernization flow variants** — derive at least three variants from the
   actual community structure discovered above.

8. **Requirements document** — invoke `requirements-extractor` to produce the
   project charter (Mission / Goals / Premises / Constraints + RTM).

9. **Divergence catalogue (seed)** — aggregate all divergences surfaced in
   research into the initial `NN-semantic-discrepancies.md`.

10. **Project governance** — `AGENTS.md` with phase index + spec pointers;
    `CLAUDE.md` with the `@AGENTS.md` shim for Claude Code.

### Phase 0 Exit Gate

- [ ] Source inventory complete; archetype recorded.
- [ ] External research grounded with T1 citations.
- [ ] Dimension set inferred from evidence (not a fixed slot list).
- [ ] At least three dimensions have extracted graphs + communities + levels.
- [ ] Per-community research notes exist for every retained community
      (or grouped community under the 50-pass cap).
- [ ] One dimension-spec file per discovered dimension.
- [ ] `00-project-charter.md` with MGPC + RTM.
- [ ] `NN-modernization-dimensions.md` with at least three flow variants
      derived from actual community structure.
- [ ] `NN-semantic-discrepancies.md` seeded with research entries.
- [ ] AGENTS.md + CLAUDE.md (or equivalents) written.

---

## Phase 1: Spec Generation and ADR Proposals

**Goal**: Create formal specs and propose all architectural decisions needed before coding begins.

**When to run**: Source analysis is done, but no ADRs have been accepted yet.

### Steps

1. **Create a project charter** (`specs/architecture/00-project-charter.md`)
   - Mission, goals, premises, constraints
   - Requirements traceability matrix
   - Solution space table linking decisions to ADRs

2. **Draft ADRs for every non-trivial decision**
   Use MADR 4.0 format (see `references/adr-template.md`). Prioritize:
   - **P0 (blocks all work)**: Migration flow variant, target framework/language, database engine
   - **P1 (blocks specific phases)**: ORM strategy, auth mechanism, background workers, etc.
   - **P2 (deferrable)**: Logging, i18n, monitoring, etc.
     Each ADR includes context, 2-4 options, trade-off analysis table, preliminary recommendation.

3. **Create ADR dependency graph** (`docs/decisions/README.md`)
   Show which ADRs depend on which others. P0 must be decided first.

### Phase 1 Exit Gate

- [ ] Project charter with traceability matrix
- [ ] All P0 and P1 ADRs drafted with trade-off analysis
- [ ] ADR dependency graph documented
- [ ] Product team review point: participate in trade-off evaluation

---

## Phase 2: ADR Acceptance via Adversarial Evaluation

**Goal**: Accept all blocking ADRs using rigorous evaluation, not gut feeling.

**When to run**: ADRs are drafted but not yet accepted.

### Steps

For each P0 ADR (then P1 in dependency order):

1. **Research phase**: Use web research to validate each option's claims about maturity,
   community support, and known issues
2. **Generate 3 divergent candidates**: Each prioritizes a different trade-off axis
   (time-to-market vs. technical excellence vs. maximum fidelity)
3. **Stress test**: Use adversarial evaluation -- an isolated critic agent tries to find
   fatal flaws in each candidate
4. **Convergence check**: If all candidates converge post-critique, the answer is clear
5. **Pairwise comparison**: If divergent, compare pairs to select the winner
6. **Document**: Write the decision into the ADR. Update ALL referencing locations:
   - The ADR file itself
   - `AGENTS.md` decision table
   - `docs/decisions/README.md` index
   - `specs/architecture/00-project-charter.md` solution space + RTM
   - `specs/architecture/NN-modernization-dimensions.md` recommendation matrix
   - Current session memory

   **This atomic update is critical -- partial status updates create contradictions that
   compound across sessions.**

### Phase 2 Exit Gate

- [ ] All P0 ADRs accepted with documented rationale
- [ ] All P1 ADRs accepted (or explicitly deferred to P2 with rationale)
- [ ] Every status change updated in ALL referencing locations
- [ ] Product team sign-off on key trade-offs

---

## Phase 3: Modernization Plan and Roadmap

**Goal**: Generate a dependency-ordered, phase-gated modernization plan.

**When to run**: ADRs are accepted, but no phase specs exist yet.

### Steps

1. **Select modernization flow variant** from the accepted ADR
2. **Define phases** based on dimension analysis:
   - Each phase corresponds to a graph community or dependency level
   - Phases are ordered by their dependency level (lower levels first)
   - Each phase has explicit entry/exit criteria
3. **For each phase**, create a spec-kit triplet:
   - `specs/NNN-phase-name/spec.md` -- user stories, requirements, acceptance criteria
   - `specs/NNN-phase-name/plan.md` -- technical context, constitution check, implementation batches
   - `specs/NNN-phase-name/tasks.md` -- checkboxed tasks with [P] parallel markers

4. **Define the walking skeleton** (first phase):
   The walking skeleton is the minimum viable subset that produces a runnable application.
   It should be achievable quickly (days, not weeks) and give confidence that the target
   architecture works. This is the most important phase for morale and risk reduction.

5. **Define data migration strategy**:
   - Schema mapping (source schema → target models)
   - Transformation rules for schema changes (documented as ADRs)
   - Seed data for development (minimum viable dataset per entity cluster, FK-ordered)
   - Subset strategy for testing (anonymization rules for PII)
   - Full modernization tooling identification

### Phase 3 Exit Gate

- [ ] All phases defined with spec/plan/tasks triplets
- [ ] Walking skeleton is Phase 1 with clear deliverables
- [ ] Data migration strategy documented
- [ ] Product team review: confirm roadmap priorities and timeline

---

## Phase 4: Execution Loop

**Goal**: Implement the modernization phase by phase, with continuous verification.

**When to run**: Phase specs exist, and implementation is in progress.

### Per-Phase Execution

For each phase, follow this loop:

```
Read spec → Read source code → Implement with traceability → Test → Validate coverage → Next batch
```

#### Implementation Rules

1. **Source traceability is mandatory**: Every meaningful code element (function, class,
   method, model, route, constant) must have a traceability comment linking to its source:

   ```
   # Source: path/to/source/file.ext:ClassName::method (lines X-Y)
   ```

   Match levels (use the most specific that applies):
   - **Direct**: source function → target function
   - **Method-level**: Class::method → target method
   - **File-level**: When target module aggregates logic from a single source file
   - **Multi-file**: When target synthesizes from multiple source files
   - **Schema-level**: For models derived from schema definitions
   - **Inferred**: When target code was inferred from source patterns
   - **New**: When code is genuinely new with no source equivalent

2. **Test after every batch**: Run the test suite after implementing each batch of tasks.
   Zero skips policy -- never skip a test; fix the underlying issue instead.

3. **Coverage validation at batch boundaries**: Run the programmatic coverage validator
   to check that new code covers its intended source functions.

4. **Semantic verification for complex functions**: For any Tier 1 function (complex SQL,
   multiple branches, cross-cutting callers), do line-by-line source↔target comparison
   using the language-specific trap catalog.

#### Building the Coverage Validator

Early in Phase 4 (typically during the walking skeleton), build a programmatic coverage
validator tool. This tool:

1. **Parses source files** using an AST parser to extract exact function boundaries
   (start AND end lines -- never approximate from "next function's start")
2. **Scans target files** for traceability comments matching source references
3. **Uses file-specific matching only**: a source function is "covered" only if a target
   file's traceability comment references the SAME source file (never global name fallback)
4. **Reports unmatched functions** as gaps to be resolved
5. **Checks multiple dimensions**: call graph edges, entity references, hook invocations

The validator should run as part of every phase gate.

#### Building the Semantic Trap Catalog

During Phase 4, as you discover translation traps between the source and target languages,
build a project-specific trap catalog (`specs/architecture/NN-semantic-discrepancies.md`).

Organize traps by domain:

- Type system & coercion traps (how the languages handle types differently)
- String & regex traps (encoding, pattern syntax, replacement semantics)
- Date & time traps (format codes, timezone handling, epoch types)
- Database & ORM traps (cursor behavior, transaction boundaries, rowcount)
- HTTP & session traps (parameter merging, header handling, error models)
- Architecture traps (singleton patterns, global state, error recovery)

Each trap entry should have: the source pattern, the target gotcha, and estimated frequency
in the codebase. This catalog grows throughout the modernization and becomes the checklist for
semantic verification.

### Phase 4 Exit Gate (per phase)

- [ ] All tasks in `tasks.md` checked off
- [ ] All tests green, zero skips
- [ ] Coverage validator: 0 unmatched for in-scope functions
- [ ] Semantic verification: Tier 1 functions verified line-by-line
- [ ] All status changes updated in ALL referencing locations

---

## Phase 5: Final Verification and Deployment

**Goal**: Ensure the complete modernization is correct and deploy.

**When to run**: All implementation phases are complete.

### Steps

1. **Full structural coverage check**
   Run the coverage validator across ALL source files. Every function must be either:
   - Exact match (migrated with traceability comment)
   - Eliminated (documented as dead code, deprecated, or language-specific infrastructure)
     Target: 100% coverage (0 unmatched functions)

2. **Full semantic verification**
   Run deep semantic verification across ALL migrated code, not just Tier 1.
   Use adversarial self-refinement: an isolated critic agent reviews each function pair
   against the semantic trap catalog. Every discrepancy must be fixed or documented.

3. **Integration pipeline verification**
   Identify the major multi-step workflows in the application. For each pipeline:
   - Trace the data flow across all participating functions
   - Verify that data shape at each boundary is identical in source and target
   - Verify that side effects happen in the same order

4. **Test suite completion**
   Ensure comprehensive test coverage even if the source had none:
   - Unit tests generated from source code analysis
   - Integration tests from API contract analysis
   - E2E tests from video/screenshot/SME knowledge (if available)
   - Golden-file regression tests (if source system can be run)

5. **Deployment preparation**
   - Production configuration (environment variables, secrets management)
   - Container/orchestration setup
   - CI/CD pipeline (must include coverage validator in CI)
   - Data migration scripts (full and subset)
   - Runbook/documentation

6. **Final product team review**
   - Demo the migrated application against the source
   - Walk through the ADR decision trail
   - Present test coverage and semantic verification results
   - Sign off

### Phase 5 Exit Gate

- [ ] Structural coverage: 100%
- [ ] Semantic verification: all tiers complete
- [ ] Integration pipelines: all verified
- [ ] Test suite: comprehensive (unit + integration + E2E)
- [ ] Deployment: CI/CD pipeline green
- [ ] Product team: signed off

---

## Multi-Session Continuity

Migrations span many sessions. Maintain continuity through:

### Session Start Protocol

1. Read `AGENTS.md` (project rules, phase index, ADR table)
2. Read `memory/MEMORY.md` (session memory index)
3. Read the latest session memory file
4. Determine current phase and next action

### Session End Protocol

1. Write a session memory file (`memory/sessions/YYYY-MM-DD.md`) with:
   - What was completed (with commit refs)
   - What remains (priority ordered)
   - Decisions made (with ADR refs)
   - Blockers discovered
2. Update `memory/MEMORY.md` index
3. Update `AGENTS.md` phase status table

### Consistency Rule

**When any status, decision, or phase changes, update ALL locations that reference it
in the same commit.** Partial updates create contradictions that compound across sessions.

Mandatory update checklist (run mentally before every status change):

- [ ] `AGENTS.md` — phase/ADR status tables
- [ ] `docs/decisions/README.md` — decision index
- [ ] `docs/decisions/NNNN-*.md` — the ADR itself
- [ ] `specs/architecture/00-project-charter.md` — solution space, RTM
- [ ] `specs/architecture/NN-modernization-dimensions.md` — recommendation matrix
- [ ] Session memory — current state for next session

### Feedback Memory

When the user corrects your approach, save the correction as a persistent feedback memory
so you don't repeat the mistake in future sessions:

```
memory/feedback/correction-name.md
---
name: correction-name
description: One-line description
type: feedback
---
Rule: [what to do or not do]
Why: [reason]
How to apply: [when this rule kicks in]
```

---

## Project Directory Structure

Every modernization project follows this layout:

```
project-root/
├── AGENTS.md                     ← Project rules & conventions
├── CLAUDE.md                     ← Points to AGENTS.md
├── constitution.md               ← Governing principles
│
├── specs/
│   ├── architecture/             ← Stable reference specs (read-only after creation)
│   │   ├── 00-project-charter.md
│   │   ├── 01-architecture.md
│   │   ├── ...
│   │   └── NN-semantic-discrepancies.md
│   ├── 001-phase-name/           ← Phase spec/plan/tasks
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   └── ...
│
├── docs/
│   ├── decisions/                ← ADRs (MADR 4.0)
│   │   ├── README.md             ← Decision index + dependency graph
│   │   └── NNNN-verb-noun.md
│   └── reports/                  ← Completed analysis reports
│
├── memory/                       ← Cross-session context
│   ├── MEMORY.md                 ← Index (loaded every session)
│   ├── sessions/                 ← Per-session notes
│   ├── feedback/                 ← Behavioral rules
│   └── archive/                  ← Superseded plans
│
├── rules/                        ← Supplementary verification rules
├── tools/                        ← Coverage validator, graph analysis scripts
├── source-repos/                 ← READ-ONLY source code
└── target-repos/                 ← Migration output (grows over time)
```

**Routing rule**: "Is this work still in progress, or is it a settled record?"

- In progress → `memory/`
- Settled decision → `docs/decisions/`
- Stable spec → `specs/`
- Completed report → `docs/reports/`

---

## Reference Files

For detailed templates and examples, read these files from the `references/` directory:

| File                                   | When to read                                             |
| -------------------------------------- | -------------------------------------------------------- |
| `references/flow-variants.md`          | During Phase 0 when proposing modernization flow variants    |
| `references/adr-template.md`           | When creating any ADR                                    |
| `references/semantic-traps-example.md` | When building the project-specific semantic trap catalog |
