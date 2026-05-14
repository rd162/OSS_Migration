# 02 — Include Graph

**Dimension**: `include-graph`
**Artifact**: `tools/graph_analysis/output/include_graph.json`
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The include graph captures **static dependency edges** between PHP source files,
derived from `require_once`, `require`, `include_once`, and `include` statements.
Each node is a source file; each directed edge is a file-level dependency.

For the PHP → Python modernization this dimension:

- Reveals the **bootstrap sequence** — which files must be loaded before others
- Identifies **tight coupling clusters** (files that mutually include each other)
- Exposes **isolated subsystems** that can be ported without touching core
- Maps the implicit Python **module/package structure** for the target codebase
- Flags **third-party library boundaries** that should become `requirements.txt` entries

---

## Graph structure

| Metric | Value |
|---|---|
| Nodes (source files) | 139 |
| Edges (include/require statements) | 66 |
| Raw Leiden communities | 85 |
| Grouped research passes (∆5) | 7 |
| Isolated singletons (size = 1) | 78 |
| Artifact | `tools/graph_analysis/output/include_graph.json` |

Node labels are relative paths from the `ttrss/` root (e.g., `classes/api.php`).
Edge direction: `includer → included` (i.e., the file that issues the `require`
statement points to the file it requires).

---

## Communities (after ∆5 grouping — 7 research groups)

### C0 — Bootstrap / Core (14 nodes)

**Members**:
`classes/db.php`, `errors.php`, `include/autoload.php`, `include/functions.php`,
`include/ccache.php`, `include/db-prefs.php`, `include/db.php`,
`include/errorhandler.php`, `lib/accept-to-gettext.php`, `lib/gettext/gettext.inc`,
`include/version.php`, `include/labels.php`,
`lib/pubsubhubbub/publisher.php`, `include/sessions.php`

**Characterisation**: The universal bootstrap cluster.
Every entry point (`index.php`, `backend.php`, `api/index.php`,
`update_daemon2.php`) includes most of these files.
This cluster defines the minimum viable application context:
DB connection, autoloader, global utilities, session handler, i18n, and version constants.

**Migration impact**: These files decompose into the Python package `__init__`,
`db.py`, `autoload` equivalent (Python imports), `sessions.py`, `utils/`.
Every Python module implicitly depends on this cluster.

**Research note**: `research/GRP-08-bootstrap-core.md`

---

### C1 — phpqrcode library (13 nodes)

**Members**:
`lib/phpqrcode/index.php`, `lib/phpqrcode/qrlib.php`, `lib/phpqrcode/qrbitstream.php`,
`lib/phpqrcode/qrconfig.php`, `lib/phpqrcode/qrconst.php`, `lib/phpqrcode/qrencode.php`,
`lib/phpqrcode/qrimage.php`, `lib/phpqrcode/qrinput.php`, `lib/phpqrcode/qrtools.php`,
`lib/phpqrcode/qrspec.php`, `lib/phpqrcode/qrsplit.php`, `lib/phpqrcode/qrrscode.php`,
`lib/phpqrcode/qrmask.php`

**Characterisation**: Fully self-contained QR code generation library
(PHP port of libqrencode). No outgoing edges to application code.
Called only from `plugins/auth_internal/init.php` via `lib/phpqrcode/phpqrcode.php`.

**Migration impact**: Replace wholesale with `qrcode` or `segno` (Python PyPI).
Do NOT port line-by-line.

**Research note**: `research/GRP-09-third-party-libs.md`

---

### C2 — API + Feed utilities + Icon fetch cluster (11 nodes)

**Members**:
`classes/api.php`, `include/rssfuncs.php`, `include/colors.php`,
`lib/floIcon.php`, `include/crypt.php`,
`lib/languagedetect/LanguageDetect.php`, `lib/pubsubhubbub/subscriber.php`,
`lib/jimIcon.php`,
`lib/languagedetect/Text/LanguageDetect/Exception.php`,
`lib/languagedetect/Text/LanguageDetect/Parser.php`,
`lib/languagedetect/Text/LanguageDetect/ISO639.php`

**Characterisation**: The feed-processing and API include cluster.
`classes/api.php` and `include/rssfuncs.php` are the heaviest files here;
their co-location in one include community reflects mutual dependencies
during feed update operations.
Language detection library and icon-fetch utilities cluster here because
they are included specifically by `rssfuncs.php`.

**Migration impact**:
- `rssfuncs.php` → `ttrss/tasks/feed_update.py` (Celery task)
- `crypt.php` → `ttrss/utils/crypt.py` (Fernet replacement)
- LanguageDetect → `langdetect` or `lingua` (PyPI)
- Icon fetch (`floIcon`, `jimIcon`) → dedicated `ttrss/utils/favicon.py`

**Research note**: `research/GRP-02-feed-engine.md`

---

### C3 — Public handler + Email + Registration cluster (8 nodes)

