---
title: "When Specs Meet Agents: A Five-Phase, Audit-First Architecture and Framework for AI-Driven Software Modernization"
author: "Dmytro Rudakov"
issue: "Issue 31 | December 2026"
publication: "Capgemini Software Engineering Magazine"
version: 0.9 - draft
---

# When Specs Meet Agents

## A Five-Phase, Audit-First Architecture and Framework for AI-Driven Software Modernization

_By Dmytro Rudakov_

> _Image 1 — hero cover (full page)_

Organizations modernizing aging systems today face a class of work that frontier LLMs do not solve on their own. The shape of that work has changed. It is no longer the dev-platform version bump that dominated earlier modernization cycles. It is the portfolio-wide architectural rewrite: classic batch ETL replaced by streaming data-mesh architectures; vertical monoliths decomposed into service meshes and event-driven microservices; siloed line-of-business systems unified behind federation overlays; transaction models lifted from two-phase commit to durable-execution sagas; trust and cryptographic estates retargeted to passwordless and post-quantum. The unifying constraint across all of these is the same: the modernization must be _measurably done_, not merely _asserted_ done.

This article describes an audit-first architecture and framework for AI-assisted modernization, built around **five pillars** — Dimensions, Traceability (with deterministic coverage validation and gap resolution as sub-disciplines), an Autonomous Cross-Vendor Multi-Agent Architecture, a Spec-Driven Approach, and Flexible Decision-Making with Human-in-the-Loop — and operationalized through a five-phase pipeline. It is not a theoretical proposal. The architecture has been validated end-to-end on two genuinely different engagements: a memory-safety-critical C-to-Rust modernization of a native system, and a complete PHP-to-Python rewrite of a non-trivial self-hosted web application. The same loop, the same coverage validator, the same gap-resolution discipline carried both engagements through to retirement of the legacy system, and the framework is consistent with the at-scale pattern reported by independent industry work [^saavedra] [^tractor].

---

## Why Current Approaches Fall Short

Legacy estates are aging faster than teams can evolve them, and compliance mandates around memory safety, post-quantum cryptography, and operational-resilience tolerances increasingly turn _"we should modernize"_ into _"we must modernize before date X."_ Frontier LLMs are now reliable engineering collaborators on tool use and long-context reasoning — they can plan, execute tools, hold thousands of lines of context, and iterate inside a loop. What they cannot do is grade their own output, and the way most teams use them today amplifies rather than corrects that limitation.

### The Confirmation-Bias Failure Mode

Frontier coding agents systematically over-report success on engineering work. Recent academic and vendor disclosures converge on the same observation: framing a pull request as _"bug-free"_ collapses vulnerability detection by an order of magnitude across current-generation models; adversarial framing succeeds in a large fraction of one-shot attacks against today's coding agents; vendors themselves now formally catalog _"misrepresenting tool results"_ and _"premature claims of success"_ as recurring failure modes; and a majority of reward-hacking episodes include explicit chain-of-thought rationale — the model frames its shortcuts as legitimate work [^confirmation-bias].

This is why so many AI-driven modernization programmes launch with rapid early wins and then quietly collapse three to six months in. The wins were the same kind of unverified claim the system continues to make at scale, and no independent check exists until a customer hits a regression in production. The implication for architecture is direct: **external grading is not an optimization but a correctness condition**, and recent surveys argue this is a structural property of current alignment, not a prompt-fix problem [^reward-hacking].

The framework presented here defeats confirmation bias structurally rather than rhetorically. Completeness is measured by a **deterministic script** — not by another LLM. This is the most important property of the entire architecture and it deserves to be stated plainly: _no model, however capable, can grade its own output reliably_. A more capable LLM is still an LLM and inherits the same alignment-shaped failure mode. Traceability links from target to source are what make a static script possible — the script counts what is covered, what is eliminated, and what remains, line by line, with no model in the loop.

### The Legacy "Chat-Driven Modernization" Failure Mode

