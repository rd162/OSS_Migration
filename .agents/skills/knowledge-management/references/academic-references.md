# Academic References — knowledge-management

Supporting literature for the knowledge-management skill's design decisions.
Loaded on demand — not part of the main SKILL.md context.

---

## Table of Contents

1. [Cognitive Architecture](#cognitive-architecture)
2. [Knowledge Representation](#knowledge-representation)
3. [Tacit-Explicit Knowledge Conversion](#tacit-explicit-knowledge-conversion)
4. [Complexity and Sense-Making](#complexity-and-sense-making)
5. [Quality Standards and Measurement](#quality-standards-and-measurement)
6. [Semantic Web and Knowledge Graphs](#semantic-web-and-knowledge-graphs)
7. [Verification and Reliability](#verification-and-reliability)
8. [Skill Formalization](#skill-formalization)
9. [Original Contributions](#original-contributions)

---

## Cognitive Architecture

- Anderson, John R.
  *The Architecture of Cognition.*
  Harvard University Press, 1983.
  ACT-R cognitive architecture: foundational distinction
  between declarative knowledge (facts, concepts)
  and procedural knowledge (skills, procedures).
  Directly informs the artifact type classification:
  Fact and Concept = declarative; Procedure = procedural.

- Anderson, John R., and Christian Lebiere.
  *The Atomic Components of Thought.*
  Lawrence Erlbaum Associates, 1998.
  Refined ACT-R theory with production rules and chunk types.
  Grounds the observation categories: each observation slot
  maps to a declarative chunk type in ACT-R's memory system.

- Newell, Allen, and Herbert A. Simon.
  *Human Problem Solving.*
  Prentice-Hall, 1972.
  Foundation for knowledge representation:
  declarative, procedural, and experiential memory types.
  Grounds the five-artifact typology and the principle
  that knowledge artifacts must mirror human cognitive structures.

---

## Knowledge Representation

- Minsky, Marvin.
  "A Framework for Representing Knowledge."
  In P. H. Winston (Ed.), *The Psychology of Computer Vision*,
  pp. 211–277. McGraw-Hill, 1975.
  Frame-based knowledge representation: structured containers
  with slots, expectations, and procedural attachments.
  Directly implemented in the frame-graph hybrid architecture:
  Observations = frame slots; Relations = procedural attachments.

- Sowa, John F.
  *Knowledge Representation: Logical, Philosophical,
  and Computational Foundations.*
  Brooks/Cole, 2000.
  Comprehensive treatment of conceptual graphs, ontologies,
  and formal knowledge representation.
  Grounds the relation type system and ontology artifact design.

---

## Tacit-Explicit Knowledge Conversion

- Nonaka, Ikujiro, and Hirotaka Takeuchi.
  *The Knowledge-Creating Company: How Japanese Companies
  Create the Dynamics of Innovation.*
  Oxford University Press, 1995.
  SECI knowledge conversion model
  (Socialization, Externalization, Combination, Internalization).
  Grounds the narrative-first workflow:
  Narrative artifacts implement Externalization (tacit → explicit),
  while artifact derivation implements Combination (explicit → explicit).

- Polanyi, Michael.
  *The Tacit Dimension.*
  Routledge & Kegan Paul, 1966.
  "We can know more than we can tell."
  Foundational work on tacit knowledge — the knowledge
  that resists codification. Grounds the design decision
  to distinguish Narrative (experiential, tacit-sourced)
  from Procedure (explicit, codifiable).

---

## Complexity and Sense-Making

- Snowden, David J., and Mary E. Boone.
  "A Leader's Framework for Decision Making."
  *Harvard Business Review*, 85(11), 68–76, 2007.
  Cynefin framework: Simple, Complicated, Complex, Chaotic domains.
  Grounds the complexity domain mapping of artifact types:
  Facts/Procedures for Simple/Complicated;
  Concepts/Narratives for Complex/Chaotic.

- Kurtz, Cynthia F., and David J. Snowden.
  "The New Dynamics of Strategy:
  Sense-Making in a Complex and Complicated World."
  *IBM Systems Journal*, 42(3), 462–483, 2003.
  Extended treatment of complexity-aware knowledge management.
  Informs the principle that Narratives are essential
  for sense-making in chaotic/complex domains where
  procedural approaches fail.

---

## Quality Standards and Measurement

- ISO/IEC 25012:2008.
  *Software engineering — Software product Quality Requirements
  and Evaluation (SQuaRE) — Data quality model.*
  International Organization for Standardization.
  Defines 15 data quality characteristics.
  The 4-metric quality model (Accuracy, Completeness,
  Consistency, Timeliness) is a focused selection
  from this standard, chosen for computational efficiency.

- Cohen, Jacob.
  "A Coefficient of Agreement for Nominal Scales."
  *Educational and Psychological Measurement*, 20(1), 37–46, 1960.
  Cohen's Kappa statistic for inter-rater reliability.
  Grounds the quality assessment reliability requirement:
  kappa >= 0.8 for deployment of automated quality gates.

- Green, David M., and John A. Swets.
  *Signal Detection Theory and Psychophysics.*
  Wiley, 1966.
  Signal detection theory: balancing precision and recall
  in threshold-based decisions.
  Grounds the quality gate design: lifecycle transitions
  use threshold-based rules that balance Type I
  (accepting poor quality) and Type II (rejecting good quality) errors.

---

## Semantic Web and Knowledge Graphs

- W3C.
  *RDF 1.1 Concepts and Abstract Syntax.*
  World Wide Web Consortium, 2014.
  https://www.w3.org/TR/rdf11-concepts/
  Graph-based data model using subject-predicate-object triples.
  Grounds the Relations section of every artifact:
  each relation is an RDF triple connecting knowledge nodes.

- W3C.
  *OWL 2 Web Ontology Language Overview.* 2nd ed.
  World Wide Web Consortium, 2012.
  https://www.w3.org/TR/owl2-overview/
  Formal semantics for ontology definition.
  Grounds the Ontology artifact type and the
  three-tier vocabulary governance model.

- Pan, Shirui, Linhao Luo, Yufei Wang, Chen Chen,
  Jiapu Wang, and Xindong Wu.
  "Unifying Large Language Models and Knowledge Graphs:
  A Roadmap."
  *IEEE Transactions on Knowledge and Data Engineering*,
  36(7), 3580–3599, 2024. arXiv:2306.08302.
  Survey of LLM-KG integration patterns.
  Grounds the use of LLM-powered quality assessment
  for knowledge graph artifacts.

---

## Verification and Reliability

- Tsaneva, S., et al.
  "Knowledge Graph Validation by Integrating LLMs
  and Human-in-the-Loop."
  *Information Processing & Management*, 62(5), 104145, 2025.
  12% precision improvement with hybrid human-AI verification.
  Grounds the dual-validation verification pattern:
  LLM assessment + human spot-check.

---

## Skill Formalization

- Jiang et al.
  "SoK: Agentic Skills — Beyond Tool Use in LLM Agents."
  arXiv:2602.20867v1, 2026.
  Skill formalization S = (C, pi, T, R):
  C = applicability condition,
  pi = executable policy,
  T = termination condition,
  R = reusable callable interface.

---

## Original Contributions

The following elements are original to this skill ecosystem,
built on the academic foundations listed above:

- **Five-artifact typology:** Fact, Concept, Procedure, Narrative,
  Ontology — synthesizing ACT-R (Anderson), Frame Theory (Minsky),
  SECI (Nonaka & Takeuchi), and Cynefin (Snowden).
  The specific mapping and litmus tests are original.

- **Narrative-first materialization:** Always start with Narrative,
  then derive Facts/Concepts/Procedures — implementing SECI's
  Externalization phase as a mandatory first step.
  The specific protocol and scope-drift guards are original.

- **Future-forward relations as knowledge gap mapping:**
  Links to non-existent artifacts as deliberate gap placeholders.
  Builds on RDF's open-world assumption (W3C) and graph theory.
  The specific use as a knowledge backlog mechanism is original.

- **Verification pattern chain:** Unverified claim → Narrative
  → verify → Fact — a structured path from tacit assumption
  to verified knowledge. Builds on Signal Detection Theory (Green & Swets)
  and ISO 25012 quality gates. The specific chain design is original.

- **Frame-graph hybrid architecture:** Combining Minsky's frames
  (Observations as slots) with RDF graph edges (Relations as triples).
  The specific integration pattern is original.
