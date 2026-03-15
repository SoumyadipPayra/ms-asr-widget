"""
py2app build script for ASR Widget.

Usage (on macOS):
    python setup_mac.py py2app

Produces:  dist/ASR Widget.app
"""
from setuptools import setup

APP = ["src/asr_widget/main.py"]
DATA_FILES = [("", ["config.toml"])]

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns",
    "plist": {
        "CFBundleName": "ASR Widget",
        "CFBundleDisplayName": "ASR Widget",
        "CFBundleIdentifier": "com.asrwidget.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSMinimumSystemVersion": "12.0",
        "LSUIElement": True,  # Agent app — no dock icon
        "NSMicrophoneUsageDescription": (
            "ASR Widget needs microphone access to capture speech for transcription."
        ),
        "NSAppleEventsUsageDescription": (
            "ASR Widget needs accessibility access to type transcriptions "
            "at the cursor position."
        ),
    },
    "packages": [
        "asr_widget",
        "websockets",
        "pynput",
        "sounddevice",
    ],
    "includes": [
        "objc",
        "AppKit",
        "Quartz",
        "Foundation",
        "PyObjCTools",
        "PyObjCTools.AppHelper",
    ],
    "excludes": [
        "tkinter",
        "test",
        "unittest",
    ],
}

setup(
    name="ASR Widget",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
