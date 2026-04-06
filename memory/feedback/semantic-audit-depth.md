---
name: semantic-audit-depth
description: Semantic code audits must read raw source and quote line numbers — summaries always miss structural bugs like indentation errors
type: feedback
---

NEVER accept a semantic audit result that does not quote the actual source lines from both the PHP file and the Python file.

**Why:** The 2026-04-06 Phase C/D sweep missed the `save_rules_and_actions` indentation bug. The for-loop body in `filters_crud.py` was dedented one level too far — the rule-insertion block ran outside the loop, saving only the last rule. An Explore agent described the function correctly ("iterates rules, inserts each") but never read the actual indentation. The bug shipped and caused data loss (all filter rules except the last were silently discarded).

**How to apply:**
- For every function audited: open both the PHP file and the Python file, read the raw source, quote key lines verbatim with line numbers.
- For every loop (`for`/`while`/`foreach`): explicitly state "loop starts line N, body is lines N+1–M". If any operation that belongs inside the loop appears at or before the loop keyword's indentation level, it is a discrepancy — file it immediately.
- SQL queries: compare column-by-column and WHERE-clause-by-WHERE-clause. "Both query the same table" is not verification.
- "Logic is equivalent" or "semantics match" without quoted line numbers from both files = not verified. Re-run.
- Deployment/environment issues (wrong Redis port, missing env var) are NOT semantic discrepancies and cannot be caught by code comparison. They belong in deployment runbooks and smoke tests.
