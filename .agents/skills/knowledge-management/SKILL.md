---
name: knowledge-management
description: >-
  Creates, revises, and materializes structured knowledge artifacts
  (Fact, Concept, Procedure, Narrative, Ontology) with CoD formatting,
  revision tracking, observation categorization, verification patterns,
  and knowledge graph relations.
  Use when user asks to 'materialize knowledge',
  'document the context', 'summarize progress',
  'save memory', 'create a knowledge artifact',
  or when structuring information into typed artifacts.
version: "2.0"
metadata:
  author: rd162@hotmail.com
  tags: knowledge-management, artifacts, revision, materialization, Basic-Memory
---

# Knowledge Management

Create, revise, and materialize structured knowledge artifacts,
forming interconnected knowledge graphs
with revision tracking and verification patterns.

## When to Use

- Creating or updating knowledge artifacts (Fact, Concept, Procedure, Narrative, Ontology)
- Materializing knowledge from context ("document this", "summarize progress")
- Managing artifact revisions (edit, archive, deprecate)
- Verifying claims through the Unverified → Narrative → Fact pattern
- Building knowledge graphs with typed relations
- User explicitly requests knowledge artifact creation or management

## When NOT to Use

- Simple note-taking without artifact typing (use plain notes)
- External knowledge gathering / web search (use a knowledge gathering capability)
- Pure file operations without knowledge structuring intent

## Termination

| Signal       | Condition                                            | Action                               |
| ------------ | ---------------------------------------------------- | ------------------------------------ |
| MATERIALIZED | All requested artifacts created with relations       | ✓ STOP — knowledge graph updated     |
| REVISED      | Target artifact updated with revision log entry      | ✓ STOP — revision tracked            |
| VERIFIED     | Claim verified, Fact updated with verification trail | ✓ STOP — verification chain complete |
| ARCHIVED     | Obsolete artifacts moved to `__ARCHIVE__/`           | ✓ STOP — archive complete            |

## Graceful Degradation

This skill adapts to the available knowledge management system:

- **Full KM system** (Basic-Memory, Obsidian with API):
  Use native create/edit/move operations for all artifact management.
- **File system only** (markdown files, no KM API):
  Create artifacts as markdown files following the templates below.
  Revision management and relations still work — they are just markdown sections.
- **No file system** (bare LLM, chat-only):
  Output artifacts as structured text in chat.
  The user can save them manually. The templates still apply.

The skill always produces structured artifacts.
The storage mechanism varies; the knowledge structure does not.

---

## Choosing the Right Artifact Type

When unsure which type to create, use these litmus tests:

| Test | Yes → | No → |
| ---- | ----- | ---- |
| Can it be verified as true/false independently? | **Fact** | Concept or Narrative |
| Does it explain how multiple facts relate? | **Concept** | Fact |
| Does it provide step-by-step instructions? | **Procedure** | Narrative |
| Remove all imperative verbs — still valuable? | **Narrative** | Procedure |
| Does it define vocabulary other artifacts must follow? | **Ontology** | Concept |

### Complexity Domain Mapping

Different situations call for different artifact types.
Simple problems with clear cause-and-effect need Facts and Procedures.
Complex or chaotic situations — where patterns only emerge in retrospect —
need Concepts and Narratives to capture sense-making.

| Domain | Characteristics | Best artifact types | Approach |
| ------ | --------------- | ------------------- | -------- |
| **Simple** | Clear cause-effect | Facts, Procedures | Categorize → apply best practice |
| **Complicated** | Knowable cause-effect | Procedures, Concepts | Analyze → apply good practice |
| **Complex** | Emergent cause-effect | Concepts, Narratives | Probe → sense → respond |
| **Chaotic** | No clear cause-effect | Narratives | Act → sense → respond |

If you're documenting a production outage (chaotic), start with a Narrative.
If you're documenting a deployment process (complicated), write a Procedure.
If you're defining what "microservices" means in this org (complex), create a Concept.

---

## Artifact Observations

Each artifact contains observations — concise tagged statements
that capture knowledge in a scannable format.

### Format

```text
- [category] Concise statement about the knowledge #tags
```

### Categories (infer from context)

**Core:** `[fact]` `[requirement]` `[assumption]` `[constraint]`
**Decision:** `[decision]` `[rationale]` `[plan]` `[action]`
**Discovery:** `[insight]` `[problem]` `[solution]` `[hypothesis]`
**Technical:** `[technique]` `[tool]` `[metric]` `[performance]`
**Quality:** `[verified]` `[unverified]` `[draft]` `[deprecated]`
**Risk:** `[risk]` `[impact]` `[tradeoff]`

