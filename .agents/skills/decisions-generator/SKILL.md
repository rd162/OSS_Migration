---
name: decisions-generator
description: >-
  Phase-2 macro-skill for AI-assisted software modernization.
  Composes `adversarial-thinking` (multi-candidate divergent design with
  attacker/defender stress-testing and pairwise comparison) with
  `deep-research-t1` (T1-grounded option validation) to produce formally
  accepted Architecture Decision Records (ADRs) for every non-trivial
  target-architecture and modernization-strategy choice.
  Runs per-ADR: candidate generation → adversarial stress-test →
  convergence check → pairwise comparison → acceptance + atomic
  cross-reference update. Use when Phase 1 artefacts exist and ADRs must
  be drafted, stress-tested, or accepted — or when the user says "generate
  decisions", "propose ADRs", "run Phase 2", "evaluate options",
  "accept the flow-variant decision", or "stress-test this decision".
version: "1.0"
metadata:
  author: OSS_Migration project
  tags: modernization, phase-2, composition, decisions, ADR, adversarial, divergent-design
  composes: [adversarial-thinking, deep-research-t1]
---

# Decisions Generator — Phase 2 Macro-Skill

A **composition skill** that drives Phase 2 of the AI-Assisted Software
Modernization Architecture (see `docs/ai-assisted-modernization-architecture.md`,
section "Phase 2 — Decisions").

This skill carries no methodology body of its own. It orchestrates
`adversarial-thinking` and `deep-research-t1` in a specific sequence,
against a specific input (Phase-1 source knowledge + open decision space),
to produce a specific output (stress-tested, stakeholder-accepted ADRs
and an atomically-consistent cross-reference web).

---

## Architectural position

```text
Phase 1 (specs-extractor) produced:
  - source architecture specifications (per dimension)
  - requirements document (MGPC + RTM)
  - seeded platform-divergence catalogue
   ↓
Phase 2 — this skill
  ├─ deep-research-t1       (validate option claims against T1 sources)
  └─ adversarial-thinking   (divergent candidates + stress test + winner)
   ↓
Phase 3 (target-specs-generator; consumes accepted ADRs)
```

See §"Skill / Agent Composition" of
`docs/ai-assisted-modernization-architecture.md` for the full pipeline diagram.

---

## When to use

- Phase 1 artefacts exist; no `docs/decisions/*.md` ADRs are accepted yet
- A previously deferred P1 or P2 decision becomes needed by the next
  modernization phase (just-in-time acceptance, triggered from Phase 3 or 4)
- A Phase-4 discovery has re-opened an already-accepted ADR and the
  decision must be re-evaluated with new evidence
- The user says "generate decisions", "propose ADRs", "run Phase 2",
  "evaluate options", "accept the flow-variant decision",
  "stress-test this decision"

## When NOT to use

- The decision is trivial (one obvious choice, no trade-offs) —
  record it as a design note, not an ADR
- P0 decisions have already been accepted and no new ADR is needed —
  proceed directly to `target-specs-generator`
- The artefact under review is a target-code refinement, not a decision —
  use `target-code-refiner` instead

---

## Inputs

| Input                                             | Required? | Used by                             |
| ------------------------------------------------- | --------- | ----------------------------------- |
| `specs/architecture/*` (Phase-1 source specs)     | **Yes**   | adversarial-thinking context        |
| `specs/architecture/00-project-charter.md` (MGPC) | **Yes**   | adversarial-thinking constraints    |
| Platform-divergence catalogue                     | **Yes**   | adversarial-thinking attack surface |
| List of open decisions (P0 / P1 / P2)             | **Yes**   | loop driver                         |
| Prior-art research, vendor proposals              | No        | deep-research-t1 expansion          |
| Stakeholder roster (who accepts each decision)    | **Yes**   | acceptance step                     |

## Outputs

1. **One ADR per non-trivial decision** under `docs/decisions/NNNN-verb-noun.md`,
   MADR 4.0 format, containing: context, decision drivers, considered options
   (at least two, each with trade-off analysis), decision, consequences,
   confirmation criteria.
