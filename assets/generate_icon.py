#!/usr/bin/env python3
"""Generate the app icon as a PNG (convert to ICNS on macOS with iconutil).

Creates a dark circle with a microphone glyph — matches the widget look.

Usage:
    python assets/generate_icon.py          # creates assets/icon.png
    # Then on macOS, run: assets/png_to_icns.sh
"""

import struct
import zlib
import os


def create_icon_png(size: int = 512) -> bytes:
    """Generate a simple icon PNG programmatically (no PIL needed)."""
    # We draw a filled circle on a transparent background
    pixels = []
    cx, cy = size / 2, size / 2
    radius = size / 2 - 8
    inner_radius = radius - 4

    for y in range(size):
        row = []
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= inner_radius:
                # Inside circle: dark gray #383840
                r, g, b, a = 56, 56, 64, 255
                # Add subtle gradient
                t = dist / inner_radius
                r = int(56 + (72 - 56) * (1 - t))
                g = int(56 + (72 - 56) * (1 - t))
                b = int(64 + (80 - 64) * (1 - t))
            elif dist <= radius:
                # Border: lighter edge
                r, g, b, a = 100, 100, 110, 200
            else:
                # Outside: transparent
                r, g, b, a = 0, 0, 0, 0

            row.extend([r, g, b, a])
        pixels.append(bytes(row))

    # Draw a simple mic shape (vertical bar + base) in white
    # Mic body: vertical rounded rectangle in center
    mic_w = size * 0.12
    mic_h = size * 0.28
    mic_cx = cx
    mic_top = cy - mic_h * 0.6
    mic_bot = cy + mic_h * 0.2
    mic_base_y = cy + mic_h * 0.5
    mic_stand_top = mic_bot + 4
    mic_stand_bot = mic_base_y
    mic_base_w = size * 0.16

    pixels2 = []
    for y in range(size):
        row = list(pixels[y])
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > inner_radius:
                continue

            idx = x * 4
            px_r, px_g, px_b, px_a = row[idx], row[idx+1], row[idx+2], row[idx+3]

            # Mic body (rounded rect)
            if abs(x - mic_cx) <= mic_w / 2 and mic_top <= y <= mic_bot:
                row[idx] = 240
                row[idx+1] = 240
                row[idx+2] = 245
                row[idx+3] = 230
            # Mic stand (thin vertical line)
            elif abs(x - mic_cx) <= 3 and mic_stand_top <= y <= mic_stand_bot:
                row[idx] = 240
                row[idx+1] = 240
                row[idx+2] = 245
                row[idx+3] = 200
            # Mic base (horizontal line)
            elif abs(x - mic_cx) <= mic_base_w / 2 and abs(y - mic_base_y) <= 3:
                row[idx] = 240
                row[idx+1] = 240
                row[idx+2] = 245
                row[idx+3] = 200
            # Mic arc (curved lines around body)
            elif mic_top + mic_h * 0.15 <= y <= mic_bot + 6:
                arc_r = mic_w * 0.85
                arc_dist = abs(abs(x - mic_cx) - arc_r)
                if arc_dist <= 2.5:
                    row[idx] = 220
                    row[idx+1] = 220
                    row[idx+2] = 230
                    row[idx+3] = 150

        pixels2.append(bytes(row))

    return _encode_png(size, size, pixels2)


def _encode_png(width: int, height: int, rows: list[bytes]) -> bytes:
    """Minimal PNG encoder for RGBA data."""
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))

    raw = b""
    for row in rows:
        raw += b"\x00" + row  # filter byte 0 (None) per row

    idat = chunk(b"IDAT", zlib.compress(raw, 9))
    iend = chunk(b"IEND", b"")

    return header + ihdr + idat + iend


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "icon.png")
    png = create_icon_png(512)
    with open(out, "wb") as f:
        f.write(png)
    print(f"Written {len(png)} bytes to {out}")
