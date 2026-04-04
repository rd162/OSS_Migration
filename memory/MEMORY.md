# Memory Index

## Active Plans
- [**Semantic Verification Plan**](semantic_verification_plan.md) — Phase 5d (2026-04-05): SME confirmed all generated code incorrect; 15 workstreams (WS-A auth through WS-O ccache); fix every function to 100% PHP semantic equivalence
- [**Coverage Gap Plan**](coverage_gap_plan.md) — Phase 5b/5c (2026-04-05): strict tree-sitter audit 100%; 2 Source errors fixed; all complete
- [**Master Plan**](master_plan.md) — Unified graph-driven migration plan (Phases 1-6), tree-sitter+NetworkX native at every gate
- [Phase 2 Detail](phase2_plan_2026-04-04.md) — 4 batches, dependency-first (Condorcet winner)
- [Phase 3 Detail](phase3_plan_2026-04-04.md) — 9 serial batches with graph-level annotations (Condorcet winner)
- [Phase 4 Detail](phase4_plan_2026-04-04.md) — 5 batches, 17 API ops
- [Phase 5 Detail](phase5_plan_2026-04-04.md) — 7 batches, Hook-Community Topological Drain (Condorcet winner)
- [Phase 6 Detail](phase6_plan_2026-04-04.md) — 6 batches, CI-first gate-driven (Condorcet winner). Key: Phase 5 DONE/0 missing hooks; exact function audit 100% (2026-04-05)

## Session History
- [Session 2026-04-03](session_2026-04-03.md) — Spec-kit built, P0+P1 ADRs accepted, Phase 1a complete
- [Session 2026-04-04](session_2026-04-04.md) — Phases 1b-4 complete, graph analysis built + enhanced, specs updated
- [Session 2026-04-05](session_2026-04-05.md) — Strict tree-sitter audit; 2 Source errors fixed; semantic verification plan written (SME found all code incorrect)

## Rules
- [Consistency Rule](feedback_consistency_rule.md) — MANDATORY: update ALL referencing locations when any status/decision changes
- [Spec Consultation](feedback_spec_consultation.md) — MANDATORY: read relevant specs/ before planning any phase

## Rework (Phase 5 prerequisite)
- [Rework Execution](rework_execution.md) — Concrete per-phase graph validation: 4 real gaps + validator tuning

## Superseded (kept for audit trail)
- [Rework Plan](rework_plan.md) — Superseded by master_plan.md (graph approach now native, not bolt-on)
- [Next Session Plan](next_session_plan.md) — Superseded by master_plan.md §Current Priority
