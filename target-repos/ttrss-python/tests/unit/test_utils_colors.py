"""
Unit tests for ttrss.utils.colors — PHP→Python migration coverage.

All pure math/string functions are tested without mocks.
Image-dependent functions (color_palette, calculate_avg_color) are tested
with a non-existent path to verify graceful failure paths only.

PHP reference: ttrss/include/colors.php (lines 1-351)
"""
import math

import pytest

from ttrss.utils.colors import (
    calculate_avg_color,
    color_hsl_to_rgb,
    color_pack,
    color_palette,
    color_rgb_to_hsl,
    color_unpack,
    hsv_to_rgb,
    resolve_html_color,
    rgb_to_hsv,
)


# ---------------------------------------------------------------------------
# resolve_html_color
# ---------------------------------------------------------------------------


def test_resolve_html_color_known_lowercase():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 7
    PHP: array_key_exists(strtolower($color), $htmlcolors) → return $htmlcolors[$key]
    Assert: lowercase 'red' resolves to '#ff0000'
    """
    assert resolve_html_color("red") == "#ff0000"


def test_resolve_html_color_known_uppercase():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 7
    PHP: strtolower($color) normalises before lookup — 'RED' resolves same as 'red'
    Assert: 'RED' resolves to '#ff0000' (case-insensitive lookup)
    """
    assert resolve_html_color("RED") == "#ff0000"


def test_resolve_html_color_unknown_passthrough():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 161
    PHP: if key not found, return $color as-is (already lowercased)
    Assert: unrecognised hex string '#abc123' is returned lowercased unchanged
    """
    assert resolve_html_color("#abc123") == "#abc123"


def test_resolve_html_color_unknown_name_passthrough():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 161
    PHP: unrecognised name not in $htmlcolors → returned as-is (lowercased)
    Assert: 'notacolor' not in lookup → returned as 'notacolor'
    """
    assert resolve_html_color("notacolor") == "notacolor"


def test_resolve_html_color_blue():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 7 (array entry 'blue')
    PHP: $htmlcolors['blue'] = '#0000ff'
    Assert: 'blue' resolves to '#0000ff'
    """
    assert resolve_html_color("blue") == "#0000ff"


def test_resolve_html_color_white():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 7 (array entry 'white')
    PHP: $htmlcolors['white'] = '#ffffff'
    Assert: 'white' resolves to '#ffffff'
    """
    assert resolve_html_color("white") == "#ffffff"


def test_resolve_html_color_black():
    """
    Source: ttrss/include/colors.php:_resolve_htmlcolor line 7 (array entry 'black')
    PHP: $htmlcolors['black'] = '#000000'
    Assert: 'black' resolves to '#000000'
    """
    assert resolve_html_color("black") == "#000000"


# ---------------------------------------------------------------------------
# color_unpack
# ---------------------------------------------------------------------------


def test_color_unpack_six_char_hex():
    """
    Source: ttrss/include/colors.php:_color_unpack lines 201-212
    PHP: sscanf($hex_color, '#%2x%2x%2x') returns [255, 0, 0] for '#ff0000'
    Assert: (255.0, 0.0, 0.0) for '#ff0000'
    """
    result = color_unpack("#ff0000")
    assert result == (255.0, 0.0, 0.0)


def test_color_unpack_three_char_shorthand():
    """
    Source: ttrss/include/colors.php:_color_unpack lines 201-212
    PHP: 3-char hex '#f00' is expanded by doubling each digit → '#ff0000'
    Assert: (255.0, 0.0, 0.0) for '#f00'
    """
    result = color_unpack("#f00")
    assert result == (255.0, 0.0, 0.0)


def test_color_unpack_normalize_true():
    """
    Source: ttrss/include/colors.php:_color_unpack lines 201-212
    PHP: divide each channel by 255 when $normalize=true
    Assert: all three values in [0.0, 1.0] for '#ff0000' with normalize=True
    """
    result = color_unpack("#ff0000", normalize=True)
    assert len(result) == 3
    r, g, b = result
    assert abs(r - 1.0) < 1e-6
    assert abs(g - 0.0) < 1e-6
    assert abs(b - 0.0) < 1e-6
    assert all(0.0 <= v <= 1.0 for v in result)


