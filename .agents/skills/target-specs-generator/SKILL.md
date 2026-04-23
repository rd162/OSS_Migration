---
name: target-specs-generator
description: >-
  Phase-3 macro-skill for AI-assisted software modernization.
  Composes iterative modernization-phase spec generation (spec / plan / tasks
  triplet per unblocked phase, driven by the primary-dimension flow
  variant accepted in Phase 2) with `adversarial-self-refine`
  (isolated critic/author loop) to produce target specifications that
  are stress-tested per spec before being handed to Phase 4.
  Loops back to `decisions-generator` when a deferred decision becomes
  needed by the next modernization phase. Use when accepted ADRs exist but
  `specs/NNN-*/spec.md` is missing or incomplete — or when the user says
  "generate target specs", "produce phase spec", "run Phase 3",
  "draft the walking skeleton", "refine the modernization-phase spec".
version: "1.0"
metadata:
  author: OSS_Migration project
  tags: modernization, phase-3, composition, specs, target-architecture, adversarial-refine, iterative
  composes: [adversarial-self-refine, deep-research-t1, requirements-extractor]
---

# Target Specs Generator — Phase 3 Macro-Skill

A **composition skill** that drives Phase 3 of the AI-Assisted Software
Modernization Architecture (see `docs/ai-assisted-modernization-architecture.md`,
section "Phase 3 — Target Specifications").

This skill contains no standalone methodology. It iterates over
modernization phases in primary-dimension order, generates each phase's
three-artifact spec set, and runs every spec through
`adversarial-self-refine` (isolated CRITIC + AUTHOR agents) before
declaring the spec stable. It loops back to `decisions-generator` when a
deferred decision becomes needed.

---

## Architectural position

```text
Phase 1 (specs-extractor)  →  source knowledge
Phase 2 (decisions-generator) → accepted ADRs
   ↓
Phase 3 — this skill
  ├─ iterative spec generation (spec / plan / tasks per phase)
  ├─ adversarial-self-refine    (critic/author loop per spec)
  ├─ requirements-extractor     (re-derive premises when a phase reshapes scope)
  └─ deep-research-t1           (target-side best-practice grounding)
   ↓  (loop-back to Phase 2 if deferred decision needed)
Phase 4 (target-code-refiner; consumes spec / plan / tasks)
```

See §"Skill / Agent Composition" of
`docs/ai-assisted-modernization-architecture.md` for the full pipeline diagram.

---

## When to use

- Accepted P0 ADRs exist (flow variant, target stack, database engine)
- `specs/NNN-phase-name/` directories are missing or incomplete
- A Phase-4 run has completed and the next modernization phase needs its
  spec / plan / tasks triplet generated
- The user says "generate target specs", "produce phase spec",
  "run Phase 3", "draft the walking skeleton",
  "refine the modernization-phase spec"

## When NOT to use

- Phase 1 or Phase 2 artefacts are missing — go back to those phases
- An already-generated spec is **passing** its exit gate and running
  cleanly in Phase 4 — do not re-refine specs without trigger evidence
- The ask is target-code refinement rather than spec refinement —
  use `target-code-refiner` instead

---

## Inputs

| Input                                                 | Required? | Used by                                 |
| ----------------------------------------------------- | --------- | --------------------------------------- |
| `specs/architecture/*` (Phase-1 source specs)         | **Yes**   | spec generation context                 |
| `specs/architecture/00-project-charter.md` (MGPC)     | **Yes**   | constraint source for every phase spec  |
| Accepted ADRs in `docs/decisions/*.md`                | **Yes**   | constraint source + traceability link   |
| Flow-variant decision (primary driving dimension)     | **Yes**   | phase-ordering driver                   |
| Platform-divergence catalogue                         | **Yes**   | exit-gate semantic-verification binding |
| Already-generated phase specs (if any)                | No        | dependency-ordering input               |

## Outputs (per modernization phase)

Three files per phase under `specs/NNN-phase-name/`:

1. **`spec.md`** — user stories, functional requirements, acceptance
   criteria, explicit scope and anti-scope, success criteria.
   Answers "what should this part of the target look like?"
2. **`plan.md`** — technical context, constitution check, referenced
   ADRs, modernization batches in dependency order, entry and exit gates,
   risk assessment. Answers "how do we get there?"
3. **`tasks.md`** — actionable checkboxed tasks with `[P]` parallel
   markers and cross-references to the source elements each task covers.
   Answers "the work to do."

