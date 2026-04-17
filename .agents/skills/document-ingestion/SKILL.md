---
name: document-ingestion
version: "1.4"
description: >-
  Converts raw documents (PDF, DOCX, PPTX, XLSX), draw.io diagrams, and video
  files (MP4, MKV, AVI, MOV) into AI-readable fragments using dual markdown
  converters (MarkItDown + Docling), mandatory WEBP sliding-window page images
  via libvips, and video processing via OpenAI Whisper (VTT subtitles) +
  PySceneDetect (scene-change cadre images). Produces an indexed __FRAGMENTS__/
  directory with SHA256 change tracking and incremental processing.
  WEBP generation must never be skipped — uses a three-strategy fallback chain
  for Office→PDF: LibreOffice headless (preferred), mammoth+Chrome (fallback),
  docx2pdf/Word (last resort). Manual VTT/SRT subtitle files from __SPECS__
  are preserved alongside Whisper-generated VTTs. Use when user says "convert
  documents", "ingest documents", "process specs", "create fragments", "prepare
  documents for analysis", "run the converter", "set up document pipeline",
  "process videos", "extract subtitles", or when a project has an __SPECS__/
  directory with raw documents or video recordings that need to be made
  AI-readable. Also use when new documents arrive or user needs to re-process
  an existing __FRAGMENTS__/ directory.
metadata:
  author: rd162@hotmail.com
  tags: document-conversion, ingestion, markitdown, docling, drawio, webp, vips, pdf, fragments, libreoffice, chrome, video, whisper, scenedetect, vtt
---

# Document Ingestion

Convert raw documents, draw.io diagrams, and video files into AI-readable
fragments using dual markdown converters, XML parsing, WEBP sliding-window
images, and video speech-to-text + scene-change extraction.
Scans project directories recursively — not limited to `__SPECS__/`.
Domain-agnostic: works for any document type and any downstream analysis.

**WEBP images are mandatory** for all page-producing formats (PDF, DOCX, PPTX).
pyvips cannot open Office files directly — PDF is the required intermediate.
If DOCX/PPTX `images/` directories are empty after a run, install LibreOffice
and re-run with `--force`. See @references/docx-pdf-strategies.md for the full
strategy chain and anti-patterns.

**Video files** (MP4, MKV, AVI, MOV, WEBM, M4V, WMV) are processed with:

- **Whisper** speech-to-text → `_whisper.vtt` subtitle files
- **PySceneDetect** → `cadre_NNN.jpg` scene-change images
- Manual VTT/SRT files found alongside videos in `__SPECS__/` are preserved

## When to Use

- Raw documents (PDF, DOCX, PPTX, XLSX) or diagrams (.drawio) need conversion
- Video files (MP4, MKV, AVI, MOV) need transcription or scene extraction
- Project has an `__SPECS__/` directory with source documents to ingest
- User wants to set up or run the document conversion pipeline
- New documents arrive and need incremental processing
- User needs to force-reprocess existing documents
- Preparing documents for any downstream analysis (survey, proposal, research)
- User mentions MarkItDown, Docling, draw.io, WEBP image generation,
  Whisper, subtitles, VTT, or scene detection

## When NOT to Use

- Documents are already in markdown format (no conversion needed)
- User only needs to read a single file (use `read_file` directly)
- Documents are code files or structured data (JSON, CSV, YAML)
- User wants to analyze fragments (use the document-survey skill instead)

## Termination

| Signal        | Condition                                                            | Action                                              |
| ------------- | -------------------------------------------------------------------- | --------------------------------------------------- |
| COMPLETE      | All documents processed, INDEX.md exists, manifest shows no failures | ✓ STOP — report fragment inventory                  |
| PARTIAL       | Some documents processed, others failed                              | ✓ STOP — report successes and failures with actions |
| NO_DEPS       | Python, libvips, or required libraries unavailable after setup       | Degrade — attempt manual read_file fallback         |
| VIDEO_PARTIAL | Whisper or scenedetect missing — video partially processed           | Degrade — report which video outputs are available  |
| BLOCKED       | No `__SPECS__/` directory and user cannot provide documents          | Ask user to place documents in `__SPECS__/`         |

