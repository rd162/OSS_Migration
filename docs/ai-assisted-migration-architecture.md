# AI-Assisted Software Migration Architecture

**A Dimension-Driven, Traceability-First Framework for Migrating Software Systems Across Technology Stacks**

---

## Abstract

This document describes a reproducible architecture for large-scale, AI-assisted software migration.
The framework is technology-agnostic: the same pipeline applies to language migrations,
framework shifts, monolith-to-microservices decompositions, data pipeline rewrites,
protocol library ports, and modernisations in which a single source repository
becomes many target repositories (or many sources consolidate into one).

The framework rests on three mechanisms:

- **Traceability** - every meaningful target element carries a link back to
  the source element(s) that shaped it *and* to the specification(s) and decision(s)
  under which it was produced.
- **Coverage Validation** - programmatic comparison of the source inventory
  against the target traceability graph, producing a categorical status
  (covered / eliminated / unmatched) for every source element.
- **Gap Resolution** - a review cycle in which unmatched source elements
  are interpreted by an AI agent, placed into the target architecture,
  and either generate new target code or enhance existing target code.
  The same cycle rewrites or corrects previously generated target code
  when coverage analysis exposes behavioural or structural defects in it.

Together these mechanisms turn AI-assisted migration from a probabilistic,
best-effort activity into an auditable, measurable process
with an explicit and verifiable notion of *completeness*.

For a catalogue of artifacts produced by an end-to-end application of the framework,
see Appendix B.

---

## Pipeline Overview

The framework is a sequence of inception stages executed once per project,
followed by a per-phase execution loop that repeats until the migration is complete.

```text
  +--------------------------------------------------------------------+
  |                      INCEPTION (once per project)                  |
  |                                                                    |
  |   Stage 1. Deep Research and Knowledge Extraction                  |
  |             -> dimension specifications                            |
  |       v                                                            |
  |   Stage 2. Requirements Specification                              |
  |             -> Mission / Goals / Premises / Constraints +          |
  |                requirements traceability matrix                    |
  |       v                                                            |
  |   Stage 3. Architecture Decisions                                  |
  |             -> decision records (priority-ordered; acceptance may  |
  |                be up-front, just-in-time, or parallel)             |
  |       v                                                            |
  |   Stage 4. Phase Breakdown                                         |
  |             -> per-phase specification, plan, and task list        |
  +--------------------------------------------------------------------+
                                    v
  +--------------------------------------------------------------------+
  |          Stage 5. PER-PHASE EXECUTION LOOP                         |
  |                                                                    |
  |     5.1  Load phase specification, plan, task list                 |
  |     5.2  Produce target artifacts with traceability links          |
  |     5.3  Structural Coverage Analysis                              |
  |     5.4  Gap Resolution (generate new or enhance existing)         |
  |     5.5  Semantic (behavioural) verification                       |
  |     5.6  Build / static analysis / automated tests                 |
  |     5.7  Phase exit gate: coverage, tests, decisions, specs        |
  |     5.8  Session handoff                                           |
  +--------------------------------------------------------------------+
```

Every arrow in the diagram is a concrete artifact hand-off, not a narrative transition.
A complete artifact inventory is given in Appendix B.

---

## Stage 1 — Deep Research and Knowledge Extraction

**Goal.** Produce a complete, evidence-based model of the source system
before any target-side decision is taken.

**Inputs.** Source repository (treated as read-only), domain documentation,
subject-matter-expert interviews, recorded walkthroughs, production configuration samples,
operational logs, and any external specifications or contracts the system implements.

**Outputs.** A set of *dimension specifications*, one per structural axis
discovered in the source. Each dimension specification is self-contained
and cross-references the source by relative path and line number
rather than duplicating source content.

**Dimensions are discovered, not prescribed.** Every software system exposes its own
set of structural axes, and the framework does not fix the list in advance.
A *dimension* is any axis along which source elements are related in a way
that materially constrains migration order, target partitioning, or verification strategy.
Each such axis is captured as a separate specification.
Common dimensions include:

- dependency graph between code elements (who calls whom)
- data-model graph (entities, tables, relationships)
- module / package graph (who imports or includes whom)
- file relationship graph (static include and dynamic load edges)
- frontend / backend coupling graph (which client code depends on which server endpoint)
- service dependency graph (microservice-to-microservice edges)
- event / message flow graph (producers, topics, consumers)
- plugin and extension-point graph
- data-pipeline topology (sources → transforms → sinks)
- protocol state machine
- configuration and feature-flag surface
- security surface (authentication, authorisation, crypto)
- concurrency and scheduling model
- regulatory / compliance boundary
- hardware-abstraction layer
- API contract surface (inbound, outbound)

A broader catalogue and applicability matrix for different system types
is given in Appendix A.

**On the source-file inventory.** Because the file relationship graph is itself a dimension,
there is no separate "table of files" artifact. The file-level view is one dimension
specification among others, produced by the same inventory and analysis step.

Artifacts produced by this stage are a collection of dimension specifications
(see Appendix B for the reference inventory) together with a subject-matter-expert
knowledge capture document when recordings or interviews are used.

---

## Stage 2 — Requirements Specification

**Goal.** Bind the source analysis to the business intent of the migration
by producing a structured requirements specification.

The specification has four mandatory components, each derived from a different analytic step.
The components are **abstract and generic**; the concrete name of the containing document
depends on the governance model adopted by the project
(Agile, Waterfall, PRINCE2, PMBOK, SAFe, RUP, or bespoke).
The framework mandates the presence of the four components, not the name of the container.

