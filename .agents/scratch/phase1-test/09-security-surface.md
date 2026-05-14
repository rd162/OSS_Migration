# 09 — Security Surface

**Dimension**: `security-surface`
**Derivation**: Cross-cutting — `include/crypt.php`, `include/functions2.php::sanitize()`,
`include/sessions.php::validate_session()`, `include/db.php` (SQL injection surface),
`classes/auth/base.php`, `config.php-dist` security constants
**Phase**: Phase 1
**Status**: extracted ✓ · research DEGRADED (no web access)

---

## Purpose

Catalogues every security mechanism in TT-RSS — authentication, credential storage,
cryptography, input sanitisation, SQL injection surface, CSRF, and session hardening.
This is a cross-cutting dimension that synthesises findings from dimensions
07 (auth/session), 04 (entity-schema), 08 (daemon) and informs Phase 2 security ADRs.

---

## Security findings inventory

### SF-01 — SQL injection via escape_string() (CRITICAL)

**Pattern**: Every DB operation uses `Db::get()->escape_string($val)` string
interpolation into raw SQL strings instead of prepared statements.
**Scope**: >500 occurrences of `db_query(` containing interpolated values.
**Example**: `"SELECT id FROM ttrss_users WHERE login = '$login'"` in `classes/api.php:60`.
**Risk**: Server-side SQL injection on any unvalidated user input.
**Python fix**: SQLAlchemy parameterised queries throughout. `escape_string()` eliminated.
**Frequency**: Every DB-touching request path.
Source: `source-repos/ttrss-php/ttrss/include/db.php`, `classes/api.php:60`

---

### SF-02 — SHA1 password hashing (HIGH)

**Pattern**: `ttrss_users.pwd_hash` stores `"SHA1:<hex>"` hashes.
SHA1 has no cost factor and is breakable via GPU dictionary attack in seconds.
**Migration**: Dual-hash with argon2id (ADR-0008). See dimension `07-session-auth-surface.md`.
Source: `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php`

---

### SF-03 — mcrypt AES-128-CBC for feed credentials (CRITICAL)

**Pattern**: `include/crypt.php` uses deprecated `mcrypt_encrypt(MCRYPT_RIJNDAEL_128, ...)`
without authentication tag (no HMAC/AEAD). Vulnerable to padding oracle attack.
mcrypt extension removed in PHP 7.2; non-functional on PHP 8+.
**Migration**: Fernet (ADR-0009). One-time DB migration of `ttrss_feeds.auth_pass`.
Source: `source-repos/ttrss-php/ttrss/include/crypt.php:full`

---

### SF-04 — HTML sanitisation (HIGH — parity critical)

**Pattern**: `sanitize($str, $force_remove_images, $owner, $site_url)` in
`include/functions2.php:~834` applies a custom HTML allowlist to article content.
Also invoked via `HOOK_SANITIZE` (plugins can override).
**Risk**: If Python's bleach/lxml allowlist does not match exactly, either:
  a) Too permissive — XSS vulnerability in article content
  b) Too strict — broken article display
**Python fix**: Configure `bleach.clean()` with the identical tag/attribute/CSS
allowlist extracted from `sanitize()` in `functions2.php`.
**Frequency**: Every article stored or displayed.
Source: `source-repos/ttrss-php/ttrss/include/functions2.php:~834`

---

### SF-05 — Session fixation / hardening (MEDIUM)

**Pattern**: `include/sessions.php` implements:
  - `session.use_only_cookies = true` (no URL-based sessions)
  - `session.cookie_secure = true` over HTTPS
  - `validate_session()` IP-prefix + user-agent + pwd_hash checks
  - Session name `ttrss_sid` / `ttrss_sid_ssl`
  - No explicit `session_regenerate_id()` call on login — session fixation risk
**Python fix**: Flask-Login + Redis with `SESSION_PROTECTION = 'strong'`;
`login_user()` creates new session on every login (regeneration implicit).
Source: `source-repos/ttrss-php/ttrss/include/sessions.php:3–25`

---

### SF-06 — No CSRF protection on API (MEDIUM)

**Pattern**: `api/index.php` and `backend.php` do not implement CSRF tokens.
They rely on same-origin cookie policy + PHP sessions.
**Risk**: Cross-site request forgery via CORS-exempt simple requests.
**Python fix**: Flask-WTF CSRF protection on state-changing routes, or
`SameSite=Strict` cookie attribute. JSON API (api/) is lower risk
if credentials are not sent via simple GET forms.
Source: `source-repos/ttrss-php/ttrss/api/index.php`, `backend.php`

