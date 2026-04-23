---
name: specs-extractor
description: >-
  Phase-1 macro-skill for AI-assisted software modernization.
  Composes `deep-research-t1` (external technology knowledge grounding)
  with `requirements-extractor` (bottom-up Chain-of-Knowledge expansion
  followed by top-down Mission/Goals/Premises/Constraints inference)
  to produce the three Phase-1 artifact families from a source repository:
  source architecture specifications (one per discovered dimension),
  a requirements document (MGPC + Requirements Traceability Matrix),
  and the initial platform-divergence catalogue.
  Use when starting a modernization project from a source repository that has
  no specs, no dimension analysis, and no ADRs — or when the user says
  "extract specs", "analyse the source", "build architecture specs",
  "produce the source knowledge base", or "run Phase 1".
version: "1.0"
metadata:
  author: OSS_Migration project
  tags: modernization, phase-1, composition, specs, requirements, dimensions, source-analysis
  composes: [deep-research-t1, requirements-extractor, knowledge-management]
---

# Specs Extractor — Phase 1 Macro-Skill

A **composition skill** that drives Phase 1 of the AI-Assisted Software
Modernization Architecture (see `docs/ai-assisted-modernization-architecture.md`,
section "Phase 1 — Knowledge Extraction").

This skill does not carry its own methodology body.
Instead it orchestrates two lower-level skills in a specific sequence,
against a specific input (source repository + domain documents),
to produce a specific output (source architecture specifications,
requirements document, and initial platform-divergence catalogue).

---

## Architectural position

```text
Phase 0 (source repo present)
   ↓
Phase 1 — this skill
   ├─ deep-research-t1      (ground external knowledge)
   ├─ requirements-extractor (MGPC + RTM from source + research)
   └─ knowledge-management   (saturate across large corpus)
   ↓
Phase 2 (decisions; see `decisions-generator` skill)
```

See §"Skill / Agent Composition" of `docs/ai-assisted-modernization-architecture.md`
for the full pipeline diagram.

---

## When to use

- Source repository present; no `specs/architecture/` directory yet
- User says "extract specs", "analyse the source", "run Phase 1",
  "produce the source knowledge base"
- Migration project bootstrap — the input is code + docs, the output
  is a structured source-knowledge model that every later phase consumes

## When NOT to use

- `specs/architecture/` already exists and is current — use
  `ai-modernization` directly and pick up from Phase 2 or later
- No source repository — this skill is source-driven
- Single-file ports or <5 kLOC throwaway migrations — over-kill

---

## Inputs

| Input                                    | Required? | Used by                       |
| ---------------------------------------- | --------- | ----------------------------- |
| Source repository (read-only)            | **Yes**   | requirements-extractor + both |
| Domain documentation                     | No        | requirements-extractor        |
| Production configuration samples         | No        | requirements-extractor        |
| Operational logs                         | No        | requirements-extractor        |
| External contracts the source implements | No        | deep-research-t1 queries      |

## Outputs (three artifact families — Phase 1)

1. **Source architecture specifications** — one per dimension,
   under `specs/architecture/NN-dimension-name.md`.
   Typical set: `01-architecture`, `02-database`, `03-api-routing`,
   `04-frontend`, `05-plugin-system`, `06-security`,
   `07-caching-performance`, `08-deployment`, `09-source-index`,
   `10-modernization-dimensions`, `11-business-rules`,
   `12-testing-strategy`, `13-decomposition-map`.
2. **Requirements document** — `specs/architecture/00-project-charter.md`
   containing Mission, Goals, Premises, Constraints, and a
   Requirements Traceability Matrix.
3. **Initial platform-divergence catalogue** —
   `specs/architecture/NN-semantic-discrepancies.md` seeded with
   divergences surfaced during research (grows in later phases).

---

## Execution protocol

### ∆1 — Pre-flight

- Verify source repository is present and read-only.
- Verify the three composing skills are installed locally
  (`.agents/skills/deep-research-t1`, `.agents/skills/requirements-extractor`,
  `.agents/skills/knowledge-management`).

### ∆2 — External knowledge grounding (deep-research-t1)

Invoke `deep-research-t1` with three research fan-outs:

1. **Source-platform patterns** — architectural layers, design patterns,
   database patterns, messaging patterns, session management, auth,
   deployment conventions typical of the source technology.
2. **Target-platform best-practices** — the equivalent patterns in the
   target technology, surfacing natural mappings and forced adaptations.
3. **Migration pitfalls for this specific source→target pair** —
   known traps, semantic divergences, data-type mismatches, control-flow
   differences. Results seed the platform-divergence catalogue (output 3).

Use sub-agent fan-out where possible — one research session per topic,
with T1 sources preferred. See `deep-research-t1/SKILL.md` Δ1-Δ7.

### ∆3 — Source-repository saturation (knowledge-management)