| Component       | Definition                                                             | Litmus test                                            |
|-----------------|------------------------------------------------------------------------|--------------------------------------------------------|
| **Mission**     | Single-sentence terminal value answering *why* the migration exists    | Recursive "why?" yields a tautology (fixed point)      |
| **Goals**       | Concrete objectives that, if changed, change the solution type         | Changing a goal changes the kind of solution needed    |
| **Premises**    | Assumptions that must hold for the goals to be achievable              | If false -> the corresponding goal becomes impossible  |
| **Constraints** | Hard (violation = rejection) and soft (violation = penalty) boundaries | Violation of a hard constraint halts the project       |

The recursive "why?" derivation of the Mission is a fixed-point procedure:
the Mission is the first answer that is circular with itself
(a tautology of terminal value). Goals are the concrete objectives that sit
immediately below the Mission. Premises are the assumptions without which goals fail;
each premise carries a source citation and a risk assessment.
Constraints are the bounded-rationality rules imposed by law, policy, team capacity,
infrastructure, or domain. The full methodology is formalised in the
`requirements-extractor` skill included in `.agents/skills/requirements-extractor/`.

**The choice of governance model is itself a first-phase decision.**
Different projects use different artifact containers for the four components.
An Agile project may use a *project charter*; a Waterfall project may use a
*project definition plan* with a *work-breakdown structure*;
a regulated programme may use a *programme vision* with a *statement of architecture work*.
The framework is neutral over the container; the four components are mandatory;
the container name and the surrounding governance artifacts are project-specific.

Stage 2 also produces a **requirements traceability matrix** linking every requirement
to the dimension specification where it was discovered, the decision record(s)
where trade-offs about it were resolved, and the phase specification(s)
where it is satisfied. The matrix is the primary device that keeps Stage 1,
Stage 3, and Stage 4 mutually consistent.

---

## Stage 3 — Architecture Decisions

**Goal.** Record every non-trivial migration choice with full trade-off analysis
so that the rationale is auditable and the decision is re-openable
if circumstances change.

Each decision is captured as a formal record
(MADR, ISO/IEC/IEEE 42010, Y-statements, or bespoke templates all work)
with the shape: context, considered options, trade-off analysis,
decision, consequences, confirmation criteria.

**Priority classes.**

| Priority | Scope                                                       | Accepted before          |
|----------|-------------------------------------------------------------|--------------------------|
| P0       | Blocks all work (flow variant, target stack, data engine)   | Stage 4 begins           |
| P1       | Blocks a specific phase (ORM, auth, workers, and so on)     | That phase begins        |
| P2       | Deferrable, no blocking dependency                          | The final release        |

**Decisions may be accepted in deferred mode.** A decision does not have to be closed
during inception. The framework supports three acceptance modes explicitly:

- **Up-front.** P0 decisions are normally accepted in Stage 3.
- **Just-in-time.** A P1 decision can remain in *proposed* state until the phase
  that first needs it; the phase entry gate then requires its acceptance.
- **Parallel with implementation.** A decision about an incremental concern
  (logging, observability, i18n) may evolve alongside early implementation
  as evidence accumulates; the decision is accepted once the design stabilises.

The framework explicitly supports decisions that are rejected or superseded later
as evidence changes; a superseded decision carries a forward link to its replacement
so that the full history remains auditable.

**How options are generated.** Each decision must contain at least two evaluated options
with trade-off analysis. Options can come from human architects, vendor proposals,
prior-art research, or iterative LLM-driven candidate generation.
Appendix D describes one structured elimination-and-replacement protocol;
the framework is agnostic to how options are sourced.

**Consistency constraint.** When the status of a decision changes
(proposed -> accepted, deprecated, superseded), every document that references that decision
must be updated atomically. Partial status updates are a leading source of
multi-session contradictions and must be treated as a build-breaking defect.
A concrete consistency checklist is captured in Appendix C.

---

## Stage 4 — Phase Breakdown

**Goal.** Convert the accepted decisions and dimension specifications into a
dependency-ordered sequence of executable phases, each small enough
to fit in a single working session.

Each phase is described by three artifacts
(named here generically; concrete container names are project-specific):

- a **phase specification** — user-visible behaviour, functional requirements,
  acceptance criteria, success criteria, explicit scope and anti-scope
- a **phase plan** — technical context, the decision records the phase depends on,
  dependency-ordered batches, risk assessment, an entry gate and an exit gate
- a **phase task list** — actionable steps, parallel markers, and cross-references
  to the source elements each step covers

The order of phases is itself an architecture decision, because the dimension chosen as
primary driver determines the entire project structure. A catalogue of flow variants
and the factors that favour each is given in Appendix E.

**Exit gates.** Every phase has an explicit exit gate listing machine-checkable conditions:
tests passing, coverage thresholds, semantic verification clean, referenced decisions accepted.
The gate is a checklist, not a narrative.

---

## Stage 5 — Per-Phase Execution Loop

Each phase is executed in a fresh working session so that context is clean
and the session handoff artifact is the only carrier of cross-phase state.
A phase may emit artifacts into any number of target repositories — single-repository,
one-to-many, and many-to-many migrations are all natural outputs of the same loop.

```text
  For each batch in the phase:
    (a) Produce target artifacts with traceability links
    (b) Structural coverage analysis  ->  gap report
    (c) Gap resolution                ->  generate new OR enhance existing
    (d) Semantic verification on high-risk elements
    (e) Build / static analysis / tests
    (f) If any step fails -> narrow scope, return to (a)
    (g) Otherwise -> next batch

  Phase exit:
    - Coverage report shows zero unmatched in-scope elements
    - All automated tests green
    - All decision records the phase depended on are in "accepted" status
    - Session handoff note written for the next phase
```

Coverage and semantic checks are executed *within* each batch of the phase loop,
not at the end of the project. This is how defects are caught while context is hot
rather than during late-stage integration.

The three core mechanisms that make this loop auditable —
Traceability, Coverage Validation, and Gap Resolution — are described next.

---

## The Core Mechanism: Traceability, Coverage, and Gap Resolution

### Why AI models miss elements of the source

