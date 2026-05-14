---
title: "When Specs Meet Agents: A Five-Phase, Audit-First Architecture for AI-Driven Software Modernization"
author: "Roman Dudkin"
issue: "Issue 31 | December 2026"
publication: "Capgemini Software Engineering Magazine"
---

# When Specs Meet Agents

## A Five-Phase, Audit-First Architecture for AI-Driven Software Modernization

_By Dmytro Rudakov_

> _Image 1 — hero cover (full page)_

Organizations modernizing aging codebases face a hard problem that frontier LLMs do not solve on their own: how to migrate a non-trivial system from one technology stack to another so completely, faithfully, and verifiably that the migration is _measurably done_ — not asserted to be done.

This article introduces a five-phase architecture for AI-assisted software modernization, anchored in four operational pillars (Dimensions, Traceability, Coverage Validation, and Modernization-Gap Resolution). It is technology-agnostic — the same pipeline applies to language migrations, framework shifts, monolith-to-microservices decompositions, data-pipeline rewrites, and protocol-library ports — and it has been validated end-to-end on a complete PHP-to-Python migration of a non-trivial web application.

---

## The Scale of the Problem: Why Current Approaches Fall Short

Three forces are converging into a significant modernization opportunity, and a corresponding gap.

**Legacy codebases are aging faster than teams can refactor them.** Many enterprises run systems built fifteen or twenty years ago, on platforms (older language versions, deprecated frameworks, end-of-life databases) that limit hiring, raise operational risk, and block security and compliance work. Compliance mandates — for memory safety, for credential storage, for prepared statements — increasingly turn "we should modernize" into "we must modernize before _date X_."

**Frontier LLMs have become viable partners for engineering work.** Today's models — Claude Opus 4.6, GPT-5.3, Gemini 3 Pro and their open-source peers — execute tools reliably, maintain coherence across thousands of lines of context, self-correct without human intervention, and operate in plan-execute-verify-correct loops. These capabilities make AI a viable collaborator on complex, multi-step modernization tasks.

**Yet there is no broadly-adopted framework for using them on real migrations.** Despite the surge of recent academic work and several promising vendor announcements, no widely-deployed methodology exists for running an end-to-end LLM-driven modernization in a way that satisfies a security auditor, a product owner, and a compliance lead at the same time.

The reasons are well-documented. Even with large-context models capable of loading entire repositories, source elements are systematically missed during migration: attention dilutes across long files, file-level claims hide function-level omissions, common names collide across unrelated modules, and work from one working session quietly contradicts assumptions made in another. Progress reports of the form _"the migration is 87% complete"_ are LLM self-assessments — not independent checks.

The result, in real projects, is a class of failure that compounds across phases: code that compiles, tests that pass, and a deployment that silently drops 10–40% of source behaviour. The architecture in this article addresses that gap directly.

The economic stakes are large. A typical enterprise modernization programme involves tens to hundreds of person-years of work, regulatory deadlines that cannot slip, and a customer-facing surface that cannot regress. Cost overruns of 30–50% are common; outright cancellations are not rare. AI assistance can compress the engineering work substantially, but only if the team can _trust_ the output enough to ship it. Trust, in this context, is not a feeling; it is a property that has to be produced by the migration process and demonstrated to security auditors, product owners, and operations leads. The framework's first job is to produce that property, and to produce it as a side-effect of work the engineering team would have to do anyway.

---

## The Landscape: Translation, Agentic Loops, and What They Miss

Two broad styles of AI-assisted migration are common today.

**Transpiler-style approaches** treat the LLM as a stochastic translator: feed it source code, receive target code. The pipeline is one-pass — a context window of source, a model invocation, and an output of target code. This style is fast for near-identical translations (e.g., one language version to a newer minor version of the same language) and it produces an immediately runnable output. It breaks down quickly for anything that requires architectural redesign: once a target element has been produced, further source analysis cannot correct it without re-running the whole translation, and there is no mechanism to enhance existing code as the team's understanding of the source deepens. The literature includes several recent variants — neuro-symbolic hybrids that wrap the LLM in static-analysis loops, skeleton-guided translation that compiles before filling in function bodies, dependency-guided ordering that uses program analysis to schedule batches — and each addresses a slice of the problem. None of them addresses the broader question: how does the team know when the migration is _done_?

