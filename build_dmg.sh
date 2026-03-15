#!/usr/bin/env bash
# Build ASR Widget.app and package it into a DMG.
#
# Usage:  ./build_dmg.sh
# Requires: macOS, Python 3.9+
#
# Produces: dist/ASRWidget-<VERSION>.dmg
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="ASR Widget"
DMG_NAME="ASRWidget"
VERSION="0.1.0"

echo "=== ASR Widget Build ==="
echo "Version: $VERSION"
echo ""

# --- 1. Set up venv -----------------------------------------------------------
echo "--- Setting up build environment ---"

# Wipe any stale build venv to ensure a clean state
rm -rf .venv-build

if command -v uv &>/dev/null; then
    uv venv .venv-build
    source .venv-build/bin/activate
    uv pip install --upgrade pip
    uv pip install \
        "pyobjc-framework-Cocoa>=10.0" \
        "pyobjc-framework-Quartz>=10.0" \
        "pyobjc-framework-ApplicationServices>=10.0" \
        "websockets>=12.0" \
        "sounddevice>=0.4.6" \
        "numpy>=1.24.0" \
        "pynput>=1.7.6" \
        "tomli>=2.0.0" \
        "pillow>=9.0" \
        "py2app>=0.28"
    uv pip install -e .
else
    python3 -m venv .venv-build
    source .venv-build/bin/activate
    pip install --upgrade pip
    pip install \
        "pyobjc-framework-Cocoa>=10.0" \
        "pyobjc-framework-Quartz>=10.0" \
        "pyobjc-framework-ApplicationServices>=10.0" \
        "websockets>=12.0" \
        "sounddevice>=0.4.6" \
        "numpy>=1.24.0" \
        "pynput>=1.7.6" \
        "tomli>=2.0.0" \
        "pillow>=9.0" \
        "py2app>=0.28"
    pip install -e .
fi

# --- 2. Generate icon ---------------------------------------------------------
echo ""
echo "--- Generating app icon ---"
python assets/generate_icon.py
if command -v iconutil &>/dev/null; then
    bash assets/png_to_icns.sh
else
    echo "WARNING: iconutil not found — skipping ICNS generation."
fi

# --- 3. Clean previous build output -------------------------------------------
echo ""
echo "--- Cleaning previous build ---"
rm -rf build dist

# --- 4. Build .app ------------------------------------------------------------
echo ""
echo "--- Building ${APP_NAME}.app ---"
python setup_mac.py py2app --dist-dir dist

if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "ERROR: Build failed — dist/${APP_NAME}.app not found"
    exit 1
fi

echo "Built: dist/${APP_NAME}.app"

# --- 5. Embed bundled config --------------------------------------------------
cp config.toml "dist/${APP_NAME}.app/Contents/Resources/"

# --- 5b. Fix sounddevice portaudio path ----------------------------------------
# sounddevice.pyc inside python39.zip resolves _sounddevice_data relative to the
# zip path, which fails.  Remove it from the zip so Python falls through to the
# uncompressed copy in lib/python3.9/ where _sounddevice_data is a sibling dir.
ZIP="dist/${APP_NAME}.app/Contents/Resources/lib/python39.zip"
if [ -f "$ZIP" ]; then
    echo "--- Fixing sounddevice in zip ---"
    zip -d "$ZIP" "sounddevice.pyc" 2>/dev/null || true
    echo "Removed sounddevice.pyc from zip"
fi

# --- 6. Create DMG ------------------------------------------------------------
echo ""
echo "--- Creating DMG ---"

DMG_DIR="dist/dmg-staging"
DMG_PATH="dist/${DMG_NAME}-${VERSION}.dmg"

rm -rf "$DMG_DIR" "$DMG_PATH"
mkdir -p "$DMG_DIR"

cp -R "dist/${APP_NAME}.app" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"

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
echo "To install:"
echo "  1. Open ${DMG_PATH}"
echo "  2. Drag '${APP_NAME}' to Applications"
echo "  3. Launch — a setup dialog will ask for your gateway URL on first run"
echo ""
echo "Permissions required on first launch:"
echo "  • Microphone:    System Settings > Privacy & Security > Microphone"
echo "  • Automation:    System Settings > Privacy & Security > Automation  (for text injection)"
echo "  • Accessibility: System Settings > Privacy & Security > Accessibility (for hotkey)"
