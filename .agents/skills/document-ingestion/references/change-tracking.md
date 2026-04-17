# Change Tracking & Incremental Processing

The converter is designed to run repeatedly as documents are added, modified, or removed.
Every run is incremental by default — only new or changed files are processed.

---

## How It Works

`.manifest.json` in `__FRAGMENTS__/` tracks every processed document using its
**path relative to CWD** as the stable key (not just the filename).
This prevents collisions when identically-named files live in different directories
(e.g. `us/report.pdf` vs `france/report.pdf`).

**The manifest is written after every individual file completes.**
Interrupted batch runs (timeout, Ctrl-C, crash) resume from the next unprocessed
file — not from the beginning. In earlier versions the manifest was only written
on clean exit, causing large batches to restart from zero on any interruption.

### Manifest Entry Format

```json
{
  "files": {
    "docs/requirements.pdf": {
      "hash": "sha256:a3f9...",
      "source": "docs/requirements.pdf",
      "processed_at": "2026-01-15T10:30:00",
      "status": "complete",
      "markitdown": "requirements/markdown/requirements_markitdown.md",
      "docling": "requirements/markdown/requirements_docling.md",
      "images": [
        "requirements/images/requirements_p001-003.webp",
        "requirements/images/requirements_p002-004.webp"
      ]
    },
    "design/architecture.drawio": {
      "hash": "sha256:7c2b...",
      "source": "design/architecture.drawio",
      "processed_at": "2026-01-15T10:31:00",
      "status": "complete",
      "drawio_parsed": "architecture/markdown/architecture_drawio_parsed.md",
      "images": ["architecture/images/architecture_diagram_p001-001.webp"]
    }
  }
}
```

**Status values:** `complete` | `markdown_only` | `images_only` | `failed` | `error`

- `complete` — markitdown + docling + WEBP all succeeded
- `markdown_only` — markdown succeeded; no WEBP (e.g. XLSX has no pages)
- `failed` — DOCX→PDF conversion failed; no WEBP generated; re-run after installing LibreOffice
- `error` — unexpected exception; check error field for details

---

## Decision Logic Per File

On each run, every discovered file is evaluated:

```text
File found in scan → compute SHA256 → check manifest:
  ├─ Not in manifest            → PROCESS  (new file)
  ├─ In manifest, hash differs  → PROCESS  (content changed)
  ├─ In manifest, prev failed   → PROCESS  (retry after error)
  ├─ In manifest, hash matches  → SKIP     (unchanged)
  └─ --force flag set           → PROCESS  (override all checks)
```

Files with `status: failed` are automatically retried on the next run.
Use `--force` to reprocess everything regardless of hash or status.

---

## Orphan Detection

When source documents are deleted or moved out of the scan directory,
their manifest entries and fragment directories become **orphaned**.

The converter detects orphans automatically on every run by checking whether
each manifest key's source path still exists on disk.

**Without `--clean`** — orphans are reported but not removed:

```text
⚠ 2 orphaned manifest entry/entries (source files no longer found):
  · docs/old_requirements.pdf
  · specs/removed_diagram.drawio
  Run with --clean to remove their fragments.
```

**With `--clean`** — orphaned fragment directories and manifest entries are deleted:

```text
→ Cleaning 2 orphaned entry/entries…
  🗑 Cleaned: old_requirements/ (was: docs/old_requirements.pdf)
  🗑 Cleaned: removed_diagram/ (was: specs/removed_diagram.drawio)
```

---

## Typical Incremental Workflows

**New documents added:**

```text
∆1: Place new documents anywhere in the project (or in __SPECS__/)
∆2: Run converter — only new files are processed; existing files are skipped
∆3: Verify with verify_images.py
∆4: Check INDEX.md for updated inventory
```

**Existing documents modified:**

```text
∆1: Edit the source document
∆2: Run converter — changed SHA256 triggers reprocessing
∆3: Fragment directory is overwritten with fresh output
```

**Documents deleted or moved:**

```text
∆1: Delete or move the source document
∆2: Run converter → orphan warning appears
∆3: Run converter --clean → orphaned fragments removed
```

**Full reprocessing (ensure fresh state):**

```text
∆1: Run: scripts/.venv/bin/python scripts/doc_converter.py --force
    (reprocesses all documents regardless of hash)
    OR: delete __FRAGMENTS__/ entirely, then run without --force
```

**Large batch interrupted mid-run:**

```text
∆1: Interrupt is safe — manifest was saved after each completed file
∆2: Re-run without --force → resumes from next unprocessed file
∆3: Completed files are recognized by their unchanged SHA256 and skipped
```

---

## Summary Report

Every run ends with a summary:

```text
SUMMARY
════════════════════════════════════════════════════════════
✓ Processed:  12  (new or changed)
⏭ Unchanged:  43
✗ Failed:      1
🗑 Cleaned:    0
📁 Output:    __FRAGMENTS__
📋 Tracked:   56 total entry/entries
DOCX→PDF strategy used: LibreOffice
════════════════════════════════════════════════════════════
```

If `Failed > 0`, check which files have `"status": "failed"` in `.manifest.json`
and confirm LibreOffice is installed (`soffice --version`), then re-run.