**Agentic loops** are more flexible. An LLM acts as an agent that plans, writes code, runs tests, and iterates inside a loop. Tools such as Claude Code, GPT Codex CLI, Cursor's agent mode, and the more recent open-source agent frameworks (LangGraph, PydanticAI, Microsoft Agent Framework) can in principle correct earlier work — the agent re-reads what it produced, finds the bug, fixes it. In practice, two failure modes recur. First, the agent has no _categorical signal_ for **which** existing element needs correction; it either revisits everything (expensive, slow, and prone to introducing regressions) or revisits nothing in particular (silent omissions persist). Second, in long-running migrations the agent loses track of its own decisions across sessions; assumptions made on day three quietly contradict assumptions made on day twelve. Without an external system of record, the agentic approach drifts.

A third style — **manual migration with AI assistance** — is what most teams actually do today. Engineers chunk the source by file or feature, prompt the model on each chunk, paste the output into the target repository, and run tests. This works, in the sense that the migration eventually completes, but it places the entire burden of orchestration on the engineering team: tracking what has been ported, what has been skipped, why each decision was taken, and how the target compares to the source. The team becomes the bookkeeping layer.

All three styles share a deeper weakness: they treat migration as a one-shot translation from one repository to another. Real modernization is rarely one-to-one. A monolith may need to become _N_ microservices; several legacy components may need to consolidate into a single modular target; the data store, the messaging fabric, the deployment topology, and the authentication model may all change at once. Any framework that locks the output shape at the input shape forces the team back to manual orchestration for everything outside that shape.

The framework presented here does not assume one-to-one, does not assume one-pass, and does not assume that completeness is something the LLM itself can report on.

---

## The Architecture: Four Pillars

Four concepts turn AI-assisted migration from a stochastic translation into an **auditable, measurable modernization** process. Each pillar answers one hazard that LLM-driven migrations routinely fail on, and each delivers a concrete benefit to a stakeholder who is otherwise asked to trust the output blindly.

> _Image 2 — the four pillars diagram_

| Pillar                             | Hazard it neutralizes                                                         | What stakeholders gain                                                                                     |
| ---------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| ① **Dimensions**                   | Migration planned on the wrong axis; structural blind spots in the source     | Structured source model; migration order that respects reality                                             |
| ② **Traceability**                 | Target code of unknown provenance; no efficient way to review fidelity        | **SMEs can review fast** — every target element cites source + spec + decision                             |
| ③ **Coverage Validation**          | "N% done" self-assessments; silent omissions                                  | "Done" is a **measurable predicate** — per-dimension, auditable                                            |
| ④ **Modernization-Gap Resolution** | Errors only surface in production; target cannot be enhanced after first pass | **Confidence** — gaps are detected and the target is iteratively corrected or enhanced, not only generated |

### ① Dimensions

A _dimension_ is a structural axis along which source architecture elements are related. Dimensions are **discovered per project**, not prescribed, and they determine migration order, partitioning, and what "complete" means.

A useful way to think about a dimension is by the relationship it captures, not by how it is stored. In every real project, six to twelve dimensions matter; some examples:

- **Code dimension** — caller ↔ callee relationships between functions, classes, modules
- **Data dimension** — foreign-key and joinable-column relationships between tables
- **API dimension** — client ↔ endpoint relationships, inbound and outbound
- **Event dimension** — producer → topic → consumer relationships in messaging
- **Plugin / hook dimension** — hook-site ↔ handler relationships
- **Protocol state** — transitions and timers between protocol states
- **Security surface** — principal ↔ resource ↔ permission relationships
- **Configuration surface** — feature-flag ↔ code-path relationships

In the reference project (a PHP-to-Python migration of a self-hosted web application), Phase 1 discovered fifteen dimensions, each stored as a separate _source architecture specification_ in `specs/architecture/`. The data dimension is captured in `02-database.md`, the plugin/hook dimension in `05-plugin-system.md`, the security surface in `06-security.md`, and twelve more.

