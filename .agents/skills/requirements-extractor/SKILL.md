---
name: requirements-extractor
description: >-
  Extracts structured requirements from raw knowledge context —
  documents, codebases, briefs, user requests, or transcripts —
  using bottom-up Chain of Knowledge expansion to surface implicit
  constraints, then top-down intent inference to produce a
  Mission, Goals, Premises, Constraints specification.
  Classifies input type (repo, spec, brief, transcript) and adapts
  search strategy accordingly. Every Premise carries a risk assessment;
  every Constraint cites its source.
  Use when you have unstructured input and need formal requirements
  before implementation, architecture, or candidate generation.
version: "3.0"
metadata:
  author: rd162@hotmail.com
  tags: requirements, discovery, CoK, prompt-engineering
---

# Requirements Extractor

Extracts structured requirements from raw knowledge context.
Combines bottom-up knowledge expansion with top-down intent inference
to produce a requirements specification with Mission, Goals,
Premises, and Constraints from any unstructured input.

The unique value of this approach:
bottom-up broadens the solution space BEFORE top-down narrows it.
This prevents both tunnel vision (narrowing too early)
and scope creep (never focusing).

## When to Use

- Analyzing a raw prompt, brief, or user request before implementation
- Uncovering hidden requirements, implicit constraints, cross-cutting concerns
- Broadening the solution space before committing to an approach
- Preparing structured input for candidate generation or architecture decisions
- Any task where "what the user said" likely understates "what the user needs"

## When NOT to Use

- Pure logic or math proofs (no hidden requirements — problem is fully stated)
- Simple factual lookups (no solution space to broaden)
- Tasks where the user has already provided a complete specification
- Creative writing where open-endedness is the goal, not a gap

## Termination

| Signal    | Condition                                                          | Action                       |
| --------- | ------------------------------------------------------------------ | ---------------------------- |
| COMPLETE  | All four components produced + Mission Space populated             | STOP — specification ready   |
| SATURATED | Phase 0 stop criteria met (see below)                              | Proceed to Phase 1           |
| BLOCKED   | Request too ambiguous to extract even basic topics                 | Ask user for clarification   |

## Graceful Degradation

This skill is self-contained methodology — no external dependencies.
The depth of each phase scales with available context budget:

- **Full budget:** Complete L5→L1 expansion + recursive "why?" chain
- **Tight budget:** L5→L3 expansion (skip L2-L1) + 2-3 "why?" steps
- **Minimal budget:** Extract explicit topics + single "why?" pass → lightweight spec

The output is always a requirements specification
with Mission, Goals, Premises, and Constraints.
The depth varies; the structure does not.

---

## Input Classification

Before starting Phase 0, classify the input to determine
what sources to read and where implicit requirements hide.
Different input types bury requirements in different places.

| Input Type | What to Read | Where Implicit Requirements Hide |
| ---------- | ------------ | -------------------------------- |
| **Repository** | README, CONTRIBUTING, docker-compose, .env.example, CI configs, package.json/requirements.txt, Makefile, architecture docs | Runtime dependencies, deployment constraints, build system mandates, code style rules, license terms |
| **Specification** | Main spec + linked normative sections, conformance clauses, MUST/SHALL language, appendices | Implementor constraints, backwards compatibility guarantees, interop assumptions, stability promises |
| **Product brief** | Surface text + read between lines for team/budget/timeline signals | Ecosystem dependencies, regulatory obligations, unstated market assumptions, team capacity limits |
| **Transcript** | Explicit statements + infer from who says what, what's NOT challenged, hedging language ("ideally", "if possible") | Soft vs hard constraints (hedging = soft), political constraints (who has veto power), assumed context |
| **Mixed** | Classify each source separately, then merge | Cross-source contradictions, different stakeholders assuming different things |

For repositories, Phase 0 should actively read beyond the README.
The README describes what the project *wants to be*;
the config files describe what it *actually requires to run*.

---

## Two-Phase Process

**Phase 0** (Bottom-Up): Expand the knowledge space using CoK triples.
**Phase 1** (Top-Down): Collapse into structured requirements specification.

Always run Phase 0 before Phase 1.
Phase 0 feeds saturation data into Phase 1.

---

## Phase 0: Bottom-Up Requirements Saturation

Broaden the solution space before narrowing intent.
Uncover hidden requirements, alternatives, and cross-cutting concerns.

### Method

