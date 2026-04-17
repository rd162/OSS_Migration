# AI-Assisted Software Migration Architecture

**A Dimension-Driven, Traceability-First Framework for Migrating Software Systems Across Technology Stacks**

---

## 1. Abstract

This document describes a architecture for large-scale, AI-assisted software migration.
It was derived empirically from a complete PHP-to-Python migration of a non-trivial web application
(~18,600 LOC, 138 source files, 35 database tables, 24 plugin hooks, 19 working sessions).
The framework is technology-agnostic: the same pipeline applies to language migrations,
framework shifts, monolith-to-microservices decompositions, data pipeline rewrites,
and protocol library ports.

The central contribution is a three-part mechanism — **Traceability**, **Coverage Validation**,
and **Blind-Zone Detection** — that turns AI-assisted migration from a probabilistic,
best-effort activity into an auditable, measurable process.
Without this mechanism, AI-assisted migration reliably covers only 20–40% of a codebase
regardless of model context window size.

---

## 2. Pipeline Overview

The framework is a linear pipeline of five stages executed once at project inception,
followed by a per-phase execution loop that repeats until the migration is complete.

```
  ┌───────────────────────────────────────────────────────────────────┐
  │                      INCEPTION (once per project)                 │
  │                                                                   │
  │   Stage 1. Deep Research & Knowledge Extraction                   │
  │       ↓                                                           │
  │   Stage 2. Architecture Documentation (per dimension)             │
  │       ↓                                                           │
  │   Stage 3. Architecture Decisions (ADRs, P0 → P1 → P2)            │
  │       ↓                                                           │
  │   Stage 4. Phase Breakdown (specs + plans + task lists)           │
  └───────────────────────────────────────────────────────────────────┘
                                    ↓
  ┌───────────────────────────────────────────────────────────────────┐
  │          Stage 5. PER-PHASE EXECUTION LOOP (one phase per session)│
  │                                                                   │
  │     5.1  Read phase spec + plan + tasks                           │
  │     5.2  Implement batch of target code with traceability links   │
  │     5.3  Mid-phase COVERAGE CHECK (blind-zone detection)  ← core  │
  │     5.4  Resolve blind zones (may restructure 5.2 output)         │
  │     5.5  Mid-phase SEMANTIC CHECK (behavioral parity)             │
  │     5.6  Run build / lint / tests                                 │
  │     5.7  Phase exit gate: coverage + tests + decision records     │
  │     5.8  Session handoff (next phase begins in a new session)     │
  └───────────────────────────────────────────────────────────────────┘
```

**Critical sequencing rule.** Coverage and semantic checks are executed *within* each phase loop,
not at the end of the project. Deferring verification to the end of the project
is the single most damaging anti-pattern in AI-assisted migration:
defects compound across sessions, traceability comments drift from the code they describe,
and the signal-to-noise ratio of late-stage verification falls below the threshold
at which errors can be corrected efficiently.

The reference project violated this rule. Coverage verification was added only after all phases
were implemented; as a result, multiple defect classes (false-positive traceability,
semantic divergence, missing features discovered only via SME review) required
retroactive rework across every phase. The rule is stated explicitly here
so that future applications of the framework avoid the same cost.

---

## 3. Stage 1 — Deep Research and Knowledge Extraction

**Goal.** Produce a complete, evidence-based model of the source system
before any target-side decision is made.

**Inputs.** Source repository (read-only), domain documentation, SME interviews,
video walkthroughs, production configuration samples.

**Outputs.**

- Full source inventory (every file annotated with language, role, and dependencies)
- A set of **dimension specifications**, one per structural axis discovered in the source
- A technology-research dossier describing idioms of the source and candidate target stacks

**Dimensions are discovered, not prescribed.** Every software system exposes
its own set of structural axes. The framework does not fix a list;
instead, each axis that materially affects migration order is captured as a separate spec.
See Appendix A for the set of dimensions discovered in the reference project
and a broader catalogue of dimensions observed in other system types.