The choice of _which_ dimensions matter for a project is itself the first migration decision — and like every other decision in this framework, it is recorded explicitly.

### ② Traceability

Every meaningful target element — function, class, method, model, route, configuration key — carries two kinds of link:

- a **source link** to the source element(s) that shaped it, with a categorical link type (direct, multi-source, inferred, schema-level, new, eliminated);
- a **specification / decision link** to the phase specification, dimension specification, and decision record(s) under which it was produced.

This pair makes the target _doubly_ traceable. A reviewer can ask, of any target element: _which source shaped this code?_ and _which decision justified this shape?_ — and read the answer in seconds.

The representation is an implementation choice. Inline comments above each target element are the simplest option. Sidecar index files keep the code clean at the price of an extra discipline. Graph databases, commit-level metadata, and specification-side mapping tables are all valid. The validator only requires that the links be programmatically parseable.

### ③ Coverage Validation

Once every target element carries a traceability link, _completeness_ becomes a property the project can measure rather than assert.

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

The output is a coverage report **per dimension**. A target that covers 95% of source functions but misses 40% of hook sites is flagged immediately, not after the migration ships. This replaces single-number coverage metrics with a vector that reflects actual structural risk.

### ④ Modernization-Gap Resolution

This is the pillar that turns the framework from a verification harness into a modernization engine.

When the coverage validator flags a source element as unmatched or low-confidence, the agent treats that as a signal to **correct or enhance the existing target element**, not only to generate new code. The same cycle applies when a new dimension is discovered, when a deferred decision becomes available, or when a new source ↔ target divergence surfaces during semantic verification.

This breaks the one-shot ceiling. A direct-translation approach cannot revise its output after the first pass without re-running the whole translation. A pure agentic approach has no signal pointing at _which_ element to revise. Coverage-driven gap resolution provides exactly that signal: a source element with weak, inconsistent, or contradicted coverage becomes an input to the next gap-resolution cycle, regardless of whether target code already exists for it.

The result is gradual modernization that gets richer over time — exactly the property that line-by-line translation cannot provide.

---

## The Pipeline: Five Phases

The four pillars are operationalized by a five-phase pipeline. Phases 1–3 run once at project inception (though they may be re-entered iteratively as evidence accumulates), Phase 4 executes repeatedly — one migration phase per working session — and Phase 5 begins once enough of the target is ready to run alongside the source.

> _Image 3 — the five phases at a glance, with overlaps highlighted_

The phases are **not strictly sequential**. Work in Phase 4 routinely triggers short returns to Phase 2 (to accept a deferred decision), Phase 3 (to generate the next migration-phase spec), or Phase 1 (when a new dimension or divergence is discovered). Phase 5 typically overlaps with Phase 4 once enough target is ready to deploy alongside the source. The diagram above shows these re-entries with bold arrows.

### Phase 1 — Knowledge Extraction and Source Specification

**Goal.** Produce a complete, evidence-based model of the source system and bind it to the business intent of the migration. Everything downstream is derived from what Phase 1 finds.

**Inputs.** Source repository (treated as read-only), domain documentation, subject-matter-expert interviews and recorded walkthroughs, production configuration samples, operational logs.

**Outputs** — three artifact families:

1. **Source architecture specifications** — one per dimension discovered (e.g. `specs/architecture/02-database.md`, `05-plugin-system.md`, …).
2. **Requirements document** — Mission, Goals, Premises, Constraints, plus a Requirements Traceability Matrix linking every requirement to the dimension specification where it was discovered, the decision record(s) where trade-offs about it will be resolved, and the migration phase(s) where it will be satisfied.
3. **Platform-divergence catalogue** — a living catalogue of behavioural divergences between the source and target platforms (for example, "source-platform falsy-value semantics differ from target-platform"; "source-platform implicit transaction nesting is not portable"). The catalogue is seeded in Phase 1 from research and SME input, and it grows through every later phase.

The choice of governance container for the requirements document is itself a Phase-1 decision. An Agile project may use a _project charter_; a Waterfall project may use a _project definition plan_ with a work-breakdown structure; a regulated programme may use a _programme vision_. The framework mandates the four components, not the name of the container.

### Phase 2 — Architect, Product, and SME Decisions