Across all phases:

- **Spec dependency graph** recorded in `AGENTS.md` phase index
- **Every spec cites** the ADRs it depends on (explicit bind)
- **Every spec carries** an adversarial-refine transcript pointer
  (or an inline log section) proving the refine loop ran to convergence

---

## Execution protocol

Runs **once per unblocked modernization phase**, ordered by the flow variant
accepted in Phase 2. The first invocation typically produces the
walking-skeleton phase; subsequent invocations produce dependent phases
in dependency-level order.

### ∆1 — Determine the next unblocked phase

Read the primary driving dimension from the flow-variant ADR, combined
with the dependency graph of already-generated phases. Select the next
phase whose required ADRs are all `accepted`.

If the next phase has dependencies on ADRs that are still `proposed` or
deferred, **loop back** to `decisions-generator` to accept them just in
time. Do not generate a spec over an unaccepted decision.

### ∆2 — Target-side grounding (deep-research-t1, optional)

For phases that introduce a new target-side technology choice not yet
researched (e.g., the first phase to use a specific ORM feature,
background-worker pattern, or deployment primitive), invoke
`deep-research-t1` for best-practice patterns and known pitfalls in the
target technology. Seed `specs/architecture/NN-semantic-discrepancies.md`
with any new divergences found.

Skip this step when the phase reuses technology patterns already
researched in Phase 1 or earlier phases.

### ∆3 — Re-derive premises if scope changed (requirements-extractor, optional)

If this phase reshapes the user-visible scope (e.g., a phase that
collapses two source features into one target feature, or promotes a
deferred feature into the walking skeleton), invoke
`requirements-extractor` with the updated scope so that the Phase-3
spec's acceptance criteria remain anchored to a current MGPC view.

Skip when the phase preserves scope.

### ∆4 — Draft the three-artifact spec set

Draft `specs/NNN-phase-name/{spec,plan,tasks}.md` in that order.

**For `spec.md`:**

- User stories and functional requirements sourced from the RTM
- Acceptance criteria phrased as machine-checkable predicates where
  possible (coverage ≥ X, semantic verification clean, tests green)
- Explicit scope and anti-scope (what this phase **does not** do)
- Cross-references to the Phase-1 dimension specs it covers

**For `plan.md`:**

- Technical context — the target architecture slice this phase produces
- Constitution check — confirm the plan respects `constitution.md`
- Referenced ADRs — every accepted decision the plan relies on, cited
- Migration batches in dependency order, each batch small enough to fit
  one working session of Phase 4
- Entry gate (ADRs required) and exit gate (coverage threshold, tests,
  semantic verification result) — machine-checkable
- Risk assessment — what could go wrong, with fallback

**For `tasks.md`:**

- Checkboxed tasks derived from the batches in `plan.md`
- `[P]` marker on tasks that can be done in parallel within a batch
- Each task cites the source element(s) it covers by relative path +
  line number (never duplicates source)
- Walking-skeleton phase tasks sized to produce a runnable target
  within days, not weeks

### ∆5 — Adversarial refine the spec (adversarial-self-refine)

Invoke `adversarial-self-refine` **per file** in the triplet, in this
order: `spec.md`, then `plan.md`, then `tasks.md`.

The skill runs isolated CRITIC and AUTHOR sessions:

