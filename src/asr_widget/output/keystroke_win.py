from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import time

logger = logging.getLogger(__name__)

# --- Win32 SendInput structures ---

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("_input", _INPUT_UNION),
    ]


_SendInput = ctypes.windll.user32.SendInput
_SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
_SendInput.restype = ctypes.c_uint


class KeystrokeInjector:
    """Injects text at the current cursor position using Win32 SendInput.

    Types Unicode characters directly into whatever window has focus.
    No special permissions required on Windows.
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
            self._send_unicode_char(char)
            if self._inter_char_delay > 0:
                time.sleep(self._inter_char_delay)

        self._needs_space = True

    def reset(self) -> None:
        self._needs_space = False

    @staticmethod
    def _send_unicode_char(char: str) -> None:
        """Send a single Unicode character via SendInput."""
        code = ord(char)

        # For characters in the Basic Multilingual Plane, send one pair.
        # For supplementary characters (emoji etc.), send as surrogate pair.
        if code > 0xFFFF:
            code -= 0x10000
            high = 0xD800 + (code >> 10)
            low = 0xDC00 + (code & 0x3FF)
            surrogates = [high, low]
        else:
            surrogates = [code]

        inputs = []
        for scan in surrogates:
            # Key down
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki.wVk = 0
            inp_down.ki.wScan = scan
            inp_down.ki.dwFlags = KEYEVENTF_UNICODE
            inp_down.ki.time = 0
            inp_down.ki.dwExtraInfo = None
            inputs.append(inp_down)

            # Key up
            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki.wVk = 0
            inp_up.ki.wScan = scan
            inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            inp_up.ki.time = 0
            inp_up.ki.dwExtraInfo = None
            inputs.append(inp_up)

        arr = (INPUT * len(inputs))(*inputs)
        _SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