**Goal.** Propose every non-trivial target-architecture and migration-strategy choice; accept each decision with the stakeholders responsible for the outcome; record the rationale so the decision is auditable and re-openable if circumstances change.

Each decision record contains: context, considered options, trade-off analysis, decision, consequences, and confirmation criteria. The LLM proposes options; humans accept them.

**Who accepts each decision matters.** Each record nominates the deciders explicitly:

| Role                       | Accountable for                                                         |
| -------------------------- | ----------------------------------------------------------------------- |
| Product team               | Business impact; scope boundaries; keep/deprecate/enhance per feature   |
| Project architect          | Target architecture coherence; flow variant; cross-decision consistency |
| Subject-matter experts     | Domain-specific constraints; behavioural parity; regulatory boundaries  |
| Security / Ops / Dev leads | Trust boundaries; deployment topology; implementability                 |

A decision accepted by the implementer alone is a design note. A decision accepted by named stakeholders is a governance artifact.

**Decisions may be accepted in deferred mode.** P0 decisions (flow variant, target stack, primary data engine) are normally accepted in Phase 2 itself. P1 decisions (ORM, auth, background-worker architecture) can remain in _proposed_ state until the migration phase that first needs them. P2 decisions (logging, observability, internationalization) can evolve in parallel with implementation.

The reference project produced 19 decision records following the MADR format, all indexed in `docs/decisions/README.md` with an explicit dependency graph.

### Phase 3 — Target Specifications

**Goal.** Produce a single set of specifications that covers both the target architecture and the migration strategy for each migration phase. The framework does not separate "target architecture specs" from "migration plan specs" — they are the same set of documents, describing the same migration phase from two angles.

Each migration phase is described by three files:

- a **specification** — user-visible behaviour, functional requirements, acceptance criteria, success criteria, explicit scope and anti-scope ("_what the target should look like_")
- a **plan** — technical context, the decision records the phase depends on, the migration batches in dependency order, risk assessment, entry and exit gates ("_how we get there_")
- a **task list** — actionable steps, parallel markers, and cross-references to the source elements each step covers ("_the work to do_")

**Generation is iterative**, not big-bang. The team generates the spec set for the first unblocked migration phase (often a walking skeleton or foundational slice), executes it through Phase 4, and only then generates the next phase's specs. At that point, decisions that were previously deferred may become needed; that triggers a short loop back to Phase 2 to accept them.

The reference project produced six migration-phase spec sets — foundation, core business logic, business operations, API handlers, semantic verification, deployment — generated in sequence with two short returns to Phase 2 along the way.

### Phase 4 — Modernization

**Goal.** Turn each migration-phase spec into verified target artifacts. Phase 4 runs once per migration phase, in a fresh working session so that context is clean and the session handoff artifact is the only carrier of cross-phase state.

> _Image 4 — the Phase 4 inner loop_

Per batch in the migration phase:

1. Produce target artifacts with traceability links.
2. Run structural coverage analysis per dimension → produce a gap report.
3. Resolve gaps: generate new target code OR enhance / correct existing target code.
4. Run semantic verification on high-risk elements (Tier 1 — line-by-line with raw source quoting).
5. Run build / static analysis / unit tests.
6. Run integration and end-to-end tests at the current scope.
7. If anything fails, narrow scope and return to step 1.

The migration-phase exit gate is a checklist, not a narrative: zero unmatched in-scope elements, all automated tests green (unit + integration + end-to-end), all decision records the phase depended on in _accepted_ status, new platform-divergence catalogue entries merged, session handoff note written.

A phase may emit artifacts into any number of target repositories. Single-repository, one-to-many, and many-to-many migrations are all natural outputs of the same loop.

### Phase 5 — Hybrid Deployment and Cutover

**Goal.** Run the target alongside the source under realistic conditions; shift traffic progressively; decommission the source system when every responsibility is covered.

For most systems a big-bang cutover is prohibitively risky. The framework treats the coexistence architecture itself as a decision, not a default. Five release modes are commonly used:

| Mode                      | When to use                                                                |
| ------------------------- | -------------------------------------------------------------------------- |
| Big-bang single cutover   | Small / mid-scale projects; full regression coverage feasible              |
| Gradual coexistence       | Large systems where full cutover risk is unacceptable                      |
| Incremental traffic shift | Systems with a gateway, service mesh, or feature-flag layer                |
| Read-first / write-later  | Data-heavy systems where writes are the highest risk                       |
| Parallel-run comparison   | Pipelines, reports, or computations where output correctness is observable |

Output topology may reshape the repository set in this phase: single repo, one-to-many, many-to-one, or many-to-many — together with per-repository CI/CD configuration, infrastructure-as-code modules, service-mesh / gateway configuration, data-migration scripts, and observability configuration consistent across the new topology.

---

## The Core Mechanism: How Coverage and Gap Resolution Work Together

Pillars ②③④ together form an auditable loop that operates on every batch in Phase 4.

> _Image 5 — the coverage and gap-resolution loop_

A common misconception is that a traceability-driven pipeline works like a transpiler — feeding source code line-by-line into an AI agent and receiving target code back. It does not. The pipeline works for any migration style, including full architectural redesigns: monolith → microservices, server-rendered → SPA, SQL triggers → stream processing, single repository → many repositories.

The key insight is that **traceability is used to detect what has not yet been accounted for; it is never used to constrain how migration is done.** The agent is free to redesign, restructure, and re-architect the target system in whatever way the accepted decisions prescribe. Traceability only tracks which source elements have been accounted for.

A worked example: suppose the source is a monolith and the target is a set of microservices. The validator reports that a source function has not been accounted for. It does _not_ instruct the agent to translate those lines. Instead the agent:

1. reads the source function to understand its business role;
2. locates the correct target service per the accepted architecture;
3. inspects what the service's responsibilities already cover;
4. either implements the missing responsibility in the target idiom or, if a related target element already exists with weak or inconsistent coverage, **enhances or corrects the existing element**;
5. adds a traceability link so the validator treats the source element as accounted for.

The generate-_or_-enhance property is the decisive advantage of this approach over direct translation and over purely agentic loops. In direct translation, once a target element is produced, further source analysis cannot correct it without re-running the whole translation. In a purely agentic approach, there is no categorical signal telling the agent which existing element requires correction. Coverage analysis provides that signal: a source element whose current coverage is weak, inconsistent, or contradicted becomes an input to the next gap-resolution cycle regardless of whether target code already exists for it. The framework therefore supports gradual modernization and correction of already-written code, not just addition of new code — which is what makes correct migration possible at scale.

---

## From Architecture to Practice: A Reference Project Walkthrough

The architecture was validated end-to-end on a complete migration of a non-trivial self-hosted web application. The source was approximately 18,600 lines of PHP across 138 files, with 35 database tables, 24 plugin hook points, and 17 REST plus 40+ RPC API endpoints. The target was Python (Flask, SQLAlchemy, Celery, vanilla-JS SPA, PostgreSQL only).

> _Image 6 — artifact flow diagram_

The full migration spanned nineteen working sessions. The artifacts produced map precisely onto the five-phase pipeline:

**Phase 1 produced fifteen source architecture specifications** in `specs/architecture/`:
`01-architecture.md` (application layering and patterns), `02-database.md` (the data dimension), `03-api-routing.md`, `04-frontend.md`, `05-plugin-system.md`, `06-security.md`, `07-caching-performance.md`, `08-deployment.md`, `09-source-index.md`, `10-migration-dimensions.md`, `11-business-rules.md`, `12-testing-strategy.md`, `13-decomposition-map.md`, `14-semantic-discrepancies.md` (the 40-category divergence taxonomy), and `15-sme-review.md`. The requirements document lived in `00-project-charter.md` together with the requirements traceability matrix.

**Phase 2 produced nineteen decision records.** The P0 decisions — flow variant (ADR-0001), target framework (ADR-0002), database engine (ADR-0003) — were accepted up front. Eight P1 decisions (ORM strategy, session management, password migration, feed-credential encryption, plugin system, background worker, feed parser, HTTP client) were accepted just-in-time before the migration phases that needed them. P2 decisions on logging and internationalization remained proposed throughout. The decision dependency graph was kept in `docs/decisions/README.md`.