Even with large-context models capable of loading an entire repository,
source elements are systematically missed during migration:

- **Attention dilution.** Long source files cause attention to concentrate on prominent
  elements while skipping less prominent ones.
- **False coverage.** File-level correspondence claims coverage of an entire file
  while actually covering only a subset of its elements.
- **Name collision.** Elements with common names are matched by name alone
  across unrelated files (a naive global-name validator makes this failure invisible).
- **Cross-session drift.** Work done in session *N* may conflict with assumptions
  from session *N − k*.

Structural coverage analysis reveals these gaps directly, and semantic verification
then detects whether the covered code actually preserves behaviour.

### Traceability

Every meaningful target element (function, class, method, model, route, constant,
schema object, pipeline stage, configuration key) carries two kinds of link:

- **Source link** — one or more references to the source element(s)
  from which the target element was derived, together with a categorical
  link type (see below).
- **Specification / decision link** — one or more references to the phase specification,
  dimension specification, or decision record under which the target element was produced.

The second kind of link makes the target *doubly* traceable: it is possible to ask
*which source shaped this code* and *which decision justified this shape*.

Source link types, in order of specificity:

| Type          | Meaning                                                                   |
|---------------|---------------------------------------------------------------------------|
| Direct        | Source element maps to a single target element                            |
| Method-level  | Source method maps to target method within a class                        |
| File-level    | Target module aggregates one source file                                  |
| Multi-source  | Target element combines logic from multiple source files                  |
| Schema-level  | Target model derived from a schema definition                             |
| Inferred      | Target code adapted from source patterns; no direct equivalent            |
| New           | Genuinely new code; no source equivalent                                  |
| Eliminated    | Source intentionally not ported (dead, deprecated, or superseded)         |

Traceability links can be recorded in several ways.
The representation is an implementation choice; the validator only requires that links be
programmatically parseable. Representation options are described in Appendix F.

### Structural Coverage Analysis and Gap Resolution

A common misconception is that a traceability-driven pipeline works like a transpiler —
feeding source code line-by-line into an AI model and receiving target code back.
**It does not.** The pipeline works for any migration style, including full architectural
redesigns (monolith -> microservices, server-rendered -> SPA, SQL triggers -> stream processing,
single repository -> many repositories).

The key insight:
**traceability is used to detect what has not yet been accounted for;
it is never used to constrain how migration is done.**
The AI model is free to redesign, restructure, and re-architect the target system
in whatever way the accepted decisions prescribe. Traceability only tracks
which source elements have been accounted for.

```text
                    SOURCE CODEBASE
                (all elements inventoried)
                           |
                    +------v-------+
                    |  COVERAGE    |
                    |  VALIDATOR   |
                    |              |
                    |  compares    |
                    |  source      |
                    |  inventory   |
                    |  against     |
                    |  target      |
                    |  traceability|
                    |  graph       |
                    +------+-------+
                           |
          +----------------+----------------+
          |                                 |
     ACCOUNTED FOR                    GAP REPORT
     (covered U eliminated)           (unmatched or low-confidence
          |                            source elements)
          |                                 |
          |                           +-----v-----+
          |                           | AI AGENT  |
          |                           | interprets|
          |                           | each gap  |
          |                           | and:      |
          |                           |  - adds a |
          |                           |    new    |
          |                           |    target |
          |                           |    element|
          |                           |  - or     |
          |                           |    enhances|
          |                           |    an     |
          |                           |    existing|
          |                           |    element|
          |                           |  - or     |
          |                           |    corrects|
          |                           |    a      |
          |                           |    previous|
          |                           |    one    |
          |                           +-----+-----+
          |                                 |
          |                           emit target edit +
          |                           traceability link
          |                                 |
          +----------------+----------------+
                           |
                    +------v-------+
                    | RE-VALIDATE  |
                    | coverage     |
                    | increases    |
                    | monotonically|
                    | until 100%   |
                    +--------------+
```

**Worked example.** Suppose the source is a monolith and the target is a set of microservices.
The validator reports that a source function has not been accounted for.
It does *not* instruct the agent to translate those lines.
Instead the agent:

1. reads the source function to understand its business role;
2. locates the correct target service per the accepted architecture;
3. inspects what the service responsibilities already cover;
4. implements the missing responsibility in the target idiom,
   **or enhances an already-implemented function** when coverage analysis shows
   that the existing implementation is incomplete, inconsistent with a new dimension,
   or contradicted by a later-accepted decision;
5. adds a traceability link so the validator treats the source element as accounted for.

This generate-*or*-enhance property is the decisive advantage of coverage-driven migration
over direct translation and over purely agentic approaches.
In direct translation, once a target element is produced, further source analysis
cannot correct it without re-running the whole translation.
In purely agentic approaches, there is no categorical signal telling the agent
*which* existing element requires correction. Coverage analysis provides that signal:
a source element whose current coverage is weak, inconsistent, or contradicted
becomes an input to the next gap-resolution cycle regardless of whether target code
already exists for it. The framework therefore supports gradual enhancement
and correction of already-written code, not just addition of new code —
which is what makes correct migration and modernisation possible at scale.

The mechanism applies equally well to:

- **Near-identical translations** — most elements map 1:1.
- **Framework migrations** — structure changes, elements mostly map.
- **Full redesigns** — source elements scatter across many targets;
  traceability tracks which are accounted for.
- **Technology shifts** — source units become fundamentally different target units
  (triggers -> streaming jobs, stored procedures -> services, monolith functions -> microservice endpoints).
- **Repository topology shifts** — one-to-many (decomposition),
  many-to-one (consolidation), many-to-many (reshaping).

### The Coverage Validator

A source-agnostic validator performs four steps:

1. **Source inventory.** Parse every source artifact to capture an exact element list.
   The parsing technology is an implementation choice
   (agent-built regular expressions, language server indexes, or AST parsers);
   options and trade-offs are described in Appendix G.
