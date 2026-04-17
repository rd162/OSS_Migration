# Sub-Agent Dispatch, Gates, Anti-Patterns, and Composition Reference

Extended reference for adversarial-thinking.
Loaded on demand for dispatch details, environment adaptation, and enrichment.

---

## Table of Contents

1. [Architecture Diagram](#architecture-diagram)
2. [Why This Architecture](#why-this-architecture)
3. [Sub-Agent Dispatch Patterns](#sub-agent-dispatch-patterns)
4. [Environment Adaptation](#environment-adaptation)
5. [Model Selection for Sub-Agents](#model-selection-for-sub-agents)
6. [Compositional Gates](#compositional-gates)
7. [Execution Mode Decision Tree](#execution-mode-decision-tree)
8. [Phase 3: Extended Condorcet Details](#phase-3-extended-condorcet-details)
9. [Anti-Patterns](#anti-patterns)
10. [Composition with Other Capabilities](#composition-with-other-capabilities)
11. [Practical Guidance from Testing](#practical-guidance-from-testing)

---

## Architecture Diagram

```text
┌──────────┐    full critique     ┌──────────────┐
│  Master   │◄───────────────────►│Critique Agent │ (sees all 3 candidates)
│Orchestrator│    full critique    │  + research   │
└─────┬─────┘───────────────────►└──────────────┘
      │
      ├─── full critique ──►┌─────────────────┐
      │                     │ Solution Author A│ (sees only candidate A)
      │                     │   + research     │
      │                     └─────────────────┘
      ├─── full critique ──►┌─────────────────┐
      │                     │ Solution Author B│ (sees only candidate B)
      │                     │   + research     │
      │                     └─────────────────┘
      └─── full critique ──►┌─────────────────┐
                            │ Solution Author C│ (sees only candidate C)
                            │   + research     │
                            └─────────────────┘
```

---

## Why This Architecture

### Why critique sees all 3

Cross-solution assessment requires comparative context.
A critique agent seeing only one candidate cannot identify
that candidate B already solved a weakness present in A,
or that all three share a common blind spot.

### Why solution authors isolate

Independent improvement prevents convergence toward a single design.
If Author A sees critique of B and C,
it anchors toward avoiding their weaknesses
rather than strengthening its own approach.

### Why no role-game framing

LLMs turn adversarial roles into performative games —
"attacker" agents exaggerate flaws for dramatic effect,
"defender" agents become dismissive rather than analytical.
Serious professional framing (compliance review, improvement task)
produces rigorous, substantive output.

---

## Sub-Agent Dispatch Patterns

### Syntax

```text
Spawn sub-agents (parallel or sequential):

1. **[agent-name]**: [task description]
   - Give it: [context handed to sub-agent]
   - Returns: [expected output]

2. **[agent-name]**: ...

Merge: [how orchestrator combines results]
```

### Modes

| Mode                | Behavior                                      |
| ------------------- | --------------------------------------------- |
| `parallel`          | All labels concurrent, single-turn each       |
| `sequential`        | Labels run one after another                  |
| `parallel + routed` | Concurrent with master routing between agents |

`parallel + routed` is the primary mode for critique/author cycles.
Critique agent runs once (seeing all candidates),
then master routes full critique to each author in parallel.

### High-Stakes Domain Extension

For high-stakes domains (medical, legal, financial, safety-critical):

```text
Both critique agent and solution authors should:
  1. Perform deep research before producing output
  2. Apply forward-consequence reasoning (trace implications 2-3 steps ahead)
  3. Cite authoritative sources (T1/T2 tier)
```

---

## Environment Adaptation

The skill uses natural-language sub-agent instructions that work across
any environment with agent-dispatch capabilities. Detect what your
environment provides and use the highest-isolation mode available.

| Capability level       | Parallel? | Routing? | Notes                              |
| ---------------------- | --------- | -------- | ---------------------------------- |
| Concurrent sub-agents  | Yes       | Yes      | Best: full isolation + parallel    |
| Sequential sub-agents  | No        | Yes      | Good: isolation preserved, serial  |
| Single-turn sub-agents | Yes       | No       | Isolation but no iterative routing |
| No sub-agents (inline) | No        | No       | Approximated via context fencing   |

**Degradation order:**

1. Parallel + routed (full isolation + concurrent refinement)
2. Parallel single-turn (good isolation, no iterative routing)
3. Sequential + routed (routing preserved, no parallelism)
4. Sequential single-turn (minimal isolation)
5. Inline with context fencing (no isolation, mark output DEGRADED)

---

## Model Selection for Sub-Agents

Different agent roles have different cognitive demands.
When the environment allows model selection per sub-agent,
use the strongest model where reasoning depth matters most
and faster models where the task is more mechanical.

| Agent Role | Cognitive Demand | Model Tier | Rationale |
| --- | --- | --- | --- |
| **Critique Agent** | Highest | Strongest (opus-class) | Weak critique → weak refinement; this agent is the quality bottleneck |
| **Solution Authors** | High | Strongest (opus-class) | Must research counter-evidence and produce creative revisions |
| **Generation (Phase 1)** | High | Strongest (opus-class) | Divergent exploration requires deep domain understanding |
| **Condorcet Voters (Standard+)** | High | Strongest (opus-class) | Research-armed voting with claim verification needs strong reasoning |
| **Condorcet Voters (Quick)** | Moderate | Fast (sonnet-class) | Quick-depth comparisons are straightforward requirement matching |
| **Inverse Spec Recovery** | Moderate | Fast (sonnet-class) | Structured extraction from solution text is well-suited to faster models |

**When model selection is unavailable:**
Use the default model for all agents. Isolation alone
(separate contexts preventing self-play bias) is worth
the dispatch overhead even without model differentiation.

**Cost optimization at scale:**
At Quick depth with 7 agents, using fast models for Condorcet voters
reduces total pipeline cost by ~20-30% with minimal quality impact.
At Deep/Maximum depth, use the strongest model for all agents —
every phase involves research and complex reasoning.

---

## Compositional Gates

Gates enforce capability dependencies between phases.
Each gate declares what is needed and what evidence proves it —
not a specific tool name. This keeps the skill portable.

### Gate Syntax

```text
GATE(label):
  REQUIRES: [capability description]
  PREFERRED: [recommended capability if available]
  EVIDENCE: [artifact that proves requirement met]
  FALLBACK: [degraded path if capability unavailable]
```

### Gates in Think-Deeper

| Phase | Gate                  | Requires                         | Evidence                          | Fallback                |
| ----- | --------------------- | -------------------------------- | --------------------------------- | ----------------------- |
| 0     | Requirements          | Requirements inference           | Structured specification          | Inline extraction       |
| 0     | Knowledge Saturation  | Domain research                  | Enriched requirements w/ sources  | Training knowledge only |
| 1     | Candidate Generation  | 3 divergent solutions            | 3 distinct candidates             | Model generates all     |
| 2     | Isolation             | Separate agent sessions          | Independent execution contexts    | Context fencing         |
| 2     | Research              | Search/research tools            | Cited sources in output           | Training knowledge only |
| 2.5   | Convergence Detection | Pattern analysis (optional)      | Termination signal detected       | Fixed iteration count   |
| 2.5   | Citation Verification | Source validation (optional)     | Citations checked against sources | Trust agent citations   |
| 3     | Pairwise Isolation    | Separate comparison sessions     | Independent comparison contexts   | Sequential fencing      |
| 3     | Enriched Requirements | Requirements from critique agent | Enriched reqs (not original Ph 0) | Original Phase 0 reqs   |

### Gate Verification

```text
FOR EACH gate in current phase:
  evidence present? → check artifacts match EVIDENCE spec
    YES → gate OPEN → proceed
    NO  → scan available capabilities → invoke if found → re-check
      → IF still NO → execute FALLBACK (degrade gracefully)
```

Why gates instead of direct tool references:

- **Portability:** Same skill works across environments with different tools
- **Decoupling:** Parent skill does not hardcode child skill identity
- **Auditability:** Gates create explicit checkpoints in execution trace
- **Graceful degradation:** Missing capability triggers fallback, not halt

---

## Execution Mode Decision Tree

```text
∆1: Detect sub-agent mechanism
     ├─ Parallel support?
     │   YES → Routing support?
     │          YES → mode = PARALLEL + ROUTED
     │          NO  → mode = PARALLEL (single-turn)
     │   NO  → Sequential available?
     │          YES → mode = SEQUENTIAL
     │          NO  → mode = INLINE (context fencing)
     │
∆2: Dispatch per mode:
     ├─ PARALLEL + ROUTED:
     │   Critique agent → all 3 candidates (one session)
     │   Master routes full critique → 3 authors (parallel)
     │   Observe termination → repeat or proceed
     │
     ├─ PARALLEL (single-turn):
     │   Critique + authors run single round each
     │   No iterative routing
     │
     ├─ SEQUENTIAL:
     │   Critique → Author A → Author B → Author C
     │   Full critique routed to each in turn
     │
     └─ INLINE:
         All in main thread
         Context fence between critique and each author
         Explicit "consider ONLY candidate X" instructions
```

---

## Phase 3: Extended Condorcet Details

The core Condorcet protocol is in SKILL.md. The comparison prompt template
is in `templates.md § Condorcet`. This section covers extended details.

### Research-Armed Condorcet (Standard+ depth)

Condorcet voters research key claims before selecting a winner.
A voter that trusts citations without verification
can be misled by a well-cited but wrong solution.

```text
For each pair of solutions being compared:
  1. Identify the 2-3 most consequential claims in each solution
     (claims that, if wrong, would change which solution is better)
  2. Verify these claims using available search tools
  3. Factor verification results into the comparison
     Verified claims > unverified > refuted
```

At Quick depth, skip research — compare on substance only.
At Maximum depth, verify all cited sources, not just top 2-3.

### Why Not Process Metadata

The comparison judges substance, not process.
Including process metadata (rounds survived, attack logs) biases voters
toward candidates that survived more rounds rather than candidates with better content.
Different execution produces different winners when voters see substance vs. metadata —
this validates that the correction matters.

### Why Enriched Requirements

The critique agent discovers implicit requirements during research —
domain constraints, safety considerations, and standards the original request did not state.
Solutions were refined against these. Voters using only the original request
would miss the dimensions that drove the refinements.

### Tie-Breaking

If two candidates tie on win count:

1. Prefer the one with stronger termination signal (HELD > CONVERGE)
2. Prefer the one with higher domain appropriateness
3. If still tied, prefer the simpler candidate

---

## Anti-Patterns

```text
MOST COMMON FAILURE: Completing Phase 0+1 then skipping to Phase 4
  The agent does the easy inline work then shortcuts the expensive sub-agent phases.
  This produces self-play — no better than a first draft.
  → Execute all phases. Reduce rounds at Quick depth, but dispatch all agents.

Self-play: one agent playing both roles in the same session
  LLMs do not genuinely self-critique (Huang et al., ICLR 2024).
  → Use separate agent sessions.

Role-game framing: telling agents they are "attackers" or "defenders"
  Turns into theatrical performance with shallow output.
  → Use professional framing: "assess compliance" / "improve based on feedback."

Sequential critique: reviewing candidates one at a time
  Loses cross-candidate insight — shared gaps go undetected.
  → Critique agent sees all 3 simultaneously.

Hardcoded cognitive strategies for candidate generation
  Produces the same divergence axes regardless of domain.
  → Infer strategies dynamically from the problem's tensions.

Omitting anti-requirements (positive-only assessment)
  Critique misses harmful patterns, only checks for missing requirements.
  → Include failure modes as anti-requirements.

Treating SOFTENING as convergence
  Critique stopped pressing, but solutions haven't genuinely improved.
  → Distinguish: SOFTENING (intervene) vs. CONVERGE (terminate).

Summarizing critique when routing to authors
  Summarization loses issues, wastes a round when critique re-discovers them.
  → Route full critique per candidate.

Authors revising without researching feedback
  Accepts or rejects claims without evidence.
  → Authors research feedback claims before improving.

Instructing termination ("stop when good enough")
  Agents optimize for ending rather than quality.
  → Let termination emerge from context: CONVERGE, DRIFTING, HELD.

Condorcet agents receiving process metadata
  Biases toward endurance rather than quality.
  → Condorcet receives only refined solutions + enriched requirements.

Generating candidates in 3 separate contexts
  No cross-awareness → overlapping rather than divergent solutions.
  → Generate all 3 in the same context.

Inline execution when sub-agents are available
  Isolation is what makes this pipeline valuable.
  → Use the highest-isolation mode the environment supports.

Running all 3 pairwise comparisons in one context
  Ordering bias contaminates later comparisons.
  → Isolate each comparison in a separate agent.
```

---

## Composition with Other Capabilities

This skill benefits from — but does not require — other capabilities:

| Phase | Preferred Capability         | What It Provides                                 | Fallback Without It              |
| ----- | ---------------------------- | ------------------------------------------------ | -------------------------------- |
| 0     | Knowledge saturation         | Research-informed enriched requirements          | Inline requirements extraction   |
| 0     | Requirements inference       | Structured specification from enriched knowledge | Inline extraction from request   |
| 0     | Anti-requirements discovery  | Documented failure modes as negative constraints | Positive-only requirements       |
| 1     | Cognitive strategy inference | Problem-specific divergence axes                 | Generic structural variation     |
| 2     | Sub-agent orchestration      | 4-agent review with master routing               | Sequential with context fencing  |
| 2     | Session continuation         | Multi-turn critique context accumulation         | Fresh context each round         |
| 2.5   | Citation verification        | Verified sources before Condorcet                | Trust citations at face value    |
| 2.5   | Inverse spec recovery        | Fresh-agent intent reconstruction per solution   | Trust solutions at face value    |
| 3     | Sub-agent orchestration      | Unbiased pairwise comparison                     | Sequential with context fencing  |
| 3     | Enriched requirements        | Voters see research-discovered requirements      | Voters see original request only |
| After | Continuation/handoff         | Session boundary management                      | Complete in current session      |

Every capability in "Preferred" improves quality. None are required.
The pipeline completes via graceful degradation.

---

## Practical Guidance from Testing

Findings from real execution with sub-agents:

- **Route full critique to authors, never summarize.** Summarization loses issues;
  the critique re-discovers them next round, wasting tokens.
- **Research-armed authors produce stronger revisions.** When authors verify
  feedback claims, they confirm valid issues, correct inaccurate ones,
  and find deeper solutions the critique did not consider.
- **Knowledge-saturated critique finds flaws pure reasoning cannot.** The critique's
  initial research discovers real-world evidence (SDK changes, debunked theories,
  regulatory updates) that transforms assessment from theoretical to evidence-based.
  Research happens once in Round 1.
- **2-3 rounds is typical.** Most candidates reach CONVERGE or HELD by round 2.
- **Cross-candidate critique is strictly better than sequential.** Seeing all 3
  simultaneously reveals shared blind spots.
- **DRIFTING usually appears at round 2.** When critique shifts from structural to
  edge-case flaws, terminate unless maximum depth is requested.
- **Author pivots are valuable.** If an author abandons its approach and proposes
  a new one, the original had a fundamental flaw. Note the pivot for Condorcet voters
  — the pivoted solution is un-critiqued.
- **Different execution produces different winners.** When Condorcet voters see
  substance instead of process metadata, outcomes change. This validates
  that the metadata-exclusion rule matters.