**Phase 3 produced six migration-phase spec sets** — foundation, core logic, business logic, API handlers, semantic verification, and deployment — each containing a spec, a plan, and a task list. Their headers cross-reference the decisions they depend on; the consistency rule ensures that when any decision's status changes, every spec referencing it is updated atomically.

**Phase 4 ran the modernization loop across six migration phases.** Target code was placed in `target-repos/ttrss-python/`. Each function, class, model, and route carries inline traceability comments of the form:

```python
# Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
# Specs:  specs/architecture/06-security.md, specs/001-foundation/spec.md
# Decisions: 0008-password-migration.md
def authenticate_user(login: str, password: str) -> Optional[User]:
    ...
```

The coverage validator was implemented as a Python script that parses both PHP source (with tree-sitter for exact element boundaries) and Python target traceability comments, producing a per-dimension report. The semantic verification report lives in `docs/reports/semantic-verification.md`. The platform-divergence catalogue grew to **40 categories covering 600+ affected call sites** by the end of Phase 4.

**Phase 5 produced the deployment topology** — production Docker Compose stack, nginx reverse-proxy configuration, pgloader-based data migration scripts, staged cutover plan — in `specs/006-deployment/` and `target-repos/ttrss-python/`.

The final structural coverage was 100% (458 / 458 in-scope source functions covered or eliminated). 27 source elements were explicitly eliminated as dead, deprecated, or superseded; each elimination is documented with the decision that justified it. The target system shipped with 1,474 automated tests (unit, integration, end-to-end) — substantially more than the source ever had — and security modernizations applied during the migration include password-hash upgrade to argon2id, feed-credential encryption with Fernet, prepared statements throughout, CSRF protection, and security headers.

A representative decision-record excerpt from the reference project:

```markdown
# 0002 — Select Python Web Framework

## Considered Options

1. Flask — closest match to source handler dispatch; native session and CSRF
2. FastAPI — modern async; no built-in sessions; client-side changes for CSRF
3. Django — full-featured but over-engineered for this codebase

## Decision: Flask

Rationale: minimises translation distance; preserves client-server contract.

## Consequences

- zero client-side changes required
- native CSRF and session model identical to source

* synchronous runtime; async deferred to Celery workers
```

And a representative migration-phase specification excerpt, showing the
unified target-architecture-and-migration-strategy structure produced in Phase 3:

```markdown
# specs/001-foundation/spec.md

## Migration Phase 1: Foundation (walking skeleton)

### What the target should look like

- Application factory with dependency injection
- Ten core ORM models (users, feeds, entries, categories, …)
- Server-side session store, signed cookies, CSRF protection
- argon2id password hashing

### What must be preserved from the source

- Existing client-server contract: same request/response shapes
- Existing cookie names so logged-in users remain logged in
- Legacy-password upgrade path (verify against legacy hash; rewrite to argon2id on next login)

### How we get there (dependency-ordered batches)

1. Models (`ttrss/models/`) — Decision: ADR-0006 (ORM strategy)
2. Authentication verifier — Decision: ADR-0008 (password migration)
3. Login / logout endpoints
4. Session middleware — Decision: ADR-0007 (session management)
5. Test suite (unit + integration)

### Exit gate

- All unit tests green
- Zero coverage gaps in the `auth/` dimension
- ADR-0006, ADR-0007, ADR-0008 in `accepted` status
- Session handoff note written for the next migration phase
```

The diagonal structure of these spec sets — what / preserve / how / exit — is
identical across all six migration phases of the reference project, which lets
reviewers move quickly between phases without re-learning the document layout.

### Quantitative outcomes

A few numbers from the reference project make the framework's effect concrete:

- **Coverage trajectory.** First-pass coverage across in-scope source functions
  was 41%. The gap-resolution mechanism (Pillar ④) drove it to 100% over the
  six migration phases. The trajectory was visible to all stakeholders because
  each migration-phase exit gate reported it.
- **Defect-detection latency.** Behavioural divergences caught during Phase 4
  were caught in the same working session in which the target code was
  produced. Without the platform-divergence catalogue and the per-dimension
  coverage report, similar projects typically catch the same class of defect
  weeks later, during integration testing.
