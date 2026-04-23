---
name: specs-extractor
description: >-
  Phase-1 macro-skill for AI-assisted software modernization.
  A generative, research-driven workflow that discovers the analysis
  dimensions relevant to the specific source application (rather than
  filling predetermined spec slots), builds a dependency graph per
  discovered dimension, detects communities via NetworkX + Leiden,
  runs per-community deep research (budget-capped), and only then
  synthesizes source architecture specifications, a requirements
  document (MGPC + RTM), and the initial platform-divergence catalogue.
  Composes `deep-research-t1`, `requirements-extractor`, and
  `knowledge-management`. Use when starting a modernization project
  from a source repository that has no specs, no dimension analysis,
  and no ADRs — or when the user says "extract specs", "analyse the
  source", "build architecture specs", "produce the source knowledge
  base", or "run Phase 1".
version: "2.0"
metadata:
  author: OSS_Migration project
  tags: modernization, phase-1, composition, specs, requirements, dimensions, source-analysis, graph-analysis, communities
  composes: [deep-research-t1, requirements-extractor, knowledge-management]
---

# Specs Extractor — Phase 1 Macro-Skill

A **composition skill** that drives Phase 1 of the AI-Assisted Software
Modernization Architecture. It does not carry its own reasoning methodology;
it orchestrates lower-level skills in a specific **generative** sequence
against a source repository, producing whatever dimension set and spec
set the specific application actually warrants.

**This skill does not produce a predetermined list of spec files.**
It discovers dimensions from the source, derives spec filenames from
those dimensions, and produces exactly the set the app requires.

---

## Architectural position

```text
Phase 0 (source repo present)
   ↓
Phase 1 — this skill  (generative, research-first, graph-based)
   ├─ deep-research-t1       (ground + per-community research)
   ├─ knowledge-management   (CoK saturation across the corpus)
   └─ requirements-extractor (MGPC + RTM from source + research)
   ↓
Phase 2 (decisions-generator)
```

See `docs/ai-assisted-modernization-architecture.md` §"Skill / Agent
Composition" and Appendix I for the full pipeline.

---

## When to use

- Source repository present; no `specs/architecture/` directory
- User says "extract specs", "analyse the source", "run Phase 1"
- Any modernization project bootstrap where dimension set is unknown

## When NOT to use

- `specs/architecture/` already current — use `ai-modernization` from Phase 2
- Single-file ports or <5 kLOC throwaway modernizations
- The app's dimensions and specs are already published elsewhere (use them)

---

## Inputs

| Input                                             | Required? | Used by                               |
| ------------------------------------------------- | --------- | ------------------------------------- |
| Source repository (read-only)                     | **Yes**   | inventory + graph extraction          |
| Target technology (language / framework)          | **Yes**   | ∆2 research framing                   |
| Domain documentation, READMEs                     | No        | requirements-extractor + ∆2 research  |
| SME recordings / transcripts already in text form | No        | requirements-extractor input          |
| Production config samples / operational logs      | No        | requirements-extractor input          |

## Outputs (discovered, not pre-listed)

1. **Source architecture specifications** — one per discovered dimension,
   named by the dimension (e.g. `02-entity-graph.md`, `05-plugin-hooks.md`),
   stored under `specs/architecture/NN-<dimension-slug>.md`.
2. **Requirements document** — `specs/architecture/00-project-charter.md`
   (MGPC + RTM).
3. **Dimensions analysis** — `specs/architecture/NN-modernization-dimensions.md`
   with discovered dimensions, graph communities per dimension, and at
   least three modernization-flow variants derived from the graph.
4. **Platform-divergence catalogue (seed)** —
   `specs/architecture/NN-semantic-discrepancies.md`.
5. **Graph artifacts** — `tools/graph_analysis/output/*.json` — one JSON
   per dimension containing nodes, edges, communities, dependency levels.

File numbering is assigned at synthesis time (∆8); do not assume slot names.

---

## Execution protocol

