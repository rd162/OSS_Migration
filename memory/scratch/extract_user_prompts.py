#!/usr/bin/env python3
"""Extract all `## User` prompts from session log files.

Outputs a combined file with session number + user prompt text.
Never loads full files into memory at once — streams line by line.
"""
import os
import re
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / "archive" / "full-logs"
OUT_FILE = Path(__file__).resolve().parent / "user_prompts_extracted.md"

# A "User" section starts with a line exactly "## User" (possibly with trailing spaces).
# It ends at the next "## " heading that is NOT "## User" content (next assistant section
# or next user section).
USER_RE = re.compile(r"^## User\s*$")
# any "## Something" heading that ends a section
SECTION_END_RE = re.compile(r"^## [A-Za-z]")

def extract_from_file(path: Path):
    """Yield (index, lines) for each user section in file (streaming)."""
    user_idx = 0
    capturing = False
    buf = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if USER_RE.match(line):
                if capturing and buf:
                    user_idx += 1
                    yield user_idx, buf
                capturing = True
                buf = []
                continue
            if capturing and SECTION_END_RE.match(line):
                # next section starts — close current user block
                user_idx += 1
                yield user_idx, buf
                capturing = False
                buf = []
                continue
            if capturing:
                buf.append(line)
        if capturing and buf:
            user_idx += 1
            yield user_idx, buf

def main():
    files = sorted(LOGS_DIR.glob("*.md"))
    with OUT_FILE.open("w", encoding="utf-8") as out:
        out.write("# Extracted User Prompts from Session Logs\n\n")
        for fp in files:
            session = fp.stem
            out.write(f"\n\n---\n\n## Session {session}\n\n")
            count = 0
            for idx, lines in extract_from_file(fp):
                count += 1
                # Trim surrounding blank lines
                while lines and not lines[0].strip():
                    lines.pop(0)
                while lines and not lines[-1].strip():
                    lines.pop()
                text = "".join(lines).rstrip()
                out.write(f"\n### Session {session} — User #{idx}\n\n")
                out.write(text)
                out.write("\n")
            if count == 0:
                out.write("_(no user sections found)_\n")
            print(f"{fp.name}: {count} user prompts")
    print(f"\nWrote: {OUT_FILE}")

if __name__ == "__main__":
    main()
