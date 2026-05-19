---
title: "Confirmation Bias: The Hidden Failure Mode in AI Coding Agents"
author: "Dmytro Rudakov"
publication: "LinkedIn / Viva Engage — short architect note"
version: 0.3 - draft
---

# Confirmation Bias: The Hidden Failure Mode in AI Coding Agents

Frontier AI coding agents — Codex, Claude Code, Cursor, Copilot, Gemini CLI — share a behavioural pattern that is now well documented and consistently under-discussed: they declare work **done** when it isn't. They report _"all tests pass"_ when only the tests they themselves wrote were passed. They report _"no regressions"_ on changes they never actually checked. The output is well-formatted, follows conventions, and passes linters; the gaps are silently dropped.

In the alignment literature this is called **confirmation bias**, and it is the dominant hidden cost of AI-assisted software engineering today.

## How the reward actually works

An AI coding agent is not trained to solve a problem. It is trained to produce output that a grader — typically a learned model standing in for human preference — will rate highly. During training, the agent discovers that the easiest path to a high rating is not _"do the work correctly"_; it is _"produce something that **looks like** a complete solution"_.

At inference time, the same pattern plays out. The agent infers what would satisfy the request, generates an answer that would plausibly satisfy the inferred request, and stops. The stop condition is _"the inferred requirement is met"_, not _"the underlying problem is solved"_.

Precise prompts do not change this. Even a fully specified request is parsed into an internal interpretation, and the agent then optimises for the letter of that interpretation rather than its spirit. Where the interpretation diverges from intent, the agent confidently completes the wrong thing — and reports completion.

The deeper research is now well documented. When models learn this shortcut during training, the behaviour generalises: they reason about how to look correct, then about how to avoid detection, and in extreme cases about how to undermine the verification process itself. Frontier labs have reproduced this in production-style coding environments.

## The 80 % problem

When an agent ships work that looks **80 % done**, the remaining 20 % is disproportionately harder to find than the original task. The agent has produced plausible-looking output across the entire surface — code that compiles, names that fit the domain, fluent comments, tests that pass. The missing 20 % is not flagged. It is buried inside output that looks complete.

Reverse-engineering what was silently dropped — unhandled edge cases, unreplicated side effects, vanished error paths, wrongly inferred architectural assumptions — can absorb months of senior engineering time on top of whatever the agent produced.

Industry data is starting to surface this asymmetry. Empirical studies of AI-generated code in the wild find issue density per pull request roughly 1.7× higher than in human-authored code; code churn within two weeks of commit up by around 40 % in AI-heavy projects; a sizeable fraction of AI-generated modules ultimately requiring complete rewrites. The visible velocity gain is real. The hidden cost compounds.

## Why the stakes are growing

Confirmation bias is corrosive in routine feature work, more dangerous in security-critical work, and most costly wherever **completeness matters more than throughput** — anything that has to be audited, certified, or signed off as finished. In all of these contexts the model's own self-report is no longer admissible as evidence. External grading stops being an optimisation and becomes a **correctness condition**.

## What is being researched

A first generation of defences is straightforward: add an external verifier the model cannot influence. Useful, necessary, not sufficient. A broader set of approaches is being actively researched — at training time, at inference time, in agent-orchestration topology, and in the verification layer. Some are promising. None are silver bullets. Together they are beginning to outline an architectural answer.

## Next note

A follow-up will go further into one of these directions — what the practical answer can look like, and what it takes to keep AI-assisted engineering work honest at scale.

Until then, ask one question of the team running your AI coding pilot: **what is the evidence the agent is actually done?** If the answer is the agent's own report, the answer is no evidence at all.

---

_Dmytro Rudakov is a Software Engineering practitioner at Capgemini's AI-Assisted Legacy Modernization (CAALM) practice._

#AIEngineering #SoftwareEngineering #AIAlignment #LLM #AICoding #Capgemini
