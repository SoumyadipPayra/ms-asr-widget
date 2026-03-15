<#
.SYNOPSIS
    Build ASR Widget into a Windows installer (.exe).

.DESCRIPTION
    1. Creates a venv and installs dependencies
    2. Generates the app icon (.ico)
    3. Bundles with PyInstaller into a single-folder dist
    4. Packages with Inno Setup into an installer .exe
       (or produces a standalone folder if Inno Setup isn't installed)

.USAGE
    .\build_exe.ps1

.OUTPUTS
    dist\ASRWidgetSetup-0.1.0.exe   (if Inno Setup is available)
    dist\ASRWidget\ASRWidget.exe     (always)
#>

$ErrorActionPreference = "Stop"
$Version = "0.1.0"
$AppName = "ASR Widget"
$ExeName = "ASRWidget"

Write-Host "=== $AppName Windows Build ===" -ForegroundColor Cyan
Write-Host "Version: $Version"
Write-Host ""

# --- 1. Venv + deps -------------------------------------------------------
Write-Host "--- Setting up build environment ---" -ForegroundColor Yellow

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv venv .venv-build 2>$null
    & .\.venv-build\Scripts\activate.ps1
    uv pip install websockets sounddevice pynput pyinstaller Pillow
} else {
    python -m venv .venv-build 2>$null
    & .\.venv-build\Scripts\activate.ps1
    pip install websockets sounddevice pynput pyinstaller Pillow
}

# --- 2. Generate icon ------------------------------------------------------
Write-Host ""
Write-Host "--- Generating app icon ---" -ForegroundColor Yellow

python assets\generate_icon.py

# Convert PNG to ICO using Pillow
python -c @"
from PIL import Image
img = Image.open('assets/icon.png')
img.save('assets/icon.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Created assets/icon.ico')
"@

# --- 3. PyInstaller --------------------------------------------------------
Write-Host ""
Write-Host "--- Building with PyInstaller ---" -ForegroundColor Yellow

$specContent = @"
# -*- mode: python ; coding: utf-8 -*-
import os, sys

block_cipher = None

a = Analysis(
    ['src/asr_widget/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('config.toml', '.')],
    hiddenimports=[
        'asr_widget.ui.widget_win',
        'asr_widget.ui.statusbar_win',
        'asr_widget.output.keystroke_win',
        'asr_widget.activation.hotkey',
        'asr_widget.activation.click',
        'asr_widget.activation.wakeword',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['test', 'unittest', 'tkinter.test'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='$ExeName',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='$ExeName',
)
"@

$specContent | Out-File -Encoding utf8 "$ExeName.spec"

pyinstaller "$ExeName.spec" --distpath dist --workpath build --noconfirm

if (-not (Test-Path "dist\$ExeName\$ExeName.exe")) {
    Write-Host "ERROR: PyInstaller build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Built: dist\$ExeName\$ExeName.exe" -ForegroundColor Green

# --- 4. Inno Setup (optional) ----------------------------------------------
$InnoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $InnoPath)) {
    # Try common alternative
    $InnoPath = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
}

if ($InnoPath) {
    Write-Host ""
    Write-Host "--- Creating installer with Inno Setup ---" -ForegroundColor Yellow

    # Inno Setup script is generated alongside
    & $InnoPath "installer.iss"

    Write-Host ""
    Write-Host "=== Build complete ===" -ForegroundColor Green
    Write-Host "  Installer: dist\${ExeName}Setup-${Version}.exe"
} else {
    Write-Host ""
    Write-Host "=== Build complete (no Inno Setup) ===" -ForegroundColor Green
    Write-Host "  Inno Setup not found — skipping installer creation."
    Write-Host "  Standalone folder: dist\$ExeName\"
    Write-Host "  Run directly:      dist\$ExeName\$ExeName.exe"
    Write-Host ""
    Write-Host "  To create an installer, install Inno Setup 6 and re-run."
}

Write-Host ""
Write-Host "  Portable .zip: compress dist\$ExeName\ for distribution"
