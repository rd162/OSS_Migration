# Sub-Agent Guide — knowledge-management

Patterns for parallelizing artifact materialization via sub-agents,
with model selection guidance.
Loaded on demand when materializing 3+ artifacts.

---

## Table of Contents

1. [When to Use Sub-Agents](#when-to-use-sub-agents)
2. [Dispatch Pattern](#dispatch-pattern)
3. [Model Selection](#model-selection)
4. [Relation Stitching](#relation-stitching)

---

## When to Use Sub-Agents

Sub-agents are beneficial when materializing **3+ independent artifacts**
from a knowledge materialization request.

| Artifact count | Strategy |
| --- | --- |
| 1-2 | Create inline (sub-agent overhead not justified) |
| 3-5 | One sub-agent per artifact (parallel creation) |
| 6+ | Group by type or domain (2-3 artifacts per agent) |

**Decision gate:**

```text
Materialization request →
  Step 1: Synthesize Narrative(s) in master context (always inline)
  Step 2: Count artifacts to materialize from narratives
    1-2 artifacts → create inline
    3+  artifacts → sub-agent available?
      YES → fan-out: one agent per artifact (or group)
      NO  → create sequentially in master context
  Step 3: Derive relations in master context (always inline)
```

**Why master handles Narratives and Relations:**
- Narratives require full conversation context to synthesize storylines
- Relations require seeing ALL artifacts to create cross-links
- Artifact creation (Facts, Concepts, Procedures) is independent per artifact

---

## Dispatch Pattern

```text
FOR EACH artifact to materialize:
  spawn_agent(
    label = "[Type] - [Name]"
    message = "Create this knowledge artifact using the template below.

      TYPE: [fact|concept|procedure|ontology]
      NAME: [artifact name]
      CONTEXT: [relevant excerpt from narrative(s)]
      TEMPLATE: [unified artifact template from SKILL.md]

      Requirements:
      - Follow the template exactly (frontmatter, revision management, observations, relations)
      - Use [category] observation tags appropriate to the content
      - Include [[future-forward]] links for knowledge gaps you identify
      - Leave the Relations section with placeholders: the master will stitch relations after all artifacts are created
      - Start revision at [r1] with current ISO8601 timestamp

      Return the complete artifact in markdown."
  )
→ collect all artifacts
→ master stitches Relations across all artifacts
→ master creates Ontology if critical mass reached (Step 3)
```

---

## Model Selection

Different artifact types have different cognitive demands.

| Artifact Type | Cognitive Demand | Model Tier | Rationale |
| --- | --- | --- | --- |
| **Fact** | Low-moderate | Fast (sonnet-class) | Structured extraction from verified evidence; template-driven |
| **Procedure** | Moderate | Fast (sonnet-class) | Step sequencing is well-structured; benefits from clarity not depth |
| **Concept** | High | Strongest (opus-class) | Defining universal properties requires deep domain understanding |
| **Narrative** | Highest | Strongest (opus-class) | Synthesizing storylines from context requires nuanced reasoning |
| **Ontology** | High | Strongest (opus-class) | Vocabulary governance and term relationships need careful judgment |
| **Master (relations)** | High | Strongest (opus-class) | Cross-artifact relation stitching requires seeing the full graph |

**When model selection is unavailable:**
Use the default model for all agents. The parallelism benefit alone
(creating 5 artifacts simultaneously vs. sequentially) justifies
sub-agent dispatch even without model differentiation.

**Budget-aware strategy:**
- **Tight budget:** Create all artifacts inline (skip sub-agents)
- **Standard:** Sub-agents for Facts and Procedures (fast model),
  inline for Concepts and Narratives (strongest model)
- **Generous:** Sub-agents for all artifacts with appropriate model tiers

---

## Relation Stitching

After all sub-agents return their artifacts, the master:

1. **Collects** all artifacts with their placeholder Relations sections
2. **Analyzes** cross-artifact dependencies and connections
3. **Fills** Relations sections using standard relation types:
   `implements` `requires` `supports` `illustrates` `is_a`
   `derived_from` `verified_by` `supersedes` `alternative_to`
4. **Adds** `[[future-forward]]` links for artifacts referenced but not yet created
5. **Checks** that every artifact has at least one relation (no isolated nodes)

This two-pass approach (create artifacts → stitch relations) ensures
that relations reflect the actual artifact content rather than
being guessed at creation time.
