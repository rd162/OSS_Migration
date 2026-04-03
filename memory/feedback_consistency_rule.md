---
name: feedback_consistency_rule
description: MANDATORY — when any status/decision changes, update ALL locations that reference it in the same commit
type: feedback
---

When accepting ADRs, completing phases, or changing any tracked status, update ALL referencing locations in the same pass — not just the primary documents.

**Why:** This pattern has failed TWICE now:
1. **P0 ADR acceptance** — sub-agents updated ADR files and AGENTS.md but left the charter's Solution Space table saying "preliminary recommendations... pending acceptance", the Traceability Matrix showing "Not started" for completed items, and "SHA1-to-bcrypt" instead of the accepted "argon2id".
2. **P1 ADR acceptance** — adversarial-thinking pipeline updated ADR files, AGENTS.md, docs/decisions/README.md, and memory, but skipped `specs/00-project-charter.md` entirely (Solution Space, Traceability Matrix, Cross-Reference tables) and skipped checking `specs/10-migration-dimensions.md`.

**How to apply:**
- Before finishing ANY status-changing task, run through the checklist in AGENTS.md Rule 16.
- When using sub-agent pipelines (adversarial-thinking, adversarial-self-refine), the MASTER must reconcile ALL locations after agents return — sub-agents don't have the full checklist context.
- The charter (`specs/00-project-charter.md`) is the most commonly missed file because it has THREE separate tables that track ADR status (Solution Space, Traceability Matrix, Cross-Reference).
- Never consider ADR acceptance "done" until the charter tables match.
