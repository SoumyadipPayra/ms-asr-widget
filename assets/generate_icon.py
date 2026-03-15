#!/usr/bin/env python3
"""Generate the app icon as a PNG (convert to ICNS on macOS with iconutil).

Requires Pillow: pip install pillow

Usage:
    python assets/generate_icon.py          # creates assets/icon.png
    # Then on macOS, run: assets/png_to_icns.sh
"""

import math
import os

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def create_icon_png(size: int = 512) -> bytes:
    if HAS_PILLOW:
        return _create_pillow(size)
    return _create_fallback(size)


def _create_pillow(size: int) -> bytes:
    """High-quality icon: deep navy circle, glassy mic, soft glow ring."""
    import io

    # --- Background ---
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Outer soft glow (very subtle)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pad = size * 0.02
    gd.ellipse([pad, pad, size - pad, size - pad], fill=(100, 140, 255, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.04))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)

    # --- Main circle: deep navy / dark slate ---
    margin = int(size * 0.045)
    circle_box = [margin, margin, size - margin, size - margin]

    # Shadow layer
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sm = margin - int(size * 0.015)
    sd.ellipse(
        [sm + int(size * 0.015), sm + int(size * 0.025),
         size - sm - int(size * 0.015), size - sm + int(size * 0.005)],
        fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.03))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)

    # Main circle fill — dark navy
    draw.ellipse(circle_box, fill=(22, 24, 38, 255))

    # Subtle radial gradient overlay (lighter centre → darker edge)
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for step in range(30, 0, -1):
        frac = step / 30
        r_px = int((size / 2 - margin) * frac)
        cx, cy = size // 2, size // 2
        alpha = int(28 * (1 - frac))
        ImageDraw.Draw(gradient).ellipse(
            [cx - r_px, cy - r_px, cx + r_px, cy + r_px],
            fill=(80, 90, 160, alpha),
        )
    img = Image.alpha_composite(img, gradient)
    draw = ImageDraw.Draw(img)

    # Thin border ring — electric blue tint
    draw.ellipse(circle_box, outline=(80, 110, 240, 80), width=max(2, size // 128))

    # Inner highlight arc (top-left glass sheen)
    sheen_box = [
        int(size * 0.18), int(size * 0.14),
        int(size * 0.82), int(size * 0.58),
    ]
    draw.arc(sheen_box, start=210, end=330, fill=(255, 255, 255, 30),
             width=max(2, size // 80))

    # ── Microphone glyph ──────────────────────────────────────────────────
    cx, cy = size / 2, size / 2

    # Mic body dimensions
    body_w = size * 0.18
    body_h = size * 0.30
    body_rx = body_w * 0.5          # fully rounded ends
    body_top = cy - size * 0.20
    body_bot = cy + size * 0.10

    # Mic body: white rounded rectangle
    body_box = [cx - body_w / 2, body_top, cx + body_w / 2, body_bot]
    draw.rounded_rectangle(body_box, radius=body_rx, fill=(255, 255, 255, 235))

    # Thin highlight inside mic body (glass look)
    hi_box = [cx - body_w * 0.28, body_top + size * 0.015,
              cx - body_w * 0.08, body_bot - size * 0.04]
    draw.rounded_rectangle(hi_box, radius=body_rx * 0.4,
                            fill=(255, 255, 255, 70))

    # Mic arc (open bottom U-shape)
    arc_r = size * 0.20
    arc_thick = max(3, size // 60)
    arc_box = [cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r]
    draw.arc(arc_box, start=0, end=180, fill=(255, 255, 255, 220),
             width=arc_thick)

    # Stand (vertical line below arc)
    stand_x = cx
    stand_top = cy + arc_r
    stand_bot = cy + arc_r + size * 0.08
    stand_w = max(3, size // 80)
    draw.rectangle(
        [stand_x - stand_w / 2, stand_top,
         stand_x + stand_w / 2, stand_bot],
        fill=(255, 255, 255, 210),
    )

    # Base (horizontal bar)
    base_w = size * 0.22
    base_h = max(3, size // 80)
    base_y = stand_bot
    draw.rounded_rectangle(
        [cx - base_w / 2, base_y - base_h / 2,
         cx + base_w / 2, base_y + base_h / 2],
        radius=base_h / 2,
        fill=(255, 255, 255, 210),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Fallback: pure-stdlib minimal encoder (no Pillow) ─────────────────────

def _create_fallback(size: int) -> bytes:
    import struct, zlib
    cx, cy = size / 2, size / 2
    radius = size / 2 - 8
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            dx, dy = x - cx, y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d <= radius - 4:
                t = d / (radius - 4)
                r = int(22 + 20 * (1 - t))
                g = int(24 + 20 * (1 - t))
                b = int(38 + 30 * (1 - t))
                row.extend([r, g, b, 255])
            elif d <= radius:
                row.extend([80, 110, 240, 160])
            else:
                row.extend([0, 0, 0, 0])
        rows.append(bytes(row))

    def chunk(ct, data):
        c = ct + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "icon.png")
    png = create_icon_png(512)
    with open(out, "wb") as f:
        f.write(png)
    print(f"Written {len(png)} bytes to {out}")
