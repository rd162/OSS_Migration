---
name: project_setup
description: Initial project setup — TT-RSS PHP-to-Python modernization with spec-kit workspace created 2026-04-03
type: project
---

PHP-to-Python modernization of Tiny Tiny RSS (TT-RSS v1.12, schema v124).

**Why:** OSS migration exercise — full behavioral preservation required.

**How to apply:** All modernization work must reference specs in `specs/` directory. Source code is read-only in `source-repos/ttrss-php/`. Target Python code grows in `target-repos/`. Migration flow variant (A-E) not yet chosen — see `specs/09-modernization-dimensions.md`.

**Status as of 2026-04-03:**

- Spec-kit created with 10 comprehensive spec documents
- AGENTS.md and CLAUDE.md established
- Deep analysis complete across all dimensions
- Next step: discuss and choose modernization flow variant, then begin migration
