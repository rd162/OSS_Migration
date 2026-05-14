# 07 — Session + Auth Surface

**Dimension**: `session-auth-surface`
**Derivation**: Cross-cutting — derived from include-graph C0 (bootstrap cluster:
`include/sessions.php`, `include/crypt.php`), db_table-graph C1 (users/sessions/version),
hook-graph C4 (HOOK_AUTH_USER), class-hierarchy C3/C4/C9 (Auth_Base, HOTP/TOTP,
Auth_Internal), call-graph C2 (Auth_Base + DbUpdater cluster)
**Phase**: Phase 1 — source knowledge extraction
**Status**: extracted ✓ · communities detected ✓ · research DEGRADED (no web access)

---

## Purpose

The session and auth surface captures the complete **authentication and session
management layer** of TT-RSS: how users are identified, how sessions are created and
validated, how credentials are stored and checked, and how the auth plugin extension
point (`HOOK_AUTH_USER`) allows replacing the default auth mechanism.

For the PHP → Python modernization this dimension:

- Drives the **Flask-Login + Redis session architecture** decision (ADR-0007)
- Defines the **argon2id dual-hash migration path** for existing SHA1 password hashes (ADR-0008)
- Defines the **Fernet re-encryption path** for mcrypt-encrypted feed credentials (ADR-0009)
- Provides the **pluggy hookspec** for `HOOK_AUTH_USER` (auth plugin parity)
- Surfaces the **`validate_session()` supplementary checks** that Flask-Login does not
  provide natively (IP prefix, user-agent hash, pwd_hash change detection)
- Identifies the `ttrss_access_keys` table as the token-auth mechanism for
  unauthenticated feed syndication

---

## Graph structure (derived)

No separate JSON artifact — derived from multiple graph dimensions.

| Component               | PHP source                       | Location in graphs        |
| ----------------------- | -------------------------------- | ------------------------- |
| Session handler         | `include/sessions.php`           | include C0, db_table C1   |
| DB session store        | `ttrss_sessions` table           | db_table C1               |
| User table              | `ttrss_users` table              | db_table C1               |
| Auth plugin interface   | `classes/iauthmodule.php`        | class-hierarchy (C9 root) |
| Auth base class         | `classes/auth/base.php`          | class-hierarchy C9        |
| Built-in auth plugin    | `plugins/auth_internal/init.php` | include C5, class C8      |
| HOOK_AUTH_USER dispatch | `include/functions.php`          | hook-graph C4             |
| TOTP library            | `lib/otphp/`                     | include C5, class C4      |
| Feed credential crypto  | `include/crypt.php`              | include C2, call-graph C2 |
| Access key table        | `ttrss_access_keys`              | db_table C0               |

---

## Communities (cross-dimension composition)

### AUTH-01 — PHP session handler (DB-backed)

**Files**: `include/sessions.php`
**Tables**: `ttrss_sessions`

PHP's native session system is overridden by `session_set_save_handler()` with
five custom callbacks: `ttrss_open/read/write/destroy/gc`.

Session data flow:

```
PHP session_start() → ttrss_read($id)
  → SELECT data FROM ttrss_sessions WHERE id='$id'
  → base64_decode(data) → PHP deserialise → $_SESSION
PHP request end → ttrss_write($id, $data)
  → base64_encode(serialize($_SESSION))
  → UPDATE ttrss_sessions SET data=..., expire=... WHERE id='$id'
```

Session name: `ttrss_sid` (HTTP) / `ttrss_sid_ssl` (HTTPS)
Session GC: 75% probability per request (`session.gc_probability = 75`)
Session lifetime: `SESSION_COOKIE_LIFETIME` config constant (0 = browser session)

`validate_session()` supplementary checks (run every request):

1. `VERSION_STATIC` in session matches current version — else invalidate
2. IP prefix check (`SESSION_CHECK_ADDRESS` = 0/1/2: none/class-C/class-B)
3. SHA1 of `HTTP_USER_AGENT` matches session — else invalidate
4. `pwd_hash` in session matches current `ttrss_users.pwd_hash` — else invalidate
5. Schema version in session matches current — else invalidate

