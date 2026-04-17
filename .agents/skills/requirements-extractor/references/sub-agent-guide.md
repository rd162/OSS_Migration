# Sub-Agent Guide — requirements-extractor

Patterns for parallelizing requirements extraction via sub-agents
when the input covers multiple independent domains or
when challenge requirements need parallel exploration.

---

## Table of Contents

1. [When to Use Sub-Agents](#when-to-use-sub-agents)
2. [Multi-Domain Parallel Expansion](#multi-domain-parallel-expansion)
3. [Parallel Challenge Exploration](#parallel-challenge-exploration)
4. [Model Selection](#model-selection)

---

## When to Use Sub-Agents

Requirements extraction is inherently sequential within a single domain
(L5→L4→L3→L2→L1 builds on each level). Sub-agents help in two scenarios:

1. **Multi-domain input** — the request spans 2+ independent domains
   that can be expanded in parallel before unified requirements synthesis
2. **Challenge exploration** — the user asks to explore alternatives,
   and Goal/Premise/Constraint challenges can run in parallel

| Scenario | Sub-agent benefit | Strategy |
| --- | --- | --- |
| Single domain, no challenges | None | Run Phase 0 + Phase 1 inline |
| Multi-domain input (2-4 domains) | High — parallel L5→L1 expansion | One sub-agent per domain |
| Multi-domain input (5+ domains) | High | Group related domains (2-3 per agent) |
| Challenge exploration (2-3 challenges) | Moderate — parallel alternatives | One sub-agent per challenge |

---

## Multi-Domain Parallel Expansion

When the input spans multiple independent domains,
each domain's L5→L1 CoK expansion can run in parallel.
The master then merges saturation data into a unified requirements specification.

### Decision Gate

```text
Request received →
  Phase 0 initial scan: identify distinct domains in the input
    1 domain → standard inline Phase 0
    2+ independent domains →
      sub-agent available?
        YES → fan-out: one agent per domain runs L5→L1
        NO  → sequential expansion per domain
  Merge saturation outputs → proceed to Phase 1 (always inline)
```

### Dispatch Pattern

```text
FOR EACH independent domain:
  spawn_agent(
    label = "[domain] requirements expansion"
    message = "Expand Chain of Knowledge for the [domain] aspects
               of this request:

               REQUEST: [original user request]
               FOCUS: [domain-specific aspects only]

               Run L5→L1 expansion:
               L5: Topics (explicit + implied for this domain)
               L4: Areas (solution patterns)
               L3: Fields (delivery mechanisms)
               L2: Disciplines (cross-cutting concerns)
               L1: Domains (classification)

               Stop when: relevance < 0.3, depth ≥ 5, or no new triples.

               Return saturation output:
               L5→{topics} | L4→[area]+{patterns} | L3→[field]+{mechanisms}
               L2→[discipline]+{concerns} | L1→[domain]✓
               Requirements: L4[constraints] + L3[constraints] + L2[mandates]
               Solution Space: {patterns from L4-L3}"
  )
→ collect all domain saturation outputs
→ master merges: deduplicate cross-domain concerns, identify domain interactions
→ master runs Phase 1 (Why? recursion + requirements specification) using merged saturation data
```

### Why Master Handles Phase 1

Phase 1 (top-down intent inference) must see the FULL saturation picture
to produce a coherent Mission. Running "why?" recursion per domain
would produce multiple competing Missions instead of one unified terminal value.

---

## Parallel Challenge Exploration

When the user asks to "explore alternatives" or "think outside the box,"
the three challenge types (Goal, Premise, Constraint) can run in parallel
since each produces an independent alternative requirements specification.

### Dispatch Pattern

```text
Original requirements specification produced →
  User requests challenge exploration →
    spawn 3 agents in parallel:

    GOAL CHALLENGE agent:
      "Given this requirements specification: [original]
       Challenge the Goal: propose a fundamentally different approach
       to achieving the same Mission.
       Cascade: update Premises and Constraints to match new Goal.
       Return: complete alternative requirements specification."

    PREMISE CHALLENGE agent:
      "Given this requirements specification: [original]
       Challenge a key Premise: what if [assumption] is false?
       Cascade: update Constraints to match new Premise.
       Return: complete alternative requirements specification."

    CONSTRAINT CHALLENGE agent:
      "Given this requirements specification: [original]
       Challenge a key Constraint: what if [limit] didn't apply?
       Return: complete alternative requirements specification."

→ collect 3 alternative requirements specifications
→ master presents original + 3 alternatives with trade-off analysis
```

---

## Model Selection

| Role | Cognitive Demand | Model Tier | Rationale |
| --- | --- | --- | --- |
| **Domain expansion (simple domains)** | Moderate | Fast (sonnet-class) | Well-known domains with clear L5→L1 paths; structured extraction |
| **Domain expansion (complex/novel)** | High | Strongest (opus-class) | Novel domains require creative triple discovery and deep reasoning |
| **Challenge agents** | High | Strongest (opus-class) | Challenging assumptions requires creative divergence and cascading |
| **Master (merge + Phase 1)** | Highest | Strongest (opus-class) | Cross-domain synthesis and Mission inference need the deepest reasoning |

**When model selection is unavailable:**
Use the default model for all agents. The parallelism benefit
(expanding 3 domains simultaneously) justifies sub-agent dispatch
even without model differentiation.

**Cost note:**
For a request spanning 3 well-known domains (e.g., "web app with payments and analytics"),
using fast models for domain expansion saves ~40% of Phase 0 cost.
For novel domains (e.g., "quantum computing + bioethics"), use the strongest model throughout.
