# AI-Assisted Software Migration Architecture

**A Dimension-Driven Framework for Migrating Arbitrary Software Systems**

---

## Pipeline Overview

This migration framework follows a five-stage pipeline. Each stage produces concrete artifacts that feed the next. The stages ensure that knowledge is extracted before decisions are made, decisions are made before plans are created, and plans are verified continuously during execution.

| Pipeline Stage | What It Produces | Stakeholder Gate |
|---|---|---|
| **Knowledge Extraction** | Source inventory, inferred dimensions (stored as MD files), dependency maps, technology research | Architect review |
| **Functionality Adjustment with Product Team** | Feature scope matrix, deprecated feature list, enhancement requests, SME recordings | Product team sign-off |
| **Migration Strategy and Architecture Decisions** | Governing principles, architecture decisions with trade-off analysis, constraints | Architecture board approval |
| **Migration Plan and Roadmap** | Phase specs, plans, task lists, data migration and transformation strategy | Project management review |
| **Execution with Continuous Verification** | Target code (with traceability), tests, coverage reports, behavioral verification reports | Dev lead + QA |

### Key Artifacts

The framework produces a structured set of migration-specific artifacts. Examples from the reference PHP-to-Python migration:

**Architecture decision** -- captures each non-trivial choice with trade-off analysis:

```markdown
# 0002 -- Select Python Web Framework
## Considered Options
1. Flask -- closest match to source handler dispatch; native session/CSRF
2. FastAPI -- modern async; but no built-in sessions, CSRF requires JS changes
3. Django -- full-featured but over-engineered for this codebase
## Decision: Flask
Rationale: reduces translation distance; zero frontend changes needed
```

**Dimension specs** -- each structural dimension inferred from source analysis is stored as an MD file. Excerpts from the actual project specs:

```
# Dimension 1: Call Graph Dependencies (specs/architecture/10-migration-dimensions.md)

Entry Points → Bootstrap → Handlers → Business Logic → Database
                                    → Plugin System
                                    → Feed Processing

Core bootstrap chain (must be migrated first in any flow):
  autoload.php → config.php → db.php → functions.php → db-prefs.php
Handler dependency chain:
  Handler (base) → Handler_Protected → {RPC, Feeds, Article, Pref_*}
                 → Handler_Public
                 → API
```

```
# Dimension 2: Entity / Database Relationships (specs/architecture/10-migration-dimensions.md)

| Cluster          | Tables                                       | Operating Code              |
| User Core        | ttrss_users, ttrss_sessions, ttrss_access_keys | sessions.php, auth_internal |
| Feed Management  | ttrss_feeds, ttrss_feed_categories           | pref/feeds.php, rssfuncs.php |
| Article Content  | ttrss_entries, ttrss_user_entries, ttrss_enclosures | rssfuncs.php, article.php |
| Filtering        | ttrss_filters2, ttrss_filters2_rules/actions | pref/filters.php, rssfuncs.php |
```

```
# Dimension 3: Frontend / Backend Coupling (specs/architecture/10-migration-dimensions.md)

| Frontend Component | Backend Handler(s)                | Coupling Level           |
| Feed sidebar tree  | Pref_Feeds::getfeedtree, RPC::getAllCounters | HIGH — custom Dojo store |
| Headlines panel    | Feeds::view (server-rendered HTML) | HIGH — HTML fragments   |
| Article view       | Article::view                     | MEDIUM — JSON data       |
| API (external)     | API class                         | LOW — pure JSON          |
```

**Migration traceability** -- links every target code element to its source origin. This can be implemented as inline comments, separate index files, or any other mechanism that allows programmatic validation. Examples of different match levels:

