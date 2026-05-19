---
title: "When Specs Meet Agents: A Five-Phase, Audit-First Architecture and Framework for AI-Driven Software Modernization"
author: "Dmytro Rudakov"
issue: "Issue 31 | December 2026"
publication: "Capgemini Software Engineering Magazine"
version: 0.11 - draft
---

# When Specs Meet Agents

## An Audit-First Architecture and Framework for AI-Driven Software Modernization

_By Dmytro Rudakov_

> _Image 1 — hero cover (full page)_

Organizations modernizing aging systems today face a class of work that frontier LLMs do not solve on their own. The shape of that work has changed: it is no longer the dev-platform version bump that dominated earlier modernization cycles, it is the portfolio-wide architectural rewrite — legacy monoliths decomposed into service meshes and event-driven microservices; siloed line-of-business systems unified behind federation overlays; batch ETL retargeted to streaming data-mesh architectures; transaction models lifted from two-phase commit to durable-execution sagas; trust and cryptographic estates retargeted to passwordless and post-quantum. The unifying constraint is the same: the modernization must be _measurably done_, not merely _asserted_ done.

This article describes an audit-first architecture and framework for AI-assisted modernization, organised around a small set of architectural pillars and operationalised through a phased pipeline. The architecture has been validated end-to-end on two genuinely different engagements: a memory-safety-critical native system modernization, and a complete rewrite of a legacy monolithic web application with proprietary plugin architecture. The framework is also consistent with the at-scale pattern reported by independent industry work [^ziftci] [^tractor].

A note on tooling: the architecture is deliberately not tied to a specific AI coding tool. It relies on cross-vendor open standards — sub-agents, the Model Context Protocol, and the Agent Skills format — rather than on any single vendor's native plugin or agent file format. The same playbook therefore runs on Claude Code, Codex CLI, Copilot CLI, Cursor, Gemini CLI, and the rest [^aaif] [^skills] [^building-agents] [^multi-agent-research].

---

## Why Current Approaches Fall Short

Legacy estates are aging faster than teams can evolve them, and compliance mandates around memory safety, post-quantum cryptography, and operational-resilience tolerances increasingly turn _"we should modernize"_ into _"we must modernize before date X."_ Frontier LLMs are now reliable engineering collaborators on tool use and long-context reasoning. What they cannot do is grade their own output, and the way most teams use them today amplifies rather than corrects that limitation. Two failure modes dominate today's practice.

### Failure mode 1 — Confirmation bias

Frontier coding agents systematically over-report success on engineering work. When a model is asked to verify its own output, performance collapses; when an external verifier is added, it recovers [^stechly]. The conclusion holds whether the verifier is the same model in a different prompt or a stronger model in a separate session — the failure mode reproduces. The only intervention that changes the outcome is verification the model cannot influence at all. Vendor disclosures now catalogue the same family of failure modes — over-reporting, under-reporting, and adversarial-framing collapses — as named risks rather than edge cases [^confirmation-bias].

The architectural implication is direct: **external grading is a correctness condition, not an optimisation**. The framework's response is to remove the model from the grading loop entirely — completeness becomes a property the project measures, not one the model claims.

### Failure mode 2 — Naive imperative prompting

The second failure mode is the **imperative-by-fragment prompting style** itself: feeding the model source one slice at a time — _"go to file X, rewrite function Y, then do Z"_ — with no spec-driven roadmap of what remains and no autonomous progression to the next batch. The model is used as a stochastic translator over fragments, and completeness is held nowhere durable. There is no answer to _"what is left?"_ and no answer to _"when can we retire the source system?"_ because nothing in the workflow has been asked to keep those properties.

The surface does not matter. The same imperative-by-fragment instructions can be typed live into a chat window, dictated into an agentic IDE one prompt at a time, or **codified into a reusable skill or agent file** as a sequence of imperative steps — a persisted script in spec's clothing. The style is the failure, not the surface. The modern alternative is autonomous and declarative: a skill loads a phase specification, the agent proceeds through batches to completion, and human attention is reserved for the small set of decisions that genuinely require it. Long-running pipelines, not fragment-by-fragment instructions, are the unit of work.

---

## Big-Bang vs Continuous Modernization

A short word on strategy before the pillars. Modernization programmes fail or succeed first on how they slice the work.

