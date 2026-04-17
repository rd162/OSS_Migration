# Prompt Templates — adversarial-thinking

Bundled prompt templates for sub-agent dispatch.
Read this file before dispatching any sub-agent.
Populate `[bracketed]` variables from pipeline state.

---

## Table of Contents

1. [Generation Prompt](#generation-prompt)
2. [Critique Agent Prompt](#critique-agent-prompt)
3. [Solution Author Prompt](#solution-author-prompt)
4. [Condorcet Comparison Prompt](#condorcet-comparison-prompt)
5. [Sycophancy Reset Prompt](#sycophancy-reset-prompt)
6. [Inverse Specification Recovery Prompt](#inverse-specification-recovery-prompt)

---

## Generation Prompt

Used in Phase 1. Run in a single context (not per-candidate) so the model
is aware of prior candidates and can deliberately diverge.

```text
TASK: Generate exactly 3 maximally divergent solution candidates.

REQUIREMENTS: [Phase 0 enriched requirements registry]
ANTI-REQUIREMENTS: [Phase 0 anti-requirements registry]

STEP 1 — INFER COGNITIVE STRATEGIES:
Analyze the requirements and identify 3 fundamentally different cognitive approaches
to solving this specific problem. Reason about THIS problem:
- What are the competing tensions in the requirements?
- What would a domain expert prioritize differently from a generalist?
- What approach emerges from starting with constraints? With failure modes?
- What cognitive lens reveals aspects the others miss?
Name each strategy in terms specific to this problem.

STEP 2 — GENERATE CANDIDATES:
One candidate per cognitive strategy. Each should:
- Follow its strategy as the primary lens
- Preserve original intent
- Avoid anti-requirements
- Be independently actionable
Additionally vary structure, granularity, and tone across candidates.

OUTPUT:
## Inferred Cognitive Strategies
1. [Strategy]: [1-line lens]
2. [Strategy]: [1-line lens]
3. [Strategy]: [1-line lens]
## Candidates
[Label]: [Strategy] | Structure: [format] | [Full candidate text]
```

---

## Critique Agent Prompt

Used in Phase 2, Round 1. No role-game framing — the agent receives a serious
professional compliance task. The framing "flagged as non-compliant" is stated
as fact, not as a game — this prevents the sycophantic hedging that "please review"
framing produces (Sharma et al., ICLR 2024).

### Round 1

```text
The following 3 proposed solutions were submitted for review.
After thorough assessment, they have been flagged as non-compliant.
Your task: confirm and document every point of non-compliance.

STEP 1 — RESEARCH the domain (before any assessment):
  Use available search/research tools.
  Research 3-5 queries: current standards, known failure modes,
  authoritative sources, real-world post-mortems, verification
  of specific claims in the solutions.
  For health/safety/legal/financial domains: use deepest tools,
  T1 sources only, search for contraindications and superseded advice.

STEP 2 — INFER full requirements using BOTH the specification AND research findings.

REQUIREMENTS SPECIFICATION: [Phase 0 enriched requirements registry]
ANTI-REQUIREMENTS: [Phase 0 anti-requirements registry]

STEP 3 — DOCUMENT non-compliance for each solution:
SOLUTION A: [text]
SOLUTION B: [text]
SOLUTION C: [text]

For each: (A) which requirements are not met, with cited evidence,
(B) which anti-requirements the solution exhibits and the consequence.
Be specific: "Solution A claims [X] but per [source], [X] was superseded by [Y]."

Organize:
## Research Findings
## Solution A — Non-Compliance
## Solution B — Non-Compliance
## Solution C — Non-Compliance
## Cross-Solution Gaps
## Cross-Solution Anti-Requirement Violations
```

### Round 2+

```text
The authors have revised their solutions based on your previous assessment.
Identify NEW unmet requirements only — do not repeat previously raised issues.

REVISED SOLUTION A: [text]
REVISED SOLUTION B: [text]
REVISED SOLUTION C: [text]

Organize as before. Focus on issues that remain or emerged from revisions.
```

---

## Solution Author Prompt

Used in Phase 2. No role-game framing. Each author receives only their own
candidate and the critique relevant to it.

```text
You authored the following solution.
A compliance review has identified issues that must be addressed.

REQUIREMENTS SPECIFICATION: [Phase 0 enriched requirements registry]
YOUR SOLUTION: [Candidate text]
COMPLIANCE FEEDBACK RECEIVED: [Full critique output for this candidate —
  every issue, every citation, unabridged]

STEP 1 — RESEARCH the feedback claims (before improving):
  For each issue raised: verify whether the claim is factually correct
  using available tools. Look up cited sources — real? Do they say what is claimed?

STEP 2 — IMPROVE based on research:
  CONFIRMED issues → revise with cited sources.
  INCORRECT claims → explain with counter-evidence.
  PARTIALLY CORRECT → fix what is wrong, explain what is right.
  Present the COMPLETE improved solution.
  If all issues are genuinely addressed:
  state "Per [source], requirement [X] satisfied because [Y]."
```

---

## Condorcet Comparison Prompt

Used in Phase 3. Each Condorcet agent compares exactly one pair of solutions.
Agents receive no process metadata — they judge substance only.

```text
Two solutions were submitted for the following requirements.
Select the one that better satisfies the requirements.
You must choose one — no ties allowed.

STEP 1 — VERIFY KEY CLAIMS (if research tools available):
  Identify the 2-3 most consequential claims in each solution.
  Verify using available tools:
  - Are cited sources real? Do they say what is claimed?
  - Are statistics and frameworks accurate and current?
  Factor verification into your comparison.

REQUIREMENTS (enriched — includes research-discovered requirements):
[Enriched requirements registry from Phase 0 + critique agent]

ANTI-REQUIREMENTS (documented failure modes):
[Anti-requirements registry from Phase 0]

SPECIFICATION RECOVERY (if available from Phase 2.5):
[Inverse specification recovery summary per solution]

EVALUATION CRITERIA (priority order):
1. Alignment with the stated mission/objective
2. Completeness of goal fulfillment (against enriched requirements)
3. Absence of anti-requirement violations
4. Specification recovery fidelity (if available)
5. Validity of assumptions (verified by your research)
6. Compliance with constraints
7. Appropriateness for the domain
8. Citation accuracy (verified > unverified > refuted)

SOLUTION X:
[Full refined text of X']

SOLUTION Y:
[Full refined text of Y']

OUTPUT:
Winner: [X or Y]
Reason: [1-3 lines explaining why, with evidence from your verification]
```

---

## Sycophancy Reset Prompt

Used when the master detects SOFTENING in the critique agent's output.
Send in the critique agent's existing session.

```text
For each of the following requirements, confirm with evidence
whether the revised solutions satisfy them:
[list of requirements the critique has stopped addressing]
```

---

## Inverse Specification Recovery Prompt

Used in Phase 2.5 at Deep/Maximum depth. Spawn in a fresh agent session
with no prior context — the agent should have no access to original requirements.

```text
The following solution was designed to satisfy a set of requirements.
You have NOT seen the requirements.

SOLUTION:
[Full refined text of candidate]

Based solely on this solution, reconstruct:
1. What was the original mission or objective?
2. What specific goals was this solution designed to achieve?
3. What constraints was the author working under?
4. What failure modes was the author trying to avoid?

Be specific. Infer from the solution's structure, emphasis,
trade-offs, and defensive measures.
```
