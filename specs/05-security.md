# 05 — Security Assessment Spec

## Summary

10 findings ranked by severity. Several critical issues should be **fixed during migration** rather than replicated.

## Findings

### CRITICAL

#### 1. SHA1 Password Hashing
- **Location**: `ttrss/include/functions2.php:1481-1489` (`encrypt_password()`)
- **Issue**: Uses SHA1 (broken) and SHA256 with simple salt. No bcrypt, argon2, or PBKDF2.
- **Legacy support**: Unsalted SHA1 hashes still accepted for login
- **Migration action**: Replace with `bcrypt` or `argon2id` via Python's `passlib` or `bcrypt` library

#### 2. SINGLE_USER_MODE Auth Bypass
- **Location**: `ttrss/include/functions.php:750-770`
- **Issue**: When enabled, bypasses all authentication — sets `$_SESSION["uid"] = 1` with admin access
- **Migration action**: Remove or gate behind strong admin password requirement

### HIGH

#### 3. Deprecated Encryption (mcrypt)
- **Location**: `ttrss/include/crypt.php`
- **Issue**: Uses `mcrypt` (removed in PHP 7.1+) with RIJNDAEL-128 for feed credential encryption
- **Migration action**: Use Python `cryptography` library (Fernet or AES-GCM)

#### 4. SSL Verification Disabled
- **Location**: `ttrss/include/functions.php:343-436`
- **Issue**: `CURLOPT_SSL_VERIFYPEER = FALSE` for all feed fetching
- **Migration action**: Enable SSL verification, use `requests` library with default cert validation

### MEDIUM

#### 5. No Prepared Statements
- **Location**: All 200+ `db_query()` call sites
- **Issue**: Raw SQL with `db_escape_string()` — relies on escaping rather than parameterization
- **Migration action**: Use SQLAlchemy with parameterized queries or ORM

#### 6. Weak CSRF Token Generation
- **Location**: `ttrss/include/functions.php:732`
- **Issue**: Token generated with `uniqid(rand(), true)` — not cryptographically secure
- **Migration action**: Use `secrets.token_hex()` or framework-native CSRF

#### 7. Missing Security Headers
- **Location**: All entry points
- **Issue**: No X-Frame-Options, X-Content-Type-Options, Content-Security-Policy, HSTS
- **Migration action**: Add security headers via middleware

#### 8. Debug Mode Information Disclosure
- **Location**: `ttrss/classes/feeds.php:213`, `ttrss/include/functions2.php:751`, `ttrss/include/rssfuncs.php:205`
- **Issue**: `$_REQUEST["debug"]` parameter prints SQL queries and timing to output
- **Migration action**: Remove debug param or gate behind admin auth + environment flag

#### 9. Inconsistent XSS Protection
- **Location**: Throughout codebase
- **Issue**: `htmlspecialchars()` used but not consistently. No centralized output filtering.
- **Migration action**: Use template engine with auto-escaping (Jinja2 `autoescape=True`)

#### 10. Password Hash in Session
- **Location**: `ttrss/include/functions.php:739`
- **Issue**: Session stores password hash for validation — exposed if session storage compromised
- **Migration action**: Use session token validation instead of storing password hash

## Authentication Architecture

### Flow

```
1. POST login form → authenticate_user($login, $password)
2. Plugin hook: HOOK_AUTH_USER → auth_internal or custom
3. Session created: uid, name, access_level, csrf_token, ip_address, user_agent, pwd_hash
4. Cookie: ttrss_sid (or ttrss_sid_ssl for HTTPS)
5. Each request: validate_session() checks IP, UA hash, pwd_hash, schema version
```

### Session Validation Checks
- IP address partial match (configurable: 0=off, 1=first 3 octets, 2=first 2, 3=full)
- User agent SHA1 hash comparison
- Password hash unchanged since login
- Schema version consistency
- Session not expired

### Authorization Levels
- 0: Regular user
- 5: Power user
- 10: Administrator
- Checked via `$_SESSION["access_level"] >= 10` for admin functions

### Session Storage
- Database-backed via custom session handlers (`ttrss_sessions` table)
- Data stored as base64-encoded strings
- Session name: `ttrss_sid` (with `_ssl` suffix for HTTPS)
- `session.use_only_cookies = true` enforced

## Input Handling

### User Input Sources
- `$_REQUEST` — used extensively (no separation of GET/POST)
- `$_SESSION` — session state
- `$_SERVER` — HTTP headers (IP, User-Agent)
- `$_FILES` — OPML import only

### Sanitization Methods
- `db_escape_string()` — SQL escaping (wraps DB adapter)
- `htmlspecialchars()` — HTML entity encoding
- `strip_tags()` — HTML tag removal
- `(int)` casting — numeric validation
- `basename()` — path traversal protection (image.php)

## External Request Surface (SSRF)

| Function | Location | Risk |
|----------|----------|------|
| `fetch_file_contents()` | functions.php:343 | Feed URLs from DB, SSL verify OFF |
| `file_get_contents()` | functions.php:464 | Fallback fetcher |
| `get_favicon_url()` | functions.php:504 | Favicon from arbitrary sites |

**Mitigations present**: Timeouts (45s), URL stored in DB (not direct from request)
**Missing**: URL whitelist, SSRF protection, SSL verification

## Cookie Configuration

| Attribute | Status |
|-----------|--------|
| Secure | Set when HTTPS detected |
| HttpOnly | Enforced via `use_only_cookies` |
| SameSite | NOT SET (missing) |
| Lifetime | Configurable (default 86400s) |

## Python Migration Security Checklist

- [ ] Replace SHA1 with bcrypt/argon2id password hashing
- [ ] Use SQLAlchemy parameterized queries (eliminate SQL injection)
- [ ] Enable SSL certificate verification for feed fetching
- [ ] Use `secrets` module for CSRF tokens and API keys
- [ ] Add security headers middleware (CSP, X-Frame-Options, HSTS, etc.)
- [ ] Use Jinja2 auto-escaping for all HTML output
- [ ] Remove debug parameter or restrict to admin + dev environment
- [ ] Use `cryptography` library for feed credential encryption
- [ ] Implement SameSite cookie attribute
- [ ] Remove SINGLE_USER_MODE or add admin password gate
- [ ] Don't store password hash in session — use token-based validation
- [ ] Add rate limiting on login endpoint
- [ ] Consider SSRF protection for feed URL fetching
