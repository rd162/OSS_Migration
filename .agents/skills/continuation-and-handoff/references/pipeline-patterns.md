# Pipeline Patterns Reference

Detailed design patterns for composing continuations and handoffs into pipelines.

## Universal Pipeline: SoT → CoD → Blueprint → Result

Domain-agnostic four-stage pipeline that works for ANY task.

| Stage | Method    | Produces                    | Application                             |
| ----- | --------- | --------------------------- | --------------------------------------- |
| 1     | SoT       | Structural skeleton         | Plan, outline, scope, decomposition     |
| 2     | CoD       | Dense operational blueprint | Steps, tools, constraints, dependencies |
| 3     | Blueprint | Full actionable spec        | Scripts, prompts, procedures, queries   |
| 4     | Result    | Final deliverable           | Code, research, analysis, documentation |

### Domain-Specific Instantiations

| Domain       | SoT Output           | CoD Output                | Blueprint Output             | Result              |
| ------------ | -------------------- | ------------------------- | ---------------------------- | ------------------- |
| **Code**     | Architecture outline | Module specs + interfaces | Implementation plan          | Source files        |
| **Research** | Search strategy plan | Tool use + source plan    | Search scripts + synthesis   | Research document   |
| **Analysis** | Analysis framework   | Data sources + methods    | Query scripts + viz prompts  | Analysis report     |
| **Design**   | Component hierarchy  | Interaction specs         | Design tokens + layouts      | Design system       |
| **Docs**     | Document structure   | Section specs + sources   | Content prompts + formatting | Documentation       |
| **Config**   | System topology      | Service dependencies      | Config templates             | Configuration files |

---

## Composition Patterns

### Sequential Pipeline

```text
P₁ → P₂ → P₃
```

Each pipeline completes fully before the next begins.
Output of Pₙ becomes input to Pₙ₊₁.

**Use case:** Phased delivery with clear stage gates.

**Continuation points:** Between any Pₙ and Pₙ₊₁.
Each stage boundary is a natural continuation or handoff point.

**Example:**

```text
P₁ (Requirements Discovery):
  SoT→CoD→Blueprint→Result: Requirements document
  → CONTINUATION or HANDOFF to P₂

P₂ (Architecture Design):
  SoT→CoD→Blueprint→Result: Architecture spec
  → CONTINUATION or HANDOFF to P₃

P₃ (Implementation):
  SoT→CoD→Blueprint→Result: Source code
```

---

### Nested Pipeline

```text
P₁(contains P₂) → P₃
```

One pipeline runs as a sub-pipeline within another.
The outer pipeline pauses while the inner one executes.

**Use case:** Research-then-implement, where research is a prerequisite.

**Example:**

```text
P₁ (Development Pipeline):
  Stage 1 (SoT): Architecture outline
  Stage 2 (CoD): Needs technology comparison →
    P₂ (Research Sub-Pipeline):
      SoT: Search strategy
      CoD: Tool use plan
      Blueprint: Search scripts
      Result: Technology comparison document
    ← P₂ result feeds back into P₁
  Stage 3 (Blueprint): Implementation plan informed by research
  Stage 4 (Result): Source code
```

---

### Parallel Pipeline

```text
P₁ ∥ P₂ → merge → P₃
```

Multiple pipelines run concurrently,
results merged before feeding into the next stage.

**Use case:** Multiple independent analyses that feed a synthesis.

**Handoff pattern:** Launch P₁ and P₂ as separate agent handoffs.
A merge agent collects both results.

**Example:**

```text
P₁ (Security Analysis):    → security report
P₂ (Performance Analysis): → performance report
                              ↓ merge
P₃ (Architecture Decision): uses both reports → final architecture
```

**Cross-vendor implementation:**

- Claude Code: Sub-agents for parallel, main agent for merge
- GitHub Copilot: Separate issues/PRs, merge in main branch
- Bare LLM: Sequential simulation (P₁ then P₂ then merge)

---

### Iterative Pipeline

```text
P₁ → P₂ → P₁↻ until converged
```

Pipelines cycle until a convergence criterion is met.

**Use case:** Refine cycles, test-driven development, progressive improvement.

**Continuation pattern:** Each iteration is a natural continuation point.
Track iteration count and convergence metric.

**Example:**

```text
Iteration 1:
  P₁ (Generate): Draft implementation
  P₂ (Validate): Run tests → 3 failures
  → CONTINUATION: "Iteration 1 complete. 3 failures. Resume P₁ with fixes."

Iteration 2:
  P₁ (Generate): Fix identified issues
  P₂ (Validate): Run tests → 0 failures ✓
  → DONE (converged)
```

**RALPH loop compatibility:**
This pattern maps directly to RALPH-style iteration.
Each cycle = one RALPH iteration with fresh context.

---

### Conditional Pipeline

```text
P₁ → (if X: P₂ else P₃) → P₄
```