2. **Decision index with dependency graph** — `docs/decisions/README.md`
   listing every ADR, status, priority, dependencies, deciders.
3. **Atomic cross-reference updates** — every document that references a
   status-changed ADR updated in the same commit (see ∆5 below).

---

## Execution protocol

Runs **once per open decision**, ordered by priority
(P0 before P1 before P2) and by dependency
(an ADR that others depend on is accepted first).

### ∆1 — Select the decision class

Use judgment to choose the
reasoning strategy for this specific decision:

| Decision class                                | Suggested reasoning strategy |
| --------------------------------------------- | ---------------------------- |
| Open-ended architectural choice (framework)   | Divergent ToT + adversarial  |
| Incremental technical choice (ORM driver)     | CoT + pairwise               |
| Regulatory / security-sensitive               | CoK + T1-only + safety gate  |
| Trade-off between non-commensurate properties | Adversarial-thinking (full)  |

For open-ended choices, proceed to ∆2 with full depth.
For narrow technical choices, the `adversarial-thinking` skill's
**Quick** or **Standard** depth is usually enough.

### ∆2 — T1 option validation (deep-research-t1)

Invoke `deep-research-t1` to validate every claim the candidate options
make about maturity, community support, performance, licence, and known
issues. This supplies the evidence base that `adversarial-thinking`
attacks and defends against.

Fan out queries per option when three or more options exist.

### ∆3 — Divergent candidate generation (adversarial-thinking)

Invoke `adversarial-thinking` with:

- **Problem statement** — one-paragraph description of the decision
  under evaluation, cited to the relevant Phase-1 specs
- **Constraints** — MGPC premises + constraints from `00-project-charter.md`,
  plus any previously accepted ADRs this decision depends on
- **Depth** — chosen in ∆1

The skill produces:

- Three to seven divergent candidates (each prioritising a different
  trade-off axis — time-to-market vs technical excellence vs fidelity
  preservation vs cost, etc.)
- Per-candidate adversarial stress-test transcripts (attacker + defender,
  separate sessions, blind critique)
- A pairwise-comparison matrix yielding one recommended candidate and
  one runner-up

### ∆4 — Convergence check

If all candidates converge after adversarial stress-testing
(defending converged to the same structural solution), the decision is
a **low-ambiguity** one — accept the converged form directly.

If candidates remain divergent, the pairwise comparison produced in ∆3
is the decision basis. Document both the winner and the runner-up in the
ADR's "Considered Options" section; document _why_ the winner beat the
runner-up in "Decision Drivers".

### ∆5 — Draft the ADR and update cross-references ATOMICALLY

Draft `docs/decisions/NNNN-verb-noun.md` in MADR 4.0 format. In the same
commit, update every location that references this decision:

- [ ] `AGENTS.md` — Architecture Decisions table (status column)
- [ ] `docs/decisions/README.md` — index + priority + dependency graph
- [ ] `docs/decisions/NNNN-*.md` — the ADR itself
- [ ] `specs/architecture/00-project-charter.md` — solution-space table,
      RTM status, cross-reference table
- [ ] `specs/architecture/10-modernization-dimensions.md` — recommendation
      matrix if the ADR affects flow-variant choice
- [ ] `memory/MEMORY.md` and the current session memory file

**Partial status updates are a build-breaking defect** — this is the
consistency rule from `AGENTS.md`. The macro-skill treats a missed
cross-reference as a ∆5 failure, not a warning.

### ∆6 — Stakeholder acceptance

Decisions are not accepted by the framework — they are accepted by the
named stakeholders identified in the ADR's frontmatter. The macro-skill
produces a decision **proposal**; a human (or a stakeholder proxy with
explicit authority) moves status from `proposed` to `accepted`.

Acceptance modes (per `docs/ai-assisted-modernization-architecture.md` §2.3):

| Mode                | When applicable                                   |
| ------------------- | ------------------------------------------------- |
| Up-front            | P0 decisions, normally accepted in Phase 2 itself |
| Just-in-time        | P1 decision blocking the next modernization phase |
| Parallel with impl. | P2 incremental concerns (logging, i18n, metrics)  |

