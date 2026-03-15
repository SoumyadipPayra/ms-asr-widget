from __future__ import annotations

import ctypes
import logging
import math
import tkinter as tk
from typing import Callable

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "idle": "#383840",
    "listening": "#26b832",
    "processing": "#e8b010",
    "error": "#d83020",
}

STATE_GLOW = {
    "idle": None,
    "listening": "#30e840",
    "processing": "#f0c830",
    "error": "#f04030",
}

RING_COUNT = 3
RING_DURATION_MS = 1800  # Full cycle in ms
FPS = 30


class FloatingWidget:
    """Floating always-on-top widget for Windows.

    Uses tkinter with Win32 transparency and layered-window support.
    Draws expanding pulse rings when active.
    """

    def __init__(
        self,
        size: int = 44,
        opacity: float = 0.9,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        self._circle_size = size
        # Window is larger to accommodate pulse rings
        self._size = size * 3
        self._opacity = opacity
        self._on_click = on_click
        self._state = "idle"
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._circle_id: int | None = None
        self._text_id: int | None = None
        self._ring_ids: list[int] = []
        self._anim_phase: float = 0.0
        self._anim_after_id: str | None = None

    def create(self, root: tk.Tk) -> None:
        self._root = root
        root.title("ASR Widget")
        root.overrideredirect(True)
        root.attributes("-topmost", True)

        # Windows: transparent background via -transparentcolor
        bg = "#010101"  # Near-black used as transparency key
        root.configure(bg=bg)
        root.attributes("-transparentcolor", bg)
        root.attributes("-alpha", self._opacity)

        # Remove from taskbar using Win32 tool window style
        root.update_idletasks()
        try:
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # Re-show to apply
            root.withdraw()
            root.after(10, root.deiconify)
        except Exception:
            logger.debug("Could not set tool-window style", exc_info=True)

        # Position bottom-right
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = screen_w - self._size - 20
        y = screen_h - self._size - 60
        root.geometry(f"{self._size}x{self._size}+{x}+{y}")

        self._canvas = tk.Canvas(
            root,
            width=self._size,
            height=self._size,
            bg=bg,
            highlightthickness=0,
        )
        self._canvas.pack()

        # Pre-create ring ovals (hidden initially)
        cx, cy = self._size // 2, self._size // 2
        for _ in range(RING_COUNT):
            rid = self._canvas.create_oval(
                cx, cy, cx, cy,
                outline="", width=1.5, state="hidden",
            )
            self._ring_ids.append(rid)

        # Main circle
        offset = (self._size - self._circle_size) // 2
        pad = 2
        self._circle_id = self._canvas.create_oval(
            offset + pad, offset + pad,
            offset + self._circle_size - pad,
            offset + self._circle_size - pad,
            fill=STATE_COLORS["idle"],
            outline="#555560",
            width=2,
        )
        self._text_id = self._canvas.create_text(
            self._size // 2,
            self._size // 2,
            text="\U0001f3a4",
            font=("Segoe UI Emoji", int(self._circle_size * 0.3)),
            fill="white",
        )

        # Events
        self._canvas.tag_bind(self._circle_id, "<Button-1>", self._handle_click)
        self._canvas.tag_bind(self._text_id, "<Button-1>", self._handle_click)

        # Drag
        self._drag_data = {"x": 0, "y": 0}
        self._canvas.tag_bind(self._circle_id, "<ButtonPress-1>", self._drag_start, add="+")
        self._canvas.tag_bind(self._circle_id, "<B1-Motion>", self._drag_move)
        self._canvas.tag_bind(self._text_id, "<ButtonPress-1>", self._drag_start, add="+")
        self._canvas.tag_bind(self._text_id, "<B1-Motion>", self._drag_move)

        logger.info("Floating widget created at (%d, %d)", x, y)

    def set_state(self, state: str) -> None:
        self._state = state
        if self._root is not None:
            self._root.after(0, self._apply_state, state)

    def _apply_state(self, state: str) -> None:
        if self._canvas is None:
            return

        fill = STATE_COLORS.get(state, STATE_COLORS["idle"])
        self._canvas.itemconfig(self._circle_id, fill=fill)

        icon = "\U0001f534" if state == "listening" else "\U0001f3a4"
        self._canvas.itemconfig(self._text_id, text=icon)

        # Pulse animation
        if state in ("listening", "processing"):
            self._start_pulse()
        else:
            self._stop_pulse()

    # --- Pulse animation ---

    def _start_pulse(self) -> None:
        if self._anim_after_id is not None:
            return
        self._anim_phase = 0.0
        for rid in self._ring_ids:
            self._canvas.itemconfig(rid, state="normal")
        self._tick_pulse()

    def _stop_pulse(self) -> None:
        if self._anim_after_id is not None:
            self._root.after_cancel(self._anim_after_id)
            self._anim_after_id = None
        for rid in self._ring_ids:
            self._canvas.itemconfig(rid, state="hidden")

    def _tick_pulse(self) -> None:
        if self._canvas is None:
            return

        cx, cy = self._size / 2, self._size / 2
        max_r = self._size / 2 - 2
        min_r = self._circle_size / 2 + 2
        glow_color = STATE_GLOW.get(self._state) or STATE_GLOW["listening"]

        for i, rid in enumerate(self._ring_ids):
            ring_phase = (self._anim_phase + i / RING_COUNT) % 1.0
            radius = min_r + (max_r - min_r) * ring_phase
            alpha = 1.0 - ring_phase

            # tkinter can't do true alpha on canvas items, so we
            # interpolate the color toward the transparent-key color
            r_hex = glow_color.lstrip("#")
            cr = int(r_hex[0:2], 16)
            cg = int(r_hex[2:4], 16)
            cb = int(r_hex[4:6], 16)
            # Fade toward near-black (#010101, the transparency key)
            fr = max(1, int(cr * alpha + 1 * (1 - alpha)))
            fg = max(1, int(cg * alpha + 1 * (1 - alpha)))
            fb = max(1, int(cb * alpha + 1 * (1 - alpha)))
            faded = f"#{fr:02x}{fg:02x}{fb:02x}"
            # Avoid exact match with the transparency key
            if faded == "#010101":
                faded = "#020202"

            self._canvas.coords(
                rid,
                cx - radius, cy - radius,
                cx + radius, cy + radius,
            )
            w = 2.0 * (1.0 - ring_phase) + 0.5
            self._canvas.itemconfig(rid, outline=faded, width=w)

        self._anim_phase = (self._anim_phase + 1.0 / (FPS * RING_DURATION_MS / 1000)) % 1.0
        self._anim_after_id = self._root.after(1000 // FPS, self._tick_pulse)

    # --- Events ---

    def _handle_click(self, event: tk.Event) -> None:
        if self._on_click is not None:
            self._on_click()

    def _drag_start(self, event: tk.Event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _drag_move(self, event: tk.Event) -> None:
        if self._root is None:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self._root.winfo_x() + dx
        y = self._root.winfo_y() + dy
        self._root.geometry(f"+{x}+{y}")

    def show(self) -> None:
        if self._root is not None:
            self._root.deiconify()

    def hide(self) -> None:
        if self._root is not None:
            self._root.withdraw()