## Graceful Degradation

- **Full tooling** (Python 3.10–3.12 + libvips + LibreOffice + Whisper + scenedetect):
  Complete pipeline — dual markdown + WEBP images + video VTT/cadres + change tracking.
- **LibreOffice missing, Chrome present:**
  mammoth + Chrome headless handles DOCX→PDF→WEBP. Good fidelity;
  DOCX themes not preserved. Install LibreOffice for best results.
- **No LibreOffice, no Chrome:**
  docx2pdf (Word via AppleScript on macOS) as last resort.
  May show permission dialogs or time out — unreliable.
- **Python only, no libvips:**
  Markdown conversion works; WEBP generation is skipped.
  Report "WEBP unavailable — install libvips" and degrade gracefully.
- **Whisper missing:**
  Video scene-change cadres still extracted. VTT generation skipped.
  Report "openai-whisper not installed — skipping VTT generation."
- **scenedetect/opencv missing:**
  Whisper VTT still generated. Scene-change cadres skipped.
  Report "scenedetect not installed — skipping scene extraction."
- **No Python:**
  Fall back to direct `read_file` on source documents.
  Report "Converter unavailable — reading documents directly."
- **Terminal unavailable:**
  Guide user through manual setup steps in chat.

---

## Bundled Scripts

This skill ships with five scripts in `scripts/`.
Copy them into every target project before running the pipeline.

| Script                               | Purpose                                                       |
| ------------------------------------ | ------------------------------------------------------------- |
| `scripts/doc_converter.py`           | Main converter: dual markdown + WEBP + video VTT/cadres       |
| `scripts/video_extract.py`           | Standalone video extractor: Whisper VTT + scene-change cadres |
| `scripts/setup_converter.sh`         | One-time setup: creates `.venv/`, installs Python deps        |
| `scripts/verify_images.py`           | Post-conversion: validates WEBP images for LLM vision         |
| `scripts/requirements_converter.txt` | Pinned dependency list for reproducible installs              |

### What `doc_converter.py` Does

1. **Recursive project scanning** — walks the project tree with `followlinks=True`,
   auto-excluding `.git`, `node_modules`, `.venv`, `__FRAGMENTS__`, `__pycache__`, etc.
   If `__SPECS__/` exists it is auto-detected and used as the scan root.
   **`__SPECS__/` entries are often symlinks** (e.g. pointing to OneDrive/SharePoint
   folders) — `followlinks=True` is required or every file under them is silently missed.
   1b. **Video file detection** — MP4, MKV, AVI, MOV, WEBM, M4V, WMV are routed
   to the video pipeline automatically during normal scanning runs.
2. **Archive extraction** — auto-detects ZIP, TAR, TAR.GZ, TGZ, 7Z.
3. **Dual markdown conversion** — every document converted twice:
   - **MarkItDown** (Microsoft): fast, excellent table fidelity
   - **Docling** (IBM): ML-based layout detection, multi-column, diagrams
4. **draw.io support** — XML parsing → structured markdown + CLI→WEBP export.
5. **WEBP sliding-window images** — Office docs converted to PDF via the
   three-strategy chain (LibreOffice → Chrome+mammoth → docx2pdf), then
   rendered as 3-page overlapping WEBP windows via pyvips.
   **Never skipped for page-producing formats.**
6. **Collision-safe fragment naming** — detects files with the same name from
   different subdirectories and automatically prepends the first distinguishing
   ancestor directory as a context prefix, so fragment directories never collide.
7. **Incremental manifest** — `.manifest.json` saved after every file.
   Interrupted batch runs resume cleanly without re-processing completed files.
8. **Master index** — `__FRAGMENTS__/INDEX.md` lists every document and output.

For the full DOCX→PDF strategy details and anti-patterns:
→ @references/docx-pdf-strategies.md

### What `video_extract.py` Does

Standalone video processor for when you only need video extraction
(without the full document conversion pipeline):

