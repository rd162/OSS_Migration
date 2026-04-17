# Sub-Agent Dispatch and Polling — deep-research-t1

Extended reference for multi-subject sub-agent fan-out,
deep research agent polling protocol, and model selection.
Loaded on demand — not part of the main SKILL.md context.

---

## Table of Contents

1. [Sub-Agent Dispatch for Multi-Subject Research](#sub-agent-dispatch-for-multi-subject-research)
2. [Deep Research Agent Polling Protocol](#deep-research-agent-polling-protocol)
3. [Model Selection for Sub-Agents](#model-selection-for-sub-agents)

---

## Sub-Agent Dispatch for Multi-Subject Research

**⚠ MANDATORY:** When research covers **2+ independent subjects**
and a sub-agent mechanism is available (see orchestration rules),
dispatch each subject to a dedicated sub-agent
rather than researching sequentially in the master context.

### Why — Context Engineering

- Each sub-agent gets a **clean, isolated context window**
  free from cross-subject noise.
- Raw web content (scraped HTML, search results, API docs)
  stays in the sub-agent's context and never pollutes the master.
- The master receives only the **synthesized report** from each sub-agent,
  dramatically reducing token consumption.
- Quality improves because each sub-agent can go deep
  without competing for context space with other subjects.
- The master retains context budget for **synthesis and comparison**
  across all subjects — the highest-value reasoning step.

### Decision Gate

```text
Research request received →
  How many independent subjects?
    1 subject  → run Δ1-Δ7 inline (standard)
    2+ subjects, NO dependencies between them →
      sub-agent available? → YES → fan-out (one agent per subject or group)
                           → NO  → sequential with context fencing
    2+ subjects, WITH dependencies →
      sequential chain (output of A feeds B)
```

### Dispatch Pattern

```text
FOR EACH independent subject (or logical group of 2-3 related subjects):
  spawn_agent(
    label = "[subject-name] research"
    message = "Research [subject]. Report on: [dimensions].
               Use web search and scraping tools.
               Cite sources with tiers (T1-T4).
               Max [N] words per section.
               Return structured findings only."
  )
→ collect all reports
→ master synthesizes: compare, rank, identify gaps, produce unified answer
```

### Grouping Heuristic

| Subject count | Strategy                                                       |
| ------------- | -------------------------------------------------------------- |
| 1             | Inline Δ1-Δ7 in master context                                 |
| 2-3           | One sub-agent per subject                                      |
| 4-6           | Group related subjects (2-3 per agent)                         |
| 7+            | Group into 3-5 agents by affinity; set per-section word limits |

### Output Budget per Sub-Agent

Target ~3,000 words per agent report.
When a single subject is expected to produce >3,000 words,
constrain with explicit section word limits in the prompt
(e.g., "max 500 words per section").
When grouping 2-3 subjects per agent,
the natural constraint of covering multiple subjects
produces balanced output without explicit limits.

### Token Savings Estimate

| Approach                         | Master context consumed                                |
| -------------------------------- | ------------------------------------------------------ |
| Sequential inline (all subjects) | Raw HTML + search results + synthesis = 80-150K tokens |
| Sub-agent dispatch               | Only synthesized reports = 10-25K tokens               |
| Savings                          | 70-85% reduction in master context usage               |

### Integration with Δ1-Δ7

Each sub-agent independently executes the full Δ1-Δ7 protocol
for its assigned subject(s).
The master does NOT re-run Δ1-Δ7 on the same subjects.
The master's role is synthesis, comparison, and gap identification.

---

## Deep Research Agent Polling Protocol

When using asynchronous deep research tools
(e.g., `deep_researcher_start` → `deep_researcher_check`),
the research runs in the background and must be polled for results.

**⚠ MANDATORY: Wait minimum 30 seconds between status checks.**

```text
∆1: Start deep research with clear, specific instructions
    → receives research_id immediately

∆2: Wait AT LEAST 30 seconds before first status check
    → do NOT poll immediately — the research needs time to run
    → use this wait time productively (run other searches in parallel)

∆3: Check status with research_id
    → status: "processing" → wait another 30+ seconds, check again
    → status: "completed" → extract results
    → status: "failed" → fall back to multi-query manual search

∆4: Keep polling with 30+ second intervals until completed or failed
    → typical completion times:
       fast model:  15-30 seconds
       balanced:    30-60 seconds
       pro/deep:    60-180 seconds (be patient!)
    → do NOT give up after 1-2 checks — research takes time
    → maximum patience: 3-5 minutes for complex queries

∆5: On completion → extract findings, integrate into CoK graph
```

### Why 30 Seconds Minimum

Polling too frequently wastes API calls without accelerating results.
Deep research agents need time to search, read, and synthesize.
Premature polling produces "still processing" responses
that consume tokens without providing value.

### Parallel Work During Wait

While waiting for deep research results,
run standard Δ3 searches in parallel.
The deep research results will supplement — not replace —
standard search findings. Both contribute to saturation.

### Deep Research Model Selection

| Research need               | Model to use        | Expected wait |
| --------------------------- | ------------------- | ------------- |
| Simple factual lookup       | fast (~15s)         | 15-30 seconds |
| Multi-source comparison     | balanced (~30-45s)  | 30-60 seconds |
| HIGH-STAKES / comprehensive | pro/deep (~60-180s) | 1-3 minutes   |
| Novel/niche topic           | pro/deep            | 1-3 minutes   |

For HIGH-STAKES domains, ALWAYS use the deepest/pro model.
The extra wait time is justified by the quality of evidence gathered.

---

## Model Selection for Sub-Agents

When the environment allows model selection per sub-agent,
match model capability to the research task's demands.

### Fan-Out Research Sub-Agents

| Research Context | Model Tier | Rationale |
| --- | --- | --- |
| **Simple factual subjects** | Fast (sonnet-class) | Well-known topics with clear T1 sources; fast model finds them efficiently |
| **Technical comparisons** | Standard (sonnet-class) | Structured comparison is well-suited to capable but fast models |
| **HIGH-STAKES subjects** | Strongest (opus-class) | Forward-consequence CoK, T1 source validation, and safety-critical synthesis require deepest reasoning |
| **Novel/niche subjects** | Strongest (opus-class) | Sparse information requires creative search strategies and careful synthesis |
| **Master synthesis** | Strongest (opus-class) | Cross-subject comparison, gap identification, and unified answer are the highest-value reasoning steps |

### Cost Optimization

For a 5-subject research request with mixed complexity:
- 3 simple subjects → fast model sub-agents
- 2 complex/high-stakes subjects → strongest model sub-agents
- Master synthesis → strongest model

This mixed strategy can reduce total pipeline cost by ~30-40%
compared to using the strongest model for all agents,
with minimal quality impact on the simple subjects.

### When Model Selection Is Unavailable

Use the default model for all sub-agents.
The context isolation benefit alone (70-85% master context reduction)
justifies sub-agent dispatch even without model differentiation.
