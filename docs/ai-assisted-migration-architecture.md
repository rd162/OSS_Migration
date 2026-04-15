# AI-Assisted Software Migration Architecture

**A Spec-Driven, Multi-Session Framework for Migrating Arbitrary Software Systems**

---

## 1. Executive Summary

This document formalizes a **generic, repeatable methodology** for conducting AI-assisted software migrations across arbitrary technology stacks and application types. The approach was developed and battle-tested during a complete PHP-to-Python migration of a non-trivial web application (18,600 LOC, 35 database tables, 24 plugin hooks, REST API, background workers), completed across 19 AI-assisted sessions.

The methodology is **stack-agnostic** and **dimension-driven**: it works by decomposing any source system along discoverable analysis dimensions, making trade-off decisions via Architecture Decision Records (ADRs), and executing the migration in spec-gated phases with continuous coverage and semantic verification.

### Key Innovation

Unlike manual migration or simple AI code translation, this framework treats migration as a **knowledge extraction + decision + verification** problem:

1. **Extract** multi-dimensional structural knowledge from source code
2. **Decide** migration flow order using dimension analysis + trade-off evaluation
3. **Execute** via spec-driven phases with adversarial quality gates
4. **Verify** structural coverage AND semantic equivalence continuously

---

## 2. Process Flow Overview

```
                    +-------------------+
                    |   SOURCE SYSTEM   |
                    | (any tech stack)  |
                    +---------+---------+
                              |
                    +---------v---------+
                    |  PHASE 0: DEEP    |
                    |  KNOWLEDGE        |
                    |  EXTRACTION       |
                    |  + Web Research   |
                    +---------+---------+
                              |
                    +---------v---------+
                    |  PHASE 1: SPEC    |
                    |  GENERATION       |
                    |  (architecture,   |
                    |   dimensions,     |
                    |   source index)   |
                    +---------+---------+
                              |
                    +---------v---------+
                    |  PHASE 2: ADR     |
                    |  DECISIONS        |
                    |  (adversarial     |
                    |   evaluation)     |
                    +---------+---------+
                              |
                    +---------v---------+
                    |  PHASE 3: PLAN    |
                    |  + ROADMAP        |
                    |  (dimension-      |
                    |   ordered phases) |
                    +---------+---------+
                              |
              +---------------+----------------+
              |               |                |
    +---------v----+  +-------v------+  +------v-------+
    | PHASE 4:     |  | CONTINUOUS:  |  | CONTINUOUS:  |
    | EXECUTE      |  | COVERAGE     |  | SEMANTIC     |
    | (per phase,  |  | VALIDATION   |  | VERIFICATION |
    | spec-gated)  |  | (structural) |  | (behavioral) |
    +---------+----+  +-------+------+  +------+-------+
              |               |                |
              +---------------+----------------+
                              |
                    +---------v---------+
                    |  PHASE 5: FINAL   |
                    |  VERIFICATION     |
                    |  + DEPLOYMENT     |
                    +-------------------+
```

---

## 3. Analysis Dimensions

Every software system can be decomposed along multiple structural dimensions. The choice and priority of dimensions varies by application type. The AI agent discovers which dimensions are most relevant during Phase 0.

### 3.1 Universal Dimensions (present in most systems)

| Dimension | What It Captures | Migration Impact |
|-----------|-----------------|-----------------|
| **Call Graph** | Which functions/methods call which others | Determines compilation/migration order: dependencies must exist before dependents |
| **Data Model / Entity Graph** | Database tables, schemas, FK relationships, entity clusters | Determines what models/types must exist before business logic |
| **Module Dependency Graph** | Import/include chains between files/packages | Determines build order and circular dependency risks |

### 3.2 Domain-Specific Dimensions (selected per project)