Source: `source-repos/ttrss-php/ttrss/include/sessions.php:38`

**Python target**:

- `ttrss_sessions` DB table → Flask-Login + Redis (server-side session)
- `session_set_save_handler()` → Flask session interface (Redis backend)
- `validate_session()` → `@before_request` function replicating checks 1–5
- Session cookie: signed cookie pointing to Redis key
- `ttrss_sessions` table preserved in schema for pgloader migration; never written
  by Python app; decommissioned post-cutover

---

### AUTH-02 — User identity table

**Table**: `ttrss_users`

Key columns:

```sql
id           serial primary key,
login        varchar(320) unique not null,
pwd_hash     varchar(250),    -- "SHA1:<hex>" or "MODE:<hash>"
salt         varchar(250),    -- legacy salt field
access_level int default 0,  -- 0=user, 10=admin
email        varchar(250),
otp_enabled  bool default false,
created_at   timestamp,
last_login   timestamp,
...
```

`access_level` values:

- `0` — regular user (default)
- `10` — administrator (access to Pref_System, user management)

`AUTH_AUTO_CREATE` config: if true, external auth plugins (LDAP, OAuth) auto-create
rows in `ttrss_users` for newly authenticated external users via `Auth_Base::auto_create_user()`.
Source: `source-repos/ttrss-php/ttrss/classes/auth/base.php`

**Python target**:

- `User` SQLAlchemy model — `__tablename__ = "ttrss_users"`
- `pwd_hash` column preserved during migration; migrated to argon2id on first login
- `access_level` preserved; `User.is_admin` property returns `access_level >= 10`
- `otp_enabled` / OTP secret stored in `ttrss_user_prefs` (pref key `OTP_SECRET_KEY`)

---

### AUTH-03 — Auth plugin system (HOOK_AUTH_USER)

**Files**: `classes/iauthmodule.php`, `classes/auth/base.php`,
`plugins/auth_internal/init.php`, `include/functions.php`

`IAuthModule` interface contract:

```php
interface IAuthModule {
    function get_login();           // return login string
    function authenticate($login, $password); // return user_id or false
    function logout($token = false);
    function check_remember_me($login); // optional remember-me
}
```

`authenticate_user($login, $password, $check_only)` in `include/functions.php`:

1. Calls `PluginHost::run_hooks(HOOK_AUTH_USER, "hook_auth_user", [$login, $password])`
2. First plugin to return a non-false user ID wins
3. On success: loads user preferences, sets `$_SESSION["uid"]`, etc.

`Auth_Internal::hook_auth_user($args)` (built-in, always registered):

1. Looks up `ttrss_users WHERE login = '$login'`
2. Computes `SHA1($salt . $password)` (or newer scheme)
3. Compares to `ttrss_users.pwd_hash`
4. Returns `user_id` on match, `false` on failure
5. If `otp_enabled`: verifies TOTP code from `$args['otp']`

Source: `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php`

**Python target**:

```python
@hookspec(firstresult=True)
def hook_auth_user(self, login: str, password: str, otp: str = "") -> int | None:
    """Return user_id on success, None to pass to next plugin."""

# Auth_Internal hookimpl:
@hookimpl
def hook_auth_user(self, login, password, otp=""):
    user = db.session.query(User).filter_by(login=login).first()
    if not user:
        return None
    # Try argon2id first, fall back to SHA1 (then upgrade)
    if verify_password(password, user.pwd_hash):
        if user.otp_enabled:
            if not pyotp.TOTP(get_pref("OTP_SECRET_KEY", user.id)).verify(otp):
                return None
        return user.id
    return None
```

---

### AUTH-04 — Feed credential encryption

**File**: `include/crypt.php`
**Config**: `FEED_CRYPT_KEY` constant

```php
function encrypt_string($str) {
    $key = hash('SHA256', FEED_CRYPT_KEY, true);
    $iv = mcrypt_create_iv(mcrypt_get_iv_size(MCRYPT_RIJNDAEL_128, MCRYPT_MODE_CBC), MCRYPT_RAND);
    $encstr = mcrypt_encrypt(MCRYPT_RIJNDAEL_128, $key, $str, MCRYPT_MODE_CBC, $iv);
    return base64_encode($iv) . ":" . base64_encode($encstr);
}
```

