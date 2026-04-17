---
name: adversarial-thinking
description: Produces rigorously stress-tested solutions through adversarial exploration. Generates divergent approaches, battle-tests each via isolated blind-attack dialogues between attacker and defender agents, then selects the strongest through pairwise comparison. Returns one recommended solution and one alternative. Use when the user asks to "think deeper", "think harder", "ultrathink", "deep research", "research deeply", "research this carefully", "give me a really good answer", "explore alternatives", "I need the best approach", or when the request is naturally high-stakes — architecture decisions, strategy choices, complex trade-offs, important designs, or any question where a first-draft answer risks missing critical flaws. Composes with deep-research-t1 when both deep knowledge gathering and adversarial solution refinement are needed.
version: "8.0"
metadata:
  author: rd162@hotmail.com
  tags: adversarial-refinement, blind-attack, solution-quality, deep-thinking, cross-platform
---

# Adversarial Solution Refinement

Explore divergent approaches, battle-test each via isolated critique/author dialogues,
select the strongest through pairwise comparison,
deliver one recommended solution and one alternative.

---

## Depth Configuration

| Depth        | Trigger                                 | Research    | Ph2 Rounds | Ph2.5              | Agents |
| ------------ | --------------------------------------- | ----------- | ---------- | ------------------ | ------ |
| **Quick**    | "quick take", "brief", "just compare"   | 1-2 queries | 1          | Skip               | 7      |
| **Standard** | Default                                 | 3-5 queries | 2-3        | Convergence only   | 7      |
| **Deep**     | "think deeply", "thorough", high-stakes | 5-8 queries | 3-5        | Conv + cite + inv  | 10     |
| **Maximum**  | "exhaustive", "ultrathink"              | Deep        | Until conv | All + cross-pollin | 10     |

Research scales with depth because shallow domains need fewer queries to saturate,
while high-stakes domains have more failure modes to discover.
Round counts reflect observed convergence patterns: most candidates stabilize by round 2-3;
deep/maximum depth allows pursuit of structural issues that surface later.

Detect depth from the user's language. Track remaining budget and downgrade mid-pipeline if needed.

---

## Termination

| Signal   | Condition                                            | Action                                         |
| -------- | ---------------------------------------------------- | ---------------------------------------------- |
| COMPLETE | Phase 4 output produced (winner + runner-up + trace) | Deliver to user                                |
| DEGRADED | A phase lacked sub-agent isolation                   | Warn user, proceed with best-effort output     |
| TIMEOUT  | Token budget exhausted mid-pipeline                  | Create continuation artifact at phase boundary |

---

## Step 1: Detect Execution Mode

Isolation is what separates this pipeline from a first draft — without separate agents,
the critique softens its own critiques and Condorcet voters inherit the master's bias.
Detect the best available sub-agent mechanism before proceeding.

```text
1. Check visible tool list for any sub-agent / agent-dispatch capability.
2. If a tool-discovery mechanism exists (e.g., ToolSearch), probe for
   agent-spawning tools before concluding none exist — some environments
   defer tool registration until discovery.
3. Classify:
   PARALLEL    — concurrent sub-agents available (preferred)
   SEQUENTIAL  — sub-agents available, one at a time
   INLINE      — no sub-agents; use context fencing, mark output DEGRADED
```

Prefer the highest-isolation mode available.
INLINE approximates the pipeline but loses the isolation that prevents self-play,
so use it only when sub-agents are genuinely unavailable.

---

## Step 2: Process Overview

```text
Phase 0  → Research domain, infer enriched requirements + anti-requirements
Phase 1  → Infer cognitive strategies, generate 3 divergent candidates
Phase 2  → Critique/author review — 4 agents (1 critique + 3 authors), master-routed
Phase 2.5 → Post-refinement checks (depth-dependent)
Phase 3  → Condorcet pairwise comparison — 3 agents, enriched requirements
Phase 4  → Output winner + runner-up
```

---

## Phase 0: Research Domain + Infer Requirements

Research the domain before inferring requirements — otherwise the critique agent
becomes the first to discover implicit requirements that should have shaped candidates.

### 0.1 Domain Research

Identify the domain and execute research queries (count per depth table above) covering:
best practices, known pitfalls, domain constraints the user may not have stated.
For high-stakes domains, trace forward consequences (what goes wrong if advice is incorrect).

