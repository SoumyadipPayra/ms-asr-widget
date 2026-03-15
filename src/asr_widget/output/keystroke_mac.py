from __future__ import annotations

import logging
import subprocess
import threading

logger = logging.getLogger(__name__)

# AppleScript that pastes from the clipboard into the currently focused app.
_PBPASTE   = "/usr/bin/pbpaste"
_PBCOPY    = "/usr/bin/pbcopy"
_OSASCRIPT = "/usr/bin/osascript"
_PASTE_SCRIPT = 'tell application "System Events" to keystroke "v" using {command down}'


class KeystrokeInjector:
    """Injects text at the current cursor position on macOS.

    Uses a clipboard-swap strategy (pbcopy → Cmd+V via osascript) so it works
    without the app needing Accessibility permission.  The original clipboard
    content is restored asynchronously after a short delay.
    """

    def __init__(self) -> None:
        self._needs_space = False

    def type_text(self, text: str) -> None:
        if not text:
            return

        if self._needs_space:
            text = " " + text

        logger.warning("INJECTING text via clipboard: %r", text)

        # Save current clipboard so we can restore it.
        try:
            old = subprocess.run(
                [_PBPASTE], capture_output=True, timeout=2
            ).stdout  # bytes
        except Exception:
            old = b""

        # Place the transcript on the clipboard (pass as UTF-8 bytes).
        try:
            subprocess.run(
                [_PBCOPY], input=text.encode("utf-8"), timeout=2, check=True
            )
        except Exception:
            logger.error("pbcopy failed — transcript not injected", exc_info=True)
            return

        # Paste into the focused window via System Events.
        try:
            result = subprocess.run(
                [_OSASCRIPT, "-e", _PASTE_SCRIPT],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode != 0:
                logger.error("osascript paste failed (rc=%d): %s", result.returncode, result.stderr.strip())
            else:
                logger.warning("osascript paste OK")
        except Exception:
            logger.error("osascript paste exception", exc_info=True)

        self._needs_space = True

        # Restore the original clipboard after giving the paste time to land.
        def _restore() -> None:
            import time
            time.sleep(0.6)
            try:
                subprocess.run([_PBCOPY], input=old, timeout=2)
            except Exception:
                pass

        threading.Thread(target=_restore, daemon=True).start()

    def reset(self) -> None:
        self._needs_space = False