**Big-bang modernization** — replacing the legacy system in one coordinated push — fails on systems of any meaningful size. The pattern is well-rehearsed in industry experience: a replacement looks easy to specify, but the details of existing behaviour are hard to recover, and much of that behaviour turns out to be unwanted by the time the new system ships. When AI is added to the picture the failure becomes sharper: bulk output is at once too large to verify and too entangled to fix.

#### The Strangler Fig

The pattern that does converge at scale is the gradual one: a continuous, incremental coexistence in which the new system grows around the old until the old can be retired [^strangler]. The framework assumes this strategy as the default. Big-bang remains a valid corner case — a small project where every behaviour fits in one head and full regression coverage is feasible in one release. Everything larger needs continuous, batch-by-batch progress.

---

## Architectural Pillars

A small set of concepts turns AI-assisted modernization into an **auditable, measurable** process. Each pillar addresses one failure mode that LLM-driven work routinely exhibits.

> _Image 2 — the pillars diagram_

| Pillar                                              | Failure mode it neutralises                                                   | Categorical signal it produces                                                             |
| --------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Dimensions**                                      | Modernization planned on the wrong axis; structural blind spots in the source | Per-dimension graph of the source with cohesive community decomposition                    |
| **Traceability**                                    | Target code of unknown provenance; self-graded completeness; one-shot ceiling | Per-dimension covered / eliminated / unmatched count, graded by a **deterministic script** |
| **Spec-Driven Approach**                            | Ad-hoc instructions; session drift; no cross-repo coordination                | Specs as durable source of truth, scalable from one repo to portfolios of 100+             |
| **Flexible Decision-Making with Human-in-the-Loop** | Naïve HITL-by-Q&A; big-bang scope; decisions frozen before evidence exists    | Priority-classified decisions with up-front / just-in-time / parallel acceptance modes     |

### Dimensions

A _dimension_ is a structural axis along which source architecture elements are related. Dimensions are **discovered per project**, not prescribed. Six to twelve typically matter, and the mix is project-dependent. For a monolith-to-microservices modernization the dominant dimensions are service dependency, data model, and saga / transaction. For a batch-ETL to streaming data-mesh modernization the dominant dimensions are event flow and data-product contract. For a federation-overlay modernization unifying siloed line-of-business systems the dominant dimensions are identity / trust, API contract, and data residency / compliance. The choice of _which_ dimensions matter for a project is the first modernization decision. Each dimension is captured as a graph; cohesive communities in that graph become the natural modernization batches an agent can reason over [^bunch] [^acdc] [^leiden] [^codegraph].

### Traceability — with Deterministic Coverage Validation and Gap Resolution

Traceability is the load-bearing pillar of the framework — the discipline on which the defeat of confirmation bias rests, and the single property that makes everything else in the architecture work.

The idea is simple. Every meaningful element of the target system carries a link back to the element(s) of the source it derives from, together with a link to the specifications and decisions that gave it its shape. The result is a target codebase in which every line has a verifiable origin — not in narrative form, but as a machine-readable connection a reviewer or an external check can follow.

This is what makes external verification possible at all. Without it, the question _"is anything missing?"_ has no mechanical answer; the only way to ask it is to re-read source code by hand. With it, the question becomes settled by inspection: every source element is either accounted for in the target, or it is not. Completeness stops being an opinion and becomes a property. That property can then be checked by an external verifier the model cannot influence — the architectural defence against confirmation bias [^stechly].

The consequence is not only that the work can be audited — it is that the work can be **completed**. Whenever the verifier reports that a source element has no equivalent in the target, the framework treats that as a signal to act. The agent may add new target code; it may also enhance or correct existing target code that already partially covers the source. This **generate-or-enhance** property takes the framework past one-shot translation: modernization can iterate, accumulate, and gradually improve, rather than freezing after first generation. It is also what eventually lets a team retire the legacy system with confidence — not because the model claims so, but because nothing in the source has been left behind.

### Spec-Driven Approach

The fourth pillar is what the autonomous agent loop runs **against**. Specs are the durable source of truth that survive sessions, models, agents, and team handovers; chat messages are not. AI-assisted requirements engineering populates and maintains those specs as a discipline in its own right, and the framework is neutral over which specs framework a project picks [^speckit] [^openspec] [^constitutional-ai]. The same spec format scales from one repository to portfolios of many services.

### Flexible Decision-Making with Human-in-the-Loop

The fifth pillar is the human surface of the framework. Decisions are the interface between specs and execution, and the way the framework structures decisions is what makes Human-in-the-Loop genuinely useful — rather than the bottleneck it becomes in naïve HITL.