**Why deep research comes first.** The target architecture cannot be chosen rationally
without quantitative evidence of what the source actually contains:
dependency depth, complexity hotspots, coupling clusters, implicit contracts,
deprecated surfaces, security posture. Skipping or compressing this stage
leads to ADRs made under uncertainty and phases that must be replanned mid-execution.

---

## 4. Stage 2 — Architecture Documentation

**Goal.** Characterize the source system as a durable reference
that all subsequent stages (decisions, phase plans, verification) can cite without re-reading the source.

The output of this stage is a stable, read-only set of documents organized by dimension.
Each document is self-contained and cross-links to the source by relative path and line number
rather than duplicating source content.

The reference project produced fifteen such documents (project charter plus fourteen
per-dimension architecture specs); the exact set is project-specific.
See Appendix B for the reference inventory.

A **project charter** sits above the per-dimension specs and captures:

- Mission, goals, governing principles
- Premises (assumptions that must hold)
- Hard and soft constraints
- A requirements traceability matrix linking every requirement
  to the spec and decision records where it is satisfied

---

## 5. Stage 3 — Architecture Decisions

**Goal.** Record every non-trivial migration choice with full trade-off analysis
before any target code is written.

Each decision is captured as a formal record (the reference project used MADR 4.0 format)
with the following shape: context, considered options, trade-off analysis,
decision, consequences, confirmation.

**Priority classes.**

| Priority | Scope | Must be accepted before |
|----------|-------|-------------------------|
| P0       | Blocks all work (migration flow, target language/framework, database engine) | Stage 4 begins |
| P1       | Blocks specific phases (ORM, auth, background workers, etc.)                 | The phase it blocks   |
| P2       | Deferrable, no blocking dependencies (logging, i18n, plugin details)         | Before the final release |

**How decisions are generated.** Each decision begins with at least two evaluated options.
Options can be sourced from human architects, vendor proposals, prior art research,
or iterative LLM-driven candidate generation (see Appendix D for the iterative variant
used in the reference project).

**Trade-off transparency.** Every decision explicitly documents the trade-offs it accepts.
This is where business value is captured and where decisions become reviewable
by non-specialist stakeholders.

**Consistency constraint.** When a decision's status changes (proposed → accepted, deprecated, superseded),
every document that references that decision must be updated atomically.
Partial status updates are a leading source of multi-session contradictions
and must be treated as a build-breaking defect.

---

## 6. Stage 4 — Phase Breakdown

**Goal.** Convert the accepted decisions and dimension specs into a dependency-ordered
sequence of executable phases, each small enough to fit in a single working session.

**Artifacts per phase.** The reference project used three files per phase,
aligned with the Spec-Driven Development convention
(see Appendix C for the spec-kit workflow used):

- `spec.md` — user stories, functional requirements, acceptance criteria, success criteria
- `plan.md` — technical context, constitution-check gate, dependency-ordered batches, risk assessment
- `tasks.md` — checkboxed steps with parallel markers and source file cross-references

**Flow variant.** The overall order of phases is itself an architecture decision,
because the dimension chosen as primary driver determines the entire project structure.
See Appendix E for a catalogue of flow variants and the factors
that favour one variant over another.

**Exit gates.** Every phase has an explicit exit gate listing the concrete conditions
that must hold before the next phase can begin: tests passing, coverage thresholds,
traceability verification clean, any required ADRs accepted.
The gate is a machine-checkable checklist, not a narrative.

---

## 7. Stage 5 — Per-Phase Execution Loop

Each phase is executed in a fresh working session so that context is clean
and the session handoff artifact is the only carrier of cross-phase state.

**The mid-phase verification checkpoint is the decisive innovation** of this framework.
After an initial batch of target code is produced, the pipeline does not proceed to the next batch
until coverage and semantic checks are clean. This catches defects while context is hot,
not weeks later during integration.