Ten steps, ordered. Loop-backs explicit. Do NOT assume a predetermined
set of specs — let the source lead.

### ∆1 — Pre-flight and source inventory

- Confirm source repo path and read-only posture.
- Enumerate the source tree: list files, count by extension, measure
  size, identify entry points and schema files.
- Write a minimal provisional inventory to scratch (not yet a spec —
  the final `09-source-index.md` or equivalent is synthesized in ∆8).
- Detect the **application archetype** — web app, CLI, daemon,
  desktop, library, ETL pipeline, protocol implementation, embedded,
  mixed. See `references/app-archetype-dimensions.md`.

### ∆2 — External knowledge grounding (deep-research-t1, round 1)

Invoke `deep-research-t1` with three parallel research fan-outs
**before looking at the code in depth** — this is how you learn what
dimensions exist in this class of application:

1. **Source-platform patterns** — architectural layers, design patterns,
   framework conventions, DB patterns, messaging, session, auth, and
   deployment conventions typical of the **source technology and app
   archetype**.
2. **Target-platform best practices** — the equivalent patterns in the
   target technology for the same archetype; surface forced adaptations.
3. **Modernization pitfalls for this source→target pair and archetype** —
   known traps, semantic divergences; seeds the divergence catalogue.

Budget: 3-8 T1 searches total across the three fan-outs; sub-agent
dispatch one agent per fan-out when available. Sources annotated with
[T1/T2/T3, URL, date].

### ∆3 — Dimension inference (evidence-based, not pre-listed)

Using (a) the app archetype from ∆1, (b) the research findings from
∆2, and (c) the provisional source inventory, infer the **set of
dimensions that materially constrain this modernization**.

Starting point: the archetype → candidate-dimensions table in
`references/app-archetype-dimensions.md`. Treat it as a starter, not
a closed set: the source may reveal additional dimensions (protocol
state machines in a messaging layer, hardware abstraction in an
embedded app, etc.) and may make some listed dimensions irrelevant.

Rules:

- Every dimension carried forward must be grounded in concrete source
  evidence (files, constructs, constants).
- Every dimension must have a stated purpose — phase ordering,
  coverage scope, or semantic-parity contract.
- Drop dimensions that cannot be extracted from this source.
- Aim for 6–12 dimensions for a typical mid-scale app.

Record the dimension list + rationale in the Phase-1 scratch. Final
`NN-modernization-dimensions.md` is written in ∆8.

### ∆4 — Per-dimension graph extraction (NetworkX + Leiden)

For each discovered dimension, build a typed graph. Each dimension has
its own extraction strategy — see
`references/per-dimension-extraction.md`.

Representative (not exhaustive):

- **Call graph** — parse source AST, emit caller→callee edges.
- **Entity / schema graph** — parse DDL (SQL, models), emit table→table
  FK edges; derive dependency levels by FK DAG.
- **Module / include graph** — parse require/import statements.
- **Class hierarchy graph** — parse class/interface extends/implements.
- **Hook / extension graph** — parse registration + invocation of
  extension points.
- **Service / message graph** — parse IDL, message schemas, pub/sub calls.
- **Protocol state machine** — parse state/event enums and transitions.
- **Data-pipeline topology** — parse source→sink graph.