- **CRITIC** sees only the draft file + the phase's ADR bundle + the
  MGPC, and asserts flaws ("this acceptance criterion is not
  machine-checkable", "this batch has an implicit dependency on a
  deferred decision", "this task has no source reference").
- **AUTHOR** sees the critique without authoring context and either
  accepts and revises, or defends. Defence = convergence signal.

Continue until convergence or until the `adversarial-self-refine`
skill's emergent termination detector fires.

Retain the refine transcript (or a summary with round count + key
critiques + final defence) alongside the spec. The presence of a
convergence signal is an exit-gate requirement.

### ∆6 — Loop-back check

After the triplet is refined, re-check the requirements-traceability
matrix in `00-project-charter.md`:

- If every in-scope requirement is now covered by a generated phase
  spec, Phase 3 is structurally complete → proceed to Phase 4 for the
  first unblocked phase.
- Otherwise → loop back to ∆1 for the next unblocked phase.

### ∆7 — Exit gate (per phase)

- [ ] `spec.md`, `plan.md`, `tasks.md` all present and non-empty
- [ ] Every acceptance criterion in `spec.md` is machine-checkable or
      explicitly flagged as human-judgement with named reviewer
- [ ] `plan.md` cites the specific ADRs it depends on (no blanket
      "per AGENTS.md" references)
- [ ] Every task in `tasks.md` carries a source cross-reference or
      is marked as a target-only task (schema migrations, CI, infra scaffolding)
- [ ] Adversarial-self-refine transcript retained; convergence signal
      observed for each of the three files
- [ ] Phase index in `AGENTS.md` updated with phase name + status
- [ ] Session memory updated with what was produced and what is next

Phase-3 exit gate (aggregate): every in-scope requirement in the RTM
covered by at least one generated phase spec; the set of phase specs
forms a complete, dependency-ordered modernization plan.

---

## Termination

| Signal      | Condition                                                | Action                                         |
| ----------- | -------------------------------------------------------- | ---------------------------------------------- |
| COMPLETE    | RTM coverage check passes; all phase specs refined       | Proceed to `target-code-refiner` (Phase 4)     |
| ITERATE     | More unblocked phases remain                             | Loop back to ∆1 for next phase                 |
| BLOCKED-ADR | Next phase depends on a deferred ADR                     | Loop back to `decisions-generator`, then ∆1    |
| DEGRADED    | `adversarial-self-refine` unavailable                    | Single-thread self-critique; mark DEGRADED     |
| REOPENED    | Phase-4 evidence invalidates a generated spec            | Loop back to ∆4 for the affected phase only    |

---

## Composition guarantee

This skill contains no methodology beyond the sequencing of sub-skill
calls and the per-phase file synthesis step. Updating
`adversarial-self-refine`, `deep-research-t1`, or `requirements-extractor`
automatically updates this skill's effective behaviour.

The composed skills conform to the Agent Skills open standard
(Dec 18 2025). This macro-skill is therefore portable across Claude
Code, Codex CLI, Amp, Devin, and any runtime that supports filesystem
skill discovery. The Claude-specific agent wrapper at
`.claude/agents/target-specs-generator.md` adds runtime concerns
(tool whitelist, model pin, context isolation) without duplicating
this playbook.

---

## Anti-patterns

```text
✗ Generate all phase specs up front, then refine them all later
✓ One phase at a time; refine each before generating the next

✗ Treat `plan.md` as an implementation pre-draft
✓ Plan is a contract over ADRs and batches; implementation happens in Phase 4

✗ Skip adversarial-refine for "simple" phases (walking skeleton)
✓ The walking skeleton benefits most from refinement — cheap to fix now

✗ Generate a spec that depends on a `proposed` ADR
✓ Loop back to `decisions-generator` first; never build on proposed decisions

✗ Include source code listings in phase specs
✓ Cross-reference source by relative path + line number only

✗ Let acceptance criteria be vague ("tests pass", "it works")
✓ Machine-checkable predicates: coverage threshold, semantic clean,
  specific test suites green

✗ Inline the full adversarial-self-refine playbook in this file
✓ Keep this file a thin composition; playbook lives in its skill

✗ Run CRITIC and AUTHOR in the same context (self-play)
✓ `adversarial-self-refine` enforces session isolation — respect it
```

---

## Relationship to other phase skills

- **Upstream** — `specs-extractor` produced the Phase-1 source knowledge
  base; `decisions-generator` produced the ADR bundle this skill binds
  every phase spec to.
- **Downstream** — `target-code-refiner` reads the generated
  spec / plan / tasks triplet and executes it batch by batch in Phase 4.
- **Loop-back — upstream** — when a deferred ADR is needed, invoke
  `decisions-generator` just-in-time before continuing.
- **Loop-back — downstream** — when Phase-4 evidence invalidates a
  generated spec (late-breaking source discovery, newly-accepted
  decision, semantic-verification failure), re-enter this skill at ∆4
  for the affected phase only and re-run ∆5 on the revised file.

---

## Provenance

- Source system: AI-Assisted Software Modernization Architecture,
  `docs/ai-assisted-modernization-architecture.md`, Phase 3.
- Composes: `adversarial-self-refine` (v3.0), `deep-research-t1` (v2.2),
  `requirements-extractor` (v3.0).
- Inferred pattern source: historical session logs in
  `memory/archive/full-logs/` where each modernization-phase spec was
  produced by iterating over the phase index, drafting the triplet,
  and running a critic/author refinement pass before handing to
  implementation — this skill formalises that composition and binds it
  to the RTM coverage exit gate.
