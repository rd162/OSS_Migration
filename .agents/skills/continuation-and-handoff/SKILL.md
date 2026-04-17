---
name: continuation-and-handoff
description: Generates structured continuation prompts for resuming work in the next session, or handoff prompts for transferring work to a different agent. Adapts to the host environment — uses native mechanisms (task lists, sub-agents, RALPH loops) when available, falls back to portable markdown artifacts. Use when work spans multiple sessions, context limits approach, a natural phase boundary is reached, or a different agent capability is needed.
version: "2.0"
metadata:
  author: rd162@hotmail.com
  tags: continuation, handoff, multi-session, cross-vendor, pipeline
---

# Continuation and Handoff

Ensure no work is lost at session boundaries.
Generate structured artifacts that let the same agent resume (continuation)
or a different agent take over (handoff).

This skill is self-contained — it detects the host environment
and adapts its output format accordingly.
No external skills are required, though it composes well
as the final step of any multi-phase workflow.

## When to Use

**Generate CONTINUATION when:**

- Context approaching limits (token budget >70%)
- Natural session boundary (phase complete, milestone reached)
- Work remaining for the same agent in a subsequent session
- Proactive checkpoint (every 2-3 major work units)

**Generate HANDOFF when:**

- Task requires a different capability tier (reasoning → execution)
- Natural agent boundary (analysis → implementation)
- User explicitly requests multi-agent workflow
- Output is an intermediate artifact for a different agent

## When NOT to Use

- Task completes fully within current session (no remaining work)
- Simple single-turn request with no state to preserve
- User explicitly says "don't worry about saving progress"
- Output is self-contained and needs no downstream agent

## Termination

| Signal   | Condition                                              | Action                                         |
| -------- | ------------------------------------------------------ | ---------------------------------------------- |
| COMPLETE | Continuation or handoff artifact written/output        | ✓ STOP — boundary handled                      |
| SKIPPED  | Task completed within session, no boundary reached     | ✓ STOP — no artifact needed                    |
| BLOCKED  | No file system, no task tools, no chat output possible | Output as final chat message (always possible) |

## Graceful Degradation

This skill always produces output — it never halts.
It adapts to whatever mechanisms are available:

- **Full capability** (task tools + file system + sub-agents):
  Use native task management, spawn sub-agents for handoff,
  write structured files for continuation.
- **File system only** (no task tools):
  Generate continuation/handoff as markdown files in the project.
- **Chat only** (no file system, no tools):
  Output the complete continuation or handoff prompt as the final chat message.
  The user copy-pastes it into the next session.

The output is always a structured artifact.
The delivery mechanism varies; the content does not.

---

## Core Terminology

| Term             | Definition                                        |
| ---------------- | ------------------------------------------------- |
| **Continuation** | Prompt for resuming the same agent next session   |
| **Handoff**      | Prompt for transferring work to a different agent |

---

## Environment Detection and Adaptation

This skill adapts its output to the host environment.
Detect capabilities and use the most native mechanism available.

### Capability Matrix

| Environment        | Continuation Mechanism             | Handoff Mechanism              |
| ------------------ | ---------------------------------- | ------------------------------ |
| **Claude Code**    | Task list + todowrite/todoread     | Sub-agents or new CC session   |
| **GitHub Copilot** | TODO comments + issue creation     | Separate workflow / agent      |
| **Cursor**         | .cursor-rules + TODO markers       | New composer session           |
| **Codex (OpenAI)** | Task file + checkpoint comments    | New codex session              |
| **Gemini CLI**     | Continuation file + session state  | New session with context file  |
| **Kimi / other**   | Continuation file or chat output   | Handoff file or chat output    |
| **Bare LLM / API** | Continuation prompt in final reply | Handoff prompt as final output |
| **MCP Skillz**     | Continuation markdown file         | Handoff markdown file          |

### Detection Heuristic

