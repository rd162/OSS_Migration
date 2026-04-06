---
name: no-skip-rule
description: NEVER skip tests or use workarounds that cause skips — fix the code or implement the missing feature
type: feedback
---

NEVER skip a test, and NEVER write a workaround that causes a test to skip.

**Why:** Skips are hidden failures. They mask unimplemented features and real bugs. Discovered during 2026-04-06 session: 392 skipped tests hid session contamination bugs and a missing `truncate_string` PHP port. The coverage validator showed 100% but the app had real defects.

**How to apply:**
- `@pytest.mark.skip`, `pytest.skip()`, `@pytest.mark.skipif`, `unittest.skip` → all prohibited, zero exceptions
- `MISSING_PORT` comment + skip = not acceptable; implement the function first, then write the test
- Wrong-namespace patches that silently bypass real code (e.g. `patch("flask_login.login_user")` instead of `patch("ttrss.blueprints.public.views.login_user")`) are a form of skip — fix the patch target
- Infrastructure skips (DB/Redis unreachable) in conftest.py fast-fail fixtures are the only permitted use of `pytest.skip()`
- Gate: `pytest` must exit with 0 skips. Any skip in CI is a build failure.