```python
# Direct match: source function maps 1:1 to target function
# Source: ttrss/include/functions.php:authenticate_user (lines 706-771)
def authenticate_user(login: str, password: str) -> Optional[User]:
    ...

# Multi-source: target function combines logic from multiple source files
# Source: ttrss/classes/feeds.php:Feeds::view (lines 45-120)
# + ttrss/include/functions2.php:queryFeedHeadlines (lines 200-450)
def view_feed(feed_id: int, view_mode: str) -> dict:
    ...

# Inferred: source pattern adapted for different target framework
# Inferred from: ttrss/include/sessions.php (session validation pattern)
# Adapted for Flask-Login; no direct PHP equivalent exists
def validate_session(session_id: str) -> bool:
    ...

# New: genuinely new code with no source equivalent
# New: no source equivalent (Alembic migration infrastructure)
def run_migrations():
    ...

# Eliminated: source code intentionally not ported
# Eliminated: ttrss/classes/db/mysql.php (MySQL adapter -- PostgreSQL-only per ADR-0003)
```

### Pipeline Flow

```
  SOURCE SYSTEM
       |
       v
  KNOWLEDGE EXTRACTION
  Infer dimensions from source code analysis and technology research
  Store each dimension as structured MD file
       |
       v
  FUNCTIONALITY ADJUSTMENT
  Product team reviews source inventory
  Confirm scope: keep / deprecate / enhance per feature
  Ingest SME knowledge (video, transcriptions, spreadsheets)
       |
       v
  MIGRATION STRATEGY & DECISIONS
  Define governing principles
  Infer and evaluate architecture decisions covering:
    - migration approach and flow
    - target technology stack
    - data migration and transformations
  Accept decisions via structured review with trade-off analysis
       |
       v
  MIGRATION PLAN / ROADMAP
  Select migration flow variant based on dimension analysis
  Create phase specs with entry/exit criteria
  Define data migrations: schema mapping, transformations, subset strategy
       |
       v
  EXECUTION WITH CONTINUOUS VERIFICATION
  Per phase: implement --> build/lint/test --> validate coverage --> verify behavior
  Traceability: every target element linked to source origin
  Coverage: programmatic validation that nothing was missed
  Behavioral check: source vs target comparison using platform knowledge catalog
```

---

## Migration Traceability and Coverage Verification

This is the core mechanism that makes complete migration achievable. Without it, AI-assisted migration reliably covers only 20-40% of a codebase, regardless of model context size.

### The Problem: Why AI Models Miss Code

Even with large-context models that can load entire repositories, code elements are systematically missed during migration:

- **Attention dilution**: Long files (2000+ lines) cause attention to concentrate on prominent functions while skipping less prominent ones
- **False coverage**: File-level traceability claims coverage of an entire file while actually covering only a few functions
- **Name collision**: Functions with common names may be "covered" by false matches from unrelated files
- **Cross-session drift**: Work done in session 5 may conflict with assumptions from session 2

In the reference project, initial coverage appeared to be 100%. When re-analyzed with strict function-level matching, true coverage was **41.2%** -- 320 of 554 functions were only surface-level matches (claimed but not actually migrated). Only after iterative gap resolution did coverage reach 100%.

### How It Works: Blind Zone Detection, Not Transpilation

A common misconception is that traceability-based migration works like a transpiler -- feeding source code line-by-line into an AI model and getting target code back. **This is not how it works.** The approach works for any migration, including full architectural redesigns (monolith to microservices, server-rendered to SPA, SQL triggers to stream processing).

The key insight: **traceability is used to detect what was missed, not to constrain how migration is done.** The AI model is free to redesign, restructure, and re-architect the target system in any way the architecture decisions prescribe. Traceability only tracks which source elements have been accounted for.

```
                    SOURCE CODEBASE
                    (all functions inventoried)
                           |
                    +------v-------+
                    | COVERAGE     |
                    | VALIDATOR    |
                    | Compares     |
                    | source       |
                    | inventory    |
                    | against      |
                    | target       |
                    | traceability |
                    +------+-------+
                           |
              +------------+------------+
              |                         |
     COVERED (72%)              BLIND ZONES (28%)
     Already processed          Not yet accounted for
              |                         |
              |                    +----v-----+
              |                    | AI MODEL |
              |                    | receives |
              |                    | blind    |
              |                    | zone     |
              |                    | report   |
              |                    +----+-----+
              |                         |
              |                    MODEL DETERMINES:
              |                    - What business function
              |                      this source code serves
              |                    - Where in the TARGET
              |                      architecture it belongs
              |                    - Whether it maps to an
              |                      existing target module
              |                      or needs a new one
              |                         |
              |                    +----v-----+
              |                    | GENERATE |
              |                    | or UPDATE|
              |                    | target   |
              |                    | code     |
              |                    +----+-----+
              |                         |
              +------------+------------+
                           |
                    +------v-------+
                    | RE-VALIDATE  |
                    | Coverage     |
                    | improves     |
                    | 72% → 85%   |
                    | → 93% → 100%|
                    +--------------+
```