A second failure mode now dominates day-to-day practice. Engineers treat the agent as a chat partner — _"go to file X, rewrite function Y, then do Z"_ — and the modernization advances one prompt at a time. The interaction is imperative, fragment-scoped, and held together by the engineer's working memory. There is no spec-driven roadmap that tells the organization _what is left_, no autonomous progression from one batch to the next, and no measurable answer to _"when can we retire the source system?"_ At scale, this style of work delivers no meaningful speed-up over fully manual coding; it cannot modernize a non-trivial project in days because the agent is paused waiting for the next human prompt at every step.

The modern alternative — and the one this article describes — is autonomous: a skill loads a spec, the agent proceeds through batches to completion, and human attention is reserved for the small set of decisions that genuinely require it. Long-running pipelines, not chat turns, are the unit of work.

---

## Big-Bang vs Continuous Modernization

A short word on strategy before the pillars. Modernization programmes fail or succeed first on how they slice the work.

**Big-bang modernization** — replacing the legacy system in one coordinated push — fails on systems of any meaningful size. The root cause is loss of traceability. When work is done in large opaque portions there is no way to track _which_ source elements have been attempted, no way to reconcile the parts that came out wrong, and no way to incrementally correct. If the bulk output is incorrect — and at LLM scale it routinely is — the team is left with a result that is simultaneously _too large to verify_ and _too entangled to fix_.

**Continuous modernization** — small batches, each fully traced, each measurably complete before the next begins — is the default the framework assumes. Big-bang remains valid as a corner case: a small project where every behaviour fits in one head and full regression coverage is feasible in one release. Everything larger needs continuous, traceable, batch-by-batch progress. The Spec-Driven and Flexible Decision-Making pillars below are what make this strategy practical at scale.

---

## The Architecture: Five Pillars

Five concepts turn AI-assisted modernization into an **auditable, measurable** process. Each pillar addresses one failure mode that LLM-driven work routinely exhibits.

> _Image 2 — the five pillars diagram_

| Pillar                                                 | Failure mode addressed                                                                | Categorical signal it produces                                                                  |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| ① **Dimensions**                                       | Modernization planned on the wrong axis; structural blind spots in the source         | Structured source model with explicit relational axes and cohesive sub-units                    |
| ② **Traceability** (incl. coverage and gap resolution) | Target code of unknown provenance; "N% done" self-assessments; one-shot ceiling       | Per-dimension covered / eliminated / unmatched count, externally and deterministically graded   |
| ③ **Autonomous Cross-Vendor Multi-Agent Architecture** | Chat-driven, prompt-by-prompt modernization; vendor lock-in; uniform-tier model waste | Long-running autonomous pipelines portable across Claude, Codex, Copilot, Cursor, Gemini, Devin |
| ④ **Spec-Driven Approach**                             | Ad-hoc instructions; session drift; no cross-repo coordination                        | Specs as durable source of truth, scalable from one repo to portfolios of 100+                  |
| ⑤ **Flexible Decision-Making with Human-in-the-Loop**  | Naive HITL-by-Q&A; big-bang scope; decisions frozen before evidence exists            | Priority-classified decisions with up-front / just-in-time / parallel acceptance modes          |

### ① Dimensions

A _dimension_ is a structural axis along which source architecture elements are related. Dimensions are **discovered per project**, not prescribed, and they determine modernization order, partitioning, and what _"complete"_ means.

A useful way to think about a dimension is by the relationship it captures. In every real project, six to twelve dimensions matter, and the mix is project-dependent. For a **monolith-to-microservices** modernization the dominant dimensions are the service-dependency graph, the data-model graph, and the transaction / saga dimension. For a **batch-ETL to streaming data-mesh** modernization the dominant dimensions are the event-flow dimension (producer → topic → consumer) and the data-product dimension (ownership, schema evolution, contracts). For a **federation-overlay** modernization that unifies several siloed line-of-business systems behind a common access plane the dominant dimensions are the identity / trust dimension, the API contract dimension, and the data-residency / compliance dimension. For a **post-quantum cryptographic** modernization the dominant dimensions are the algorithm-and-key-store dimension, the certificate-chain dimension, and the protocol-handshake dimension. For a **classical web application** modernization — the article's public reference engagement — the dimensions were code, data, API, plugin / hook, security, and configuration. The choice of _which_ dimensions matter for a project is itself the first modernization decision.