2. **Target scanning.** Parse every target artifact for traceability links.
3. **Strict matching.** A source element is *covered* only when the target traceability
   link references the *same source location*. There is no global-name fallback;
   a target element linked to one source file does not cover a same-named element
   in a different source file.
4. **Dimension cross-check.** Verify that dependency edges, entity references,
   and integration points from the dimension specifications are present in the target.

Each source element falls into exactly one of three categories:

| Category    | Definition                                                                |
|-------------|---------------------------------------------------------------------------|
| Covered     | Target code with a traceability link pointing to this source element      |
| Eliminated  | Documented as dead, deprecated, or superseded; not ported                 |
| Unmatched   | No target equivalent — a gap that must be resolved before the phase exits |

Unmatched elements feed Gap Resolution. The loop continues until
coverage reaches 100% of in-scope elements (eliminated + covered = total)
or until the phase exit gate is explicitly waived with a documented exception.

### Semantic (behavioural) verification

Structural coverage proves that every source element has been accounted for.
It does not prove that the target behaves correctly.
A target element can be structurally covered but semantically wrong.

Semantic verification compares source / target element pairs according to a depth tier:

| Tier | Criteria                                              | Depth                                          |
|------|-------------------------------------------------------|------------------------------------------------|
| 1    | Complex logic, many branches, cross-cutting callers   | Line-by-line with source quoting               |
| 2    | Moderate complexity                                   | Block-level with spot checks                   |
| 3    | Simple wrappers, accessors                            | Signature and return type                      |
| 4    | Data models, schemas                                  | Field-by-field                                 |

Tier-1 reviews quote raw source lines from both files.
Summarised reviews without source quotes systematically miss structural defects
(misindented loop bodies, dropped branches, inverted conditions).
A concrete, representative discrepancy taxonomy is given in Appendix H.

### Platform-knowledge catalogue

During migration the team accumulates a catalogue of patterns where the source
and target platforms diverge despite superficially similar code.
Each entry documents the source pattern, how the target differs,
an estimated frequency, and the recommended remediation.
The catalogue becomes the reference used during semantic verification
and prevents the same class of error from recurring across phases.
See Appendix H for a representative example.

### Integration-pipeline verification

Per-element verification catches per-element defects.
It does not catch defects that emerge when data flows through multiple elements
with incompatible assumptions — for example, an identifier constructed one way in
function *f* but looked up differently in function *g*.

The framework defines a small number of end-to-end integration pipelines
and verifies each as an ordered contract: boundary-by-boundary,
the data shape produced at step *k* must match the shape consumed at step *k + 1*.
Appendix I describes the mechanism in detail.

---

## Functionality Adjustment

**Goal.** Align migration scope with business needs *before and during* implementation,
using the same artifact-driven pipeline.

The framework provides three integration points for product and subject-matter-expert input:

1. **Feature scope review** (during Stage 1). Product confirms which features are kept as-is,
   enhanced, deprecated, or eliminated. The outcome is a feature scope matrix
   referenced by all later stages.
2. **SME knowledge ingestion** (any time). Recordings, screenshots, spreadsheets,
   and walkthroughs of the working source application are ingested, transcribed,
   and used to generate end-to-end test scenarios and to discover features
   not visible from source code analysis alone.
3. **Sampled SME verification** (during each phase). Randomly sampled source / target
   element pairs are reviewed by SMEs. This catches divergences that no automated
   check can detect (domain-specific behaviour, undocumented business rules,
   cosmetic expectations).

---

## Hybrid Deployment and Coexistence

For most systems a big-bang cutover is prohibitively risky; source and target must coexist
for some period. The framework treats the coexistence architecture itself as a decision,
not a default. The pipeline is flexible enough to span the full range:

- **Big-bang, single-repository** — small and mid-scale projects where the entire migration
  is completed, verified, and released in one cutover.
- **Gradual coexistence** — source and target run side-by-side for months or years
  with a documented sunset plan; incremental traffic migration via API gateway,
  shared database, compatibility shim, or service mesh.
- **Repository topology change** — the output may be one-to-many (monolith decomposition),
  many-to-one (consolidation), or many-to-many (reshaping), together with
  the CI / CD, infrastructure-as-code, and deployment manifests for the entire
  target topology. The framework is not a repository-to-repository translator;
  it is a knowledge-to-artifacts pipeline whose output is whatever set of repositories
  the accepted architecture prescribes.

Representative coexistence patterns:

| Pattern                   | Mechanism                                                         |
|---------------------------|-------------------------------------------------------------------|
| Web applications          | Shared database; API gateway; compatibility shim                  |
| Microservices             | Service-by-service cutover; contracts preserved at each step      |
| Protocol libraries        | Linked side-by-side; conformance tests against both               |
| Data pipelines            | Parallel runs on a data subset; output equivalence check          |
| Event-driven systems      | Dual consumers during transition; producer-by-producer switchover |
| Embedded / firmware       | Dual-image slots; staged rollouts with automatic rollback         |

Every shim, dual-path, or bridge is tracked as a removal item with a documented sunset.

---

## Applicability Across System Types

The pipeline is technology-agnostic. What changes between applications is
the set of dimensions discovered in Stage 1, the decisions taken in Stage 3,
and the flow variant chosen in Stage 4.
Appendix A catalogues dimensions observed across system types;
Appendix E catalogues flow variants.

The three core mechanisms (Traceability, Coverage Validation, Gap Resolution)
apply unchanged to language migrations, framework shifts, monolith decompositions,
CLI ports, desktop-to-web moves, network-protocol library ports,
data pipeline rewrites, stored-procedure extractions, and embedded / IoT modernisations.

---

## Benefits

- **Explicit trade-offs.** Every non-trivial choice is recorded as a decision with analysis.
- **Measurable completeness.** Coverage is a programmatic metric checked at every phase gate,
  not a claim.