### Examples

```text
- [fact] PostgreSQL 14 on AWS RDS, 16GB instance #infra
- [decision] GraphQL chosen for flexible queries #api
- [problem] Login takes 2-3 seconds #perf
- [solution] Index users.email column, reduced to <100ms #optimization
- [verified] 10K req/sec measured in load test #benchmark
- [unverified] Scales to 100K req/sec — needs testing #untested
```

---

## Future-Forward Relations

Link to non-existent artifacts as knowledge gap placeholders:

```text
## Relations

- requires [[Procedure - Database Backup Protocol]]   # doesn't exist yet
- implements [[Concept - Zero-Downtime Deployment]]    # needs to be written
```

Syntax: `[[Artifact Type - Name]]` → unresolved link = pending dependency.
These map knowledge gaps and guide future work.

---

## Revision Management

### Type-Based Rules

| Artifact Type | Strategy       | Rationale                             |
| ------------- | -------------- | ------------------------------------- |
| Fact          | Revision-based | Facts evolve with new evidence        |
| Concept       | Revision-based | Definitions refine over time          |
| Procedure     | Revision-based | Steps improve and update              |
| Ontology      | Revision-based | Vocabulary evolves with domain        |
| Narrative     | **Immutable**  | Historical records of specific events |

### Revision Log (prepend newest first)

```markdown
## Revision Management

- [r3] 2025-01-15T14:30Z — auth update, OAuth2 migration
- [r2] 2025-01-10T09:15Z — rate limit added for security
- [r1] 2025-01-05T11:00Z — initial creation
```

**Rules:** ISO8601 timestamps, concise entry per line, newest first, increment counter.

### Deprecation Strategies

| Strategy       | When to Use                 | Action                                       |
| -------------- | --------------------------- | -------------------------------------------- |
| Supersede      | Better replacement exists   | New artifact + `supersedes` relation         |
| Archive        | Entire domain obsolete      | Move to `__ARCHIVE__/`                       |
| Tag deprecated | Partially relevant          | Add `[deprecated]` observation + revision    |
| Merge          | Overlapping artifacts found | Combine into new artifact, archive originals |

---

## Verification Pattern

Unverified claims follow a specific path to become verified Facts:

```text
1. Unverified claim → create Narrative with [assumption] #unverified
2. Reference or create a verification Procedure
3. Execute verification → create Process Narrative (immutable) with results
4. Update or create Fact via revision → verified_by [[Process Narrative]]
```

**Key rules:**

- Unverified claims are Narratives, never Facts
- Verification execution produces an immutable Process Narrative
- Facts are updated only after a verification trail exists

For detailed verification flow examples with full artifact content,
see @references/extended-artifact-guide.md.

---

## Knowledge Materialization Protocol

**Triggers:** "materialize knowledge" | "document context" | "summarize progress" | "save memory"

**Principle:** Narrative-First — write what happened, then derive structured artifacts.

### Step 1: Synthesize Narrative(s)

Identify storylines in the current context. Separate per story.
Type each as Completed (past events) or Planning (future intent).
Embed `[[future-forward]]` links to seed knowledge gaps.
Mark unverified claims with `[assumption] #unverified`.

### Step 2: Materialize Artifacts

Selectively create Facts, Concepts, and Procedures from the narratives.

**Materialization heuristics (create when):**

- **Central** — direct subject of the request
- **Explanatory** — core recurring concept that needs a definition
- **Actionable** — immediate concrete steps someone could follow
- **Dependency** — artifact A needs artifact B to make sense

**Defer when:**

- Briefly mentioned — create a `[[future-forward]]` link instead
- Tangential or scope-drifting — not part of the core request

**Scope drift guard:** Ask yourself "Am I still answering the original request?"
If the artifact is about a different topic, defer it.

### Step 3: Derive Ontology (when critical mass reached)

Once enough artifacts exist, analyze recurring vocabulary
and formalize key terms as an Ontology artifact.

**Vocabulary governance:** When creating ontology terms, consider scope:

- **Core terms** (reused across many artifacts): `is_a`, `requires`, `produces` —
  stable, high governance, change rarely
- **Domain terms** (specific to a knowledge area): `bio:expresses`, `legal:cites` —
  must map to a core term via `subPropertyOf`
- **Project aliases** (local convenience): team nicknames, local shorthand —
  never canonical, project-scoped and ephemeral

This prevents vocabulary bloat while keeping domain expressiveness.