```
  For each batch in the phase:
    (a) Implement target code with traceability links to source origins
    (b) Run coverage validator  →  produces blind-zone report
    (c) Resolve blind zones      →  may restructure (a) output
    (d) Run semantic checks on Tier 1 functions
    (e) Build / lint / unit / integration tests
    (f) If any step fails → loop back to (a) with a narrower scope
    (g) Otherwise → next batch

  Phase exit:
    - Coverage validator reports zero unmatched in-scope elements
    - All tests green
    - All referenced ADRs in 'accepted' status
    - Session handoff note written for the next phase
```

The three core mechanisms that make this loop auditable — Traceability,
Coverage Validation, and Blind-Zone Detection — are described in the next section.

---

## 8. Core Mechanism: Traceability, Coverage, and Blind Zones

### 8.1 Why AI models miss code

Even with large-context models capable of loading an entire repository,
code elements are systematically missed during migration:

- **Attention dilution.** Long files (2000+ lines) cause attention to concentrate on prominent
  functions while skipping less prominent ones.
- **False coverage.** File-level traceability claims coverage of an entire file
  while actually covering only a few functions.
- **Name collision.** Functions with common names are "covered" by false matches
  from unrelated files (global-name fallback in naive validators).
- **Cross-session drift.** Work done in session *N* may conflict with assumptions from session *N − k*.

The reference project measured this directly. Initial reported coverage was 100%;
strict tree-sitter-based re-analysis with file-specific matching showed true coverage of **41.2%**
(320 of 554 functions were false-positive matches).
Only after iterative blind-zone resolution did coverage reach 100%.

### 8.2 Traceability is detection, not transpilation

A common misconception is that a traceability-driven pipeline works like a transpiler —
feeding source code line-by-line into an AI model and receiving target code back.
**It does not.** The pipeline works for any migration style,
including full architectural redesigns (monolith → microservices, server-rendered → SPA,
SQL triggers → stream processing).

The key insight:
**traceability is used to detect what was missed, not to constrain how migration is done.**
The AI model is free to redesign, restructure, and re-architect the target system
in whatever way the accepted ADRs prescribe. Traceability only tracks
which source elements have been accounted for.

```
                    SOURCE CODEBASE
                    (all elements inventoried by AST parser)
                           │
                    ┌──────▼───────┐
                    │  COVERAGE    │
                    │  VALIDATOR   │
                    │              │
                    │  compares    │
                    │  source      │
                    │  inventory   │
                    │  against     │
                    │  target      │
                    │  traceability│
                    └──────┬───────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
     COVERED                         BLIND ZONES
     (accounted for)                 (not yet accounted for)
          │                                 │
          │                           ┌─────▼─────┐
          │                           │ AI MODEL  │
          │                           │  reads    │
          │                           │  source,  │
          │                           │  reasons  │
          │                           │  about    │
          │                           │  target   │
          │                           │  placement│
          │                           └─────┬─────┘
          │                                 │
          │                           generate OR update
          │                           target code +
          │                           add traceability link
          │                                 │
          └────────────────┬────────────────┘
                           │
                    ┌──────▼───────┐
                    │ RE-VALIDATE  │
                    │ coverage     │
                    │ monotonically│
                    │ increases    │
                    │ until 100%   │
                    └──────────────┘
```

**Example.** Suppose the source is a monolith and the target is microservices.
The validator detects that a source function has not been accounted for.
It does *not* instruct the AI to translate those lines.
Instead the AI:
(1) reads the source function to understand its business role;
(2) locates the correct target service per the accepted architecture;
(3) checks which of the service's responsibilities are already present;
(4) implements the missing responsibility in the target's idiom;
(5) adds a traceability link so the validator treats the source element as accounted for.

This is why the mechanism applies equally to:

- **Near-identical translations** (Java 8 → Java 17): most functions map 1:1.
- **Framework migrations** (PHP monolith → Python Flask): structure changes, functions mostly map.
- **Full redesigns** (monolith → microservices): source functions scatter across services;
  traceability tracks which ones have been accounted for.
- **Technology shifts** (SQL triggers → Spark): source triggers become streaming jobs;
  traceability ensures no trigger is forgotten.

### 8.3 Traceability link shape

Every meaningful target element (function, class, method, model, route, constant)
carries a link that states its relationship to source. Link types,
in order of specificity:

