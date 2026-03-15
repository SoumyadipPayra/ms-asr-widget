from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable

logger = logging.getLogger(__name__)

STATE_COLORS = {
    "idle": "#404048",
    "listening": "#2ecc40",
    "processing": "#f0c020",
    "error": "#e64030",
}

STATE_OUTLINE = {
    "idle": "#666670",
    "listening": "#50ff70",
    "processing": "#ffe060",
    "error": "#ff6050",
}


class FloatingWidget:
    """Floating always-on-top circular widget using tkinter.

    Works on Linux (X11/Wayland) and macOS.
    """

    def __init__(
        self,
        size: int = 44,
        opacity: float = 0.9,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        self._size = size
        self._opacity = opacity
        self._on_click = on_click
        self._state = "idle"
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._circle_id: int | None = None
        self._text_id: int | None = None

    def create(self, root: tk.Tk) -> None:
        """Attach to an existing Tk root and create the widget."""
        self._root = root
        root.title("ASR Widget")
        root.overrideredirect(True)  # Borderless
        root.attributes("-topmost", True)  # Always on top

        try:
            root.attributes("-alpha", self._opacity)
        except tk.TclError:
            pass  # Alpha not supported on all Linux WMs

        # Make the window background transparent where possible
        root.configure(bg="black")
        try:
            root.wm_attributes("-transparentcolor", "black")
        except tk.TclError:
            pass  # Not supported everywhere

        # Position bottom-right
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = screen_w - self._size - 30
        y = screen_h - self._size - 60
        root.geometry(f"{self._size}x{self._size}+{x}+{y}")

        # Canvas for the circle
        self._canvas = tk.Canvas(
            root,
            width=self._size,
            height=self._size,
            bg="black",
            highlightthickness=0,
        )
        self._canvas.pack()

        pad = 2
        self._circle_id = self._canvas.create_oval(
            pad, pad, self._size - pad, self._size - pad,
            fill=STATE_COLORS["idle"],
            outline=STATE_OUTLINE["idle"],
            width=2,
        )
        self._text_id = self._canvas.create_text(
            self._size // 2,
            self._size // 2,
            text="\U0001f3a4",
            font=("", int(self._size * 0.35)),
            fill="white",
        )

        # Click handler
        self._canvas.bind("<Button-1>", self._handle_click)

        # Enable dragging
        self._drag_data = {"x": 0, "y": 0}
        self._canvas.bind("<ButtonPress-1>", self._drag_start, add="+")
        self._canvas.bind("<B1-Motion>", self._drag_move)

        logger.info("Floating widget created at (%d, %d)", x, y)

    def set_state(self, state: str) -> None:
        """Update the visual state. Thread-safe via root.after()."""
        self._state = state
        if self._root is not None:
            self._root.after(0, self._apply_state, state)

    def _apply_state(self, state: str) -> None:
        if self._canvas is None:
            return
        fill = STATE_COLORS.get(state, STATE_COLORS["idle"])
        outline = STATE_OUTLINE.get(state, STATE_OUTLINE["idle"])
        self._canvas.itemconfig(self._circle_id, fill=fill, outline=outline)

        icon = "\U0001f534" if state == "listening" else "\U0001f3a4"
        self._canvas.itemconfig(self._text_id, text=icon)

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
