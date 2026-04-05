#!/bin/bash
#
# Document Converter Setup Script
# ================================
# Creates a Python virtual environment and installs all required
# dependencies for the RFP document conversion pipeline.
#
# Installs:
#   - markitdown + docling     (dual markdown converters)
#   - pyvips + Pillow          (WEBP image rendering)
#   - python-pptx, python-docx (Office document handling)
#   - docx2pdf                 (DOCX → PDF via Word/LibreOffice)
#   - openpyxl                 (Excel handling)
#   - PyMuPDF                  (PDF page-count fallback)
#   - py7zr                    (7z archive extraction)
#   - openai-whisper           (video speech-to-text VTT subtitles)
#   - scenedetect + opencv     (video scene-change cadre images)
#   - tqdm                     (progress bars)
#
# Usage (run from project root OR from scripts/ subdirectory):
#   chmod +x setup_converter.sh
#   ./setup_converter.sh                  # if script is at project root
#   bash scripts/setup_converter.sh       # if script is in scripts/ subdir
#
# After setup, run the converter (no activation needed):
#   scripts/.venv/bin/python scripts/doc_converter.py         # from project root
#   .venv/bin/python doc_converter.py                         # from scripts/ dir
#
# Or activate the venv first:
#   source scripts/.venv/bin/activate     # bash/zsh  (from project root)
#   . scripts/.venv/bin/activate          # POSIX sh  (from project root)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Place .venv inside the script's own directory so the path is predictable
# regardless of where the caller's CWD is.
# When scripts live in a scripts/ subdirectory the venv path will be scripts/.venv/
# and you invoke the converter as:
#   scripts/.venv/bin/python scripts/doc_converter.py   (from project root)
VENV_DIR="${SCRIPT_DIR}/.venv"

# Detect whether the script lives in a subdirectory called "scripts"
# and inform the user about the correct invocation paths.
IN_SCRIPTS_SUBDIR=false
if [[ "$(basename "${SCRIPT_DIR}")" == "scripts" ]]; then
    IN_SCRIPTS_SUBDIR=true
    PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
else
    PROJECT_ROOT="${SCRIPT_DIR}"
fi

echo "=============================================="
echo "Document Converter Setup"
echo "=============================================="
echo ""

# ── Python detection ──────────────────────────────────────────────────────────
PYTHON_CMD=""
for candidate in python3.11 python3.10 python3; do
    if command -v "$candidate" &> /dev/null; then
        PYTHON_CMD="$candidate"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "✗ Python 3.10+ not found. Please install Python before running this script."
    exit 1
fi

PYTHON_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python: $($PYTHON_CMD --version)"

# B5: Warn about Python 3.13+ — pre-release versions can have compatibility
# issues with third-party packages (e.g. markitdown exception hierarchy changes
# in Python 3.14 caused FileConversionException to bypass except-Exception blocks).
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
    echo ""
    echo "⚠  Python ${PYTHON_VER} detected."
    echo "   Python 3.13+ may have compatibility issues with some dependencies."
    echo "   Recommended: Python 3.10–3.12 for maximum stability."
    echo "   The converter includes workarounds for known Python 3.14 issues."
    echo "   Proceeding — if you hit problems, try: brew install python@3.11"
fi
echo ""

# ── Virtual environment ───────────────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    echo "→ Virtual environment already exists: $VENV_DIR"
    read -p "  Recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        echo "→ Removed existing environment"
    else
        echo "→ Using existing environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "→ Creating virtual environment…"
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

echo "→ Activating virtual environment…"
source "$VENV_DIR/bin/activate"

# ── pip bootstrap ─────────────────────────────────────────────────────────────
echo "→ Upgrading pip / wheel / setuptools…"
pip install --upgrade pip wheel setuptools --quiet

echo ""
echo "→ Installing document conversion libraries…"
echo "  (This may take a few minutes on first run)"
echo ""

# ── Markdown converters ───────────────────────────────────────────────────────
echo "  [1/12] markitdown…"
pip install "markitdown[all]" --quiet

echo "  [2/12] docling…"
pip install docling --quiet

# ── Image processing ──────────────────────────────────────────────────────────
echo "  [3/12] pyvips…"
pip install pyvips --quiet

echo "  [4/12] Pillow…"
pip install Pillow --quiet

# ── Office document libraries ─────────────────────────────────────────────────
echo "  [5/12] python-pptx / python-docx / openpyxl…"
pip install python-pptx openpyxl python-docx --quiet

# ── DOCX → PDF converter ──────────────────────────────────────────────────────
echo "  [6/12] docx2pdf  (DOCX → PDF via Word on macOS/Windows)…"
pip install docx2pdf --quiet

# ── PDF fallback ──────────────────────────────────────────────────────────────
echo "  [7/12] PyMuPDF  (PDF page-count fallback)…"
pip install PyMuPDF --quiet