- **Generate-or-enhance.** Coverage signals support *correcting and enhancing* already-generated
  target code as the source analysis deepens — not only adding new code.
- **Early error detection.** Errors are caught within the same session they are introduced,
  not during final integration.
- **Test generation for legacy systems.** The target ends with richer automated test coverage
  than the source ever had, turning migration from a risk event into a quality event.
- **Behavioural correctness.** The platform-knowledge catalogue prevents systematic
  translation errors from recurring.
- **Stakeholder-friendly decision records.** Trade-off analysis tables can be reviewed
  by non-specialist stakeholders and revisited when business needs change.
- **Flexible output topology.** The pipeline produces whatever set of repositories,
  CI / CD pipelines, infrastructure-as-code, and deployment manifests the accepted
  architecture prescribes.

---

# Appendices

All appendices are either catalogues, illustrative examples, or implementation notes.
Each real project will instantiate its own versions of these tables.
Nothing in the appendices is prescriptive.

---

## Appendix A — Dimension Catalogue

Dimensions commonly discovered during Stage 1.
Every real project should infer its own set.

### Structural dimensions (common to most systems)

| Dimension                   | Captures                                              | Migration impact                             |
|-----------------------------|-------------------------------------------------------|----------------------------------------------|
| Call graph                  | Which elements call which others                      | Dependency order for migration               |
| Data model / entity graph   | Tables, schemas, relationships, clusters              | Models required before business logic        |
| Module / package graph      | Import and include chains between packages            | Build order; circular-dependency risk        |
| File relationship graph     | Static include and dynamic load edges between files   | File-level partitioning                      |
| Service dependency graph    | Inter-service calls                                   | Distributed-system migration order           |
| Event / message flow graph  | Producers, topics, subscribers                        | Event-driven migration order                 |
| Infrastructure dependency   | Services <-> infrastructure (DB, cache, queue)        | Cloud / platform migration                   |

### Domain-specific dimensions (examples)

| Dimension                              | Example system types                                 |
|----------------------------------------|------------------------------------------------------|
| Frontend / backend coupling            | Web apps with server-rendered HTML or SPAs           |
| Plugin / extension-point graph         | Applications with hook points and extension APIs     |
| Protocol state machine                 | Network-protocol implementations                     |
| Data pipeline topology                 | ETL, stream processors, trigger chains               |
| Configuration / feature-flag surface   | Systems with extensive config or feature flags       |
| Security surface                       | Auth flows, encryption, session management           |
| Concurrency and scheduling model       | Multi-threaded, async, event-driven                  |
| API contract surface (inbound)         | Public APIs with external consumers                  |
| API contract surface (outbound)        | Integrations with third-party services               |
| Regulatory / compliance boundary       | Regulated industries (finance, health, defence)      |
| Hardware abstraction layer             | Embedded / IoT                                       |
| Data warehouse / OLAP cubes            | Analytics platforms                                  |
| File-based persistent state            | Legacy systems with disk-backed state                |
| Search index topology                  | Systems with dedicated search infrastructure         |
| Object-storage key namespace           | Systems with substantial blob storage                |
| Scheduler / cron graph                 | Systems with time-driven background work             |
| Multi-tenant isolation boundary        | SaaS platforms                                       |
| Observability topology                 | Systems with custom metrics / log pipelines          |

### Applicability matrix

| System type                   | Typical primary dimension   | Typical secondary dimensions              |
|-------------------------------|-----------------------------|-------------------------------------------|
| Web application (MVC)         | Entity graph                | Call graph, frontend coupling             |
| Server-rendered app           | Frontend / backend coupling | Entity graph, template system             |
| Desktop application           | UI event model              | Call graph, persistence                   |
| CLI tool                      | Call graph                  | Argument parsing, I/O model               |
| Data processing pipeline      | Pipeline topology           | Data model, checkpoint semantics          |
| Network protocol library      | Protocol state machine      | Timer semantics, packet encoding          |
| Microservices                 | Service dependency graph    | API contracts, message topics             |
| Stored-procedure system       | Pipeline topology           | Entity graph, transaction boundaries      |
| Event-driven architecture     | Message topics              | Service graph, event schema               |
| Embedded / IoT                | Hardware abstraction        | Call graph, memory model                  |
| Analytics warehouse           | OLAP cube / DAG topology    | Data model, scheduler graph               |
| SaaS multi-tenant platform    | Tenant isolation boundary   | Service graph, data-model graph           |

---

## Appendix B — Reference Project Artifact Inventory

This appendix catalogues the artifacts produced by one end-to-end application of the framework.
The inventory is indicative, not prescriptive; each real project will produce a different set
depending on its discovered dimensions and accepted decisions.

### Summary

| Metric                                            | Value                                                   |
|---------------------------------------------------|---------------------------------------------------------|
| Source lines of code                              | ~18,600                                                 |
| Source files                                      | 138                                                     |
| Database tables                                   | 35 (31 active, 4 deprecated / eliminated)               |
| Plugin hooks                                      | 24                                                      |
| Inbound API endpoints                             | 17 REST, 40+ RPC                                        |
| Working sessions                                  | 19                                                      |
| Dimension specifications                          | 15 (architecture root + per-dimension documents)        |
| Phase specifications                              | 6                                                       |
| Architecture decisions                            | 19                                                      |
| Automated tests at completion                     | 1,474 (unit + integration + end-to-end)                 |
| Platform-knowledge patterns catalogued            | 40 categories, 600+ affected call sites                 |
| Integration pipelines verified                    | 8                                                       |
| Final structural coverage                         | 100% (458 / 458 in-scope elements)                      |
| Eliminated source elements                        | 27+                                                     |
| Security modernisations during migration          | Password-hash upgrade, credential encryption, prepared statements, CSRF, security headers |

### Dimension specifications (Stage 1 output)