- **Decision throughput.** Nineteen decision records were produced over
  nineteen working sessions. Each was reviewed and accepted by the named
  stakeholders before the migration phase that needed it began. Two of the
  19 (ADR-0004 on frontend strategy, ADR-0010 on plugin-system implementation)
  were re-opened by Phase-4 discoveries, accepted in a new form, and the
  downstream specs updated atomically per the consistency rule.
- **Test coverage uplift.** The target shipped with 1,474 automated tests,
  versus the source's near-zero. The migration was a net quality improvement,
  not only a technology shift.
- **Security modernisations applied during migration.** SHA-1 password hashes
  upgraded to argon2id with gradual upgrade on login; feed credentials
  re-encrypted from deprecated mcrypt to Fernet on first access; prepared
  statements throughout; CSRF protection and security headers added.
- **Output topology.** The target is one repository (`target-repos/ttrss-python/`)
  plus a separate operations layer (`docker-compose.prod.yml`, `nginx/`,
  `pgloader.load`). The pipeline could equally have produced N repositories
  for a microservice decomposition — the architecture decision to keep a
  single target repository was recorded explicitly as ADR-0001.

---

## Established Foundations and Novel Contributions

The architecture combines established practices with a small number of contributions that change what AI-assisted modernization can do.

### Established practices

- **Decision records** — Architecture Decision Records (Nygard 2011, MADR project), well-established in the software-architecture community.
- **Requirements traceability** — IEEE 830 / ISO 29148; project-charter and requirements-traceability-matrix conventions from PMBOK and arc42.
- **Spec-driven development** — the spec → plan → tasks → execution lifecycle popularized by GitHub Spec-Kit and earlier model-driven methodologies.
- **Adversarial review loops** — independent-reviewer / author cycles, used in multiple recent agentic frameworks.

### Novel contributions

- **Completeness as a verifiable predicate.** Traditional progress reports are agent self-assessments. Here, every source element is in exactly one of three categorical states (covered / eliminated / unmatched), and the migration-phase exit gate rejects the phase until the count of unmatched in-scope elements is zero. "Done" becomes a programmatically verifiable property.
- **Dimensional coverage, not file coverage.** Coverage is reported _per dimension_ — one report for the code dimension, one for the data dimension, one for the event flow, and so on. A target that covers 95% of source functions but misses 40% of hook sites is flagged immediately, rather than shipping with a silent feature gap. This replaces single-number coverage metrics with a vector that reflects actual structural risk.
- **Generate-or-enhance, driven by coverage signals.** Coverage signals trigger correction or enhancement of already-generated target code — not only generation of new code. This breaks the one-shot ceiling of transpiler-style migration and gives a purely agentic approach the categorical signal it otherwise lacks.
- **Unified target-architecture and migration-strategy specifications.** Phase 3 produces one spec set, not two. The question "what should this look like?" and the question "how do we migrate to it?" are answered in the same document, which eliminates the drift that accumulates when architecture and migration plans are maintained separately.
- **Platform-divergence catalogue as a living artifact.** A project-specific catalogue of source ↔ target behavioural divergences is seeded in Phase 1 and grown in every later phase. It transforms semantic verification from ad-hoc review into a checklist-driven audit with falsifiable entries, and prevents the same class of error from recurring across migration phases.
- **Iterative, deferrable decisions bound to migration phases.** P1/P2 decisions can be accepted just-in-time, or in parallel with implementation, without blocking progress on unrelated phases. The requirements traceability matrix and the decision index keep the dependency graph explicit; a Phase-4 discovery can legitimately re-open a Phase-2 decision without invalidating already-completed migration phases.

---

## Stakeholder Benefits

The framework is designed so that each named stakeholder gets a concrete, verifiable benefit, not a generic promise of "AI productivity."

