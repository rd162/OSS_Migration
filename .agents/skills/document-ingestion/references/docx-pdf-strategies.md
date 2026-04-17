# DOCX→PDF Strategy Chain

## Why PDF is Required

pyvips cannot open Office formats directly.
Running `pyvips.Image.new_from_file("doc.docx")` raises "not a known file format".
PDF is always the mandatory intermediate for WEBP rendering.

The converter in `doc_converter.py` tries three strategies in priority order,
stopping at the first success.

---

## Strategy 1 — LibreOffice headless _(preferred)_

```text
soffice --headless --convert-to pdf --outdir {tmpdir} {file.docx}
```

- Fully automated — no GUI, no dialogs, no AppleScript, no system permissions
- Maximum fidelity: DOCX themes, cover page branding, embedded images, tables, fonts
- Handles all Office formats including legacy `.doc` (Word 97-2003) and `.ppt`/`.pptx`
- ~10 seconds per document

**Install:**

```text
macOS:  brew install --cask libreoffice    ← must use --cask (not the formula)
Linux:  sudo apt install libreoffice
```

> macOS note: `brew install --cask libreoffice` installs the full app and symlinks
> `soffice` to `/opt/homebrew/bin/soffice`. The formula (`brew install libreoffice`)
> does NOT install `soffice`. Always use `--cask`.

**Verify:**

```text
soffice --version   # LibreOffice 26.x.x or similar
```

---

## Strategy 2 — mammoth + Chrome headless _(fallback; DOCX only)_

```text
mammoth file.docx → HTML (embedded images as base64 data URIs)
chrome --headless=new --no-sandbox --print-to-pdf={out.pdf} file:///{file.html}
```

- Fully automated — no GUI, no dialogs, no permissions required
- Preserves embedded images (via base64 encoding) and text formatting
- DOCX themes and cover page designs are not preserved
- ~8 seconds per document
- DOCX/DOC only — does not handle PPTX/PPT

**Requirements:**

- `mammoth` Python package (already in `requirements_converter.txt`)
- Google Chrome or Chromium installed at any standard path

Chrome is auto-detected from these candidate paths (in order):

```text
google-chrome | google-chrome-stable | chromium | chromium-browser
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
/Applications/Chromium.app/Contents/MacOS/Chromium
/usr/bin/google-chrome | /usr/bin/chromium
```

No configuration is needed — if Chrome is present at any of these paths,
Strategy 2 activates automatically when LibreOffice is absent.

---

## Strategy 3 — docx2pdf / Word AppleScript _(last resort)_

```text
docx2pdf file.docx output.pdf   # drives Microsoft Word via AppleScript
```

- Requires Microsoft Word installed (macOS/Windows)
- On macOS: drives Word via AppleScript and may prompt for Automation permission
- 2-minute timeout — can hang if Word shows a Protected View dialog or security prompt
- Word's `open` AppleScript command may silently drop files in some security configurations
- Only activates when both LibreOffice and Chrome are unavailable

**When docx2pdf hangs:** install LibreOffice. It is fully headless and dialog-free.

---

## Failure path

If all three strategies fail, WEBP generation is skipped for that file.
The manifest records `"status": "failed"`.
Re-run with `--force` after installing LibreOffice to recover.

---

## Fidelity Comparison

| Feature                      | LibreOffice | mammoth + Chrome | docx2pdf / Word |
| ---------------------------- | :---------: | :--------------: | :-------------: |
| DOCX themes / cover page     |      ✓      |        ✗         |        ✓        |
| Embedded images              |      ✓      |        ✓         |        ✓        |
| Tables                       |      ✓      |        ✓         |        ✓        |
| Text / headings              |      ✓      |        ✓         |        ✓        |
| `.doc` (Word 97-2003)        |      ✓      |        ✗         |        ✓        |
| `.pptx` / `.ppt`             |      ✓      |        ✗         |        ✓        |
| Fully automated (no dialogs) |      ✓      |        ✓         |        ✗        |
| Works without GUI            |      ✓      |        ✓         |        ✗        |
| Typical time per document    |    ~10s     |       ~8s        |    ~10s–120s    |

---

## Anti-Patterns

These approaches must NOT be used in the DOCX→PDF→WEBP pipeline:

| Approach                                  | Why it fails                                                                                                                                                                                      |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PyMuPDF` (`fitz`) DOCX open              | Opens DOCX and produces a PDF, but **silently drops all embedded images**. Diagram and chart pages render completely blank in the WEBP output. Text is preserved but images are lost.             |
| `pyvips.Image.new_from_file("file.docx")` | pyvips raises "not a known file format" — it has no DOCX loader. PDF is always required as the intermediate format; there is no way to bypass this.                                               |
| Skipping WEBP for DOCX/PPTX               | WEBP images are mandatory. Architecture diagrams, process flows, tables, and cover pages are only accessible for LLM vision analysis via WEBP. Empty `images/` directories mean information loss. |
| Relying solely on docx2pdf                | Word's AppleScript interface is fragile on macOS: permission prompts, Protected View dialogs, and 2-minute timeouts make it unreliable for automation. Always prefer LibreOffice.                 |
