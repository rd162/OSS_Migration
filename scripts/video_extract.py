#!/usr/bin/env python3
"""
Video Extractor Script
======================
Extracts from MP4 (and other video) files:
1. VTT subtitles using OpenAI Whisper (speech-to-text)
2. Scene-change images using PySceneDetect + OpenCV

Output follows the same __FRAGMENTS__/ structure as doc_converter.py:
    __FRAGMENTS__/{VideoName}/
        markdown/{VideoName}_whisper.vtt
        images/cadre_000.jpg, cadre_001.jpg, ...

Integrates with the existing manifest (.manifest.json) for incremental
processing and SHA256 change detection.

Usage:
    # Process all videos in __SPECS__ (or current directory):
    python scripts/video_extract.py

    # Process a single video:
    python scripts/video_extract.py --file "presentation.mp4"

    # Force reprocessing:
    python scripts/video_extract.py --force

    # Adjust scene detection sensitivity (lower = more sensitive):
    python scripts/video_extract.py --threshold 20.0

    # Use a larger Whisper model for better accuracy:
    python scripts/video_extract.py --whisper-model medium

Requirements:
    pip install openai-whisper scenedetect[opencv] opencv-python-headless
"""

import os
import sys
import json
import hashlib
import argparse
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import logging

# Suppress noisy warnings from Whisper/torch
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger("video_extract")

# Supported video extensions
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv"}

# Directories to skip when scanning
SKIP_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "__FRAGMENTS__", ".tmp", ".tox", ".mypy_cache", ".pytest_cache",
}


# ---------------------------------------------------------------------------
# Utility helpers (mirror doc_converter patterns)
# ---------------------------------------------------------------------------

def get_file_hash(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_manifest(manifest_path: Path) -> Dict:
    if manifest_path.exists():
        with open(manifest_path, "r") as fh:
            return json.load(fh)
    return {"files": {}, "last_updated": None}


def save_manifest(manifest_path: Path, manifest: Dict):
    manifest["last_updated"] = datetime.now().isoformat()
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)


def manifest_key(filepath: Path) -> str:
    cwd = Path.cwd().resolve()
    try:
        return str(filepath.resolve().relative_to(cwd))
    except ValueError:
        return str(filepath.name)


def needs_processing(filepath: Path, manifest: Dict, force: bool = False) -> bool:
    if force:
        return True
    key = manifest_key(filepath)
    current_hash = get_file_hash(filepath)
    if key not in manifest["files"]:
        return True
    prev = manifest["files"][key]
    if prev.get("hash") != current_hash:
        return True
    if prev.get("status") in ("error", "failed", "pending"):
        return True
    return False


# ---------------------------------------------------------------------------
# Whisper VTT generation
# ---------------------------------------------------------------------------