| Type          | Meaning |
|---------------|---------|
| Direct        | Source function maps to target function |
| Method-level  | `Class::method` maps to target method   |
| File-level    | Target module aggregates one source file |
| Multi-source  | Target function combines logic from multiple source files |
| Schema-level  | Target model derived from a schema definition |
| Inferred      | Target code adapted from source patterns; no direct equivalent |
| New           | Genuinely new code; no source equivalent |
| Eliminated    | Source intentionally not ported (dead, deprecated, or superseded) |

Each traceability link is programmatically parseable so the coverage validator
can build the source→target correspondence automatically.

### 8.4 The coverage validator

A source-agnostic validator performs four steps:

1. **Source inventory.** Parse every source file with a proper AST (e.g. tree-sitter)
   to capture exact start *and* end lines for every function/method/class/table.
2. **Target scanning.** Parse every target file for traceability links.
3. **Strict matching.** A source element is "covered" only if the target's
   traceability link references the *same source file*. There is no global-name fallback;
   a Python function named `edit` with a link to `pref/users.php` does not cover
   a PHP function `edit` in `pref/labels.php`.
4. **Dimension cross-check.** Verify that dependency edges, entity references,
   and integration points from the dimension specs are present in the target.

Each source element falls into exactly one of three categories:
**Covered**, **Eliminated**, or **Unmatched**.
Unmatched elements are the blind zones that must be resolved before the phase can exit.

### 8.5 Semantic (behavioural) verification

Structural coverage proves that every source element has been considered.
It does not prove that the target behaves correctly.
A function can be structurally covered but semantically wrong.

In the reference project, SME review of sampled function pairs
revealed that **all reviewed functions had at least one behavioural discrepancy**
despite 100% structural coverage. The root causes fall into a small, enumerable taxonomy:
in the reference project, 40 categories spanning SQL semantics, type coercion,
data flow, session state, return shape, and feature completeness. See Appendix F for the full list.

Semantic verification compares source/target function pairs according to a depth tier:

| Tier | Criteria | Depth |
|------|----------|-------|
| 1    | Complex logic, many branches, cross-cutting callers | Line-by-line with raw-source quoting |
| 2    | Moderate complexity                                 | Block-level with spot checks |
| 3    | Simple wrappers / getters / setters                 | Signature and return type |
| 4    | Data models / schemas                               | Column-by-column |

**Mandatory audit rule.** Tier 1 reviews must quote raw source lines from both files.
Summarized reviews without line-number quotes systematically miss structural defects
such as misindented loop bodies. The reference project encountered exactly this failure mode
and made line-number quoting a non-negotiable rule for Tier 1.

### 8.6 Platform knowledge catalogue

During migration, the team accumulates a catalogue of patterns where source and target
platforms diverge despite superficially similar code. Each entry documents:
the source pattern, how the target differs, and estimated frequency.
The catalogue is the reference used during semantic verification
and prevents the same class of error from recurring across phases.

The reference project catalogued 40 such patterns affecting 600+ call sites.

### 8.7 Integration-pipeline verification

Per-function verification catches per-function defects.
It does not catch defects that emerge when data flows through multiple functions
with incompatible assumptions — for example, an identifier constructed one way in `f()`
but looked up a different way in `g()`.

The framework defines a small number of end-to-end integration pipelines
(the reference project used eight) and verifies each as an ordered contract:
boundary-by-boundary, the data shape produced at step *k* must match
the shape consumed at step *k + 1*. This catches the class of defects
missed by per-function audits.

---

## 9. Functionality Adjustment

**Goal.** Align migration scope with business needs *before and during* implementation.

The pipeline provides three natural integration points for product and SME input:

1. **Feature scope review** (during Stage 1). Product confirms which features are kept as-is,
   enhanced, deprecated, or eliminated. Output: a feature scope matrix referenced by all later stages.
2. **SME knowledge ingestion** (any time). Recordings, screenshots, spreadsheets, and walkthroughs
   of the working source application are ingested, transcribed, and used to generate
   end-to-end test scenarios and to discover features missed by pure code analysis.
