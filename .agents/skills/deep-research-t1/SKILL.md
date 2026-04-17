---
name: deep-research-t1
version: "2.2"
description: >-
  Systematically gathers, validates, and synthesizes external knowledge
  using CoK graph-based expansion until saturation, combining a structured
  web search protocol (Δ1-Δ7) with temporal-aware querying, domain-specific
  source tiering (T1-T4), and deep research pipelines with sub-agent fan-out.
  Escalates research depth for high-stakes domains (medical, legal,
  pharmacology, psychology, engineering, financial) using forward-consequence
  CoK fills, T1-only evidence constraints, and safety disclaimers.
  Resolves source conflicts via tier-weighted recency ranking,
  exposes contradictions rather than silently resolving them,
  and degrades gracefully to training-knowledge-only mode.
  Use when user asks to "research this", "verify this", "deep dive",
  "think deeper", "systematic review", or needs authoritative knowledge.
  Supports sub-agent fan-out and persistent playbook generation.

argument-hint: "<topic> [--file deep_research.md]"
allowed-tools: WebSearch, WebFetch, Read, Write, Edit, Grep, Glob, AskUserQuestion
metadata:
  author: rd162@hotmail.com
  tags: chain-of-knowledge, web-search, source-tiering, deep-research, high-stakes, sub-agent-dispatch, graceful-degradation, domain-escalation, playbook-generation
---

# Deep Research

Systematic methodology for gathering, validating, and synthesizing
external knowledge using Chain of Knowledge (CoK) graph-based expansion
until saturation, executed via the Δ1-Δ7 web search protocol
with domain-specific source tiering.

## Invocation Context

This skill runs in two distinct environments with different activation mechanics:

### Claude Code (native runtime)

`/deep-research` is a first-class slash command with argument parsing.

```text
/deep-research swift concurrency
/deep-research kubernetes cost optimization --file infra.md
/deep-research --file existing-playbook.md   (re-researches and updates)
```

`argument-hint`, `user-invocable`, and `$ARGUMENTS` only work here.
All other environments ignore these frontmatter fields.

**Argument Parsing** — parse `$ARGUMENTS` before doing anything:

1. If `$ARGUMENTS` contains `--file <path>` — extract as output path.
   Everything else is the topic.
2. Else if a token ends in `.md` or contains `/` — treat as output path.
   Everything else is the topic.
3. Else treat ALL of `$ARGUMENTS` as the topic.
   Auto-generate path: `<topic-slug>.md` in the current working directory.
4. If `$ARGUMENTS` is empty — show help and stop:

```text
Usage:
  /deep-research swift concurrency
  /deep-research kubernetes cost optimization --file infra.md
  /deep-research --file existing-playbook.md   (re-researches and updates)
```

**Output mode:**

- File path resolved → `mode = file` (write playbook, see File Output section)
- No file path → `mode = inline` (answer in conversation, standard Δ1-Δ7)

For MCP environment setup (Zed, Cursor, Windsurf, Claude Desktop),
see @references/invocation-context.md.

## Disambiguation Step

_(Applies in all environments. In Claude Code, runs after argument parsing.
In MCP environments, runs based on conversation context.)_

Before executing, use **AskUserQuestion** if ANY of these apply:

- Topic has multiple common meanings — ask which one.
- Topic is too broad — ask what aspect matters.
- Topic implies unstated context (cloud provider, language, audience level).
- `mode = file` and file already exists — confirm update or overwrite.

Skip if the topic is specific and unambiguous.

## When to Use

- Factual claims requiring verification against current sources
- Current knowledge needed (versions, APIs, best practices, pricing)
- Technical comparisons or benchmarks
- Contested topics needing multiple authoritative sources
- Implementation or debugging with unfamiliar tools/APIs
- User explicitly asks to research, verify, or find current information

## When NOT to Use

- Pure logic or mathematical proofs (no external knowledge needed)
- Creative writing or opinion pieces
- Tasks where all information is already in project context
- User explicitly says to use training knowledge only

## Termination

