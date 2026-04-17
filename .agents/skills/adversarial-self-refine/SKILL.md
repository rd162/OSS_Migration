---
name: adversarial-self-refine
description: Iteratively improve any solution through blind assertive critique until the model defends or converges. Uses isolated sub-agents (CRITIC + AUTHOR) so critique is never biased by authoring context. Falls back to single-thread when sub-agents unavailable (DEGRADED). Use when refining drafts, code, prompts, designs, plans, or any artifact that benefits from iterative quality improvement. Applies a recursive functor pattern with emergent termination detection.
version: "3.0"
metadata:
  author: rd162@hotmail.com
  tags: prompt-engineering, self-refine, iterative-improvement, quality, multi-agent
---

# Adversarial Self-Refine Loop

Iteratively improve any solution via **isolated** blind assertive critique.
The CRITIC agent has no memory of authoring the solution —
producing sharper critique than same-context self-critique.
The AUTHOR agent receives critique cold, without defensive attachment.

**Why isolation matters:**

- Same-context critique: the model "knows" why it made each choice → biased toward early defense
- Isolated CRITIC: genuinely no authoring context → cannot rationalize the original decisions → sharper critique
- Isolated AUTHOR: receives critique cold → no sunk-cost defense → more honest revision

**Why blind assertive critique works better than "what could improve?":**

- "What could improve?" → model ALWAYS finds something → loop never terminates
- "This is flawed. X is missing." → model either AGREES (revises) or DISAGREES (defends)
- Defense = natural convergence signal. The model arguing FOR its solution
  means it has reached a fixed point — further critique would be circular.
- The "blind" part is token-efficient: you don't verify the critique first.
  The model verifies by accepting (revise) or rejecting (defend).

## When to Use

- Refining drafts, code, prompts, designs, plans, or any artifact
- Polishing a selected candidate after multi-candidate comparison
- Strengthening a seed solution before branching into alternatives
- Any task where iterative quality improvement is worth the token cost

## When NOT to Use

- Single-pass tasks where first output is sufficient (low stakes)
- Tasks requiring external verification (use tool-based validation instead)
- Creative divergence (self-refine converges — use candidate generation first)
- Tight token budgets where even 2 iterations exceed the allowance
- Tasks where the user needs multiple alternatives (use candidate generation instead)

---

## Step 0: Execution Mode Detection (MANDATORY)

**Always run this before starting the loop.**

```text
∆0: Detect available sub-agent mechanism
  Step 1: Check visible tool list for Agent, spawn_agent, Task
  Step 2: If ToolSearch available, ALWAYS probe "Agent spawn subagent"
          (Claude Code defers Agent tool — doesn't appear in visible list until discovered)
  Step 3: Classify → PARALLEL | SEQUENTIAL | INLINE
```

| Mode           | Condition                          | Quality   | Notes                              |
| -------------- | ---------------------------------- | --------- | ---------------------------------- |
| **PARALLEL**   | Sub-agents + concurrent dispatch   | Best      | CRITIC and AUTHOR in separate sessions |
| **SEQUENTIAL** | Sub-agents, one-at-a-time          | Good      | CRITIC first, then AUTHOR          |
| **INLINE**     | No sub-agents available            | DEGRADED  | Single-thread fallback, mark output |

**HARD RULE:** If sub-agents are available, they MUST be used.
Running INLINE when sub-agents are available produces no adversarial benefit —
same-context critique is biased by authoring memory.

---

## Core Principle

```text
R: Sol → Sol
R(s) = Author(Critic(s))   ← two isolated agents

Fixed point: R(s*) ≅ s*  (defense emerged OR converged)
```

Each iteration: MASTER sends sₙ to CRITIC (isolated) → routes critique to AUTHOR (isolated) → collects sₙ₊₁.
Termination is **observed by MASTER**, never instructed to sub-agents.

## Three Governing Rules

| Rule               | Implementation                                               | Why                                                                      |
| ------------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Assertive Critique | Assert "X is flawed" — NOT "What could improve?"             | Forces a binary response: revise (agree) or defend (disagree)            |
| Blind Critique     | Assert "requirement unmet" — don't verify the claim yourself | The AUTHOR does the verification; saves tokens, avoids confirmation bias |
| Isolated Agents    | CRITIC has no authoring history; AUTHOR has no critique history | Prevents both biased critique and sycophantic defense                |

---

## Agent Architecture

### MASTER (current conversation)
- Holds the requirements, current solution sₙ, and loop state
- Spawns CRITIC and AUTHOR as isolated sub-agents each round
- Routes FULL critique output to AUTHOR (never summarize — lossy)
- Observes termination signals from AUTHOR output
- Never instructs "stop if good enough"

### CRITIC agent (isolated sub-agent, one per round)
- Receives: requirements + current solution sₙ
- Does NOT know: it will be responded to, that an AUTHOR exists
- Task: assert compliance failures as facts, not questions
- Output: numbered list of unmet requirements and structural flaws
- Cognitive mode: **declarative assessment** — evaluating what IS against what SHOULD BE

