---
name: Phase 7 Plan — Deferred Items
description: Backlog of features explicitly deferred from Phase 6; prerequisites and implementation notes per item
type: project
---

# Phase 7 Plan — Deferred Items

All Phases 1–6 of the PHP→Python migration are complete as of 2026-04-06.
This file captures everything explicitly deferred, with its ADR/spec reference and
the backend readiness state (most backends are already done).

---

## P0 — Immediate unblock (backends ready, only frontend work needed)

### Labels CRUD editor in Settings modal
- **Deferred by**: ADR-0019 (out of scope for Phase 6 modal)
- **Backend**: `/prefs/labels/*` fully implemented (create, rename, set color, delete)
- **Frontend gap**: Settings modal has no Labels tab
- **Work**: ~80 lines JS + CSS in `app.js`; 3–4 E2E tests
- **API calls**: `GET /prefs/labels` (list), `POST /prefs/labels` (create), `POST /prefs/labels/<id>/rename`, `DELETE /prefs/labels/<id>`

### Users tab in Settings modal (admin only)
- **Deferred by**: ADR-0019
- **Backend**: `/prefs/users/*` fully implemented (list, create, save, delete, reset_password)
- **Frontend gap**: Settings modal has no Users tab; admin can't create users from UI
- **Work**: ~100 lines JS + CSS; show only when `S.user` is admin (check via `getConfig` response)
- **API calls**: `GET /prefs/users` (list), `POST /prefs/users` (create), `DELETE /prefs/users/<id>`
- **SME spec-15 §4.1**: user creation was shown as a core workflow in the demo

---

## P1 — UX improvements (medium effort)

### Drag-and-drop category assignment
- **Deferred by**: ADR-0018
- **Backend**: `POST /prefs/feeds/categorize` already correct; no changes needed
- **Frontend gap**: Category assignment uses `<select>` dropdown (ADR-0018 alternative)
- **Work**: HTML5 native drag-and-drop on `.feed-item` → drop zone on `.cat-row`; ~150 lines JS
- **Note**: ADR-0018 says "Phase 7 backlog"; the dropdown remains as fallback for accessibility

### Multi-rule filter builder
- **Deferred by**: ADR-0019 (single rule + single action only in Phase 6)
- **Backend**: `POST /prefs/filters` accepts `request.form.getlist("rule")` and `request.form.getlist("action")` — already supports multiple rules/actions
- **Frontend gap**: Settings Filters tab only sends one rule and one action
- **Work**: Add/remove rule rows dynamically; ~120 lines JS

### Keyboard shortcut map
- **Deferred by**: ADR-0017 (Escape only implemented)
- **PHP original**: `hotkey_map` via plugin hooks; ~20 shortcuts (j/k navigate, s star, u mark unread, etc.)
- **Work**: Add `keydown` handler mapping to existing `data-action` names; no backend changes

---

## P2 — Infrastructure / policy (lower urgency)

### Logging strategy (ADR-0012)
- **Status**: ADR-0012 is `proposed`; structlog already wired but strategy not finalized
- **Work**: Define log levels per module, structured fields, log rotation policy

### i18n / localization (ADR-0013)
- **Status**: ADR-0013 is `proposed`; no implementation
- **SME spec-15 §13**: listed in test matrix but no test cases written
- **Work**: Flask-Babel integration; po/mo files; language selector in Settings Account tab
- **Estimate**: Large — touches all user-visible strings

### Plugin UI hooks
- **Deferred by**: ADR-0017 (backend plugin hooks intact; `PluginHost.js` client-side hooks not implemented)
- **Backend**: `pluggy` hook system fully wired (14 hooks); `hook_prefs_edit_feed`, `hook_prefs_tab` etc. all fire
- **Frontend gap**: No `PluginHost.js` equivalent; plugin-rendered HTML fragments not supported
- **Work**: Depends on which plugins need UI; auth_internal has no UI needs; readability plugin would need iframe injection support

---

## Release gate (do before any Phase 7 work)

Tag `v1.0.0` to trigger `.github/workflows/deploy.yml`:
```
git tag v1.0.0
git push origin v1.0.0
```

This runs pgloader MySQL→PostgreSQL migration + PHP serialize→JSON blob conversion on the
production database. Verify with `pre_migration_audit.sh` first.

---

## Summary table

| Item | Backend ready | Frontend work | Effort | Priority |
|------|--------------|--------------|--------|----------|
| Labels CRUD in settings | ✓ | ~80 lines JS | S | P0 |
| Users tab in settings | ✓ | ~100 lines JS | S | P0 |
| Drag-drop categories | ✓ | ~150 lines JS | M | P1 |
| Multi-rule filter builder | ✓ | ~120 lines JS | M | P1 |
| Keyboard shortcuts | ✓ | ~60 lines JS | S | P1 |
| Logging strategy | partial | config only | S | P2 |
| i18n / localization | — | large rewrite | XL | P2 |
| Plugin UI hooks | ✓ | per-plugin | varies | P2 |
