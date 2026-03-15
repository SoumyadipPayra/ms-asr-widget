#!/usr/bin/env bash
# Convert icon.png to icon.icns (macOS only, uses iconutil)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ICONSET="$SCRIPT_DIR/icon.iconset"

mkdir -p "$ICONSET"

# Generate all required sizes from the 512x512 source
for size in 16 32 64 128 256 512; do
    sips -z $size $size "$SCRIPT_DIR/icon.png" --out "$ICONSET/icon_${size}x${size}.png" 2>/dev/null
    double=$((size * 2))
    if [ $double -le 512 ]; then
        sips -z $double $double "$SCRIPT_DIR/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" 2>/dev/null
    fi
done

iconutil -c icns "$ICONSET" -o "$SCRIPT_DIR/icon.icns"
rm -rf "$ICONSET"
echo "Created $SCRIPT_DIR/icon.icns"
