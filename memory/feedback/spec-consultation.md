---
name: Always consult specs; propose updates for discrepancies
description: Must read relevant spec-kit documents before planning or generating code; must flag and update specs when discrepancies are found
type: feedback
---

Always consult the relevant spec-kit documents (`specs/`) before planning any phase or generating code — not just session memory or ADR files.

**Why:** When planning Phase 1b, the session notes summarised scope as "25 models + feed stub" but `specs/10-migration-dimensions.md` additionally required Pluggy hookspecs, PluginManager singleton, and the functions.php decomposition map. The plan nearly omitted these. Session memory is a compressed summary; the specs are authoritative.

**Also discovered:** `specs/02-database.md` FK map incorrectly listed `ttrss_counters_cache → ttrss_feeds` — the actual PostgreSQL schema has no such FK constraint. Spec discrepancies must be flagged and corrected, not silently trusted.

**How to apply:**
- Before planning or coding any phase: read the relevant spec(s) for that phase scope, not just the session memory.
- When a discrepancy between a spec and the actual source (SQL schema, PHP code) is identified: flag it explicitly and propose a spec update in the same session.
- Spec-kit index: `AGENTS.md § Spec-Kit Index` lists all 13 spec documents and their scope.