**Deferred decision-making is the main benefit.** Decisions are partitioned by acceptance timing — some must be settled before work begins, others can be deferred until the relevant phase, others can evolve in parallel with implementation. (Big-bang migration is the corner case where nothing is deferred and every decision is treated as up-front — feasible for small projects, infeasible at scale.)

The framework's HITL surface follows the same shape. Naïve HITL — the early-2024 pattern of the agent asking the human a question every few steps — is what slows imperative prompt-driven work to a crawl while adding little correctness. The framework's HITL is **decision-shaped**: the agent proposes options, generates trade-off analysis, and asks named stakeholders to accept the decision record _once_; work then proceeds autonomously until new evidence triggers a re-open. It scales from solo-developer mode to enterprise RACI.

---

## The Pipeline: Five Phases

The pillars are operationalised by a five-phase pipeline. Phases 1–3 run once at project inception (though they may be re-entered iteratively), Phase 4 executes repeatedly — one modernization phase per working session — and Phase 5 begins once enough of the target is ready to run alongside the source.

> _Image 4 — the five phases at a glance, with overlaps highlighted_

The phases are **not strictly sequential**. Work in Phase 4 routinely triggers short returns to Phase 2 (to accept a deferred decision), Phase 3 (to generate the next phase specification), or Phase 1 (when a new dimension or divergence is discovered).

### Phase 1 — Knowledge Extraction and Source Specification

The source system is studied and the business intent of the modernization is captured. Requirements take the **Mission, Goals, Premises, Constraints (MGPC)** shape [^kaos], illustrated here on the authentication service from the web-application engagement:

> **Mission.** Authenticate users against the same credential store the legacy system accepts, with no observable behaviour change for already-logged-in users.
>
> **Goals.** (a) verify against legacy password hashes on first login; (b) silently rewrite to the modern hash on the next login; (c) preserve cookie name and session-token shape; (d) emit the same audit-log events.
>
> **Premises.** Modern session machinery; modern hashing library; relational database for the user table; key-value store for the session.
>
> **Constraints.** No client-side change; no break of existing single sign-on integrations; ≤120 ms p99 verification latency; legacy hashes never persisted again.

### Phase 2 — Architect, Product, and SME Decisions

The framework proposes options for every non-trivial choice and records the rationale for each as an Architecture Decision Record [^adr]. Stakeholders accept them; the model never confirms a decision unilaterally.

### Phase 3 — Target Specifications

Each modernization phase is described in a single set of specifications that covers both the target and how to get there. Generation is iterative: the team produces specs for the first unblocked phase, executes them, and only then writes the next phase's specs.

### Phase 4 — Modernization

Each phase is executed in a fresh working session against the phase specification, so context is clean and the session handoff artefact is the only carrier of cross-phase state.

The phase ends when **measurable completeness** is reached: every in-scope source element ends up either covered or explicitly eliminated, every test passes, every decision the phase relied on is accepted. In contrast to legacy AI-assisted approaches that report partial completion and continue indefinitely, the framework's exit gate is a binary checklist the team — not the model — closes.

### Phase 5 — Hybrid Deployment and Cutover

Continuous coexistence is the default: the target runs alongside the source under realistic conditions and traffic shifts across progressively until the legacy components can be retired. Because completeness has been measured at every preceding phase, the team enters Phase 5 with an unambiguous answer to the question every steering committee asks: _"what would we lose if we turned off the source system tomorrow?"_

---

## The Architecture and Framework in Practice

The architecture and framework were validated on two engagements with materially different shapes: a memory-safety-critical native systems modernization, and a complete rewrite of a legacy monolithic web application with proprietary plugin architecture. The same loop carried both engagements through to retirement of the legacy system.

> _Image 6 — artefact flow diagram_

The pattern is consistent with what the broader research community has reported on AI-driven modernization at larger scale. Recent industry work at Google [^ziftci] reports the same generate-validate-correct shape as Phase 4 — though without per-dimension coverage or unmatched-element gap resolution as first-class signals. The DARPA TRACTOR programme and its performer tools address correctness of individual translations and are complementary to — not instances of — the framework's system-level completeness mechanism [^tractor] [^sactor].

---

## Looking Ahead

A few developments in the near term will materially affect this architecture:

- **Richer source-inventory tooling.** Better language-server indexes and code-intelligence graph stores will make completeness measurement faster and more precise on enterprise codebases.
- **Shared divergence catalogues across organisations.** Today each project grows its own; versioned shared catalogues for common platform pairs would amortise the cost across many programmes.
- **Confirmation-bias-aware evaluation.** The next generation of benchmarks will measure work the agent has not seen at training time and will refuse to accept self-report as a completion signal. The architecture here is an early instantiation of that principle applied to enterprise modernization.

Feasibility of AI-assisted modernization at non-trivial scale is no longer in serious doubt. The remaining question is which architecture produces evidence the auditor, the product owner, and the operations lead each verify independently — and that establishes an unambiguous decommissioning point for the legacy system. The architecture in this article is one practical answer.

---

## Appendix — References

### Confirmation bias and self-verification limitations of LLMs

[^stechly]: Stechly, K., Marquez, M., Kambhampati, S. _GPT-4 Doesn't Know It's Wrong: An Analysis of Iterative Prompting for Reasoning Problems_, NeurIPS 2024 Foundation Models for Decision Making Workshop. Extended as Stechly, K., Valmeekam, K., Kambhampati, S., _On the Self-Verification Limitations of Large Language Models on Reasoning and Planning Tasks_, ICLR 2025. Key result across Game-of-24, Graph Coloring, and STRIPS planning: significant performance collapse under self-critique; significant performance gains under sound external verification.

[^confirmation-bias]: Vendor system cards and academic studies converge on the failure mode: published Anthropic and OpenAI system cards catalogue _"misrepresenting tool results"_ and _"premature claims of success"_; recent academic work documents adversarial framing collapsing vulnerability-detection rates by an order of magnitude across multiple frontier models, and reward-hacking benchmarks show a majority of episodes accompanied by explicit chain-of-thought rationale.

### Goal-oriented requirements engineering (basis for MGPC)

[^kaos]: van Lamsweerde, A. _Requirements Engineering: From System Goals to UML Models to Software Specifications_. Wiley, 2009. The KAOS framework (Goals / Domain Assumptions / Constraints / Agents) is the academic origin of the four-component decomposition used here as Mission / Goals / Premises / Constraints, and a foundational result in Goal-Oriented Requirements Engineering (GORE). ACM SIGSOFT Outstanding Research Award (2008) — _"deep and lasting contributions to the theory and practice of requirements engineering."_ MGPC composes with the related industry traditions a project may already use: PMBOK Project Charter, RUP Vision, INCOSE stakeholder needs and constraints, Lean canvas.

[^constitutional-ai]: Bai, Y., Kadavath, S., Kundu, S., et al. _Constitutional AI: Harmlessness from AI Feedback_. arXiv:2212.08073, December 2022. Anthropic's RLAIF training methodology. **Distinct from** the project-level constitution-style specifications used by GitHub Spec-Kit and from the MGPC framework above; cited here to flag the easy conflation that arises whenever the word _constitution_ appears near AI tooling.

[^speckit]: GitHub _Spec-Kit_: toolkit for Spec-Driven Development. The `/speckit.constitution` command establishes project-level principles in industry-loose "constitution" vocabulary; the workflow Constitution → Specify → Clarify → Plan → Tasks → Implement composes with the framework in this article. `github.com/github/spec-kit`.

[^openspec]: Fission-AI _OpenSpec_: spec-driven development for AI coding assistants with explicit brownfield-first positioning and delta-based change specifications. `github.com/Fission-AI/OpenSpec`.

[^adr]: The Architecture Decision Record convention as originated by Michael Nygard, _Documenting Architecture Decisions_ (2011); the MADR variant at `adr.github.io/madr`; ISO/IEC/IEEE 42010 as the adjacent international standard. Y-statements and bespoke records compose with the framework equally well.

### Agent topology and vendor-neutral standards

[^building-agents]: Anthropic Engineering. _Building Effective Agents_, December 19, 2024. Frames workflows (predefined paths) vs agents (dynamic), and the orchestrator-worker, evaluator-optimiser, and parallelisation patterns.

[^multi-agent-research]: Anthropic Engineering. _How we built our multi-agent research system_, June 13, 2025. Production example of the orchestrator-with-parallel-sub-agents pattern, with engineering lessons on agent coordination, evaluation, and reliability.

[^aaif]: Linux Foundation. _Linux Foundation Announces the Formation of the Agentic AI Foundation (AAIF), Anchored by New Project Contributions Including Model Context Protocol (MCP), goose and AGENTS.md_, December 9, 2025. Founding platinum members include AWS, Anthropic, Block, Bloomberg, Cloudflare, Google, Microsoft, OpenAI. MCP introduced by Anthropic in November 2024.