| Signal    | Condition                                                        | Action                                            |
| --------- | ---------------------------------------------------------------- | ------------------------------------------------- |
| SATURATED | Core covered, or depth ≥ max, or relevance < 0.3, or budget out | STOP — synthesize and present findings            |
| NO_TOOLS  | Zero search/fetch tools available after Δ1 scan                  | Degrade — training knowledge with disclaimer      |
| EMERGENCY | External verification becomes impossible mid-protocol            | Mark uncertainty — never present as authoritative |

## Graceful Degradation

- **Full tooling** (search + scrape + summarize): Complete Δ1-Δ7 with deep research pipeline.
- **Partial tooling** (any single search tool): Δ1-Δ7 with reduced coverage.
- **No external tools:** Training knowledge ONLY with explicit disclaimer.
- **Limited budget:** Δ1-Δ3 only (strategy + execute), skip deep research pipeline.

The skill always produces output. The confidence level varies.

---

## High-Stakes Domain Escalation

**CRITICAL: Some domains carry life-affecting consequences.**
A wrong answer in medicine can cause death; in psychology, suicide;
in legal advice, imprisonment; in pharmacology, poisoning;
in structural engineering, building collapse.

**High-stakes domains:** Medical, Psychology, Pharmacology, Legal (advisory),
Structural/Civil engineering, Nutrition (medical), Childcare, Financial (advisory).

**Detection heuristic:**
If the answer could plausibly influence a decision affecting someone's
physical health, mental health, legal standing, financial security,
or physical safety — treat as high-stakes. When uncertain, **escalate**.
This follows Signal Detection Theory (Green & Swets, 1966):
false negative cost (catastrophic) >> false positive cost (tokens).

**Mandatory protocol when high-stakes detected:**

1. **Deep research MANDATORY.** Use the strongest available research tool.
   If none exists, compensate with 5-8 targeted searches constrained to T1 sources.
2. **Forward-consequence CoK MANDATORY.** Fill consequence and contraindication gaps:
   `(recommendation, interacts_with, ?)`, `(advice, contraindicated_for, ?)`,
   `(solution, assuming, ?)`, `(approach, if_wrong, ?)`,
   `(recommendation, superseded_by, ?)`, `(treatment, withdrawn_in, ?)`.
3. **T1 sources ONLY** for high-stakes claims. T2-T4 may inform direction but never override T1.
4. **Safety disclaimers ALWAYS.** "Consult a qualified [professional]."
   Mark confidence. Expose contradictions — never silently resolve them.
5. **CoK depth minimum L0-L4.** Do not stop at L2 — forward-consequence fills
   often reveal critical gaps at L3-L4.

See @references/domain-knowledge-matrix.md for forward-consequence CoK patterns by domain.

---

## Chain of Knowledge (CoK) Methodology

Build linked triples `(subject, relation, object)`,
identify gaps, and fill them via targeted search.

### Forward-Fill Pattern

```text
Known:  (Next.js, supports, SSR)  (SSR, improves, SEO)
Gaps:   (SSR, requires, ?)  (SEO, measured_by, ?)  (Next.js, competes_with, ?)
Action: Fill each ? via targeted search → expand graph → repeat
```

Forward-consequence fill extends this to discover what COULD GO WRONG —
mandatory for high-stakes domains. See High-Stakes Domain Escalation above
and @references/domain-knowledge-matrix.md for domain-specific patterns.

### Complexity-Informed Research Depth

Cynefin framework (Snowden & Boone, 2007) grounds depth selection:

| Domain Complexity | CoK Depth | Research Approach |
| ----------------- | --------- | ----------------- |
| **Simple** | L0-L2 | Standard Δ1-Δ7, few searches |
| **Complicated** | L0-L3 | Multiple angles, T1-T2 sources |
| **Complex** | L0-L4 | Deep research, broad sweep |
| **Chaotic** | L0-L4 + consequences | Maximum depth, forward-consequence fills |

### Expansion Levels and Stop Criteria

```text
L0: Initial topic → direct triples (relevance 1.0)
L1: First expansion → related concepts (~0.7)
L2: Second expansion → supporting details (~0.5)
L3: Third expansion → peripheral context (~0.3)
L4: Predicted relevance < 0.3 → STOP

Stop when ANY: all core covered, depth ≥ max, relevance < 0.3,
budget exhausted, circular references detected.
```

---

## Source Tiers