**Example**: Suppose the source is a monolith and the target is microservices. The coverage validator detects that `functions.php:authenticate_user` (lines 706-771) has not been accounted for in any target service. It does NOT tell the AI "translate these 65 lines." Instead, the AI:

1. Reads the source function to understand what it does (user authentication with SHA1 + session creation)
2. Looks at the target architecture to determine where authentication belongs (the `auth-service` microservice)
3. Checks what the `auth-service` already has and what's missing
4. Implements the missing functionality in the target's idiom (argon2id, JWT tokens, whatever the architecture decisions prescribe)
5. Adds a traceability link so the validator knows this source element is now accounted for

The traceability link does NOT mean the target code is a line-by-line translation. It means "this source functionality has been considered and its business intent is preserved in the target."

This is why the approach works equally well for:
- **Near-identical translations** (Java 8 -> Java 17): most functions map 1:1
- **Framework migrations** (PHP monolith -> Python Flask): structure changes but functions mostly map
- **Full redesigns** (monolith -> microservices): source functions scatter across multiple services; traceability tracks which ones have been accounted for
- **Technology shifts** (SQL triggers -> Spark): source triggers become streaming jobs; traceability ensures no trigger is forgotten

### Traceability Levels

Every meaningful code element in the target carries a traceability link to its source origin:

- **Direct**: source function maps to target function
- **Method-level**: source `Class::method` maps to target method
- **File-level**: target module aggregates logic from a single source file
- **Multi-source**: target function combines logic from multiple source files
- **Schema-level**: target models derived from database schema definitions
- **Inferred**: target code adapted from source patterns with no direct equivalent
- **New**: genuinely new code with no source equivalent
- **Eliminated**: source code intentionally not ported (documented as dead, deprecated, or superseded)

### The Coverage Validator

A programmatic validator checks coverage across all dimensions:

1. **Source inventory**: Parse every source file to extract function boundaries
2. **Target scanning**: Parse every target file for traceability links back to source
3. **Strict matching**: A function is "covered" only if the target's traceability references the SAME source file -- no global name fallback
4. **Dimension cross-check**: Verify that dependency edges, entity references, and integration points are present in the target

Every source function falls into one of three categories:

| Category | Definition |
|---|---|
| **Covered** | Target code with traceability link pointing to this source function |
| **Eliminated** | Documented as dead code, deprecated, or source-technology-specific infrastructure |
| **Unmatched** | No target equivalent -- a blind zone that must be resolved |

### Behavioral Verification

A function can be structurally "covered" but semantically wrong. During the reference project, SME review of sampled function pairs revealed that **all reviewed functions had behavioral discrepancies** despite 100% structural coverage.

The behavioral verification process compares source and target function pairs:

1. Read source function with exact boundaries
2. Read target function with its traceability link
3. Compare control flow (every branch, loop, return)
4. Compare data flow (assignments, arguments, return values)
5. Check against the platform knowledge catalog (see below)
6. Verify integration boundaries (data shape between cooperating functions)

Verification depth is tiered by complexity:

| Tier | Criteria | Depth |
|---|---|---|
| **Tier 1** | Complex logic, many branches, cross-cutting callers | Line-by-line |
| **Tier 2** | Moderate complexity | Block-level with spot checks |
| **Tier 3** | Simple getters/setters/wrappers | Signature + return type |
| **Tier 4** | Data models / schemas | Column-by-column |

### Platform Knowledge Catalog

During migration, the team discovers patterns where the source and target platforms behave differently despite superficially similar code. These are cataloged as a project-specific reference.

The catalog is organized by domain: type system, string handling, date/time, database interaction, HTTP/session, architecture patterns. Each entry documents: the source platform pattern, how the target platform differs, and estimated frequency in the codebase.