**Graph-based representation and community detection.** Each dimension is naturally represented as a graph (call graph for the code dimension, foreign-key graph for the data dimension, producer-topic-consumer graph for the event dimension, hook-site-to-handler graph for the plugin dimension). Once a dimension is a graph, modern community-detection algorithms — Leiden, Louvain, and their hierarchical variants — partition each graph into **cohesive clusters of related elements**. These clusters become the natural modernization batches: an LLM asked to migrate _"the user-authentication community"_ or _"the feed-processing community"_ reasons over a coherent slice of the source rather than an arbitrary file selection, and the modernization roadmap follows the dependency order between communities. The reference engagements used NetworkX with Leiden detection on five dimension graphs (call, class, schema, hook, include) to produce the per-community modernization plan; supplemental graph and community files travel alongside the dimension specifications.

### ② Traceability (with Deterministic Coverage Validation and Gap Resolution)

Traceability is the second pillar — and the discipline on which the framework's defeat of confirmation bias rests. It contains three sub-disciplines that work as one auditable loop: the traceability links themselves, the **deterministic coverage validation** that exploits them, and the **gap-resolution loop** that closes the unmatched count.

#### 2.1 Traceability links

Every meaningful target element — function, class, method, model, route, configuration key, CDC connector, saga step — carries two kinds of link: a **source link** to the source element(s) that shaped it, with a categorical link type (direct, multi-source, aggregating, inferred, schema-level, new, eliminated); and a **specification / decision link** to the phase specification, dimension specification, and decision record(s) under which it was produced.

The links are **many-to-many, not one-to-one**. A single legacy authentication routine is routinely split into a credential validator, a session issuer, and an audit emitter in the target; a single saga step routinely subsumes what used to be several scattered procedural blocks under two-phase commit. The framework requires only that every target element carry _at least one_ source link, and that every source element be in one of three categorical states.

Representation is an implementation choice. Inline comments above each target element are the simplest and most robust option; sidecar JSON or YAML indexes keep target code clean at the cost of extra discipline; graph databases, commit-level metadata, and specification-side mapping tables are all valid. The only architectural requirement is that the links be programmatically parseable.

#### 2.2 Deterministic Coverage Validation

Once every target element carries a traceability link, completeness becomes a property the project can **measure** rather than assert. The measurement is performed by a static script the LLM cannot influence — this is the categorical signal that replaces the model's self-report.

The script performs four steps: a source inventory (parse every source artifact to capture an exact element list); a target scan (parse every target artifact for traceability links); strict matching (a source element is _covered_ only when at least one target traceability link references that exact source location — no global-name fallback); and a per-dimension cross-check (dependency edges, entity references, and integration points from the dimension specifications must be present in the target). Each source element falls into exactly one of three categories: **Covered**, **Eliminated** (documented as dead, deprecated, or superseded), or **Unmatched**.

The output is a coverage percentage **per dimension**. A target that covers 95% of source functions but misses 40% of saga compensating actions, or 60% of plugin hook sites, is flagged immediately. This replaces single-number coverage metrics with a vector that reflects actual structural risk, and it replaces the model's _"the modernization is 87% complete"_ with a count the team can verify line-by-line.

**This step must be deterministic.** A static script counting links is what defeats confirmation bias. Substituting an LLM grader — even a more capable one in a separate session — re-introduces the failure mode the framework exists to remove. The script is the part of the architecture that the LLM is structurally forbidden to touch.

#### 2.3 Modernization-Gap Resolution

When the coverage script flags a source element as unmatched, the agent treats that as a signal to **generate new target code or enhance the existing target element** — not only to translate the legacy lines. The same loop fires when a new dimension is discovered, when a previously deferred decision becomes available, or when source/target divergence surfaces during semantic verification.

This breaks the one-shot ceiling that purely translation-based approaches face. The agent reads the unmatched source element to understand its business role, locates the correct target location per the accepted architecture, inspects what the target already covers, either implements the missing responsibility or enhances a related target element that has weak coverage, and adds a traceability link so the script treats the source as accounted for.

> _Image 3 — the coverage and gap-resolution loop_

