from __future__ import annotations

import logging
from typing import Callable

from pynput import keyboard

from asr_widget.activation.base import ActivationSource

logger = logging.getLogger(__name__)


class HotkeyActivation(ActivationSource):
    """Activation via a global hotkey.

    Supports two modes:
      - "toggle": press once to start, press again to stop
      - "push_to_talk": hold to record, release to stop
    """

    def __init__(
        self,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
        combination: str = "<cmd>+<shift>+<space>",
        mode: str = "toggle",
    ) -> None:
        super().__init__(on_activate, on_deactivate)
        self._combination = combination
        self._mode = mode
        self._hotkey_listener: keyboard.GlobalHotKeys | None = None
        self._key_listener: keyboard.Listener | None = None
        # For push_to_talk: track which keys are currently pressed
        self._hotkey_keys = self._parse_combination(combination)
        self._pressed_keys: set = set()

    def start(self) -> None:
        logger.info("Registering hotkey: %s (mode=%s)", self._combination, self._mode)

        if self._mode == "push_to_talk":
            self._key_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self._key_listener.start()
        else:
            # Toggle mode uses GlobalHotKeys
            self._hotkey_listener = keyboard.GlobalHotKeys(
                {self._combination: self._on_hotkey}
            )
            self._hotkey_listener.start()

    def stop(self) -> None:
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._key_listener is not None:
            self._key_listener.stop()
            self._key_listener = None

    def _on_hotkey(self) -> None:
        """Called when the hotkey combo is pressed (toggle mode)."""
        logger.debug("Hotkey triggered (toggle)")
        self.toggle()

    def _on_key_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Track pressed keys for push-to-talk detection."""
        normalized = self._normalize_key(key)
        if normalized is not None:
            self._pressed_keys.add(normalized)
        if self._hotkey_keys.issubset(self._pressed_keys):
            self.activate()

    def _on_key_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Detect hotkey release for push-to-talk."""
        normalized = self._normalize_key(key)
        if normalized is not None:
            self._pressed_keys.discard(normalized)
        if not self._hotkey_keys.issubset(self._pressed_keys):
            self.deactivate()

    @staticmethod
    def _normalize_key(key: keyboard.Key | keyboard.KeyCode) -> str | None:
        if isinstance(key, keyboard.Key):
            return key.name
        if isinstance(key, keyboard.KeyCode):
            return key.char
        return None

    @staticmethod
    def _parse_combination(combo: str) -> set[str]:
        """Parse a pynput-style combo string into a set of key names."""
        keys = set()
        for part in combo.split("+"):
            part = part.strip().strip("<>")
            # Map common names
            mapping = {
                "cmd": "cmd",
                "ctrl": "ctrl",
                "alt": "alt",
                "shift": "shift",
                "space": "space",
            }
            keys.add(mapping.get(part.lower(), part.lower()))
        return keys