| Dimension | Applicable When | Example |
|-----------|----------------|---------|
| **Frontend/Backend Coupling** | Web applications with UI layer | Server-rendered HTML vs API-driven SPA; coupling level per component |
| **Plugin/Extension System** | Applications with plugin architecture | Hook points, plugin lifecycle, extension API surface |
| **Network Protocol State Machine** | Protocol implementations (e.g., BFD, BGP) | State transitions, timer semantics, packet encoding/decoding |
| **Data Pipeline Topology** | ETL/data processing systems | DAG of transformations, source/sink connectors, checkpoint semantics |
| **Configuration Surface** | Systems with extensive config | Config constants, env vars, feature flags, profile-aware overrides |
| **Security Surface** | Applications handling auth/crypto | Auth flows, encryption schemes, session management, access control |
| **Concurrency Model** | Multi-threaded/async systems | Thread pools, event loops, message passing, lock ordering |
| **API Contract Surface** | Systems with external API consumers | Request/response schemas, versioning, backward compatibility |
| **CLI Interface** | Command-line tools | Argument parsing, subcommands, piping, exit codes |
| **Desktop UI Event Model** | Desktop applications | Widget tree, event binding, layout engine, accessibility |

### 3.3 Dimension Discovery Process

During Phase 0, the AI agent:

1. **Inventories** all source files with size, language, and purpose annotation
2. **Builds** a dependency graph (using AST parsers like tree-sitter) across all discovered dimensions
3. **Identifies communities** via graph analysis (e.g., Leiden community detection on the call graph) to find natural service boundaries
4. **Ranks dimensions** by migration impact: the dimension with the highest coupling drives the primary migration order
5. **Conducts deep web research** on source technology patterns, target technology best practices, and known migration pitfalls for the specific technology pair

---

## 4. Migration Flow Variants

The analysis dimensions enable multiple migration ordering strategies. The choice is a trade-off decision documented as an ADR.

### Variant A: Entity-First (Bottom-Up)

Models/schemas first, then data access, then business logic, then handlers.

- **Best for**: Database-heavy applications, systems where the data model is stable
- **Risk**: Long time to first runnable code
- **Example trade-off**: Choosing this for a SQL-trigger-based ETL system where data model IS the application

### Variant B: Call-Graph-First (Top-Down)

Entry points and routing first, then handlers with stubs, then fill in business logic.

- **Best for**: API-heavy systems, microservices
- **Risk**: Stubs accumulate technical debt; refactoring when stubs are replaced

### Variant C: Vertical Slice (Feature-First)

Complete end-to-end slices: one feature at a time including its model, logic, API, and UI.

- **Best for**: Team-based migrations with parallel workstreams
- **Risk**: Cross-cutting concerns (auth, config, sessions) must be extracted early

### Variant D: Hybrid Walking Skeleton

Walking skeleton first (minimal runnable app), then complete foundation, then call-graph-ordered business logic, then handlers, then cross-cutting concerns.

- **Best for**: Solo developer or small team; applications with clear layered architecture
- **Trade-off**: Balances time-to-first-runnable-code against foundation quality
- **Example concrete choice**: For a PHP web app migrating to Python, Flask was chosen over FastAPI despite FastAPI being "more modern" because Flask's session/CSRF/template model more closely matched the source architecture, reducing translation distance and time to market

### Variant E: Granular Multi-Pass

Multiple fine-grained passes, each addressing one dimension exclusively.

- **Best for**: Large teams with specialists per dimension
- **Risk**: Excessive coordination overhead for small teams

### Decision Framework

The variant selection considers:

| Factor | Favors |
|--------|--------|
| Solo developer | Variant D (walking skeleton reduces risk) |
| Large team | Variant C (parallel slices) or E (specialists) |
| Stable data model | Variant A (entity-first) |
| External API consumers | Variant B (contract-first) |
| Time-to-market pressure | Variant D (runnable in days) |
| Maximum technical excellence | Variant E (thorough but slow) |

---

## 5. Decision Framework: Architecture Decision Records

Every non-trivial migration choice is documented as a formal **Architecture Decision Record** (MADR 4.0 format). Decisions are prioritized:

- **P0 (blocks all work)**: Migration flow variant, target framework/language, database engine
- **P1 (blocks specific phases)**: ORM strategy, auth mechanism, background worker architecture, serialization format
- **P2 (deferrable)**: Logging, i18n, plugin system details, monitoring

### Decision Evaluation Process

Each P0/P1 decision undergoes **adversarial evaluation**:

1. **Research phase**: Deep web research on each option's trade-offs, maturity, community support
2. **Candidate generation**: 3 divergent solution proposals with different trade-off priorities
3. **Stress testing**: Each candidate is critiqued by an isolated reviewer agent who tries to find fatal flaws
4. **Convergence check**: If all candidates converge to the same answer after critique, the decision is clear
5. **Pairwise comparison**: If divergent, Condorcet-style pairwise voting selects the winner

### Trade-off Transparency

Every ADR explicitly documents trade-offs between:

- **Time to market** vs. **technical excellence** (e.g., choosing a "less modern" framework that better matches source architecture, reducing translation distance)
- **Stability** vs. **innovation** (e.g., using a proven ORM over a newer but less battle-tested one)
- **Fidelity** vs. **improvement** (e.g., fixing known security vulnerabilities during migration vs. strict behavioral parity)

---

## 6. Spec-Driven Development Workflow

The migration follows a strict spec-driven lifecycle for every phase:

```
Constitution  -->  Specification  -->  Planning  -->  Tasks  -->  Execution  -->  Validation
(principles)      (what to build)     (how)          (steps)     (code)          (verify)
```

### 6.1 Constitution

Project-level principles that govern all decisions:

- **Behavioral Parity**: Same input must produce same output (the fundamental migration constraint)
- **Source Traceability**: Every target code element must link to its source origin
- **Security-by-Default**: Migration is an opportunity to fix vulnerabilities, never to regress
- **Test-First**: No phase is complete without its test gate

### 6.2 Specification

Each migration phase gets a formal spec with:
- User stories mapping to source functionality
- Functional requirements with IDs (FR-NNN)
- Acceptance criteria (measurable, technology-agnostic)
- Success criteria gates

### 6.3 Planning

