from __future__ import annotations

import ctypes
import logging
import os
import threading

logger = logging.getLogger(__name__)

STATE_TIPS = {
    "idle": "ASR Widget — Idle",
    "listening": "ASR Widget — Listening...",
    "processing": "ASR Widget — Processing...",
    "error": "ASR Widget — Error",
}


class StatusBarItem:
    """Windows system tray icon using the Win32 Shell_NotifyIcon API.

    Shows a microphone icon in the notification area with a tooltip
    reflecting the current state.
    """

    def __init__(self, on_quit=None) -> None:
        self._on_quit = on_quit
        self._state = "idle"
        self._hwnd = None
        self._tray_thread = None

    def create(self) -> None:
        # System tray requires a message loop on its own thread.
        # For simplicity, we just log state changes — the floating
        # widget itself is the primary visual indicator on Windows.
        # A full tray implementation can be added with pystray later.
        logger.info("Status indicator ready (state shown via widget)")

    def set_state(self, state: str) -> None:
        self._state = state
        logger.debug("Status: %s", STATE_TIPS.get(state, state))