The **generate-or-enhance** property is the decisive advantage over chat-driven and one-shot approaches: the framework supports gradual correction of already-written code, not just addition of new code. This is what makes correct modernization possible at scale and what eventually lets the team retire the legacy system with confidence.

### ③ Autonomous Cross-Vendor Multi-Agent Architecture

The third pillar is the agent topology in which the framework executes. The architecture is **vendor-neutral** by design — it works with any AI coding tool that supports three capabilities now converging into an industry baseline: **sub-agents** (isolated contexts and parallel dispatch), **MCP** (the Model Context Protocol for tool and data integration), and **Skills** (the Agent Skills open standard published by Anthropic in late 2025 and now adopted across multiple vendors). Tools that satisfy all three include Claude Code, OpenAI Codex CLI, GitHub Copilot CLI, Cursor, Google Gemini CLI, Sourcegraph Amp, Cognition Devin, Google Jules, and others. The framework's methodology lives in portable skills; per-vendor wrappers carry only runtime concerns (tool whitelist, model selection, context isolation).

Five sub-patterns operationalize the pillar:

- **Long-running autonomous pipelines.** A skill loads a phase specification and proceeds to completion through the inner loop (produce → validate coverage → resolve gaps → semantic verify → test) without prompt-by-prompt human supervision. The unit of work is the phase, not the chat turn.
- **Tiered-model collaboration.** A high-capability model (Opus, GPT-5 Pro, Gemini Pro) is dispatched for triage, root-cause analysis, and fix-strategy inference; a cheaper, faster model (Haiku, smaller-tier peers) executes the inferred fixes mechanically — fixing failing unit tests, applying type annotations, propagating refactors. Routing the right tier to the right task increases swarm velocity and reduces cost by up to an order of magnitude on long-running pipelines.
- **Divergent-then-convergent decision making.** Parallel sub-agents generate alternative candidate designs or implementations against the same specification. An orchestrator agent runs structured pairwise comparison and selects the strongest, optionally returning the alternative as fallback. This replaces single-shot generation with adversarial breadth before depth.
- **Pipeline completeness gates.** The orchestrator must dispatch _every_ phase that the methodology defines; silently skipping an expensive verification phase to "save tokens" is the most damaging anti-pattern in agentic modernization. The framework treats the gate as a structural property of the orchestration layer, not a model preference.
- **Cross-session continuity through skills, not chat history.** A new working session loads the same skill against the next phase specification and resumes work; state lives in versioned artifacts (specs, decision records, traceability links, coverage reports), not in agent memory. This is what makes the architecture survive context window limits and team handovers.

The pillar is the architectural reason a chat-driven, single-model approach cannot match the framework: tier mismatch and missing isolation are not addressable in the chat paradigm.

### ④ Spec-Driven Approach

The fourth pillar is what the autonomous agent loop runs **against**. Specs are the durable source of truth; chat messages are not. A spec is a versioned artifact that survives sessions, models, agents, and team handovers.

The framework uses a generic **constitutional-style specification framework**: each target component is described by four declarative components — **Mission** (the terminal value the component serves), **Goals** (frozen objectives that, if changed, change the solution), **Premises** (assumptions and givens the architecture is willing to depend on), and **Constraints** (boundaries the architecture will not violate). The four components are the project's _constitution_ in the constitutional-AI sense: principles the agent reasons under, not prompts the agent is told to follow. They map naturally onto established traditions (PMBOK Project Charter, RUP Vision, INCOSE stakeholder needs and constraints, Lean canvases) so adopting the framework does not force a new vocabulary on an existing governance practice.

**Each project picks its own governance container and specs framework.** The container — _project charter_ for Agile, _project definition plan_ for Waterfall, _project initiation document_ for PRINCE2, _programme vision_ for regulated programmes — is a Phase-1 decision. The specs framework on top is likewise a choice: GitHub Spec-Kit fits constitution-first work (new modules and microservices extracted from a monolith); Fission-AI's OpenSpec fits brownfield delta-style work; bespoke layouts work where the project has strong prior art. The framework is neutral over the choice and composes with all of them.

