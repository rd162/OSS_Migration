# Academic References — deep-research-t1

Supporting literature for the deep-research-t1 skill's design decisions.
Loaded on demand — not part of the main SKILL.md context.

---

## Table of Contents

1. [Chain of Knowledge and Knowledge Graphs](#chain-of-knowledge-and-knowledge-graphs)
2. [Agentic Search and Reasoning](#agentic-search-and-reasoning)
3. [Complexity Frameworks](#complexity-frameworks)
4. [Quality Standards and Source Tiering](#quality-standards-and-source-tiering)
5. [Signal Detection Theory](#signal-detection-theory)
6. [Fixed-Point Theory and Saturation](#fixed-point-theory-and-saturation)
7. [Knowledge Conversion (SECI)](#knowledge-conversion-seci)
8. [Knowledge Representation](#knowledge-representation)
9. [Applied Category Theory](#applied-category-theory)
10. [Prompt Engineering Methods](#prompt-engineering-methods)
11. [Skill Formalization](#skill-formalization)
12. [Original Contributions](#original-contributions)

---

## Chain of Knowledge and Knowledge Graphs

- Li, Xingxuan, Ruochen Zhao, Yew Ken Chia, Bosheng Ding,
  Shafiq Joty, Soujanya Poria, and Lidong Bing.
  "Chain-of-Knowledge: Grounding Large Language Models
  via Dynamic Knowledge Adapting over Heterogeneous Sources."
  arXiv:2305.13269, 2023.
  Foundation for CoK triple structure (subject, relation, object)
  and graph-based expansion. Dynamic knowledge retrieval across
  heterogeneous sources grounds the forward-fill pattern
  and multi-level CoK expansion (L0→L4).

- Pan, Shirui, Linhao Luo, Yufei Wang, Chen Chen,
  Jiapu Wang, and Xindong Wu.
  "Unifying Large Language Models and Knowledge Graphs:
  A Roadmap."
  *IEEE Transactions on Knowledge and Data Engineering*,
  36(7), 3580–3599, 2024. arXiv:2306.08302.
  Survey of LLM–KG integration patterns.
  Grounds the use of knowledge graph triples for
  knowledge space expansion and saturation checking.

---

## Agentic Search and Reasoning

- Xu, Jiatong, Jinzheng He, Haoran Que, Chaoyun Zhang,
  Xinting Huang, Xin Liu, Yangyu Huang, Tao Qin, and Tie-Yan Liu.
  "Search-o1: Agentic Search-Enhanced Large Reasoning Models."
  arXiv:2501.05366, 2025.
  Agentic search integration: interleaving search actions
  within reasoning chains. Grounds the Δ1-Δ7 protocol's
  integration of search execution within structured reasoning,
  and the principle that search should be embedded in
  the reasoning process rather than run as a separate pre-step.

- Nakano, Reiichiro, Jacob Hilton, Suchir Balaji,
  Jeff Wu, Long Ouyang, Christina Kim, et al.
  "WebGPT: Browser-Assisted Question-Answering
  with Human Feedback."
  arXiv:2112.09332, 2021.
  Early work on LLM-driven web search for question answering.
  Establishes the pattern of training models to search,
  navigate, and synthesize web content — foundational
  to the skill's web search protocol.

---

## Complexity Frameworks

- Snowden, David J., and Mary E. Boone.
  "A Leader's Framework for Decision Making."
  *Harvard Business Review*, November 2007.
  Cynefin complexity framework: Simple, Complicated, Complex, Chaotic.
  Grounds the complexity-informed research depth mapping:
  Simple domains (clear cause-effect) need shallow CoK (L0-L2);
  Complex domains (emergent patterns) need deep CoK (L0-L4);
  Chaotic domains (high-stakes, no clear patterns) need
  maximum depth plus forward-consequence fills.

---

## Quality Standards and Source Tiering

- ISO/IEC 25012:2008.
  "Software Engineering — Software Product Quality Requirements
  and Evaluation (SQuaRE) — Data Quality Model."
  International Organization for Standardization, 2008.
  Defines 15 data quality characteristics.
  The T1-T4 source tiering system maps to the Accuracy dimension:
  T1 (peer-reviewed) = highest inherent accuracy,
  T4 (unverified) = lowest. Tier-weighted conflict resolution
  operationalizes ISO 25012's accuracy assessment.

- Tsaneva, Sonia, Kenzie Doyle, Michele Catasta,
  and Christopher Potts.
  "Improving Automated Knowledge Graph Construction
  with LLM-Guided Fact Verification."
  arXiv:2501.02618, 2025.
  Hybrid human-AI workflows improve precision by 12%
  in knowledge graph fact verification.
  Grounds the dual-validation approach: LLM verification
  of source claims combined with tier-based human trust.

---

## Signal Detection Theory

- Green, David M., and John A. Swets.
  *Signal Detection Theory and Psychophysics.*
  Wiley, 1966. Reprinted Krieger, 1974.
  Foundation of threshold-based decision making under uncertainty.
  Grounds the high-stakes domain detection heuristic:
  false negatives (missing a high-stakes domain) have
  catastrophic cost (harm, death, imprisonment), while
  false positives (over-researching a safe domain)
  cost only extra tokens. This asymmetric cost structure
  makes low detection thresholds rational —
  the "when uncertain, escalate" principle follows directly
  from SDT's cost-matrix optimization.

---

## Fixed-Point Theory and Saturation

- Tarski, Alfred.
  "A Lattice-Theoretical Fixpoint Theorem
  and Its Applications."
  *Pacific Journal of Mathematics*, 5(2), 285–309, 1955.
  Fixed-point theory for monotone functions on lattices.
  CoK saturation is formally a fixed-point detection:
  when expansion F^n(KG) ≈ F^(n-1)(KG), further iteration
  produces no new knowledge — the graph has reached
  a fixed point. The stop criteria (relevance < 0.3,
  circular references, requirements covered) are
  observable proxies for this fixed-point condition.

- Kleene, Stephen Cole.
  *Introduction to Metamathematics.*
  North-Holland, 1952.
  Iterative approximation to fixed points via ascending chains.
  The L0→L1→L2→...→L4 expansion is an ascending chain
  in the knowledge graph lattice; saturation occurs when
  the chain stabilizes (the least fixed point is reached).

---

## Knowledge Conversion (SECI)

- Nonaka, Ikujiro, and Hirotaka Takeuchi.
  *The Knowledge-Creating Company:
  How Japanese Companies Create the Dynamics of Innovation.*
  Oxford University Press, 1995.
  SECI model: Socialization, Externalization, Combination,
  Internalization. Two phases of the skill implement SECI:
  Δ4 (Organize) implements Combination — systematically combining
  explicit knowledge from multiple sources into structured findings.
  File Output mode implements Externalization — converting
  research findings into persistent structured artifacts
  (markdown playbooks) for organizational knowledge capture.

- Polanyi, Michael.
  *The Tacit Dimension.*
  Routledge & Kegan Paul, 1966.
  Foundation for tacit/explicit knowledge distinction.
  The skill's source hierarchy (local docs → web search)
  traverses from tacit project knowledge to explicit
  external knowledge, mirroring Polanyi's knowledge spectrum.

---

## Knowledge Representation

- Minsky, Marvin.
  "A Framework for Representing Knowledge."
  In *The Psychology of Computer Vision*,
  ed. Patrick H. Winston, 211–277. McGraw-Hill, 1975.
  Frame-based knowledge representation.
  The Δ4 output structure (SOURCES, CONSENSUS, CONTRADICTIONS, GAPS)
  is a frame with named slots for organizing research findings —
  each slot captures a different aspect of the knowledge state.

---

## Applied Category Theory

- Fong, Brendan, and David I. Spivak.
  *An Invitation to Applied Category Theory:
  Seven Sketches in Composability.*
  Cambridge University Press, 2019. arXiv:1803.05316.
  Formal vocabulary (objects, morphisms, functors)
  for the CoK expansion as a functor from Topics to Knowledge Graphs.
  The saturation predicate S: KG × Req → Bool is a natural
  transformation detecting when the functor has reached
  its fixed point.

---

## Prompt Engineering Methods

- Wei, Jason, Xuezhi Wang, Dale Schuurmans,
  Maarten Bosma, Brian Ichter, Fei Xia, Ed Chi,
  Quoc V. Le, and Denny Zhou.
  "Chain-of-Thought Prompting Elicits Reasoning
  in Large Language Models."
  NeurIPS 2022. arXiv:2201.11903.
  Chain-of-Thought reasoning as foundation for structured
  multi-step inference. The Δ1-Δ7 protocol applies CoT-style
  decomposition to research methodology.

- Yao, Shunyu, Dian Yu, Jeffrey Zhao, Izhak Shafran,
  Thomas L. Griffiths, Yuan Cao, and Karthik Narasimhan.
  "Tree of Thoughts: Deliberate Problem Solving
  with Large Language Models."
  NeurIPS 2023. arXiv:2305.10601.
  Tree-structured exploration of alternatives.
  The sub-agent fan-out pattern mirrors ToT's parallel
  exploration of thought branches — each sub-agent explores
  one research subject independently before synthesis.

---

## Skill Formalization

- Jiang et al.
  "SoK: Agentic Skills — Beyond Tool Use in LLM Agents."
  arXiv:2602.20867v1, 2026.
  Skill formalization S = (C, π, T, R):
  C = applicability condition,
  π = executable policy,
  T = termination condition,
  R = reusable callable interface.
  Progressive disclosure: metadata (name + description)
  always in context; SKILL.md body loaded on trigger;
  references loaded on demand.

---

## Original Contributions

The following elements are original to this skill ecosystem,
built on the academic foundations listed above:

- **Δ1-Δ7 web search protocol:** Structured seven-step
  research methodology from tool discovery through validated output.
  Synthesizes agentic search (Xu et al.) with CoK expansion
  (Li et al.) and source tiering (ISO 25012 Accuracy).

- **Forward-consequence CoK:** Extension of standard CoK
  forward-fill to include consequence, contraindication,
  and supersession triples for high-stakes domains.
  Standard CoK discovers what IS; forward-consequence
  discovers what COULD GO WRONG.

- **Complexity-informed research depth:** Mapping Cynefin
  domains (Snowden & Boone) to CoK expansion depth
  and research tool selection. Simple → shallow,
  Complex → deep, Chaotic/High-Stakes → maximum + consequences.

- **SDT-grounded escalation:** High-stakes detection threshold
  set low because the cost matrix is asymmetric
  (Green & Swets): false negative = catastrophic,
  false positive = token cost only.

- **Sub-agent context engineering:** Fan-out pattern
  where raw web content stays in sub-agent contexts,
  master receives only synthesized reports —
  70-85% context reduction while preserving research depth.

- **Source tier conflict resolution:** Tier-weighted recency
  ranking for contradictions, with explicit exposure
  rather than silent resolution. Operationalizes
  ISO 25012 Accuracy across heterogeneous sources.
