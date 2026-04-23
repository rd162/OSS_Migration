---
name: target-code-refiner
description: >-
  Phase-4 macro-skill for AI-assisted software modernization.
  Composes target-code generation with traceability, structural coverage
  validation, gap resolution, and `adversarial-self-refine` (isolated
  critic/author loop) applied to every non-trivial target artifact
  produced in a modernization phase. Drives the per-batch execution loop
  defined in `ai-modernization` Phase 4, wiring in adversarial refinement
  after each batch of target code is written and before the next
  coverage pass. Loops back to `decisions-generator` when a Phase-4
  discovery invalidates an accepted ADR, and loops back to
  `target-specs-generator` when the phase spec itself proves wrong.
  Use when `specs/NNN-*/tasks.md` exists and implementation must produce
  verified target artifacts — or when the user says "execute the phase",
  "run Phase 4", "implement the walking skeleton", "refine the target
  code", "close the coverage gap", "continue the modernization".
version: "1.0"
metadata:
  author: OSS_Migration project
  tags: modernization, phase-4, composition, execution, target-code, coverage, adversarial-refine
  composes: [adversarial-self-refine, ai-modernization, deep-research-t1]
---

# Target Code Refiner — Phase 4 Macro-Skill

A **composition skill** that drives Phase 4 of the AI-Assisted Software
Modernization Architecture (see `docs/ai-assisted-modernization-architecture.md`,
section "Phase 4 — Modernization Execution").

This skill carries no standalone execution methodology. It wraps the
per-batch loop defined in `ai-modernization` (Phase 4) with
`adversarial-self-refine` applied to every non-trivial target artifact
before it is handed to the coverage validator, and with explicit
loop-back edges to `decisions-generator` and `target-specs-generator`
when Phase-4 evidence invalidates upstream artifacts.

---

## Architectural position

```text
Phase 3 (target-specs-generator) → spec / plan / tasks per phase
   ↓
Phase 4 — this skill (runs once per modernization phase, one session per run)
  ├─ ai-modernization                 (per-batch execution loop, coverage validator,
  │                                semantic trap catalogue, traceability rules)
  ├─ adversarial-self-refine      (critic/author loop on each target artifact)
  └─ deep-research-t1             (just-in-time target-pattern lookup)
   ↓  (loop-back to Phase 2 or Phase 3 as evidence dictates)
Phase 5 (hybrid deployment; consumes verified target artifacts)
```

See §"Skill / Agent Composition" of
`docs/ai-assisted-modernization-architecture.md` for the full pipeline diagram.

---

## When to use

- A Phase-3 spec set (`specs/NNN-*/spec.md` + `plan.md` + `tasks.md`)
  exists and is current, with its adversarial-refine convergence signal
  observed
- All ADRs the phase depends on are `accepted`
- Target-repository workspace exists (even if empty)
- The user says "execute the phase", "run Phase 4", "implement the
  walking skeleton", "refine the target code", "close the coverage gap",
  "continue the modernization", "what's next" (when a phase spec is pending
  execution)

## When NOT to use

- Phase-3 spec set is missing or incomplete → use `target-specs-generator`
- An ADR the phase depends on is still `proposed` → use
  `decisions-generator` to accept it just in time
- The ask is deployment / cutover rather than implementation → proceed
  to Phase 5
- The entire source was not yet analysed → use `specs-extractor` first

---

## Inputs

| Input                                                      | Required? | Used by                               |
| ---------------------------------------------------------- | --------- | ------------------------------------- |
| `specs/NNN-phase-name/spec.md` + `plan.md` + `tasks.md`    | **Yes**   | loop driver                           |
| `specs/architecture/*` (Phase-1 source specs)              | **Yes**   | traceability + coverage input         |
| Accepted ADRs in `docs/decisions/*.md`                     | **Yes**   | constraint enforcement + traceability |
| Platform-divergence catalogue                              | **Yes**   | semantic-verification checklist       |
| Coverage validator (`tools/` or ai-modernization-provided) | **Yes**   | structural coverage per batch         |
| Source repository (read-only)                              | **Yes**   | traceability resolution               |

