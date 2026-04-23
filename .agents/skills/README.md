# Local Project Skills

Self-contained skill library for this project — mirrored from the shared PE_Library so that the project remains self-describing and portable across AI coding runtimes (Claude Code, Codex CLI, Amp, Devin, and any tool that honours the Agent Skills open standard published Dec 18 2025).

---

## Two layers: atomic skills and macro-skills

This directory holds two classes of skill, distinguished by how they behave, not by where they live:

| Layer             | Role                                                                                                                                                                                                                                                                                         | Examples                                                                                                                                                                                                                                                  |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Atomic skills** | Single-responsibility playbooks. Each carries a complete methodology for one reasoning pattern or one knowledge-gathering task.                                                                                                                                                              | `deep-research-t1`, `requirements-extractor`, `adversarial-thinking`, `adversarial-self-refine`, `knowledge-management |
| **Macro-skills**  | Thin composition playbooks. Each orchestrates two or more atomic skills in a specific sequence against a specific modernization-phase input, to produce a specific modernization-phase output. No duplicated methodology — macro-skills are single-source-of-truth **routers**, not content. | `specs-extractor` (Phase 1), `decisions-generator` (Phase 2), `target-specs-generator` (Phase 3), `target-code-refiner` (Phase 4), `ai-modernization` (end-to-end spine)                                                                                  |

The split mirrors the architecture described in `docs/ai-assisted-modernization-architecture.md` §"Skill / Agent Composition": atomic skills are the reusable cross-project primitives; macro-skills bind those primitives to this framework's phase model.

---

## Installed skills

### Atomic skills (cross-project, cross-platform)

| Skill                      | Purpose                                                                                                                                                                                               |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `requirements-extractor`   | Two-phase requirements discovery (bottom-up Chain-of-Knowledge → top-down intent) producing a Mission / Goals / Premises / Constraints specification.                                                 |
| `deep-research-t1`         | Tier-1 deep research pipeline for grounding decisions in authoritative sources.                                                                                                                       |
| `knowledge-management`     | Chain-of-Knowledge saturation across a large corpus.                                                                                                                                                  |
| `adversarial-thinking`     | Multi-candidate divergent design with attacker/defender stress-testing and pairwise comparison.                                                                                                       |
| `adversarial-self-refine`  | Isolated CRITIC / AUTHOR loop for iterative output refinement; emergent termination via author defence.                                                                                               |

### Macro-skills (phase compositions specific to this framework)

| Skill                    | Phase                             | Composes                                                                                                                                                                  | Produces                                                                                                                   |
| ------------------------ | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `specs-extractor`        | Phase 1 — Knowledge Extraction    | `deep-research-t1` + `requirements-extractor` + `knowledge-management`                                                                             | Source architecture specs (one per dimension), requirements document (MGPC + RTM), seeded platform-divergence catalogue    |
| `decisions-generator`    | Phase 2 — Decisions               | `adversarial-thinking` + `deep-research-t1`                                                                                                      | Stress-tested, stakeholder-accepted ADRs; atomic cross-reference updates                                                   |
| `target-specs-generator` | Phase 3 — Target Specifications   | `adversarial-self-refine` + `deep-research-t1` + `requirements-extractor`                                                                                                 | `spec.md` / `plan.md` / `tasks.md` triplet per unblocked modernization phase, each refined to convergence                  |
| `target-code-refiner`    | Phase 4 — Modernization Execution | `ai-modernization` (per-batch loop, coverage validator, trap catalogue, traceability rules) + `adversarial-self-refine` + `deep-research-t1` | Verified target artifacts with traceability; coverage + semantic verification reports; explicit loop-backs to Phases 2 / 3 |
| `ai-modernization`       | Spine — Phases 0 → 5              | Called by the macro-skills as the source of execution rules, coverage-validator patterns, traceability-comment formats, and directory conventions                         | End-to-end modernization workflow reference, plus Phase-0 and Phase-5 playbook content                                     |

---

## Composition pattern (skills drive agents)

Each macro-skill is **the playbook**. The thin agent wrappers in `.claude/agents/` are the Claude-specific **runtime harnesses** (tool whitelist, model pin, context isolation, worktree isolation, per-agent memory) that exist only to provide runtime concerns the Agent Skills standard intentionally does not specify.

```text
.agents/skills/<name>/SKILL.md           ← playbook (portable, single source of truth)
       ↑
       │ preloaded via `skills:` frontmatter
       │
