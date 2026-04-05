---
title: Frontend Implementation Strategy
status: accepted
date: 2026-04-05
decision_makers: [rd]
consulted: []
informed: []
---

# ADR-0017 — Frontend Implementation: Vanilla-JS SPA, Zero Build

## Status

Accepted

## Context

ADR-0004 declared the frontend strategy TBD ("proposed"). The Python backend is now
complete (Phases 1–5b done, 1390 tests passing, 0 coverage gaps). A browser UI is
needed to make the application fully usable. Three strategies were evaluated via
adversarial review:

- **A. Vanilla-JS SPA, zero build** — `index.html` + `app.js` + `app.css`, native
  `fetch`, no framework, no build step.
- **B. htmx + Alpine.js + Jinja2** — server-rendered fragments, requires 3 new Flask
  blueprint routes and htmx/Alpine CDN or vendor assets.
- **C. Preact + esbuild micro-build** — component tree with esbuild bundler (one
  binary), committed built output for deployability.

Competing tensions: delivery speed vs. maintainability; zero infrastructure changes vs.
modern DX; avoiding legacy tech while not introducing React overhead.

The original TT-RSS uses Dojo Toolkit 1.x (deprecated, GPL+AFL licensing conflict,
maintenance-only since 2021). Reuse is ruled out.

## Decision

Adopt **Candidate A: Vanilla-JS SPA, zero build**.

The entire frontend is three files in `ttrss/static/`: `index.html`, `app.js`,
`app.css`. The public blueprint's `/` route is updated to serve `index.html`. No new
Flask routes, no build tooling, no npm, no CDN dependency. All six required UI
components (login, feed sidebar, article list, reading pane, header/nav,
settings+subscribe) are implemented as template-literal render functions in `app.js`.

State lives in a single plain JS object. A `render()` function performs full `innerHTML`
replacement on every state change, with a `bind()` pass to re-attach event listeners.
Article content is rendered in an `<iframe srcdoc>` to prevent XSS from feed-sourced
HTML. Auth uses `fetch` with `credentials: 'include'`; the HttpOnly session cookie is
set by the backend. No credentials are ever written to `localStorage` or `sessionStorage`.

## Consequences

**Positive:**
- Zero new infrastructure — `flask run` serves a working app immediately (R06)
- No build step to fail, no npm, no CDN dependency (R10, AR03)
- No new Flask routes (AR04)
- Full six-component MVP delivered in one session (R01)
- PHP source traceability via JSDoc `/** Source: */` comments (R09)
- iframe XSS isolation for article content (R08)

**Negative / mitigations:**
- `app.js` is monolithic (~700 lines); mitigated by clear IIFE section structure
  and section-level JSDoc comments. Refactor to ES modules + esbuild (Candidate C)
  is a low-risk future step.
- `innerHTML` re-renders lose scroll position; mitigated by saving/restoring
  `scrollTop` on the sidebar and article list before re-render.
- No virtual DOM diffing means full re-render on every state change; acceptable at
  RSS-reader scale (tens of feeds, hundreds of articles).

## Supersedes

ADR-0004 (frontend strategy): status changes from "proposed" to "superseded by ADR-0017".