### 0.2 Infer Requirements

Use a requirements-inference capability if available; otherwise extract inline from
the user's request combined with research findings.

Structure requirements as MGPC where possible —
Mission (terminal value), Goals (concrete objectives),
Premises (assumptions that must hold), Constraints (hard/soft limits).
This structure gives the critique agent specific categories to probe:
unmet Goals, violated Constraints, false Premises.

Produce:

- **Enriched requirements registry** — structured as MGPC when feasible,
  with explicit + research-discovered requirements and sources.
- **Anti-requirements registry** — failure modes and anti-patterns the solution should avoid.
  Format: `[AR-id]: Solutions should not [pattern] | Source: [ref] | Consequence: [impact]`.
  Anti-requirements tell the critique what failure modes to probe — the ones pure reasoning
  misses because they require domain knowledge to recognize.
- **Domain research summary** — key findings shared with the critique agent to avoid redundant research.

---

## Phase 1: Generate 3 Divergent Candidates

The enriched requirements map to multiple valid solutions —
each candidate explores a different region of the solution space.
Divergence isn't arbitrary: it comes from different weightings of
competing requirements (e.g., simplicity vs. extensibility,
speed vs. safety, convention vs. innovation).

Generate all 3 in the same context so each candidate is aware of prior ones and can
deliberately diverge. Cross-awareness drives divergence; separate contexts produce overlap.

Use the **generation prompt template** from `references/templates.md § Generation`.
The template instructs the model to:

1. Infer 3 cognitive strategies grounded in the specific problem's tensions
   (not generic labels — the strategies emerge from competing requirements,
   especially from tensions between Goals and Constraints or between
   hard and soft constraints that pull in different directions).
2. Generate one candidate per strategy, varying structure, granularity, and tone.
   Varying these secondary axes alongside the primary strategy lens prevents
   candidates that differ in approach but look identical in form.

---

## Phase 2: Critique/Author Review

Each candidate is stress-tested through dialogue between a critique agent and
isolated solution authors. The master orchestrates routing.

### Why Isolation Matters

A single agent playing both roles softens its own critiques — LLMs do not genuinely
self-critique (Huang et al., ICLR 2024; Madaan et al., NeurIPS 2023).
Role-game framing ("you are the attacker") produces theatrical rather than substantive
output. Instead, frame agents with serious professional tasks: the critique agent
documents non-compliance; solution authors research feedback and improve.

### Agent Architecture (4 agents)

```text
CRITIQUE AGENT (one session, receives all 3 candidates simultaneously)
  — Researches domain, documents unmet requirements and anti-requirement violations
  — Seeing all 3 enables cross-candidate gap detection that sequential review misses
  — Same session preserved across rounds (context accumulates)

SOLUTION AUTHOR A (isolated session, receives only Candidate A + critique for A)
SOLUTION AUTHOR B (isolated session, receives only Candidate B + critique for B)
SOLUTION AUTHOR C (isolated session, receives only Candidate C + critique for C)
  — Each researches feedback claims, then improves their solution
  — Isolation prevents convergence toward a single design
```

### Routing Protocol

```text
Round 1:
  Dispatch critique agent with all 3 candidates + enriched requirements
    → critique researches domain, produces per-candidate compliance assessment
  Master routes FULL critique to each author (route per-candidate section only,
    but preserve every issue and citation — summarization loses issues
    that waste a round when the critique re-discovers them)
    → each author researches claims, improves solution

Round 2+:
  Master sends all 3 revised solutions to critique (same session):
    "Identify NEW unmet requirements in the revised solutions."
    → critique produces updated assessment → master routes → authors improve
  Repeat until termination signal observed.
```

Use prompt templates from `references/templates.md § Critique` and `§ Author`.

### Termination (Observed, Not Instructed)

The master observes agent output for signals — agents are never told when to stop,
because instructed termination causes agents to optimize for ending rather than quality.

| Signal        | Observation                                              | Action       |
| ------------- | -------------------------------------------------------- | ------------ |
| CONVERGE      | Critique recycling previous points, no novel issues      | Terminate    |
| DRIFTING      | Issues shifting from structural to edge-case             | Terminate    |
| SOFTENING     | Critique accommodating rather than assessing (see below) | Intervene    |
| AUTHOR-HELD   | Author states "requirements met per [evidence]"          | Note quality |
| AUTHOR-FAILED | Author acknowledges fundamental gap                      | Note flaw    |

