# Extended Artifact Guide

Detailed reference material for the knowledge management skill.
Covers type clarifications, full artifact templates,
verification flow examples, and temporal evolution patterns.

Loaded on demand — not part of the main SKILL.md context.

---

## Type Clarifications

### Concept vs Narrative

- **Concept:** Timeless, abstract knowledge.
  Explains _what_ something is or _how_ it works in general terms.
  - Litmus: "Would this be true in any project or context?"
  - Use for: Definitions, architectural patterns, principles, frameworks
  - Example: `Concept - REST API Design`

- **Narrative:** Experiential, context-specific knowledge.
  Tells the story of _what happened_ during a specific event or process.
  - Litmus: "Does this tell what happened in a specific situation?"
  - Use for: Post-mortems, retrospectives, design evolution stories
  - Example: `Narrative - Q1 API Refactoring Experience`

| Aspect        | Concept                      | Narrative                           |
| ------------- | ---------------------------- | ----------------------------------- |
| **Purpose**   | Define and explain           | Recount and reflect                 |
| **Time**      | Timeless, abstract           | Time-bound, specific                |
| **Scope**     | General, context-independent | Specific, context-dependent         |
| **Qualities** | Clarity, coherence           | Richness, relevance, insight        |

### Procedure vs Narrative

- **Procedure:** Prescriptive, instructional knowledge.
  Step-by-step directions for _how to perform_ a task.
  - Litmus: "Can someone follow these steps to complete a task?"
  - Characteristics: Imperative language, numbered steps, prerequisites, decision points
  - Example: `Procedure - Database Migration Process`

- **Narrative:** Experiential, reflective knowledge.
  Tells what _actually happened_ during a specific instance.
  - Litmus: "Does this tell what happened in a specific situation?"
  - Characteristics: Past tense, context/circumstances, decisions and outcomes, lessons learned
  - Example: `Narrative - Production Outage October 2024`

**Key Differentiator:** Procedure = _how to do_ (future, prescriptive).
Narrative = _what was done_ (past, descriptive).

### Claims, Assertions, and Decisions

Claims and decisions require careful classification:

- **Verifiable claim** → Fact (once verified)
  - "Python was created in 1991" → Fact
- **Context-dependent claim** → Narrative
  - "We chose Python for Project X because..." → Narrative
- **Steps to verify a claim** → Procedure
  - "How to benchmark system performance" → Procedure
- **Unverified claim** → Narrative with `[assumption]` tag
  - "System handles 10K req/sec" (untested) → Narrative `#unverified`

---

## Full Artifact Templates

### Fact Template

```markdown
---
title: Fact - Python Creation Date
type: fact
tags:
  - technology
  - computer-science
  - programming-languages
---

## Revision Management

- [r1] 2024-09-01T10:00:00Z → Initial creation

---

# Fact - Python Creation Date

Python was created by Guido van Rossum in 1991.

## Evidence

- Python documentation
- Guido van Rossum's personal blog

## Observations

- [fact] Created in 1991 by Guido van Rossum #history
- [verified] Confirmed by official Python documentation #authoritative
- [source] https://docs.python.org/3/faq/general.html
- [context] First released as version 0.9.0 on February 20, 1991 #timeline

## Relations

- supports [[Concept - Python Language Evolution]]
```

### Concept Template

```markdown
---
title: Concept - Microservices Architecture
type: concept
tags:
  - technology
  - software-engineering
  - architecture
---

## Revision Management

- [r1] 2024-10-01T10:00:00Z → Initial creation

---

# Concept - Microservices Architecture

A software architecture pattern where applications are built
as small, independent services communicating via APIs.

## Definition

Microservices architecture is an approach to developing
a single application as a suite of small services,
each running in its own process
and communicating with lightweight mechanisms.

## Observations

- [fact] Small services communicate via lightweight APIs (HTTP/REST, gRPC) #architecture
- [assumption] Services can be independently deployed and scaled #deployment
- [requirement] Needs service discovery mechanism (Consul, Eureka) #infrastructure
- [constraint] Increased operational complexity vs monolith #tradeoff
- [technique] API Gateway pattern for external communication #integration

## Relations

- is_a [[Concept - Distributed Systems Architecture]]
- requires [[Concept - Service Mesh]]
```

### Procedure Template

```markdown
---
title: Procedure - Database Migration Process
type: procedure
tags:
  - technology
  - software-engineering
  - database
---

## Revision Management

- [r1] 2024-09-15T14:00:00Z → Initial creation

---

# Procedure - Database Migration Process

## Objective

Migrate production database schema without downtime.

## Steps

1. Create backup of current database
2. Test migration on staging environment
3. Apply migration during low-traffic window
4. Verify data integrity post-migration

## Observations

- [requirement] Zero-downtime migration during deployment #availability
- [risk] Data loss if backup verification step skipped #critical
- [constraint] Must complete within 2-hour maintenance window #timing
- [technique] Blue-green deployment for rollback capability #deployment

## Relations

- requires [[Procedure - Database Backup Protocol]]
- implements [[Concept - Zero-Downtime Deployment]]
```

### Narrative Template

