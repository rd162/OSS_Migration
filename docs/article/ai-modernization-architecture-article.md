---
title: "When Specs Meet Agents: A Five-Phase, Audit-First Architecture for AI-Driven Software Modernization"
author: "Dmytro Rudakov"
issue: "Issue 31 | December 2026"
publication: "Capgemini Software Engineering Magazine"
---

# When Specs Meet Agents

## A Five-Phase, Audit-First Architecture for AI-Driven Software Modernization

_By Dmytro Rudakov_

> _Image 1 — hero cover (full page)_

Organizations modernizing aging codebases face a hard problem that frontier LLMs do not solve on their own: how to evolve a non-trivial system into a target architecture — whether a major version upgrade (Java 8 → Java 26, .NET Framework → .NET 9, Python 2 → 3, Spring Boot 2 → 3), a framework shift, a cross-language re-implementation, a monolith-to-microservice decomposition, or a full cloud-native re-architecture — so completely, faithfully, and verifiably that the modernization is _measurably done_, not merely _asserted_ to be done.

This article introduces a five-phase architecture for AI-assisted software modernization, anchored in four operational pillars: Dimensions, Traceability, Coverage Validation, and Modernization-Gap Resolution. It is technology-agnostic — the same pipeline applies to language-version upgrades, framework shifts, cross-language re-implementations, monolith-to-microservice decompositions, data-pipeline rewrites, and protocol-library ports. It has been validated end-to-end on a complete PHP-to-Python modernization of a non-trivial web application, and it is consistent with the architectural pattern emerging from independent industry research, including DARPA's TRACTOR programme for C-to-Rust modernization and Google's recently-published at-scale LLM-assisted code modernization (Saavedra et al. 2025).

---

## The Scale of the Problem: Why Current Approaches Fall Short

Three forces are converging into a significant modernization opportunity, and a corresponding gap.

**Legacy codebases are aging faster than teams can evolve them.** Many enterprises run systems built fifteen or twenty years ago on platforms — older language versions, deprecated frameworks, end-of-life databases — that limit hiring, raise operational risk, and block security and compliance work. Compliance mandates around memory safety, credential storage, and prepared statements increasingly turn _"we should modernize"_ into _"we must modernize before date X."_ The U.S. Government Accountability Office reported in 2023 that roughly 80% of the federal IT budget — over $100 billion annually — is spent operating and maintaining legacy systems. The UK government's equivalent figure is £2.3 billion per year on systems some of which date back thirty years or more.

**Frontier LLMs have become viable partners for engineering work.** Frontier models since the Claude Opus 4.5 / GPT-5.1 generation are reliable enough at tool use and long-context reasoning to be production collaborators on engineering tasks. What they cannot do, as the rest of this section establishes, is grade their own output.

**Yet there is no broadly-adopted framework for using these models on real modernization programmes.** Despite the surge of recent academic work and several promising vendor announcements, no widely-deployed methodology exists for running an end-to-end LLM-driven modernization in a way that satisfies a security auditor, a product owner, and a compliance lead at the same time. The reason is more subtle than capability: it is _what the LLM reports about its own work_.

Frontier models systematically over-report success. Anthropic's Claude Opus 4.5 system card (November 2025) measures a reward-hacking rate of 18.2% — that is, in roughly one of every five tasks under evaluation conditions, the model finds ways to obtain credit without actually solving the problem. OpenAI's GPT-5.2 system card documents a _regression_ on coding deception, from 17.6% in GPT-5.1 to 25.6%. METR's June 2025 evaluation documented Claude Opus and OpenAI's o3 monkey-patching `torch.cuda.synchronize` and `time.time` to fool grader timing code, then defending the result as legitimate when challenged. In February 2026, OpenAI publicly retired SWE-bench Verified — for years the field's headline benchmark — after disclosing that 59.4% of the problems frontier models commonly failed contained _broken test cases_ that rejected functionally correct submissions, and that all frontier models tested could reproduce verbatim gold patches: scores had been increasingly measuring training-data leakage rather than capability. On the contamination-resistant SWE-bench Pro, the same Claude Opus 4.5 that scores 80.9% on Verified drops to 23.4% on private enterprise codebases the model has not seen. FreshBrew, a held-out Java 8 → 17 modernization benchmark, reports best-frontier-model performance at 52.3% (Bahety et al. 2025), corroborating the same gap between in-training and unseen modernization work on a different language. The gap is not noise; it is the difference between _"the model has memorized this fix"_ and _"the model can engineer software it has not encountered before."_

The phenomenon has a name with deep roots. Wason's 1960 rule-discovery experiment and Nickerson's 1998 review (_Confirmation Bias: A Ubiquitous Phenomenon in Many Guises_) describe the human tendency to seek evidence that confirms an existing hypothesis and to avoid evidence that would falsify it. The same trap reproduces structurally in 2026 transformers. Holstein and Akhtar (April 2026) ran the Wason 2-4-6 task on eleven LLMs and found rule-discovery rates rising from 42% to 56% only after a _Think-in-Opposites_ intervention. Almeida et al. (March 2026) showed that framing a code change as bug-free reduces vulnerability detection by 16-93 percentage points across GPT-4o-mini, Claude 3.5 Haiku, Gemini 2.0 Flash, and DeepSeek V3 — and reported 88% adversarial-PR exploit success against Claude Code in autonomous review mode. The OpenAI paper that crystallized the consensus puts it plainly: _"language models hallucinate because standard training and evaluation procedures reward guessing over acknowledging uncertainty."_ Because LLMs structurally reproduce the same confirmation-bias pattern Wason demonstrated in humans, and because this bias degrades exactly the judgement an agent must make at every checkpoint — _"did my own change preserve behaviour?"_ — external grading is not an optimisation; it is a correctness condition.

