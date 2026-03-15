from __future__ import annotations

import logging
import platform
import time

logger = logging.getLogger(__name__)


class KeystrokeInjector:
    """Injects text at the current cursor position.

    Uses pynput on all platforms. Falls back to xdotool on Linux
    if pynput keyboard control isn't available.

    On macOS, requires Accessibility permission.
    On Linux, requires X11 (Wayland support via xdotool).
    """

    def __init__(self, inter_char_delay: float = 0.002) -> None:
        self._inter_char_delay = inter_char_delay
        self._needs_space = False
        self._controller = None
        self._use_xdotool = False
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            from pynput.keyboard import Controller
            self._controller = Controller()
            # Quick test — on some Linux setups this may fail
            logger.info("Keystroke injector: using pynput")
        except Exception:
            if platform.system() == "Linux":
                import shutil
                if shutil.which("xdotool"):
                    self._use_xdotool = True
                    logger.info("Keystroke injector: using xdotool fallback")
                else:
                    logger.error("No keystroke backend available. Install xdotool.")
            else:
                logger.error("pynput keyboard controller not available")

    def type_text(self, text: str) -> None:
        """Type the given text at the current cursor position."""
        if not text:
            return

        if self._needs_space:
            text = " " + text

        logger.debug("Typing %d characters", len(text))

        if self._use_xdotool:
            self._type_xdotool(text)
        elif self._controller is not None:
            self._type_pynput(text)
        else:
            logger.warning("No keystroke backend — transcript not typed: %s", text)

        self._needs_space = True

    def reset(self) -> None:
        """Reset state (no leading space on next type)."""
        self._needs_space = False

    def _type_pynput(self, text: str) -> None:
        for char in text:
            self._controller.type(char)
            if self._inter_char_delay > 0:
                time.sleep(self._inter_char_delay)

    def _type_xdotool(self, text: str) -> None:
        import subprocess
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--", text],
            check=False,
        )