**Members**:
`classes/handler/public.php`, `lib/MiniTemplator.class.php`,
`classes/ttrssmailer.php`, `classes/pref/users.php`,
`lib/phpmailer/class.phpmailer.php`, `include/digest.php`,
`lib/phpmailer/class.smtp.php`, `register.php`

**Characterisation**: The outbound-communication and public-HTTP cluster.
`handler/public.php` and `digest.php` co-locate because digest sending
is triggered from the same update path that serves public feeds.
PHPMailer 5.x and MiniTemplator are bundled dependencies used only here.

**Migration impact**:
- `handler/public.php` → Flask Blueprint `public`
- `ttrssmailer.php` + `phpmailer/` → `flask-mail` / `aiosmtplib`
- `digest.php` → `ttrss/tasks/digest.py` Celery task
- `MiniTemplator` → Jinja2 templates
- `register.php` → Flask route `/register`

**Research note**: `research/GRP-07-email-digest.md`

---

### C4 — Main UI entry + utility cluster (7 nodes)

**Members**:
`include/functions2.php`, `include/login_form.php`, `lib/sphinxapi.php`,
`lib/jshrink/Minifier.php`, `index.php`, `lib/Mobile_Detect.php`, `prefs.php`

**Characterisation**: Main web UI entry points and their direct includes.
`functions2.php` is the second large utility file (~2413 LOC);
it is included by `index.php` and `prefs.php` for HTML rendering utilities
(`sanitize()`, `format_article()`, `getFeedUnread()`).
Sphinx search API and JS minifier are included from `index.php` or `prefs.php`
conditionally.

**Migration impact**:
- `functions2.php::sanitize()` → `bleach.clean()` + `lxml` allowlist
- `functions2.php::format_article()` → Jinja2 template
- `sphinxapi.php` → `sphinxapi` Python client or PostgreSQL FTS
- `jshrink/` → drop (build-time tooling handles JS minification)
- `Mobile_Detect.php` → `user-agents` PyPI library
- `index.php` → Flask route `/` serving SPA `index.html`
- `prefs.php` → Flask Blueprint `prefs` entry point

**Research note**: `research/GRP-08-bootstrap-core.md`

---

### C5 — OTP + auth_internal cluster (6 nodes)

**Members**:
`classes/pref/prefs.php`, `lib/otphp/vendor/base32.php`,
`lib/otphp/lib/otp.php`, `lib/otphp/lib/totp.php`,
`lib/phpqrcode/phpqrcode.php`, `plugins/auth_internal/init.php`

**Characterisation**: TOTP/OTP authentication cluster.
`auth_internal/init.php` includes `otphp` (TOTP library) and `phpqrcode`
(for QR code enrollment). `pref/prefs.php` includes `auth_internal`
for OTP configuration UI.

**Migration impact**:
- `otphp/` → `pyotp` (PyPI)
- `phpqrcode/` (entry only) → `qrcode` PyPI
- `auth_internal/init.php` → `ttrss/plugins/auth_internal/__init__.py`

**Research note**: `research/GRP-06-auth-session.md`

---

### C6 — Sanity check cluster (2 nodes)

**Members**:
`include/sanity_check.php`, `include/sanity_config.php`

**Characterisation**: Runtime configuration and environment validation.
`sanity_config.php` validates required constants; `sanity_check.php`
checks DB connectivity, PHP extensions, and writable directories.
Included only at bootstrap time before any request is processed.

**Migration impact**:
- `sanity_check.php` → Flask CLI command `flask check` / startup hook
- `sanity_config.php` → `ttrss/config.py` validation with `pydantic` Settings

**Research note**: `research/GRP-08-bootstrap-core.md`

---

### Singletons (78 nodes — absorbed)

78 files appear as isolated single-node communities.
The majority are:
- Entry-point files (`backend.php`, `api/index.php`, `update_daemon2.php`,
  `update.php`, `opml.php`, `image.php`) that include others but are not
  included by others — they are DAG roots.
- Leaf library files with no outgoing include edges.
- PHP files in `classes/pref/`, `classes/auth/`, `classes/db/`
  that are loaded by the autoloader rather than explicit `require_once`.

These singletons are NOT isolated modules; they are DAG roots or leaves.
Migration order: roots last (entry points), leaves first.

---

## Dependency levels (topological order)

| Level | Characterisation | Representative files |
|---|---|---|
| 0 (bootstrap — no incoming) | Core utilities, DB abstraction, session handler | `include/db.php`, `include/functions.php`, `include/sessions.php`, `lib/phpmailer/class.smtp.php` |
| 1 | First-level includes — pull in level-0 files | `classes/db.php`, `include/functions2.php`, `include/rssfuncs.php`, `include/ccache.php` |
| 2 | Mid-tier handlers and pref files | `classes/feeds.php`, `classes/api.php`, `classes/pref/*.php`, `classes/backend.php` |
| 3+ (entry points) | Top-level PHP scripts included by nothing | `index.php`, `backend.php`, `api/index.php`, `update_daemon2.php`, `prefs.php`, `public.php` |