1. **Whisper VTT** — transcribes audio to `_whisper.vtt` subtitle files
2. **Scene-change cadres** — extracts `cadre_NNN.jpg` images at scene boundaries
3. Uses the same `__FRAGMENTS__/` structure and `.manifest.json` change tracking
4. Supports `--whisper-model` (tiny/base/small/medium/large) and `--threshold`

Usage: `scripts/.venv/bin/python scripts/video_extract.py`

### What `setup_converter.sh` Does

- Detects best available Python (prefers 3.11, warns on 3.13+)
- Creates `.venv/` with markitdown, docling, pyvips, mammoth, and all deps
- Checks libvips, LibreOffice, Chrome, and draw.io; reports which DOCX→PDF
  strategy will be active based on what is installed

- Installs video processing deps: openai-whisper, scenedetect, opencv-python-headless
  (gracefully skipped if installation fails — video processing is optional)

### What `verify_images.py` Does

- Scans `__FRAGMENTS__/` for all generated WEBP files
- Validates format, dimensions, and decodability via Pillow
- Checks LLM vision constraints (min 10KB, max 20MB, 100–8192px)
- Generates `IMAGE_VERIFICATION_REPORT.md`

---

## System Dependencies

| Dependency             | Required        | macOS                             | Linux                                        |
| ---------------------- | --------------- | --------------------------------- | -------------------------------------------- |
| Python 3.10–3.12       | Yes             | `brew install python@3.11`        | `sudo apt install python3.11`                |
| libvips + poppler      | Yes             | `brew install vips poppler`       | `sudo apt install libvips-dev poppler-utils` |
| **LibreOffice**        | **Recommended** | `brew install --cask libreoffice` | `sudo apt install libreoffice`               |
| Google Chrome/Chromium | Fallback        | Usually pre-installed             | `sudo apt install chromium-browser`          |
| draw.io                | Optional        | `brew install --cask drawio`      | [download .deb from jgraph/drawio-desktop]   |
| ffmpeg                 | For video       | `brew install ffmpeg`             | `sudo apt install ffmpeg`                    |

**LibreOffice is strongly recommended.** Without it, the converter falls back
to mammoth+Chrome (lower fidelity) then docx2pdf/Word (unreliable on macOS).
LibreOffice is also required for `.doc` (Word 97-2003) and PPTX/PPT.

On macOS use `brew install --cask libreoffice` — the `--cask` flag is required.
The bare formula (`brew install libreoffice`) does not install `soffice`.

---

## Prerequisites

Before deploying scripts, verify LibreOffice is installed:

```text
which soffice && soffice --version
```

If not found, install it:

```text
macOS:  brew install --cask libreoffice
Linux:  sudo apt install libreoffice
```

---

## Step 1: Deploy Scripts to Project

**Option A — Scripts at project root:**

```text
cp {skill-path}/scripts/* {ProjectRoot}/
chmod +x {ProjectRoot}/setup_converter.sh
```

**Option B — Scripts in `scripts/` subdirectory (cleaner):**

```text
mkdir -p {ProjectRoot}/scripts
cp {skill-path}/scripts/* {ProjectRoot}/scripts/
chmod +x {ProjectRoot}/scripts/setup_converter.sh
```

Always run converter commands from the project root.
Documents do not need to be in `__SPECS__/` — the converter scans the whole tree.

## Step 2: One-Time Setup

```text
Option A: ./setup_converter.sh
Option B: bash scripts/setup_converter.sh
```

This creates `.venv/` with all dependencies. Verify:

```text
scripts/.venv/bin/python -c "import pyvips; import markitdown; import mammoth; print('OK')"
soffice --version
```

## Step 3: Run the Converter

```text
Option A: .venv/bin/python doc_converter.py
Option B: scripts/.venv/bin/python scripts/doc_converter.py
```

### Command-Line Flags