3. **Sampled SME verification** (during each phase). SMEs review randomly sampled
   source/target function pairs. This catches divergences that no automated check can detect
   (domain-specific behaviour, undocumented business rules, cosmetic expectations).

The reference project used this mechanism to discover features
(drag-drop category assignment, keyboard shortcuts, multi-rule filter builder)
that were not visible from source code analysis alone.

---

## 10. Hybrid Deployment and Coexistence

For large systems a big-bang cutover is prohibitively risky;
source and target must coexist for some period.
The coexistence architecture is itself an ADR and varies by system type:

- **Web applications** — shared database, API gateway for traffic routing, compatibility shim
- **Microservices** — service-by-service migration, inter-service contracts preserved at each step
- **Protocol libraries** — linked side-by-side, conformance tests against both implementations
- **Data pipelines** — parallel runs on the same data subset, output equivalence check before cutover
- **Event-driven systems** — dual consumers during transition, producer-by-producer switchover

Every shim or dual-path component is tracked as a removal item with a documented sunset.

---

## 11. Applicability Across System Types

The pipeline is technology-agnostic. What changes between applications is
the set of dimensions discovered in Stage 1, the decisions taken in Stage 3,
and the flow variant chosen in Stage 4.
Appendix A catalogues dimensions observed across system types;
Appendix E catalogues flow variants.

The three core mechanisms (traceability, coverage validation, blind-zone detection)
apply unchanged to: language migrations, framework shifts, monolith decompositions,
CLI ports, desktop-to-web moves, network protocol library ports, data pipeline rewrites,
stored-procedure extractions, and embedded/IoT codebase modernizations.

---

## 12. Benefits

- **Explicit trade-offs.** Every non-trivial choice is recorded as a decision with analysis.
- **Measurable completeness.** Coverage is a programmatic metric checked at every phase gate,
  not a claim.
- **Early error detection.** Errors are caught within the same session they are introduced,
  not during final integration.
- **Test generation for legacy systems.** The target ends up with better test coverage
  than the source ever had, turning migration from a risk event into a quality event.
- **Behavioural correctness.** The platform knowledge catalogue prevents systematic
  translation errors from recurring.
- **Stakeholder-friendly decision records.** Trade-off analysis tables can be reviewed
  by non-specialists.

---

# Appendices

All appendices are illustrative. Each real project will instantiate its own versions
of the tables and examples below; nothing here is prescriptive.

---

## Appendix A — Dimension Catalogue

Dimensions commonly discovered during Stage 1.
Every real project should infer its own set.

### Structural dimensions (common to most systems)

| Dimension | What it captures | Why it matters |
|-----------|------------------|----------------|
| Call graph                 | Which functions call which others                 | Dependency order for migration |
| Data model / entity graph  | Tables, schemas, relationships, clusters          | What models must exist before business logic |
| Module dependency graph    | Import/include chains between files/packages      | Build order and circular-dependency risk |
| Service dependency graph   | Which services call which others                  | Distributed-system migration order |
| Event/message flow graph   | Producers, topics, subscribers                    | Event-driven migration order |
| Infrastructure dependency  | Services ↔ infrastructure (DB, cache, queue)      | Cloud / platform migration |

### Domain-specific dimensions (examples)

| Dimension | Example system types |
|-----------|---------------------|
| Frontend/backend coupling         | Web apps with server-rendered HTML or SPAs |
| Plugin/extension system           | Applications with hook points and extension APIs |
| Protocol state machine            | Network-protocol implementations |
| Data pipeline topology            | ETL, stream processors, trigger chains |
| Configuration surface             | Systems with extensive config constants / feature flags |
| Security surface                  | Auth flows, encryption, session management |
| Concurrency model                 | Multi-threaded, async, event-driven |
| API contract surface              | Systems with external consumers |
| Regulatory compliance boundaries  | Regulated industries |
| Hardware abstraction layer        | Embedded / IoT |

### Applicability matrix

