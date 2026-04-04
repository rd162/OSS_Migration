"""Color utility functions for TT-RSS.

Provides color conversion (RGB/HSL/HSV), hex packing/unpacking,
HTML color name resolution, and image palette extraction.

Source: ttrss/include/colors.php (lines 1-351)
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image


# Source: ttrss/include/colors.php:_resolve_htmlcolor (lines 7-162)
_HTML_COLORS: dict[str, str] = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9",
    "darkgreen": "#006400",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "grey": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred ": "#cd5c5c",
    "indigo ": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}


# Source: ttrss/include/colors.php:_resolve_htmlcolor (lines 7-162)
def resolve_html_color(color: str) -> str:
    """Resolve an HTML color name to its hex value.

    If the color is already a hex string or not found in the lookup table,
    it is returned as-is (lowercased).
    """
    color = color.lower()
    return _HTML_COLORS.get(color, color)


# Source: ttrss/include/colors.php:_color_hue2rgb (lines 192-198)
def _color_hue_to_rgb(m1: float, m2: float, h: float) -> float:
    """Helper for HSL-to-RGB conversion."""
    if h < 0:
        h += 1
    elif h > 1:
        h -= 1

    if h * 6 < 1:
        return m1 + (m2 - m1) * h * 6
    if h * 2 < 1:
        return m2
    if h * 3 < 2:
        return m1 + (m2 - m1) * (0.66666 - h) * 6
    return m1


# Source: ttrss/include/colors.php:_color_rgb2hsl (lines 165-179)
def color_rgb_to_hsl(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert an RGB triplet (normalized 0-1) to HSL."""
    r, g, b = rgb
    min_val = min(r, g, b)
    max_val = max(r, g, b)
    delta = max_val - min_val
    l = (min_val + max_val) / 2
    s = 0.0

    if l > 0 and l < 1:
        s = delta / (2 * l if l < 0.5 else 2 - 2 * l)

    h = 0.0
    if delta > 0:
        if max_val == r and max_val != g:
            h += (g - b) / delta
        if max_val == g and max_val != b:
            h += 2 + (b - r) / delta
        if max_val == b and max_val != r:
            h += 4 + (r - g) / delta
        h /= 6

    return (h, s, l)


