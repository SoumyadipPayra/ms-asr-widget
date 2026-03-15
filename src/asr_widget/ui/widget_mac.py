from __future__ import annotations

import logging
import math
from typing import Callable

import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMakeRect,
    NSPanel,
    NSParagraphStyleAttributeName,
    NSParagraphStyle,
    NSScreen,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from AppKit import NSFloatingWindowLevel
import Quartz

logger = logging.getLogger(__name__)

# --- Colors ---------------------------------------------------------------

def _nscolor(r, g, b, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a)

STATE_FILL = {
    "idle":       (0.22, 0.22, 0.25),
    "listening":  (0.15, 0.72, 0.32),
    "processing": (0.92, 0.72, 0.12),
    "error":      (0.88, 0.22, 0.18),
}

STATE_GLOW = {
    "idle":       (0.40, 0.40, 0.45, 0.0),
    "listening":  (0.15, 0.90, 0.40, 0.45),
    "processing": (0.95, 0.80, 0.20, 0.35),
    "error":      (0.95, 0.30, 0.20, 0.35),
}

# --- Pulse ring layer (Core Animation) ------------------------------------

RING_COUNT = 3          # Number of concentric radiation rings
RING_DURATION = 1.8     # Total animation cycle duration (seconds)


class PulseView(NSView):
    """Transparent overlay that draws expanding, fading concentric rings
    to create a subtle radiation/sonar pulse when the widget is active.
    """

    def initWithFrame_(self, frame):
        self = objc.super(PulseView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._phase = 0.0          # 0..1 animation phase
        self._color = (0.15, 0.90, 0.40, 0.45)
        self._animating = False
        self._timer = None
        return self

    def drawRect_(self, rect):
        if not self._animating:
            return

        cx = self.bounds().size.width / 2
        cy = self.bounds().size.height / 2
        max_radius = cx  # View is square, centered

        for i in range(RING_COUNT):
            # Stagger rings evenly across the cycle
            ring_phase = (self._phase + i / RING_COUNT) % 1.0
            radius = 12 + (max_radius - 12) * ring_phase
            alpha = self._color[3] * (1.0 - ring_phase) * 0.6

            if alpha < 0.01:
                continue

            r, g, b, _ = self._color
            color = _nscolor(r, g, b, alpha)
            color.setStroke()

            ring = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(cx - radius, cy - radius, radius * 2, radius * 2)
            )
            ring.setLineWidth_(1.5 * (1.0 - ring_phase) + 0.5)
            ring.stroke()

    def startAnimating_(self, color):
        self._color = color
        self._animating = True
        self._phase = 0.0
        if self._timer is None:
            from Foundation import NSTimer
            self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0 / 30.0,  # 30 fps
                self,
                "tick:",
                None,
                True,
            )

    def stopAnimating(self):
        self._animating = False
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None
        self.setNeedsDisplay_(True)

    def tick_(self, timer):
        self._phase = (self._phase + 1.0 / (30.0 * RING_DURATION)) % 1.0
        self.setNeedsDisplay_(True)


# --- Main circle view -----------------------------------------------------