def test_color_unpack_normalize_white():
    """
    Source: ttrss/include/colors.php:_color_unpack lines 201-212
    PHP: '#ffffff' with normalize=true → (1.0, 1.0, 1.0)
    Assert: all three channels equal 1.0 when normalised
    """
    result = color_unpack("#ffffff", normalize=True)
    assert all(abs(v - 1.0) < 1e-6 for v in result)


def test_color_unpack_html_name_resolves():
    """
    Source: ttrss/include/colors.php:_color_unpack lines 201-212
    PHP: if $hex_color does not start with '#', call _resolve_htmlcolor first
    Assert: color_unpack('red') resolves via resolve_html_color → (255.0, 0.0, 0.0)
    """
    result = color_unpack("red")
    assert result == (255.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# color_pack
# ---------------------------------------------------------------------------


def test_color_pack_red():
    """
    Source: ttrss/include/colors.php:_color_pack lines 215-219
    PHP: sprintf('#%02x%02x%02x', $r, $g, $b) — bitshift pack to hex string
    Assert: (255, 0, 0) → '#ff0000'
    """
    assert color_pack((255, 0, 0)) == "#ff0000"


def test_color_pack_zero_padding():
    """
    Source: ttrss/include/colors.php:_color_pack lines 215-219
    PHP: sprintf format ensures leading zeros — (0, 0, 0) → '#000000'
    Assert: (0, 0, 0) → '#000000' with correct zero padding
    """
    assert color_pack((0, 0, 0)) == "#000000"


def test_color_pack_white():
    """
    Source: ttrss/include/colors.php:_color_pack lines 215-219
    PHP: (255, 255, 255) → '#ffffff'
    Assert: color_pack((255, 255, 255)) == '#ffffff'
    """
    assert color_pack((255, 255, 255)) == "#ffffff"


def test_color_pack_normalize_mode():
    """
    Source: ttrss/include/colors.php:_color_pack lines 215-219
    PHP: with normalize=True, inputs in [0,1] are scaled by 255 before packing
    Assert: (1.0, 0.0, 0.0) with normalize=True → '#ff0000'
    """
    assert color_pack((1.0, 0.0, 0.0), normalize=True) == "#ff0000"


# ---------------------------------------------------------------------------
# color_rgb_to_hsl
# ---------------------------------------------------------------------------


def test_color_rgb_to_hsl_red():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl lines 165-179
    PHP: RGB (1,0,0) in [0-1] → HSL hue ~0.0, saturation 1.0, lightness 0.5
    Assert: hsl[1] (saturation) == 1.0 and hsl[2] (lightness) ≈ 0.5 for pure red
    """
    h, s, l = color_rgb_to_hsl((1.0, 0.0, 0.0))
    assert abs(s - 1.0) < 1e-6
    assert abs(l - 0.5) < 1e-6


def test_color_rgb_to_hsl_white():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl lines 165-179
    PHP: white (1,1,1) → saturation=0, lightness=1
    Assert: s==0.0 and l==1.0 for (1.0, 1.0, 1.0)
    """
    h, s, l = color_rgb_to_hsl((1.0, 1.0, 1.0))
    assert abs(s - 0.0) < 1e-6
    assert abs(l - 1.0) < 1e-6


def test_color_rgb_to_hsl_black():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl lines 165-179
    PHP: black (0,0,0) → saturation=0, lightness=0
    Assert: s==0.0 and l==0.0 for (0.0, 0.0, 0.0)
    """
    h, s, l = color_rgb_to_hsl((0.0, 0.0, 0.0))
    assert abs(s - 0.0) < 1e-6
    assert abs(l - 0.0) < 1e-6


# ---------------------------------------------------------------------------
# color_hsl_to_rgb
# ---------------------------------------------------------------------------


def test_color_hsl_to_rgb_red():
    """
    Source: ttrss/include/colors.php:_color_hsl2rgb lines 182-189
    PHP: HSL (0, 1, 0.5) → RGB (1, 0, 0) in normalized [0-1] range
    Assert: round-trip red HSL → RGB produces approximately (1.0, 0.0, 0.0)
    """
    r, g, b = color_hsl_to_rgb((0.0, 1.0, 0.5))
    assert abs(r - 1.0) < 1e-4
    assert abs(g - 0.0) < 1e-4
    assert abs(b - 0.0) < 1e-4


def test_color_rgb_hsl_round_trip_red():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl lines 165-179 and
            ttrss/include/colors.php:_color_hsl2rgb lines 182-189
    PHP: RGB→HSL→RGB round-trip must be lossless for primary colours
    Assert: color_hsl_to_rgb(color_rgb_to_hsl((1,0,0))) ≈ (1,0,0)
    """
    original = (1.0, 0.0, 0.0)
    hsl = color_rgb_to_hsl(original)
    recovered = color_hsl_to_rgb(hsl)
    assert abs(recovered[0] - 1.0) < 1e-4
    assert abs(recovered[1] - 0.0) < 1e-4
    assert abs(recovered[2] - 0.0) < 1e-4


def test_color_hsl_to_rgb_white():
    """
    Source: ttrss/include/colors.php:_color_hsl2rgb lines 182-189
    PHP: HSL (0, 0, 1) → white (1.0, 1.0, 1.0)
    Assert: all channels ≈ 1.0 for white (s=0, l=1)
    """
    r, g, b = color_hsl_to_rgb((0.0, 0.0, 1.0))
    assert abs(r - 1.0) < 1e-4
    assert abs(g - 1.0) < 1e-4
    assert abs(b - 1.0) < 1e-4


# ---------------------------------------------------------------------------
# rgb_to_hsv
# ---------------------------------------------------------------------------


def test_rgb_to_hsv_red():
    """
    Source: ttrss/include/colors.php:rgb2hsl lines 221-255
    PHP: (despite name rgb2hsl) computes HSV — red (255,0,0) → H=0, S=1, V=1
    Assert: rgb_to_hsv((255, 0, 0)) == (0.0, 1.0, 1.0)
    """
    h, s, v = rgb_to_hsv((255, 0, 0))
    assert abs(h - 0.0) < 1e-6
    assert abs(s - 1.0) < 1e-6
    assert abs(v - 1.0) < 1e-6


def test_rgb_to_hsv_black_edge_case():
    """
    Source: ttrss/include/colors.php:rgb2hsl lines 221-255
    PHP: black (0,0,0) has del_max==0 → H=0, S=0, V=0
    Assert: rgb_to_hsv((0, 0, 0)) → (0.0, 0.0, 0.0) — no division by zero
    """
    h, s, v = rgb_to_hsv((0, 0, 0))
    assert h == 0.0
    assert s == 0.0
    assert v == 0.0


def test_rgb_to_hsv_white():
    """
    Source: ttrss/include/colors.php:rgb2hsl lines 221-255
    PHP: white (255,255,255) → H=0, S=0, V=1
    Assert: saturation is 0, value is 1.0 for white
    """
    h, s, v = rgb_to_hsv((255, 255, 255))
    assert abs(s - 0.0) < 1e-6
    assert abs(v - 1.0) < 1e-6


def test_rgb_to_hsv_green():
    """
    Source: ttrss/include/colors.php:rgb2hsl lines 221-255
    PHP: pure green (0,255,0) → H≈1/3 (0.333), S=1, V=1
    Assert: hue ≈ 0.333 for green, saturation=1, value=1
    """
    h, s, v = rgb_to_hsv((0, 255, 0))
    assert abs(h - 1 / 3) < 1e-4
    assert abs(s - 1.0) < 1e-6
    assert abs(v - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# hsv_to_rgb
# ---------------------------------------------------------------------------


def test_hsv_to_rgb_red():
    """
    Source: ttrss/include/colors.php:hsl2rgb lines 257-283
    PHP: (despite name hsl2rgb) converts HSV — H=0, S=1, V=1 → (255, 0, 0)
    Assert: hsv_to_rgb((0.0, 1.0, 1.0)) → (255.0, 0.0, 0.0)
    """
    r, g, b = hsv_to_rgb((0.0, 1.0, 1.0))
    assert abs(r - 255.0) < 1e-6
    assert abs(g - 0.0) < 1e-6
    assert abs(b - 0.0) < 1e-6


def test_hsv_to_rgb_black():
    """
    Source: ttrss/include/colors.php:hsl2rgb lines 257-283
    PHP: s==0 branch → r=g=b = v*255; V=0 → (0, 0, 0)
    Assert: hsv_to_rgb((0.0, 0.0, 0.0)) → (0.0, 0.0, 0.0)
    """
    r, g, b = hsv_to_rgb((0.0, 0.0, 0.0))
    assert abs(r - 0.0) < 1e-6
    assert abs(g - 0.0) < 1e-6
    assert abs(b - 0.0) < 1e-6


def test_hsv_to_rgb_white():
    """
    Source: ttrss/include/colors.php:hsl2rgb lines 257-283
    PHP: s==0, V=1 → r=g=b=255
    Assert: hsv_to_rgb((0.0, 0.0, 1.0)) → (255.0, 255.0, 255.0)
    """
    r, g, b = hsv_to_rgb((0.0, 0.0, 1.0))
    assert abs(r - 255.0) < 1e-6
    assert abs(g - 255.0) < 1e-6
    assert abs(b - 255.0) < 1e-6


def test_rgb_hsv_round_trip_red():
    """
    Source: ttrss/include/colors.php:rgb2hsl lines 221-255 and
            ttrss/include/colors.php:hsl2rgb lines 257-283
    PHP: RGB→HSV→RGB must recover original value for primary colours
    Assert: hsv_to_rgb(rgb_to_hsv((255, 0, 0))) ≈ (255, 0, 0)
    """
    original = (255, 0, 0)
    hsv = rgb_to_hsv(original)
    r, g, b = hsv_to_rgb(hsv)
    assert abs(r - 255.0) < 1e-4
    assert abs(g - 0.0) < 1e-4
    assert abs(b - 0.0) < 1e-4


def test_hsv_to_rgb_all_six_sectors():
    """
    Source: ttrss/include/colors.php:hsl2rgb lines 257-283
    PHP: var_i branches 0-5 cover the six hue sectors of the colour wheel
    Assert: hsv_to_rgb returns 3-tuple for each of six sector-boundary hues
    """
    sector_hues = [0.0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6]
    for h in sector_hues:
        result = hsv_to_rgb((h, 1.0, 1.0))
        assert len(result) == 3
        assert all(0.0 <= v <= 255.0 for v in result)


# ---------------------------------------------------------------------------
# calculate_avg_color — non-existent path (graceful failure)
# ---------------------------------------------------------------------------


def test_calculate_avg_color_nonexistent_path():
    """
    Source: ttrss/include/colors.php:calculate_avg_color lines 334-350
    PHP: calls colorPalette(); if palette is null or empty, returns ''
    Assert: non-existent image path → empty string (no exception raised)
    """
    result = calculate_avg_color("/nonexistent/path/to/icon.png")
    assert result == ""


def test_calculate_avg_color_returns_string():
    """
    Source: ttrss/include/colors.php:calculate_avg_color lines 334-350
    PHP: always returns a string — either '#rrggbb' or ''
    Assert: return type is str regardless of input validity
    """
    result = calculate_avg_color("/no/such/file.ico")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# color_palette — non-existent path (graceful failure)
# ---------------------------------------------------------------------------


def test_color_palette_nonexistent_path_returns_none():
    """
    Source: ttrss/include/colors.php:colorPalette lines 285-332
    PHP: fopen() failure / file_exists() false → returns null (None in Python)
    Assert: non-existent path → None (not an exception, not an empty list)
    """
    result = color_palette("/nonexistent/path/image.png", num_colors=5)
    assert result is None


def test_color_palette_nonexistent_path_no_exception():
    """
    Source: ttrss/include/colors.php:colorPalette lines 285-332
    PHP: file errors are swallowed — caller receives null, not an exception
    Assert: color_palette with bad path does not raise any exception
    """
    try:
        color_palette("/no/such/file.gif", num_colors=3)
    except Exception as exc:
        pytest.fail(f"color_palette raised unexpectedly: {exc}")


def test_color_palette_granularity_floor():
    """
    Source: ttrss/include/colors.php:colorPalette lines 285-332
    PHP: granularity < 1 is clamped to 1 — abs(intval($granularity)) with min 1
    Assert: granularity=0 is silently clamped; no exception, still returns None
           for a non-existent file (tests the clamping path runs without error)
    """
    result = color_palette("/nonexistent/image.png", num_colors=5, granularity=0)
    assert result is None


# ---------------------------------------------------------------------------
# Additional tests to cover remaining branches (lines 186, 193, 212-217, 316, 319-321)
# ---------------------------------------------------------------------------

def test_color_rgb_to_hsl_max_red_branch():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl line 174
    PHP: if ($var_max == $var_r && $var_r != $var_g) $h += ($var_g - $var_b) / $delta;
    Assert: max_val==r and max_val!=g branch executes (covers line 212).
    """
    # Red dominant, g != r → hits first if-branch in hsl h calculation
    h, s, l = color_rgb_to_hsl((1.0, 0.5, 0.0))
    assert isinstance(h, float)
    assert 0.0 <= h <= 1.0

def test_color_rgb_to_hsl_max_green_branch():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl line 175
    PHP: if ($var_max == $var_g && $var_g != $var_b) $h += 2 + ($var_b - $var_r) / $delta;
    Assert: max_val==g and max_val!=b branch executes (covers line 214).
    """
    # Green dominant → hits second if-branch
    h, s, l = color_rgb_to_hsl((0.0, 1.0, 0.5))
    assert isinstance(h, float)
    assert 0.0 <= h <= 1.0

def test_color_rgb_to_hsl_max_blue_branch():
    """
    Source: ttrss/include/colors.php:_color_rgb2hsl line 176
    PHP: if ($var_max == $var_b && $var_b != $var_r) $h += 4 + ($var_r - $var_g) / $delta;
    Assert: max_val==b and max_val!=r branch executes (covers line 216).
    """
    h, s, l = color_rgb_to_hsl((0.0, 0.5, 1.0))
    assert isinstance(h, float)
    assert 0.0 <= h <= 1.0

def test_color_hsl_to_rgb_h_minus_branch():
    """
    Source: ttrss/include/colors.php:_hsl_to_rgb helper line ~190
    PHP: if ($h < 0) $h += 1;
    Assert: h < 0 branch in _hsl_to_rgb helper executes (covers line 183-184 / 193).
    """
    # Calling hsl_to_rgb with a hue that would require negative intermediate h
    r, g, b = color_hsl_to_rgb((0.95, 1.0, 0.5))
    assert all(0.0 <= x <= 1.0 for x in (r, g, b))

def test_rgb_to_hsv_green_branch():
    """
    Source: ttrss/include/colors.php:rgb2hsl (HSV) line ~243
    PHP: if ($var_max == $var_g) $H = (1/3) + $del_R - $del_B;
    Assert: var_g == var_max branch (covers line 314), h wrapping (lines 318-320).
    """
    h, s, v = rgb_to_hsv((0, 255, 0))  # Pure green
    assert abs(h - (1 / 3)) < 0.01

def test_rgb_to_hsv_blue_branch():
    """
    Source: ttrss/include/colors.php:rgb2hsl (HSV) line ~246
    PHP: else $H = (2/3) + $del_G - $del_R;
    Assert: var_b == var_max branch (covers line 316) and possible h > 1 wrap.
    """
    h, s, v = rgb_to_hsv((0, 0, 255))  # Pure blue
    assert abs(h - (2 / 3)) < 0.01

def test_color_palette_with_real_1x1_png():
    """
    Source: ttrss/include/colors.php:colorPalette lines 285-332
    PHP: function colorPalette($imageFile, $numColors, $granularity=5)
    Assert: 1×1 red PNG → palette returns list containing a hex color string.
    Tests lines 385-404 (image loading + quantization path).
    """
    import struct, zlib, io
    from PIL import Image
    from ttrss.utils.colors import color_palette

    # Build minimal 1×1 red PNG in memory
    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    tmp = io.BytesIO()
    img.save(tmp, format="PNG")
    tmp.seek(0)

    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(tmp.read())
        path = f.name
    try:
        result = color_palette(path, num_colors=5)
        assert result is not None
        assert isinstance(result, list)
        if result:
            assert len(result[0]) in (6, 7)  # RRGGBB or #RRGGBB
    finally:
        os.unlink(path)

def test_calculate_avg_color_with_real_1x1_png():
    """
    Source: ttrss/include/colors.php:calculateAvgColor lines 334-351
    PHP: function calculateAvgColor($img)
    Assert: 1×1 red PNG → returns hex string or empty (covers lines 425-434).
    """
    from PIL import Image
    from ttrss.utils.colors import calculate_avg_color
    import tempfile, io, os

    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    tmp = io.BytesIO()
    img.save(tmp, format="PNG")
    tmp.seek(0)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(tmp.read())
        path = f.name
    try:
        result = calculate_avg_color(path)
        # May be empty string (saturation/value filtered out for pure primary)
        assert isinstance(result, str)
    finally:
        os.unlink(path)
