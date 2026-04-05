# ADR-0019: Simplified In-App Preferences Modal

- **Status**: accepted
- **Date**: 2026-04-06
- **Relates to**: ADR-0017 (Vanilla JS SPA)

## Context

The PHP TT-RSS preferences system was a full-page tabbed interface with Dojo tree widgets
for feeds, filters, and labels, rendered server-side as HTML fragments. The SME demo
showed a rich preferences panel with:

- Feeds tab: tree of feeds/categories with drag-drop + inline edit
- Filters tab: rule/action builder with add/remove rows
- Labels tab: color-picker, caption editor
- Users tab: admin user management table
- System tab: server config, log viewer

## Decision

The Python SPA implements preferences as an **in-app modal** (Settings ▾ in the footer)
with tabbed sections. Implemented tabs and their scope:

| Tab | Functionality | Notes |
|-----|---------------|-------|
| Account | Show username, update interval preference | Simple form |
| Feeds | List feeds with category selector + remove | Dropdown replaces drag-drop (ADR-0018) |
| Categories | Add/rename/delete categories | Full CRUD |
| Filters | List filters, create simple filter (1 rule + 1 action) | Simplified from PHP multi-rule builder |
| OPML | Export link + import file upload | Full functionality |

## Out of scope for Phase 6

- **Labels tab**: labels exist in the sidebar (cat_id = -2); full label CRUD editor deferred.
- **Users tab**: admin user management deferred (backend `/prefs/users/*` already implemented).
- **System tab**: server log, plugin management deferred.
- **Multi-rule filter builder**: PHP filter builder supported multiple rules/actions per filter.
  Phase 6 implements single-rule + single-action creation. Multi-rule editing via backend API
  remains available.

## Consequence

All backend routes for preferences are already implemented and fully tested. The modal
pattern means no full-page navigation — users stay in the reading app while managing feeds.
This is a UX pattern difference from PHP (full-page) but achieves full functional parity
for the most common workflows shown in the SME demo.