# ── Archive support ───────────────────────────────────────────────────────────
echo "  [8/12] py7zr  (7z archive extraction)…"
pip install py7zr --quiet

# ── Video processing (optional — skipped gracefully if absent) ────────────────
echo "  [9/12] openai-whisper  (video speech-to-text)…"
pip install openai-whisper --quiet 2>/dev/null || echo "    ⚠ openai-whisper install failed (optional — video VTT will be skipped)"

echo "  [10/12] scenedetect  (video scene-change detection)…"
pip install "scenedetect[opencv]" --quiet 2>/dev/null || echo "    ⚠ scenedetect install failed (optional — video cadres will be skipped)"

echo "  [11/12] opencv-python-headless…"
pip install opencv-python-headless --quiet 2>/dev/null || echo "    ⚠ opencv install failed (optional — video cadres will be skipped)"

# ── Utilities ─────────────────────────────────────────────────────────────────
echo "  [12/12] tqdm  (progress bars)…"
pip install tqdm --quiet

echo ""
echo "=============================================="
echo "✓ Python dependencies installed"
echo "=============================================="
echo ""

# ── System dependency checks ──────────────────────────────────────────────────
echo "Checking system dependencies…"
echo ""

# libvips (required for PDF → WEBP rendering via pyvips)
if command -v vips &> /dev/null; then
    echo "✓ libvips: $(vips --version | head -1)"
else
    echo "⚠  libvips NOT found — PDF/DOCX → WEBP rendering will fail."
    echo ""
    echo "   Install on macOS:   brew install vips poppler"
    echo "   Install on Ubuntu:  sudo apt install libvips-dev poppler-utils"
    echo "   Install on Fedora:  sudo dnf install vips-devel poppler-utils"
    echo ""
fi

# LibreOffice (primary Office → PDF converter, all platforms)
if command -v soffice &> /dev/null; then
    echo "✓ LibreOffice: $(soffice --version 2>/dev/null || echo 'found')"
else
    echo "⚠  LibreOffice NOT found."
    echo "   DOCX/PPTX image extraction will fall back to:"
    echo "     • docx2pdf (DOCX on macOS/Windows with Word installed)"
    echo "     • python-docx native renderer (DOCX, lower fidelity)"
    echo "     • python-pptx native renderer (PPTX)"
    echo ""
    echo "   Install on macOS:   brew install --cask libreoffice"
    echo "   Install on Ubuntu:  sudo apt install libreoffice"
    echo ""
fi

# poppler (pdfinfo — used as an alternative page-count tool)
if command -v pdfinfo &> /dev/null; then
    echo "✓ poppler (pdfinfo): found"
else
    echo "ℹ  poppler/pdfinfo not found (optional — pyvips handles page counts)"
fi

echo ""
echo "=============================================="
echo "Setup complete!"
echo "=============================================="
echo ""

if [ "$IN_SCRIPTS_SUBDIR" = true ]; then
    echo "Scripts are in:  ${SCRIPT_DIR}"
    echo "Project root:    ${PROJECT_ROOT}"
    echo "Python venv:     ${VENV_DIR}"
    echo ""
    echo "Next steps (run from project root: ${PROJECT_ROOT}):"
    echo ""
    echo "  1. Run the converter (no activation needed):"
    echo "     ${VENV_DIR}/bin/python ${SCRIPT_DIR}/doc_converter.py"
    echo ""
    echo "     Or activate the venv first:"
    echo "     source ${VENV_DIR}/bin/activate    # bash/zsh"
    echo "     . ${VENV_DIR}/bin/activate         # POSIX sh"
    echo "     python ${SCRIPT_DIR}/doc_converter.py"
    echo ""
    echo "  2. Validate output images:"
    echo "     ${VENV_DIR}/bin/python ${SCRIPT_DIR}/verify_images.py"
    echo ""
    echo "Options:"
    echo "     ... doc_converter.py --force           # reprocess all files"
    echo "     ... doc_converter.py --file name.pdf   # process one file"
    echo "     ... doc_converter.py --help            # full usage"
    echo ""
    echo "NOTE: __SPECS__/ and __FRAGMENTS__/ are resolved relative to your"
    echo "      current working directory.  Run from the project root."
else
    echo "Next steps:"
    echo ""
    echo "  1. Activate the environment:"
    echo "     source ${VENV_DIR}/bin/activate    # bash/zsh"
    echo "     . ${VENV_DIR}/bin/activate         # POSIX sh"
    echo ""
    echo "  2. Run the converter:"
    echo "     python doc_converter.py"
    echo ""
    echo "  3. Validate output images:"
    echo "     python verify_images.py"
    echo ""
    echo "  4. Deactivate when done:"
    echo "     deactivate"
    echo ""
    echo "Options:"
    echo "     python doc_converter.py --force           # reprocess all files"
    echo "     python doc_converter.py --file name.pdf   # process one file"
    echo "     python doc_converter.py --help            # full usage"
fi
echo "=============================================="