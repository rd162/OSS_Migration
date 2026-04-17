---
name: selecting-pe-methods
description: Selects the optimal prompt engineering method or method combination for a given task based on domain, complexity, stakes, and constraints. Use when deciding between reasoning strategies (CoT, ToT, GoT, CoD, SoT), action patterns (ReAct, Plan-and-Solve), or knowledge methods (CoK) before starting work. Provides a decision matrix and selection rationale.
version: "2.0"
metadata:
  author: rd162@hotmail.com
  tags: prompt-engineering, method-selection, reasoning, CoT, ToT, ReAct, CoD, SoT
---

# Selecting PE Methods

Choose the right prompt engineering method (or combination) for any task
based on domain, complexity, stakes, and available budget.

This skill is self-contained decision logic — no external dependencies.
It produces a recommendation; the caller decides whether to follow it.

## When to Use

- Starting a new task and unsure which reasoning strategy fits
- Combining multiple methods for a complex workflow
- Selecting the right structure (prose, pseudo-code, XML, code-based)
- Deciding how much rigor a task warrants (single-pass vs. multi-candidate)
- Optimizing token spend by matching method weight to task stakes

## When NOT to Use

- Pure creative writing with no quality constraints (just generate)
- Single-step factual lookups (no method selection needed)
- Tasks where the user has already chosen a specific method
- Greetings, clarifications, or simple follow-up questions

## Termination

| Signal    | Condition                                       | Action                                 |
| --------- | ----------------------------------------------- | -------------------------------------- |
| COMPLETE  | Recommendation produced with all 5 fields       | ✓ STOP — done                          |
| AMBIGUOUS | Two methods score equally across all dimensions | Ask user to clarify priority dimension |
| BLOCKED   | Task cannot be classified on any dimension      | Request more context from user         |

## Graceful Degradation

This skill is pure decision logic with no external dependencies.
It always produces a recommendation regardless of environment.

- **Full context:** Classify all 5 dimensions, apply selection rules, choose structure
- **Limited context:** Classify stakes + complexity only, apply simplified rules
- **Minimal:** Default to CoT sequential reasoning (safe universal fallback)

The output is always a method recommendation.
Depth of analysis varies; the recommendation format does not.

---

## Method Catalog

### Reasoning Methods

| Method              | Pattern                                | Best For                      |
| ------------------- | -------------------------------------- | ----------------------------- |
| **CoT**             | step₁→step₂→…→answer                   | Sequential problem solving    |
| **ToT**             | explore branches→evaluate→prune→select | Multiple solution paths       |
| **GoT**             | nodes + edges→merge/refine→converge    | Complex multi-path reasoning  |
| **CoD**             | symbols→3-8 words→outcomes             | Token-efficient reasoning     |
| **SoT**             | outline→expand each parallel→merge     | Fast structured generation    |
| **Multi-Candidate** | generate N→compare→select best         | Robust divergent exploration  |
| **Self-Refine**     | solution→critique→rethink→converge     | Iterative quality improvement |

### Knowledge Methods

| Method                  | Pattern                               | Best For                        |
| ----------------------- | ------------------------------------- | ------------------------------- |
| **CoK**                 | triples→forward-fill gaps→saturate    | Context gathering, verification |
| **Generated Knowledge** | generate facts→augment context→answer | Fast internal knowledge priming |

Generated Knowledge is NOT suitable for time-sensitive
or out-of-training-data claims.
Always verify with tools when freshness matters.

### Action Methods

| Method             | Core Question                | Best For                |
| ------------------ | ---------------------------- | ----------------------- |
| **ReAct**          | "What should I do next?"     | Dynamic tool use        |
| **ReflAct**        | "Am I aligned with my goal?" | Long tasks, drift risk  |
| **Plan-and-Solve** | "How do I break this down?"  | Known structure upfront |

### Prompt Structures

| Structure            | Format                     | Best For               |
| -------------------- | -------------------------- | ---------------------- |
| **Natural Language** | Prose instructions         | Simple tasks, creative |
| **Structured**       | Headers, bullets, sections | Complex multi-part     |
| **Pseudo-code**      | IF/THEN/ELSE, loops        | Conditional logic      |
| **Code-based**       | Actual code templates      | Precise algorithms     |
| **XML/JSON Schema**  | Tagged structure           | Strict output format   |

---

## Selection Matrix

### By Scenario

| Scenario              | Primary Method       | Add Self-Refine?      |
| --------------------- | -------------------- | --------------------- |
| High-stakes complex   | Multi-Candidate      | Refine all candidates |
| Real-time execution   | ReAct                | Refine final only     |
| Research/analysis     | ToT + CoK            | Refine winner         |
| Creative/diverse      | Single + Self-Refine | Yes, single loop      |
| Verification-critical | Multi-Candidate      | Refine all + winner   |
| Code generation       | Code-based + CoT     | Refine winner         |
| Multi-step planning   | Plan-and-Solve       | Refine each step      |
| Token-constrained     | Single + Self-Refine | Max 2-3 iterations    |

### By Stakes

```text
High-stakes       → Multi-Candidate (3+) + pairwise comparison
Factual claims    → External verification (tools, search)
Quality iteration → Self-Refine until defense or convergence
Complex breakdown → Plan-and-Solve OR ToT exploration
Low-stakes simple → CoT or single-pass (default)
```

---

## Decision Procedure

### Step 1: Classify the Task

Assess along these dimensions:

| Dimension      | Low                         | High                       |
| -------------- | --------------------------- | -------------------------- |
| **Stakes**     | Informal, reversible        | Production, irreversible   |
| **Complexity** | Single-step, well-defined   | Multi-step, ambiguous      |
| **Divergence** | One obvious approach        | Multiple viable approaches |
| **Freshness**  | Static knowledge sufficient | Current data required      |
| **Budget**     | Tight token constraints     | Generous token allowance   |

### Step 2: Apply Selection Rules

```text
IF stakes=high AND divergence=high
  → Multi-Candidate + pairwise comparison
  (use a multi-candidate skill if available; otherwise generate 2-3 options and compare)

IF stakes=high AND divergence=low
  → Single candidate + Self-Refine
  (use a refinement skill if available; otherwise critique-revise manually)

IF complexity=high AND structure=known
  → Plan-and-Solve with ReAct fallback

IF complexity=high AND structure=unknown
  → ToT exploration → prune → select

IF freshness=high
  → CoK with external tool verification

IF budget=tight
  → CoD traces + SoT skeleton (minimize output tokens)

IF task=code-generation
  → Code-based prompting + CoT reasoning

IF task=research
  → CoK saturation + ToT for synthesis

IF task=creative
  → High temperature + Self-Refine loop

DEFAULT
  → CoT sequential reasoning
```

These rules reference capabilities by description, not by tool name.
If a matching skill is available, invoke it.
If not, apply the pattern inline — the methodology works
regardless of whether it's packaged as a skill.

### Step 3: Choose Prompt Structure

```text
Simple task + creative freedom → Natural Language
Complex task + multiple parts  → Structured (headers, bullets)
Conditional logic              → Pseudo-code
Precise algorithm              → Code-based template
Strict output format           → XML/JSON schema
```

### Step 4: Determine Self-Refine Integration

```text
High-stakes + multi-candidate → Refine ALL candidates before comparison
High-stakes + single          → Refine until DEFENSE or CONVERGE
Medium-stakes                 → Refine winner only (post-selection)
Low-stakes                    → Skip self-refine (single-pass)
Token-constrained             → Max 2-3 iterations if refining at all
```

---

## Method Composition Patterns

Common combinations that work well together:

```text
SoT + CoD:          skeleton → dense blueprint → full spec → result
                     (multi-component problems needing structure + density)

CoK + Multi-Cand:   saturate knowledge → identify alternatives → generate candidates → compare
                     (facts gathered before solutions proposed)

ReAct + Refine:     tool loop → intermediate result → self-refine → final output
                     (dynamic data fetching followed by polishing)

Plan + ReAct:       decompose upfront → execute plan → if step fails, switch to ReAct
                     (known structure, uncertain sub-step outcomes)
```

---

## Output Format

When recommending a method, use this template:

```text
TASK: [1-line description]
DIMENSIONS: stakes=[H/M/L] | complexity=[H/M/L] | divergence=[H/M/L] | freshness=[H/M/L] | budget=[tight/standard/generous]

METHOD: [Primary method]
  + [Secondary method if needed]
  + [Self-Refine integration level]

STRUCTURE: [Prompt structure type]

RATIONALE: [1-2 lines explaining the selection]
```

### Example

```text
TASK: Design authentication system for banking app
DIMENSIONS: stakes=H | complexity=H | divergence=H | freshness=M | budget=standard

METHOD: Multi-Candidate (3 divergent)
  + CoK verification for security standards
  + Self-Refine ALL candidates before comparison

STRUCTURE: Structured (headers + pseudo-code for flows)

RATIONALE: High stakes + high divergence demands multi-candidate comparison.
Banking domain requires CoK for compliance verification.
```

---

## Anti-Patterns

```text
✗ Selecting a method without classifying the task dimensions first
✓ Always run Step 1 (classify) before Step 2 (select)

✗ Recommending Multi-Candidate for every high-stakes task
✓ Check divergence — low divergence + high stakes → Self-Refine, not Multi-Candidate

✗ Skipping the self-refine integration decision (Step 4)
✓ Every recommendation must specify how self-refine fits (including "skip")

✗ Recommending CoK without tool availability for verification
✓ CoK with freshness=high requires external tools — verify availability first

✗ Outputting a method name without the structured format
✓ Always produce TASK/DIMENSIONS/METHOD/STRUCTURE/RATIONALE

✗ Over-engineering low-stakes tasks with heavy method combinations
✓ Low-stakes simple → CoT or single-pass (default)

✗ Assuming specific skills must be available to apply a method
✓ Methods are patterns — apply inline if no matching skill exists
```

## Environment Compatibility

This skill is pure decision logic — no tooling dependencies.
Works with any agent or LLM that supports the skills format:

- **Claude Code / API**: Use thinking tool for selection reasoning
- **GitHub Copilot / VS Code**: Apply as mental framework before task
- **Cursor / Codex / Gemini CLI**: Same decision procedure applies
- **Kimi / other agents**: Works in any conversational context
- **Bare LLMs**: Include selection output in initial prompt for guidance
- **Programmatic**: Implement as a classifier function routing to method templates

## References

- Besta et al.,
  "Demystifying Chains, Trees, and Graphs of Thoughts"
  (arXiv:2401.14295, 2024).
  Taxonomy of reasoning topologies supporting systematic method comparison.
- Pandey et al.,
  "Adaptive Graph of Thoughts: Test-Time Adaptive Reasoning
  Unifying Chain, Tree, and Graph Structures"
  (arXiv:2502.05078, 2025).
  Adaptive method selection across reasoning structures.
- The 5-dimension classification (stakes, complexity, divergence,
  freshness, budget) and the decision procedure are novel —
  no published framework provides an equivalent actionable selection
  system for prompt engineering methods.