| Path                                                | Content                                                                           |
|-----------------------------------------------------|-----------------------------------------------------------------------------------|
| specs/architecture/01-architecture.md               | Application layering, patterns, request lifecycle                                 |
| specs/architecture/02-database.md                   | Entity / schema dimension                                                         |
| specs/architecture/03-api-routing.md                | Inbound API contract surface                                                      |
| specs/architecture/04-frontend.md                   | Frontend / backend coupling                                                       |
| specs/architecture/05-plugin-system.md              | Plugin / extension-point graph                                                    |
| specs/architecture/06-security.md                   | Security surface                                                                  |
| specs/architecture/07-caching-performance.md        | Caching, concurrency, scheduling                                                  |
| specs/architecture/08-deployment.md                 | Deployment topology                                                               |
| specs/architecture/09-source-index.md               | File relationship graph (roles, dependencies, annotations)                        |
| specs/architecture/10-migration-dimensions.md       | Call-graph communities; cross-dimension synthesis                                 |
| specs/architecture/11-business-rules.md             | Business-rule inventory                                                           |
| specs/architecture/12-testing-strategy.md           | Test-category matrix                                                              |
| specs/architecture/13-decomposition-map.md          | Source-element -> target-module decomposition                                     |
| specs/architecture/14-semantic-discrepancies.md     | 40-category discrepancy taxonomy, semantic traps, pipeline contracts (Appendix H) |
| specs/architecture/15-sme-review.md                 | Feature inventory from SME walkthrough                                            |

### Requirements specification (Stage 2 output)

| Path                                           | Content                                                                                     |
|------------------------------------------------|---------------------------------------------------------------------------------------------|
| specs/architecture/00-project-charter.md       | Mission, Goals, Premises, Constraints, requirements traceability matrix (Agile container)   |

### Architecture decisions (Stage 3 output)

docs/decisions/0001-migration-flow-variant.md through 0019-preferences-modal-pattern.md,
plus docs/decisions/README.md (index and dependency graph) and
docs/decisions/compliance-review-response.md (cross-decision review).

### Phase specifications (Stage 4 output)

| Path                                                   | Scope                                                                     |
|--------------------------------------------------------|---------------------------------------------------------------------------|
| specs/001-foundation/{spec,plan,tasks}.md              | Models, auth, DB bootstrap, app factory                                   |
| specs/002-core-logic/{spec,plan,tasks}.md              | Feed parsing, counter cache, filters, labels, sanitisation                |
| specs/003-business-logic/{spec,plan,tasks}.md          | Preferences CRUD, digests, OPML                                           |
| specs/004-api-handlers/{spec,plan,tasks}.md            | 17 API operations, authentication guards, tree-building algorithms        |
| specs/005-semantic-verification/{spec,plan,tasks}.md   | 40-category taxonomy, 105+ remediations, 598 tests, 0 unresolved gaps     |
| specs/006-deployment/{spec,plan,tasks}.md              | CI, coverage gate, Docker / Compose / reverse proxy, data migration       |

### Representative artifact shapes

**Decision record excerpt (Agile container — MADR 4.0 format):**

```markdown
# 0002 — Select Target Web Framework

## Considered Options
1. Framework A — closest match to source handler dispatch; native session and CSRF
2. Framework B — modern async; no built-in sessions; requires client-side changes for CSRF
3. Framework C — full-featured but over-engineered for this codebase

## Decision: Framework A
Rationale: minimises translation distance; preserves client-server contract.
```

**Traceability link examples (representation: inline comment):**

```text
# Direct match
# Source: <source path>:<qualified name> (lines 706-771)
# Specs:  specs/architecture/06-security.md, specs/001-foundation/spec.md
# Decisions: 0008-password-migration.md

# Multi-source
# Source: <source1>:<name> (lines 45-120)
#       + <source2>:<name> (lines 200-450)
# Specs: specs/architecture/02-database.md, specs/architecture/03-api-routing.md

# Inferred
# Inferred from: <source pattern>; no direct source equivalent
# Specs: specs/001-foundation/spec.md
# Decisions: 0007-session-management.md

# New (no source equivalent)
# New; no source equivalent — schema migration infrastructure
# Specs: specs/006-deployment/spec.md

# Eliminated
# Eliminated: <source path>:<name> — removed per ADR 0003 (target uses single DB engine)
```

---

## Appendix C — Spec-Driven Lifecycle and Consistency

Each phase follows a spec-driven lifecycle:

```
Principles -> Specification -> Planning -> Tasks -> Execution -> Validation
```

| Step          | Artifact                            | Content                                                                          |
|---------------|-------------------------------------|----------------------------------------------------------------------------------|
| Principles    | Governance principles (container)   | Ordered governing principles                                                     |
| Specification | Phase specification                 | Behaviour, functional requirements, acceptance criteria, success criteria        |
| Planning      | Phase plan                          | Technical context, batches, risks, entry and exit gates, decision dependencies   |
| Tasks         | Phase task list                     | Checkboxed actions, parallel markers, source cross-references                    |
| Execution     | Target artifacts                    | Code, schema, pipelines, infrastructure-as-code, CI / CD                         |
| Validation    | Exit gate                           | Tests green, coverage validated, semantic verification clean                     |

### Consistency rule

When any status, decision, or phase changes, all referencing locations must be updated
atomically: decision record, decision index, requirements specification, dimension specifications,
session memory. Partial updates create contradictions that compound across sessions.

The consistency check is a machine-checkable checklist that enumerates the documents
that reference the affected status field.

---

## Appendix D — Iterative Decision Evaluation

For critical decisions, the framework can generate multiple candidate options
and refine them through structured comparison.

1. Generate three initial candidates, each optimising for a different trade-off axis
   (time-to-market, technical excellence, behavioural fidelity).