## Outputs (per modernization phase)

1. **Target artifacts** emitted into `target-repos/*` — target code,
   schemas, configs, CI/CD fragments, deployment manifests. Every
   meaningful element carries a traceability comment binding it to the
   source element(s) that shaped it and the specs / decisions that
   justified it.
2. **Coverage report** — programmatic per-dimension status
   (covered / eliminated / unmatched) for every in-scope source element.
3. **Semantic verification report** — checklist-driven audit against
   the platform-divergence catalogue for every high-risk target element.
4. **Adversarial-refine transcripts** — retained for every non-trivial
   target artifact that went through the critic/author loop.
5. **Platform-divergence catalogue updates** — new divergences surfaced
   during the phase appended to `specs/architecture/NN-semantic-discrepancies.md`.
6. **Phase-exit session memory note** — written to `memory/sessions/YYYY-MM-DD.md`;
   ready for the next session or phase.

---

## Execution protocol

Runs **once per modernization phase**, in a fresh working session. The
per-phase loop processes batches defined in the phase's `plan.md`.
Within a batch, the per-batch loop produces target artifacts,
adversarial-refines them, then validates coverage and semantics.

### ∆1 — Session bootstrap

- Read `AGENTS.md` to confirm phase index and current status.
- Read `specs/NNN-phase-name/spec.md` + `plan.md` + `tasks.md`.
- Read every ADR cited in `plan.md`.
- Read the platform-divergence catalogue.
- If a prior session note exists for this phase (resumed session),
  read `memory/sessions/` to restore the execution cursor.
- Verify the coverage validator is available and runs cleanly against
  the current target tree (empty tree is fine for the first phase).

Fail fast if any of the above is missing; do not invent a fallback spec.

### ∆2 — Per-batch execution loop

For each batch in `plan.md`, in dependency order:

#### ∆2a — Produce target artifacts with traceability

Follow the `ai-modernization` Phase-4 implementation rules (source
traceability comments, match levels, zero-skips testing policy).
Target artifacts include code, schemas, migrations, configs, tests.

Keep each produced artifact small enough to fit a single refine cycle;
large files should be decomposed before being refined.

#### ∆2b — Adversarial-refine the artifact (adversarial-self-refine)

For every non-trivial target artifact produced in ∆2a, invoke
`adversarial-self-refine` in isolated sessions:

- **CRITIC** sees the target artifact + the relevant source element(s) +
  the platform-divergence catalogue + the phase's ADR bundle. It
  asserts specific flaws — behavioural divergence from source, missing
  traceability, missing edge-case handling, violated decision, silent
  fallthrough, type-coercion trap, transaction-boundary mismatch.
- **AUTHOR** sees the critique without authoring context and either
  revises the artifact or defends it. Defence = convergence signal.

Continue until convergence or until the skill's emergent termination
detector fires. Retain the transcript alongside the artifact
(or a summary with round count + key critiques + final defence).

Small, purely-structural artifacts (boilerplate, trivial wiring) may
skip refinement — document the skip reason in the batch log.

#### ∆2c — Structural coverage analysis (per dimension)

Run the coverage validator across every dimension the batch touches
(call graph, entity graph, event flow, hook sites, etc. — as produced
in Phase 1). Produce a per-dimension gap report.

#### ∆2d — Gap resolution

For each unmatched in-scope element in the gap report, decide:

- **Generate new** — write a new target element with traceability to
  the unmatched source element; run ∆2b on the new element.
- **Enhance existing** — extend an already-written target element to
  cover the unmatched source element; re-run ∆2b on the enhanced
  element (adversarial refine against the larger responsibility set).