| Role                       | Concrete benefit                                                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Subject-matter expert      | Review becomes a mechanical walk of cited source ↔ target pairs. No more "where did this code come from?"                                                          |
| Product owner              | Decisions are explicit, named, and reviewable by non-specialists; trade-offs become re-openable when business needs change                                         |
| Project architect          | One unified spec set per migration phase; deferred decisions bound to the phases that need them; consistency rule enforces atomic updates                          |
| Security / compliance lead | Every credential, every cipher, every security-relevant code path is traceable to source and to the decision that justified its target form                        |
| Operations lead            | Phase 5 produces the full deployment topology — IaC, CI/CD, reverse-proxy, data-migration scripts — not just target code                                           |
| Development lead           | Phase-4 exit gate is machine-checkable; per-dimension coverage replaces percentage-of-LOC metrics; modernization can stop mid-migration without losing audit trail |

---

## Looking Ahead

The field is advancing rapidly as model capabilities mature and context windows expand. Several developments are worth watching:

- **Better source inventory tooling.** Tree-sitter-based parsers, language-server indexes, and code-intelligence graph stores (SCIP, stack-graphs, CodeQL) will make the source-side of the coverage validator faster and more precise.
- **Living divergence catalogues across organizations.** Today each project grows its own platform-divergence catalogue. Shared, versioned catalogues for common platform pairs (Java 8 → Java 21, Python 2 → Python 3, Oracle PL/SQL → PostgreSQL, AngularJS → Angular) would amortize the cost across many migrations.
- **Multi-agent orchestration frameworks.** Microsoft Agent Framework, LangGraph, PydanticAI and others are converging on typed, declarative orchestration of LLM agents. The five-phase pipeline maps naturally onto these substrates.
- **Formal verification for the semantic verification step.** For safety-critical sub-systems, semantic verification could be lifted from checklist-driven audit to formal equivalence proofs — a natural fit with current research on LLM-assisted theorem proving.

The question is no longer whether AI-driven modernization is feasible. It is which architecture will do it reliably, at scale, and in a way that auditors, product teams, and operations leads can each verify independently.

The architecture in this article — dimension-driven, traceability-first, coverage-validated, and built around gradual gap resolution rather than one-shot translation — is one practical answer.

---

## References

**Foundational frameworks and patterns**

- Nygard, M. (2011). _Documenting Architecture Decisions_. The ADR convention adopted across the architecture community; MADR project (`adr.github.io/madr`).
- IEEE Standard 830-1998 and ISO/IEC/IEEE 29148-2018. Requirements engineering vocabulary and recommended practice.
- arc42 documentation template (`arc42.org`). The "Introduction and Goals" section corresponds to the requirements document used here.
- van Lamsweerde, A. (2001). _Goal-Oriented Requirements Engineering_. RE 2001. Foundational reference for the Mission / Goals decomposition.

**AI-assisted migration: surveys and methodologies**

- DARPA TRACTOR program — _Translating All C to Rust_. Public charter; representative example of government-funded research into AI-assisted migration.
- Microsoft Research (2025). Hiring and clarification posts on AI-assisted Rust migration tooling.
- GitHub Spec-Kit project (`github.com/github/spec-kit`). Spec-driven development tooling used as the orchestration layer in the reference project.

**Adjacent academic work informing specific pillars**

- Traag, V. A., Waltman, L., & van Eck, N. J. (2019). _From Louvain to Leiden: guaranteeing well-connected communities_. Scientific Reports 9, 5233. Community-detection methods applicable to dimensional partitioning.
- Blondel et al. (2008). _Fast unfolding of communities in large networks_. arXiv:0803.0476. Original Louvain algorithm.
- Sarkar, Waddell & Dybvig (2004). _A Nanopass Framework for Compiler Education_. JFP. Ordered-pass design pattern that informs the spec → decision → migration-phase pipeline.

**Standards and conventions**

- Linux Foundation / Agentic AI Foundation. _AGENTS.md cross-tool standard for AI-agent instructions_ (`agents.md`).
- MADR 4.0 — Markdown Any Decision Records (`adr.github.io/madr`).
- INCOSE Systems Engineering Handbook v5. Requirements layering and stakeholder analysis.

---

_About the author. The architecture described in this article was developed and validated during a complete PHP-to-Python migration of a self-hosted web application over nineteen working sessions in 2026. The reference project artifacts — fifteen source architecture specifications, nineteen decision records, six migration-phase spec sets, a 40-category platform-divergence catalogue, and the full target codebase — are available as a working example._