Build Chain of Knowledge (CoK) triples from the request,
expanding from specific topics upward through areas, fields,
disciplines, and domains.

**Triple structure:** `(subject, relation, object)` — linked knowledge units.

### Hierarchy

```text
L5: Topics      → explicit and implied subjects from the request
L4: Areas       → solution patterns that group topics
L3: Fields      → delivery mechanisms and implementation approaches
L2: Disciplines → cross-cutting concerns and mandates
L1: Domains     → top-level classification and disjointness verification
```

### Expansion per Level

**L5 — Topics:** Extract explicit, then expand implicit.
`(request, states, topic)` → `(topic, implies|requires|enables, topic)`

**L4 — Areas:** Group topics into solution areas and patterns.
`(topic, belongs_to, area)` → `(area, has_pattern, pattern)`

**L3 — Fields:** Map areas to delivery mechanisms.
`(area, implements_via, field)` → `(field, requires, mechanism)`

**L2 — Disciplines:** Cross-cutting concerns and mandates.
`(field, grounded_in, discipline)` → `(discipline, mandates, concern)`

**L1 — Domains:** Classify and verify disjointness.
`(discipline, part_of, domain)` → `(domain, disjoint_from, domain)`

### Saturation Output

Produce this summary after completing all levels:

```text
L5→{topics} | L4→[area]+{patterns} | L3→[field]+{mechanisms}
L2→[discipline]+{concerns} | L1→[domain]✓
Requirements: L4[constraints] + L3[constraints] + L2[mandates]
```

### Stop Criteria

Stop expanding when ANY is true:

- Relevance drops below 0.3
- Depth reaches 5 levels
- No new triples generated at current level
- Token budget exhausted

---

## Phase 1: Top-Down Intent Inference

Collapse the broadened space into a structured requirements specification.

### The "Why?" Recursion

Start with the stated request and ask "why?" repeatedly
until the answer becomes circular (a tautology).
The tautology is the Mission — the terminal value
that justifies all downstream goals.

This separates what the user ASKED for from what the user NEEDS.

```text
Example: "build a todo app"
  → why? "to manage tasks"
  → why? "to increase productivity"
  → why? "to improve well-being"
  → why? "well-being is intrinsically valuable" ← tautology = Mission
```

**Note on terminology:** This skill calls the recursive "why?" process
the "W-functor" — original notation
inspired by category theory's concept of functors as structure-preserving maps.
The "W" stands for "Why." It is not established academic terminology;
it is a practical shorthand for this specific recursion pattern.

### Mission Quality Gate

After deriving the Mission, apply this self-check:

1. **Single sentence.** If the Mission is more than one sentence,
   contains a list, or has "two parts," the recursion hasn't reached
   a fixed point — go deeper. The tautology is always expressible
   as one statement.
