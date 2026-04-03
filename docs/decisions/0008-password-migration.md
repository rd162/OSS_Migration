# ADR-0008: Password Hash Migration

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase stores user passwords as SHA1 hashes (via `sha1()`) with a salt stored alongside in the `ttrss_users` table (`pwd_hash` column, format `sha1:salt:hash`). Some older records may use unsalted MD5. SHA1 is cryptographically broken for collision resistance and considered inadequate for password storage — it lacks key stretching, making brute-force attacks feasible with modern GPUs.

The Python migration must upgrade to a modern password hashing algorithm (bcrypt, argon2, or scrypt) while preserving the ability for existing users to log in without a forced password reset.

## Options

### A: Dual-Hash with Gradual Migration

On login, check the hash format:
1. If legacy (`sha1:salt:hash`): verify with SHA1, then re-hash with bcrypt/argon2 and update the DB row
2. If modern (`$2b$...` or `$argon2id$...`): verify with the modern algorithm directly

Over time, all active users migrate automatically. Dormant accounts retain old hashes until login or admin action.

### B: Big-Bang Migration (Force Reset All)

Invalidate all existing password hashes. Send password reset emails to all users. New passwords are hashed with bcrypt/argon2 from day one.

- Clean break — no legacy hash code
- Disruptive to users (especially if email is not configured)
- Dormant accounts handled cleanly

### C: Wrap-Hash Migration

Hash existing SHA1 hashes with bcrypt: `bcrypt(sha1(password))`. Store with a flag indicating the double-hash. On login, compute `sha1(input)` then `bcrypt.verify()`. Optionally re-hash to pure bcrypt on successful login.

- No user disruption
- All hashes upgraded in one DB migration
- Slightly more complex verification logic
- SHA1 weakness is mitigated by outer bcrypt layer

## Trade-off Analysis

| Criterion | A: Dual-Hash Gradual | B: Big-Bang Reset | C: Wrap-Hash |
|-----------|---------------------|-------------------|--------------|
| User disruption | None | High (all users reset) | None |
| Implementation complexity | Medium | Low | Medium |
| Legacy code retention | Temporary (login check) | None | Permanent (double-hash) |
| Dormant account handling | Remains SHA1 until login | Forced reset | All upgraded immediately |
| Security posture during migration | Gradual improvement | Immediate full security | Immediate (bcrypt wraps SHA1) |
| Password reset email dependency | No | Yes (critical) | No |
| Rollback complexity | Low | High (hashes destroyed) | Low |

## Preliminary Recommendation

**Option A (Dual-Hash with Gradual Migration)** — least disruptive, straightforward to implement, and the legacy SHA1 verification code is small and isolated. Active users migrate transparently on their next login. For dormant accounts, add an admin tool or scheduled job to flag accounts that have not migrated after N months, optionally forcing a reset for those users only.

Target hash algorithm: **argon2id** (via the `argon2-cffi` library) as the primary choice, with bcrypt as fallback if argon2 is unavailable.

## Decision

**TBD**

## Consequences

- If Option A: legacy SHA1 verification code must be maintained until all accounts are migrated
- If Option A: a monitoring query (`SELECT count(*) WHERE pwd_hash LIKE 'sha1:%'`) tracks migration progress
- If Option A: dormant accounts remain on SHA1 indefinitely unless forced
- If Option B: clean but disruptive; not viable if users lack email or the instance lacks SMTP
- If Option C: all accounts secured immediately but double-hash logic is permanent overhead
- All options: new user registrations always use argon2id from day one
