"""
Pass 3: targeted modernization rename for remaining framework-context 'migration' occurrences.
Protected: database/schema/Alembic/data/pgloader migration contexts.
"""

import os

REPLACEMENTS = [
    # AI-assisted migration phrases
    ("AI-assisted migration", "AI-assisted modernization"),
    ("AI-Assisted Migration", "AI-Assisted Modernization"),
    ("coverage-driven migration", "coverage-driven modernization"),
    ("End-to-end migration reference", "End-to-end modernization reference"),
    ("end-to-end migration", "end-to-end modernization"),
    ("End-to-end migration", "End-to-end modernization"),
    ("run the migration", "run the modernization"),
    # Skill description / trigger phrase remnants
    ("create migration specs", "create modernization specs"),
    ("the migration and becomes the checklist", "the modernization and becomes the checklist"),
    ("Ensure the complete migration is correct", "Ensure the complete modernization is correct"),
    ("migration-pitfalls research", "modernization-pitfalls research"),
    ("Phase-3 migration agent", "Phase-3 modernization agent"),
    ("each migration phase", "each modernization phase"),
    ("Each migration phase", "Each modernization phase"),
    ("migration style", "modernization style"),
    ("turn AI-assisted migration", "turn AI-assisted modernization"),
    ("Turn AI-assisted migration", "Turn AI-assisted modernization"),
    # Architecture doc body text
    ("the migration exists", "the modernization exists"),
    ("bind it to the business intent of the migration", "bind it to the business intent of the modernization"),
    ("that change what AI-assisted migration can do", "that change what AI-assisted modernization can do"),
    ("AND migration strategy", "AND modernization strategy"),
    ("the migration strategy", "the modernization strategy"),
    ("Align migration scope", "Align modernization scope"),
    ("the migration scope", "the modernization scope"),
    ("during migration:", "during modernization:"),
    ("During migration,", "During modernization,"),
    ("during migration,", "during modernization,"),
    ("for a migration style", "for a modernization style"),
    ("any migration style", "any modernization style"),
    ("source of silent semantic defects during migration", "source of silent semantic defects during modernization"),
    ("are systematically missed during migration", "are systematically missed during modernization"),
    ("systematically missed during migration", "systematically missed during modernization"),
    ("migration is done", "modernization is done"),
    ("migration from a probabilistic", "modernization from a probabilistic"),
    ("materially constrains migration", "materially constrains modernization"),
    ("understand where the migration stands", "understand where the modernization stands"),
    ("needs to resume, run coverage checks, do semantic verification, or create migration specs",
     "needs to resume, run coverage checks, do semantic verification, or create modernization specs"),
    # Agent wrapper descriptions
    ("End-to-end migration orchestrator", "End-to-end modernization orchestrator"),
    ("Does not contain migration methodology", "Does not contain modernization methodology"),
    ("Language or framework migration", "Language or framework modernization"),
    # Table entries in arch doc
    ("End-to-end migration workflow reference", "End-to-end modernization workflow reference"),
    ("End-to-end migration reference", "End-to-end modernization reference"),
]

PROTECTED = [
    "database migration",
    "Database migration",
    "Database Migration",
    "schema migration",
    "Schema migration",
    "Schema Migration",
    "Alembic migration",
    "alembic migration",
    "data migration script",
    "data-migration script",
    "Data migration script",
    "Data migration strategy",
    "data migration strategy",
    "Data migration",
    "pgloader",
    "mysql",
    "MySQL",
    "one-time migration",
    "OAuth2 migration",
    "migration script",
    "migration file",
    "migration table",
    "migration infrastructure",
    "migration generation",
    "seed migration",
    "migration from MySQL",
    "Data migration scripts",
    "migration scripts",
    "schema migrations",
    "Schema migrations",
]

TARGET_FILES = [
    "docs/ai-assisted-modernization-architecture.md",
    ".agents/skills/ai-modernization/SKILL.md",
    ".agents/skills/specs-extractor/SKILL.md",
    ".agents/skills/target-code-refiner/SKILL.md",
    ".agents/skills/decisions-generator/SKILL.md",
    ".agents/skills/target-specs-generator/SKILL.md",
    ".agents/skills/README.md",
    ".claude/agents/modernization-orchestrator.md",
    ".claude/agents/specs-extractor.md",
    ".claude/agents/target-specs-generator.md",
    ".claude/agents/target-code-refiner.md",
    ".claude/agents/README.md",
    "AGENTS.md",
]


def process(path):
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    new_lines = []
    changed = 0
    for line in lines:
        if any(p in line for p in PROTECTED):
            new_lines.append(line)
            continue
        new_line = line
        for old, new in REPLACEMENTS:
            new_line = new_line.replace(old, new)
        if new_line != line:
            changed += 1
        new_lines.append(new_line)
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"  ✓ {path} ({changed} lines)")
    return changed


total = 0
for p in TARGET_FILES:
    total += process(p)
print(f"\nPass 3 done: {total} lines changed")