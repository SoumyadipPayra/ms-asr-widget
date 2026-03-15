from __future__ import annotations

import json
import logging
import os
import platform
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_URL = "ws://localhost:8765"
DEFAULT_HOTKEY = "<cmd>+<shift>+<space>" if platform.system() == "Darwin" else "<ctrl>+<shift>+<space>"


def needs_setup() -> bool:
    """Check if first-run setup is needed."""
    marker = _marker_path()
    return not marker.exists()


def _marker_path() -> Path:
    """Path to the setup-complete marker file."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "asr-widget" / ".setup_done"


def _config_dir() -> Path:
    marker = _marker_path()
    return marker.parent


def run_setup_wizard() -> dict | None:
    """Run the first-launch setup wizard.

    Returns a dict of settings if the user completes setup, or None if cancelled.
    """
    result = {}
    cancelled = [False]

    root = tk.Tk()
    root.title("ASR Widget — Setup")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # Center on screen
    w, h = 480, 420
    sx = root.winfo_screenwidth() // 2 - w // 2
    sy = root.winfo_screenheight() // 2 - h // 2
    root.geometry(f"{w}x{h}+{sx}+{sy}")

    # Style
    style = ttk.Style()
    style.configure("Title.TLabel", font=("", 16, "bold"))
    style.configure("Section.TLabel", font=("", 11, "bold"))

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    # Title
    ttk.Label(frame, text="Welcome to ASR Widget", style="Title.TLabel").pack(pady=(0, 5))
    ttk.Label(frame, text="Let's configure your speech-to-text setup.").pack(pady=(0, 15))

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=5)

    # --- Server endpoint ---
    ttk.Label(frame, text="Server Endpoint", style="Section.TLabel").pack(anchor="w", pady=(10, 2))
    ttk.Label(frame, text="WebSocket URL of the ASR gateway:").pack(anchor="w")
    url_var = tk.StringVar(value=DEFAULT_URL)
    url_entry = ttk.Entry(frame, textvariable=url_var, width=50)
    url_entry.pack(anchor="w", pady=(2, 0))
    url_entry.focus_set()

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

    # --- Hotkey ---
    ttk.Label(frame, text="Hotkey", style="Section.TLabel").pack(anchor="w", pady=(5, 2))
    hk_label = "Cmd+Shift+Space" if platform.system() == "Darwin" else "Ctrl+Shift+Space"
    ttk.Label(frame, text=f"Global shortcut to toggle recording (default: {hk_label}):").pack(anchor="w")
    hotkey_var = tk.StringVar(value=DEFAULT_HOTKEY)
    ttk.Entry(frame, textvariable=hotkey_var, width=30).pack(anchor="w", pady=(2, 0))

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

    # --- Permissions note ---
    ttk.Label(frame, text="Permissions", style="Section.TLabel").pack(anchor="w", pady=(5, 2))

    if platform.system() == "Darwin":
        perm_text = (
            "On first use macOS will prompt for:\n"
            "  \u2022 Microphone access (for audio capture)\n"
            "  \u2022 Accessibility (for typing at cursor)\n"
            "Grant both in System Settings > Privacy & Security."
        )
    elif platform.system() == "Windows":
        perm_text = (
            "Windows may show these prompts:\n"
            "  \u2022 Microphone access (Settings > Privacy > Microphone)\n"
            "  \u2022 Firewall — allow network access for the ASR server\n"
            "No admin privileges are required."
        )
    else:
        perm_text = (
            "Ensure the following are available:\n"
            "  \u2022 Microphone access (PulseAudio/PipeWire)\n"
            "  \u2022 X11/XWayland for keystroke injection\n"
            "  \u2022 xdotool installed (fallback typing)"
        )
    ttk.Label(frame, text=perm_text, justify="left").pack(anchor="w")

    # --- Buttons ---
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill="x", pady=(15, 0))

    def on_cancel():
        cancelled[0] = True
        root.destroy()

    def on_finish():
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter the gateway server URL.")
            return

        result["gateway_url"] = url
        result["hotkey"] = hotkey_var.get().strip() or DEFAULT_HOTKEY
        root.destroy()

    ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="left")
    ttk.Button(btn_frame, text="Start", command=on_finish).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()

    if cancelled[0]:
        return None

    # Write config and marker
    _save_config(result)
    return result


def _save_config(settings: dict) -> None:
    """Write the user's settings to config.toml and mark setup as done."""
    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.toml"
    hotkey = settings.get("hotkey", DEFAULT_HOTKEY)

    toml_content = f"""[gateway]
url = "{settings['gateway_url']}"

[audio]
sample_rate = 16000
chunk_duration_ms = 100

[hotkey]
combination = "{hotkey}"
mode = "toggle"

[ui]
size = 44
opacity = 0.9
"""
    config_path.write_text(toml_content)

    # Write marker
    marker = _marker_path()
    marker.write_text("setup_complete\n")

    logger.info("Config saved to %s", config_path)
