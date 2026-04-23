# ADR Template (MADR 4.0)

Use this exact structure for every Architecture Decision Record.

## File Naming

`docs/decisions/NNNN-verb-noun.md` — numbers are sequential, never reused.

## Template

```markdown
---
status: proposed | accepted | deprecated | superseded by [NNNN]
date: YYYY-MM-DD
decision_makers: [list]
consulted: [list]
informed: [list]
---

# NNNN — Title as Present-Tense Verb Phrase

## Context and Problem Statement

Why this decision is needed. Reference the specific specs, dimensions, or constraints
that motivate it. Include links to relevant spec files.

## Decision Drivers

- Driver 1 (link to constraint or goal)
- Driver 2

## Considered Options

1. **Option A** — one-line summary
2. **Option B** — one-line summary
3. **Option C** — one-line summary

## Trade-off Analysis

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Criterion 1 | assessment | assessment | assessment |
| Criterion 2 | assessment | assessment | assessment |
| ... | ... | ... | ... |

## Decision

Chosen: **Option X**, because [rationale referencing trade-off analysis].

## Consequences

### Positive
- Consequence 1

### Negative
- Consequence 1

## Confirmation

How to verify this decision is implemented in code. Include specific file paths,
test commands, or validation queries.
```

## Priority Levels

- **P0 (blocks all work)**: Must be decided before any implementation begins.
  Examples: modernization flow variant, target framework/language, database engine.

- **P1 (blocks specific phases)**: Must be decided before the phase that needs it.
  Examples: ORM strategy, auth mechanism, background worker architecture.

- **P2 (deferrable)**: Can be decided when needed, doesn't block other work.
  Examples: logging strategy, i18n approach, monitoring setup.

## Adversarial Evaluation Protocol

For P0 and P1 decisions:

1. **Research**: Use web research to validate each option's claims
2. **3 Candidates**: Generate proposals with different trade-off priorities
   - Candidate A: optimizes for time-to-market
   - Candidate B: optimizes for technical excellence
   - Candidate C: optimizes for behavioral fidelity
3. **Stress test**: Isolated critic agent attacks each candidate
4. **Convergence check**: If all converge post-critique → clear answer
5. **Pairwise voting**: If divergent → Condorcet comparison

## Consistency Rule

When accepting an ADR, update ALL of these in the same commit:
- [ ] The ADR file (status, date, decision section)
- [ ] `AGENTS.md` — decision table
- [ ] `docs/decisions/README.md` — decision index
- [ ] `specs/architecture/00-project-charter.md` — solution space + RTM
- [ ] `specs/architecture/NN-modernization-dimensions.md` — recommendation matrix
- [ ] Session memory — current state