**The Spec-Driven pillar scales from one repository to portfolios of many.** A small modernization may live in a single target repository. A monolith decomposition emits _N_ target repositories from one source. A microservices portfolio of 100+ services is modernized by treating each service's spec set as a node in a cross-repo dependency graph and applying the same five-phase pipeline per node, with shared cross-repo decision records and cross-repo coverage reports. The same spec format describes the unit at every scale — the agent loop does not care whether it is reading one repository's spec or one of a hundred.

### ⑤ Flexible Decision-Making with Human-in-the-Loop

The fifth pillar is the human surface of the framework. Decisions are the interface between specs and execution, and the way the framework structures decisions is what makes Human-in-the-Loop genuinely useful — rather than the bottleneck it becomes in naive chat-style HITL.

**Deferred decision-making is the main benefit.** Not every decision needs to be settled before work begins. The framework partitions decisions into priority classes:

- **P0** — blocks all work (flow variant, target stack, primary data engine). Accepted up-front.
- **P1** — blocks a specific modernization phase (ORM choice, authentication, saga substrate, background-worker fabric). Accepted just-in-time, before the phase that first needs them.
- **P2** — deferrable, no blocking dependency (logging strategy, observability surface, internationalisation). Accepted in parallel with implementation, as evidence accumulates.

This is why **big-bang migration is only a corner case**: a big-bang programme is one where every decision is treated as P0 and accepted up-front. For small projects this is feasible; for everything larger the team's ability to **choose which functions to modernize now and which to defer** is the deciding factor in whether the programme converges. The default is continuous modernization with most decisions deferred; big-bang is what happens when the deferred set is empty.

The framework's HITL surface follows the same shape. Naive HITL — the early-2024 pattern of the agent asking the human a question every few steps — is what slows chat-driven modernizations to a crawl while adding little correctness. The framework's HITL is **decision-shaped**: the agent proposes options, generates trade-off analysis, and asks the appropriate stakeholders to accept the decision record — _once_ — at which point work proceeds autonomously against the accepted decision. Re-opens are explicit, audited, and bound to new evidence.

The framework spans the full range of team modes. A solo developer running a quick presale demo can act as every stakeholder; a regulated enterprise programme can route each decision through an established RACI of product, architecture, security, operations, and SME leads. The decision-record format and the priority classes are identical in both cases; only the acceptance signatures change.

---

## The Pipeline: Five Phases

The five pillars are operationalized by a five-phase pipeline. Phases 1–3 run once at project inception (though they may be re-entered iteratively as evidence accumulates), Phase 4 executes repeatedly — one modernization phase per working session — and Phase 5 begins once enough of the target is ready to run alongside the source.

> _Image 4 — the five phases at a glance, with overlaps highlighted_

The phases are **not strictly sequential**. Work in Phase 4 routinely triggers short returns to Phase 2 (to accept a deferred decision), Phase 3 (to generate the next phase specification), or Phase 1 (when a new dimension or divergence is discovered). Phase 5 typically overlaps with Phase 4 once enough target is ready to deploy alongside the source.

### Phase 1 — Knowledge Extraction and Source Specification

**Goal.** Produce a complete, evidence-based model of the source system and bind it to the business intent of the modernization.

**Outputs.** One source architecture specification per dimension discovered (each backed by its dimension graph and community decomposition); a requirements document built on the Mission / Goals / Premises / Constraints constitutional framework plus a Requirements Traceability Matrix; and a platform-divergence catalogue of behavioural differences between source and target platforms, seeded in Phase 1 and grown through every later phase.

A short example of the Mission / Goals / Premises / Constraints breakdown for a single target component — the authentication service in a PHP-to-Python modernization — illustrates the shape:

> **Mission.** Authenticate users against the same credential store the legacy system accepts, with no observable behaviour change for already-logged-in users.
>
> **Goals.** (a) verify against legacy password hashes on first login; (b) silently rewrite to the modern hash on the next login; (c) preserve cookie name and session-token shape; (d) emit the same audit-log events.
>
> **Premises.** Modern session machinery; modern hashing library; relational database for the user table; key-value store for the session.
>
> **Constraints.** No client-side change; no break of existing single sign-on integrations; ≤120 ms p99 verification latency; legacy hashes never persisted again.