```markdown
---
title: Narrative - Production Outage October 2024
type: narrative
tags:
  - technology
  - software-engineering
  - incident-response
  - #outage-2024-q4
---

## Revision Management

- [r1] 2024-10-15T16:00:00Z → Initial creation → Incident documentation

---

# Narrative - Production Outage October 2024

On October 15, 2024, our main API service had a 2-hour outage
due to a cascading failure in our caching layer.
A Redis node ran out of memory,
causing request timeouts that overwhelmed our primary database.

## Observations

- [problem] Redis out-of-memory caused cascading timeouts #incident
- [insight] Cache failure overwhelmed primary database #cascading-failure
- [solution] Implemented memory limits and eviction policies #fix
- [lesson] Backup cache layer needed for critical paths #resilience
- [impact] 2-hour outage affecting 50K users #severity

## Relations

- illustrates [[Concept - Cascading Failure Pattern]]
- externalizes [[Procedure - Incident Response Protocol]]
```

### Ontology Template

```markdown
---
title: Ontology - Core Knowledge Terms
type: ontology
tags:
  - technology
  - software-engineering
  - core-concepts
---

## Revision Management

- [r1] 2024-08-01T09:00:00Z → Initial creation

---

# Ontology - Core Knowledge Terms

prefix: km
description: "Foundational vocabulary for knowledge management system"

## Observations

- [fact] Defines shared vocabulary for knowledge management system #meta
- [requirement] Must remain stable to avoid breaking artifact references #stability
- [context] Evolved from analyzing 50+ artifacts across multiple domains #foundation

## Relations

- imports [[Ontology - Quality Metrics]]

## Terms

- id: km:artifact
  label: "Knowledge Artifact"
  definition: "A structured unit of knowledge"
- id: km:relation
  label: "Relation"
  definition: "A directed link between artifacts"
```

---

## Verification Flow — Detailed Example

### ∆1: Document Unverified Claim as Narrative

```markdown
Narrative - Initial Performance Hypothesis (2024-01-15)

## Observations

- [assumption] System handles 10K req/sec → needs testing #unverified
- [hypothesis] Current architecture sufficient #needs-verification

## Relations

- references [[Procedure - Performance Benchmark Protocol]]
```

### ∆2: Reference or Create Verification Procedure

```markdown
Procedure - Performance Benchmark Protocol

## Revision Management

- [r1] 2024-01-10T10:00:00Z → Initial creation

## Objective

Verify system performance under load.

## Steps

1. Configure load generator → 10K req/sec
2. Run 1M requests → measure latency
3. Record metrics → p50, p95, p99
```

### ∆3: Execute Verification → Immutable Process Narrative

```markdown
Narrative - Performance Testing Execution (2024-01-20)

## Observations

- [process] Executed benchmark protocol → 1M requests #testing
- [result] Measured 10K req/sec → 50ms p95 latency #results
- [context] Testing environment → production-like config #conditions

## Relations

- documents_execution_of [[Procedure - Performance Benchmark Protocol]]
- derived_from [[Narrative - Initial Performance Hypothesis]]
```

### ∆4: Update Fact via Revision

```markdown
Fact - System Performance Metrics

## Revision Management

- [r2] 2024-01-20T15:00:00Z → Added verified metrics → Load test results
- [r1] 2024-01-10T12:00:00Z → Initial creation

## Evidence

- [fact] Handles 10K req/sec → 50ms p95 latency #verified
- [fact] Tested with 1M requests → production config #validated

## Relations

- verified_by [[Narrative - Performance Testing Execution 2024-01-20]]
```

---

## Temporal Evolution Through Narratives

Narratives are immutable temporal records.
New events produce new Narratives; they never edit old ones.

### Example Progression

```markdown
Narrative - Initial Analysis (2024-01-15)

- [finding] Current system at capacity #analysis
- [decision] Investigate optimization options #decision
```

```markdown
Narrative - Follow-up Investigation (2024-01-20)

- [process] Tested 3 optimization approaches #testing
- [result] Caching provides best ROI #results
- [decision] Implement caching layer #decision
- derived_from [[Narrative - Initial Analysis]]
```

```markdown
Narrative - Implementation Review (2024-02-01)

- [outcome] Caching deployed to production #deployment
- [result] Performance improved 50% #success
- documents_implementation_of [[Procedure - Caching Strategy]]
```

### Living Knowledge Gets Updated via Revisions

```markdown
Fact - System Performance Metrics

## Revision Management

- [r3] 2024-02-01T16:00:00Z → Post-caching metrics → 50% improvement
- [r2] 2024-01-20T15:00:00Z → Added verified metrics → Load test
- [r1] 2024-01-10T12:00:00Z → Initial creation

## Evidence

- [fact] Handles 15K req/sec with caching → 30ms p95 latency #verified
- [fact] Previous baseline 10K req/sec → 50ms p95 #historical
- [fact] Improvement verified in production → 2 weeks stable #production
```

**Pattern:** Narratives capture events (immutable timeline).
Facts/Concepts/Procedures evolve via revision (living knowledge).
Relations link them into a coherent knowledge graph.
