from __future__ import annotations

import logging
import tkinter as tk

logger = logging.getLogger(__name__)


class StatusBarItem:
    """Lightweight status indicator.

    On Linux this is a simple label inside the floating widget's
    tooltip. The actual state is shown by the widget color itself.
    This class exists to keep the interface consistent and can be
    extended with system tray support (e.g., pystray) later.
    """

    def __init__(self) -> None:
        self._state = "idle"

    def create(self) -> None:
        logger.info("Status bar item ready (state shown via widget color)")

    def set_state(self, state: str) -> None:
        self._state = state
        logger.debug("Status: %s", state)
