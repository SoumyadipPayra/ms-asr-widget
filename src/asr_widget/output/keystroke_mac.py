from __future__ import annotations

import logging
import time

import Quartz

logger = logging.getLogger(__name__)


class KeystrokeInjector:
    """Injects text at the current cursor position using macOS CGEvent API.

    Types into whatever application currently has keyboard focus.
    Requires Accessibility permission in System Preferences >
    Privacy & Security > Accessibility.
    """

    def __init__(self, inter_char_delay: float = 0.001) -> None:
        self._inter_char_delay = inter_char_delay
        self._needs_space = False

    def type_text(self, text: str) -> None:
        if not text:
            return

        if self._needs_space:
            text = " " + text

        logger.debug("Typing %d characters", len(text))

        for char in text:
            self._type_char(char)
            if self._inter_char_delay > 0:
                time.sleep(self._inter_char_delay)

        self._needs_space = True

    def reset(self) -> None:
        self._needs_space = False

    @staticmethod
    def _type_char(char: str) -> None:
        event_down = Quartz.CGEventCreateKeyboardEvent(None, 0, True)
        event_up = Quartz.CGEventCreateKeyboardEvent(None, 0, False)
        Quartz.CGEventKeyboardSetUnicodeString(event_down, 1, char)
        Quartz.CGEventKeyboardSetUnicodeString(event_up, 1, char)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