| Flag                    | Effect                                                           |
| ----------------------- | ---------------------------------------------------------------- |
| _(no flags)_            | Scan CWD recursively (or `__SPECS__/` if it exists)              |
| `--scan-dir PATH`       | Scan only this directory (recursively)                           |
| `--force`               | Reprocess everything (ignore change tracking)                    |
| `--file "name.pdf"`     | Process a specific file only (searched recursively)              |
| `--clean`               | Remove fragments for deleted/moved source documents              |
| `--no-recurse`          | Only scan top-level of the scan directory                        |
| `--fragments-dir PATH`  | Override `__FRAGMENTS__/` output location                        |
| `--whisper-model MODEL` | Whisper model: tiny, base, small, medium, large (default: base)  |
| `--scene-threshold N`   | Scene detection sensitivity — lower = more cadres (default: 5.0) |

### Directory Exclusions

Automatically excluded: `__FRAGMENTS__` `.venv` `venv` `.env` `node_modules`
`.git` `.svn` `.tmp` `.cache` `__pycache__` `dist` `build` `.tox` `.idea` `.vscode`
and any directory starting with `.`

## Step 4: Verify Output

```text
∆1: list_directory("__FRAGMENTS__/") → confirm fragment directories exist
∆2: read_file("__FRAGMENTS__/INDEX.md") → check master index
∆3: scripts/.venv/bin/python scripts/verify_images.py
∆4: Spot-check one markitdown + one docling output for quality
∆5: For DOCX/PPTX: confirm images/ dir is non-empty
    (if empty → LibreOffice missing; install and re-run --force)
```

### Expected Output Structure

```text
__FRAGMENTS__/
├── INDEX.md                              # Master index of all documents
├── .manifest.json                        # SHA256 change tracking (saved per-file)
├── IMAGE_VERIFICATION_REPORT.md
│
├── {Document Name}/
│   ├── markdown/
│   │   ├── {name}_markitdown.md
│   │   └── {name}_docling.md
│   └── images/                           # Non-empty for PDF/DOCX/PPTX
│       ├── {name}_p001-003.webp          # Pages 1–3 (3-page sliding window)
│       ├── {name}_p002-004.webp
│       └── ...
│
├── {Video Name}/                         # Video files
│   ├── markdown/
│   │   ├── {name}_whisper.vtt            # Whisper-generated subtitles
│   │   └── {name}.vtt                    # Manual subtitle (if found in __SPECS__)
│   └── images/
│       ├── cadre_000.jpg                 # Scene-change frame images
│       ├── cadre_001.jpg
│       └── ...
```

XLSX produces `markdown/` only (spreadsheets have no renderable pages).
Video files produce VTT subtitles + scene-change cadre images (no markdown conversion).

## Step 5: Report Completion

```text
docs[N] → markitdown[N] | docling[N] | webp_images[N] | failures[N]
videos[N] → vtt[N] | cadres[N] | manual_subs[N]
DOCX→PDF strategy used: LibreOffice | Chrome+mammoth | docx2pdf
Whisper model used: tiny | base | small | medium | large
Per-doc: {name}→md✓ webp✓ | {name}→md✓ webp✗(no converter) | ...
Per-video: {name}→vtt✓ cadres✓ | {name}→vtt✗(no whisper) cadres✓ | ...
```

---

## Converter Strategy

### Standard Documents

Every document is converted twice for cross-referencing:

| Converter      | Strengths                               | Weaknesses               |
| -------------- | --------------------------------------- | ------------------------ |
| **MarkItDown** | Fast; excellent tables; structured docs | May miss complex layouts |
| **Docling**    | ML layout detection; multi-column       | Slower; heavier deps     |

### draw.io Diagrams

1. **XML parser** → components (with shape types), connections (with labels),
   multi-page diagram names → structured markdown
2. **draw.io CLI** → each page → PDF → WEBP (requires draw.io app; optional)

### Converter Selection Guide

| Document Type               | Best for reading | Reason                          |
| --------------------------- | ---------------- | ------------------------------- |
| Structured reports / tables | markitdown       | Superior table fidelity         |
| Complex PDFs / multi-column | docling          | ML-based layout detection       |
| Diagrams / visuals          | WEBP images      | LLM vision analysis             |
| Spreadsheets                | markitdown       | Sheet-by-sheet extraction       |
| draw.io diagrams            | drawio_parsed.md | Components + connections + WEBP |

---