This uses `mcrypt` (removed from PHP 7.2, `MCRYPT_RIJNDAEL_128` = AES-128 CBC).
Encrypted feed credentials stored in `ttrss_feeds.auth_pass` (VARCHAR).
Format: `<base64(iv)>:<base64(ciphertext)>`

Source: `source-repos/ttrss-php/ttrss/include/crypt.php`

**Python target**:

```python
# ttrss/utils/crypt.py
from cryptography.fernet import Fernet

def encrypt_string(plaintext: str, key: str) -> str:
    f = Fernet(derive_fernet_key(key))
    return f.encrypt(plaintext.encode()).decode()

def decrypt_string(ciphertext: str, key: str) -> str:
    f = Fernet(derive_fernet_key(key))
    return f.decrypt(ciphertext.encode()).decode()
```

**Migration requirement**: During data migration (pgloader + post-migration script),
decrypt all `ttrss_feeds.auth_pass` values using the mcrypt key, re-encrypt using
Fernet. The mcrypt decryption must be done in a Python script that wraps the
mcrypt-compatible `pyaes` or `pycryptodome` library for the one-time migration.

---

### AUTH-05 — TOTP / OTP

**Files**: `lib/otphp/lib/otp.php`, `lib/otphp/lib/totp.php`,
`lib/phpqrcode/phpqrcode.php`
**Table**: `ttrss_user_prefs` (pref key: `OTP_SECRET_KEY`)

TOTP follows RFC 6238 (Google Authenticator compatible):

- `TOTP::generateOTP($counter)` — generates 6-digit HMAC-SHA1 code
- Base32 secret stored in `ttrss_user_prefs` per user
- QR code enrollment via `lib/phpqrcode/` generating PNG image

**Python target**:

```python
import pyotp
secret = get_pref("OTP_SECRET_KEY", user_id)
totp = pyotp.TOTP(secret)
is_valid = totp.verify(user_submitted_code)
# QR code for enrollment:
import qrcode
uri = totp.provisioning_uri(name=user.login, issuer_name="TT-RSS")
img = qrcode.make(uri)
```

---

### AUTH-06 — Access key token auth

**Table**: `ttrss_access_keys`
**Usage**: `public.php?op=rss&key=<token>` — unauthenticated RSS syndication

```sql
create table ttrss_access_keys (
  id         serial primary key,
  access_key varchar(250) not null,
  feed_id    integer,
  is_cat     boolean default false,
  owner_uid  integer not null references ttrss_users(id)
);
```

Access keys allow per-feed RSS export without session auth. Generated per-user,
per-feed from `Handler_Public::generateFeedKey()`.

**Python target**: `AccessKey` model; `verify_token(key)` lookup function;
`@token_required` decorator for the `/feed/<key>` syndication route.

---

## Dependency levels (migration order)

| Level | Component                                                 | Rationale                                     |
| ----- | --------------------------------------------------------- | --------------------------------------------- |
| 0     | `User` model, `ttrss_users` schema                        | Root dependency for everything                |
| 1     | Password hashing utils (argon2id + SHA1 verify)           | Required before login() works                 |
| 2     | Flask-Login setup, session config                         | Required before any authenticated route       |
| 3     | `validate_session()` equivalents in `@before_request`     | Required before UI routes                     |
| 4     | Auth plugin system (pluggy hookspec + Auth_Internal impl) | Required for login flow                       |
| 5     | TOTP verification                                         | Required for OTP-enabled users                |
| 6     | Feed credential encryption (Fernet)                       | Required before feed update with auth'd feeds |
| 7     | Access key token auth                                     | Required for public RSS syndication           |

---

## Modernization impact

### Critical security improvements (intentional divergences)

1. **SHA1 → argon2id password hashing** (ADR-0008):
   All `ttrss_users.pwd_hash` values are SHA1 hashes.
   Python: verify SHA1 on first login (for migration compatibility), then
   re-hash with argon2id and overwrite. After migration window closes, reject
   SHA1-only accounts (force password reset).
   Source: `plugins/auth_internal/init.php` `authenticate()` method.
   Frequency: every login. Severity: CRITICAL security improvement.

