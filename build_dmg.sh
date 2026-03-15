#!/usr/bin/env bash
# Build ASR Widget.app and package it into a DMG.
#
# Usage:  ./build_dmg.sh
# Requires: macOS, Python 3.11+, uv (or pip)
#
# Produces: dist/ASRWidget.dmg
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="ASR Widget"
DMG_NAME="ASRWidget"
VERSION="0.1.0"

echo "=== ASR Widget Build ==="
echo "Version: $VERSION"
echo ""

# --- 1. Set up venv -------------------------------------------------------
echo "--- Setting up build environment ---"
if command -v uv &>/dev/null; then
    uv venv .venv-build 2>/dev/null || true
    source .venv-build/bin/activate
    uv pip install -e ".[mac]" py2app 2>/dev/null || \
    uv pip install \
        pyobjc-framework-Cocoa \
        pyobjc-framework-Quartz \
        websockets \
        sounddevice \
        pynput \
        py2app
else
    python3 -m venv .venv-build 2>/dev/null || true
    source .venv-build/bin/activate
    pip install \
        pyobjc-framework-Cocoa \
        pyobjc-framework-Quartz \
        websockets \
        sounddevice \
        pynput \
        py2app
fi

# --- 2. Generate icon ------------------------------------------------------
echo ""
echo "--- Generating app icon ---"
python assets/generate_icon.py
if command -v iconutil &>/dev/null; then
    bash assets/png_to_icns.sh
else
    echo "WARNING: iconutil not found (not on macOS?). Using placeholder icon."
    # py2app will work without an icon, just won't look as nice
fi

# --- 3. Build .app ---------------------------------------------------------
echo ""
echo "--- Building ${APP_NAME}.app ---"
python setup_mac.py py2app --dist-dir dist

if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "ERROR: Build failed — dist/${APP_NAME}.app not found"
    exit 1
fi

echo "Built: dist/${APP_NAME}.app"

# --- 4. Copy config into app bundle ----------------------------------------
cp config.toml "dist/${APP_NAME}.app/Contents/Resources/"

# --- 5. Create DMG ---------------------------------------------------------
echo ""
echo "--- Creating DMG ---"

DMG_DIR="dist/dmg-staging"
DMG_PATH="dist/${DMG_NAME}-${VERSION}.dmg"

rm -rf "$DMG_DIR" "$DMG_PATH"
mkdir -p "$DMG_DIR"

cp -R "dist/${APP_NAME}.app" "$DMG_DIR/"

# Create a symlink to /Applications for drag-to-install
ln -s /Applications "$DMG_DIR/Applications"

# Create DMG
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

rm -rf "$DMG_DIR"

echo ""
echo "=== Build complete ==="
echo "  App: dist/${APP_NAME}.app"
echo "  DMG: ${DMG_PATH}"
echo ""
echo "To install: open the DMG and drag '$APP_NAME' to Applications."
echo ""
echo "First run permissions needed:"
echo "  1. Microphone: System Settings > Privacy & Security > Microphone"
echo "  2. Accessibility: System Settings > Privacy & Security > Accessibility"