| System type                   | Typical primary dimension   | Typical secondary dimensions |
|-------------------------------|-----------------------------|------------------------------|
| Web application (MVC)         | Entity graph                | Call graph, frontend coupling |
| Server-rendered app           | Frontend/backend coupling   | Entity graph, template system |
| Desktop application           | UI event model              | Call graph, persistence |
| CLI tool                      | Call graph                  | Argument parsing, I/O model |
| Data processing pipeline      | Pipeline topology           | Data model, checkpoint semantics |
| Network protocol library      | Protocol state machine      | Timer semantics, packet encoding |
| Microservices                 | Service dependency graph    | API contracts, message topics |
| Stored-procedure system       | Data pipeline topology      | Entity graph, transaction boundaries |
| Event-driven architecture     | Message topics              | Service graph, event schema |
| Embedded / IoT                | Hardware abstraction        | Call graph, memory model |

---

## Appendix B — Reference Project Statistics

Reference project: full PHP-to-Python migration of a medium-sized self-hosted web application.

| Metric | Value |
|--------|-------|
| Source LOC                              | ~18,600 PHP |
| Source files                            | 138 |
| Database tables                         | 35 (31 active, 4 deprecated/eliminated) |
| Plugin hooks                            | 24 |
| API endpoints                           | 17 REST, 40+ RPC |
| Working sessions to complete            | 19 |
| Architecture specs generated            | 14 (plus project charter) |
| Phase specs generated                   | 6 |
| Architecture decisions recorded         | 19 |
| Tests at completion                     | 1,474 (unit + integration + E2E) |
| Platform-knowledge patterns catalogued  | 40 categories, 600+ call sites |
| Integration pipelines verified          | 8 |
| Final structural coverage               | 100% (458 / 458 in-scope functions) |
| Eliminated source elements              | 27+ |
| Security improvements                   | SHA1 → argon2id, mcrypt → Fernet, prepared statements, CSRF, security headers |

### Legacy elimination examples

| Item | Action |
|------|--------|
| MySQL / DB-type conditional branches              | Eliminated — PostgreSQL-only per ADR |
| 4 deprecated tables (themes, labels v1, filters v1, scheduled_updates) | Not ported — absent from schema v124 |
| SHA1 dual-hash verification                       | Gradual upgrade to argon2id on login; SHA1 sunset documented |
| Sphinx full-text search dependency                | Eliminated — replaced by PostgreSQL tsvector |
| Legacy JavaScript compatibility shim              | Eliminated — replaced by vanilla-JS SPA |
| Dojo / Prototype legacy JS libraries              | Replaced with zero-dependency vanilla JS |
| mcrypt encryption (deprecated in source platform) | Replaced with Fernet symmetric encryption |

### Artifact shapes (illustrative)

**Architecture decision record** (MADR 4.0 format):

```markdown
# 0002 — Select Python Web Framework

## Considered Options
1. Flask — closest match to source handler dispatch; native session/CSRF
2. FastAPI — modern async; no built-in sessions; CSRF requires JS changes
3. Django — full-featured but over-engineered for this codebase

## Decision: Flask
Rationale: reduces translation distance; zero frontend changes needed.
```

**Traceability link examples** (Python):

```python
# Direct match
# Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
def authenticate_user(login: str, password: str) -> Optional[User]: ...

# Multi-source
# Source: ttrss/classes/feeds.php:Feeds::view (lines 45-120)
#       + ttrss/include/functions2.php:queryFeedHeadlines (lines 200-450)
def view_feed(feed_id: int, view_mode: str) -> dict: ...

# Inferred
# Inferred from: ttrss/include/sessions.php (session validation pattern)
# Adapted for Flask-Login; no direct PHP equivalent.
def validate_session(session_id: str) -> bool: ...

# New (no source equivalent)
# New: no source equivalent — Alembic migration infrastructure.
def run_migrations() -> None: ...

# Eliminated (documented non-port)
# Eliminated: ttrss/classes/db/mysql.php — PostgreSQL-only per ADR-0003.
```

---

## Appendix C — Spec-Driven Development Workflow

Each phase follows a spec-driven lifecycle:

```
Principles → Specification → Planning → Tasks → Execution → Validation
```

| Stage | Artifact | Contents |
|-------|----------|----------|
| Principles     | `constitution.md` / charter | Ordered governing principles |
| Specification  | `spec.md`                   | User stories, functional requirements, acceptance criteria, success criteria |
| Planning       | `plan.md`                   | Technical context, dependency-ordered batches, risk assessment, constitution-check gate |
| Tasks          | `tasks.md`                  | Checkboxed steps, parallel markers, source file cross-references |
| Execution      | (code)                      | Implementation with traceability and continuous testing |
| Validation     | exit-gate checklist         | Tests green, coverage validated, semantic verification passed |

### Consistency rule

When any status, decision, or phase changes, all referencing locations must be updated
atomically: decision record, decision index, charter, dimension specs, session memory.
Partial updates create contradictions that compound across sessions.

---

## Appendix D — Iterative Decision Evaluation

For critical decisions, the framework can generate multiple solution candidates
and refine them through structured comparison.

1. Generate three initial candidates, each optimising for a different trade-off axis
   (time-to-market, technical excellence, behavioural fidelity).
2. Review each candidate independently, looking for fatal flaws and unaddressed constraints.
3. In each round, eliminate the weakest candidate (fewest favourable pairwise comparisons)
   and replace it with a new candidate addressing flaws identified in prior rounds.
4. Repeat with two survivors plus one new challenger. Each round is constant cost:
   exactly three candidates and three pairwise comparisons.
5. Iterate until candidates converge or diminishing returns are observed.

This is one way to generate decision variants. Variants can also come from human architects,
vendor proposals, or prior-art research. The framework is agnostic to how variants are generated —
only that each decision contains at least two evaluated options with trade-off analysis.

---

## Appendix E — Flow Variants

The overall order of phases is itself an architecture decision.
Each project discovers its own optimal flow based on its dimensions.
The table below is illustrative — real projects often combine or adapt entries.

| Variant | Strategy | Typical scenario | Primary risk |
|---------|----------|------------------|--------------|
| Entity-First             | Models/schemas → logic → handlers        | Database-heavy, stable data model     | Long time to first runnable code |
| Call-Graph-First         | Entry points → fill in dependencies      | API-heavy systems, microservices      | Stub accumulation |
| Vertical Slice           | End-to-end features, one at a time       | Large team, parallel workstreams      | Cross-cutting concerns extracted too late |
| Minimal Runnable First   | Smallest working app, then expand        | Small team, layered architecture      | More upfront planning |
| One-Dimension-Per-Pass   | Each pass addresses one dimension        | Large team with specialists           | High coordination overhead |
| Protocol-Structure-Driven| Packet structures, state machines first  | Network protocol libraries            | — |
| Service-Graph-Driven     | Leaf services first, work inward         | Microservice decomposition            | — |
| DAG-Topology-Driven      | Sinks first, then transforms, then sources | Data pipeline migrations            | — |
| Contract-First           | API contracts first, implementation second | Systems with external consumers     | — |
| Message-Topic-Driven     | By event type / topic cluster            | Event-driven architectures            | — |

### Factors that favour each variant

| Factor | Favours |
|--------|---------|
| Small team                      | Minimal-runnable-first (fast feedback) |
| Large team                      | Vertical slices or one-dimension-per-pass |
| External API consumers          | Contract-first |
| Time-to-market pressure         | Minimal-runnable-first |
| Regulatory constraints          | Entity-first (data-model stability) |

---

## Appendix F — Semantic Discrepancy Taxonomy

The reference project catalogued 40 categories of behavioural discrepancy
observed during semantic verification. They fall into six domains:

| Domain | Example categories |
|--------|--------------------|
| SQL semantics          | Missing JOIN, wrong WHERE, missing ORDER BY, wrong LIMIT/OFFSET, missing owner-scope guard |
| Type system            | Language-specific truthiness, coercion rules, null vs empty |
| Data flow              | Identifier construction mismatch, field truncation, timestamp validation |
| Session / state        | Missing session keys, wrong cookie attributes, wrong state machine |
| Return values          | Wrong shape, wrong field names, wrong status semantics |
| Features / behaviour   | Missing hook call, missing cache invalidation, missing branch, missing pagination |