The same four-line shape is applied to every component the modernization produces. Goals and Constraints become acceptance criteria; Premises become entry-gate dependencies on decision records; Mission becomes the SME-review hook.

The choice of governance container (charter, vision, project initiation document, programme vision) and of specs framework (constitution-first, brownfield-delta, bespoke) is itself a Phase-1 decision. Different projects benefit from different governance models and specs frameworks; the framework mandates the four constitutional components, not the container they live in.

### Phase 2 — Architect, Product, and SME Decisions

**Goal.** Propose every non-trivial target-architecture and modernization-strategy choice; accept each decision with the stakeholders responsible for the outcome; record the rationale so the decision is auditable and re-openable.

Each decision is captured as an Architecture Decision Record [^adr] containing context, considered options, trade-off analysis, decision, consequences, and confirmation criteria. The agent proposes options; humans accept them. This is the second place where the framework refuses to let the LLM grade its own work: the model never confirms a decision unilaterally.

The decision-acceptance surface scales across team modes. A solo developer producing a presale demo can act as every stakeholder in one session; an enterprise programme can route each decision through an established RACI of product, architecture, security, operations, and SME leads. The format and the priority classes are identical in both cases.

**Decisions are partitioned by acceptance timing — and deferral is the default at higher classes.** P0 decisions are normally accepted in Phase 2 itself. P1 decisions can remain _proposed_ until the modernization phase that first needs them. P2 decisions evolve in parallel with implementation. This is the mechanism that makes continuous modernization possible: the ability to start work on the unblocked parts of the system while specific architectural choices for later parts of the system remain genuinely open.

### Phase 3 — Target Specifications

**Goal.** Produce a single set of specifications that covers both the target architecture and the modernization strategy for each phase. The framework does not separate _target architecture_ from _modernization plan_ — they are the same set of documents, describing the same phase from two angles. This unification eliminates the drift that accumulates when architecture and strategy plans are maintained separately.

Each modernization phase is described by three artifacts: a **specification** (user-visible behaviour, acceptance criteria, scope, anti-scope); a **plan** (technical context, decision-record dependencies, modernization batches in dependency order, risk assessment, entry and exit gates); and a **task list** (actionable steps, parallel markers, source-element cross-references).

**Generation is iterative**, not big-bang. The team generates the spec set for the first unblocked phase (often a walking skeleton or foundational slice), executes it through Phase 4, and only then generates the next phase's specs. Deferred decisions that become needed trigger a short loop back to Phase 2.

### Phase 4 — Modernization

**Goal.** Turn each phase specification into verified target artifacts. Phase 4 runs once per modernization phase, in a fresh working session, so context is clean and the session handoff artifact is the only carrier of cross-phase state.

> _Image 5 — the Phase 4 inner loop_

Per batch in the modernization phase:

1. Produce target artifacts with traceability links.
2. Run the deterministic coverage validator per dimension → produce a gap report.
3. Resolve gaps: generate new target code OR enhance / correct existing target code.
4. Run semantic verification on high-risk elements, against the platform-divergence catalog (line-by-line, with raw source quoting).
5. Run build, static analysis, and unit tests.
6. Run integration and end-to-end tests at the current scope.
7. If anything fails, narrow scope and return to step 1.

The phase exit gate is a checklist, not a narrative: zero unmatched in-scope elements, all automated tests green, all decision records the phase depended on in _accepted_ status, new platform-divergence catalogue entries merged, session handoff note written. The exit gate is the only place where the team — not the model — declares the phase done.

A phase may emit artifacts into any number of target repositories. Single-repository, one-to-many, and many-to-many outputs are all natural results of the same loop, which is what allows the Spec-Driven pillar to scale up to portfolios of many services.

### Phase 5 — Hybrid Deployment and Cutover

**Goal.** Run the target alongside the source under realistic conditions; shift traffic progressively; decommission the source system when every responsibility is covered.