### AUTHOR agent (isolated sub-agent, one per round)
- Receives: current solution sₙ + FULL critique output
- Does NOT know: critique came from a separate CRITIC agent
- Does NOT know: it is being "tested" or that a loop is running
- Task: improve the solution addressing ALL critique points
- Output: revised solution sₙ₊₁
- Cognitive mode: **procedural revision** — applying skills to transform the solution

**Why cognitive mode separation matters:**
The CRITIC's job is declarative — it evaluates what IS against what SHOULD BE.
The AUTHOR's job is procedural — it applies transformation skills to improve.
When these modes share context, the declarative assessment gets contaminated
by procedural memory ("I chose this approach because...") — producing
rationalization instead of genuine evaluation. Isolation keeps them clean.

**Critical framing for AUTHOR:** Do NOT frame as "defend or revise."
Frame as: "This feedback was received on your solution. Improve it."
The defense signal emerges naturally — do not instruct it.

---

## The Loop

```text
s₀ ← initial solution

REPEAT {
  CRITIC ← spawn isolated sub-agent
  critique ← CRITIC(requirements, sₙ)

  AUTHOR ← spawn isolated sub-agent
  response ← AUTHOR(sₙ, critique)          ← FULL critique, not summarized

  IF defense_detected(response): RETURN (response, DEFENSE)
  IF response ≈ sₙ:              RETURN (response, CONVERGE)
  sₙ₊₁ ← response
} UNTIL max_iter → RETURN (sₙ, TIMEOUT)
```

**⚠ NO EXIT PERMISSION:** Never include "if good enough, stop" in any sub-agent prompt.
MASTER observes termination — sub-agents never decide to stop.

---

## Termination Signals (Observed by MASTER in AUTHOR output)

| Signal   | Detection                                              | Confidence | Action            |
| -------- | ------------------------------------------------------ | ---------- | ----------------- |
| DEFENSE  | AUTHOR argues FOR the solution instead of revising     | HIGH       | ✓ STOP — done     |
| CONVERGE | sₙ₊₁ ≈ sₙ (output stabilized, similarity > 0.95)       | MEDIUM     | ✓ STOP — adequate |
| CYCLE    | sₙ ≅ sₖ where k < n-1 (revisiting earlier state)       | LOW-MED    | ✓ STOP — use best |
| TIMEOUT  | max_iter reached                                       | VARIES     | ✓ STOP — use last |

### Defense Markers (in AUTHOR output)

- "correct because..."
- "already handles..."
- "critique doesn't apply because..."
- "intentional design choice..."
- "justified by..."

When defense emerges, the AUTHOR has reached a fixed point.
This is the natural termination signal —
no instruction needed, the model's behavior tells you it's done.

### Sycophancy Watch (in CRITIC output, round 2+)

If CRITIC begins accommodating the solution rather than assessing it
(praise appearing, hedging language, scope shrinking), MASTER resets
the CRITIC context with the original requirements restated:
"These requirements were not met. Reassess from scratch."

---

## Sub-Agent Prompt Templates

Templates are in `references/templates.md` — read before dispatching any sub-agent.

Key rules (also documented in the templates file):
- Neither prompt contains any exit clause — MASTER observes termination
- AUTHOR is framed as "improve" not "defend or revise" — defense emerges naturally
- CRITIC is framed as compliance review, not role-play — produces substantive output

---

## Execution Mode Protocols

### PARALLEL mode (preferred)

Each round: spawn CRITIC → collect output → spawn AUTHOR (passing full critique) → collect output → check termination.
CRITIC and AUTHOR are in different rounds so they cannot be parallel within a round (AUTHOR depends on CRITIC output).
Between rounds, the next CRITIC can be spawned as soon as AUTHOR output is collected.

### SEQUENTIAL mode

Same as PARALLEL — CRITIC and AUTHOR are inherently sequential within a round.
No behavioral difference from PARALLEL for this skill.

### INLINE mode (DEGRADED — use only when no sub-agents available)

Run critique and revision in the same conversation thread.
Acknowledge the limitation: same-context critique is biased.
Mark output: `⚠ DEGRADED: running inline (no sub-agents available)`

```text
[INLINE CRITIQUE TURN]
REQUIREMENTS: [requirements]
CANDIDATE: [current solution]
Critique this candidate: 1) wrong? 2) missing? 3) over-engineered? 4) out of scope?

[INLINE REVISION TURN]
SOLUTION: [solution]
CRITIQUE: [critique]
Generate a revised solution addressing ALL critiques.
```

---

## Token Budget Guidelines

| Budget   | Max Iterations | Agents per round | Total agents     |
| -------- | -------------- | ---------------- | ---------------- |
| Tight    | 2-3            | 2 (CRITIC+AUTHOR)| 4-6              |
| Standard | 3-5            | 2 (CRITIC+AUTHOR)| 6-10             |
| Generous | 5-10           | 2 (CRITIC+AUTHOR)| 10-20            |

