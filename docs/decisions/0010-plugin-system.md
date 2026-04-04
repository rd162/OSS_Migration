# ADR-0010: Plugin System Implementation

- **Status**: accepted
- **Date proposed**: 2026-04-03
- **Date accepted**: 2026-04-04
- **Deciders**: Session 2026-04-04

## Context

The PHP codebase uses a singleton `PluginHost` class that provides a hook-based plugin system. Plugins are PHP classes that extend `Plugin` and register for hooks (e.g., `HOOK_ARTICLE_FILTER`, `HOOK_FEED_PARSED`, `HOOK_RENDER_ARTICLE`). There are 24 defined hook points across the feed update pipeline, article rendering, authentication, and preference management.

Key characteristics of the PHP plugin system:
- Plugins are discovered by scanning the `plugins/` and `plugins.local/` directories
- Each plugin is a single class with an `init($host)` method that registers hooks
- Hooks are called sequentially; some hooks allow plugins to modify data in-place
- System plugins (e.g., `auth_internal`, `note`) are always loaded
- User plugins are per-user enabled/disabled via preferences
- Plugin API version compatibility checking

The Python replacement must support equivalent hook points, discovery, per-user enable/disable, and a clear API contract.

## Options

### A: pluggy (pytest-Style Hook System)

Use `pluggy` (the hook system extracted from pytest). Plugins declare hook implementations via markers; the host calls hooks via a `PluginManager`. Discovery via `importlib` or entry points.

- Battle-tested (powers pytest ecosystem)
- Supports hook specifications (contracts), first-result, and wrappers
- No built-in discovery — pair with `importlib` or `pkg_resources`
- Clean separation of hook spec and hook implementation

### B: stevedore (Entry Points)

Use `stevedore` (OpenStack library) for plugin discovery and loading via Python entry points (`setup.cfg` / `pyproject.toml`). Hooks implemented as method calls on loaded plugin objects.

- Entry-point-based discovery (standard Python packaging)
- Supports drivers (single), hooks (multiple), and extensions
- Heavier dependency; designed for larger plugin ecosystems
- Less flexible hook calling conventions than pluggy

### C: Custom Hook System

Build a minimal hook system similar to the PHP `PluginHost`: a registry dict mapping hook names to lists of callables, with `add_hook()` / `run_hooks()` methods.

- Exact match to PHP architecture (easy mental model for migration)
- No external dependencies
- Must build and maintain hook spec validation, ordering, error handling
- Risk of reinventing wheels (testing, debugging, tracing)

### D: Django Signals / Blinker

Use the `blinker` library (or Django's signal system if using Django). Signals are named events; receivers connect to signals and are called when the signal fires.

- Simple pub/sub pattern
- No hook specifications or contracts
- No return-value aggregation (fire-and-forget)
- Not suitable for hooks that modify data in-place (e.g., article filter chain)

## Trade-off Analysis

| Criterion | A: pluggy | B: stevedore | C: Custom | D: blinker |
|-----------|-----------|-------------|-----------|------------|
| Hook specifications (contracts) | Yes | No | Manual | No |
| Data-modifying hooks (filter chains) | Yes (firstresult, wrappers) | Limited | Manual | No (fire-and-forget) |
| Discovery mechanism | importlib / entry points | Entry points (built-in) | Directory scan | Manual registration |
| External dependency weight | Light (~1 pkg) | Medium (~3 pkgs) | None | Light (~1 pkg) |
| Testing support | Excellent (pytest native) | Good | Manual | Good |
| Community / maintenance | Excellent (pytest team) | Good (OpenStack) | N/A | Good |
| Per-user plugin enable/disable | Application layer | Application layer | Application layer | Application layer |
| Migration complexity from PHP | Medium | Medium | Low | Medium |
| Hook ordering control | Yes (tryfirst/trylast) | Load order | Manual | No |

## Preliminary Recommendation

**Option A (pluggy)** for the hook system combined with `importlib`-based directory discovery. This provides:

1. **Hook specifications** as Python classes decorated with `@hookspec` — documents the contract for each of the 24 hooks
2. **Hook implementations** via `@hookimpl` — plugins declare which hooks they implement
3. **Filter chains** via `firstresult` and wrapper hooks — supports data-modifying hooks like `HOOK_ARTICLE_FILTER`
4. **Discovery** via scanning a `plugins/` directory and importing modules with `importlib`
5. **Per-user state** managed at the application layer (a user-plugin mapping table in the DB)

The PHP `PluginHost` singleton maps directly to a `pluggy.PluginManager` instance.

## Decision

**Option A: pluggy + importlib directory discovery.** Use `pluggy` for the hook system (hook specifications as `@hookspec` classes, hook implementations via `@hookimpl`) combined with `importlib`-based scanning of the `plugins/` directory for discovery. The PHP `PluginHost` singleton maps to a `pluggy.PluginManager` instance. Per-user enable/disable is managed at the application layer.

## Consequences

- Hook specifications (`ttrss/plugins/hookspecs.py`) serve as documentation and contract for plugin authors; all 24 PHP hooks are mapped to Python hookspecs
- pytest integration is natural — pluggy is the same hook system used by pytest, so test fixtures can register mock hook implementations without additional scaffolding
- Per-user enable/disable requires an application-layer wrapper around the PluginManager (a user→plugin mapping table in the DB, already present as `ttrss_plugin_storage`)
