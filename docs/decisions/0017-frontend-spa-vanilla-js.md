# ADR-0017: Vanilla JS SPA — Replace Dojo Toolkit Frontend

- **Status**: accepted
- **Date**: 2026-04-05
- **Supersedes**: ADR-0004 (Frontend Migration Strategy — Option A deferred)
- **Deciders**: migration team

## Context

ADR-0004 proposed three options. Option A (keep legacy Prototype.js + Dojo 1.8 frontend) was
originally chosen for Phase 1 to avoid blocking backend validation on a risky dual-rewrite.

By Phase 5b the backend was fully validated. Carrying the legacy frontend into Phase 6 deployment
created new risks:
- **CDN dependency**: Prototype.js and Dojo 1.8 are no longer on popular CDNs.
- **Compatibility**: Dojo 1.8 `dijit` tree widgets fail in modern browsers' strict-mode JS.
- **Complexity**: The PHP SPA injected HTML fragments server-side; Python would need to replicate
  27+ PHP dialog templates just to serve the same Dojo dialogs.
- **Security**: Prototype.js 1.7 has known prototype-pollution vulnerabilities.

## Decision

Implement a **zero-dependency vanilla JS SPA** that is visually faithful to the PHP Claro theme
and uses the same JSON API contract (POST /api/). Key constraints:

- No build step, no npm, no bundler.
- All HTML rendered client-side from the same API the PHP frontend used.
- Hash routing `#f=FEED_ID&c=CAT_ID` matches PHP URL scheme.
- Session cookie pattern identical (HttpOnly, no localStorage tokens).
- Article content rendered in a sandboxed iframe (XSS isolation, R08).

## Consequences

**Positive**
- Zero legacy JS debt; single 800-line file instead of 3000-line Dojo/Prototype codebase.
- No CDN dependencies; fully self-hosted.
- Modern browser compatible; passes Playwright E2E automation.
- Same JSON API means all integration tests remain valid.

**Negative (Deferred)**
- **Drag-and-drop** feed reordering and category assignment: HTML5 native drag-and-drop is
  possible in vanilla JS but Dojo's `dijit.Tree` drag-drop UX is complex to replicate faithfully.
  Deferred to ADR-0018 — category assignment implemented via dropdown instead.
- **Full preferences panel**: PHP had a full-page tabbed preferences dialog with complex Dojo
  tree widgets for feeds/filters/labels. Python SPA uses a simplified in-app modal (ADR-0019).
- **Plugin UI hooks**: `PluginHost.js` client-side hooks not implemented — plugins that required
  custom JS UI are not supported in Phase 6. Backend plugin hooks remain fully intact.
- **Keyboard shortcut map**: PHP supported a configurable hotkey map via plugin hooks; Python SPA
  supports only Escape key. Full shortcut support deferred.

## Acceptance criteria

- [x] Login / logout flow
- [x] Six virtual feeds (all/fresh/starred/published/archived/recent)
- [x] Category collapse/expand
- [x] Real feed sidebar with unread badges
- [x] Headline list with view modes (all/unread/starred/published)
- [x] Article reading pane with sandboxed iframe
- [x] Star / unstar article
- [x] Mark all read (catchupFeed)
- [x] Subscribe modal (URL → subscribeToFeed API)
- [x] Unsubscribe from feed
- [x] Settings modal (account + feed list)
- [x] Hash routing + session persistence on reload
- [x] 51/52 Playwright E2E tests pass