2. **Invariant test.** Change any Goal — does the Mission still hold?
   If not, the Mission is too specific (it's actually a Goal).
3. **Tautology test.** Ask "why?" one more time.
   If the answer restates the Mission or becomes circular,
   it's a genuine fixed point.

### Specification Components

| Component       | Litmus Test                                         | Source              |
| --------------- | --------------------------------------------------- | ------------------- |
| **Mission**     | Asking "why?" yields a tautology (circular answer)  | "Why?" fixed point  |
| **Goals**       | Changing the goal changes the solution type         | Frozen from request |
| **Premises**    | If false, the goal becomes impossible               | L4-L2 saturation    |
| **Constraints** | Violation causes rejection (hard) or penalty (soft) | User stated + L3-L2 |

### Inferring Each Component

**Mission:** The terminal value from "why?" recursion.
Must pass the quality gate above.

**Goals:** Freeze the concrete objectives from the original request.
Changing a goal should change the type of solution entirely.

**Premises:** Extract from L4-L2 saturation data.
Each premise is an assumption that, if false, makes a goal impossible.
Every premise MUST include:
- **Source** — where this assumption comes from (stated, inferred from [file/section], industry standard)
- **Risk if false** — what happens to the project if this assumption is wrong

Flag any premise as **HIGH RISK** when falsification would
invalidate the Mission itself, not just a single Goal.

**Constraints:** Combine user-stated constraints with mandates from L2-L3.
Split into two tiers:
- **Hard** (violation = rejection) — non-negotiable boundaries
- **Soft** (violation = penalty) — strong preferences with possible tradeoffs

Every constraint MUST cite its **Source** — who or what imposed it:
`Legal (stated)`, `IT policy (stated)`, `inferred from [context]`,
`industry standard`, `regulatory`, etc.
This makes the specification auditable and challengeable.

### Output Template

```text
## Mission

[Single sentence — the terminal "why?" value]

W-functor chain: [request] → [why1] → [why2] → ... → [tautology]

## Goals

1. [Concrete objective] — [measurable criterion if available]
2. ...

## Premises

| # | Premise | Source | Risk if false |
|---|---------|--------|---------------|
| P1 | [assumption] | [where it comes from] | [consequence] |

[Flag HIGH RISK premises explicitly]

## Constraints

### Hard (violation = rejection)

| # | Constraint | Source |
|---|-----------|--------|
| C1 | [boundary] | [who imposed it] |

### Soft (violation = penalty)

| # | Constraint | Source |
|---|-----------|--------|
| S1 | [preference] | [who requested it] |

## Mission Space

[See Mission Space section below]
```

---

## Mission Space

After producing the requirements specification, compile a Mission Space —
a compact knowledge base of evaluated alternatives and critical context
that supplements the requirements breakdown.

The Mission Space captures what Phase 0 discovered but doesn't fit
neatly into Goals, Premises, or Constraints:

1. **Evaluated alternatives** — viable approaches from L4-L3 patterns,
   with fit assessment against the hard constraints
2. **Domain context** — critical knowledge about the problem domain
   that any implementor needs (regulatory landscape, ecosystem dynamics,
   market assumptions)
3. **Knowledge gaps** — things the specification cannot answer
   because the input didn't address them (flagged for follow-up)

The Mission Space is not a recommendation — it is a map of the solution terrain.
It lets downstream consumers (architects, candidate generators, decision-makers)
navigate alternatives without re-doing the research.

---

## Worked Example

**Raw request:** "Build a social network for dog owners"
**Input type:** Product brief (informal)

### Phase 0 Output

```text
L5→{profiles, connections, messaging, photos, dog-breeds, events, location}
L4→[social-engagement]+{feeds, groups, matching} | [pet-mgmt]+{health, breeding}
L3→[web-platform]+{SPA, REST API, real-time} | [mobile]+{native, PWA}
L2→[software-engineering]+{security, testing, scalability}
   [data-science]+{recommendations, moderation}
L1→[technology]✓ (disjoint: veterinary-science→separate domain)
```

### Phase 1 Output

```text
## Mission

Foster community and well-being among dog owners.

W-functor: social network → connect owners → build community
→ improve well-being → intrinsic value ← tautology

## Goals

1. Connect dog owners via profiles, messaging, and events
2. Enable photo/media sharing centered on dogs
3. Provide breed-specific communities and content

## Premises

| # | Premise | Source | Risk if false |
|---|---------|--------|---------------|
| P1 | Users have reliable internet | Industry standard | Offline-first arch needed |
| P2 | Users own or care for dogs | Inferred from target audience | Platform has no audience |
| P3 | Mobile-first usage pattern | Inferred from social app norms | Web-only may underserve |

## Constraints

### Hard
| # | Constraint | Source |
|---|-----------|--------|
| C1 | Authentication required | Security mandate (L2) |
| C2 | Content moderation | Legal/safety (L2) |
| C3 | GDPR compliance | Regulatory (L2) |

### Soft
| # | Constraint | Source |
|---|-----------|--------|
| S1 | Real-time messaging | User expectation (inferred) |
| S2 | Location services | Geo-matching for events (L4) |

## Mission Space

Alternatives: {PWA+REST, native+GraphQL, hybrid+real-time}
Domain context: Pet social networks compete with Facebook Groups;
  breed-specific forums have loyal but small audiences.
Knowledge gaps: Monetization model, content liability policy,
  veterinary content boundary (advice vs. information).
```

---

## Handling Partial Input

Real-world requests often provide incomplete information.
Rather than failing, apply expansion:

```text
Input: "Build SPA with cloud platform, budget $50K"
Present:  Goals, Premises, Constraints   Missing: Mission
→ W(Goal): Why SPA? → reach users → empower access → intrinsic value
→ Fill remaining P and C from L5→L1 saturation
```

The expansion is idempotent — always run both phases regardless.

---

## Optional: Challenge Requirements

After producing the specification, evolve requirements by challenging
Goals, Premises, or Constraints — while Mission stays invariant.

| Challenge | Transforms | Cascade | Example |
| --------- | ---------- | ------- | ------- |
| **Goal** | G → G' | P and C must update | Cloud → radio mesh |
| **Premise** | P → P' | C must update | "Web" → "Local-first" |
| **Constraint** | C → C' | None | "Mobile-first" → "Multi-platform" |

**Mission is never challenged** — it is the fixed point.
**Cascading is mandatory** — a goal challenge without P/C updates
produces an internally inconsistent spec.

---

## Integration with Other Skills

This skill's output is consumed by downstream skills,
but it can also be used standalone for requirements analysis.

- **Candidate generation:** Goals and Constraints become evaluation criteria;
  Mission Space ensures divergent alternatives
- **Pairwise comparison:** Goals and Constraints become scoring criteria
- **Verification:** Premises become testable assumptions
- **Audit:** The CoK saturation output documents the reasoning trail

## Sub-Agent Dispatch

Requirements extraction benefits from sub-agents in two scenarios:

**Multi-domain input:** When the request spans 2+ independent domains,
each domain's L5→L1 CoK expansion runs in parallel via sub-agents.
The master merges saturation data, then runs Phase 1 (always inline —
Mission inference needs the full picture).

**Challenge exploration:** When exploring alternatives, Goal/Premise/Constraint
challenges run in parallel since each produces an independent alternative spec.

| Scenario | Strategy |
| --- | --- |
| Single domain | Inline (no sub-agents) |
| 2-4 independent domains | One sub-agent per domain |
| Challenge exploration | One sub-agent per challenge type |

See @references/sub-agent-guide.md for dispatch patterns,
model selection, and the merge protocol.

## Anti-Patterns

```text
✗ Skipping Phase 0 and jumping straight to specification (misses hidden requirements)
✓ Always run Phase 0 before Phase 1 — saturation feeds intent inference

✗ Writing Mission as a list or multi-sentence paragraph
✓ Mission is ONE sentence — if it needs a list, the "why?" recursion isn't done

✗ Premises without risk assessment ("Users have internet" — so what?)
✓ Every Premise states what breaks if it's false: "P fails → offline arch needed"

✗ Constraints without source citation ("Must be on-prem" — says who?)
✓ Every Constraint cites its source: "On-prem only — Legal (stated)"

✗ Treating Premises as Goals (premises are assumptions, goals are objectives)
✓ Litmus: if false → goal impossible (premise) vs. changing it → different solution (goal)

✗ Listing every L5 topic without grouping into L4 areas
✓ Group topics → areas → fields → disciplines → domains (hierarchy matters)

✗ Skipping non-obvious files in repo inputs (only reading the README)
✓ Read docker-compose, .env, CI configs, CONTRIBUTING — that's where real constraints live
```

## Environment Compatibility

This skill is pure methodology — no tooling dependencies.
Works with any agent or LLM:

- **Claude Code / Claude API**: Use thinking tool for CoK expansion
- **GitHub Copilot / VS Code**: Apply as analysis framework before implementation
- **Cursor / Codex / Gemini CLI**: Same two-phase process applies
- **Kimi / other agents**: Works in any conversational context
- **Bare LLMs**: Run Phase 0 + Phase 1 manually in conversation
- **Programmatic**: Implement as CoK graph builder → requirements extractor pipeline

## Formal Basis

The two-phase process has grounding in established theory:

- **Phase 0 (Bottom-Up):** Chain of Knowledge expansion (Li et al., 2023)
  combined with goal decomposition from goal-oriented RE (van Lamsweerde, 2001).
  The L5→L1 hierarchy mirrors generalization functors
  from Applied Category Theory (Fong & Spivak, 2019).
- **Phase 1 (Top-Down):** The recursive "why?" chain adapts Toyota's
  5 Whys root cause analysis (Ohno, 1988). The Mission as a fixed point
  of the W-functor has formal grounding in Tarski's fixed-point theorem (1955).
- **Requirements structure:** Adapts Pohl's requirements layering (2010)
  for prompt engineering. ACT formalization treats Mission, Goals, Premises,
  Constraints as objects in a Requirements Category with morphisms between levels.

See `references/academic-references.md` for full citations and provenance.

## References

See `references/academic-references.md` for full citations and provenance.

Key references: Li et al. 2023 (CoK), Pohl 2010 (Requirements Engineering),
van Lamsweerde 2001 (GORE), Ohno 1988 (5 Whys).
