# Claude Code Agents — Thin Runtime Wrappers

This directory holds **thin runtime harnesses** — one markdown file per
agent. Each file carries only Claude-Code-specific runtime concerns
(tool whitelist, model pin, context isolation, worktree isolation,
per-agent memory) and preloads one or more skills from
`.agents/skills/` via the `skills:` frontmatter. None of these files
carries methodology content.

The methodology — the playbooks, protocols, anti-patterns,
termination signals, composition rules — lives in the skills. Skills
are cross-platform (Agent Skills open standard, 18 Dec 2025) and are
therefore the portable, single-source-of-truth layer. The wrappers in
this directory are the Claude-specific, replaceable binding layer.

See `docs/ai-assisted-modernization-architecture.md` §"Skill / Agent
Composition" for the framework-level rationale, and Appendix K for the
2025 research on which this split is based.

---

## Why the split?

Before Agent Skills reached GA on 16 Oct 2025, `.claude/agents/*.md`
files were the only place to keep a specialised agent's persona,
methodology, and toolset — so the body of each file carried the full
playbook. That is the **pre-Skills-era pattern**, and it is still what
most blog posts and examples show.

After Skills GA (Oct 2025) and especially after Skills were published
as an open cross-platform standard (18 Dec 2025), the same persona can
live in a skill that works in Claude Code, Codex CLI, Amp, Devin,
Jules, and any compliant runtime. The agent file's only remaining job
is runtime binding — the things a cross-platform skill cannot express:

| Capability                                    | Skill alone | Agent wrapper |
| --------------------------------------------- | :---------: | :-----------: |
| Deliver methodology / playbook                | ✓           | —             |
| Progressive disclosure of resources           | ✓           | —             |
| Cross-tool portability                        | ✓           | ✗             |
| `/command` invocation                         | ✓           | ✗             |
| **Enforced tool whitelist**                   | ✗           | ✓             |
| **Isolated context window**                   | ✗           | ✓             |
| **Per-agent model pin**                       | ✗           | ✓             |
| **Session-wide launch** (`claude --agent X`)  | ✗           | ✓             |
| **Worktree isolation**                        | ✗           | ✓             |
| **Per-agent persistent memory**               | ✗           | ✓             |
| **Managed / org-tier override**               | ✗           | ✓             |

Every capability in the "agent wrapper" column is a runtime concern,
not a content concern. That is exactly the split these files enforce.

---

## Wrappers in this directory

| File                            | Preloaded skill (primary) | Phase | Model | Isolation | Purpose                                                    |
| ------------------------------- | ------------------------- | :---: | :---: | :-------: | ---------------------------------------------------------- |
| `modernization-orchestrator.md`     | `ai-modernization`            | 0-5   | opus  | —         | End-to-end phase detection and dispatch                    |
| `specs-extractor.md`            | `specs-extractor`         | 1     | opus  | —         | Source knowledge extraction (dimensions, MGPC, divergence) |
| `decisions-generator.md`        | `decisions-generator`     | 2     | opus  | —         | ADR drafting via adversarial stress-testing                |
| `target-specs-generator.md`     | `target-specs-generator`  | 3     | opus  | —         | Per-phase spec/plan/tasks triplet with critic/author loop  |
| `target-code-refiner.md`        | `target-code-refiner`     | 4     | opus  | worktree  | Per-batch execution, coverage, semantic verification       |

Each wrapper also preloads the sub-skills its macro-skill composes with
(`deep-research-t1`, `adversarial-thinking`, `adversarial-self-refine`,
`requirements-extractor`, `knowledge-management`), so those
sub-skills are available without additional discovery round-trips
during multi-step runs.

---

## How a wrapper file is structured

Every file in this directory follows the same shape:

```yaml
---
name: <agent-name>
description: <when Claude should delegate to this agent>
tools: <comma-separated whitelist>
model: <opus | sonnet | haiku | inherit | full-id>
permissionMode: <default | acceptEdits | auto | dontAsk | plan>
isolation: <worktree | none>         # optional
memory: <project | user | local>     # optional
skills: [<skill-id>, <skill-id>, ...] # preload at startup
---

# <Agent name> (agent wrapper)

Thin runtime harness. Points at the macro-skill. Lists runtime
concerns. ~10-80 lines of body at most. No methodology.
```

The body is short by design. If a wrapper's body starts accumulating
methodology, that methodology belongs in a skill — extract it.

---

## Anti-patterns (do not do)

- **Duplicate the skill's playbook into the agent body.** The two will
  drift. Skill is the source of truth.
- **Put new methodology into an agent file because "it is
  Claude-specific".** Runtime config belongs here; methodology belongs
  in a skill.
- **Create a separate agent for every conceivable task.** Most tasks
  are well-served by skills invoked in the main thread. Reserve
  agents for context isolation, tool-whitelist enforcement, model
  pinning, worktree isolation, or session-wide launch.
- **Rely on nested subagent spawning.** Claude Code forbids it
  (docs.claude.com/en/docs/claude-code/sub-agents). Orchestration
  happens from the main thread, via skills. These wrappers follow that
  rule.

---

## Cross-tool portability

The skills these wrappers point at are portable. To run the same
modernization framework on Codex CLI, Amp, Devin, or any runtime that
supports filesystem-based skill discovery:

- `.agents/skills/*` is consumed as-is — the playbooks port across
  tools without modification.
- This directory (`.claude/agents/`) is **not** portable and does not
  need to be. Each target tool provides its own runtime-binding layer
  (Codex: `.codex/agents/*.toml`; Cursor:
  `.cursor/agents/*.md` with a subtly different schema; Amp: generic
  Task-tool subagents; Devin / Jules / Windsurf: no user-defined
  subagent file mechanism at all — they rely on the skills directly).
- The correct mental model: skill library = portable core;
  this directory = replaceable Claude binding.

See Appendix K of `docs/ai-assisted-modernization-architecture.md` for the
full cross-vendor matrix and citations.
