# Dimension: call-graph + class-hierarchy + include-graph · Community: CG-3

## Label: Auth / Schema Migration / OTP

**Source communities merged:**
- call-graph community 2 (77 members: Auth_Base, Auth_Internal, DbUpdater, Handler_Public::dbupdate/sharepopup)
- call-graph community 6 (54 members: Db_PDO::connect, HOTP, OTP, TOTP, Base32, DB connect methods)
- class-graph communities 8 (Plugin/Auth_Internal), 9 (Auth_Base), 17 (DbUpdater)
- include-graph community 5 (plugins/auth_internal/init.php, lib/otphp/*)

⚠ NOTE: ∆2 DEGRADED — all findings below are training-knowledge only [TRAINING].
No web search available. Verify against current library documentation before Phase 2.

---

## Members

| File | Level | Est. LOC | Role |
|------|-------|----------|------|
| `classes/auth/base.php` | L1 | ~80 | Auth_Base abstract class — interface contract |
| `plugins/auth_internal/init.php` | L2 | ~200 | Auth_Internal — SHA1/salted-SHA1 password auth |
| `classes/dbupdater.php` | L1 | ~120 | DbUpdater — schema version migration runner |
| `include/sessions.php` | L0 | ~150 | Custom PHP session handlers (ttrss_sessions table) |
| `include/functions.php` | L0 | ~1500 | authenticate_user(), login_sequence(), validate_session() |
| `include/crypt.php` | L0 | ~40 | encrypt_string / decrypt_string (mcrypt AES-128-CBC) |
| `lib/otphp/lib/otp.php` | L0 | ~80 | OTP base class |
| `lib/otphp/lib/hotp.php` | L0 | ~60 | HOTP counter-based OTP |
| `lib/otphp/lib/totp.php` | L0 | ~60 | TOTP time-based OTP |
| `lib/otphp/vendor/base32.php` | L0 | ~80 | Base32 encode/decode for OTP secrets |
| `classes/pluginhost.php` (HOOK_AUTH_USER) | L0 | partial | Hook dispatch for auth plugins |
| `schema/versions/pgsql/*.sql` | L0 | varies | Incremental migration scripts (up to v124) |

---

## Representative constructs

**Authentication:**
- `Auth_Base::authenticate($login, $password)` — abstract; implemented by Auth_Internal
- `Auth_Internal::authenticate($login, $password)` — verifies SHA1/salted-SHA1, calls `auth_module_get_user_id()`
- `functions.php::authenticate_user($login, $password, $check_only=false)` — outer auth function; fires `HOOK_AUTH_USER`; writes `$_SESSION`
- `functions.php::login_sequence()` — full login flow: POST handler → `authenticate_user` → session init → plugin load
- `functions.php::validate_session()` — per-request session check: version match, IP check, schema version check
- `functions.php::logout_user()` — clears session, redirects
- `include/sessions.php::session_get_schema_version()` — reads `ttrss_version` table; used in session validation

**Password hashing (source pattern):**
```php
// Auth_Internal::authenticate (inferred from schema + auth flow)
// ttrss_users.pwd_hash format: "SHA1:<sha1(password)>"
// or salted:                   "SHA1:<sha1(salt + password)>"
// salt stored in ttrss_users.salt
$stored = "SHA1:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8";  // SHA1("password")
```

**OTP/TOTP:**
- `TOTP::__construct($secret)` — creates TOTP with Base32-decoded secret
- `TOTP::at($timestamp)` — generates 6-digit code for timestamp window
- `TOTP::verify($otp, $timestamp, $window)` — verifies OTP within time window
- `ttrss_users.otp_enabled` — boolean flag; `ttrss_users.otp_secret` — Base32 secret (inferred)

**Schema migration:**
- `DbUpdater::getSchemaVersion()` — reads `ttrss_version.schema_version`
- `DbUpdater::isUpdateRequired()` — compares DB version to `SCHEMA_VERSION` constant
- `DbUpdater::performUpdateTo($version)` — applies `schema/versions/pgsql/<version>.sql`
- `DbUpdater::getSchemaLines($version)` — reads SQL migration file line by line

**Session storage:**
- Custom PHP session save handlers registered in `sessions.php`
- `ttrss_open($save_path, $session_name)` — DB connect
- `ttrss_close()` — no-op
- `ttrss_read($id)` — `SELECT data FROM ttrss_sessions WHERE id = ?`
- `ttrss_write($id, $data)` — UPSERT into `ttrss_sessions`
- `ttrss_destroy($id)` — `DELETE FROM ttrss_sessions`
- `ttrss_gc($lifetime)` — `DELETE WHERE expire < NOW()`

**Encryption:**
- `encrypt_string($str)` — mcrypt AES-128-CBC, SHA256-derived key from `FEED_CRYPT_KEY`; IV prepended as `<base64_iv>:<base64_ciphertext>`
- `decrypt_string($str)` — reverse of above

---

## Research findings [TRAINING — unverified]

### PHP auth patterns
- TT-RSS implements a plugin-based auth architecture where `HOOK_AUTH_USER` allows
  third-party plugins to authenticate users (e.g., LDAP, OAuth).
  Auth_Internal is the bundled default plugin.
- SHA1 password hashing (even salted) is considered broken for passwords;
  Python argon2-cffi is the current recommended replacement [T2 — industry standard, 2024].
- PHP `mcrypt` extension was deprecated in PHP 7.1 and removed in PHP 7.2.
  All production TT-RSS installations should already have moved off mcrypt,
  but the source code still uses it — indicating the code may have PHP 5.x era origins [T2 — TRAINING].
- TOTP (RFC 6238) is compatible across implementations: the OTPHP library's
  Base32 secret format is identical to `pyotp` (Python) [T2 — TRAINING].

### PHP session security
- TT-RSS uses DB-backed sessions (`ttrss_sessions` table) for centralized storage,
  which enables multi-server deployments but requires careful session GC [T2 — TRAINING].
- `SESSION_CHECK_ADDRESS` setting (0/1/2) optionally binds sessions to IP;
  full IP check (`case 2`) breaks IPv6 and NAT setups [T2 — TRAINING].
- `session_regenerate_id(true)` on login prevents session fixation [T1 — PHP docs].

### Schema migration
- `DbUpdater` is a hand-rolled migration runner using numbered SQL files.
  It is functionally equivalent to Alembic (Python) revision files [T2 — TRAINING].
- Migration scripts in `schema/versions/pgsql/` are numbered 21–124.
  Gaps in the sequence (e.g., 35, 34, 21 visible in directory listing) indicate
  some schema versions applied to MySQL only, or selective feature branches [T2 — source scan].

### OTP compatibility
- `lib/otphp/` is a PHP port of a Ruby TOTP library.
  Python `pyotp` implements RFC 6238 (TOTP) and RFC 4226 (HOTP) identically.
  Secret migration: Base32-encoded secret from `ttrss_users` column is directly usable
  with `pyotp.TOTP(secret)` without conversion [T2 — TRAINING].

---

## Target-side mapping

| PHP component | Python / Flask replacement | Notes |
|---------------|---------------------------|-------|
| `Auth_Base` abstract class | `ABC` / `pluggy` hookspec `@hookspec def authenticate(login, password)` | pluggy allows multiple auth backends |
| `Auth_Internal` (SHA1 verify) | `argon2.PasswordHasher().verify()` + dual-hash migration path | Detect `SHA1:` prefix → verify → rehash |
| `authenticate_user()` | Flask-Login `login_user(user, remember=...)` | `login_user` sets `current_user` in session |
| `validate_session()` | `@login_required` decorator + `LoginManager.user_loader` callback | Schema version check → separate middleware |
| `login_sequence()` | `POST /auth/login` Flask route | Blueprint: `auth_bp` |
| `logout_user()` | `logout_user()` + `flask.session.clear()` | Flask-Login built-in |
| `ttrss_open/read/write/destroy/gc` session handlers | Flask-Session with Redis backend | `SESSION_TYPE = 'redis'` |
| `ttrss_sessions` table | Redis `SETEX session:<id> <data>` | Drop DB sessions table; migrate active sessions |
| `HOOK_AUTH_USER` | pluggy `@hookspec def authenticate_user(login, password)` | `firstresult=True` — first non-None wins |
| `DbUpdater` | Alembic `alembic upgrade head` | Migration files in `alembic/versions/` |
| `schema/versions/pgsql/*.sql` | Alembic revision `.py` files | One Alembic revision per SQL version |
| `encrypt_string` (mcrypt) | `cryptography.fernet.Fernet(key).encrypt(data)` | Key from `FEED_CRYPT_KEY` env var |
| `decrypt_string` (mcrypt) | `Fernet(key).decrypt(token)` | Need data migration for existing ciphertext |
| `lib/otphp/TOTP` | `pyotp.TOTP(secret)` | Secret is identical Base32; direct swap |
| `ttrss_users.otp_enabled` | Column preserved; Python checks `user.otp_enabled` | No change needed |

---

## Divergences spotted (seeds for ∆10b)

**DIV-AUTH-01 — SHA1 password upgrade path**
- Source: `ttrss_users.pwd_hash = "SHA1:<hex>"` or `"SHA1:<sha1(salt+pass)>"`.
- Target: argon2id hash in same column.
- Gap: Must detect old hash format on login → verify → silently rehash → commit.
  If user's password is correct but stored as SHA1, we must rehash without user knowing.
- Frequency: All existing users (100% of `ttrss_users` rows).
- Risk: Silent migration fails if argon2 write fails → user locked out. Must be atomic.

**DIV-AUTH-02 — mcrypt ciphertext format incompatibility**
- Source: `"<base64(iv)>:<base64(ciphertext)>"` using PKCS7-padded AES-128-CBC.
- Target: Fernet uses a different format (version byte + timestamp + IV + ciphertext + HMAC).
- Gap: Existing encrypted `auth_pass` values in `ttrss_feeds` cannot be decrypted by Fernet.
  Requires a one-time migration: decrypt with mcrypt-equivalent (PyCryptodome AES-128-CBC),
  re-encrypt with Fernet.
- Frequency: All feeds where `auth_pass != ''` and `auth_pass_encrypted = true`.
- Risk: If migration is partial, some feeds lose their credentials.

**DIV-AUTH-03 — PHP pass-by-reference in HOOK_AUTH_USER**
- Source: `run_hooks(PluginHost::HOOK_AUTH_USER, &$user_info)` mutates `$user_info` array.
- Target: Python cannot pass dicts by reference to pluggy hooks the same way;
  pluggy's `firstresult=True` returns the first non-None value.
- Gap: PHP pattern allows multiple auth plugins to annotate the user dict;
  Python pattern returns first successful auth result only.
- Impact: MEDIUM — auth plugin behaviour contracts change slightly.

**DIV-AUTH-04 — Session IP binding**
- Source: `SESSION_CHECK_ADDRESS` mode 1/2 binds session to `/16` subnet or full IP.
- Target: Not a Flask-Login built-in; must be custom middleware.
- Gap: IPv6 clients may fail mode 2 (full IP) checks if they change addresses mid-session
  (which is normal for IPv6).

**DIV-AUTH-05 — SINGLE_USER_MODE bypass**
- Source: `validate_session()` returns `true` immediately if `SINGLE_USER_MODE`.
  `authenticate_user()` auto-logs in as user ID 1 if SINGLE_USER_MODE.
- Target: Flask-Login equivalent: `LoginManager.anonymous_user` or always-logged-in fixture.
- Gap: Must preserve this operating mode for single-user deployments.

**DIV-SCHEMA-01 — Schema migration numbering**
- Source: Migration scripts are numbered SQL files (21–124); some numbers skipped.
- Target: Alembic uses UUIDs + `down_revision` chains, not sequential integers.
- Gap: Must generate one Alembic revision per SQL migration file,
  preserving the logical sequence from 21 → 124 without gaps affecting upgrade paths.

---

## Open questions (Phase 2 ADR items)

1. **ADR candidate**: Should DB sessions migrate to Redis or to signed Flask cookies?
   Redis provides server-side revocation; signed cookies reduce infrastructure dependency.
   TT-RSS's multi-user model likely benefits from server-side revocation (logout-all-devices).

2. **ADR candidate**: argon2id parameters — what time/memory cost factors for
   a self-hosted instance on typical VPS hardware (2 cores, 1GB RAM)?
   PHP default SHA1 has no parameters; Python argon2-cffi defaults are:
   `time_cost=2, memory_cost=65536, parallelism=2` — verify these are appropriate.

3. **ADR candidate**: Should mcrypt→Fernet migration happen at startup (migrate all),
   at feed-fetch time (lazy per-feed), or as a one-off CLI command?
   Startup migration risks long startup on large deployments.
   Lazy migration risks credential loss if migration fails silently.
   CLI command is the safest but requires operator intervention.

4. **Research needed**: Does `pyotp.TOTP` implement the same TOTP window tolerance
   as `lib/otphp/TOTP::verify($otp, $timestamp, $window=1)`?
   PHP: ±1 time step (default). pyotp: `valid_window` parameter, default 0 (exact).
   Must set `valid_window=1` for backwards-compatible OTP verification.

5. **Research needed**: Current Alembic best practice for importing raw SQL into
   revision files (for the 21–124 migration chain already expressed as .sql files).
   Alembic supports `op.execute(text(...))` for raw SQL in revision files.