Migration rule: **port level-0 modules first**.
The Python package structure should mirror this level ordering:
`ttrss/db/` → `ttrss/utils/` → `ttrss/blueprints/` → `ttrss/cli/`.

---

## Python module mapping (from include communities)

| PHP include cluster | Python package/module |
|---|---|
| C0 bootstrap | `ttrss/__init__.py`, `ttrss/db.py`, `ttrss/utils/db_helpers.py`, `ttrss/sessions.py` |
| C1 phpqrcode | `qrcode` PyPI (replace entirely) |
| C2 API + feed + icons | `ttrss/blueprints/api/`, `ttrss/tasks/feed_update.py`, `ttrss/utils/favicon.py` |
| C3 public + email + digest | `ttrss/blueprints/public/`, `ttrss/tasks/digest.py`, `ttrss/mail.py` |
| C4 UI + functions2 | `ttrss/blueprints/backend/`, `ttrss/utils/sanitize.py`, `ttrss/utils/article.py` |
| C5 OTP + auth_internal | `ttrss/plugins/auth_internal/`, `ttrss/utils/otp.py` |
| C6 sanity checks | `ttrss/config.py` (pydantic Settings), `ttrss/cli/check.py` |
| Entry-point singletons | `ttrss/wsgi.py`, `ttrss/cli/update.py`, `ttrss/cli/daemon.py` |

---

## Modernization impact

### Bootstrap sequence preservation
The Python application must replicate the PHP bootstrap order:

```
1. Config constants  → ttrss/config.py (pydantic Settings)
2. DB connection     → Flask-SQLAlchemy app factory
3. Autoloader equiv  → Python import (automatic)
4. Error handler     → Flask error handlers + Python logging
5. i18n init         → Flask-Babel localeselector
6. Session init      → Flask-Login + Redis backend
7. Plugin load       → pluggy PluginManager.register() at app startup
```

Failure to preserve this order causes subtle init failures
(e.g., `get_pref()` called before DB is connected, or hooks fired before
plugins are registered).

### Circular include detection
The 66-edge include graph with 139 nodes is relatively sparse (density ≈ 0.003),
which means PHP's `require_once` guards successfully prevent circular include
loops. Python's import system handles this natively — no special action needed.

### Autoloader → Python imports
PHP's SPL autoloader (`include/autoload.php`) maps class names to file paths
using underscore-as-directory-separator convention:
- `Handler_Public` → `classes/handler/public.php`
- `Auth_Internal` → `plugins/auth_internal/init.php`
- `Db_Pgsql` → `classes/db/pgsql.php`

Python does not need an autoloader; the mapping becomes explicit module imports.
The naming convention is documented for reference; Python class names should
follow PEP 8 (`HandlerPublic`, `AuthInternal`, `DbPgsql`).

---

## Source cross-references

| Construct | Source | Line(s) |
|---|---|---|
| SPL autoloader registration | `source-repos/ttrss-php/ttrss/include/autoload.php` | full |
| Bootstrap sequence (entry) | `source-repos/ttrss-php/ttrss/index.php` | 1–30 |
| Bootstrap sequence (daemon) | `source-repos/ttrss-php/ttrss/update_daemon2.php` | 1–25 |
| Bootstrap sequence (API) | `source-repos/ttrss-php/ttrss/api/index.php` | full |
| Session handler registration | `source-repos/ttrss-php/ttrss/include/sessions.php` | 130–145 |
| i18n bootstrap | `source-repos/ttrss-php/ttrss/include/functions.php` | `startup_gettext()` |
| Sanity config check | `source-repos/ttrss-php/ttrss/include/sanity_config.php` | full |
| Sanity runtime check | `source-repos/ttrss-php/ttrss/include/sanity_check.php` | full |
| QRcode entry include | `source-repos/ttrss-php/ttrss/lib/phpqrcode/phpqrcode.php` | full |
| TOTP include chain | `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` | top |

---

## Notes and caveats

- **High singleton count (78/85)**: Most PHP source files are not explicitly
  `require_once`'d because the SPL autoloader loads them on demand.
  The include graph captures only *explicit* include statements; the true
  runtime dependency graph is denser than the 66-edge graph suggests.
  The call graph (dimension 01) provides the runtime dependency signal.

- **Sparse graph, strong clustering**: Despite 139 nodes and only 66 edges,
  the 7 retained communities (C0–C6) are semantically coherent and align
  well with logical subsystem boundaries. This is a positive signal: PHP
  modules are not excessively entangled at the file-include level.

- **autoload.php is a pivot node**: `include/autoload.php` is in the
  bootstrap cluster (C0) but implicitly loads every class file at runtime.
  Its edges to class files are NOT in the include graph (they are dynamic);
  they appear as call-graph edges. Do not interpret the sparse C0 cluster
  as evidence that class files are independent of the bootstrap.

- **Research mode**: ∆6 community research ran in DEGRADED mode (no external
  web search). Target-side guidance from training knowledge only.
  Phase 2 ADR drafting should verify Python package choices against current
  ecosystem state.