def generate_vtt(video_path: Path, output_dir: Path,
                 model_name: str = "base") -> Optional[Path]:
    """Transcribe video audio to VTT subtitle file using Whisper."""
    try:
        import whisper
        from whisper.utils import get_writer
    except ImportError:
        logger.error("openai-whisper not installed. Run: pip install openai-whisper")
        return None

    logger.info(f"  Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)

    logger.info(f"  Transcribing audio...")
    result = model.transcribe(str(video_path))

    # Write VTT file
    vtt_writer = get_writer("vtt", str(output_dir))
    vtt_writer(result, str(video_path))

    # Whisper names output after the input stem
    expected_vtt = output_dir / f"{video_path.stem}.vtt"
    # Rename to follow our naming convention
    final_vtt = output_dir / f"{video_path.stem}_whisper.vtt"
    if expected_vtt.exists() and expected_vtt != final_vtt:
        expected_vtt.rename(final_vtt)
    elif not expected_vtt.exists() and not final_vtt.exists():
        # Try to find any .vtt written
        vtts = list(output_dir.glob("*.vtt"))
        if vtts:
            vtts[0].rename(final_vtt)
        else:
            logger.warning("  Whisper did not produce a VTT file")
            return None

    logger.info(f"  VTT saved: {final_vtt.name}")
    return final_vtt


# ---------------------------------------------------------------------------
# Scene detection + frame extraction
# ---------------------------------------------------------------------------

def extract_scene_frames(video_path: Path, output_dir: Path,
                         threshold: float = 27.0) -> List[Path]:
    """Detect scene changes and save the first frame of each new scene."""
    try:
        from scenedetect import detect, ContentDetector
    except ImportError:
        logger.error(
            "scenedetect not installed. Run: pip install scenedetect[opencv]"
        )
        return []

    try:
        import cv2
    except ImportError:
        logger.error("opencv not installed. Run: pip install opencv-python-headless")
        return []

    logger.info(f"  Detecting scene changes (threshold={threshold})...")
    scene_list = detect(str(video_path), ContentDetector(threshold=threshold))
    logger.info(f"  Found {len(scene_list)} scene changes")

    if not scene_list:
        # If no scene changes detected, save the first frame as a fallback
        cap = cv2.VideoCapture(str(video_path))
        success, frame = cap.read()
        saved = []
        if success:
            img_path = output_dir / "cadre_000.jpg"
            cv2.imwrite(str(img_path), frame)
            saved.append(img_path)
            logger.info(f"  No scene changes found; saved first frame")
        cap.release()
        return saved

    cap = cv2.VideoCapture(str(video_path))
    saved_images = []

    for i, scene in enumerate(scene_list):
        start_frame = scene[0].get_frames()
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        success, frame = cap.read()
        if success:
            img_path = output_dir / f"cadre_{i:03d}.jpg"
            cv2.imwrite(str(img_path), frame)
            saved_images.append(img_path)

    cap.release()
    logger.info(f"  Saved {len(saved_images)} scene images")
    return saved_images


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_video(filepath: Path, fragments_dir: Path,
                  whisper_model: str = "base",
                  threshold: float = 27.0) -> Dict:
    """Process a single video file — VTT + scene images."""
    results = {
        "source":       str(filepath),
        "hash":         get_file_hash(filepath),
        "processed_at": datetime.now().isoformat(),
        "vtt":          None,
        "images":       [],
        "status":       "pending",
        "type":         "video",
    }

    safe_stem = filepath.stem
    doc_dir = fragments_dir / safe_stem
    doc_dir.mkdir(parents=True, exist_ok=True)

    # VTT goes into markdown/ (text content, parallel to _markitdown.md)
    markdown_dir = doc_dir / "markdown"
    images_dir = doc_dir / "images"
    markdown_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Processing video: {filepath.name}")
    logger.info(f"{'=' * 60}")

    # 1. VTT subtitles
    logger.info("→ Generating VTT subtitles (Whisper)…")
    vtt_path = generate_vtt(filepath, markdown_dir, model_name=whisper_model)
    if vtt_path:
        results["vtt"] = str(vtt_path.relative_to(fragments_dir))

    # 2. Scene-change images
    logger.info("→ Extracting scene-change frames…")
    images = extract_scene_frames(filepath, images_dir, threshold=threshold)
    results["images"] = [str(img.relative_to(fragments_dir)) for img in images]

    # Status
    has_vtt = bool(results["vtt"])
    has_img = bool(results["images"])

    if has_vtt and has_img:
        results["status"] = "complete"
    elif has_vtt:
        results["status"] = "vtt_only"
    elif has_img:
        results["status"] = "images_only"
    else:
        results["status"] = "failed"

    logger.info(f"→ Status: {results['status']}")
    return results


def scan_for_videos(scan_dir: Path) -> List[Path]:
    """Recursively find video files, skipping excluded directories."""
    videos = []
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(Path(root) / f)
    return sorted(videos)


def main():
    parser = argparse.ArgumentParser(
        description="Extract VTT subtitles and scene-change images from videos"
    )
    parser.add_argument(
        "--file", type=str, help="Process a single video file"
    )
    parser.add_argument(
        "--scan-dir", type=str,
        help="Directory to scan (default: __SPECS__ if it exists, else cwd)"
    )
    parser.add_argument(
        "--fragments-dir", type=str, default="__FRAGMENTS__",
        help="Output fragments directory (default: __FRAGMENTS__)"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Force reprocessing even if unchanged"
    )
    parser.add_argument(
        "--whisper-model", type=str, default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--threshold", type=float, default=27.0,
        help="Scene detection sensitivity — lower = more sensitive (default: 27.0)"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    fragments_dir = Path(args.fragments_dir)
    fragments_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = fragments_dir / ".manifest.json"
    manifest = load_manifest(manifest_path)

    # Determine files to process
    if args.file:
        video_files = [Path(args.file)]
        if not video_files[0].exists():
            logger.error(f"File not found: {args.file}")
            sys.exit(1)
    else:
        scan_dir = Path(args.scan_dir) if args.scan_dir else None
        if scan_dir is None:
            specs = Path("__SPECS__")
            scan_dir = specs if specs.is_dir() else Path(".")
        logger.info(f"Scanning {scan_dir} for video files...")
        video_files = scan_for_videos(scan_dir)
        logger.info(f"Found {len(video_files)} video file(s)")

    if not video_files:
        logger.info("No video files to process.")
        return

    # Process
    processed = 0
    skipped = 0
    failed = 0

    for vf in video_files:
        if not needs_processing(vf, manifest, force=args.force):
            logger.info(f"Skipping (unchanged): {vf.name}")
            skipped += 1
            continue

        try:
            results = process_video(
                vf, fragments_dir,
                whisper_model=args.whisper_model,
                threshold=args.threshold,
            )
            key = manifest_key(vf)
            manifest["files"][key] = results
            save_manifest(manifest_path, manifest)
            processed += 1
        except Exception as e:
            logger.error(f"FAILED: {vf.name} — {e}")
            key = manifest_key(vf)
            manifest["files"][key] = {
                "source": str(vf),
                "hash": get_file_hash(vf),
                "processed_at": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
                "type": "video",
            }
            save_manifest(manifest_path, manifest)
            failed += 1

    logger.info(f"\nDone — processed: {processed}, skipped: {skipped}, failed: {failed}")


if __name__ == "__main__":
    main()