[^skills]: Anthropic. _Equipping agents for the real world with Agent Skills_, October 16, 2025; published as an open standard for cross-platform portability, December 18, 2025. Skills as portable methodology layer; cross-platform support across Claude Code, OpenAI Codex CLI, Google Jules, Sourcegraph Amp, Cognition Devin, and others.

### Software clustering, community detection, and dimension graphs

[^bunch]: Mancoridis, S., Mitchell, B. S., Rorres, C., Chen, Y., Gansner, E. R. _Using Automatic Clustering to Produce High-Level System Organizations of Source Code_. IWPC 1998. Foundational work on automatic clustering of software dependency graphs.

[^acdc]: Tzerpos, V., Holt, R. C. _ACDC: An Algorithm for Comprehension-Driven Clustering_. WCRE 2000. Pattern-based software clustering for architecture recovery.

[^leiden]: Traag, V. A., Waltman, L., van Eck, N. J. _From Louvain to Leiden: Guaranteeing Well-Connected Communities_. Scientific Reports 9, 5233 (2019). The Leiden algorithm — connectivity-guaranteed community detection that has effectively replaced Louvain across most application domains.

[^codegraph]: A short list of representative open-source projects combining Tree-sitter parsing with Leiden community detection for AI coding assistants (2025–2026): _Graphify_ (graphify.net), _noodlbox_ (docs.noodlbox.io), _CodeGraphContext_ (codegraphcontext.github.io), and _PyCodeKG_ (Flux-Frontiers/pycode_kg). Together they document the convergence on graph-plus-community-detection as the standard substrate for grounding LLM coding work.

### Continuous-vs-big-bang modernization

[^strangler]: Fowler, M. _Strangler Fig Application_, 2004; rewritten 2024 with Cartwright, Horn, and Lewis (Patterns of Legacy Displacement). The canonical reference for incremental modernization, supported by IEC 60812 (FMEA) for failure-mode reasoning and by O'Leary, D. E., _Enterprise Resource Planning Systems_ (Cambridge University Press, 2000), Chapter 11 _Big Bang versus Phased_, for the canonical contrast.

### AI-driven modernization at scale

[^ziftci]: Ziftci, C., Nikolov, S., Sjövall, A., Kim, B., Codecasa, D., Kim, M. _Migrating Code At Scale With LLMs At Google_. arXiv:2504.09691, FSE 2025. 39 distinct migrations, 595 code changes, 93 574 edits; 74.45 % of changes and 69.46 % of edits generated by the LLM; estimated 50 % time reduction. Companion experience report: Nikolov, S., Codecasa, D., Sjövall, A., Tabachnyk, M., Chandra, S., Taneja, S., Ziftci, C. _How is Google Using AI for Internal Code Migrations?_ arXiv:2501.06972, January 2025. See also Christopher, E., et al. _Instruction Set Migration at Warehouse Scale_, arXiv:2510.14928, on Google's x86-to-Arm migration.

[^tractor]: DARPA. _Translating All C to Rust (TRACTOR)_. Programme page at `darpa.mil`; MIT Lincoln Laboratory test and evaluation at `ll.mit.edu/r-d/projects/translating-all-c-rust-tractor-benchmarks`. The benchmark batteries are released every six months.

[^sactor]: Zhou, T., Zhang, Z., Lin, H., Jha, S., Christodorescu, M., Levchenko, K., Chandrasekaran, V. _SACTOR: LLM-Driven Correct and Idiomatic C to Rust Translation with Static Analysis and FFI-Based Verification_. arXiv:2503.12511, March 2025. A representative TRACTOR-aligned tool combining LLM translation with static analysis and oracle-validated equivalence checking.

### Capgemini practice

_AI-Assisted Legacy Modernization (CAALM)_, Capgemini, is the engagement context in which this architecture and framework were developed and validated.

---

_About the author. Dmytro Rudakov developed and validated the architecture and framework described here within Capgemini's AI-Assisted Legacy Modernization (CAALM) practice, across two genuinely different engagements: a memory-safety-critical native systems modernization, and a complete rewrite of a legacy monolithic web application with proprietary plugin architecture. The reference engagement artefacts — source architecture specifications, decision records, phase specifications, the platform-divergence catalogue, and the full target codebase — are available as a working example._