.claude/agents/<name>.md                 ← thin runtime harness (Claude-specific)
```

The playbook is one file. The harness is the other. They never duplicate content.

- Update a skill → every invocation mode benefits (main thread, static subagent, dynamic `Agent`-tool dispatch, any cross-tool runtime that supports Agent Skills).
- Update an agent wrapper → only Claude-specific runtime concerns change.
- Remove the wrapper → skills still work; they can be invoked directly in main thread (`/skill-name`) or dispatched dynamically via `spawn_agent` without a named agent file.

See `docs/ai-assisted-modernization-architecture.md` Appendix I (Agent Integration) and Appendix K (Agent Architecture in 2025 CLI Coding Assistants) for the research and contrast with the pre-Skills-GA era when static `*.md` agent files carried the full methodology in their body.

---

## Directory layout

```text
.agents/skills/
├── README.md                       ← this file
│
├── adversarial-self-refine/        ← atomic
│   ├── SKILL.md
│   └── references/
├── adversarial-thinking/           ← atomic
│   ├── SKILL.md
│   ├── agents/
│   ├── evals/
│   └── references/
├── deep-research-t1/               ← atomic
│   ├── SKILL.md
│   ├── evals/
│   └── references/
├── knowledge-management/           ← atomic
├── requirements-extractor/         ← atomic
│   ├── SKILL.md
│   └── references/
│
├── ai-modernization/                   ← spine (Phases 0→5 reference)
│   ├── SKILL.md
│   └── references/
│       ├── adr-template.md
│       ├── flow-variants.md
│       └── semantic-traps-example.md
│
├── specs-extractor/                ← macro, Phase 1
│   └── SKILL.md
├── decisions-generator/            ← macro, Phase 2
│   └── SKILL.md
├── target-specs-generator/         ← macro, Phase 3
│   └── SKILL.md
└── target-code-refiner/            ← macro, Phase 4
    └── SKILL.md
```

---

## Invocation modes

The same skill can be executed three ways; pick the lightest that fits:

| Mode                        | When to use                                                                           | How                                                                                |
| --------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Main-thread direct**      | Quick interactive use; no isolation needed; user-triggered.                           | `/skill-name` slash command or description-based auto-invocation.                  |
| **Static subagent wrapper** | Session-wide persona; enforced tool whitelist; model pin; team-shared review surface. | `@agent-name` or `claude --agent agent-name`; wrapper preloads the skill.          |
| **Dynamic subagent spawn**  | Parallel fan-out; one-shot isolation; dynamic task parameterisation.                  | Master skill or orchestrator agent calls the `Agent` tool with a task description. |

Claude Code disallows nested subagent spawning (subagents cannot spawn further subagents). Skill-driven orchestration from the main thread or the top-level orchestrator agent is the portable pattern — see `docs/ai-assisted-modernization-architecture.md` §"Skill / Agent Composition".

---

## Cross-platform portability

Every skill in this directory conforms to the Agent Skills open standard (Anthropic, Dec 18 2025). The skills are consumable by any compliant runtime:

| Runtime     | Path convention                                                                             |
| ----------- | ------------------------------------------------------------------------------------------- |
| Claude Code | `.agents/skills/*/SKILL.md` (native, plus this project's `CLAUDE.md` → `@AGENTS.md` import) |
| Codex CLI   | `.agents/skills/*/SKILL.md` or `$REPO_ROOT/.agents/skills/` discovery                       |
| Amp         | `.agents/skills/SKILL.md` — native location                                                 |
| Devin       | `.agents/skills/`, `.claude/skills/`, `.codex/skills/` — all scanned                        |
| Copilot CLI | Manageable via `gh` CLI since Apr 2026                                                      |

The agent wrappers in `.claude/agents/` are Claude-specific. To run this framework under Codex CLI, mirror the wrappers as `.codex/agents/*.toml` (format differs; content is essentially "preload these skills + this tool whitelist"). Under Amp, Devin, Jules, or any tool without a static subagent file, the skills are invoked directly — no wrapper needed.

---

## How to extend

1. **Add a new atomic skill** → clone an existing atomic-skill directory, replace `SKILL.md` body with the new playbook, keep the frontmatter schema. Atomic skills must be self-contained (no references to macro-skills).
2. **Add a new macro-skill** → create a directory under `.agents/skills/`, write a `SKILL.md` that describes only (a) when to use, (b) inputs / outputs, (c) the ∆-step composition sequence over existing atomic skills, (d) termination signals, (e) anti-patterns. Do **not** inline atomic-skill methodology. List the composed skills in the frontmatter `composes:` field so the dependency is explicit.
3. **Add an agent wrapper** → only when the skill needs Claude-specific runtime enforcement (tool whitelist, model pin, worktree isolation, session-wide launch). Create `.claude/agents/<name>.md` with ≤ 20 lines of body that (a) identifies itself as a thin harness, (b) points at the matching skill, (c) lists its runtime concerns, (d) declares what it does not do. Never duplicate the playbook.
4. **Update `AGENTS.md`** → the consistency rule from that file applies to this directory: any new macro-skill that changes the phase index must be reflected in `AGENTS.md` and in `docs/ai-assisted-modernization-architecture.md` Appendix I.

---

## Governance

These skills are referenced from the main architecture document and its appendices; invoking them within this project must use the local copies in this directory rather than external paths (e.g., `/Users/.../PE_Library/__SKILLS__/*`) so that the project is portable and fully auditable. If a skill is updated in the shared PE_Library, re-sync by copying the new `SKILL.md` (and any `references/`) into the matching subdirectory here and commit the change as a single, reviewable diff.