## WEBP Sliding Window

Pages are rendered as 3-page overlapping WEBP windows:

```text
p001-003: Page 1 │ Page 2 │ Page 3
p002-004: Page 2 │ Page 3 │ Page 4
...continues to last 3 pages
```

Overlapping windows preserve context across page boundaries.
Typical size: 300KB–2MB per image (LibreOffice output).

Read with: `read_file("__FRAGMENTS__/{doc}/images/{doc}_p010-012.webp")`

WEBP is essential for architecture diagrams, complex tables, multi-column layouts,
cover pages, and any visual content requiring LLM vision analysis.
**Never voluntarily skip WEBP.** If `images/` is empty after processing
a DOCX or PPTX, install LibreOffice and re-run `--force`.

### Image Settings

| Constant          | Default | Range | Description                   |
| ----------------- | ------- | ----- | ----------------------------- |
| `IMAGE_DPI`       | 150     | 0–600 | Resolution (150 = balanced)   |
| `PAGES_PER_IMAGE` | 3       | 1–5   | Pages per WEBP sliding window |
| `WEBP_QUALITY`    | 85      | 0–100 | Encoder quality (85 = good)   |

---

## Change Tracking

The manifest is written after every file — interrupted batch runs
resume cleanly from the next unprocessed file.

Decision logic per file:

```text
File found → SHA256 → check manifest:
  ├─ Not in manifest           → PROCESS  (new)
  ├─ Hash differs              → PROCESS  (changed)
  ├─ Previous run failed       → PROCESS  (retry)
  ├─ Hash matches              → SKIP     (unchanged)
  └─ --force flag              → PROCESS  (override)
```

For the full manifest format, orphan detection, incremental workflow patterns,
and summary report format:
→ @references/change-tracking.md

---

## Anti-Patterns

| Approach                                        | Why it fails                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PyMuPDF` DOCX→PDF                              | Silently drops all embedded images — diagram pages render blank in WEBP output                                                                                                                                                                                                                         |
| `pyvips` direct DOCX                            | pyvips has no DOCX loader: "not a known file format" — PDF is always required                                                                                                                                                                                                                          |
| Skipping WEBP for Office docs                   | Architecture diagrams and visual tables are only readable via LLM vision on WEBP                                                                                                                                                                                                                       |
| `brew install libreoffice` (no `--cask`)        | Installs the formula, not the app — `soffice` is never linked                                                                                                                                                                                                                                          |
| `docx2pdf` as primary strategy                  | Word AppleScript is unreliable: permission dialogs, 2-min timeouts, silent drops                                                                                                                                                                                                                       |
| Assuming `pyvips.Image.pdfload` works           | libvips ships pdfload as a **dynamic module** (vips-poppler.dylib) that may not load at runtime even when `vips --vips-config` says "true". Always probe with `_pdfload_available()` and fall back to `pdftoppm`. The silent failure mode is an empty `AttributeError` with no message — easy to miss. |
| `os.walk(__SPECS__)` without `followlinks=True` | `__SPECS__/` entries are symlinks — walk stops at the symlink, finds zero files. Always use the converter script or pass `followlinks=True` / `find -L` explicitly.                                                                                                                                    |
| Ad-hoc manifest cross-check via custom scan     | Writing a custom file scanner to check what's in the manifest bypasses the converter's symlink handling. Run `doc_converter.py` (dry-run or normal) to get an authoritative view.                                                                                                                      |
| Whisper `large` model on CPU                    | Extremely slow (~6h for 30-min video on ARM Mac). Use `tiny` or `base` for CPU; reserve `large` for GPU.                                                                                                                                                                                               |
| Eager vips module loading with Whisper          | Loading vips modules at import time interferes with PyTorch/Whisper on ARM Macs. Use lazy init pattern.                                                                                                                                                                                                |

---

## Troubleshooting

For the full troubleshooting table, diagnostic commands, and strategy chain
failure analysis:
→ @references/troubleshooting.md

Most common fix for empty `images/` directories:

```text
brew install --cask libreoffice
scripts/.venv/bin/python scripts/doc_converter.py --force
```

---

## Post-Ingestion Checklist

```text
- [ ] All scanned documents have folders in __FRAGMENTS__/
- [ ] Each document has at least one markdown output
- [ ] PDF documents have non-empty images/ directories
- [ ] DOCX/PPTX documents have non-empty images/ directories
      (if empty: LibreOffice/Chrome missing — install and re-run --force)
