# Troubleshooting

## Quick Lookup

| Issue                                             | Cause                                                              | Solution                                                                            |
| ------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `ModuleNotFoundError: pyvips`                     | Wrong Python interpreter or venv not activated                     | Use direct path: `scripts/.venv/bin/python scripts/doc_converter.py`                |
| `unable to call pdfload`                          | libvips installed but poppler missing                              | `brew install vips poppler` (macOS) or `sudo apt install libvips-dev poppler-utils` |
| `soffice` not found                               | LibreOffice not installed                                          | `brew install --cask libreoffice` — `--cask` is required on macOS                   |
| `brew install libreoffice` gives no `soffice`     | Installed the formula, not the cask                                | `brew uninstall libreoffice && brew install --cask libreoffice`                     |
| DOCX `images/` directory is empty                 | No DOCX→PDF converter found at runtime                             | Install LibreOffice, then re-run with `--force`                                     |
| mammoth+Chrome produces no images                 | Chrome not found at any candidate path                             | Install Chrome or LibreOffice; check `_CHROME_CANDIDATES` in `doc_converter.py`     |
| docx2pdf hangs for 2 minutes                      | Word shows a Protected View dialog or Automation permission prompt | Install LibreOffice — fully headless, no dialogs, no permissions                    |
| PyMuPDF DOCX→PDF has blank diagram pages          | PyMuPDF silently drops embedded images from DOCX                   | Use LibreOffice or Chrome strategy; never use PyMuPDF for the WEBP pipeline         |
| `.drawio` images skipped                          | draw.io CLI not found                                              | Install draw.io desktop app; XML markdown is still generated without it             |
| No documents found                                | Wrong scan directory or CWD                                        | Check CWD; use `--scan-dir path/to/docs` to point at the correct directory          |
| Legacy `.doc` file skipped                        | Word 97-2003 format; Chrome/mammoth cannot handle it               | LibreOffice handles `.doc` natively — Strategy 1 must be active                     |
| `.pptx` or `.ppt` images missing                  | Chrome/mammoth Strategy 2 does not support PPTX                    | Install LibreOffice — only Strategy 1 handles PPTX/PPT                              |
| Large batch restarts from zero after interruption | Old `doc_converter.py` only saved manifest on clean exit           | Update `doc_converter.py` to v1.3+ — manifest is now saved after every file         |
| Slow processing on large batch                    | Normal: docling is ML-based; LibreOffice spawns per file           | Use `--file name.docx` to process specific files; re-runs are incremental           |
| Script crashes on `.zip` archive                  | Archive contained a `.doc` file                                    | Fixed in current version — update `doc_converter.py`                                |
| `Python 3.14` crash                               | `BaseException` incompatibility in some deps                       | Fixed in current version; or switch to Python 3.11 via `pyenv`                      |
| Blank or corrupted WEBP images                    | libvips rendering issue or very low DPI                            | Run `scripts/.venv/bin/python scripts/verify_images.py --verbose` to diagnose       |
| `status: failed` entries in `.manifest.json`      | DOCX→PDF conversion failed at runtime                              | Install LibreOffice; re-run `--force` to retry failed files                         |
| INDEX.md not updated                              | Run was interrupted before final write                             | Re-run converter — INDEX.md is regenerated on every clean exit                      |
| Fragment directory exists but is empty            | Previous run crashed mid-file                                      | Re-run with `--force` for that specific file                                        |

---

## Most Common Fix

If DOCX or PPTX files have empty `images/` directories after conversion, the
cause is almost always a missing DOCX→PDF converter. The fix in 99% of cases:

```text
brew install --cask libreoffice
scripts/.venv/bin/python scripts/doc_converter.py --force
```

---

## Diagnosing Strategy Chain Failures

To see which DOCX→PDF strategy was attempted, run with verbose logging:

```text
scripts/.venv/bin/python scripts/doc_converter.py --file "problem.docx" 2>&1 | grep -E "Strategy|LibreOffice|mammoth|docx2pdf|✓|✗|⚠"
```

Expected output when LibreOffice is active:

```text
  Trying LibreOffice → PDF…
  ✓ LibreOffice → problem.pdf
  ✓ Image: pages 1-3 → problem_p001-003.webp
```

Expected output when only Chrome is available:

```text
  Trying LibreOffice → PDF…
  Trying mammoth + Chrome headless → PDF…
  ✓ mammoth + Chrome → problem.pdf
  ✓ Image: pages 1-3 → problem_p001-003.webp
```

If all three strategies fail:

```text
  Trying LibreOffice → PDF…
  Trying mammoth + Chrome headless → PDF…
  Trying docx2pdf → PDF…
  ⚠ Could not convert problem.docx to PDF via any converter
  → Status: failed
```

Install LibreOffice and re-run to resolve.

---

## Checking Dependencies

Run this to confirm all critical dependencies are available:

```text
# libvips (required for all WEBP)
python -c "import pyvips; print('pyvips', pyvips.__version__)"

# LibreOffice (preferred DOCX→PDF)
soffice --version

# Chrome (fallback DOCX→PDF)
google-chrome --version 2>/dev/null || /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version 2>/dev/null

# draw.io CLI (optional; for .drawio WEBP export)
/Applications/draw.io.app/Contents/MacOS/draw.io --version 2>/dev/null || echo "draw.io not found (optional)"
```