Branch based on intermediate results.

**Use case:** Different processing paths for different input types.

**Handoff pattern:** P₁ produces result + routing decision.
Handoff includes the branch condition and both possible paths.

**Example:**

```text
P₁ (Analyze Input):
  Result: "Input is a legacy codebase"
  Branch: complexity > threshold?

  YES → P₂ (Incremental Migration):
    Migrate module by module, test each
  NO  → P₃ (Full Rewrite):
    Rewrite from scratch with new patterns

P₄ (Integration Testing):
  Validate result regardless of path taken
```

---

## Capability Cascade (Agent Tiers)

Map pipeline stages to agent capability tiers for cost optimization.

| Stage | Tier     | Produces      | Handoff Contains                         |
| ----- | -------- | ------------- | ---------------------------------------- |
| 1     | Premium  | SoT skeleton  | Outline + ALL handoffs (2-N)             |
| 2     | Capable  | CoD blueprint | Blueprint + parameterized(3) + sealed(4) |
| 3     | Mid-tier | Full spec     | Spec + parameterized(4)                  |
| 4     | Fast     | Execution     | Results (terminal or next-pipeline)      |

**Principle:** Use the most capable (expensive) agent for planning,
cascade down to faster (cheaper) agents for execution.

**Cross-vendor tier mapping:**

| Tier     | Claude              | OpenAI         | Google            |
| -------- | ------------------- | -------------- | ----------------- |
| Premium  | Opus                | o3 / GPT-4o   | Gemini Ultra      |
| Capable  | Sonnet              | GPT-4o-mini    | Gemini Pro        |
| Mid-tier | Haiku               | GPT-4o-mini    | Gemini Flash      |
| Fast     | Haiku (low-temp)    | GPT-3.5        | Gemini Flash-Lite |

---

## Composed Pipeline Examples

### CoK-Informed Development

```text
Pipeline 1 — Requirements Discovery:
  SoT→CoD→Blueprint→Result: Refined requirements document

Pipeline 2 — Research (parallel with P1 or after):
  SoT→CoD→Blueprint→Result: Technology comparison

Pipeline 3 — Implementation:
  [Inputs: Requirements doc + Technology comparison]
  SoT→CoD→Blueprint→Result: Final deliverable
```

### Research-to-Production

```text
RESEARCH PIPELINE (prerequisite):
  SoT: Search strategy + resource plan
  CoD: Tool use plan (scrape, summarize, compare)
  Blueprint: Search scripts + synthesis prompts
  Result: Research synthesis document
     ↓ feeds into
IMPLEMENTATION PIPELINE:
  SoT: Architecture based on research
  CoD: Module specs informed by findings
  Blueprint: Implementation plan
  Result: Source code
```

### Multi-Phase Feature Development (RALPH-Compatible)

```text
Phase 1 — Requirements (1 iteration):
  Analyze request → produce MGPC spec
  → Write to specs/ directory
  → Exit (RALPH advances)

Phase 2 — Planning (1 iteration):
  Read specs/ → produce IMPLEMENTATION_PLAN.md
  → Prioritized task list, no code
  → Exit (RALPH advances)

Phase 3 — Building (N iterations):
  Per iteration:
    Pick top task from plan
    Implement → test → commit
    Update plan (mark done, surface next)
    Exit (RALPH re-invokes with fresh context)
  Until: all tasks complete

Phase 4 — Integration (1 iteration):
  Run full test suite
  Generate final report
  Clean up
```

---

## Cached Templates for Cycles

When pipelines iterate (generate → critique → refine → critique…),
cache reusable templates to reduce overhead:

```text
For loops:
├── core_critique_template.md  (reused each iteration)
├── core_refine_template.md    (reused each iteration)
└── cycle_state.json           (iteration count, termination signal)

Each iteration: cached template + current artifact + cycle state
```

---

## Continuation/Handoff Placement in Pipelines

### Where to Place Continuations

```text
✓ Between pipeline stages (SoT→CoD, CoD→Blueprint, etc.)
✓ Between pipeline compositions (P₁→P₂)
✓ At iteration boundaries in iterative pipelines
✓ When context budget exceeds 70%
✓ At natural phase boundaries (requirements→design→implementation)
```

### Where to Place Handoffs

```text
✓ When crossing capability tiers (Premium→Capable→Fast)
✓ When crossing domains (analysis→implementation)
✓ When parallel pipelines need independent execution
✓ When pipeline stage requires different tooling
```

### What to Include

Every continuation or handoff at a pipeline boundary must specify:

1. **Current pipeline stage** — where in SoT→CoD→Blueprint→Result
2. **Completed artifacts** — with file paths and types
3. **Next stage instructions** — explicit, not implicit
4. **Constraints carried forward** — from MGPC or user requirements
5. **Success criteria** — how the next stage knows it's done