**Combining signals:** converge + held = strong candidate; drifting + held = adequate;
author-failed = fundamental flaw worth noting for Condorcet voters.
End a round when all 3 candidates reach a signal or budget is exhausted.

### Sycophancy Collapse (SOFTENING)

Distinct from convergence (issues genuinely exhausted) and drifting (diminishing returns).
Signs: praise before findings, hedging ("might benefit from..."), premature resolution,
scope shrinking despite unchanged solutions, coaching tone.
Intervene by sending a same-session prompt listing requirements the critique stopped addressing.
If it persists, flag for Condorcet voters.

---

## Phase 2.5: Post-Refinement Checks

Run depth-dependent checks between Phase 2 and Phase 3.
At Standard depth, only convergence detection runs. Read `references/phase-detail.md`
for full protocols at Deep/Maximum depth.

**Convergence detection** (all depths): Compare refined solutions pairwise.
If all 3 share >80% structural overlap, merge into one and skip Condorcet —
comparing near-identical solutions produces meaningless distinctions.
If 2 converge but 1 is distinct, merge the pair and run a single comparison.

**Citation verification** (Deep+): Mark each citation VERIFIED / UNVERIFIED / MISREPRESENTED.
Attach summary to Condorcet metadata.

**Inverse specification recovery** (Deep+): Spawn 3 fresh agents (no prior context),
each reconstructing requirements from one solution alone. Compare recovered spec
against Phase 0 registry — high recovery = well-aligned; low recovery = superficial compliance.

**Cross-pollination** (Maximum only): Share key innovations (not full solutions)
across authors, then re-check convergence.

---

## Phase 3: Condorcet Pairwise Comparison

Spawn 3 sub-agents (one per pair), each comparing two refined solutions against
the enriched requirements registry. Isolation prevents ordering bias.

```text
compare-AB: full A' + full B' + enriched requirements → winner?
compare-AC: full A' + full C' + enriched requirements → winner?
compare-BC: full B' + full C' + enriched requirements → winner?
```

Use the enriched requirements (not original Phase 0) — the critique agent discovers
implicit requirements during research, and solutions were refined against them.
Voters using only the original request miss the dimensions that drove refinements.

Condorcet agents receive only the full refined solutions + enriched requirements.
They do not receive critique logs, round counts, or process metadata — the comparison
judges substance, not process. Including survival metadata biases toward endurance
rather than quality.

At Standard+ depth, Condorcet voters research key claims before voting —
a well-cited but wrong solution can mislead voters who trust citations at face value.

Use the comparison prompt template from `references/templates.md § Condorcet`.

**Tally:** Most wins = Winner. Second = Runner-up. Third = Rejected.
Tie-break: prefer stronger termination signal, then higher domain fit, then simpler solution.

---

## Phase 4: Output

Before producing output, verify that Phase 2 and Phase 3 sub-agents were actually
dispatched (not simulated inline). If any are missing, go back and execute them.
The value of this pipeline is isolation — skipping sub-agent phases and declaring
a winner from inline reasoning is self-play, producing output no better than a first draft.

```text
RECOMMENDED → [Winner]: [1-line summary] | Best for: ... | Trade-off: ...
ALTERNATIVE → [Runner-up]: [1-line summary] | Best for: ... | Trade-off: ...
SELECTION GUIDANCE → if [criterion] → Recommended; else → Alternative
```

Suppress runner-up when: user requested one option, winner is dramatically stronger,
or runner-up was TIMEOUT. Hide raw candidates, traces, and rejected unless requested.

---

## Reference Files

| File                              | When to read                                              |
| --------------------------------- | --------------------------------------------------------- |
| references/templates.md           | Before dispatching any sub-agent — contains prompt        |
|                                   | templates for critique, author, generation, and Condorcet |
| references/delegate-and-gates.md  | Dispatch patterns, environment adaptation, gates,         |
|                                   | anti-patterns, composition table                          |
| references/phase-detail.md        | Phase 2.5 full protocols (Deep/Maximum), execution trace  |
| references/academic-references.md | Supporting literature for design decisions                |
