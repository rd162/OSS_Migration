# ADR-0004: Frontend Migration Strategy

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The TT-RSS frontend is a server-rendered SPA hybrid using:
- **Prototype.js** (~1.7) — DOM manipulation, AJAX
- **Dojo Toolkit** (~1.8) — dijit widgets, data stores, tree components
- **Custom JS** — 11 application files (~3000 lines)
- **Server-rendered HTML** — headlines, dialogs, toolbars generated in PHP

Both Prototype.js and Dojo are legacy libraries (Prototype essentially unmaintained since 2015, Dojo 1.x superseded by Dojo 2+).

The frontend communicates with the backend through a well-defined JSON RPC contract via `backend.php?op=X&method=Y`.

## Options

### A: Keep Existing Frontend (Phase 1 only)
- Build Python backend with identical JSON API contract
- Frontend JS stays unchanged — served as static files
- Verify behavior parity by running same frontend against new backend
- Defer frontend modernization to Phase 2

### B: Rewrite with htmx (Server-Rendered)
- Closest to current architecture (server sends HTML fragments)
- Replace Prototype.js AJAX with htmx attributes
- Replace dijit widgets with lightweight alternatives (Alpine.js, vanilla JS)
- Incremental: can replace one component at a time

### C: Rewrite with React/Vue SPA
- Modern SPA with API-first backend
- Complete frontend rewrite
- Backend becomes pure REST/GraphQL API
- Highest effort, highest long-term maintainability

### D: Rewrite with Jinja2 + HTMX + Alpine.js
- Server-rendered pages with Jinja2 templates
- HTMX for AJAX interactions (partial page updates)
- Alpine.js for client-side interactivity (dropdowns, toggles)
- No heavy JS framework, keeps server-rendering pattern

## Trade-off Analysis

| Criterion | A: Keep | B: htmx | C: React/Vue | D: Jinja2+htmx+Alpine |
|-----------|---------|---------|--------------|----------------------|
| Migration effort | Minimal | Medium | Very high | Medium |
| Behavior parity verification | Easy | Medium | Hard | Medium |
| Can start immediately | Yes | No (needs backend first) | No | No |
| Long-term maintainability | Poor (legacy libs) | Good | Best | Good |
| Performance | Same | Better | Better | Better |
| Team skill requirements | None | Low | High (React/Vue) | Low |

## Preliminary Recommendation

**Option A for Phase 1** — keep existing frontend to validate backend migration with zero frontend risk.

**Option D for Phase 2** — Jinja2 + htmx + Alpine.js modernizes the frontend while preserving the server-rendered architecture that TT-RSS already uses.

## Decision

**Option C (Vanilla JS SPA) — accepted 2026-04-05, superseded by ADR-0017.**

See [ADR-0017](0017-frontend-spa-vanilla-js.md) for the full rationale. In practice the team
chose zero-dependency vanilla JS (no Jinja2 server-side fragments, no htmx, no Alpine.js) to
eliminate the CDN dependency on Dojo 1.8 and Prototype.js. The vanilla SPA uses the same JSON
API contract (`POST /api/`) as the PHP frontend.

Status: **accepted** (resolved).

## Consequences

- If Option A: must preserve exact JSON response format from `backend.php`
- If Option A: must serve static JS/CSS files from Python app
- If Option D (Phase 2): need to map dijit widgets to Alpine.js equivalents
- Frontend choice doesn't block backend migration (decoupled by JSON contract)
