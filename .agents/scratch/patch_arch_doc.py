import os

PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'ai-assisted-modernization-architecture.md'))

with open(PATH, 'r') as f:
    txt = f.read()

# After Appendix I.3's "Loop-backs as first-class edges" paragraph, inject a new "Generative dimension discovery" paragraph
MARKER = """Loop-backs are the mechanism by which Phase-4 evidence feeds back into
Phases 2 and 3; they are not exceptions.

#### I.4 Claude agent wrappers — thin runtime harnesses"""

NEW_INSERT = """Loop-backs are the mechanism by which Phase-4 evidence feeds back into
Phases 2 and 3; they are not exceptions.

**Generative dimension discovery.** The Phase-1 macro-skill
(`specs-extractor`) does not produce a predetermined list of spec
filenames. It follows a ten-step workflow: (1) source inventory and
application-archetype detection, (2) external-knowledge grounding via
`deep-research-t1` (three fan-outs: source-platform patterns,
target-platform best practices, pitfalls for this source→target pair),
(3) dimension inference from archetype + research + source evidence —
using an archetype → candidate-dimensions starter table but dropping
rows without source evidence and adding rows the source reveals,
(4) per-dimension graph extraction via AST parsing + NetworkX + Leiden
community detection (reference implementation: the PHP graph builder
at `tools/graph_analysis/build_php_graphs.py`; adapt per source language
by swapping the AST parser), (5) community research budget and
grouping with a hard cap of 50 research passes, (6) per-community
deep research, (7) source-corpus saturation via `knowledge-management`,
(8) dimension-spec synthesis — one file per discovered dimension named
by the dimension itself, (9) modernization-dimensions synthesis with
flow variants derived from actual community structure, (10)
`requirements-extractor` for MGPC + RTM, plus the seeded
platform-divergence catalogue. See
`.agents/skills/specs-extractor/SKILL.md` and its `references/`
directory for the full playbook plus the archetype-dimensions table,
per-dimension extraction strategies, and community-research budget
heuristics.

#### I.4 Claude agent wrappers — thin runtime harnesses"""

if MARKER in txt:
    txt = txt.replace(MARKER, NEW_INSERT)
    print('I.3 generative-discovery paragraph inserted')
else:
    print('MARKER not found — skipping I.3 insert')

with open(PATH, 'w') as f:
    f.write(txt)