| Tier | Description                          | Default Confidence | Weight in Conflicts |
| ---- | ------------------------------------ | ------------------ | ------------------- |
| T1   | Peer-reviewed / official docs / RFCs | HIGH               | Strongest           |
| T2   | Expert blogs / established sources   | MED                | Strong              |
| T3   | Community forums / Stack Overflow    | LOW                | Weak                |
| T4   | Opinions / unverified claims         | LOW                | Weakest             |

When sources conflict, higher tier + more recent = stronger evidence.
Annotate every cited source with its tier.

---

## Web Search Protocol (Δ1-Δ7)

Seven steps from tool discovery to validated output. Skip none.

### Δ1: Tool Availability

Scan available tools. If zero external tools, switch to degraded mode.

### Δ2: Strategy

Get the current date (mandatory — NO hardcoded years):

```text
current_date = now(timezone="local")
current_year = extract year from current_date
```

**Check for high-stakes domain** (see above). If detected:
escalate to deep research, plan 5-8 searches, constrain to T1,
include forward-consequence CoK queries.

Plan 3+ searches covering different angles (5-8 for high-stakes):

- **Primary:** Official / peer-reviewed sources
- **Practitioner:** Real-world usage and experience
- **Comparative:** Benchmarks / analysis / alternatives
- **[HIGH-STAKES] Consequences:** Contraindications, interactions, failure modes
- **[HIGH-STAKES] Superseded:** Updated guidelines, retracted findings

See @references/domain-knowledge-matrix.md for domain-specific
tool selection, query patterns, and CoK depth guidance.

### Δ3: Execute

For each planned search: execute with temporal qualifiers
(use `{current_year}`, never hardcode),
record each finding with source URL + date + tier (T1-T4).

### Δ4: Organize

```text
SOURCES: [Source]:[Finding](T#) — at least 3
CONSENSUS: [What sources agree on]
CONTRADICTIONS: [Where sources disagree and why]
GAPS: [What remains unclear]
```

### Δ5: Weight

Resolve conflicts using source tier priority.
Higher tier + more recent = stronger evidence.

### Δ6: Output

```text
Based on [N] sources (searched: {current_date}):

[ANSWER]

Evidence:
- [Claim] (Source: [cite], T#)

[IF contested] Sources vary. Consult [authority].
[IF degraded] Training knowledge only. No external verification.
```

### Δ7: Validation Checklist

- Current date obtained (not hardcoded)?
- 3+ searches executed (5+ for high-stakes)?
- 3+ sources cited with URLs and tiers?
- Contradictions explicitly exposed?
- [HIGH-STAKES] Deep research tool used (or 5-8 T1-targeted searches)?
- [HIGH-STAKES] Forward-consequence CoK completed?
- [HIGH-STAKES] Safety disclaimer included?

If any item fails, fix before presenting.

---

## Deep Research Pipeline

For comprehensive research (20-50+ references). Use when: novel/niche topic,
systematic review needed, user says "deep dive," or HIGH-STAKES domain.

```text
1. Broad sweep: 20-50 references via multiple search tools
2. Filter: top 10 by relevance and tier
3. Summarize: key points from each candidate
4. Select: top 3-5 highest-quality sources
5. Extract: full content from selected sources
6. Synthesize: build CoK triples → comprehensive cited answer
```

### Sub-Agent Dispatch for Multi-Subject Research

**MANDATORY:** When research covers 2+ independent subjects
and a sub-agent mechanism is available,
dispatch each subject to a dedicated sub-agent.

| Subject count | Strategy |
| ------------- | -------- |
| 1 | Inline Δ1-Δ7 |
| 2-3 | One sub-agent per subject |
| 4-6 | Group related subjects (2-3 per agent) |
| 7+ | Group into 3-5 agents by affinity |

Each sub-agent independently executes full Δ1-Δ7.
Master synthesizes, compares, and identifies gaps.

See @references/sub-agent-dispatch.md for dispatch patterns,
output budgets, grouping heuristics, and model selection guidance.

### Deep Research Agent Polling Protocol

For asynchronous deep research tools: wait **minimum 30 seconds** between checks.
Use wait time productively — run standard Δ3 searches in parallel.

For HIGH-STAKES domains, ALWAYS use the deepest/pro model.
See @references/sub-agent-dispatch.md for full polling protocol.