# Source: ttrss/include/colors.php:_color_hsl2rgb (lines 182-189)
def color_hsl_to_rgb(hsl: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert an HSL triplet to RGB (normalized 0-1)."""
    h, s, l = hsl
    m2 = l * (s + 1) if l <= 0.5 else l + s - l * s
    m1 = l * 2 - m2
    return (
        _color_hue_to_rgb(m1, m2, h + 0.33333),
        _color_hue_to_rgb(m1, m2, h),
        _color_hue_to_rgb(m1, m2, h - 0.33333),
    )


# Source: ttrss/include/colors.php:_color_unpack (lines 201-212)
def color_unpack(hex_color: str, normalize: bool = False) -> tuple[float, ...]:
    """Convert a hex color string (or HTML color name) into an RGB triplet.

    Args:
        hex_color: A hex color string like ``"#ff0000"`` or ``"#f00"``,
            or an HTML color name like ``"red"``.
        normalize: If True, values are normalized to 0.0-1.0 range.
            Otherwise, values are in 0-255 range.

    Returns:
        A 3-tuple of (R, G, B) values.
    """
    if not hex_color.startswith("#"):
        hex_color = resolve_html_color(hex_color)

    # Strip the leading '#'
    hex_str = hex_color.lstrip("#")

    # Expand shorthand (e.g. "f00" -> "ff0000")
    if len(hex_str) == 3:
        hex_str = hex_str[0] * 2 + hex_str[1] * 2 + hex_str[2] * 2

    c = int(hex_str, 16)
    out: list[float] = []
    for i in (16, 8, 0):
        val = (c >> i) & 0xFF
        out.append(val / 255 if normalize else float(val))

    return tuple(out)


# Source: ttrss/include/colors.php:_color_pack (lines 215-219)
def color_pack(rgb: tuple[float, ...], normalize: bool = False) -> str:
    """Convert an RGB triplet to a hex color string.

    Args:
        rgb: A 3-tuple of (R, G, B) values.
        normalize: If True, input values are in 0.0-1.0 range and will
            be scaled to 0-255 first.

    Returns:
        A hex color string like ``"#ff0000"``.
    """
    out = 0
    for k, v in enumerate(rgb):
        out |= int(v * 255 if normalize else v) << (16 - k * 8)
    return "#" + format(out, "06x")


# Source: ttrss/include/colors.php:rgb2hsl (lines 221-255)
# NOTE: Despite the PHP name "rgb2hsl", this actually computes HSV (value, not
# lightness). The Python name is corrected to rgb_to_hsv.
def rgb_to_hsv(arr: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert an RGB triplet (0-255) to HSV (all components 0-1)."""
    var_r = arr[0] / 255
    var_g = arr[1] / 255
    var_b = arr[2] / 255

    var_min = min(var_r, var_g, var_b)
    var_max = max(var_r, var_g, var_b)
    del_max = var_max - var_min

    v = var_max

    if del_max == 0:
        h = 0.0
        s = 0.0
    else:
        s = del_max / var_max

        del_r = (((var_max - var_r) / 6) + (del_max / 2)) / del_max
        del_g = (((var_max - var_g) / 6) + (del_max / 2)) / del_max
        del_b = (((var_max - var_b) / 6) + (del_max / 2)) / del_max

        if var_r == var_max:
            h = del_b - del_g
        elif var_g == var_max:
            h = (1 / 3) + del_r - del_b
        else:  # var_b == var_max
            h = (2 / 3) + del_g - del_r

        if h < 0:
            h += 1
        if h > 1:
            h -= 1

    return (h, s, v)


# Source: ttrss/include/colors.php:hsl2rgb (lines 257-283)
# NOTE: Despite the PHP name "hsl2rgb", this actually converts from HSV.
# The Python name is corrected to hsv_to_rgb.
def hsv_to_rgb(arr: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert an HSV triplet (all 0-1) to RGB (0-255)."""
    h, s, v = arr

    if s == 0:
        r = g = b = v * 255
    else:
        var_h = h * 6
        var_i = math.floor(var_h)
        var_1 = v * (1 - s)
        var_2 = v * (1 - s * (var_h - var_i))
        var_3 = v * (1 - s * (1 - (var_h - var_i)))

        if var_i == 0:
            var_r, var_g, var_b = v, var_3, var_1
        elif var_i == 1:
            var_r, var_g, var_b = var_2, v, var_1
        elif var_i == 2:
            var_r, var_g, var_b = var_1, v, var_3
        elif var_i == 3:
            var_r, var_g, var_b = var_1, var_2, v
        elif var_i == 4:
            var_r, var_g, var_b = var_3, var_1, v
        else:
            var_r, var_g, var_b = v, var_1, var_2

        r = var_r * 255
        g = var_g * 255
        b = var_b * 255

    return (r, g, b)


# Source: ttrss/include/colors.php:colorPalette (lines 285-332)
def color_palette(
    image_path: str, num_colors: int, granularity: int = 5
) -> list[str] | None:
    """Extract a color palette from an image file.

    Samples pixels at the given granularity, quantizes each channel to
    multiples of 0x33 (web-safe), and returns the most frequent colors.

    Args:
        image_path: Path to the image file. Pillow handles ICO natively.
        num_colors: Maximum number of colors to return.
        granularity: Step size for pixel sampling (minimum 1).

    Returns:
        A list of hex color strings (without ``#`` prefix, e.g. ``"FF0000"``),
        sorted by frequency (most common first), or ``None`` on failure.
    """
    granularity = max(1, abs(int(granularity)))
    colors: dict[str, int] = {}

    try:
        img = Image.open(image_path)
        img = img.convert("RGB")
    except Exception:
        return None

    width, height = img.size
    if width <= 0 or height <= 0:
        return None

    for x in range(0, width, granularity):
        for y in range(0, height, granularity):
            pixel = img.getpixel((x, y))
            red = round(round(pixel[0] / 0x33) * 0x33)
            green = round(round(pixel[1] / 0x33) * 0x33)
            blue = round(round(pixel[2] / 0x33) * 0x33)
            this_rgb = f"{red:02X}{green:02X}{blue:02X}"
            colors[this_rgb] = colors.get(this_rgb, 0) + 1

    # Sort by frequency descending
    sorted_colors = sorted(colors.keys(), key=lambda c: colors[c], reverse=True)
    return sorted_colors[:num_colors]


# Source: ttrss/include/colors.php:calculate_avg_color (lines 334-350)
def calculate_avg_color(icon_path: str) -> str:
    """Calculate a representative average color from an icon file.

    Extracts a 4-color palette and returns the first color that has
    sufficient saturation and brightness (filtering out near-black,
    near-white, and desaturated colors).

    Args:
        icon_path: Path to the icon/image file.

    Returns:
        A hex color string (e.g. ``"#ab12cd"``), or an empty string
        if no suitable color is found.
    """
    palette = color_palette(icon_path, 4, 4)

    if palette is not None:
        for p in palette:
            hsl = rgb_to_hsv(color_unpack(f"#{p}"))

            if (
                hsl[1] > 0.25
                and hsl[2] > 0.25
                and not (0 <= hsl[0] < 0.01 and hsl[1] < 0.01)
                and not (0 <= hsl[0] < 0.01 and hsl[2] > 0.99)
            ):
                return color_pack(hsv_to_rgb(hsl))

    return ""