**Overall flow:** Request → Narrative(s) + {Facts, Concepts, Procedures} → Graph → `[[future-forward]]` as backlog

### Sub-Agent Dispatch for Bulk Materialization

When materializing **3+ artifacts**, dispatch each to a sub-agent
for parallel creation. The master handles Narratives (need full context)
and relation stitching (needs all artifacts).

| Artifact count | Strategy |
| --- | --- |
| 1-2 | Create inline |
| 3-5 | One sub-agent per artifact |
| 6+ | Group by type (2-3 per agent) |

For model selection per artifact type and the full dispatch protocol,
see @references/sub-agent-guide.md.

---

## Unified Artifact Template

```markdown
---
title: [Type] - [Name]
type: [fact|concept|procedure|narrative|ontology]
tags:
  - domain
  - discipline
  - topic
  - #identity-tag
---

## Revision Management

- [r1] YYYY-MM-DDTHH:MM:SSZ — initial creation

---

# [Type] - [Name]

[1-2 sentence definition]

## [Type-Specific Section]

[Content — see type-specific guidance below]

## Observations

- [category] Concise statement about this knowledge #tag

## Relations

- relation_type [[Target Artifact]]
```

**Type-Specific Sections:**

- **Fact:** Evidence section listing verified sources
- **Concept:** Definition section explaining universal properties
- **Procedure:** Objective + numbered Steps
- **Narrative:** Story in past tense (immutable once created)
- **Ontology:** Terms with ids, labels, and definitions

**Standard Relations:**
`implements` `requires` `supports` `illustrates` `is_a`
`derived_from` `verified_by` `supersedes` `superseded_by`
`documents_execution_of` `alternative_to`

For full artifact templates with detailed examples per type,
see @references/extended-artifact-guide.md.

---

## Key Patterns

### Supersession

When replacing an artifact:
create the new artifact with a `supersedes [[Old]]` relation,
and add `superseded_by [[New]]` to the old artifact.

### Future-Forward Links

`[[Artifact Type - Name]]` links to artifacts that don't exist yet.
These are knowledge gap placeholders — a backlog of things to document.
They map what you know you don't know.

---

## Anti-Patterns

```text
✗ Treating unverified claims as Facts
✓ Document claims as Narratives with [assumption], verify first, then create Fact

✗ Editing Narratives after creation (breaks immutability)
✓ Narratives are immutable — create new ones for new events

✗ Creating artifacts without a revision management section
✓ Every artifact starts with [r1] revision entry

✗ Creating artifacts without relations (isolated nodes in the graph)
✓ Every artifact links to at least one other artifact

✗ Over-materializing tangential topics (scope drift)
✓ Defer tangential topics as [[future-forward]] relations

✗ Skipping the verification pattern for factual claims
✓ Unverified claim → Narrative → verify → Fact (always follow the chain)
```

---

## Environment Compatibility

This skill works with any system that can store structured text:

- **Basic-Memory:** Native support (create_note, edit_note, move_note)
- **Obsidian / Markdown files:** Compatible via file operations
- **Claude Code / Cursor / Codex / Gemini CLI:** Create artifacts as project files
- **Kimi / other agents:** Output artifacts as structured text
- **Bare LLM / chat-only:** Output artifact templates in chat for user to save
- **Any structured note system:** Template patterns are format-agnostic

## Formal Basis

The artifact typology and lifecycle have grounding in established theory:

- **Five artifact types:** Map to ACT-R cognitive architecture (Anderson, 1983):
  Fact/Concept = declarative knowledge, Procedure = procedural knowledge,
  Narrative = experiential (SECI Externalization), Ontology = structural.
- **Frame-graph hybrid:** Observations = frame slots (Minsky, 1975);
  Relations = RDF triples (W3C Semantic Web Standards).
- **Complexity mapping:** Artifact types align with Cynefin domains
  (Snowden & Boone, 2007): Facts/Procedures for Simple/Complicated,
  Concepts/Narratives for Complex/Chaotic.
- **Quality model:** 4-metric selection from ISO 25012 (2008),
  with lifecycle gates informed by Signal Detection Theory (Green & Swets, 1966).
- **Verification pattern:** Dual-validation (LLM + human) based on
  hybrid workflow research showing 12% precision improvement (Tsaneva et al., 2025).

See `references/academic-references.md` for full citations and provenance.

## References

See `references/academic-references.md` for full citations and provenance.

Key references: Anderson 1983 (ACT-R), Nonaka & Takeuchi 1995 (SECI),
Minsky 1975 (Frames), Snowden & Boone 2007 (Cynefin).