---

## Knowledge Sources (Priority Order)

1. **Local docs** — project files, READMEs (project-specific context)
2. **LLM pattern files** — `llms*.txt` in current directory (domain patterns)
3. **Library docs** — Context7, official API references (authoritative)
4. **Web search** — any available search/scrape tools (current/external)
5. **Memory systems** — session memory, notes (cross-session continuity)

Check local sources before reaching for the web.
See @references/domain-knowledge-matrix.md for domain-specific tool selection.

---

## Example

```text
User: "What's the best state management for React?"

Δ1: Available tools: web search, scrape
Δ2: Strategy (date from now()):
  - S1: "React state management {current_year} comparison"
  - S2: "React state management production usage"
  - S3: "Redux vs Zustand vs Jotai benchmark {current_year}"
Δ3: Execute → 6 sources (T1: 2, T2: 3, T3: 1)
Δ4: Consensus: Zustand growing, Redux dominant in enterprise
    Contradictions: T3 "Redux is dead" vs T1 adoption data
Δ5: Weight: T1 > T3 → Redux dominant, Zustand rising fastest
Δ6: Output with 6 cited sources, tiers annotated
Δ7: Validation checks pass
```

---

## File Output (mode = file)

When a file path is resolved from `$ARGUMENTS`, write findings
to a persistent markdown playbook instead of answering inline.

- **Create mode** (file doesn't exist): Run Δ1-Δ7, group into sections, write with source URLs
- **Update mode** (file exists): Target changes since `Captured:` date, merge inline, preserve voice
- Every claim MUST have a source URL. Voice: direct, concise, practitioner-focused.

See @references/file-output-protocol.md for full create/update protocols,
templates, and the verification step.

---

## Anti-Patterns

```text
✗ Hardcoded years in search queries ("React 2024 state management")
✓ Dynamic year from now() ("React {current_year} state management")

✗ Single search, single source → presenting as authoritative
✓ 3+ searches, 3+ sources with tier annotations

✗ Skipping source tiers → treating blog post same as official docs
✓ T1-T4 tier annotation on every cited source

✗ Ignoring contradictions between sources
✓ Explicitly exposing contradictions with tier-weighted resolution

✗ Halting because no search tools are available
✓ Degrade gracefully: use training knowledge with explicit disclaimer

✗ Presenting training knowledge as current fact without verification
✓ Search first, cite sources, mark uncertainty when present

✗ Standard-depth search for medical, psychology, or legal questions
✓ HIGH-STAKES: deep research mandatory, T1 only, forward-consequence CoK

✗ Researching 3+ independent subjects sequentially in master context
✓ Fan-out to sub-agents: one per subject, each runs Δ1-Δ7 independently

✗ Polling deep research status every 5 seconds
✓ Wait minimum 30 seconds between deep research status checks
```

---

## Environment Compatibility

- **Full capability:** Multiple search + scrape + summarize tools → best results
- **Partial:** Any single web search tool → reduced coverage, protocol still applies
- **No external tools:** Training knowledge with explicit disclaimer → degraded but functional
- **Claude Code / Cursor / Codex / Gemini CLI / Kimi:** Works with any available search tools

## Formal Basis

- **CoK expansion:** Li et al., 2023 — triple-based graph expansion with saturation as fixed-point detection.
- **Source tiering:** T1-T4 hierarchy operationalizes ISO 25012 Accuracy dimension.
- **Complexity-informed depth:** Cynefin domains (Snowden & Boone, 2007) map to CoK depth.
- **High-stakes detection:** Asymmetric threshold per SDT (Green & Swets, 1966).
- **Knowledge conversion:** Δ4 = SECI Combination; File Output = SECI Externalization (Nonaka & Takeuchi, 1995).
- **Δ4 output structure:** Frame with named slots per Minsky's Frame Theory (1975).

See `references/academic-references.md` for full citations and provenance.

## References

See `references/academic-references.md` for full citations and provenance.

Key references: Li et al. 2023 (CoK), Xu et al. 2025 (Search-o1),
Snowden & Boone 2007 (Cynefin), Green & Swets 1966 (SDT),
Nonaka & Takeuchi 1995 (SECI).