Each spec produces a plan with:
- Technical context from dimension analysis
- Constitution check gate (verify principles aren't violated)
- Dependency-ordered implementation batches
- Risk assessment

### 6.4 Tasks

Plans decompose into checkboxed tasks with:
- Parallel markers [P] for independent work
- User story references [US#]
- Source file cross-references

### 6.5 Execution

Implementation follows the task list with:
- Source traceability comments on every code element
- Continuous test execution
- Coverage validation at each batch boundary

### 6.6 Validation

Each phase exit requires:
- All tests green (zero skips allowed)
- Coverage validator reports 0 unmatched in-scope functions
- Semantic verification for modified code
- Spec acceptance criteria met

---

## 7. Coverage Verification (Structural)

### 7.1 The Problem: LLM Attention Blindness

Even with 1M context models that can load entire repositories, LLMs systematically miss code elements during migration:

- **Attention dilution**: Long files (2000+ lines) cause attention to concentrate on early/prominent functions while skipping less prominent ones
- **Name collision**: Functions with common names may be "covered" by false matches from unrelated files
- **Scope creep**: File-level Source comments claim coverage of an entire file while actually covering only 2-3 functions
- **Community detection limitations**: Graph analysis may group functions into the wrong community, causing them to fall through phase boundaries

### 7.2 The Solution: Multi-Dimensional Coverage Validation

A programmatic validator checks coverage across all dimensions:

1. **AST-based source inventory**: Parse every source file with a language-specific AST parser (e.g., tree-sitter) to extract exact function boundaries (start AND end lines)
2. **Target traceability scanning**: Parse every target file for traceability comments linking back to source files
3. **File-specific matching**: A function is only "covered" if the target file's Source comment references the SAME source file (no global name fallback)
4. **Dimension cross-check**: Verify that call graph edges, database table references, hook invocations, and import chains are all present in the target

### 7.3 Coverage Categories

| Category | Definition |
|----------|-----------|
| **Exact match** | Target function has Source comment pointing to this exact source function with correct file + line range |
| **Eliminated** | Source function is documented as eliminated (e.g., dead code, deprecated feature, language-specific infrastructure) |
| **Unmatched** | Source function has no target equivalent -- a gap that must be resolved |

### 7.4 Why This Matters

In the reference project, initial "file-level" coverage appeared to be 100%. When re-analyzed with strict function-level, file-specific matching:
- 320 of 554 functions were "file-level matches" only (claimed but not actually migrated)
- True strict coverage was 41.2%
- After iterative gap resolution across multiple sessions, coverage reached 100%

**Without programmatic coverage validation, migration gaps are invisible.** The LLM's confidence in "complete" migration is unreliable -- the validator is the source of truth.

---

## 8. Semantic Verification (Behavioral)

### 8.1 The Problem: Structural Coverage != Behavioral Correctness

A function can be "covered" (present in the target with a Source comment) but semantically wrong. During the reference project, SME review of sampled function pairs revealed that **all reviewed functions had semantic discrepancies** despite 100% structural coverage.

Categories of semantic discrepancy include:

- **Type system divergence**: Source language's type coercion semantics don't match target language (e.g., PHP `empty("0")` is truthy, Python `"0"` is falsy -- affects every conditional)
- **SQL translation drift**: Same query intent, different SQL topology (implicit joins vs explicit, different WHERE columns, missing subquery wrappers)
- **API contract divergence**: Missing response fields, different error envelopes, changed parameter types
- **Side effect ordering**: Operations happen in different sequence (cache invalidation before vs after write)
- **Feature omission**: Sub-features silently dropped during migration
- **Error model change**: Source logs-and-continues, target raises exceptions (fundamentally different failure semantics)

### 8.2 The Solution: Deep Semantic Verification

Every migrated function undergoes line-by-line comparison against its source:

1. **Read source function** with exact line boundaries from AST parser
2. **Read target function** with its Source traceability comment
3. **Compare control flow**: Every branch, loop, and return in source must have a corresponding construct in target
4. **Compare data flow**: Every variable assignment, function call argument, and return value must be semantically equivalent
5. **Check language-specific traps**: A catalog of known translation traps for the specific language pair (40+ for PHP-to-Python)
6. **Verify integration pipeline contracts**: Cross-function data flow boundaries must preserve the same shape and semantics

### 8.3 Complexity-Tiered Triage

Not all functions need the same verification depth:

| Tier | Criteria | Verification Depth |
|------|----------|-------------------|
| **Tier 1** (deep audit) | Functions with complex SQL, multiple branches, or cross-cutting callers | Line-by-line with language-trap checklist |
| **Tier 2** (standard) | Functions with moderate complexity | Block-level comparison with spot checks |
| **Tier 3** (quick check) | Simple getters, setters, thin wrappers | Signature + return type check |
| **Tier 4** (model check) | ORM models / data classes | Column-by-column schema comparison |

### 8.4 Integration Pipeline Verification

Beyond individual functions, verify multi-step workflows end-to-end:

- Identify the N-step pipeline (e.g., "feed update" = fetch -> parse -> sanitize -> deduplicate -> store -> invalidate cache -> update counters)
- At each boundary between steps, verify that the data shape passed from step N to step N+1 is identical in source and target
- Verify side effects happen in the same order

---

## 9. Multi-Session Continuity

Complex migrations span many AI sessions. The framework ensures continuity through:

### 9.1 Session Memory

Each session ends with a structured memory file capturing:
- What was completed (with commit references)
- What remains (with priority ordering)
- Decisions made (with ADR references)
- Blockers discovered

### 9.2 Feedback Loop

User corrections create persistent feedback memories that guide all future sessions:
- Behavioral rules ("always consult specs before proposing changes")
- Quality standards ("semantic verification must be deep, not superficial")
- Process corrections ("don't skip the consistency checklist")

### 9.3 Spec-as-Source-of-Truth

Specs, ADRs, and the constitution are the durable artifacts. Session memories are ephemeral context. When a conflict exists between memory and specs, specs win. When specs need updating, the update must touch ALL referencing locations atomically (consistency rule).

---

## 10. Benefits of This Approach

### 10.1 Trade-off Flexibility

ADR-driven decisions make trade-offs **explicit and adjustable**:

- **Time to market vs. technical excellence**: The framework allows choosing a "less modern" target technology that better matches the source architecture (e.g., Flask over FastAPI) because reducing translation distance accelerates delivery
- **Fidelity vs. improvement**: Security vulnerabilities can be fixed during migration while maintaining behavioral parity for everything else
- **Completeness vs. speed**: Dimensions can be re-prioritized mid-migration if business needs change
- **SPA rewrite vs. keep existing frontend**: Choosing to build a new SPA frontend vs. keeping the legacy UI is a documented ADR with clear trade-offs, not an implicit assumption

### 10.2 Migration Coverage (Blind Spot Detection)

Even 1M-context models loading all repo files will systematically miss code during migration:

- **Attention dilution** in long files causes functions to be skipped
- **File-level traceability** creates false confidence (claiming a 2000-line file is "covered" when 3 functions were migrated)
- **Cross-session drift**: Work done in session 5 may conflict with assumptions from session 2

The programmatic coverage validator solves this by treating coverage as a **measurable metric** checked at every phase gate, not a subjective judgment. This multi-session approach with explicit coverage percentage tracking catches blind spots that single-session approaches miss entirely.

### 10.3 Semantic Correctness Assurance

Structural coverage (the code exists) is necessary but not sufficient. Semantic verification catches:

- **Silent behavioral divergence**: Code that compiles and passes basic tests but produces different output for edge cases
- **Language-specific traps**: Patterns that look equivalent across languages but behave differently (40+ documented for PHP-to-Python alone)
- **Integration boundary errors**: Individual functions are correct but the data they pass between each other has changed shape

The dual coverage+semantic approach is like the difference between "did we translate every sentence?" and "does the translated document mean the same thing?"

### 10.4 Test Coverage Even for Legacy Systems Without Tests

The framework generates comprehensive test suites even when the source system has zero tests:

- **Unit tests**: Generated from source code analysis with traceability comments citing the PHP source function, its behavior, and the assertion
- **Integration tests**: Generated from API contract analysis, verifying endpoint behavior
- **E2E/UI automation tests**: Generated from video recordings, screenshots, and SME transcriptions of the working source application
- **Golden-file regression tests**: Captured from running the source system, replayed against the target

This means the migration target ends up with **better test coverage than the source ever had**, turning migration from a risk event into a quality improvement event.

### 10.5 Adversarial Quality Assurance

The framework uses adversarial self-refinement at multiple points:

- **ADR evaluation**: Isolated critic agents try to break each proposed decision
- **Code verification**: Isolated critic agents review migrated code against source, looking specifically for the discrepancy taxonomy
- **Spec consistency**: Cross-artifact analysis catches contradictions between specs, ADRs, and code

This adversarial approach catches issues that cooperative-only review misses, because the critic agent's explicit goal is to find flaws, not to confirm correctness.

---

## 11. Answers to Key Migration Questions

### Q1: Knowledge Extraction -- Dimensions and Storage

**How to collect different dimensions and define new ones?**

Dimensions are discovered during Phase 0 through:

1. **Automated analysis**: AST parsing + graph analysis of source code reveals call graphs, entity relationships, module dependencies
2. **Deep web research**: Research on the source technology's common architectural patterns reveals which dimensions are typically important
3. **Manual identification**: SME interviews and documentation review reveal domain-specific dimensions (business rules, regulatory constraints, data lineage)

Each discovered dimension is stored as a structured markdown file:
- `specs/architecture/NN-dimension-name.md` -- formal dimension definition with graph data, communities, and dependency levels
- Dimensions are immutable reference specs; they capture what IS, not what should be

**New dimensions** can be defined at any point by:
1. Creating a new spec file with the dimension's graph structure
2. Adding it to the coverage validator's dimension list
3. Re-running coverage validation to assess the migration's completeness along the new dimension

### Q2: Adjustment of Functionality with Product Team

The spec-driven workflow provides natural integration points for product team review:

1. **After Phase 0 (Knowledge Extraction)**: Product team reviews the source inventory and confirms which features are in scope, which are deprecated, and which need enhancement during migration
2. **During ADR decisions**: Product team participates in trade-off decisions (e.g., "do we keep the legacy Dojo UI or build a new SPA?")
3. **After each phase spec**: Product team reviews acceptance criteria before implementation begins
4. **During semantic verification**: SME review of sampled function pairs catches behavioral divergences that automated tools miss
5. **Video/screenshot ingestion**: Product team provides recordings of the working source application; these are transcribed and used to generate E2E test scenarios

The ADR process is specifically designed for this: proposed decisions include trade-off analysis tables that non-technical stakeholders can evaluate.

### Q3: Migration Plan / Roadmap

The roadmap emerges from dimension analysis:

1. **Phase ordering** is determined by dependency levels in the primary dimension (call graph, entity graph, or whatever the project prioritizes)
2. **Phase grouping** uses graph community detection to find natural migration units
3. **Phase gating** ensures each phase is complete before the next begins (tests green, coverage validated, semantic verification passed)

The roadmap is stored as:
- `specs/NNN-phase-name/spec.md` -- what to build
- `specs/NNN-phase-name/plan.md` -- how to build it
- `specs/NNN-phase-name/tasks.md` -- checkboxed steps

### Q4: Migration Strategy and Architecture Constraints

Strategy is captured in three layers:

1. **Constitution** (`constitution.md`): Immutable principles ordered by priority (e.g., "behavioral parity" > "security improvement" > "code modernization")
2. **ADRs** (`docs/decisions/`): Each constraint gets a formal record with context, options, trade-off analysis, and decision
3. **Dimension specs** (`specs/architecture/`): The structural analysis that informs strategy

Architecture constraints are enforced through:
- **Traceability verification**: Every code element must link to its source
- **Coverage validation**: Every source element must have a target equivalent
- **Semantic verification**: Every target element must be behaviorally equivalent
- **Test gates**: Phase completion requires all tests green with zero skips

### Q5: Data Migrations Including Transformations

Data migration is a first-class concern:

1. **Schema mapping**: Source schema is analyzed dimension-by-dimension; ORM models are generated from source schema (e.g., via sqlacodegen) and then reviewed/adjusted
2. **Transformation rules**: When source and target schemas differ (e.g., password hash upgrade, encryption algorithm change), transformation functions are documented as ADRs with rollback plans
3. **Subset migration**: For development/testing, a data subset strategy is defined:
   - Seed data (minimum viable dataset for each entity cluster)
   - FK-ordered insertion (respect referential integrity)
   - Anonymization rules for PII
4. **Full migration tooling**: Tools like pgloader (for MySQL-to-PostgreSQL) or custom ETL scripts handle production data migration
5. **Verification**: Post-migration row counts, FK integrity checks, and spot-check queries validate data correctness

---

## 12. Applicability to Different System Types

The framework adapts its dimension priorities to the application type:

| System Type | Primary Dimension | Secondary Dimensions | Example Adjustments |
|-------------|------------------|---------------------|-------------------|
| **Web Application (MVC)** | Entity Graph | Call Graph, Frontend/Backend Coupling | Walking skeleton approach; API contract tests |
| **Server-Side Rendered App** | Frontend/Backend Coupling | Entity Graph, Template System | Template migration becomes a phase; JS coupling analysis |
| **Desktop Application** | UI Event Model | Call Graph, Data Persistence | Widget tree migration; event binding preservation |
| **CLI Tool** | Call Graph | Argument Parsing, I/O Model | Argument/flag parity tests; exit code preservation |
| **Data Processing Pipeline** | Pipeline Topology | Data Model, Checkpoint Semantics | DAG preservation; idempotency guarantees; data subset testing |
| **Network Protocol Implementation** | Protocol State Machine | Timer Semantics, Packet Encoding | State machine equivalence proofs; packet capture replay testing |
| **Microservices** | API Contract Surface | Data Model per service, Inter-service Communication | Contract-first migration; service-by-service vertical slices |
| **SQL Trigger/Stored Proc System** | Data Pipeline Topology | Entity Graph, Transaction Boundaries | Trigger-to-application-code extraction; transaction semantics preservation |

---

## 13. Starter Prompts

### 13.1 Phase 0: Knowledge Extraction

```
== ultrathink ==

This project contains source code to be migrated from [SOURCE_TECH] to [TARGET_TECH].
Source is in [source-dir/], target will grow in [target-dir/].

Your job for now:
1. Deep analysis of source repos
2. Build spec-kit driven workspace with comprehensive specs inferred from source code
   - Use deep web research for architectural patterns, common migration pitfalls,
     and target technology best practices
   - Create a source code index where each spec points to related source files
3. Discover and document analysis dimensions:
   - Call graph dependencies (use AST parsing)
   - Entity/database relationships
   - [Additional dimensions relevant to this project type]
4. Propose migration flow variants with trade-off analysis
5. Store all artifacts in project-local directories (specs/, docs/, memory/)

Ask questions if requirements are ambiguous.
```

### 13.2 Phase 1: ADR Decisions

```
/adversarial-thinking [session-memory-file] accept P0 ADRs

Evaluate the proposed P0 decisions using adversarial evaluation:
1. Generate 3 divergent solution candidates
2. Stress-test each with isolated critique agents
3. Document the winning decision in MADR 4.0 format
4. Update ALL referencing locations atomically
```

### 13.3 Phase N: Execute Migration Phase

```
Implement [specs/NNN-phase-name/tasks.md]

Follow the task list. For each task:
1. Read the source code referenced in the spec
2. Implement the target code with traceability comments
3. Run tests after each batch
4. Run coverage validation at batch boundaries
```

### 13.4 Coverage Check

```
Run full coverage verification -- ensure every element of source files
is processed and produced translation artifacts in target repo.

Use AST-based parsing (not grep) for exact function boundaries.
File-specific matching only (no global name fallback).
```

### 13.5 Semantic Verification

```
/adversarial-self-refine Run deep semantic verification per
specs/architecture/NN-semantic-discrepancies.md

For EVERY migrated function:
1. Read source with exact line boundaries
2. Read target with traceability comment
3. Compare line-by-line: control flow, data flow, language traps
4. Fix all discrepancies
5. Add/update tests for each fix
```

---

## 14. Appendix: Reference Project Statistics

The methodology was validated on a PHP-to-Python web application migration:

| Metric | Value |
|--------|-------|
| Source LOC | ~18,600 PHP |
| Source files | 138 |
| Database tables | 35 (31 active) |
| Plugin hooks | 24 |
| API endpoints | 17+ REST, 40+ RPC |
| Sessions to complete | 19 |
| Specs generated | 14 architecture + 6 phase specs |
| ADRs created | 19 |
| Tests at completion | 1,474 (unit + integration + E2E) |
| Semantic discrepancy categories | 40 (D01-D40) |
| Language-specific traps documented | 40+ |
| Integration pipelines verified | 8 |
| Final structural coverage | 100% (458/458 in-scope functions) |
| Security improvements | SHA1->argon2id, mcrypt->Fernet, prepared statements, CSRF, security headers |
