# ADR-0013: Internationalization Approach

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase uses GNU gettext for internationalization. The `locale/` directory contains 20 language directories (e.g., `locale/fr_FR/LC_MESSAGES/messages.po`), each with `.po` (human-editable) and `.mo` (compiled binary) files. Translatable strings are marked with `__()` (a wrapper around `gettext()`). The active locale is set via `accept-to-gettext.php` which parses the browser's `Accept-Language` header.

Key characteristics:
- ~1,500 translatable strings across the codebase
- `.po` files represent significant community translation effort
- Plural forms handled via `ngettext()`
- Some strings contain HTML or format specifiers (`%s`, `%d`)
- JavaScript strings are translated separately via inline JSON

The Python replacement must:
- Reuse existing `.po`/`.mo` translation files (avoid re-translating 20 languages)
- Support string extraction from Python source and Jinja2 templates
- Handle plural forms correctly per locale
- Support runtime locale switching per user preference

## Options

### A: Python gettext + Babel

Use Python's built-in `gettext` module for runtime translation lookup, combined with `Babel` (via `Flask-Babel`) for string extraction, `.po` file management, and locale negotiation.

- Python `gettext` reads standard `.mo` files — direct reuse of existing translations
- Babel extracts strings from Python source and Jinja2 templates
- Flask-Babel integrates locale selection with Flask request context
- `pybabel` CLI for compiling `.po` to `.mo`, updating catalogs

### B: Babel Only (Without gettext)

Use Babel's own translation catalog system exclusively, bypassing Python's `gettext` module. Babel can load `.po` files directly and provides its own `gettext()`/`ngettext()` functions.

- Slightly more Pythonic API
- Still reads `.po`/`.mo` files
- Less standard than the `gettext` module approach
- Flask-Babel uses this approach internally

### C: Custom Translation System

Build a custom key-value translation system (e.g., JSON files per locale, loaded at startup). Abandon `.po`/`.mo` format.

- Maximum flexibility (JSON, YAML, DB-backed)
- Loses all existing `.po` translations (must re-import)
- No standard tooling for translators (Poedit, Weblate, Transifex)
- Must implement plural forms manually

## Trade-off Analysis

| Criterion | A: gettext + Babel | B: Babel Only | C: Custom |
|-----------|-------------------|---------------|-----------|
| Reuse existing .po/.mo files | Direct | Direct | Requires conversion |
| String extraction | pybabel extract (Jinja2 + Python) | pybabel extract | Custom |
| Plural form support | Native (ngettext) | Native | Manual |
| Translator tooling compatibility | Full (Poedit, Weblate) | Full | None |
| Flask integration | Flask-Babel | Flask-Babel | Custom middleware |
| Runtime locale switching | Per-request (Flask-Babel) | Per-request (Flask-Babel) | Custom |
| Standard compliance | GNU gettext standard | GNU gettext standard | Proprietary |
| JavaScript translations | Separate extraction needed | Separate extraction needed | Could unify |
| Migration effort | Low (rename `__()` to `_()`) | Low | High |

## Preliminary Recommendation

**Option A (Python gettext + Babel)** — this is the natural choice because:

1. **Existing `.po` files work as-is** — the 20 language directories with community translations are directly reusable
2. **Flask-Babel** provides `_()` and `ngettext()` in templates and Python code, matching the PHP `__()` pattern
3. **pybabel extract** scans both Python source and Jinja2 templates for translatable strings
4. **pybabel update** merges new strings into existing `.po` files without losing translations
5. **Locale negotiation** via Flask-Babel's `@babel.localeselector` replaces `accept-to-gettext.php`

Migration steps:
1. Copy existing `locale/` directory to Python project
2. Rename `__()` calls to `_()` during code migration
3. Run `pybabel extract` to generate a fresh `.pot` template
4. Run `pybabel update` to merge new/changed strings into existing `.po` files
5. Translators review and update only the changed strings

## Decision

**TBD**

## Consequences

- If Option A: preserves all existing community translations (significant value)
- If Option A: translators continue using familiar tools (Poedit, Weblate, Transifex)
- If Option A: JavaScript string translation needs a separate solution (e.g., `jed` or inline JSON)
- If Option B: functionally identical to A; the distinction is an implementation detail
- If Option C: would discard years of community translation work
- All options: strings with `%s`/`%d` format specifiers should be migrated to Python `.format()` or f-string compatible patterns
