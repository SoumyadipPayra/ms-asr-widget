from __future__ import annotations

import logging
from typing import Callable

import objc
from AppKit import (
    NSApplication,
    NSMenu,
    NSMenuItem,
    NSObject,
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


class _MenuTarget(NSObject):
    """Thin ObjC shim so a Python callable can serve as an NSMenuItem target."""

    def initWithCallback_(self, callback: Callable) -> "_MenuTarget":
        self = objc.super(_MenuTarget, self).init()
        self._callback = callback
        return self

    def action_(self, sender) -> None:
        self._callback()


class StatusBarItem:
    """macOS NSStatusItem in the menu bar."""

    def __init__(self, on_quit=None, on_preferences: Callable | None = None) -> None:
        self._on_quit = on_quit
        self._on_preferences = on_preferences
        self._status_item = None
        self._state = "idle"
        self._state_menu_item = None
        self._prefs_target: _MenuTarget | None = None

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

        if self._on_preferences is not None:
            self._prefs_target = _MenuTarget.alloc().initWithCallback_(self._on_preferences)
            prefs_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Preferences\u2026", "action:", ","
            )
            prefs_item.setTarget_(self._prefs_target)
            menu.addItem_(prefs_item)
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