---

### SF-07 — FEED_CRYPT_KEY blank default (MEDIUM)

**Pattern**: `FEED_CRYPT_KEY` defaults to `''` in `config.php-dist:26`.
When blank, `encrypt_string()` is not called — feed passwords stored in plaintext.
Most deployments may not have feed credential encryption enabled.
**Python fix**: Require `FEED_CRYPT_KEY` to be set; enforce in startup sanity check.
Make Fernet key derivation mandatory; warn if blank at startup.
Source: `source-repos/ttrss-php/ttrss/config.php-dist:26`

---

### SF-08 — HOOK_QUERY_HEADLINES SQL fragment injection (HIGH)

**Pattern**: Plugin may return raw SQL fragment (e.g., `" AND score > 0 "`)
appended to a SELECT query in `classes/api.php:648` and `classes/feeds.php:298`.
A malicious or buggy plugin can inject arbitrary SQL.
**Python fix**: Replace with structured `query_builder` API (SQLAlchemy Select object).
Plugins mutate the query object via typed SQLAlchemy expressions only.
Source: `source-repos/ttrss-php/ttrss/classes/api.php:648`

---

### SF-09 — `$_REQUEST` superglobal merge (MEDIUM)

**Pattern**: `$_REQUEST` merges `$_GET`, `$_POST`, `$_COOKIE`.
If a parameter is expected from POST but accepted from GET, CSRF via GET becomes possible.
**Python fix**: Explicit `request.form.get()` vs `request.args.get()` per parameter.
Source: pervasive in `classes/api.php`, `classes/rpc.php`, etc.

---

### SF-10 — Method-string dispatch without whitelist (HIGH)

**Pattern**: `$handler->$method()` dispatches any PHP method whose name matches
the `op` parameter. No whitelist enforced by the base `Handler` class.
Subclasses define methods; only visible PHP methods are callable, but any public
method on a Handler subclass is potentially reachable.
**Python fix**: Flask route dispatch is explicit — every valid operation must
have a declared route. No dynamic method-name dispatch.
Source: `source-repos/ttrss-php/ttrss/classes/handler.php`

---

## Security surface summary

| Finding | Severity | Migration effort | ADR |
|---|---|---|---|
| SF-01 SQL injection | CRITICAL | HIGH (>500 sites) | SQLAlchemy parameterised queries |
| SF-02 SHA1 pwd hash | HIGH | MEDIUM (dual-hash migration) | ADR-0008 |
| SF-03 mcrypt AES | CRITICAL | MEDIUM (one-time DB migration) | ADR-0009 |
| SF-04 HTML sanitise | HIGH | MEDIUM (allowlist config) | Phase 2 |
| SF-05 Session fixation | MEDIUM | LOW (Flask-Login handles) | ADR-0007 |
| SF-06 No CSRF | MEDIUM | LOW (Flask-WTF) | Phase 2 |
| SF-07 Blank crypt key | MEDIUM | LOW (startup check) | ADR-0009 |
| SF-08 SQL hook injection | HIGH | MEDIUM (query_builder API) | Phase 2 ADR |
| SF-09 $_REQUEST merge | MEDIUM | MEDIUM (per-site audit) | Phase 4 |
| SF-10 Method dispatch | HIGH | LOW (explicit Flask routes) | Phase 1 |

---

## Source cross-references

| Construct | Source | Lines |
|---|---|---|
| SQL injection (login) | `source-repos/ttrss-php/ttrss/classes/api.php` | 60 |
| `escape_string()` wrapper | `source-repos/ttrss-php/ttrss/include/db.php` | full |
| `encrypt_string()` mcrypt | `source-repos/ttrss-php/ttrss/include/crypt.php` | full |
| `sanitize()` allowlist | `source-repos/ttrss-php/ttrss/include/functions2.php` | ~834 |
| Session hardening config | `source-repos/ttrss-php/ttrss/include/sessions.php` | 3–25 |
| `validate_session()` | `source-repos/ttrss-php/ttrss/include/sessions.php` | 38–100 |
| HOOK_QUERY_HEADLINES injection | `source-repos/ttrss-php/ttrss/classes/api.php` | 648 |
| `$_REQUEST` superglobal | `source-repos/ttrss-php/ttrss/classes/api.php` | pervasive |
| Method dispatch | `source-repos/ttrss-php/ttrss/classes/handler.php` | full |
| `FEED_CRYPT_KEY` | `source-repos/ttrss-php/ttrss/config.php-dist` | 26 |
| SHA1 hash scheme | `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` | `authenticate()` |