- [ ] .drawio files have parsed markdown (components + connections)
- [ ] Video files have _whisper.vtt in markdown/ (if Whisper installed)
- [ ] Video files have cadre_NNN.jpg in images/ (if scenedetect installed)
- [ ] Manual VTT/SRT files from __SPECS__ are preserved in markdown/
- [ ] INDEX.md lists all processed documents
- [ ] verify_images.py reports no critical issues
- [ ] No "status": "failed" entries in .manifest.json
- [ ] Noted which DOCX→PDF strategy was used (LibreOffice > Chrome > docx2pdf)
```

## Composition

- **Downstream:** Feeds `__FRAGMENTS__/` into the **document-survey** skill.
- Any other analysis workflow can consume `__FRAGMENTS__/` directly.

## Video Processing Details

### Whisper Speech-to-Text

Generates `_whisper.vtt` subtitle files from video audio.
Model selection trades accuracy vs. speed:

| Model    | Size   | ~Time (30-min video, CPU)  | Accuracy |
| -------- | ------ | -------------------------- | -------- |
| `tiny`   | 39 MB  | ~30 min                    | Good     |
| `base`   | 74 MB  | ~90 min                    | Better   |
| `small`  | 244 MB | ~3 hours                   | Good+    |
| `medium` | 769 MB | ~6 hours                   | High     |
| `large`  | 1.5 GB | GPU only (impractical CPU) | Highest  |

**Recommendation:** Use `--whisper-model tiny` for fast iteration;
`base` (default) for production quality on CPU.

### Scene-Change Cadre Images

PySceneDetect extracts the first frame of each new scene as JPEG.
The `--scene-threshold` controls sensitivity:

- **Lower values** (e.g. 3.0) = more cadres, catches subtle changes
- **Default (5.0)** = aggressive, good for 30-min meetings/demos
- **Higher values** (e.g. 27.0) = fewer cadres, only major scene changes

If no scene changes are detected, the first frame is saved as a fallback.

### Manual Subtitle Preservation

When video files in `__SPECS__/` have companion `.vtt` or `.srt` files
(e.g. from Microsoft Teams or manual transcription), these are automatically
copied into the fragment's `markdown/` directory alongside the Whisper output.
Both manual and Whisper-generated subtitles are preserved — they complement
each other (manual may have speaker labels; Whisper handles audio-only content).

---

## Environment Compatibility

| Capability                  | Requirement                             | Degradation if missing                        |
| --------------------------- | --------------------------------------- | --------------------------------------------- |
| Dual markdown conversion    | Python 3.10–3.12 + markitdown + docling | None (core capability)                        |
| WEBP from PDF               | libvips + poppler                       | No WEBP — install libvips                     |
| WEBP from DOCX/PPTX         | LibreOffice (preferred) or Chrome       | No WEBP for Office docs — install LibreOffice |
| DOCX themes / cover pages   | LibreOffice                             | Themes lost with Chrome fallback              |
| Legacy `.doc` / `.ppt`      | LibreOffice                             | Skipped without LibreOffice                   |
| draw.io XML markdown        | Python only                             | Always available                              |
| draw.io WEBP images         | draw.io desktop CLI                     | No diagram images; XML markdown still works   |
| Video VTT subtitles         | openai-whisper + ffmpeg                 | VTT skipped; cadre images still extracted     |
| Video scene-change cadres   | scenedetect + opencv-python-headless    | Cadres skipped; VTT still generated           |
| Incremental resume on crash | doc_converter.py v1.4+                  | Full restart on interruption (old versions)   |
| Any AI assistant            | —                                       | Works with Claude Code, Cursor, Copilot, etc. |
| Any OS                      | libvips available                       | macOS + Linux native; Windows needs WSL       |