2. **mcrypt → Fernet** (ADR-0009):
   `include/crypt.php` uses deprecated mcrypt AES-128 CBC.
   Python: `cryptography.fernet.Fernet`. One-time migration of `ttrss_feeds.auth_pass`.
   Source: `source-repos/ttrss-php/ttrss/include/crypt.php`
   Frequency: every feed with stored credentials. Severity: CRITICAL.

3. **DB sessions → Redis sessions**:
   PHP serialised session data in `ttrss_sessions` cannot be read by Python.
   All active user sessions are invalidated at cutover (users must re-login).
   This is an expected one-time disruption; document in deployment notes.
   Source: `source-repos/ttrss-php/ttrss/include/sessions.php`
   Severity: HIGH (UX impact at deployment, no data loss).

4. **`validate_session()` IP + user-agent checks**:
   These supplementary checks are not provided by Flask-Login natively.
   Must be implemented as a custom `@before_request` function.
   The IP prefix check (`SESSION_CHECK_ADDRESS = 1/2`) must be config-driven
   (some deployments disable it for NAT environments).
   Source: `source-repos/ttrss-php/ttrss/include/sessions.php:38`
   Severity: MEDIUM.

5. **SQL injection in login** (security fix):
   `API::login()` builds `WHERE login = '$login'` with `escape_string()`.
   Python uses parameterised query: `filter_by(login=login)`.
   Source: `source-repos/ttrss-php/ttrss/classes/api.php:55`
   Severity: HIGH security fix.

---

## Divergences seeded

- D-SA-01: SHA1 → argon2id (→ `12-semantic-discrepancies.md`)
- D-SA-02: mcrypt AES-128 → Fernet (→ `12-semantic-discrepancies.md`)
- D-SA-03: DB session store → Redis (session invalidation at cutover)
- D-SA-04: `validate_session()` supplementary checks — not in Flask-Login default
- D-SA-05: OTP secret storage in `ttrss_user_prefs` — must use same pref key

---

## Source cross-references

| Construct                               | Source                                                        | Line(s)                          |
| --------------------------------------- | ------------------------------------------------------------- | -------------------------------- |
| DB session handler                      | `source-repos/ttrss-php/ttrss/include/sessions.php`           | full                             |
| `validate_session()`                    | `source-repos/ttrss-php/ttrss/include/sessions.php`           | 38–100                           |
| Session callbacks                       | `source-repos/ttrss-php/ttrss/include/sessions.php`           | 100–145                          |
| `encrypt_string()` / `decrypt_string()` | `source-repos/ttrss-php/ttrss/include/crypt.php`              | full                             |
| `IAuthModule` interface                 | `source-repos/ttrss-php/ttrss/classes/iauthmodule.php`        | full                             |
| `Auth_Base::auto_create_user()`         | `source-repos/ttrss-php/ttrss/classes/auth/base.php`          | full                             |
| `Auth_Internal` built-in auth           | `source-repos/ttrss-php/ttrss/plugins/auth_internal/init.php` | full                             |
| `authenticate_user()` + HOOK_AUTH_USER  | `source-repos/ttrss-php/ttrss/include/functions.php`          | `authenticate_user()`            |
| `API::login()` (SQL injection risk)     | `source-repos/ttrss-php/ttrss/classes/api.php`                | 55–110                           |
| `ttrss_users` schema                    | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`  | `create table ttrss_users`       |
| `ttrss_sessions` schema                 | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`  | `create table ttrss_sessions`    |
| `ttrss_access_keys` schema              | `source-repos/ttrss-php/ttrss/schema/ttrss_schema_pgsql.sql`  | `create table ttrss_access_keys` |
| TOTP OTP class                          | `source-repos/ttrss-php/ttrss/lib/otphp/lib/totp.php`         | full                             |
| `FEED_CRYPT_KEY` config                 | `source-repos/ttrss-php/ttrss/config.php-dist`                | `FEED_CRYPT_KEY`                 |
| `SESSION_CHECK_ADDRESS`                 | `source-repos/ttrss-php/ttrss/config.php-dist`                | `SESSION_CHECK_ADDRESS`          |
