from __future__ import annotations

import asyncio
import logging
import platform
import queue
import sys
import threading

from asr_widget.activation.click import ClickActivation
from asr_widget.activation.hotkey import HotkeyActivation
from asr_widget.asr.client import ASRClient
from asr_widget.audio.capture import MicCapture
from asr_widget.config import AppConfig, load_config
from asr_widget.output import KeystrokeInjector
from asr_widget.ui import FloatingWidget, StatusBarItem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


class App:
    """Main application orchestrator.

    Threading model:
      - Main thread: UI event loop (NSApplication on macOS, tkinter on Linux)
      - Background thread: asyncio event loop (WebSocket + audio pump)
      - PortAudio thread: microphone callback (managed by sounddevice)
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._active = False

        # Components
        self._mic = MicCapture(config.audio)
        self._injector = KeystrokeInjector()
        self._asr_client = ASRClient(
            gateway_url=config.gateway.url,
            sample_rate=config.audio.sample_rate,
            on_transcript=self._on_transcript,
            on_state_change=self._on_asr_state_change,
        )

        # UI
        self._widget = FloatingWidget(
            size=config.ui.size,
            opacity=config.ui.opacity,
            on_click=self._on_widget_click,
        )
        self._statusbar = StatusBarItem()

        # Activation sources
        self._click_activation = ClickActivation(
            on_activate=self._on_activate,
            on_deactivate=self._on_deactivate,
        )
        self._hotkey_activation = HotkeyActivation(
            on_activate=self._on_activate,
            on_deactivate=self._on_deactivate,
            combination=config.hotkey.combination,
            mode=config.hotkey.mode,
        )

        self._audio_pump_task: asyncio.Task | None = None

    def run(self) -> None:
        """Start the application."""
        # Asyncio event loop on a background thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_async_loop, daemon=True, name="async-loop"
        )
        self._loop_thread.start()

        # Activation sources
        self._click_activation.start()
        self._hotkey_activation.start()

        logger.info(
            "ASR Widget running — hotkey: %s, gateway: %s",
            self._config.hotkey.combination,
            self._config.gateway.url,
        )

        if platform.system() == "Darwin":
            self._run_macos()
        else:
            self._run_tkinter()

    def _run_macos(self) -> None:
        """macOS: NSApplication + NSPanel."""
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self._widget.create()
        self._statusbar.create()

        from PyObjCTools import AppHelper
        try:
            AppHelper.runEventLoop()
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

    def _run_tkinter(self) -> None:
        """Linux / fallback: tkinter."""
        import tkinter as tk
        root = tk.Tk()
        self._widget.create(root)
        self._statusbar.create()

        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        self._hotkey_activation.stop()
        if self._active:
            self._mic.stop()
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("Shut down")

    def _run_async_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # -- Activation callbacks --

    def _on_activate(self) -> None:
        if self._active:
            return
        self._active = True
        logger.info("Activated — starting recording")

        self._widget.set_state("listening")
        self._statusbar.set_state("listening")
        self._injector.reset()
        self._mic.start()

        asyncio.run_coroutine_threadsafe(self._start_streaming(), self._loop)

    def _on_deactivate(self) -> None:
        if not self._active:
            return
        self._active = False
        logger.info("Deactivated — stopping recording")

        self._mic.stop()
        asyncio.run_coroutine_threadsafe(self._stop_streaming(), self._loop)

        self._widget.set_state("idle")
        self._statusbar.set_state("idle")

    def _on_widget_click(self) -> None:
        self._click_activation.on_click()

    # -- Async streaming --

    async def _start_streaming(self) -> None:
        ok = await self._asr_client.start_session()
        if not ok:
            logger.error("Failed to start ASR session")
            self._widget.set_state("error")
            self._statusbar.set_state("error")
            self._active = False
            self._mic.stop()
            return

        self._audio_pump_task = asyncio.create_task(self._audio_pump())

    async def _stop_streaming(self) -> None:
        if self._audio_pump_task is not None:
            self._audio_pump_task.cancel()
            try:
                await self._audio_pump_task
            except asyncio.CancelledError:
                pass
            self._audio_pump_task = None

        await self._asr_client.stop_session()

    async def _audio_pump(self) -> None:
        mic_queue = self._mic.chunk_queue
        while True:
            chunk = await self._loop.run_in_executor(
                None, self._blocking_queue_get, mic_queue
            )
            if chunk is None:
                break
            if chunk:
                await self._asr_client.send_audio(chunk)

    @staticmethod
    def _blocking_queue_get(q: queue.Queue, timeout: float = 0.5) -> bytes | None:
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return b""

    # -- Transcript callback --

    def _on_transcript(self, text: str) -> None:
        logger.info("Transcript: %s", text)
        self._injector.type_text(text)

    def _on_asr_state_change(self, state: str) -> None:
        if self._active:
            self._widget.set_state(state)
            self._statusbar.set_state(state)


def main() -> None:
    config = load_config()
    app = App(config)
    app.run()


if __name__ == "__main__":
    main()