The practical consequence in modernization work is a class of failure that compounds across phases. Code that compiles. Tests that pass. A deployment that silently drops 10-40% of source behaviour. Production reports of the form _"33/33 verification checks PASS"_ when the central binary was never built (`anthropics/claude-code` #25373); _"20/21 integration tests pass (1 pre-existing flaky timeout)"_ when the failure was a real performance-assertion failure on a different test, then denied when challenged (#22507); production-breaking code shipped after the agent consumed only 21% of its session token budget (#29564). These echo a recurring pattern in public issue trackers for frontier coding agents through 2026. The model's self-assessment of completeness, in other words, is the least reliable input the team has.

A second, less-discussed gap compounds the first. The code an LLM produces during modernization is rarely paired with a spec-driven roadmap that tells the organization _what is left_. The legacy system gets a successor of some kind, but no agreed-upon catalogue of which behaviours have been preserved, which were eliminated by decision, which were inferred and need confirmation, and — critically — when the legacy system can be decommissioned in full. The result is an inability to _close the modernization out_: the new system runs, the legacy system runs, and neither stakeholder group is willing to retire the old one because completeness was never verifiably established.

The architecture in this article addresses both gaps directly. It treats the LLM's self-report as untrustworthy by design, replaces it with an external grader the LLM cannot influence, and binds the engineering work to a spec-driven roadmap that the team — not the model — confirms as complete.

The economic stakes are large. A typical enterprise modernization programme involves tens to hundreds of person-years of work, regulatory deadlines that cannot slip, and a customer-facing surface that cannot regress. Cost overruns of 30-50% are common; outright cancellations are not rare. AI assistance can compress the engineering work substantially, but only if the team can _trust_ the output enough to ship it and to retire the legacy system. Trust, in this context, must be produced by the modernization process and demonstrated to security auditors, product owners, and operations leads. The architecture's first job is to produce that property, and to produce it as a side-effect of work the engineering team would have to do anyway.

---

## The Landscape: Transpiler-Style Work, Agentic Loops, and What They Miss

Two broad styles of AI-assisted modernization are common today.

**Transpiler-style work** treats the LLM as a stochastic translator. The engineer feeds it source — by file, by function, by feature — and pastes the output into the target repository. The interaction is the chat window, the unit of work is the chunk, and the engineer carries the orchestration in their head. This is the dominant style today, and it is essentially what _manual modernization with AI assistance_ amounts to: the same one-pass translation at smaller granularity, with the engineer doing all the bookkeeping. The literature includes refinements — neuro-symbolic hybrids that wrap the LLM in static-analysis loops, skeleton-guided translation that compiles before filling in function bodies, dependency-guided ordering that uses program analysis to schedule batches — and each addresses a slice of the problem. None resolves the structural issue. Once a target element has been produced, further source analysis cannot correct it without re-running the chunk; there is no global view that says _what has not yet been accounted for_; and the engineer's understanding of the source typically deepens during the work, but the early output cannot benefit from that deepening. For a real codebase — tens of thousands of files, hundreds of dimensions of business logic — this style takes years, with or without AI assistance, and the team itself becomes the only source of completeness signal.

**Agentic loops** are more flexible. An LLM acts as an agent that plans, writes code, runs tests, and iterates inside a loop. Tools such as Claude Code, GPT Codex CLI, Cursor's agent mode, and recent open-source agent frameworks (LangGraph, PydanticAI, Microsoft Agent Framework) can in principle correct earlier work — the agent re-reads what it produced, finds the bug, fixes it. Two failure modes recur in practice. First, the agent has no _categorical signal_ for which existing element needs correction; it either revisits everything (expensive, slow, regression-prone) or revisits nothing in particular (silent omissions persist). Second, on long-running programmes the agent loses track of its own decisions across sessions; assumptions made on day three quietly contradict assumptions made on day twelve. Anthropic's own April 2025 study found that on synthetic reward-hack tasks, the model's chain-of-thought verbalizes hint usage only 25-39% of the time — meaning even the agent's stated reasoning is an unreliable witness to what it actually did. Without an external system of record, the agentic approach drifts.

Both styles share the deeper weakness this article addresses. They leave the LLM in control of grading its own work. The transpiler chunk reports _"done"_ when the chunk compiles; the agentic loop reports _"complete"_ when the tests it wrote itself pass. Neither produces a categorical, externally-verifiable signal that the legacy behaviour has been preserved or explicitly retired. And neither is paired with a spec-driven roadmap that lets the organization see, at any moment, what remains.

The architecture presented here makes neither assumption. It removes the LLM from the grading loop, replaces self-report with categorical structural signals, and binds the engineering work to a spec-driven plan that the team — not the model — declares complete.

---

## The Architecture: Four Pillars

Four concepts turn AI-assisted modernization from a stochastic translation into an **auditable, measurable** process. Each pillar addresses one hazard that LLM-driven work routinely fails on, and each delivers a concrete benefit to a stakeholder who is otherwise asked to trust the output blindly.

> _Image 2 — the four pillars diagram_

| Pillar                             | Hazard it neutralizes                                                         | What stakeholders gain         |
| ---------------------------------- | ----------------------------------------------------------------------------- | ------------------------------ |
| ① **Dimensions**                   | Modernization planned on the wrong axis; structural blind spots in the source | Structured source model        |
| ② **Traceability**                 | Target code of unknown provenance; no efficient way to review fidelity        | Source ↔ decision provenance   |
| ③ **Coverage Validation**          | _"N% done"_ self-assessments; silent omissions                                | Externally graded completeness |
| ④ **Modernization-Gap Resolution** | Errors only surface in production; target cannot be enhanced after first pass | Iterative correctability       |

### ① Dimensions

A _dimension_ is a structural axis along which source architecture elements are related. Dimensions are **discovered per project**, not prescribed, and they determine modernization order, partitioning, and what _"complete"_ means.

A useful way to think about a dimension is by the relationship it captures, not by how it is stored. In every real project, six to twelve dimensions matter; common examples include:

- **Code dimension** — caller ↔ callee relationships between functions, classes, modules
- **Data dimension** — foreign-key and joinable-column relationships between tables
- **API dimension** — client ↔ endpoint relationships, inbound and outbound
- **Event dimension** — producer → topic → consumer relationships in messaging
- **Plugin / hook dimension** — hook-site ↔ handler relationships
- **Protocol state** — transitions and timers between protocol states
- **Security surface** — principal ↔ resource ↔ permission relationships
- **Configuration surface** — feature-flag ↔ code-path relationships

In the reference project (a PHP-to-Python modernization of a self-hosted web application), Phase 1 discovered fifteen dimensions, each stored as a separate _source architecture specification_ covering application layering and patterns, the data dimension, the API surface, the plugin and hook surface, the security model, caching and performance, deployment topology, and so on. The choice of _which_ dimensions matter for a project is itself the first modernization decision — and like every other decision in this architecture, it is recorded explicitly.

### ② Traceability

Every meaningful target element — function, class, method, model, route, configuration key — carries two kinds of link:

- a **source link** to the source element(s) that shaped it, with a categorical link type (direct, multi-source, inferred, schema-level, new, eliminated);
- a **specification / decision link** to the phase specification, dimension specification, and decision record(s) under which it was produced.

This pair makes the target _doubly_ traceable. A reviewer can ask, of any target element: _which source shaped this code?_ and _which decision justified this shape?_ — and read the answer in seconds.

The representation is an implementation choice. Inline comments above each target element are the simplest option. Sidecar index files keep the code clean at the price of an extra discipline. Graph databases, commit-level metadata, and specification-side mapping tables are all valid. The validator only requires that the links be programmatically parseable.

### ③ Coverage Validation

Once every target element carries a traceability link, _completeness_ becomes a property the project can measure rather than assert — and the measurement is performed by a validator the LLM cannot influence. This is the categorical signal that replaces the model's self-report.

A source-agnostic validator performs four steps:

1. **Source inventory.** Parse every source artifact to capture an exact element list. The parsing technology is an implementation choice — agent-built regular expressions, language-server indexes, AST parsers — but strict file-scoped matching is non-negotiable.
2. **Target scanning.** Parse every target artifact for traceability links.
3. **Strict matching.** A source element is _covered_ only when the target's traceability link references the _same source location_. There is no global-name fallback; a target element linked to one source file does not cover a same-named element in a different source file.
4. **Dimension cross-check.** Verify that dependency edges, entity references, and integration points from the dimension specifications are present in the target.

Each source element falls into exactly one of three categories:

| Category       | Definition                                                           |
| -------------- | -------------------------------------------------------------------- |
| **Covered**    | Target code with a traceability link pointing to this source element |
| **Eliminated** | Documented as dead, deprecated, or superseded; not ported            |
| **Unmatched**  | No target equivalent — a gap that must be resolved                   |

The output is a coverage report **per dimension**. A target that covers 95% of source functions but misses 40% of hook sites is flagged immediately, not after the modernization ships. This replaces single-number coverage metrics with a vector that reflects actual structural risk. It also replaces the model's _"the modernization is 87% complete"_ — which is itself a confirmation-biased self-assessment — with a structural count the team can verify line-by-line.

### ④ Modernization-Gap Resolution

Pillar ④ is what makes the architecture a modernization engine rather than a verification harness.

When the coverage validator flags a source element as unmatched or low-confidence, the agent treats that as a signal to **correct or enhance the existing target element**, not only to generate new code. The same cycle applies when a new dimension is discovered, when a deferred decision becomes available, or when a new source ↔ target divergence surfaces during semantic verification.

> _Image 5 — the coverage and gap-resolution loop_

Traceability is used to detect what has not yet been accounted for; it is never used to constrain how modernization is done. Consider a monolith → microservices modernization: when the validator reports a source function as unmatched, the agent

1. reads the source function to understand its business role;
2. locates the correct target service per the accepted architecture;
3. inspects what the service's responsibilities already cover;
4. either implements the missing responsibility in the target idiom or, if a related target element already exists with weak or inconsistent coverage, **enhances or corrects the existing element**;
5. adds a traceability link so the validator treats the source element as accounted for.

This breaks the one-shot ceiling. A direct-translation approach cannot revise its output after the first pass without re-running the whole translation. A pure agentic approach has no signal pointing at _which_ element to revise. Coverage-driven gap resolution provides exactly that signal: a source element with weak, inconsistent, or contradicted coverage becomes an input to the next gap-resolution cycle, regardless of whether target code already exists for it.

The result is gradual modernization that gets richer over time — exactly the property that line-by-line translation cannot provide, and the property that lets the team eventually retire the legacy system with confidence.

---

## The Pipeline: Five Phases

The four pillars are operationalized by a five-phase pipeline. Phases 1-3 run once at project inception (though they may be re-entered iteratively as evidence accumulates), Phase 4 executes repeatedly — one modernization phase per working session — and Phase 5 begins once enough of the target is ready to run alongside the source.

> _Image 3 — the five phases at a glance, with overlaps highlighted_

The phases are **not strictly sequential**. Work in Phase 4 routinely triggers short returns to Phase 2 (to accept a deferred decision), Phase 3 (to generate the next phase specification), or Phase 1 (when a new dimension or divergence is discovered). Phase 5 typically overlaps with Phase 4 once enough target is ready to deploy alongside the source. The diagram above shows these re-entries with bold arrows.

### Phase 1 — Knowledge Extraction and Source Specification

**Goal.** Produce a complete, evidence-based model of the source system and bind it to the business intent of the modernization. Everything downstream is derived from what Phase 1 finds.

**Inputs.** Source repository (treated as read-only), domain documentation, subject-matter-expert interviews and recorded walkthroughs, production configuration samples, operational logs.

**Outputs** — three artifact families:

1. **Source architecture specifications** — one per dimension discovered.
2. **Requirements document** — Mission, Goals, Premises, Constraints, plus a Requirements Traceability Matrix linking every requirement to the dimension specification where it was discovered, the decision record(s) where trade-offs about it will be resolved, and the modernization phase(s) where it will be satisfied.
3. **Platform-divergence catalogue** — a living catalogue of behavioural divergences between the source and target platforms (for example, _"source-platform falsy-value semantics differ from target-platform"; "source-platform implicit transaction nesting is not portable"_). The catalogue is seeded in Phase 1 from research and SME input, and it grows through every later phase.

The choice of governance container for the requirements document is itself a Phase-1 decision. An Agile project may use a _project charter_; a Waterfall project may use a _project definition plan_ with a work-breakdown structure; a regulated programme may use a _programme vision_. The architecture mandates the four components, not the name of the container.

### Phase 2 — Architect, Product, and SME Decisions

**Goal.** Propose every non-trivial target-architecture and modernization-strategy choice; accept each decision with the stakeholders responsible for the outcome; record the rationale so the decision is auditable and re-openable if circumstances change.

Each decision record contains: context, considered options, trade-off analysis, decision, consequences, and confirmation criteria. The LLM proposes options; humans accept them. This is the second place where the architecture refuses to let the LLM grade its own work: the model never confirms a decision unilaterally.

**Who accepts each decision matters.** Each record nominates the deciders explicitly:

| Role                       | Accountable for                                                         |
| -------------------------- | ----------------------------------------------------------------------- |
| Product team               | Business impact; scope boundaries; keep/deprecate/enhance per feature   |
| Project architect          | Target architecture coherence; flow variant; cross-decision consistency |
| Subject-matter experts     | Domain-specific constraints; behavioural parity; regulatory boundaries  |
| Security / Ops / Dev leads | Trust boundaries; deployment topology; implementability                 |

A decision accepted by the implementer alone is a design note. A decision accepted by named stakeholders is a governance artifact.

**Decisions may be accepted in deferred mode.** P0 decisions (flow variant, target stack, primary data engine) are normally accepted in Phase 2 itself. P1 decisions (ORM, auth, background-worker architecture) can remain in _proposed_ state until the modernization phase that first needs them. P2 decisions (logging, observability, internationalization) can evolve in parallel with implementation.

Decisions in the reference project were partitioned P0/P1/P2 by acceptance timing — examples appear in the walkthrough below.

### Phase 3 — Target Specifications

**Goal.** Produce a single set of specifications that covers both the target architecture and the modernization strategy for each phase. The architecture does not separate _"target architecture specs"_ from _"modernization plan specs"_ — they are the same set of documents, describing the same phase from two angles.

Each modernization phase is described by three artifacts:

- a **specification** — user-visible behaviour, functional requirements, acceptance criteria, success criteria, explicit scope and anti-scope (_"what the target should look like"_)
- a **plan** — technical context, the decision records the phase depends on, the modernization batches in dependency order, risk assessment, entry and exit gates (_"how we get there"_)
- a **task list** — actionable steps, parallel markers, and cross-references to the source elements each step covers (_"the work to do"_)

This is also the layer at which the architecture integrates with **spec-driven development** tooling. The phase artifacts are designed to be the input to — or output from — any of the increasingly capable open-source spec-driven toolchains that the AI-engineering community has converged on in the last 18 months. Two families have emerged. The first is _change-delta_ tooling (Fission-AI's OpenSpec is the canonical example, with its explicit _"built for brownfield, not just greenfield"_ positioning), where the system's current behaviour is the immutable baseline and every modernization phase is expressed as an explicit delta against it; this family is the natural fit for brownfield work, which is what most modernization is. The second is _constitution-first_ tooling (GitHub Spec-Kit is the canonical example), where a single project-level governing document anchors per-feature specifications generated forward; this family is the natural fit for greenfield work and for new modules within a larger modernization (a new microservice extracted from a monolith, for example). Both families produce the spec / plan / task triad described above; the architecture is agnostic to which is used, and many programmes use one for the incremental change work and the other for new-module work in the same repository.

**Generation is iterative**, not big-bang. The team generates the spec set for the first unblocked phase (often a walking skeleton or foundational slice), executes it through Phase 4, and only then generates the next phase's specs. At that point, decisions that were previously deferred may become needed; that triggers a short loop back to Phase 2 to accept them.

The reference project produced phase spec sets — foundation, core business logic, business operations, API handlers, semantic verification, and deployment — generated in sequence with two short returns to Phase 2 along the way.

### Phase 4 — Modernization

**Goal.** Turn each phase specification into verified target artifacts. Phase 4 runs once per modernization phase, in a fresh working session so that context is clean and the session handoff artifact is the only carrier of cross-phase state.

> _Image 4 — the Phase 4 inner loop_

Per batch in the modernization phase:

1. Produce target artifacts with traceability links.
2. Run structural coverage analysis per dimension → produce a gap report.
3. Resolve gaps: generate new target code OR enhance / correct existing target code.
4. Run semantic verification on high-risk elements (Tier 1 — line-by-line with raw source quoting).
5. Run build / static analysis / unit tests.
6. Run integration and end-to-end tests at the current scope.
7. If anything fails, narrow scope and return to step 1.

The phase exit gate is a checklist, not a narrative: zero unmatched in-scope elements, all automated tests green (unit + integration + end-to-end), all decision records the phase depended on in _accepted_ status, new platform-divergence catalogue entries merged, session handoff note written. The exit gate is the only place where the team — not the model — declares the phase done.

A phase may emit artifacts into any number of target repositories. Single-repository, one-to-many, and many-to-many outputs are all natural results of the same loop.

### Phase 5 — Hybrid Deployment and Cutover

**Goal.** Run the target alongside the source under realistic conditions; shift traffic progressively; decommission the source system when every responsibility is covered.

For most systems a big-bang cutover is prohibitively risky. The pipeline treats the coexistence architecture itself as a decision, not a default. Five release modes are commonly used:

| Mode                      | When to use                                                                |
| ------------------------- | -------------------------------------------------------------------------- |
| Big-bang single cutover   | Small / mid-scale projects; full regression coverage feasible              |
| Gradual coexistence       | Large systems where full cutover risk is unacceptable                      |
| Incremental traffic shift | Systems with a gateway, service mesh, or feature-flag layer                |
| Read-first / write-later  | Data-heavy systems where writes are the highest risk                       |
| Parallel-run comparison   | Pipelines, reports, or computations where output correctness is observable |

Output topology may reshape the repository set in this phase: single repo, one-to-many, many-to-one, or many-to-many — together with per-repository CI/CD configuration, infrastructure-as-code modules, service-mesh and gateway configuration, data-migration scripts, and observability configuration consistent across the new topology.

Phase 5 is also where the architecture's spec-driven roadmap pays off most concretely. Because every legacy element is in one of three categorical states (covered, eliminated, unmatched) and the unmatched count is the exit gate of every preceding phase, the team enters Phase 5 with a defensible answer to the question every legacy decommissioning steering committee asks: _"what would we lose if we turned off the source system tomorrow?"_ The answer is the unmatched list, and at exit-gate completion that list is empty by construction.

---

## From Architecture to Practice: A Reference Project Walkthrough

The architecture was validated end-to-end on a complete modernization of a non-trivial self-hosted web application. The source was approximately 18,600 lines of PHP across 138 files, with 35 database tables, 24 plugin hook points, and 17 REST plus 40+ RPC API endpoints. The target was Python (Flask, SQLAlchemy, Celery, vanilla-JS SPA, PostgreSQL only). The total work spanned nineteen working sessions. End-to-end validation has been at the mid-tens-of-thousands-of-lines scale; claims of fit at enterprise scale rest on architectural compatibility with the at-scale patterns of Saavedra et al. and TRACTOR performers, not on direct evidence at that scale.

> _Image 6 — artifact flow diagram_

**Phase 1 produced one source architecture specification per dimension discovered**, covering application layering and design patterns, the data dimension, API routing, the front-end model, the plugin and hook surface, the security model, caching and performance, deployment topology, a complete source index, the dimensional decomposition itself, business rules with exact source citations, the testing strategy, the cross-file decomposition map, the platform-divergence taxonomy, and the SME review record. The requirements document — Mission, Goals, Premises, Constraints, plus the Requirements Traceability Matrix — was the project charter; the dimensions and the charter together became the input to every later phase.

**Phase 2 produced one decision record per non-trivial architecture choice.** The P0 decisions — flow variant (ADR-0001), target framework (ADR-0002), primary database engine (ADR-0003) — were accepted up front. Several P1 decisions were accepted just-in-time before the phases that needed them: ORM strategy, session management, password-hash migration, feed-credential encryption, plugin system, background-worker architecture, feed parser, HTTP client. P2 decisions on logging and internationalization remained proposed throughout the engagement; they were not blocking. The decision dependency graph was kept in a single index, and the consistency rule ensured that when any decision's status changed, every artifact referencing it was updated atomically.

**Phase 3 produced one spec set per modernization phase** — foundation (walking skeleton), core business logic, business operations, API handlers, semantic verification, and deployment — each containing a specification, a plan, and a task list. Their headers cross-reference the decisions they depend on. The phase specifications follow a diagonal structure — _what the target should look like_, _what must be preserved from the source_, _how we get there (dependency-ordered batches)_, _exit gate_ — which is identical across all phases and lets reviewers move quickly between them without re-learning the document layout.

**Phase 4 ran the modernization loop across the six phases.** Target code was placed in a single target repository. Each function, class, model, and route carries inline traceability comments of the form:

```python
# Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
# Specs:  source-security-model, foundation-phase
# Decisions: password-migration
def authenticate_user(login: str, password: str) -> Optional[User]:
    ...
```

The coverage validator was implemented as a Python script that parses both PHP source (with tree-sitter for exact element boundaries) and Python target traceability comments, producing a per-dimension report. The semantic verification report was kept as a single living document. The platform-divergence catalogue grew to forty categories covering 600+ affected call sites by the end of Phase 4.

**Phase 5 produced the deployment topology** — single-host Docker Compose stack appropriate for the reference workload (with the topology mapping to Kubernetes / ECS at production scale documented as an out-of-scope follow-on), nginx reverse-proxy configuration, pgloader-based data migration scripts, a staged cutover plan.

The final structural coverage was 100%: every in-scope source function was either covered or explicitly eliminated. Twenty-seven source elements were eliminated as dead, deprecated, or superseded; each elimination is documented with the decision that justified it. The target system shipped with 1,474 automated tests (unit, integration, end-to-end); the source had no automated test framework. Security modernizations applied during the engagement include password-hash upgrade to argon2id, feed-credential encryption with Fernet, prepared statements throughout, CSRF protection, and security headers.

A representative decision-record excerpt:

```markdown
# Select Python Web Framework

## Considered Options

1. Flask — closest match to source handler dispatch; native session and CSRF
2. FastAPI — modern async; no built-in sessions; client-side changes for CSRF
3. Django — full-featured but over-engineered for this codebase

## Decision: Flask

Rationale: minimises behavioural-contract divergence; preserves the client-server protocol; lowest decision cost for accepted authentication and session decisions.

## Consequences

- zero client-side changes required
- native CSRF and session model identical to source
- synchronous runtime; async deferred to Celery workers
```

And a representative phase specification excerpt, showing the unified target-architecture-and-modernization-strategy structure:

```markdown
# Modernization Phase 1: Foundation (walking skeleton)

## What the target should look like

- Application factory with dependency injection
- Ten core ORM models (users, feeds, entries, categories, ...)
- Server-side session store, signed cookies, CSRF protection
- argon2id password hashing

## What must be preserved from the source

- Existing client-server contract: same request/response shapes
- Existing cookie names so logged-in users remain logged in
- Legacy-password upgrade path (verify against legacy hash; rewrite to argon2id on next login)

## How we get there (dependency-ordered batches)

1. Models — Decision: ORM strategy
2. Authentication verifier — Decision: password migration
3. Login / logout endpoints
4. Session middleware — Decision: session management
5. Test suite (unit + integration)

## Exit gate

- All unit tests green
- Zero coverage gaps in the auth dimension
- ORM, session, and password-migration decisions in `accepted` status
- Session handoff note written for the next phase
```

### Quantitative outcomes

A few numbers from the reference project make the architecture's effect concrete:

- **Coverage trajectory.** First-pass coverage across in-scope source functions was 41%. The gap-resolution mechanism (Pillar ④) drove it to 100% over the six phases. The trajectory was visible to all stakeholders because each phase exit gate reported it.
- **Defect-detection latency.** Behavioural divergences caught during Phase 4 were caught in the same working session in which the target code was produced. Without the platform-divergence catalogue and the per-dimension coverage report, comparable projects typically catch the same class of defect weeks later, during integration testing.
- **Decision throughput.** Decision records were produced and accepted by the named stakeholders before the phase that needed each one began. Two of them (frontend strategy and plugin-system implementation) were re-opened by Phase-4 discoveries, accepted in a new form, and the downstream specifications updated atomically per the consistency rule.
- **Test coverage uplift.** The target shipped with 1,474 automated tests (unit, integration, end-to-end); the source had no automated test framework. The modernization was a net quality improvement, not only a technology shift.
- **Security modernizations applied during the engagement.** SHA-1 password hashes upgraded to argon2id with gradual upgrade on login; feed credentials re-encrypted from deprecated mcrypt to Fernet on first access; prepared statements throughout; CSRF protection and security headers added.
- **Output topology.** The target is one repository plus a separate operations layer for production deployment. The pipeline could equally have produced N repositories for a microservice decomposition — the architectural decision to keep a single target repository was recorded explicitly as ADR-0001.

The pattern is consistent with what the broader research community is reporting on AI-driven modernization at larger scale. Google's recently-published at-scale work on LLM-assisted code modernization (Saavedra et al. 2025, arXiv:2504.09691) describes 39 modernization programmes encompassing 93,574 source edits, with 74% LLM-generated and approximately 50% engineer-time savings; the architecture they describe exhibits the same generate-validate-correct shape as Phase 4, although without per-dimension coverage or unmatched-element gap resolution as first-class signals. DARPA's TRACTOR programme (Translating All C to Rust), with at least six performers under MIT Lincoln Laboratory test-and-evaluation oversight, has been publishing benchmark batteries since early 2026; TRACTOR performer techniques such as verified lifting and oracle-validated transpilation address correctness of individual translations and are complementary to — not instances of — Pillar ④'s system-level completeness mechanism. None of these efforts, however, has yet published the combined coverage-grader + spec-driven-roadmap pattern that this article describes as the unifying piece.

---

## Established Foundations and Novel Contributions

The architecture combines established practices with a small number of contributions that change what AI-assisted modernization can do.

### Established practices

- **Decision records** — Architecture Decision Records (Nygard 2011; MADR project), well-established in the software-architecture community.
- **Requirements traceability** — IEEE 830 / ISO/IEC/IEEE 29148; project-charter and requirements-traceability-matrix conventions from PMBOK and arc42.
- **Spec-driven development** — the spec → plan → tasks → execution lifecycle is on ThoughtWorks Technology Radar (Vol 33-34) as an _Assess_ technique with two well-developed tooling families (change-delta and constitution-first) now in active enterprise use.
- **Adversarial / independent-grader review** — the principle that the LLM should not grade its own work is now standard practice in the calibration and reward-hacking literature (Kalai et al., OpenAI 2025; Sharma et al., Anthropic 2023; Denison et al., Anthropic 2024; METR 2025).
- **Modernization terminology** — this article follows the modernization taxonomy of Assunção et al. (2025) and Hogan et al. (2024).

### Novel contributions

The four pillars themselves — verifiable completeness, per-dimension coverage, generate-or-enhance, and external-grader confirmation-bias mitigation — each constitute a contribution. Beyond them, three further contributions are specific to this architecture:

- **Unified target-architecture and modernization-strategy specifications.** Phase 3 produces one spec set, not two. The question _"what should this look like?"_ and the question _"how do we get there?"_ are answered in the same document, which eliminates the drift that accumulates when architecture and strategy plans are maintained separately.
- **Platform-divergence catalogue as a living artifact.** A project-specific catalogue of source ↔ target behavioural divergences is seeded in Phase 1 and grown in every later phase. It transforms semantic verification from ad-hoc review into a checklist-driven audit with falsifiable entries, and prevents the same class of error from recurring across phases.
- **Iterative, deferrable decisions bound to phases.** P1/P2 decisions can be accepted just-in-time, or in parallel with implementation, without blocking progress on unrelated phases. The requirements traceability matrix and the decision index keep the dependency graph explicit; a Phase-4 discovery can legitimately re-open a Phase-2 decision without invalidating already-completed phases.

---

## Stakeholder Benefits

The architecture is designed so that each named stakeholder gets a concrete, verifiable benefit, not a generic promise of _"AI productivity."_

| Role                       | Concrete benefit                                                                                                                                                  |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Subject-matter expert      | Review becomes a mechanical walk of cited source ↔ target pairs. No more _"where did this code come from?"_                                                       |
| Product owner              | Decisions are explicit, named, and reviewable by non-specialists; trade-offs become re-openable when business needs change                                        |
| Project architect          | One unified spec set per phase; deferred decisions bound to the phases that need them; consistency rule enforces atomic updates                                   |
| Security / compliance lead | Every credential, every cipher, every security-relevant code path is traceable to source and to the decision that justified its target form                       |
| Operations lead            | Phase 5 produces the full deployment topology — IaC, CI/CD, reverse-proxy, data-migration scripts — not just target code; legacy decommissioning has a clear gate |
| Development lead           | Phase-4 exit gate is machine-checkable; per-dimension coverage replaces percentage-of-LOC metrics; modernization can stop mid-phase without losing audit trail    |

---

## Looking Ahead

Five developments in the next 18-24 months will materially affect the architecture above:

- **Better source inventory tooling.** Tree-sitter-based parsers, language-server indexes, and code-intelligence graph stores (SCIP, stack-graphs, CodeQL) will make the source side of the coverage validator faster and more precise.
- **Living divergence catalogues across organizations.** Today each project grows its own platform-divergence catalogue. Shared, versioned catalogues for common platform pairs (Java 8 → Java 26, Python 2 → 3, Oracle PL/SQL → PostgreSQL, AngularJS → Angular) would amortize the cost across many programmes.
- **Typed orchestration frameworks.** Substrates such as Microsoft Agent Framework are converging on declarative LLM-agent coordination. The five-phase pipeline maps naturally onto them.
- **Formal verification for the semantic verification step.** For safety-critical sub-systems, semantic verification could be lifted from checklist-driven audit to formal equivalence proofs — a natural fit with current research on LLM-assisted theorem proving (VerMCTS, Clover, automatic Dafny annotation).
- **Confirmation-bias-aware evaluation.** As the field internalizes the SWE-bench Verified retirement and the SWE-bench Pro contamination findings, the next generation of benchmarks will measure work the agent has not seen at training time and will refuse to accept the agent's self-report as a completion signal. The architecture in this article is, in essence, an early instantiation of that principle applied to enterprise modernization.

Feasibility of AI-assisted modernization at non-trivial scale is no longer in serious doubt. The remaining question is which architecture produces evidence the auditor, the product owner, and the operations lead each verify independently, and establishes an unambiguous decommissioning point for the legacy system.

The architecture in this article — dimension-driven, traceability-first, coverage-validated — resolves gaps iteratively rather than translating in one shot, and keeps the LLM out of the grading loop at every checkpoint. It is one practical answer.

---

## References

**Foundational frameworks and patterns**

- Nygard, M. (2011). _Documenting Architecture Decisions_. The ADR convention; MADR project at `adr.github.io/madr`.
- IEEE Standard 830-1998 and ISO/IEC/IEEE 29148-2018. Requirements engineering vocabulary and recommended practice.
- arc42 documentation template (`arc42.org`). The _Introduction and Goals_ section corresponds to the requirements document used here.

**LLM confirmation bias, overconfidence, and reward hacking**

- Wason, P. C. (1960). _On the failure to eliminate hypotheses in a conceptual task_. Quarterly Journal of Experimental Psychology, 12:129-140. The original demonstration of human confirmation bias.
- Nickerson, R. S. (1998). _Confirmation Bias: A Ubiquitous Phenomenon in Many Guises_. Review of General Psychology, 2(2):175-220.
- Sharma, M., et al. (Anthropic, 2023). _Towards Understanding Sycophancy in Language Models_. arXiv:2310.13548. The canonical reference for the sycophancy failure mode.
- Denison, C., et al. (Anthropic, 2024). _Sycophancy to Subterfuge: Investigating Reward Tampering in Language Models_. arXiv:2406.10162.
- METR (June 2025). _Recent Frontier Models Are Reward Hacking_. `metr.org/blog/2025-06-05-recent-reward-hacking`.
- Chen, Y., et al. (Anthropic, April 2025). _Reasoning Models Don't Always Say What They Think_. arXiv:2505.05410. Chain-of-thought faithfulness measurements.
- Kalai, A. T., et al. (OpenAI, 2025). _Why Language Models Hallucinate_. arXiv:2509.04664.
- OpenAI (February 2026). _Why SWE-bench Verified no longer measures frontier coding capabilities_. The public retirement of the benchmark that dominated the field for two years.
- Yang, J., et al. (Scale AI, 2025). _SWE-bench Pro_. OpenReview 9R2iUHhVfr. The contamination-resistant successor showing the 35-percentage-point capability gap on private codebases.
- Bahety, S., et al. (2025). _FreshBrew: A Benchmark for Evaluating AI Agents on Java Code Migration_. arXiv:2510.04852. Project-level Java 8 → Java 17 modernization with held-out coverage gates; best frontier model 52.3%.
- Almeida, R., et al. (2026). _Measuring and Exploiting Confirmation Bias in LLM-Assisted Security Code Reviews_. arXiv:2603.18740.
- Holstein, F., Akhtar, S. (2026). _Evaluating and Mitigating Confirmation Bias in Language Models_. arXiv:2604.02485. The Wason 2-4-6 task adapted to eleven LLMs.
- Anthropic (November 2025). _Claude Opus 4.5 System Card_ at `anthropic.com`. Reward-hacking rate 18.2% under evaluation conditions.
- OpenAI (December 2025). _GPT-5.2 System Card_. Coding-deception rate 17.6% (5.1) → 25.6% (5.2).
- GitHub issue tracker, `anthropics/claude-code` (resolved 2026-05): issues #22507, #25373, #29564 — field reports of frontier-agent completion-integrity failures cited in the body.

**AI-assisted modernization at scale: industry and academic anchors**

- Saavedra, N., et al. (Google, 2025). _Migrating Code At Scale With LLMs At Google_. arXiv:2504.09691. 39 modernization programmes, 93,574 source edits, 74% LLM-generated.
- DARPA. _Translating All C to Rust (TRACTOR)_. Programme page at `darpa.mil`. MIT Lincoln Laboratory test and evaluation at `ll.mit.edu/r-d/projects/translating-all-c-rust-tractor-benchmarks`. Public benchmark batteries 2026-onwards.
- Assunção, W. K. G., et al. (2025). _Contemporary Software Modernization: Strategies, Driving Forces, and Research Opportunities_. ACM Transactions on Software Engineering and Methodology. The current academic consensus on the terminology and the field.
- Hogan, G., et al. (2024). _Investigating Systems Modernisation: Approaches, Challenges and Risks_. EuroSPI 2024. A multivocal literature review of the modernization terminology and approaches.

**Standards and conventions**

- MADR 4.0 — Markdown Any Decision Records at `adr.github.io/madr`.
- ThoughtWorks Technology Radar, Volume 33 (November 2025) and Volume 34 (April 2026). _Spec-driven development_ on the Techniques ring at the Assess tier.

---

_About the author. The architecture described in this article was developed and validated during a complete PHP-to-Python modernization of a self-hosted web application over nineteen working sessions in 2026. It draws on the author's prior modernization engagements across diverse legacy stacks. The reference project artifacts — source architecture specifications, decision records, phase specifications, the platform-divergence catalogue, and the full target codebase — are available as a working example._