Reference implementation: `examples/build_php_graphs.py` (copied from
the reference project's `tools/graph_analysis/`). Adapt per target
language: the structure is generic (AST → NetworkX → Leiden); only
the language parser changes (tree-sitter supports ~50 languages).

Community detection: **Leiden** (primary, via `leidenalg` + `igraph`)
with `greedy_modularity_communities` (NetworkX) as fallback. Resolution
≈ 1.0. Record per-node community id + per-node dependency level
(topological rank in the SCC-condensed DAG).

Output artifacts:
`tools/graph_analysis/output/{dimension}_graph.json` with
`nodes / edges / communities / levels / members` fields, plus
`communities_summary.json`.

### ∆5 — Community research budget and grouping

Collect every (dimension, community) pair produced by ∆4. Let N be
the total count across all dimensions.

Caps and grouping:

| N            | Strategy                                                      |
| ------------ | ------------------------------------------------------------- |
| N ≤ 20       | One research pass per community — no grouping                 |
| 20 < N ≤ 50  | Group tiny / tightly-related communities pairwise; cap at 50  |
| N > 50       | Group aggressively by cross-dimension affinity; hard cap 50   |

Grouping heuristics (`references/community-research-budget.md`):

- Communities that span the same files across dimensions → group.
- Communities of < 3 nodes → merge into the nearest larger community
  by edge density.
- The "core" community in call + include + class graphs is almost
  always the same cluster — merge into one research pass.

### ∆6 — Per-community deep research (deep-research-t1, round 2)

For each community (or grouped community), invoke `deep-research-t1`
with a task framed to that community's concrete content:

- Input: member list (files / tables / services), dependency levels,
  representative constructs, grep of key symbols.
- Research questions: established patterns for this sub-system in the
  source tech, target-side equivalents, known modernization traps,
  relevant open-source projects for comparison.

Budget ≤ N_effective (after ∆5 grouping) searches; sub-agent fan-out
one research agent per community when available.

Output: one research note per community saved to scratch
(`.agents/scratch/phase1/research/<dim>-<comm>.md`), feeding ∆7 + ∆8.

### ∆7 — Source-corpus saturation (knowledge-management)

For large source repositories (> 10 kLOC), invoke
`knowledge-management` to run CoK expansion over the corpus using:

- Graph artifacts from ∆4 as the structural skeleton
- Community research notes from ∆6 as semantic context
- Targeted reads of key files flagged by the graphs (entry points,
  hot nodes, hub classes)

For small repos (< 10 kLOC) saturation can be done inline with
`Read` + `Grep` without invoking `knowledge-management` formally.

### ∆8 — Dimension-spec synthesis

Produce one spec file per **dimension** (not per fixed slot name).
Naming convention: `specs/architecture/NN-<dimension-slug>.md` where
`NN` is an assigned two-digit prefix and `dimension-slug` is derived
from the dimension's technical name.

Each dimension spec MUST contain:

1. **Purpose** — what this dimension captures and why it matters for
   modernization (phase ordering, coverage scope, parity contract).
2. **Graph structure** — nodes, edges, types, size (point to the JSON
   artifact in `tools/graph_analysis/output/`).
3. **Communities** — one table listing each community with member
   list + one-line characterization + representative files/tables.
4. **Dependency levels** — for dimensions with a DAG, the level
   assignment (bootstrap / level-0 / ... / leaves).
5. **Modernization impact** — which target-side patterns apply, which
   forced adaptations are expected, which divergences seed the
   catalogue.
6. **Source cross-references** — by relative path + line number; never
   duplicate source text.

Write each spec using the research notes from ∆6 and the saturation
evidence from ∆7 as the primary source of claims. Every non-trivial
claim cites a source file:line or a research tier-annotated URL.

### ∆9 — Modernization-dimensions synthesis + flow variants

Produce `NN-modernization-dimensions.md`. It MUST contain:

1. The full list of discovered dimensions with one-line purpose.
2. The inter-dimension coupling summary (e.g., call graph × entity
   graph × hook graph community overlap).
3. At least three modernization flow variants (entity-first /
   call-graph-first / service-first / etc.), each with pros and cons
   derived from the actual community structure, not generic advice.
4. A recommendation matrix scored against discovered constraints.

### ∆10 — Requirements + divergence catalogue + exit gate

**Requirements document** (∆10a): invoke `requirements-extractor` with
the bundle of (dimension specs, community research notes, source
inventory, user brief). Output → `00-project-charter.md` containing
Mission / Goals / Premises / Constraints and a Requirements
Traceability Matrix keyed to dimension-spec filenames.

**Platform-divergence catalogue seed** (∆10b): synthesize from
every divergence surfaced in ∆2 + ∆6 research into
`NN-semantic-discrepancies.md`. Each entry: category, source pattern,
target gotcha, estimated frequency (grep count from the corpus),
forward-link to the modernization phase most likely to exercise it.

**Exit gate**:

- [ ] Source inventory complete; application archetype recorded.
- [ ] ∆2 research notes exist with T1 citations.
- [ ] Dimension list justified by source evidence.
- [ ] At least three dimensions have extracted graphs + communities +
      levels in `tools/graph_analysis/output/`.
- [ ] Per-community research notes exist for every community (or grouped
      community) produced in ∆5.
- [ ] One dimension-spec file per discovered dimension, cross-referenced
      to source by path:line.
- [ ] `00-project-charter.md` with MGPC + RTM.
- [ ] `NN-modernization-dimensions.md` with discovered dimensions,
      communities summary, and ≥ 3 flow variants.
- [ ] `NN-semantic-discrepancies.md` seeded with research-derived entries.
- [ ] `AGENTS.md` updated with the phase index + spec pointers.

If any box unchecked, loop back to the step that produced it.

---

## Termination

| Signal     | Condition                                       | Action                                 |
| ---------- | ----------------------------------------------- | -------------------------------------- |
| COMPLETE   | ∆10 exit gate green                             | Hand off to `decisions-generator`      |
| PARTIAL    | Core specs present; some dimensions thin        | Flag gaps in session notes; continue   |
| DEGRADED   | Graph tools unavailable                         | Fall back to grep-based approximations |
| BLOCKED    | Source repo unreadable / ambiguous              | Ask user; do not invent                |

---

## Composition guarantee

This skill carries no reasoning methodology. Every concrete step is
a call into an atomic skill (`deep-research-t1`,
`requirements-extractor`, `knowledge-management`) or a structural
operation (graph extraction, community detection, synthesis). Updating
any atomic skill automatically updates this skill's behaviour.

The skill is cross-platform: the composed skills conform to the
Agent Skills open standard (Dec 18 2025). The graph extraction step
uses generic tooling (NetworkX + Leiden) and a language-appropriate
AST parser — the reference example is PHP via tree-sitter; replace
the parser for another source language.

---

## Anti-patterns

```text
✗ Write specs to a predetermined filename set before dimensions are known
✓ Names derive from dimensions discovered in ∆3

✗ Skip ∆2 research — generate specs only from code
✓ ∆2 research IS what tells you which dimensions matter

✗ Skip graph extraction — write prose-only "dimension" specs
✓ Every dimension spec cites its graph artifact JSON

✗ One deep-research pass for the whole codebase
✓ Per-community research — specific symbols, specific traps

✗ 200 unbounded research queries because there are 200 communities
✓ ∆5 grouping caps the budget at 50

✗ Inline the full deep-research / requirements-extractor playbooks here
✓ This file is thin composition; playbooks live in their skills

✗ Fan-out sub-agents sequentially when they are independent
✓ Parallel spawn for ∆2 fan-out (3 sessions) and ∆6 per-community
```

---

## References

- `references/app-archetype-dimensions.md` — app archetype → candidate
  dimensions starter table.
- `references/per-dimension-extraction.md` — extraction strategy per
  dimension type.
- `references/community-research-budget.md` — ∆5 grouping heuristics
  + budget math.
- `examples/build_php_graphs.py` — reference NetworkX + Leiden graph
  builder for PHP. Adapt per source language.

---

## Provenance

- Source system: AI-Assisted Software Modernization Architecture,
  `docs/ai-assisted-modernization-architecture.md`, Phase 1.
- Composes: `deep-research-t1`, `requirements-extractor`,
  `knowledge-management`.
- Pattern source: the reference project's session logs
  (`memory/archive/full-logs/`) and the graph-analysis tool suite
  (`tools/graph_analysis/`), where Phase 1 was executed manually by
  interleaving research, tree-sitter-based graph extraction,
  Leiden community detection, and per-community deep research. This
  skill formalises that workflow.
