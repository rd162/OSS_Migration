#!/usr/bin/env python3
"""
Image Verification Script
=========================
Verifies that generated WEBP images are valid and readable for LLM vision processing.

This script:
1. Scans __FRAGMENTS__ for generated WEBP images
2. Validates image format, dimensions, and readability
3. Reports on image quality and suitability for vision models
4. Generates a verification report

Usage:
    python verify_images.py [--fragments-dir PATH]

Note: The images can be read by LLM vision models using read_file tool
      with the image path (e.g., read_file("__FRAGMENTS__/docname/images/file.webp"))
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Vision model constraints
MIN_IMAGE_SIZE = 10 * 1024  # 10KB minimum
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB maximum
MIN_DIMENSION = 100  # pixels
MAX_DIMENSION = 8192  # pixels (most vision models support up to 4096-8192)
RECOMMENDED_MAX_DIMENSION = 4096  # For optimal processing


def get_image_info(filepath: Path) -> Dict:
    """Get image metadata using Pillow."""
    try:
        from PIL import Image
        
        with Image.open(filepath) as img:
            return {
                "valid": True,
                "format": img.format,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
                "size_bytes": filepath.stat().st_size,
                "size_mb": round(filepath.stat().st_size / (1024 * 1024), 2),
            }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def check_image_suitability(info: Dict) -> Tuple[bool, List[str]]:
    """Check if image is suitable for LLM vision processing."""
    issues = []
    
    if not info.get("valid"):
        return False, [f"Invalid image: {info.get('error', 'Unknown error')}"]
    
    # Check size
    size_bytes = info.get("size_bytes", 0)
    if size_bytes < MIN_IMAGE_SIZE:
        issues.append(f"Image too small ({size_bytes} bytes < {MIN_IMAGE_SIZE} bytes)")
    if size_bytes > MAX_IMAGE_SIZE:
        issues.append(f"Image too large ({info['size_mb']}MB > {MAX_IMAGE_SIZE // (1024*1024)}MB)")
    
    # Check dimensions
    width = info.get("width", 0)
    height = info.get("height", 0)
    
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        issues.append(f"Dimensions too small ({width}x{height} < {MIN_DIMENSION}px min)")
    
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        issues.append(f"Dimensions exceed max ({width}x{height} > {MAX_DIMENSION}px)")
    
    # Warnings (not failures)
    warnings = []
    if width > RECOMMENDED_MAX_DIMENSION or height > RECOMMENDED_MAX_DIMENSION:
        warnings.append(f"Large dimensions ({width}x{height}) may be downscaled by vision model")
    
    suitable = len(issues) == 0
    return suitable, issues + warnings


def verify_image_readability(filepath: Path) -> bool:
    """Verify image can be fully read and decoded."""
    try:
        from PIL import Image
        
        with Image.open(filepath) as img:
            # Force full decode
            img.load()
            # Verify we can access pixel data
            img.getpixel((0, 0))
        return True
    except Exception as e:
        logger.warning(f"⚠ Readability check failed: {e}")
        return False


def scan_fragments_directory(fragments_dir: Path) -> List[Path]:
    """Find all WEBP images in fragments directory."""
    images = []
    
    for webp_file in fragments_dir.rglob("*.webp"):
        images.append(webp_file)
    
    return sorted(images)


def generate_report(results: List[Dict], fragments_dir: Path) -> Path:
    """Generate verification report."""
    report_path = fragments_dir / "IMAGE_VERIFICATION_REPORT.md"
    
    total = len(results)
    valid = sum(1 for r in results if r.get("suitable"))
    invalid = total - valid
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Image Verification Report\n\n")
        f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Total Images | {total} |\n")
        f.write(f"| Valid for Vision | {valid} |\n")
        f.write(f"| Issues Found | {invalid} |\n")
        f.write(f"| Success Rate | {(valid/total*100) if total > 0 else 0:.1f}% |\n\n")
        
        f.write("## Vision Model Compatibility\n\n")
        f.write("These images are designed for LLM vision processing:\n\n")
        f.write("- **Format:** WEBP (widely supported)\n")
        f.write("- **Sliding Window:** Each image contains 3 consecutive pages\n")
        f.write("- **Resolution:** Optimized for text readability\n")
        f.write("- **Access Method:** Use `read_file(path)` tool\n\n")
        
        f.write("## Image Details\n\n")
        
        # Group by document
        by_doc = {}
        for r in results:
            doc_name = r["path"].parent.parent.name
            if doc_name not in by_doc:
                by_doc[doc_name] = []
            by_doc[doc_name].append(r)
        
        for doc_name, doc_results in sorted(by_doc.items()):
            f.write(f"### {doc_name}\n\n")
            f.write("| Image | Dimensions | Size | Status |\n")
            f.write("|-------|------------|------|--------|\n")
            
            for r in doc_results:
                info = r.get("info", {})
                status = "✓" if r.get("suitable") else "✗"
                dims = f"{info.get('width', '?')}x{info.get('height', '?')}"
                size = f"{info.get('size_mb', '?')}MB"
                
                rel_path = r["path"].relative_to(fragments_dir)
                f.write(f"| [{r['path'].name}]({rel_path}) | {dims} | {size} | {status} |\n")
            
            f.write("\n")
        
        if invalid > 0:
            f.write("## Issues Found\n\n")
            for r in results:
                if not r.get("suitable") and r.get("issues"):
                    f.write(f"**{r['path'].name}:**\n")
                    for issue in r["issues"]:
                        f.write(f"  - {issue}\n")
                    f.write("\n")
        
        f.write("## Usage Example\n\n")
        f.write("To read these images with an LLM that supports vision:\n\n")
        f.write("```python\n")
        f.write("# Using read_file tool (supports vision for image files)\n")
        f.write('image_content = read_file("__FRAGMENTS__/document_name/images/image.webp")\n')
        f.write("# The LLM will receive the image for visual analysis\n")
        f.write("```\n\n")
    
    return report_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify generated WEBP images for LLM vision processing"
    )
    parser.add_argument(
        '--fragments-dir',
        type=Path,
        default=Path(__file__).parent / "__FRAGMENTS__",
        help="Directory containing generated fragments"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Show detailed output for each image"
    )
    
    args = parser.parse_args()
    
    if not args.fragments_dir.exists():
        logger.error(f"✗ Fragments directory not found: {args.fragments_dir}")
        logger.info("Run doc_converter.py first to generate fragments")
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("Image Verification for LLM Vision Processing")
    logger.info("="*60)
    
    # Find images
    images = scan_fragments_directory(args.fragments_dir)
    logger.info(f"Found {len(images)} WEBP image(s)")
    
    if not images:
        logger.warning("No images found. Run doc_converter.py first.")
        sys.exit(0)
    
    # Verify each image
    results = []
    
    for img_path in images:
        if args.verbose:
            logger.info(f"Checking: {img_path.name}")
        
        info = get_image_info(img_path)
        suitable, issues = check_image_suitability(info)
        readable = verify_image_readability(img_path) if info.get("valid") else False
        
        result = {
            "path": img_path,
            "info": info,
            "suitable": suitable and readable,
            "readable": readable,
            "issues": issues
        }
        results.append(result)
        
        if args.verbose:
            status = "✓" if result["suitable"] else "✗"
            logger.info(f"  {status} {info.get('width', '?')}x{info.get('height', '?')} | {info.get('size_mb', '?')}MB")
            for issue in issues:
                logger.info(f"    ⚠ {issue}")
    
    # Generate report
    report_path = generate_report(results, args.fragments_dir)
    
    # Summary
    valid_count = sum(1 for r in results if r["suitable"])
    
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✓ Valid images:   {valid_count}/{len(results)}")
    logger.info(f"✗ Issues found:   {len(results) - valid_count}")
    logger.info(f"📄 Report:        {report_path}")
    logger.info("="*60)
    
    # Print usage hint
    if valid_count > 0:
        sample_img = next((r["path"] for r in results if r["suitable"]), None)
        if sample_img:
            rel_path = sample_img.relative_to(args.fragments_dir.parent)
            logger.info("\n💡 To use with LLM vision:")
            logger.info(f'   read_file("{rel_path}")')
    
    sys.exit(0 if valid_count == len(results) else 1)


if __name__ == "__main__":
    main()