The pipeline treats the coexistence architecture as a decision, not a default. Five release modes are commonly used: gradual coexistence (the default for non-trivial systems), incremental traffic shift through a gateway or service mesh, read-first / write-later for data-heavy systems, parallel-run comparison for pipelines and computations, and single-event cutover for the corner case of small projects where full regression coverage in one release is feasible.

The operations lead inherits the full deployment topology — infrastructure-as-code modules, service-mesh and gateway configuration, data-migration scripts, observability configuration — together with a defensible decommissioning gate. Because every legacy element is in one of three categorical states and the unmatched count is the exit gate of every preceding phase, the team enters Phase 5 with an unambiguous answer to the question every steering committee asks: _"what would we lose if we turned off the source system tomorrow?"_ The answer is the unmatched list, and at exit-gate completion that list is empty by construction.

---

## The Architecture and Framework in Practice

The architecture and framework were validated on two engagements with materially different shapes. The first is a memory-safety-critical C-to-Rust modernization of a native system, where the dominant dimensions were data flow, ownership, and the integration surface between unsafe and safe code regions. The second — the public reference engagement — is a complete PHP-to-Python rewrite of a non-trivial self-hosted web application, where the dominant dimensions were the plugin / hook surface, the security model, and the API surface. The same loop, the same deterministic coverage validator, the same gap-resolution discipline carried both engagements through to retirement of the legacy system.

> _Image 6 — artifact flow diagram_

In the web engagement, Phase 1 produced one source architecture specification per dimension discovered (each backed by a NetworkX graph and a Leiden community decomposition), the constitutional Mission / Goals / Premises / Constraints requirements document, and a platform-divergence catalogue. Phase 2 produced a small set of P0 decisions accepted up front, with most P1 decisions accepted just-in-time before the phases that needed them and P2 decisions evolved in parallel with implementation. Phase 4 ran the modernization loop across the planned phases. Each function, class, model, and route carries a traceability link of the form:

```python
# Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
# Specs:  source-security-model, foundation-phase
# Decisions: password-migration
def authenticate_user(login: str, password: str) -> Optional[User]:
    ...
```

The coverage validator is a Python script that parses both source (with tree-sitter for exact element boundaries) and target traceability links, producing a per-dimension percentage report — a deterministic count, not a model assessment.

A representative decision-record excerpt:

```markdown
# Select Python Web Framework

## Considered Options

1. Flask — closest match to source handler dispatch; native session and CSRF
2. FastAPI — modern async; no built-in sessions; client-side changes for CSRF
3. Django — full-featured but over-engineered for this codebase

## Decision: Flask

Rationale: minimizes behavioral-contract divergence; preserves the client-server protocol; lowest decision cost given the accepted authentication and session decisions.

## Consequences

- zero client-side changes required
- native CSRF and session model identical to source
- synchronous runtime; async deferred to background workers
```

The modernization shipped with a target that explicitly documents which source elements were eliminated (with the decision record that justified each elimination), and a deployment topology backed by data-migration scripts and a staged cutover plan.

The pattern is consistent with what the broader research community has reported on AI-driven modernization at larger scale [^saavedra] [^tractor]: the same generate-validate-correct shape as Phase 4 emerges across organizations, and the framework's coverage-and-gap-resolution discipline is the missing system-level completeness mechanism.

---

## Looking Ahead

A few developments in the near term will materially affect this architecture:

- **Richer source-inventory tooling.** Tree-sitter-based parsers are already in use; the next round of progress will come from language-server indexes and code-intelligence graph stores that make the source side of the coverage validator faster and more precise on enterprise codebases.
- **Living divergence catalogues across organizations.** Today each project grows its own platform-divergence catalogue. Shared, versioned catalogues for common platform pairs would amortize the cost across many programmes.
- **Typed orchestration frameworks for multi-agent pipelines.** Substrates such as Microsoft Agent Framework and OpenAI Agents SDK are converging on declarative LLM-agent coordination; the five-phase pipeline maps naturally onto them.
- **Formal verification for the semantic-verification step.** For safety-critical sub-systems, semantic verification can be lifted from checklist-driven audit to formal equivalence proofs.
- **Confirmation-bias-aware evaluation.** The next generation of benchmarks will measure work the agent has not seen at training time and will refuse to accept the agent's self-report as a completion signal. The architecture here is an early instantiation of that principle applied to enterprise modernization.

