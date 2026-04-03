# AGENTS.md — PHP-to-Python Migration Project

## Mission

Migrate Tiny Tiny RSS (TT-RSS) from PHP to Python, fully preserving all specs, design, and behavior of the source project.

## Project Layout

```
OSS_Migration/
├── AGENTS.md              ← This file (project rules & conventions)
├── CLAUDE.md              ← Umbrella pointing here
├── specs/                 ← Spec-kit: architecture, DB, API, etc.
│   ├── 00-architecture.md
│   ├── 01-database.md
│   ├── 02-api-routing.md
│   ├── 03-frontend.md
│   ├── 04-plugin-system.md
│   ├── 05-security.md
│   ├── 06-caching-performance.md
│   ├── 07-deployment.md
│   ├── 08-source-index.md
│   └── 09-migration-dimensions.md
├── memory/                ← Project memory (cross-session context)
├── rules/                 ← Supplementary rules if needed
├── source-repos/          ← READ-ONLY: PHP source (ttrss-php/)
│   └── ttrss-php/
└── target-repos/          ← Python migration target (grows here)
```

## Critical Rules

### Storage Rules
1. **NEVER** write files into `~/.claude/projects/*/memory/` — all memory goes to `./memory/`
2. **NEVER** modify anything inside `source-repos/` — it is read-only reference
3. **NEVER** store project specs, memory, or rules in `.claude/` — that dir is only for Claude-specific config (settings, skills)
4. All specs, memory, rules, and artifacts go in the **project root** under their respective directories
5. This ensures cross-platform portability (not tied to Claude's home directory)

### Migration Rules
6. Target Python code goes into `target-repos/` — this is where the migrated project grows
7. Every spec document in `specs/` must cross-reference source files by relative path (e.g., `source-repos/ttrss-php/ttrss/classes/db.php`) rather than duplicating source code
8. Specs may include **reasonable code examples** to highlight important architectural decisions, but must not be a copy of the source
9. When migrating, always verify behavior parity against the source spec before marking a component complete

### Analysis Rules
10. Use deep web research for any complicated architectural topic (PHP patterns, 3-tier architecture, ORM vs transactional script, etc.)
11. For source code analysis dimensions (call graph, entity graph, etc.), consider using NetworkX and Leiden community detection
12. Migration flow is driven by dimensions documented in `specs/09-migration-dimensions.md` — discuss and choose flow before starting migration

### Quality Rules
13. Preserve all functional behavior from the PHP source
14. Fix known security issues during migration (SHA1→bcrypt, prepared statements, etc.) — document deviations in specs
15. Maintain spec-to-code traceability throughout the migration

## Spec-Kit Index

| Spec | Contents |
|------|----------|
| `00-architecture.md` | Application layers, design patterns, request lifecycle, class hierarchy |
| `01-database.md` | 35 tables, FK map, migration system, seed data, schema patterns |
| `02-api-routing.md` | Entry points, handler dispatch, RPC endpoints, request/response contracts |
| `03-frontend.md` | JS files, AJAX patterns, Dojo/Prototype widgets, server-rendered HTML |
| `04-plugin-system.md` | 24 hooks, plugin lifecycle, storage, system vs user plugins |
| `05-security.md` | 10 findings by severity, auth flow, session management, encryption |
| `06-caching-performance.md` | Counter cache, file cache, HTTP caching, daemon architecture |
| `07-deployment.md` | Docker, Nginx/PHP-FPM, CI/CD, environment config |
| `08-source-index.md` | Complete file inventory with purpose annotations and cross-references |
| `09-migration-dimensions.md` | Call graph, entity graph, frontend/backend dimensions, migration flow variants |

## Recommended Skills

Skills that should be installed in `.claude/skills/` for this project:

- **inferring-requirements** — requirements discovery before each migration phase
- **deep-research-t1** — research Python equivalents for PHP patterns
- **document-ingestion** — if external specs/docs need processing
- **continuation-and-handoff** — multi-session migration continuity
- **adversarial-self-refine** — iterative quality improvement of migrated code
- **selecting-pe-methods** — choose optimal reasoning strategy per migration task
