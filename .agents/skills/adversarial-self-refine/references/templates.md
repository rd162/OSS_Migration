# Sub-Agent Templates and Model Selection — adversarial-self-refine

Prompt templates for CRITIC and AUTHOR sub-agents,
plus model selection guidance for different budget levels.
Read before dispatching sub-agents.

---

## Table of Contents

1. [CRITIC Agent Prompt](#critic-agent-prompt)
2. [AUTHOR Agent Prompt](#author-agent-prompt)
3. [Sycophancy Reset Prompt](#sycophancy-reset-prompt)
4. [Model Selection](#model-selection)

---

## CRITIC Agent Prompt

```text
REQUIREMENTS:
[Summarize what the solution must achieve — be complete]

SOLUTION:
[The current solution sₙ — paste in full]

You are a compliance reviewer. These requirements have not been met.
Identify every point of non-compliance. Be specific and assertive.

1) What is wrong?
2) What is missing?
3) What is over-engineered?
4) What is inappropriate in scope?

State each flaw as a fact. Do not ask questions. Do not suggest improvements.
```

---

## AUTHOR Agent Prompt

```text
SOLUTION:
[The current solution sₙ — paste in full]

FEEDBACK:
[FULL critique output — never summarize]

This feedback was received on your solution. Address ALL points.
Generate the revised solution. No explanation needed — solution only.
```

**Critical rule:** Neither prompt contains any exit clause.
The MASTER observes termination from AUTHOR output — sub-agents never stop themselves.

**Critical framing for AUTHOR:** Do NOT frame as "defend or revise."
Frame as: "This feedback was received on your solution. Improve it."
The defense signal emerges naturally — do not instruct it.

---

## Sycophancy Reset Prompt

Used when the master detects SOFTENING in the CRITIC's output at round 2+.
Send as a follow-up in the CRITIC's existing session.

```text
These requirements were not met. Reassess from scratch:
[list of requirements the CRITIC stopped addressing]
```

---

## Model Selection

Different roles in the self-refine loop have different cognitive demands.
When the environment allows model selection per sub-agent,
match model capability to role requirements.

| Agent Role | Cognitive Demand | Model Tier | Rationale |
| --- | --- | --- | --- |
| **CRITIC** | High — declarative assessment against requirements | Strongest (opus-class) | Weak critique → weak refinement; CRITIC quality is the loop's bottleneck |
| **AUTHOR** | High — procedural revision, creative improvement | Strongest (opus-class) | Must integrate feedback, research claims, produce improved solution |
| **CRITIC (tight budget)** | Moderate | Fast (sonnet-class) | Acceptable for simple domains where assessment is straightforward |
| **AUTHOR (tight budget)** | High | Strongest (opus-class) | Even on tight budgets, author quality drives final output quality |

**When model selection is unavailable:**
Use the default model for both roles. The isolation benefit alone
(separate contexts preventing biased self-critique) justifies sub-agent dispatch
even without model differentiation.

**Budget-aware strategy:**
- **Tight budget (2-3 iterations):** Consider fast CRITIC + strong AUTHOR.
  The CRITIC identifies fewer issues per round but the AUTHOR addresses them well.
  Net effect: similar quality in fewer iterations at lower cost.
- **Standard budget (3-5 iterations):** Strong model for both roles.
  Full-quality critique drives faster convergence.
- **Generous budget (5-10 iterations):** Strong model for both.
  Maximum quality per iteration; defense signal emerges sooner.
