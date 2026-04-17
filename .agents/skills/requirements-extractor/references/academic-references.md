# Academic References — requirements-extractor

Supporting literature for the requirements-extractor skill's design decisions.
Loaded on demand — not part of the main SKILL.md context.

---

## Table of Contents

1. [Requirements Engineering Foundations](#requirements-engineering-foundations)
2. [Goal-Oriented Requirements Engineering](#goal-oriented-requirements-engineering)
3. [Applied Category Theory](#applied-category-theory)
4. [Chain of Knowledge and Knowledge Graphs](#chain-of-knowledge-and-knowledge-graphs)
5. [Root Cause Analysis and the "Why?" Recursion](#root-cause-analysis-and-the-why-recursion)
6. [Prompt Engineering Methods](#prompt-engineering-methods)
7. [Skill Formalization](#skill-formalization)
8. [Original Contributions](#original-contributions)

---

## Requirements Engineering Foundations

- Pohl, Klaus.
  *Requirements Engineering: Fundamentals, Principles, and Techniques.*
  Springer, 2010.
  Comprehensive RE textbook. Source for goal-oriented requirements structure.
  The MGPC framework (Mission, Goals, Premises, Constraints) adapts
  Pohl's requirements layering for prompt engineering contexts.

- Wiegers, Karl, and Joy Beatty.
  *Software Requirements.* 3rd ed.
  Microsoft Press, 2013.
  Practical requirements elicitation techniques:
  stakeholder interviews, document analysis, prototyping.
  Informs the bottom-up discovery of implicit requirements.

---

## Goal-Oriented Requirements Engineering

- van Lamsweerde, Axel.
  "Goal-Oriented Requirements Engineering: A Guided Tour."
  *Proceedings of the 5th IEEE International Symposium
  on Requirements Engineering (RE'01)*, pp. 249–262, 2001.
  Foundational survey of goal-oriented RE.
  Goals as first-class requirements objects that decompose
  into sub-goals and operationalizations.
  Grounds the MGPC hierarchy: Mission decomposes into Goals,
  Goals imply Premises and Constraints.

- Dardenne, Anne, Axel van Lamsweerde, and Stephen Fickas.
  "Goal-Directed Requirements Acquisition."
  *Science of Computer Programming*, 20(1–2), 3–50, 1993.
  KAOS goal modeling framework.
  Goal refinement patterns and obstacle analysis.
  Informs the Phase 0 expansion from topics to areas to fields:
  each level refines goals into operationalizable sub-goals.

- Yu, Eric S. K.
  "Towards Modelling and Reasoning Support
  for Early-Phase Requirements Engineering."
  *Proceedings of the 3rd IEEE International Symposium
  on Requirements Engineering (RE'97)*, pp. 226–235, 1997.
  i* (i-star) framework for agent-oriented modeling.
  Intentional dependencies between actors — grounds the distinction
  between Mission (terminal intent) and Goals (instrumental intent).

---

## Applied Category Theory

- Fong, Brendan, and David I. Spivak.
  *An Invitation to Applied Category Theory:
  Seven Sketches in Composability.*
  Cambridge University Press, 2019. arXiv:1803.05316.
  Accessible introduction to category theory for applied domains.
  Provides the formal vocabulary (objects, morphisms, functors,
  natural transformations) used in the ACT formalization
  of requirements engineering in the companion primer.

- Mac Lane, Saunders.
  *Categories for the Working Mathematician.* 2nd ed.
  Springer, 1998. (Original edition 1971.)
  Definitive reference for category theory.
  Functor composition, fixed points, and endofunctor theory —
  formal grounding for the Why-functor W and Challenge functors
  F_G, F_P, F_C defined in the Requirements Engineering Primer.

- Spivak, David I.
  *Category Theory for the Sciences.*
  MIT Press, 2014.
  Category theory applied to databases, knowledge representation,
  and scientific modeling. Provides precedent for using
  functors to map between requirement and solution categories.

---

## Chain of Knowledge and Knowledge Graphs

- Li, Xingxuan, Ruochen Zhao, Yew Ken Chia, Bosheng Ding,
  Shafiq Joty, Soujanya Poria, and Lidong Bing.
  "Chain-of-Knowledge: Grounding Large Language Models
  via Dynamic Knowledge Adapting over Heterogeneous Sources."
  arXiv:2305.13269, 2023.
  Foundation for CoK triple structure (subject, relation, object)
  and graph-based expansion used in Phase 0.
  Dynamic knowledge retrieval across heterogeneous sources
  grounds the multi-level topic→area→field→discipline→domain traversal.

- Pan, Shirui, Linhao Luo, Yufei Wang, Chen Chen,
  Jiapu Wang, and Xindong Wu.
  "Unifying Large Language Models and Knowledge Graphs:
  A Roadmap."
  *IEEE Transactions on Knowledge and Data Engineering*,
  36(7), 3580–3599, 2024. arXiv:2306.08302.
  Survey of LLM–KG integration patterns.
  Grounds the use of knowledge graph triples for requirements
  space expansion and saturation checking.

---

## Root Cause Analysis and the "Why?" Recursion

- Ohno, Taiichi.
  *Toyota Production System:
  Beyond Large-Scale Production.*
  Productivity Press, 1988.
  Origin of the "5 Whys" technique for root cause analysis.
  The recursive "why?" chain in Phase 1 (W-functor)
  adapts this industrial technique for mission discovery,
  continuing until the answer becomes tautological (fixed point).

- Tarski, Alfred.
  "A Lattice-Theoretical Fixpoint Theorem
  and Its Applications."
  *Pacific Journal of Mathematics*, 5(2), 285–309, 1955.
  Fixed-point theorem for monotone functions on lattices.
  Provides the formal grounding for the Mission as a fixed point
  of the Why-functor: W(M) = M.

---

## Prompt Engineering Methods

- Wei, Jason, Xuezhi Wang, Dale Schuurmans,
  Maarten Bosma, Brian Ichter, Fei Xia, Ed Chi,
  Quoc V. Le, and Denny Zhou.
  "Chain-of-Thought Prompting Elicits Reasoning
  in Large Language Models."
  NeurIPS 2022. arXiv:2201.11903.
  Chain-of-Thought reasoning as a foundation for
  structured multi-step inference. The Phase 0→Phase 1
  two-phase process applies CoT-style decomposition
  to requirements analysis.

- Yao, Shunyu, Dian Yu, Jeffrey Zhao, Izhak Shafran,
  Thomas L. Griffiths, Yuan Cao, and Karthik Narasimhan.
  "Tree of Thoughts: Deliberate Problem Solving
  with Large Language Models."
  NeurIPS 2023. arXiv:2305.10601.
  Tree-structured exploration of solution alternatives.
  The L5→L1 expansion hierarchy mirrors ToT's branching
  exploration of thought paths.

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

- **W-functor notation:** Recursive "why?" as an endofunctor
  with Mission as fixed point — inspired by category theory's
  functor concept (Mac Lane, Fong & Spivak) and Toyota's
  5 Whys (Ohno). The specific formalization is original.

- **MGPC as PE framework:** Adapting requirements engineering
  (Pohl, van Lamsweerde) for prompt engineering optimization.
  The four-tuple structure and litmus tests are original.

- **CoK-based requirements saturation:** Using Chain of Knowledge
  triple expansion (Li et al.) with hierarchical abstraction levels
  for systematic requirements discovery. The specific L5→L1
  hierarchy and saturation criteria are original.

- **Two-phase bottom-up then top-down:** Phase 0 broadens
  before Phase 1 narrows — the specific sequencing and
  integration of CoK expansion with MGPC inference is original.