In the reference project, 40 such patterns were discovered and 600+ call sites were affected. This catalog becomes the checklist that prevents the same class of error from recurring across migration phases.

### Continuous Verification During Execution

Every batch of migrated code goes through:

1. **Build and lint** -- target code compiles and passes static analysis
2. **Unit and integration tests** -- generated from source analysis even when the source had no tests
3. **Coverage validation** -- programmatic check that all in-scope source functions are accounted for
4. **Behavioral spot-checks** -- Tier 1 functions verified against the platform knowledge catalog

This incremental verification is a fundamental benefit of the approach: errors are caught within the same session they are introduced, not discovered weeks later during integration testing.

---

## Knowledge Extraction

**Goal**: Understand the source system deeply enough to make informed migration decisions.

### Dimensions Are Inferred During Analysis

The framework does not prescribe a fixed set of dimensions. Instead, dimensions are **inferred** during source code analysis and technology research. Every software system has its own structural characteristics, and the analysis discovers which dimensions are most relevant for the specific project.

### Commonly Occurring Dimensions

Three dimensions appear in nearly every migration, though their relative importance varies:

| Dimension | What It Captures | Migration Impact |
|---|---|---|
| **Call Graph** | Which functions/methods call which others | Determines migration order: dependencies must exist before dependents |
| **Data Model / Entity Graph** | Tables, schemas, relationships, entity clusters | Determines what models/types must exist before business logic |
| **Module Dependency Graph** | Import/include chains between files/packages | Determines build order and circular dependency risks |

At higher levels of abstraction, similar structural dimensions appear:

| Dimension | What It Captures | Applicable When |
|---|---|---|
| **Service Dependency Graph** | Which microservices call which others; upstream/downstream relationships | Distributed systems, SOA |
| **Data Mesh Domain Boundaries** | Which data domains own which datasets; cross-domain contracts | Data platform migrations |
| **Event/Message Flow Graph** | Which producers emit which events; which consumers subscribe | Event-driven architectures |
| **Infrastructure Dependency Map** | Which services depend on which infrastructure (databases, caches, queues) | Cloud migrations, platform shifts |

### Domain-Specific Dimensions

Beyond the common ones, each project type reveals its own dimensions. The table below shows a few examples -- real projects frequently surface dimensions not listed here, such as regulatory compliance boundaries, shared library version constraints, hardware abstraction layers, multi-tenant isolation boundaries, or build system dependency chains:

| Dimension | Example Projects |
|---|---|
| Frontend/Backend Coupling | Web apps with server-rendered HTML or API-driven SPAs |
| Plugin/Extension System | Applications with hook points and extension APIs |
| Protocol State Machine | Network protocol implementations (BFD, BGP, MQTT) |
| Data Pipeline Topology | ETL systems, stream processors, SQL trigger chains |
| Configuration Surface | Systems with extensive config constants or feature flags |
| Security Surface | Applications with auth flows, encryption, session management |
| Concurrency Model | Multi-threaded, async, or event-driven systems |
| API Contract Surface | Systems with external API consumers requiring backward compatibility |

### How Dimensions Are Discovered

1. **Inventory** all source files with language and purpose annotation
2. **Analyze dependencies** across the source code to build structural maps for each discovered dimension
3. **Identify natural groupings** -- clusters of tightly-coupled code that form natural migration units
4. **Rank dimensions** by migration impact: the highest-coupling dimension drives primary migration order
5. **Research** source and target technology patterns, best practices, and known migration pitfalls for the specific technology pair

### Storage

Each dimension is stored as a structured markdown file: `specs/architecture/NN-dimension-name.md` with dependency structure, natural groupings, and dependency levels. New dimensions can be defined at any point during the migration.

---

## Functionality Adjustment with Product Team

**Goal**: Align migration scope with business needs before any code is written.

The framework provides natural integration points for product team review:

1. **Feature scope review**: Product team reviews the source inventory and confirms which features are in scope, which are deprecated, and which need enhancement
2. **Trade-off participation**: Product team evaluates decision trade-off analysis tables (designed for non-technical stakeholders)
3. **Phase acceptance criteria**: Product team reviews each phase spec before implementation begins
4. **SME knowledge ingestion**: Product team provides recordings, screenshots, and transcriptions of the working source application -- used to generate E2E test scenarios and verify behavioral parity
5. **Behavioral verification sampling**: SME review of selected source-vs-target function pairs catches divergences that automated checks miss

**Key artifact**: A feature scope matrix documenting for each source feature: keep as-is, enhance during migration, deprecate, or eliminate.

---

## Migration Strategy and Architecture Decisions

**Goal**: Lock in all blocking decisions before implementation begins.

### Governing Principles

Project-level principles, ordered by priority:

- **Behavioral Parity**: The target system must preserve the business functionality of the source. This does not mean identical I/O at the API level -- APIs, protocols, and interfaces may change as documented in architecture decisions. It means the same business operations produce equivalent business outcomes. For example, in the reference project: PHP's server-rendered HTML was replaced by a completely new vanilla JS SPA; SHA1 password hashing was replaced by argon2id; MySQL support was entirely dropped in favor of PostgreSQL-only. Each deviation was a deliberate, documented decision -- not an accident.
- **Source Traceability**: Every target code element must link to its source origin. This is what makes coverage validation possible and prevents code from "appearing from nowhere" during migration.
- **Incremental Verification**: Every small batch of migrated code is built, linted, tested, and coverage-checked before proceeding to the next. This catches errors within the same session, not weeks later.

### Architecture Decisions

Every non-trivial migration choice is documented as a formal decision record. This includes target architecture decisions, migration process decisions, AND data migration decisions. Decisions are prioritized:

- **P0 (blocks all work)**: Migration flow variant, target framework/language, database engine
- **P1 (blocks specific phases)**: ORM strategy, auth mechanism, background worker architecture
- **P2 (deferrable)**: Logging, i18n, plugin details, monitoring

#### The Decision Process

```
  Infer what decisions are needed
  (from dimension analysis + technology research)
         |
         v
  Draft decision record with 2-5 variants
  (each variant includes trade-off analysis)
         |
         v
  Propose recommended variant
         |
         v
  SME / product team / architect review
         |
         v
  Accept decision --> update ALL referencing artifacts
```

Decisions cover three categories:

1. **Migration approach**: Which dimensions drive the migration order? What flow variant? What phase structure? (Example from the reference project: the "start with a minimal runnable app, then expand" approach was chosen over "one dimension at a time" because the small team size made multi-dimension coordination overhead prohibitive)