### ∆7 — Exit gate (per ADR)

- [ ] ADR file present in MADR 4.0 format with ≥ 2 options
- [ ] Adversarial stress-test transcripts retained in
      `docs/decisions/transcripts/` or linked from the ADR
- [ ] Deep-research evidence citations in the ADR (source + tier + date)
- [ ] All cross-references updated atomically (∆5 checklist)
- [ ] Named stakeholders recorded; status is either `proposed` (awaiting
      human acceptance) or `accepted` (human accepted)
- [ ] Forward-link placeholder if this ADR might be superseded later

Phase-2 exit gate (aggregate): every P0 ADR accepted, every P1 ADR
either accepted or explicitly deferred to just-in-time with rationale.

---

## Termination

| Signal   | Condition                                     | Action                               |
| -------- | --------------------------------------------- | ------------------------------------ |
| COMPLETE | All P0 ADRs accepted, P1 deferred-or-accepted | Proceed to `target-specs-generator`  |
| ITERATE  | New ADR surfaces mid-phase                    | Loop back to ∆1 for the new decision |
| DEGRADED | Adversarial-thinking skill unavailable        | Use CoT + manual pairwise; disclaim  |
| BLOCKED  | Stakeholder unavailable                       | Mark ADR `proposed`; hand off        |
| REOPENED | Phase-4 discovery invalidates an accepted ADR | Loop back to ∆2 with new evidence;   |
|          |                                               | supersede old ADR; forward-link      |

---

## Composition guarantee

This skill contains no new methodology. Its entire behaviour is the
sequence of calls into `adversarial-thinking` and `deep-research-t1`.
Updating any of those skills automatically
updates this skill's effective behaviour.

All composed skills conform to the Agent Skills open standard
(Dec 18 2025), so this macro-skill is likewise portable across Claude
Code, Codex CLI, Amp, Devin, and any runtime that supports filesystem
skill discovery.

The Claude-specific agent wrapper `.claude/agents/decisions-generator.md`
provides tool-whitelist enforcement, model pinning, and context
isolation when running this skill inside an isolated subagent — but the
playbook (this file) is the single source of truth.

---

## Anti-patterns

```text
✗ Generate a single "best" candidate and attack it
✓ Generate ≥ 3 divergent candidates, attack each independently

✗ Critic and author share the same session (self-play)
✓ Adversarial-thinking enforces separate critique/author sessions

✗ Accept an ADR without updating the RTM and the charter
✓ ∆5 atomic cross-reference update is mandatory

✗ Skip T1 research because the option "looks obvious"
✓ Every claim in every option cited to a tier-annotated source

✗ Record only the winner; discard runner-up
✓ Runner-up preserved in ADR for audit and re-openability

✗ Inline the full adversarial-thinking playbook in this file
✓ Keep this file a thin composition; playbook lives in its skill

✗ Treat stakeholder acceptance as a rubber stamp
✓ Named deciders + consulted parties; acceptance is governance, not UI
```

---

## Relationship to other phase skills

- **Upstream** — `specs-extractor` produces the Phase-1 input bundle this
  skill consumes.
- **Downstream** — `target-specs-generator` reads the accepted ADRs and
  binds each modernization-phase spec to the decisions it depends on.
- **Loop-back** — `target-code-refiner` (Phase 4) may surface evidence
  that invalidates an accepted ADR; this skill is re-entered in that
  case, and the old ADR is superseded with a forward link.

---

## Provenance

- Source system: AI-Assisted Software Modernization Architecture,
  `docs/ai-assisted-modernization-architecture.md`, Phase 2.
- Composes: `adversarial-thinking` (v8.0), `deep-research-t1` (v2.2).
- Inferred pattern source: historical session logs in
  `memory/archive/full-logs/` where each ADR was produced by interleaving
  deep-research evidence gathering with multi-candidate divergent
  design and adversarial refinement — this skill formalises that
  composition and binds it to the ADR consistency rule.