## Model Selection

When the environment allows per-agent model selection,
use the strongest model for AUTHOR (drives output quality)
and consider a faster model for CRITIC at tight budgets.
See `references/templates.md § Model Selection` for the full table.

## Anti-Patterns

```text
✗ Running INLINE when sub-agents are available
✓ Always use isolated agents — same-context critique is biased

✗ Summarizing critique before passing to AUTHOR
✓ Route FULL critique text — summarization is lossy

✗ "Critique the solution. If good enough, you may stop."
✓ "Critique the solution." — no exit clause, ever

✗ Framing AUTHOR as "defend or revise"
✓ "This feedback was received. Improve the solution."

✗ Running only one iteration
✓ Running until defense, convergence, or timeout

✗ Discarding weak iterations (all inform the process)
✓ Keeping the full trace for confidence assessment
```

## Composition Modes

Self-Refine composes with other skills and patterns:

| Mode                   | Pattern                                 | When to Use                        |
| ---------------------- | --------------------------------------- | ---------------------------------- |
| **Standalone**         | Self-Refine only                        | Simple tasks, tight token budget   |
| **Refine-Then-Branch** | Self-Refine seed → generate branches    | Strengthen seed before exploration |
| **Branch-Then-Refine** | Generate branches → Self-Refine winner  | Polish the selected candidate      |
| **Refine-Each-Branch** | Self-Refine each branch → compare all   | Maximum quality per candidate      |
| **Full Integration**   | Self-Refine at multiple pipeline stages | Highest quality, highest cost      |

This skill is commonly invoked by multi-candidate comparison workflows
(one invocation per candidate, in isolation).
It can also be used standalone for any artifact that benefits from polishing.

## Trace Format

Use compact notation for tracking refinement history:

```text
s₀→CRITIC[gap identified]→AUTHOR→s₁→CRITIC[flaw found]→AUTHOR→defense→s' (DEFENSE)
s₀→CRITIC[over-engineered]→AUTHOR→s₁≈s₀→s' (CONVERGE)
s₀→CRITIC[unclear]→AUTHOR→s₁→CRITIC[weak]→AUTHOR→s₂≈s₁→s' (CONVERGE)
```

Mark degraded runs: `(INLINE-DEGRADED)` at end of trace.

## Example

```text
Task: API endpoint design for order management
Mode: PARALLEL (sub-agents available)

s₀[REST basic]
  →CRITIC: "Missing state transitions, no idempotency"
  →AUTHOR→s₁[REST + state machine + idempotency keys]
  →CRITIC: "No audit trail, weak error taxonomy"
  →AUTHOR→defense: "Audit trail handled by middleware layer (intentional separation).
                    Error taxonomy covers all RFC 7807 cases."
  →s' (DEFENSE, HIGH confidence)
```

## Reference Files

| File | When to read |
| --- | --- |
| references/templates.md | Before dispatching any sub-agent — contains prompt templates and model selection guidance |
| references/academic-references.md | Supporting literature for design decisions |

## Environment Compatibility

| Environment              | Sub-agents      | Mode       | Notes                              |
| ------------------------ | --------------- | ---------- | ---------------------------------- |
| Claude Code              | Agent tool      | PARALLEL   | Probe with ToolSearch first        |
| Claude API (agentic)     | Tool use        | PARALLEL   | Spawn via tool calls               |
| GitHub Copilot / VS Code | None typically  | INLINE     | Mark DEGRADED                      |
| Cursor / Codex           | None typically  | INLINE     | Mark DEGRADED                      |
| Bare LLMs / manual       | None            | INLINE     | Run turns manually, mark DEGRADED  |
| Programmatic             | Parallel calls  | PARALLEL   | Implement critic/author as API calls |

## Formal Basis

The core loop R(s) = Author(Critic(s)) has grounding in established theory:

- **Fixed-point convergence:** The defense signal is a behavioral fixed point
  R(s*) ~ s* — grounded in Tarski's fixed-point theorem (1955)
  and iterative approximation (Kleene, 1952).
- **Isolation mandate:** LLMs cannot self-correct reasoning without
  external feedback (Huang et al., ICLR 2024). Multi-agent debate
  avoids Degeneration-of-Thought (Liang et al., EMNLP 2024).
- **Assertive critique:** Builds on Constitutional AI's principle-guided
  critique (Bai et al., 2022) and AI Safety via Debate (Irving et al., 2018).
- **Cognitive basis:** CRITIC operates on declarative assessment,
  AUTHOR applies procedural revision — mapping to ACT-R's
  declarative/procedural knowledge distinction (Anderson, 1983).

See `references/academic-references.md` for full citations and provenance.

## References

See `references/academic-references.md` for full citations and provenance.

Key references: Madaan et al. 2023 (Self-Refine), Huang et al. 2024 (self-correction limits),
Irving et al. 2018 (AI Safety via Debate).
