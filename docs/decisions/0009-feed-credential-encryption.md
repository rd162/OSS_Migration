# ADR-0009: Feed Credential Encryption

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase encrypts feed authentication credentials (HTTP Basic Auth passwords stored in `ttrss_feeds.auth_pass`) using the `mcrypt` extension with AES-128-CBC. The encryption key is derived from `FEED_CRYPT_KEY` in `config.php`. The `mcrypt` PHP extension has been deprecated since PHP 7.1 and removed in PHP 7.2, making the existing encryption code unmaintainable even in PHP.

The Python migration must:
- Decrypt existing feed passwords encrypted with mcrypt AES-128-CBC
- Re-encrypt them with a modern, maintained encryption library
- Support key rotation in the future
- Handle the transition transparently (feeds must continue to authenticate)

## Options

### A: Fernet (cryptography Library)

Use `Fernet` from the `cryptography` package. Fernet provides AES-128-CBC with HMAC-SHA256 authentication, key derivation, and timestamped tokens. It is a high-level, misuse-resistant API.

- Built-in authentication (HMAC) prevents tampering
- Timestamped tokens enable key rotation policies
- Single-key symmetric encryption
- Well-audited `cryptography` library

### B: AES-GCM (cryptography Library)

Use `AES-GCM` directly from the `cryptography` package. GCM provides authenticated encryption with associated data (AEAD). More control than Fernet but more room for misuse.

- Authenticated encryption (built-in integrity)
- Requires manual nonce management (critical to never reuse)
- Industry standard for modern encryption
- Lower-level API than Fernet

### C: Keep mcrypt-Compatible Format

Use a Python mcrypt-compatible library (e.g., `pycryptodome` in mcrypt compat mode) to read/write the same AES-128-CBC format. This allows the PHP and Python systems to share the same encrypted values during a transition period.

- Zero migration effort for existing data
- Maintains deprecated, unauthenticated encryption (CBC without HMAC)
- Vulnerable to padding oracle attacks
- No path forward for key rotation

## Trade-off Analysis

| Criterion | A: Fernet | B: AES-GCM | C: mcrypt-Compatible |
|-----------|-----------|------------|---------------------|
| Security (authenticated encryption) | Yes (HMAC-SHA256) | Yes (GCM tag) | No (CBC only) |
| Misuse resistance | High (opinionated API) | Medium (nonce management) | Low |
| Migration script needed | Yes (decrypt old, re-encrypt) | Yes (decrypt old, re-encrypt) | No |
| Key rotation support | Built-in (MultiFernet) | Manual | None |
| Library maintenance | Excellent (pyca/cryptography) | Excellent (pyca/cryptography) | Poor (mcrypt deprecated) |
| PHP interoperability during transition | No (different format) | No (different format) | Yes |
| Implementation complexity | Low | Medium | Low |
| Padding oracle resistance | N/A (authenticated) | N/A (authenticated) | Vulnerable |

## Preliminary Recommendation

**Option A (Fernet)** — provides the strongest security guarantees with the simplest API. The migration path is:

1. Write a one-time migration script that reads existing mcrypt-encrypted passwords using `pycryptodome` (AES-128-CBC decrypt with the existing `FEED_CRYPT_KEY`)
2. Re-encrypt each password with Fernet using a new key derived from the same or rotated secret
3. Update the `auth_pass` column with the new Fernet tokens
4. Mark migrated rows (e.g., prefix `fernet:` or a separate column)

`MultiFernet` supports transparent key rotation: add a new key, and old tokens remain decryptable until re-encrypted.

## Decision

**TBD**

## Consequences

- If Option A: requires a data migration script run once during deployment
- If Option A: Fernet tokens are ~2x larger than raw AES-CBC ciphertext (base64 + HMAC + timestamp)
- If Option A: MultiFernet enables future key rotation without downtime
- If Option B: similar benefits to A but requires careful nonce management
- If Option C: no migration effort but perpetuates a known-vulnerable encryption scheme
- All options: the `FEED_CRYPT_KEY` secret must be securely transferred to the Python deployment
