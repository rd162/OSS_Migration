# File Output Protocol — deep-research-t1

Full create/update protocols for persistent markdown playbook generation.
Loaded on demand from the main SKILL.md.

---

## Create mode (file does not exist)

1. Run Δ1-Δ7 with sub-agent fan-out if 2+ research angles needed.
2. Group findings into 5-10 logical sections.
3. Write the file:

```markdown
# [Title derived from topic]

## [Section Name]

[Tight synthesis paragraph + bullet insights]
[Claim]. — [Source Name](URL)

---

## Sources

- [URL 1]
- [URL 2]

---

_Captured: YYYY-MM-DD_
```

Rules:

- Every claim MUST have a source URL — drop findings without one.
- Voice: direct, concise, practitioner-focused. No hedging, no filler.
- Example — BAD: "It is generally recommended to consider caching for performance."
- Example — GOOD: "Cache aggressively. Redis for shared state, in-memory for hot paths."

## Update mode (file already exists)

1. Read the existing file. Note section headings, Sources list, and voice/style.
2. Run Δ1-Δ7 targeted to what has changed since the `*Captured:*` date.
3. For each new finding:
   - Locate the correct existing section.
   - Use Edit to merge inline — NEVER create a "New Findings" subsection.
   - Match the existing voice exactly (re-read a paragraph to internalize it first).
   - Format: `[Insight]. — [Source Name](URL)`
   - If a finding contradicts existing content AND has HIGH confidence (T1):
     update the existing claim, keep the old source for comparison.
   - If Medium confidence only: add as "alternative perspective", do not replace.
4. Add new source URLs to the Sources list at the bottom.
5. Update the `*Captured:*` date.

Rules:

- NEVER change the voice or restructure sections.
- NEVER add a claim without a source URL.
- ALWAYS preserve existing content unless explicitly superseded by a T1 source.

## Verification step (both modes)

After writing, read the file and verify:

- Every claim has a source URL.
- No duplicate entries.
- New content reads cohesively with existing content.
- Sources list is complete.

Then report:

```text
## Playbook [Created | Updated]

File: [absolute path]
Mode: [create | update]
Topic: [what was researched]
Sections [created | modified]: N
Sources: N
Findings integrated: N
Findings dropped (no source / duplicate): N
```
