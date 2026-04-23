import re, os

PATH = os.path.join(os.path.dirname(__file__), '..', 'skills', 'ai-modernization', 'SKILL.md')
PATH = os.path.normpath(PATH)

with open(PATH, 'r') as f:
    txt = f.read()

# Replace the whole Phase-0 block (up to but not including Phase 1 heading).
pattern = re.compile(
    r'## Phase 0: Deep Knowledge Extraction.*?(?=## Phase 1: Spec Generation and ADR Proposals)',
    re.DOTALL,
)

NEW = """## Phase 0: Deep Knowledge Extraction

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

"""

new_txt, n = pattern.subn(NEW, txt)
print(f"replacements: {n}")
if n:
    with open(PATH, 'w') as f:
        f.write(new_txt)
    print("written")
