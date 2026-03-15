from __future__ import annotations

import logging

from AppKit import (
    NSApplication,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)

logger = logging.getLogger(__name__)

STATE_ICONS = {
    "idle": "\U0001F3A4",       # microphone
    "listening": "\U0001F534",  # red circle
    "processing": "\U0001F7E1", # yellow circle
    "error": "\U0001F6D1",      # stop sign
}


class StatusBarItem:
    """macOS NSStatusItem in the menu bar."""

    def __init__(self, on_quit=None) -> None:
        self._on_quit = on_quit
        self._status_item = None
        self._state = "idle"
        self._state_menu_item = None

    def create(self) -> None:
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.setTitle_(STATE_ICONS["idle"])

        menu = NSMenu.alloc().init()

        state_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Status: Idle", None, ""
        )
        state_item.setEnabled_(False)
        menu.addItem_(state_item)
        self._state_menu_item = state_item

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "terminate:", "q"
        )
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)
        logger.info("Status bar item created")

    def set_state(self, state: str) -> None:
        self._state = state
        if self._status_item is not None:
            icon = STATE_ICONS.get(state, STATE_ICONS["idle"])
            self._status_item.setTitle_(icon)
        if self._state_menu_item is not None:
            self._state_menu_item.setTitle_(f"Status: {state.capitalize()}")
