# ∆5 — Community Research Budget + Grouping Heuristics

After ∆4 produces one graph per dimension, each graph has communities.
Summed across dimensions this is N raw communities. ∆5 groups them so
that ∆6's per-community research budget stays bounded.

---

## Hard caps

| Measure                           | Cap                     |
| --------------------------------- | ----------------------- |
| Maximum research passes in ∆6     | 50                      |
| Minimum community size to research alone | 3 nodes         |
| Maximum community group size      | 8 member communities    |

Grouping is NOT optional above 20 communities. At > 50 it is
aggressive. The goal is to avoid 200 unbounded web searches.

---

## Grouping heuristics

Apply in order. Stop when total effective passes ≤ the cap.

### Heuristic 1 — Merge by cross-dimension co-location

If the same set of files appears in community X of dimension A and
community Y of dimension B, merge X and Y into one research pass.

Example from the reference project:
- Call-graph community "Core" = `{functions.php, db.php, config.php, ...}`
- Include-graph community "bootstrap" = same file set
- Class-hierarchy community "Db" = `{Db, Db_Pgsql, Db_Mysqli}` living in the same files

→ one research pass: "TT-RSS bootstrap / core"

### Heuristic 2 — Absorb tiny communities

Any community with < 3 nodes: merge into its nearest larger neighbour
by (a) shared edges across dimensions, then (b) call-graph proximity.

### Heuristic 3 — Merge by subsystem semantic label

After extraction, each community has a representative set of symbols.
If two communities' representatives share a subsystem label
(e.g., both have "Pref_" prefix; both mention "HOOK_RENDER"), merge.

### Heuristic 4 — Cap by dimension

If one dimension has > 15 communities, keep only the top 10 by size;
absorb smaller communities into the nearest larger one. Very small
communities rarely warrant their own research pass.

### Heuristic 5 — Cross-cutting services go last

Logging, error handling, configuration — group these into one
"infrastructure" research pass at the end. Usually they need the same
target-side research ("structured logging in Python") regardless of
source subsystem.

---

## Budget math

Worst case: N = total raw communities across all dimensions.

- N ≤ 20  →  one pass per community; budget = N
- 20 < N ≤ 50  →  apply Heuristics 1–3 until N_eff ≤ 50; budget = N_eff
- N > 50  →  apply all heuristics aggressively; hard cap 50

Each research pass ≈ 3-8 T1 searches + 1-2 fetches (per
`deep-research-t1` Δ1–Δ7). Total Phase-1 research cost:

- Small app: ~15 searches total (∆2 + few ∆6 passes)
- Mid-scale: ~50-150 searches
- Large: ~200-400 searches (hard ceiling after grouping)

Sub-agent fan-out reduces wall-clock time: spawn one agent per
∆6 pass when a sub-agent mechanism is available. Agents are
independent; merge their output into synthesis.

---

## Scheduling notes

- ∆2 research (3 fan-outs) MUST complete before ∆6 starts — the
  target-side and archetype-pattern context ∆2 produces is what
  makes per-community research efficient. Do NOT interleave.
- ∆6 passes are independent and parallelisable.
- ∆7 saturation happens after ∆6 so it can use community notes as
  CoK seed context.

---

## Community note format (∆6 output)

Each ∆6 research pass writes one note to
`.agents/scratch/phase1/research/<dim>-<comm>.md`:

```markdown
# Dimension: <name> · Community: <id / label>

## Members
- <file / table / service> (<level>, <LOC>)
- ...

## Representative constructs
- <class / function / symbol>
- ...

## Research findings
<Tier-annotated citations from deep-research-t1 Δ1-Δ7>

## Target-side mapping
<How this community maps to target-technology idioms>

## Divergences spotted
<Seeds for the platform-divergence catalogue in ∆10>

## Open questions
<Items for Phase 2 ADR drafting>
```

These notes feed ∆8 synthesis + ∆10a requirements derivation +
∆10b divergence-catalogue seeding.

---

## Degradation

If `deep-research-t1` or web access is unavailable:
- Skip ∆2 (mark DEGRADED in session notes)
- ∆6 falls back to "training-knowledge-only" per-community notes
- Dimension specs still produced from graphs + source reads, but
  with no target-side grounding. Flag the Phase-1 output as
  PARTIAL so Phase 2 knows to revisit.