Each project will discover its own taxonomy. The pattern is that discrepancies
cluster into a small number of categories (fewer than 50 in most systems),
so a per-project catalogue pays for itself quickly.

---

## Appendix G — Integration Pipeline Contracts

Per-function verification is insufficient because defects emerge at function boundaries.
The framework defines a small set of end-to-end integration pipelines
and verifies each as an ordered contract: data produced at step *k*
must match data consumed at step *k + 1*.

The reference project used eight pipelines:

| Pipeline | Steps |
|----------|-------|
| Feed update          | Schedule → fetch → parse → sanitize → dedup → persist → counters → hooks |
| Article search       | Query build → SQL → pagination → hydrate → permissions → response |
| API request          | Auth → dispatch → validate → handle → shape response → seq echo |
| Authentication       | Credential → hash verify → session create → cookie → state hydrate |
| Counter cache        | Event → invalidate → recompute → publish |
| OPML roundtrip       | Import parse → validate → persist ↔ export query → serialize |
| Digest generation    | Query due → render → send → mark sent |
| Plugin lifecycle     | Discover → load → init → hook register → hook invoke |

Each pipeline's contract is a table of boundary shapes.
Verification walks the pipeline end-to-end, checking that neighbouring steps agree.

---

## Appendix H — Multi-Session Continuity

Complex migrations span many working sessions.
Continuity is maintained through three mechanisms:

1. **Session memory.** Each session ends with a structured handoff file capturing
   what was completed, what remains, decisions made, and blockers discovered.
2. **Feedback persistence.** Corrections from reviewers become persistent rules
   that guide all future sessions.
3. **Specs as source of truth.** Specs, decisions, and governing principles
   are durable artifacts. Session memories are ephemeral context.
   When conflict exists, specs win.

---

## Appendix I — Data Migration and Transformations

Data migration covers all forms of persistent and streaming state —
not just relational databases. The approach depends on the data type.

### Database migration

1. **Schema mapping.** Source schema analysed dimension-by-dimension;
   target models generated and reviewed.
2. **Transformation rules.** When schemas differ, transformations are documented
   as decisions with rollback plans.
3. **Subset migration** (dev / test). Seed data per entity cluster,
   FK-ordered insertion, PII anonymization.
4. **Verification.** Post-migration row counts, FK integrity, spot-check queries.

### Other data types

| Data type | Considerations |
|-----------|----------------|
| Message schemas              | Schema versioning, consumer/producer compatibility, dead-letter handling |
| ETL pipelines / stored procs | Topology preservation, checkpoint/restart, idempotency, backfill |
| Data warehouse / OLAP cubes  | Materialized-view recreation, aggregation equivalence, historical backfill |
| File-based state             | Format conversion, directory structure, permission model |
| Search indexes               | Index schema, re-indexing, relevance tuning |
| Object storage               | Key namespace, metadata preservation, access policy |

Each data-migration type is documented as a decision with transformation rules,
rollback plan, and verification criteria.

---

## Appendix J — The Mid-Phase Verification Anti-Pattern (Lessons Learned)

The reference project deferred coverage and semantic verification
to the end of the project rather than running them mid-phase.
The consequences were:

- False-positive 100% coverage (grep-based validator missed 320 functions)
- Retroactive tree-sitter-based re-audit required
- SME review found all sampled functions had behavioural discrepancies
  despite 100% structural coverage
- 40-category discrepancy taxonomy had to be derived after the fact
  rather than being available during implementation
- UI functional defects (filter rules silently losing data due to a misindented loop body)
  reached end-user testing

Every one of these costs would have been avoided by running the verification loop
at the mid-phase checkpoint rather than at the end of the project.

**This is the single most important operational lesson of the framework:**
verification belongs inside the per-phase loop, not after it.
The pipeline diagrammed in Section 2 reflects this lesson;
the reference project arrived at it through experience rather than design.