For large source repositories (>10 kLOC), invoke `knowledge-management`
to perform Chain-of-Knowledge saturation across the corpus:

- Build the initial file inventory (`09-source-index.md`).
- Parse AST to discover call-graph edges → `10-modernization-dimensions.md`.
- Detect entity / schema references → input for `02-database.md`.
- Detect plugin / hook sites → input for `05-plugin-system.md`.
- Detect security surface (auth, crypto, session) → input for `06-security.md`.

For small source repositories the agent can saturate directly via
`Read` + `Grep` without invoking `knowledge-management` formally.

### ∆4 — Requirements derivation (requirements-extractor)

Invoke `requirements-extractor` with the following input bundle:

- The source repository inventory produced in ∆3
- The research findings from ∆2
- Any domain documents, SME transcripts, or production configs

The skill runs its two phases:

- **Bottom-up Chain-of-Knowledge expansion** — triples derived from source
  code and docs; implicit constraints surfaced
- **Top-down intent inference** — Mission / Goals / Premises / Constraints
  synthesised from the expanded triples + user-provided modernization brief

Output → `specs/architecture/00-project-charter.md`
(requirements document, including the Requirements Traceability Matrix).

### ∆5 — Dimension specifications

For every dimension discovered in ∆3, produce a specification file that:

- Names the dimension and its source evidence
- Describes the graph / structure / set it defines
- Cross-references source files by relative path + line number
  (never duplicates source code)
- States the modernization impact — phase ordering? coverage scope?
  semantic-verification contract?

This step is performed by the calling agent using the evidence already
gathered; it is a synthesis step, not a new skill invocation.

### ∆6 — Seed the platform-divergence catalogue

Take every divergence surfaced in ∆2's modernization-pitfalls research and
record it in `specs/architecture/NN-semantic-discrepancies.md` with:

- Category (type-coercion, string, date, database, HTTP, architecture, …)
- Source pattern → target gotcha
- Estimated frequency in the source corpus (derived from ∆3 grep counts)
- Forward-link to the modernization-phase spec(s) that will exercise it

The catalogue grows in every later phase; this step only seeds it.

### ∆7 — Exit gate

- [ ] `specs/architecture/09-source-index.md` exists and every file annotated
- [ ] At least three dimensions analysed with dependency-level information
- [ ] At least three modernization-flow variants proposed
      (see `ai-modernization` Phase 0 step 4)
- [ ] Architecture specs cover all major concerns (layers, DB, API, security,
      perf, deployment, business rules, testing)
- [ ] `00-project-charter.md` contains Mission / Goals / Premises / Constraints
      and a filled-in RTM
- [ ] Platform-divergence catalogue seeded with research-derived entries
- [ ] `AGENTS.md` updated with the phase index and spec pointers

If any box is unchecked, loop back to the step that produced it.

---

## Termination

| Signal   | Condition                                       | Action                                |
| -------- | ----------------------------------------------- | ------------------------------------- |
| COMPLETE | All ∆7 gates checked; files committed           | Proceed to `decisions-generator`      |
| PARTIAL  | Core artifacts present but some dimensions thin | Flag gaps in session memory; continue |
| DEGRADED | External research tools unavailable             | Use training knowledge only; disclaim |
| BLOCKED  | Source repo unreadable or ambiguous             | Ask user; do not invent               |

---

## Composition guarantee

This skill produces no new methodology; it only sequences lower-level
skills and the human-facing agent's synthesis steps. Updating any of the
composed skills (`deep-research-t1`, `requirements-extractor`,
`knowledge-management`) automatically updates this
skill's effective behaviour.

The composed skills are cross-platform (Agent-Skills open standard,
Dec 18 2025). This macro-skill is therefore also cross-platform:
invokable from Claude Code, Codex CLI, Amp, Devin, or any runtime that
supports Agent Skills with filesystem-based skill discovery.

---

## Anti-patterns

```text
✗ Skip ∆2 research → specs grounded only in source code
✓ Always seed divergence catalogue from external research

✗ Duplicate source code into specs
✓ Cross-reference by relative path + line number

✗ Write `00-project-charter.md` first, discover dimensions later
✓ Dimensions and source-index first; charter synthesises over them

✗ Inline the full deep-research / requirements playbooks in this file
✓ Keep this file a thin composition; playbooks live in their skills

✗ Invoke sub-skills sequentially when they are independent
✓ Fan out ∆2's three research topics in parallel sub-agents
```

---

## Provenance

- Source system: AI-Assisted Software Modernization Architecture,
  `docs/ai-assisted-modernization-architecture.md`, Phase 1.
- Composes: `deep-research-t1` (v2.2), `requirements-extractor` (v3.0),
  `knowledge-management`.
- Inferred pattern source: historical session logs in
  `memory/archive/full-logs/` where Phase 1 was executed manually by
  interleaving deep-research and requirements-extraction —
  this skill formalises that composition.