class CircleView(NSView):
    """Draws the solid circle with a microphone glyph."""

    def initWithFrame_state_(self, frame, state):
        self = objc.super(CircleView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._state = state or "idle"
        return self

    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        r, g, b = STATE_FILL.get(self._state, STATE_FILL["idle"])

        # Shadow
        shadow_color = _nscolor(0, 0, 0, 0.35)
        shadow_color.setFill()
        shadow_rect = NSMakeRect(1, 0, self.bounds().size.width - 2, self.bounds().size.height - 2)
        NSBezierPath.bezierPathWithOvalInRect_(shadow_rect).fill()

        # Main circle
        inset = 2
        circle_rect = NSMakeRect(
            inset, inset,
            self.bounds().size.width - inset * 2,
            self.bounds().size.height - inset * 2,
        )
        _nscolor(r, g, b, 0.95).setFill()
        path = NSBezierPath.bezierPathWithOvalInRect_(circle_rect)
        path.fill()

        # Subtle highlight on upper half
        highlight_rect = NSMakeRect(
            inset + 4, self.bounds().size.height / 2,
            self.bounds().size.width - inset * 2 - 8,
            self.bounds().size.height / 2 - inset - 2,
        )
        _nscolor(1, 1, 1, 0.12).setFill()
        NSBezierPath.bezierPathWithOvalInRect_(highlight_rect).fill()

        # Border
        _nscolor(1, 1, 1, 0.15).setStroke()
        path.setLineWidth_(1.0)
        path.stroke()

        # Mic icon (using SF Symbols text fallback)
        icon = "\U0001F399" if self._state != "listening" else "\U0001F534"
        font_size = self.bounds().size.width * 0.36
        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(font_size),
            NSForegroundColorAttributeName: _nscolor(1, 1, 1, 0.9),
        }
        from Foundation import NSString
        ns_str = NSString.alloc().initWithString_(icon)
        size = ns_str.sizeWithAttributes_(attrs)
        x = (self.bounds().size.width - size.width) / 2
        y = (self.bounds().size.height - size.height) / 2
        ns_str.drawAtPoint_withAttributes_((x, y), attrs)

    def setState_(self, state):
        self._state = state
        self.setNeedsDisplay_(True)

    def mouseDown_(self, event):
        if hasattr(self, "_on_click") and self._on_click is not None:
            self._on_click()


# --- Floating widget -------------------------------------------------------

class FloatingWidget:
    """Native macOS floating always-on-top circular widget with pulse animation."""

    def __init__(
        self,
        size: int = 44,
        opacity: float = 0.9,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        self._size = size
        self._pulse_size = size * 3  # Pulse rings extend beyond the circle
        self._opacity = opacity
        self._on_click = on_click
        self._state = "idle"
        self._panel: NSPanel | None = None
        self._circle_view: CircleView | None = None
        self._pulse_view: PulseView | None = None

    def create(self) -> None:
        """Create and show the floating widget. Must be called on main thread."""
        screen = NSScreen.mainScreen()
        sf = screen.visibleFrame()

        # Position bottom-right, window sized for pulse rings
        x = sf.origin.x + sf.size.width - self._pulse_size - 20
        y = sf.origin.y + 20
        frame = NSMakeRect(x, y, self._pulse_size, self._pulse_size)

        self._panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        self._panel.setLevel_(NSFloatingWindowLevel)
        self._panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        self._panel.setAlphaValue_(self._opacity)
        self._panel.setOpaque_(False)
        self._panel.setBackgroundColor_(NSColor.clearColor())
        self._panel.setMovableByWindowBackground_(True)
        self._panel.setHasShadow_(False)
        self._panel.setIgnoresMouseEvents_(False)

        # Container view
        container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, self._pulse_size, self._pulse_size)
        )
        self._panel.setContentView_(container)

        # Pulse layer (fills entire window)
        self._pulse_view = PulseView.alloc().initWithFrame_(
            NSMakeRect(0, 0, self._pulse_size, self._pulse_size)
        )
        container.addSubview_(self._pulse_view)

        # Circle view (centered within the larger window)
        offset = (self._pulse_size - self._size) / 2
        self._circle_view = CircleView.alloc().initWithFrame_state_(
            NSMakeRect(offset, offset, self._size, self._size),
            "idle",
        )
        self._circle_view._on_click = self._on_click
        container.addSubview_(self._circle_view)

        self._panel.orderFrontRegardless()
        logger.info("Floating widget created at (%.0f, %.0f)", x, y)

    def set_state(self, state: str) -> None:
        """Update visual state. Thread-safe."""
        self._state = state
        if self._circle_view is not None:
            self._circle_view.performSelectorOnMainThread_withObject_waitUntilDone_(
                "setState:", state, False
            )
        if self._pulse_view is not None:
            glow = STATE_GLOW.get(state, STATE_GLOW["idle"])
            if state in ("listening", "processing"):
                self._pulse_view.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "startAnimating:", glow, False
                )
            else:
                self._pulse_view.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "stopAnimating", None, False
                )

    def show(self) -> None:
        if self._panel is not None:
            self._panel.orderFrontRegardless()

    def hide(self) -> None:
        if self._panel is not None:
            self._panel.orderOut_(None)