- **Eliminate** — document that the source element has no target
  equivalent (deprecated feature, language-specific infrastructure,
  superseded by an accepted ADR), with a forward link to the
  justification.

Repeat ∆2b-∆2d until the batch's gap report shows zero unmatched
in-scope elements.

#### ∆2e — Semantic verification on high-risk elements

For any Tier-1 element in the batch (complex SQL, multiple branches,
cross-cutting callers, session / auth / crypto touchpoints), perform
line-by-line source↔target comparison against the platform-divergence
catalogue. Append any newly discovered divergence to
`specs/architecture/NN-semantic-discrepancies.md`.

#### ∆2f — Tests and static analysis

Run the test suite (unit + integration + end-to-end at the current
scope) and static-analysis / lint / type-check as prescribed in
`plan.md`. Zero-skips policy — never skip a test; fix the underlying
issue instead.

If any step fails, narrow scope and return to ∆2a for the failing
slice.

### ∆3 — Loop-back decisions

Phase-4 evidence may invalidate upstream artifacts. The macro-skill
treats the following signals as explicit loop-back triggers:

| Signal                                                      | Loop-back target         | What to do                                        |
| ----------------------------------------------------------- | ------------------------ | ------------------------------------------------- |
| Semantic-verification failure rooted in an ADR's assumption | `decisions-generator`    | Supersede the ADR; forward-link old → new         |
| Coverage gap that reveals the phase spec is wrong           | `target-specs-generator` | Revise spec / plan / tasks; re-run ∆5 (refine)    |
| New divergence class large enough to be a phase of its own  | `target-specs-generator` | Generate a new phase spec; re-sequence downstream |
| Target-side pattern pitfall not yet researched              | `deep-research-t1`       | T1 research pass; then resume ∆2a                 |

Loop-backs are first-class. They are not "exceptions" — they are the
mechanism by which Phase 4 feeds evidence back into Phases 2 and 3.

### ∆4 — Phase-exit checks

Once every batch in `plan.md` has cleared ∆2a-∆2f and no loop-back
remains outstanding:

- Run the full coverage validator across all in-scope elements for the
  phase. Every source element must be `covered` or `eliminated` with a
  documented reason. Unmatched count must be zero.
- Run semantic verification across all touched high-risk elements
  (aggregate of batch ∆2e results).
- Run the full test suite at the phase's scope (not just the current
  batch). All tests must be green; zero skips.
- Confirm every ADR cited in `plan.md` remains `accepted` (not
  superseded mid-phase without a replacement).
- Append new divergences from the phase to the catalogue.

### ∆5 — Session handoff

Write the session memory note directly to `memory/sessions/YYYY-MM-DD.md`
with: batches completed (with commit refs) and remaining, coverage report
summary, semantic-verification summary, loop-backs executed or pending, and
next-session entry point. Then update `AGENTS.md` phase status table
atomically (consistency rule).

### ∆6 — Exit gate (per phase)

- [ ] Every task in `tasks.md` checked off
- [ ] Every batch has cleared ∆2a-∆2f
- [ ] Coverage validator: 0 unmatched in-scope elements per dimension
- [ ] Semantic verification: all Tier-1 elements verified; catalogue
      updated
- [ ] Tests green; zero skips
- [ ] All status changes propagated (consistency rule — see `AGENTS.md`)
- [ ] Handoff note written; `AGENTS.md` phase index reflects reality
- [ ] Every non-trivial target artifact has an adversarial-refine
      transcript or a documented skip reason

---

## Termination