```text
IF task list tools available (todowrite, todoread, task_list)
  → Use native task management for continuation
  → Write remaining work as structured tasks
ELIF sub-agent / spawn capability available
  → Use sub-agents for handoff
  → Generate handoff context as sub-agent prompt
ELIF file system access available
  → Generate continuation/handoff as markdown files
  → Place in project directory
ELSE (bare LLM, no tools)
  → Output continuation/handoff prompt as final chat message
  → User copy-pastes into next session
  → This is always possible — the skill never fails to produce output
```

---

## Continuation Structure

For the same agent resuming in the next session.

### Template

```text
═══════════════════════════════════════════════
CONTINUATION: [Agent/Session Name] Session [N] → Session [N+1]
═══════════════════════════════════════════════

## TO RUN THIS SESSION

[Loading instructions appropriate to environment]

═══════════════════════════════════════════════

ARTIFACTS:
- [file]: [type] (skeleton|blueprint|code|research|config)

DONE: [1-line summary of completed work]
PENDING: [what remains for this agent]

TASK_FOR_NEXT_SESSION:
[Explicit instructions for next session]
- Target: [specific focus]
- Constraints: [carried forward]
- Success criteria: [measurable outcome]

NEXT_CONTINUATION: [expected output for subsequent session]
═══════════════════════════════════════════════
```

### Claude Code Adaptation

When task list tools are available, write continuation as tasks:

```text
Use todowrite to create tasks:
  - task_1: "[specific next action]" (status: not_started)
  - task_2: "[specific next action]" (status: not_started)
  - context: "Continuation from session N. Artifacts: [list]. Constraints: [list]."

On next session start:
  → Agent reads task list → resumes from first not_started task
```

### RALPH Loop Adaptation

When operating inside a RALPH-style iteration loop:

```text
Write to IMPLEMENTATION_PLAN.md or equivalent:
  - Mark completed tasks as done
  - Next task clearly specified at top
  - Exit cleanly (agent returns, loop re-invokes)
  - Fresh context on next iteration (no carry-over drift)
```

---

## Handoff Structure

For transferring work to a different agent or capability tier.

### Template

```text
═══════════════════════════════════════════════
HANDOFF: [Current Agent] → [Next Agent]
═══════════════════════════════════════════════

## TO RUN THIS HANDOFF

[Loading instructions appropriate to environment]

═══════════════════════════════════════════════

ARTIFACTS:
- [file]: [type] (code|research|analysis|doc|config|script|synthesis)

DONE: [1-line summary from current agent]
PENDING: [what next agent must complete]

PROMPT_FOR_NEXT_AGENT:
[Explicit instructions for receiving agent]
- Task: [specific action]
- Preserve: [constraints from current agent]
- Output: [expected format]

SEALED_HANDOFFS (cascade mode only):
- HANDOFF_TO_AGENT_N+2: [pass forward unchanged]
- HANDOFF_TO_AGENT_N+3: [pass forward unchanged]

NEXT_HANDOFF: [what receiving agent should produce]
═══════════════════════════════════════════════
```

### Claude Code Sub-Agent Adaptation

When sub-agent or spawn capability is available:

```text
Spawn sub-agent with:
  - System prompt: [handoff PROMPT_FOR_NEXT_AGENT section]
  - Context files: [artifact list]
  - Constraints: [inherited from current session]
  - Return: [expected output format]
```

### Bare LLM Adaptation

When no tooling is available:

```text
Output the complete handoff as the final chat message.
Structure it so the user can:
  1. Copy the PROMPT_FOR_NEXT_AGENT section
  2. Paste it as the opening message in a new session
  3. Attach referenced artifacts manually
```

---

## Inversion of Control (IoC) Principle

The capable agent generates handoffs — not a central orchestrator.
Each agent produces its output PLUS the handoff for the next agent.

```text
Classic (fragile):  Orchestrator → prompt₁ → Agent₁ → prompt₂ → Agent₂
IoC (robust):       Agent₁(req) → [artifact₁ + handoffs₂₋ₙ] → Agent₂ → [artifact₂ + param(handoff₃)]
```

This principle means no rigid orchestration layer is required.
Any agent that completes work can generate the handoff for the next agent,
regardless of the host environment or available tooling.

---

## Template Generation Modes

