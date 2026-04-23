"""
Remove references to the 4 deleted skills from README and spine table.
Deleted: document-ingestion, document-survey, continuation-and-handoff, selecting-pe-methods
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def patch(path, ops):
    full = os.path.join(ROOT, path)
    with open(full, "r", encoding="utf-8") as f:
        txt = f.read()
    original = txt
    for old, new in ops:
        txt = txt.replace(old, new)
    if txt != original:
        with open(full, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"  patched: {path}")
    else:
        print(f"  unchanged: {path} (no matches found)")


# ── Shared substitutions that apply to multiple files ──────────────────────

COMPOSES_SPECS = (
    "`deep-research-t1` + `requirements-extractor` + `knowledge-management` + `document-ingestion`",
    "`deep-research-t1` + `requirements-extractor` + `knowledge-management`",
)
COMPOSES_DECISIONS = (
    "`adversarial-thinking` + `deep-research-t1` + `selecting-pe-methods`",
    "`adversarial-thinking` + `deep-research-t1`",
)
COMPOSES_REFINER_SUFFIX = (
    " + `continuation-and-handoff`",
    "",
)

# ── .agents/skills/README.md ───────────────────────────────────────────────

README_SKILLS = ".agents/skills/README.md"

README_SKILLS_OPS = [
    # Examples column
    ("`, `document-ingestion`", ""),
    ("`, `document-survey`", ""),
    ("`, `continuation-and-handoff`", ""),
    ("`, `selecting-pe-methods`", ""),
    # Atomic table rows (exact row text including trailing newline)
    (
        "| `document-ingestion`       | Ingest transcripts, video frames, spreadsheets into structured knowledge.                                                                                                                             |\n",
        "",
    ),
    (
        "| `document-survey`          | Reads and cross-references document fragments from dual converters, analyses WEBP images, researches the subject entity, and generates a structured survey / knowledge base with source traceability. |\n",
        "",
    ),
    (
        "| `continuation-and-handoff` | Multi-session continuity and checkpoint protocols.                                                                                                                                                    |\n",
        "",
    ),
    (
        "| `selecting-pe-methods`     | Selection of prompt-engineering method per task archetype.                                                                                                                                            |\n",
        "",
    ),
    # Macro table Composes cells
    COMPOSES_SPECS,
    COMPOSES_DECISIONS,
    COMPOSES_REFINER_SUFFIX,
    # Directory layout entries
    ("├── continuation-and-handoff/       ← atomic\n", ""),
    ("├── document-ingestion/             ← atomic\n", ""),
    ("├── selecting-pe-methods/           ← atomic\n", ""),
    (
        "├── document-survey/            ← atomic\n│   ├── SKILL.md\n│   └── references/\n",
        "",
    ),
    ("├── document-survey/            ← atomic\n", ""),
    # "also preloads" sentence in bottom portability section
    (
        "(`deep-research-t1`, `adversarial-thinking`, `adversarial-self-refine`,\n"
        "`requirements-extractor`, `knowledge-management`,\n"
        "`continuation-and-handoff`, `selecting-pe-methods`)",
        "(`deep-research-t1`, `adversarial-thinking`, `adversarial-self-refine`,\n"
        "`requirements-extractor`, `knowledge-management`)",
    ),
]

patch(README_SKILLS, README_SKILLS_OPS)

# ── .agents/skills/ai-modernization/SKILL.md ──────────────────────────────

SPINE = ".agents/skills/ai-modernization/SKILL.md"

SPINE_OPS = [
    COMPOSES_SPECS,
    COMPOSES_DECISIONS,
    COMPOSES_REFINER_SUFFIX,
]

patch(SPINE, SPINE_OPS)

# ── .claude/agents/README.md ───────────────────────────────────────────────

README_AGENTS = ".claude/agents/README.md"

README_AGENTS_OPS = [
    (
        "(`deep-research-t1`, `adversarial-thinking`, `adversarial-self-refine`,\n"
        "`requirements-extractor`, `knowledge-management`,\n"
        "`continuation-and-handoff`, `selecting-pe-methods`)",
        "(`deep-research-t1`, `adversarial-thinking`, `adversarial-self-refine`,\n"
        "`requirements-extractor`, `knowledge-management`)",
    ),
]

patch(README_AGENTS, README_AGENTS_OPS)

# ── Final residual check ───────────────────────────────────────────────────

REMOVED = [
    "document-ingestion",
    "document-survey",
    "continuation-and-handoff",
    "selecting-pe-methods",
]

CHECK_FILES = [
    README_SKILLS,
    SPINE,
    README_AGENTS,
]

print("\n-- residual check --")
ok = True
for path in CHECK_FILES:
    full = os.path.join(ROOT, path)
    with open(full, "r", encoding="utf-8") as f:
        content = f.read()
    for skill in REMOVED:
        if skill in content:
            print(f"  WARN {path}: still contains '{skill}'")
            ok = False
if ok:
    print("  clean — no residual references found")