| Signal       | Condition                                | Action                                                      |
| ------------ | ---------------------------------------- | ----------------------------------------------------------- |
| COMPLETE     | ∆6 exit gate green                       | Proceed to next phase (loop to ∆1 of next phase) or Phase 5 |
| ITERATE      | More batches remain in the current phase | Loop back to ∆2                                             |
| BLOCKED-ADR  | Evidence invalidates an accepted ADR     | Loop back to `decisions-generator`                          |
| BLOCKED-SPEC | Evidence invalidates the phase spec      | Loop back to `target-specs-generator`                       |
| DEGRADED     | `adversarial-self-refine` unavailable    | Single-thread self-critique; mark DEGRADED                  |
| SESSION-END  | Context budget exhausted mid-batch       | Write session note to memory/sessions/; resume next run     |
| ALL-PHASES   | Every modernization phase passes ∆6      | Proceed to Phase 5 (hybrid deployment)                      |

---

## Composition guarantee

This skill contains no execution methodology of its own beyond the
sequencing of sub-skill calls and the loop-back edges. Every detail of
per-batch execution, traceability formatting, coverage validation, and
semantic trap checking lives in `ai-modernization`; every detail of the
critic/author loop lives in `adversarial-self-refine`. Updating either
of those skills automatically updates this skill's behaviour.

All composed skills conform to the Agent Skills open standard
(Dec 18 2025). This macro-skill is therefore portable across Claude
Code, Codex CLI, Amp, Devin, and any runtime that supports filesystem
skill discovery. The Claude-specific agent wrapper at
`.claude/agents/target-code-refiner.md` adds runtime concerns (tool
whitelist, model pin, context isolation, worktree isolation, per-agent
memory) without duplicating this playbook.

---

## Anti-patterns

```text
✗ Generate a whole batch of target code and refine it at the end
✓ Refine each non-trivial artifact before it reaches the coverage validator

✗ Treat coverage gaps as "to-do later"
✓ Gaps are resolved inside the same batch that surfaced them

✗ Skip adversarial-refine for "translated" code
✓ One-to-one translations are where semantic-divergence traps hide

✗ Accept a test skip because the function is missing
✓ Implement the function; write the test; zero-skips policy

✗ Let an ADR be quietly violated when the target code diverges
✓ Either revise the code or formally supersede the ADR

✗ Execute a phase over a spec that was never adversarially refined
✓ `target-specs-generator` must have observed convergence first

✗ Run coverage at the end of the phase only
✓ Coverage runs inside every batch; gaps are caught while context is hot

✗ Discard adversarial-refine transcripts after convergence
✓ Retain — they are audit evidence that refinement actually happened

✗ Write the handoff note only at end-of-session when context is already lost
✓ Handoff note is produced at ∆5 for every phase exit, not session exit

✗ Inline the full ai-modernization or adversarial-self-refine playbooks here
✓ Keep this file a thin composition; playbooks live in their skills
```

---

## Relationship to other phase skills

- **Upstream** — `target-specs-generator` produced the spec / plan /
  tasks triplet this skill executes. `decisions-generator` produced the
  ADR bundle the plan binds to.
- **Downstream** — Phase 5 (hybrid deployment) consumes verified target
  artifacts and cutover plans emitted by this skill.
- **Loop-back — `decisions-generator`** — Phase-4 evidence can reopen an
  accepted ADR. Supersede, do not silently contradict.
- **Loop-back — `target-specs-generator`** — Phase-4 evidence can
  reopen a phase spec. Revise + re-refine; do not patch around.
- **Internal re-entry** — a failing batch loops back to ∆2a for the
  failing slice only; healthy batches are not re-run.

---

## Provenance

- Source system: AI-Assisted Software Modernization Architecture,
  `docs/ai-assisted-modernization-architecture.md`, Phase 4.
- Composes: `ai-modernization` (Phase-4 per-batch loop, traceability rules,
  coverage validator, semantic trap catalogue), `adversarial-self-refine`
  (v3.0), `deep-research-t1` (v2.2).
- Inferred pattern source: historical session logs in
  `memory/archive/full-logs/` where Phase 4 was executed manually by
  interleaving code production, critic/author refinement, coverage
  validation, and loop-back decisions back into Phase 2 / Phase 3 —
  this skill formalises that composition and makes the loop-back edges
  explicit rather than implicit.