2. Review each candidate independently for fatal flaws and unaddressed constraints.
3. In each round, eliminate the weakest candidate (fewest favourable pairwise comparisons)
   and replace it with a new candidate addressing flaws identified in prior rounds.
4. Repeat with two survivors plus one new challenger. Each round has constant cost:
   exactly three candidates, three pairwise comparisons.
5. Iterate until candidates converge or diminishing returns are observed.

This is one way to generate options. Options may also come from human architects,
vendor proposals, prior-art research, or hybrid methods.
The framework requires at least two evaluated options per decision; it is agnostic
to how those options are produced.

Pattern files and runtime harnesses for this protocol are included in
`.agents/skills/adversarial-thinking/` and `.agents/skills/adversarial-self-refine/`.

---

## Appendix E — Flow Variants

The overall order of phases is itself an architecture decision.
Each project discovers its own optimal flow based on its dimensions.
The list below is illustrative — real projects frequently combine or adapt entries.

| Variant                    | Strategy                                                | Typical scenario                      | Primary risk                              |
|----------------------------|---------------------------------------------------------|---------------------------------------|-------------------------------------------|
| Entity-first               | Models / schemas -> logic -> handlers                   | Database-heavy, stable data model     | Long time to first runnable code          |
| Call-graph-first           | Entry points -> fill in dependencies                    | API-heavy systems, microservices      | Stub accumulation                         |
| Vertical slice             | End-to-end features, one at a time                      | Large team, parallel workstreams      | Cross-cutting concerns extracted too late |
| Minimal runnable first     | Smallest working system, then expand                    | Small team, layered architecture      | More upfront planning                     |
| One-dimension-per-pass     | Each pass addresses one dimension                       | Large team with specialists           | High coordination overhead                |
| Protocol-structure-driven  | Packet structures, state machines first                 | Network protocol libraries            | —                                         |
| Service-graph-driven       | Leaf services first, work inward                        | Microservice decomposition            | —                                         |
| DAG-topology-driven        | Sinks first, then transforms, then sources              | Data pipeline migrations              | —                                         |
| Contract-first             | API contracts first, implementation second              | Systems with external consumers       | —                                         |
| Message-topic-driven       | By event type or topic cluster                          | Event-driven architectures            | —                                         |
| Risk-first                 | Highest-risk components first                           | Safety-critical modernisations        | —                                         |
| Compliance-first           | Regulated boundaries first                              | Finance, health, defence              | —                                         |
| Repository-split           | One dimension per target repository                     | Monolith-to-microservices             | Cross-repository CI complexity            |

### Factors that favour each variant

| Factor                         | Favours                                              |
|--------------------------------|------------------------------------------------------|
| Small team                     | Minimal runnable first (fast feedback)               |
| Large team                     | Vertical slices or one-dimension-per-pass            |
| External API consumers         | Contract-first                                       |
| Time-to-market pressure        | Minimal runnable first                               |
| Regulatory constraints         | Entity-first or compliance-first (stability)         |
| High safety stakes             | Risk-first                                           |
| Repository topology shift      | Repository-split or service-graph-driven             |

---

## Appendix F — Traceability Link Representations

The representation of traceability links is an implementation choice,
not part of the framework normative contract.
The validator only requires programmatic parseability. Options include:

| Representation                     | Description                                                                 | Trade-offs                                           |
|------------------------------------|-----------------------------------------------------------------------------|------------------------------------------------------|
| Inline source comments             | Structured comment blocks above each target element                         | No extra files; travels with the code; clutters code |
| Sidecar index files                | JSON / YAML / TOML index mapping target paths to source + decision metadata | Target code stays clean; requires index discipline   |
| Dedicated graph database           | Nodes for source and target elements; edges for traceability links          | Rich querying; infrastructure overhead               |
| Commit-level metadata              | Traceability encoded in commit messages or Git notes                        | History-preserving; requires VCS tooling             |
| Specification-side mapping tables  | Mapping tables stored inside phase specifications                           | Human-readable; coupling to specs                    |
| Hybrid                             | Lightweight inline pointer + authoritative sidecar index                    | Best of both; duplication risk                       |

The reference project used inline comments for source links and inline references
for specification and decision links. Projects with substantial existing tooling
(Bazel, Buck2, language-server ecosystems) may prefer sidecar indexes
or graph databases.

---

## Appendix G — Source Inventory and Validator Implementation

The coverage validator needs an exact inventory of source elements with boundary information.
Several implementation strategies exist, in increasing order of rigour:

| Strategy                                    | Description                                                                   | Best for                               |
|---------------------------------------------|-------------------------------------------------------------------------------|----------------------------------------|
| Agent-built regex sweep                     | The AI agent builds language-specific regexes and enumerates elements         | Small codebases; prototypes            |
| Language server / indexer                   | Use IDE-grade indexers to enumerate symbols                                   | Languages with mature tooling          |
| AST parsing                                 | Parse each source file to a full syntax tree and extract element boundaries   | Large, heterogeneous codebases         |
| Compiler-produced symbol graphs             | Extract symbols from compiler intermediate representations                    | Compiled languages with stable IR      |
| Query over existing code-intelligence graph | Query an existing source-graph store (e.g. SCIP, stack-graphs, CodeQL)        | Projects already instrumented          |

Naive strategies (name-based grep without file scoping) produce false-positive coverage;
strict strategies (full AST with exact start and end boundaries and file-scoped matching)
produce reliable coverage. The trade-off is engineering effort versus precision.
The validator output shape is the same regardless of strategy:
covered / eliminated / unmatched, with a citation for every claim.

---

## Appendix H — Semantic Discrepancy Taxonomy

A real project will discover its own taxonomy. The pattern is that discrepancies cluster
into a small number of categories (fewer than 50 in most systems),
so a per-project catalogue pays for itself quickly.
A representative 40-category taxonomy observed in the reference project (Appendix B)
spans six domains:

| Domain                 | Example categories                                                                                        |
|------------------------|-----------------------------------------------------------------------------------------------------------|
| SQL semantics          | Missing JOIN, wrong WHERE, missing ORDER BY, wrong LIMIT / OFFSET, missing owner-scope guard, SQL dialect remnant, transaction-boundary change, parameter type divergence |
| Type system            | Language-specific truthiness, coercion rules, numeric-boundary off-by-one, null vs empty, array vs map semantics |
| Data flow              | Identifier construction mismatch, content priority inversion, field truncation, timestamp validation, encoding normalisation |
| Session / state        | Session state elimination, session fallback, config constant mapping, profile-aware queries, global-variable elimination, in-memory cache elimination |
| Return values          | Wrong shape, wrong field names, return materialisation, error envelope, HTTP header omission, JSON response structure |
| Features / behaviour   | Feature absent, hook argument mismatch, hook call-site missing, side-effect order, error-recovery model, DOM / parsing model, transactional semantics |

Each taxonomy entry is a pattern with a code, a name, a description,
a representative source / target pair, and an estimated frequency in the codebase.
The taxonomy drives two things:

- semantic verification checklists applied to each element according to its tier;
- a remediation catalogue telling the agent how to rewrite each pattern correctly.

---

## Appendix I — Integration Pipeline Contracts

Per-element verification catches per-element defects.
Defects also emerge at element boundaries: data produced in one element
does not match the shape consumed in the next.

The framework defines a small set of end-to-end integration pipelines
and verifies each as an ordered contract. Each pipeline is a chain of steps;
the contract for step *k* to step *k + 1* is the exact shape of the data at that boundary,
the invariants that must hold, and the side effects that must have completed.

Representative pipelines (from the reference project — see Appendix B):

| Pipeline              | Steps                                                                                                |
|-----------------------|------------------------------------------------------------------------------------------------------|
| Feed update           | Schedule -> fetch -> parse -> sanitise -> dedup -> persist -> update counters -> fire hooks          |
| Article search        | Query build -> SQL -> pagination -> hydrate -> permission check -> response                          |
| API request           | Authenticate -> dispatch -> validate -> handle -> shape response -> sequence echo                    |
| Authentication        | Credential -> hash verify -> session create -> cookie -> hydrate state                               |
| Counter cache         | Event -> invalidate -> recompute -> publish                                                          |
| OPML roundtrip        | Import parse -> validate -> persist <-> export query -> serialise                                    |
| Digest generation     | Query due -> render -> send -> mark sent                                                             |
| Plugin lifecycle      | Discover -> load -> initialise -> register hooks -> invoke hooks                                     |

Each pipeline contract is stored as a table of boundary shapes.
Verification walks the pipeline end-to-end, checking that neighbouring steps agree.

---

## Appendix J — Data Migration and Transformations

Data migration covers all forms of persistent and streaming state —
not just relational databases. The approach depends on the data type.

### Database migration

1. **Schema mapping.** Source schema analysed dimension-by-dimension;
   target models generated and reviewed.
2. **Transformation rules.** When schemas differ, transformations are documented
   as decisions with rollback plans.
3. **Subset migration** for development and testing. Seed data per entity cluster,
   foreign-key-ordered insertion, personally-identifiable-information anonymisation.
4. **Verification.** Post-migration row counts, foreign-key integrity, spot-check queries.

### Other data types

| Data type                    | Considerations                                                                              |
|------------------------------|---------------------------------------------------------------------------------------------|
| Message schemas              | Schema versioning, consumer / producer compatibility, dead-letter handling                  |
| ETL pipelines / stored procs | Topology preservation, checkpoint / restart, idempotency, backfill                          |
| Data warehouse / OLAP cubes  | Materialised-view recreation, aggregation equivalence, historical backfill                  |
| File-based state             | Format conversion, directory structure, permission model                                    |
| Search indexes               | Index schema, re-indexing strategy, relevance-tuning validation                             |
| Object storage               | Key namespace, metadata preservation, access-policy translation                             |

Each data-migration type is documented as a decision with transformation rules,
a rollback plan, and verification criteria.

---

## Appendix K — Multi-Session Continuity

Complex migrations span many working sessions.
Continuity is maintained through three mechanisms:

1. **Session memory.** Each session ends with a structured handoff file capturing
   what was completed, what remains, decisions made, and blockers discovered.
2. **Feedback persistence.** Corrections from reviewers become persistent rules
   that guide all future sessions.
3. **Specifications as source of truth.** Specifications, decisions, and governing principles
   are durable artifacts. Session memories are ephemeral context.
   When conflict exists, specifications win.

Pattern files and runtime harnesses for multi-session continuity are included in
`.agents/skills/continuation-and-handoff/`.

---

## Appendix L — Skill Library

The framework is implemented on top of a library of reusable skills.
Copies are maintained in `.agents/skills/` within this project for self-containment.

| Skill                          | Purpose                                                                                                         |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `requirements-extractor`       | Two-phase (bottom-up Chain-of-Knowledge -> top-down intent) Mission / Goals / Premises / Constraints derivation |
| `deep-research-t1`             | Tier-1 deep research pipeline for grounding decisions in authoritative sources                                  |
| `knowledge-management`         | Chain-of-Knowledge saturation across a large corpus                                                             |
| `document-ingestion`           | Ingestion of transcripts, video frames, spreadsheets into structured knowledge                                  |
| `adversarial-thinking`         | Multi-candidate divergent design with pairwise comparison                                                       |
| `adversarial-self-refine`      | Independent reviewer / author loop for iterative output refinement                                              |
| `continuation-and-handoff`     | Multi-session continuity and checkpoint protocols                                                               |
| `selecting-pe-methods`         | Selection of prompt-engineering method per task archetype                                                       |

Skills are consumed by invoking them through the agent skill loader;
each skill is self-describing and includes termination conditions and anti-patterns.
