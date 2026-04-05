# ADR-0018: Drag-and-Drop Category Assignment — Deferred

- **Status**: accepted
- **Date**: 2026-04-06
- **Relates to**: ADR-0017 (Vanilla JS SPA)

## Context

The PHP TT-RSS frontend used Dojo's `dijit.Tree` widget which provided full drag-and-drop
support for assigning feeds to categories. The SME demo (2026-04-06) showed this as a
primary workflow: drag a feed from "Uncategorized" to a category folder.

## Decision

Drag-and-drop category assignment is **not implemented** in Phase 6. Instead, category
assignment is exposed via a **category selector dropdown** in the Settings modal's Feeds
section. Each feed row shows a `<select>` element listing all user categories; changing
the selection calls `POST /prefs/feeds/categorize`.

HTML5 native drag-and-drop (`draggable`, `ondragstart`, `ondrop`) is technically available
in vanilla JS without a library. The decision NOT to implement it is intentional:

1. **UX fidelity**: PHP's Dojo tree showed a visual drop target with expand/collapse animation.
   Replicating this UX in vanilla JS requires ~300 lines of non-trivial event handling
   (drag ghost, nested drop zones, tree re-render on drop) with significant edge-case complexity.
2. **Risk vs value**: The dropdown achieves the same functional outcome with zero risk.
   Drag-drop is a UX convenience, not a correctness requirement.
3. **Accessibility**: Dropdown category assignment is more accessible than drag-and-drop.
4. **Phase scope**: Phase 6 is Deployment, not UX enhancement. Drag-drop is a Phase 7 backlog item.

## Consequence

Users assign feeds to categories via the Settings modal (Feeds tab → category dropdown per
feed). New categories are created in the Settings modal Categories tab.

The functional capability of PHP's drag-drop IS fully replicated — only the interaction
metaphor differs.

## Backlog

Phase 7: Implement HTML5 native drag-drop with visual ghost and drop zone highlighting.
The backend `/prefs/feeds/categorize` route is already correct and requires no changes.