| Mode               | Pattern                                          | When to Use           |
| ------------------ | ------------------------------------------------ | --------------------- |
| **Full Cascade**   | Agent₁ generates ALL handoffs (stages 2-N)       | Predictable pipelines |
| **One-Step**       | Each agent generates only the next handoff       | Adaptive workflows    |
| **Unsealing**      | Sealed handoffs passed forward, unsealed in turn | Complex unknowns      |
| **Cached + Delta** | Core prompts reused, agents add customization    | Cyclic pipelines      |

### Full Cascade (Recommended Default)

```text
Agent₁ produces:
├── artifact₁.md
├── HANDOFF_TO_AGENT2.md (full template)
├── HANDOFF_TO_AGENT3.md (skeleton — less detail)
└── HANDOFF_TO_AGENT4.md (skeleton — minimal)

Each subsequent agent:
→ Execute handoff template
→ Parameterize next handoff with results
→ Enrich with external data
→ Pass forward
```

---

## Template Detail Levels

| Level             | Contents                         | When                 |
| ----------------- | -------------------------------- | -------------------- |
| **Skeleton**      | Headers + brief instructions     | Capable downstream   |
| **Full**          | Complete, needs parameterization | Limited downstream   |
| **Parameterized** | Template with `{{placeholders}}` | Structured injection |
| **Enriched**      | Full + attached context/files    | Complex domain       |

---

## Breadcrumb Patterns

Leave markers in generated artifacts for the next agent or session:

```text
Universal:      <!-- TODO(next-agent): [specific instruction] -->
Continuation:   <!-- CONTINUE: [checkpoint marker] -->
Handoff:        <!-- HANDOFF: [receiving agent] [instruction] -->
Code:           # TODO(next-agent): [instruction]
Slots:          {{INJECT: results}} {{PARAM: requirements}} {{PIPELINE: name}}
```

---

## Pipeline Composition

Continuations and handoffs compose into pipelines:

| Pattern         | Structure                | Use Case                      |
| --------------- | ------------------------ | ----------------------------- |
| **Sequential**  | P₁ → P₂ → P₃             | Phased delivery               |
| **Nested**      | P₁(contains P₂) → P₃     | Research-then-implement       |
| **Parallel**    | P₁ ∥ P₂ → merge → P₃     | Multiple analyses → synthesis |
| **Iterative**   | P₁ → P₂ → P₁↻ until done | Refine cycles                 |
| **Conditional** | P₁ → (if X: P₂ else P₃)  | Branch on results             |

See @references/pipeline-patterns.md for detailed pipeline design patterns.

---

## Decision Flow

```text
Task complete in current session?
  ↓ NO
Same agent continues?
  ├─ YES → GENERATE CONTINUATION
  │        Detect environment → use most native mechanism
  │        Include: artifacts + checkpoint + next steps
  │
  └─ NO  → Different agent needed?
           ↓ YES
           → GENERATE HANDOFF
           Detect environment → use most native mechanism
           Full cascade when possible
           Include: artifacts + prompt(s) + breadcrumbs
```

---

## Anti-Patterns

```text
✗ Ending without continuation/handoff when work remains
✓ Every session boundary has a complete continuation OR handoff

✗ Vague "continue from here" without explicit prompt
✓ Templates parameterized with actual results and specific next steps

✗ Missing artifact references in continuation/handoff
✓ Artifacts contain expansion markers and breadcrumbs

✗ Using "continuation" when a different agent is needed
✓ Same agent → continuation; different agent → handoff

✗ Ignoring native environment mechanisms (task lists, sub-agents)
✓ Detect environment first, use the most native mechanism available

✗ Assuming all environments support file creation
✓ Graceful degradation: task tools → files → chat output (always works)

✗ Halting because no file system or task tools are available
✓ Chat output is always possible — the skill never fails to produce output
```

---

## Trigger Checklist

Before completing any complex task, verify:

```text
- [ ] Is significant work remaining?
- [ ] Am I at a natural phase boundary?
- [ ] Is context usage high or approaching limits?
- [ ] Would a fresh session improve quality?
- [ ] Does remaining work need different capabilities?

IF ANY checked → generate continuation or handoff
```