Feasibility of AI-assisted modernization at non-trivial scale is no longer in serious doubt. The remaining question is which architecture produces evidence the auditor, the product owner, and the operations lead each verify independently, and that establishes an unambiguous decommissioning point for the legacy system. This article describes one practical answer: dimension-driven with graph-based community detection, traceability-first with deterministic coverage validation and gap-resolving generate-or-enhance loops, executed by an autonomous cross-vendor multi-agent topology, governed by spec-driven artifacts, and guided by deferred, priority-classified human decisions rather than chat-by-chat prompting.

---

## Appendix — References

**Foundational frameworks and patterns.** Chikofsky & Cross's _Reverse Engineering and Design Recovery_ (1990) established the source-side analysis vocabulary; ISO/IEC 19506 (Knowledge Discovery Meta-Model) is the international standard underpinning Phase 1; Fowler's _Patterns of Legacy Displacement_ describes Strangler Fig and related coexistence patterns; O'Leary's _Enterprise Resource Planning Systems_ provides the canonical big-bang-vs-phased contrast; IEC 60812 (FMEA) is the provenance of the failure-mode vocabulary.

[^adr]: The Architecture Decision Record format used here follows the convention originated by Michael Nygard, _Documenting Architecture Decisions_ (2011), with the MADR variant at `adr.github.io/madr` and ISO/IEC/IEEE 42010 as adjacent precedents. Other equivalent templates (Y-statements, bespoke records) compose with the framework equally well.

[^confirmation-bias]: Vendor and academic disclosures on confirmation-bias and reward-hacking failure modes in current-generation coding agents: Anthropic's published system cards (formal cataloguing of _"misrepresenting tool results"_ and _"premature claims of success"_); recent academic work on adversarial framing collapsing vulnerability-detection rates across multiple frontier models (Mitropoulos et al.); reward-hacking benchmarks showing a majority of episodes accompanied by explicit chain-of-thought rationale; and arXiv:2604.13602 on reward hacking as a structural property of current RLHF / RLVR alignment.

[^reward-hacking]: Surveys of reward-hacking in large models argue the failure is not addressable through prompt engineering alone and requires architectural mechanisms — external grading, structural signals, deterministic verification — to defeat. The Proxy Compression Hypothesis is one formulation.

[^saavedra]: Saavedra, N., et al. (Google, 2025). _Migrating Code At Scale With LLMs At Google_. arXiv:2504.09691. Thirty-nine modernization programmes across 93,574 source edits; same generate-validate-correct shape as Phase 4 here, without per-dimension coverage or unmatched-element gap resolution as first-class signals.

[^tractor]: DARPA's _Translating All C to Rust (TRACTOR)_ programme: verified lifting with LLMs, skeleton-guided translation, oracle-validated transpilation. Programme page at `darpa.mil`; MIT Lincoln Laboratory test and evaluation at `ll.mit.edu/r-d/projects/translating-all-c-rust-tractor-benchmarks`. Complementary to — not an instance of — the system-level completeness mechanism described here.

**Agent platform standards (late 2025).** The Agent Skills open standard published by Anthropic in late 2025 is the portable methodology layer the third pillar depends on. The AGENTS.md cross-tool standard, stewarded by the Linux Foundation's Agentic AI Foundation since late 2025, is the corresponding portable governance layer. The Model Context Protocol (MCP) is the portable tool / data integration layer. Together they make a vendor-neutral multi-agent topology feasible.

**Capgemini practice.** _AI-Assisted Legacy Modernization (CAALM)_, Capgemini's modernization practice, is the engagement context in which this architecture and framework were developed and validated.

---

_About the author. Dmytro Rudakov developed and validated the architecture and framework described here within Capgemini's AI-Assisted Legacy Modernization (CAALM) practice, across two genuinely different engagements: a memory-safety-critical C-to-Rust modernization of a native system, and a complete PHP-to-Python rewrite of a non-trivial self-hosted web application. The reference engagement artifacts — source architecture specifications, decision records, phase specifications, the platform-divergence catalog, and the full target codebase — are available as a working example._