2. **Target architecture**: What framework, database, ORM, auth mechanism? (Example: Flask was chosen over FastAPI because Flask's session/CSRF/template model more closely matched the PHP source architecture, reducing translation distance -- even though FastAPI is "more modern")

3. **Boundary decisions**: How to handle cases where source and target have no direct equivalent? (Example: PHP server-rendered HTML had no direct Python equivalent. The decision was to build a new vanilla JS SPA rather than port the legacy Dojo/Prototype frontend -- a complete architectural change justified by the dead state of both legacy JS libraries)

#### Trade-off Transparency

Every decision explicitly documents trade-offs. This is where business value is captured:

- **Time to market vs. technical excellence**: Choosing a framework that better matches source architecture reduces translation distance, even if it's "less modern"
- **Stability vs. innovation**: Using a proven ORM over a newer but less battle-tested one
- **Fidelity vs. improvement**: Fixing security vulnerabilities during migration (SHA1 -> argon2id) while maintaining behavioral parity for everything else
- **Simplification vs. compatibility**: Dropping MySQL support entirely eliminated dual-database testing burden and Sphinx dependency, at the cost of MySQL users needing to migrate data

---

## Migration Plan and Roadmap

**Goal**: Produce a dependency-ordered, phase-gated migration plan with data migration and transformation strategy.

### Migration Flow Variants

Dimension analysis reveals natural migration ordering strategies. The choice of flow variant is itself an architecture decision, because it determines the entire project structure.

Each project discovers its own optimal flow based on its dimensions. For instance, a network protocol library migration (e.g., BFD implementation) would have protocol-data-structure-driven flow; a microservices migration would have service-dependency-graph-driven flow; a data pipeline migration (SQL triggers to Spark) would have DAG-topology-driven flow. The common thread is that **dimensions drive the flow**, not a fixed template.

Some commonly used flow patterns (these are illustrative -- real projects often combine or adapt them):

| Variant | Strategy | Typical Scenario | Risk |
|---|---|---|---|
| **Entity-First** | Models/schemas first, then logic, then handlers | Database-heavy apps, stable data model | Long time before any runnable code |
| **Call-Graph-First** | Entry points first, then fill in dependencies | API-heavy systems, microservices | Stub accumulation |
| **Vertical Slice** | Complete end-to-end slices, one feature at a time | Large team with parallel workstreams | Cross-cutting concerns need early extraction |
| **Minimal Runnable First** | Start with smallest working app, then expand phase by phase | Small team, layered architecture | More upfront planning |
| **One-Dimension-Per-Pass** | Each pass addresses one structural dimension | Large team with specialists per area | High coordination overhead |
| **Protocol-Structure-Driven** | Packet structures and state machines first | Network protocol libraries | |
| **Service-Graph-Driven** | Leaf services first, work inward along dependency graph | Microservice decomposition | |
| **DAG-Topology-Driven** | Sinks first, then transforms, then sources | Data pipeline migrations | |
| **Contract-First** | API contracts first, implementation second | Systems with external consumers | |
| **Message-Topic-Driven** | By event type / topic clusters | Event-driven architectures | |

Business factors influence variant selection:

| Factor | Favors |
|---|---|
| Small team | Minimal runnable first (fast feedback, low risk) |
| Large team | Vertical slices (parallel work) or one-dimension-per-pass (specialists) |
| External API consumers | Contract-first (preserve compatibility) |
| Time-to-market pressure | Minimal runnable first (working app in days) |
| Regulatory constraints | Entity-first (data model stability) |

### Data Migration and Transformations

Data migration covers all forms of persistent and streaming state -- not just relational databases. The approach depends on the type of data being migrated.

#### Database Migrations

1. **Schema mapping**: Source schema analyzed dimension-by-dimension; target models generated and reviewed
2. **Transformation rules**: When schemas differ, transformations documented as architecture decisions with rollback plans
3. **Subset migration** for development/testing: seed data per entity cluster, FK-ordered insertion, PII anonymization
4. **Verification**: Post-migration row counts, FK integrity checks, spot-check queries

Example from the reference project: MySQL-to-PostgreSQL migration via pgloader, including data type mapping, character set conversion, and index recreation. Password hashes were not batch-converted; instead, a dual-verification path upgraded each user to argon2id on their next login. Feed credentials encrypted with deprecated mcrypt were re-encrypted with Fernet on first access.

#### Other Data Migration Scenarios

The same dimension-driven approach applies to non-database data. The examples below are illustrative -- each real project will have its own combination of data types requiring migration:

| Data Type | Migration Considerations |
|---|---|
| **Message schemas** | Schema versioning; consumer/producer compatibility during transition; dead-letter queue handling |
| **ETL pipelines / stored procedures** | Topology preservation; checkpoint/restart semantics; idempotency guarantees; backfill strategy |
| **Data warehouse / OLAP cubes** | Materialized view recreation; aggregation logic equivalence; historical data backfill |
| **File-based state** | Format conversion; directory structure mapping; permission model translation |
| **Search indexes** | Index schema mapping; re-indexing strategy; relevance tuning validation |
| **Object storage** | Key namespace mapping; metadata preservation; access policy translation |

Each data migration type is documented as an architecture decision with transformation rules, rollback plan, and verification criteria.

---

## Hybrid Deployment and Coexistence

During migration, source and target systems often need to coexist. This is especially important for large systems where a "big bang" cutover is too risky.

The coexistence architecture is different for every project and should be accepted through architecture decisions. Some common patterns:

- **Web applications**: Share a database between old and new backends, or use an API gateway to route traffic, or keep the old frontend with a compatibility shim on top of the new backend
- **Microservices**: Migrate service by service, with inter-service contracts preserved at each step; route traffic via service mesh or API gateway
- **Network protocol libraries**: Link old and new library versions together during transition; run conformance tests against both implementations
- **Data pipelines**: Run old and new pipelines in parallel on the same data subset; compare outputs for equivalence before switching over
- **Event-driven systems**: Run dual consumers during transition; compare event handling results; switch producer-by-producer

The key principle is that the hybrid architecture is temporary and has a documented sunset plan. Every compatibility shim, dual-path, or bridge component should be tracked as a future removal item.

---

## Applicability to Different System Types

The framework adapts its dimension priorities and flow variants to the application type. The table below shows typical patterns -- each real project discovers its own dimensions during the knowledge extraction stage. These are illustrative, not exhaustive:

| System Type | Typical Primary Dimension | Common Secondary Dimensions | Example Adjustments |
|---|---|---|---|
| **Web Application (MVC)** | Entity Graph | Call Graph, Frontend/Backend Coupling | Minimal runnable first; API contract tests |
| **Server-Side Rendered App** | Frontend/Backend Coupling | Entity Graph, Template System | Template migration as a phase; JS coupling analysis |
| **Desktop Application** | UI Event Model | Call Graph, Data Persistence | Widget tree migration; event binding preservation |
| **CLI Tool** | Call Graph | Argument Parsing, I/O Model | Argument/flag parity tests; exit code preservation |
| **Data Processing Pipeline** | Pipeline Topology | Data Model, Checkpoint Semantics | DAG preservation; idempotency guarantees |
| **Network Protocol Implementation** | Protocol State Machine | Timer Semantics, Packet Encoding | State machine equivalence proofs; packet capture replay |
| **Microservices** | Service Dependency Graph | API Contracts, Message Bus Topics | Contract-first; service-by-service vertical slices |
| **SQL Trigger/Stored Proc System** | Data Pipeline Topology | Entity Graph, Transaction Boundaries | Trigger-to-application-code extraction |
| **Event-Driven Architecture** | Message Bus Topics | Service Graph, Event Schema | Topic-cluster migration; schema registry preservation |
| **Embedded / IoT** | Hardware Abstraction Layer | Call Graph, Memory Model | HAL compatibility layer; resource constraint testing |

---

## Benefits

### Explicit Trade-offs via Architecture Decisions

Every decision is documented with trade-off analysis. Stakeholders can see exactly why Flask was chosen over FastAPI, why MySQL support was dropped, or why a new SPA was built instead of porting legacy JavaScript. Decisions can be revisited with full context if business needs change.

### Complete Migration via Coverage Validation

Without programmatic coverage validation, AI-assisted migration reliably covers only 20-40% of a codebase. The coverage validator turns migration completeness into a measurable metric checked at every phase gate. In the reference project, this mechanism caught 320 functions that appeared covered but were not.

### Incremental Verification

Every small batch of migrated code is built, linted, tested, and coverage-checked before proceeding. Errors are caught within the same session they are introduced -- not weeks later during integration testing. This is a fundamental advantage over batch migration approaches where errors accumulate undetected.

### Test Generation for Legacy Systems

The framework generates comprehensive test suites even when the source has zero tests: unit tests from source analysis, integration tests from API contracts, E2E tests from SME recordings. The target ends up with better test coverage than the source ever had, turning migration from a risk event into a quality improvement event.

### Behavioral Correctness via Platform Knowledge

The platform knowledge catalog (40 patterns in the reference project, 600+ affected call sites) prevents systematic translation errors. Without it, every function in the target is a potential silent behavioral divergence.

---

## Appendix A: Reference Project Statistics

| Metric | Value |
|---|---|
| Source LOC | ~18,600 PHP |
| Source files | 138 |
| Database tables | 35 (31 active, 4 deprecated/eliminated) |
| Plugin hooks | 24 |
| API endpoints | 17+ REST, 40+ RPC |
| Sessions to complete | 19 |
| Specs generated | 14 architecture + 6 phase specs |
| Architecture decisions created | 19 |
| Tests at completion | 1,474 (unit + integration + E2E) |
| Platform knowledge patterns | 40 categories, 600+ affected call sites |
| Integration pipelines verified | 8 |
| Final structural coverage | 100% (458/458 in-scope functions) |
| Eliminated functions (dead/deprecated) | 27+ |
| Security improvements | SHA1->argon2id, mcrypt->Fernet, prepared statements, CSRF, security headers |

### Legacy elimination examples

| Item | Action Taken |
|---|---|
| MySQL/DB_TYPE conditional SQL branches | Eliminated -- PostgreSQL-only per architecture decision |
| 4 deprecated tables (themes, labels v1, filters v1, scheduled_updates) | Not ported -- absent from source schema v124 |
| SHA1 dual-hash verification | Gradual upgrade to argon2id on login; SHA1 code has documented sunset |
| Sphinx full-text search dependency | Eliminated -- replaced by PostgreSQL tsvector |
| `deprecated.js` backward-compat shim layer | Eliminated -- replaced by vanilla JS SPA |
| Dojo/Prototype legacy JS libraries | Replaced with zero-dependency vanilla JS SPA |
| mcrypt encryption (deprecated in source platform) | Replaced with Fernet symmetric encryption |

## Appendix B: Spec-Driven Development Workflow

Each migration phase follows a spec-driven lifecycle:

```
Principles --> Specification --> Planning --> Tasks --> Execution --> Validation
```

- **Principles**: Project-level governing rules ordered by priority
- **Specification**: User stories, functional requirements, acceptance criteria
- **Planning**: Technical context from dimension analysis, dependency-ordered batches, risk assessment
- **Tasks**: Checkboxed steps with parallel markers and source file cross-references
- **Execution**: Implementation with traceability and continuous testing
- **Validation**: Phase exit gate (tests green, coverage validated, behavioral verification passed)

Each phase produces three files:
- `specs/NNN-phase-name/spec.md` -- what to build
- `specs/NNN-phase-name/plan.md` -- how to build it
- `specs/NNN-phase-name/tasks.md` -- checkboxed steps

### Consistency Rule

When any status, decision, or phase changes, ALL referencing locations must be updated atomically: the decision record, decision index, project charter, dimension specs, and session memory. Partial updates create contradictions that compound across sessions.

## Appendix C: Iterative Decision Evaluation

For critical decisions, the framework can generate multiple solution candidates and iteratively refine them through structured comparison.

The process works in rounds:
1. Generate 3 initial candidates, each optimizing for a different trade-off axis (e.g., time-to-market, technical excellence, behavioral fidelity)
2. Each candidate is reviewed independently, looking for fatal flaws and unaddressed constraints
3. In each round, the weakest candidate (receiving fewest favorable comparisons) is eliminated and replaced by a new candidate that addresses the flaws identified in prior rounds
4. The process repeats with the 2 surviving candidates plus 1 new challenger -- each round requires exactly 3 candidates and 3 pairwise comparisons, making it constant-cost per iteration
5. Iterations continue until candidates converge on the same answer, or until a candidate is strong enough that further iteration shows diminishing returns

This iterative elimination-and-replacement approach avoids anchoring on early candidates while keeping computational cost bounded. It is one approach to generating decision variants. In other cases, variants may come from human architects, vendor proposals, or prior art research. The framework is agnostic to how variants are generated -- only that each decision contains at least 2 evaluated options with trade-off analysis.

## Appendix D: Iterative Code Refinement

After generating migrated code, the framework runs iterative review cycles where an independent reviewer examines the output against the platform knowledge catalog. The implementer fixes identified issues. This cycle continues until no new issues are found.

This is particularly effective for catching platform-specific behavioral differences that are easy to miss on first pass. In the reference project, this process discovered 105+ fixes across 40 discrepancy categories.

## Appendix E: Multi-Session Continuity

Complex migrations span many sessions. Continuity is maintained through:

- **Session memory**: Each session ends with a structured file capturing what was completed, what remains, decisions made, and blockers discovered
- **Feedback persistence**: Corrections from reviewers create persistent rules that guide all future sessions
- **Specs as source of truth**: Specs, decisions, and governing principles are durable artifacts. Session memories are ephemeral context. When conflict exists, specs win.
