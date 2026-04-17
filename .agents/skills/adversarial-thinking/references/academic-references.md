# Academic References — adversarial-thinking

Supporting literature for the adversarial-thinking skill's design decisions.
Loaded on demand — not part of the main SKILL.md context.

---

## Table of Contents

1. [Condorcet and Ranked Voting](#condorcet-and-ranked-voting)
2. [Self-Correction and Self-Play Limitations](#self-correction-and-self-play-limitations)
3. [Sycophancy and Multi-Agent Collapse](#sycophancy-and-multi-agent-collapse)
4. [Inverse Specification and Reward Signal Design](#inverse-specification-and-reward-signal-design)
5. [Skill Formalization](#skill-formalization)

---

## Condorcet and Ranked Voting

- Zhao, Xiutian, Ke Wang, and Wei Peng.
  "An Electoral Approach to Diversify LLM-based
  Multi-Agent Collective Decision-Making."
  EMNLP 2024. arXiv:2410.15168.
  Condorcet and ordinal voting for LLM agent decisions;
  surveys 52 multi-agent systems and identifies heavy reliance
  on dictatorial and plurality voting as a diversity failure.

- Wang, Weiqin, Yile Wang, and Hui Huang.
  "Ranked Voting based Self-Consistency of Large Language Models."
  Findings of ACL 2025. arXiv:2505.10772.
  Ranked voting (instant-runoff, Borda count, MRR) improves
  chain-of-thought reasoning over majority-vote self-consistency.

- Lanctot, Marc, Kate Larson, Michael Kaisers, Quentin Berthet,
  Ian Gemp, Manfred Diaz, Roberto-Rafael Maura-Rivero,
  Yoram Bachrach, Anna Koop, and Doina Precup.
  "Soft Condorcet Optimization for Ranking of General Agents."
  AAMAS 2025. arXiv:2411.00119.
  Condorcet-optimal ranking under noisy pairwise comparisons;
  robust to >40% missing preference data.

---

## Self-Correction and Self-Play Limitations

- Madaan, Aman, Niket Tandon, Prakhar Gupta, Skyler Hallinan,
  Luyu Gao, Sarah Wiegreffe, Uri Alon, et al.
  "Self-Refine: Iterative Refinement with Self-Feedback."
  NeurIPS 2023. arXiv:2303.17651.
  Foundation for the iterative critique-and-revise loop;
  also documents near-zero self-correction on math reasoning
  (94% "looks good" rate) — motivates external critique isolation.

- Liang, Tian, Zhiwei He, Wenxiang Jiao, Xing Wang, Yan Wang,
  Rui Wang, Yujiu Yang, Shuming Shi, and Zhaopeng Tu.
  "Encouraging Divergent Thinking in Large Language Models
  through Multi-Agent Debate."
  EMNLP 2024. arXiv:2305.19118.
  Coins Degeneration-of-Thought (DoT) — motivation for isolated
  adversarial agents over single-model self-reflection.

- Huang, Jie, Xinyun Chen, Swaroop Mishra, Huaixiu Steven Zheng,
  Adams Wei Yu, Xinying Song, and Denny Zhou.
  "Large Language Models Cannot Self-Correct Reasoning Yet."
  ICLR 2024. arXiv:2310.01798.
  Definitive evidence that intrinsic self-correction degrades accuracy —
  foundational justification for the self-play prohibition.

- Kamoi, Ryo, Yusen Zhang, Nan Zhang, Jiawei Han, and Rui Zhang.
  "When Can LLMs Actually Correct Their Own Mistakes?
  A Critical Survey of Self-Correction of LLMs."
  Transactions of the ACL, vol. 12, pp. 1417–1440, 2024.
  Survey establishing that self-correction works only when
  verification is substantially easier than generation —
  grounds the knowledge-saturation requirement in Phase 2.

---

## Sycophancy and Multi-Agent Collapse

- Sharma, Mrinank, Meg Tong, Tomasz Korbak, David Duvenaud,
  Amanda Askell, Samuel R. Bowman, et al.
  "Towards Understanding Sycophancy in Language Models."
  ICLR 2024. arXiv:2310.13548.
  Defines answer/feedback/mimicry sycophancy typologies;
  shows preference model complicity in rewarding sycophancy.
  Grounds the inverted compliance framing in Phase 2.

- Kim, Sungwon, and Daniel Khashabi.
  "Challenging the Evaluator: LLM Sycophancy Under User Rebuttal."
  Findings of EMNLP 2025. arXiv:2509.16533.
  Demonstrates sequential vs. simultaneous evaluation paradox —
  grounds agent isolation and Condorcet pairwise design.

- Yao, Binwei, Chao Shang, Wanyu Du, Jianfeng He, Ruixue Lian,
  Yi Zhang, Hang Su, Sandesh Swamy, and Yanjun Qi.
  "Peacemaker or Troublemaker: How Sycophancy Shapes
  Multi-Agent Debate."
  arXiv:2509.23055, 2025.
  Demonstrates that inter-agent sycophancy collapses debates
  into premature consensus, yielding lower accuracy than
  single-agent baselines — grounds the CRITIQUE-SOFTENING
  detection mechanism.

- Watson, Nell, and Ali Hessami.
  "Psychopathia Machinalis: A Nosological Framework
  for Understanding Pathologies in Advanced Artificial Intelligence."
  Electronics 14(16), 3162, 2025. doi:10.3390/electronics14163162.
  Inverse Reward Internalization (Syndrome 5.4) and
  hidden intent fallacy — grounds the inverted compliance
  framing mechanism and SOFTENING detection.

---

## Inverse Specification and Reward Signal Design

- Kumar, Karthik Ragunath Ananda, and Subrahmanyam Arunachalam.
  "Learning to Present: Inverse Specification Rewards
  for Agentic Slide Generation."
  arXiv:2603.16839, 2026.
  Inverse specification reward — recoverability of intent
  from output as a quality proxy. Grounds Phase 2.5
  inverse specification recovery step.

---

## Applied Category Theory and Requirements Formalization

- Fong, Brendan, and David I. Spivak.
  *An Invitation to Applied Category Theory:
  Seven Sketches in Composability.*
  Cambridge University Press, 2019. arXiv:1803.05316.
  Formal vocabulary (objects, morphisms, functors)
  for the Requirements Category and Solution Functor F: Req → Sol.
  Phase 0 requirements inference maps between these categories;
  Phase 1 candidate generation applies the Solution Functor
  to produce divergent branches.

- Pohl, Klaus.
  *Requirements Engineering: Fundamentals, Principles,
  and Techniques.*
  Springer, 2010.
  Source for goal-oriented requirements structure.
  The MGPC framework (Mission, Goals, Premises, Constraints)
  used in Phase 0.2 adapts Pohl's requirements layering.

- van Lamsweerde, Axel.
  "Goal-Oriented Requirements Engineering: A Guided Tour."
  *Proceedings of the 5th IEEE International Symposium
  on Requirements Engineering (RE'01)*, pp. 249–262, 2001.
  Goal decomposition and obstacle analysis.
  Informs the enriched requirements registry: goals decompose
  into assessment criteria for Condorcet voters.

- Tarski, Alfred.
  "A Lattice-Theoretical Fixpoint Theorem
  and Its Applications."
  *Pacific Journal of Mathematics*, 5(2), 285–309, 1955.
  Fixed-point theory grounding convergence detection in Phase 2:
  when the critique-and-revise loop reaches a fixed point
  (defense or output stabilization), further iteration is circular.

---

## Cognitive Architecture

- Anderson, John R.
  *The Architecture of Cognition.*
  Harvard University Press, 1983.
  ACT-R cognitive architecture: declarative vs. procedural knowledge.
  Grounds the critique/author separation:
  CRITIQUE operates on declarative assessment (compliance evaluation),
  AUTHOR applies procedural revision (solution improvement).
  Isolation prevents cross-contamination of cognitive modes.

---

## Skill Formalization

- Jiang et al.,
  "SoK: Agentic Skills — Beyond Tool Use in LLM Agents"
  (arXiv:2602.20867v1, 2026).
  Skill formalization `S = (C, π, T, R)`:
  C = applicability condition,
  π = executable policy,
  T = termination condition,
  R = reusable callable interface.
  Workflow enforcement (Pattern-3): hard-gated methodology compliance.
  Hierarchical composition: policy π selecting child skill `s ∈ Σ`.
