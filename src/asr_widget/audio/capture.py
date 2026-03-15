from __future__ import annotations

import logging
import queue
import threading

import numpy as np
import sounddevice as sd

from asr_widget.config import AudioConfig

logger = logging.getLogger(__name__)


class MicCapture:
    """Microphone audio capture.

    Opens the system microphone and produces PCM s16le chunks
    at the configured sample rate and chunk duration. Chunks are
    pushed to a ``queue.Queue`` for consumption by the async audio pump.
    """

    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._stream: sd.InputStream | None = None
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=200)
        self._running = False

    @property
    def chunk_queue(self) -> queue.Queue[bytes | None]:
        """Queue of PCM s16le byte chunks. ``None`` signals end of stream."""
        return self._queue

    def start(self) -> None:
        """Start capturing audio from the microphone."""
        if self._running:
            return

        # Drain any leftover data
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        device = self._config.device
        self._stream = sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self._config.chunk_samples,
            device=device,
            callback=self._audio_callback,
        )
        self._running = True
        self._stream.start()
        logger.info(
            "Mic capture started (sr=%d, chunk=%dms, device=%s)",
            self._config.sample_rate,
            self._config.chunk_duration_ms,
            device or "default",
        )

    def stop(self) -> None:
        """Stop capturing audio."""
        if not self._running:
            return
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        # Signal end of stream
        self._queue.put(None)
        logger.info("Mic capture stopped")

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Called by PortAudio on its own thread."""
        if status:
            logger.warning("Audio callback status: %s", status)
        if not self._running:
            return
        # indata is (frames, 1) int16 array — flatten and convert to bytes
        try:
            self._queue.put_nowait(indata.tobytes())
        except queue.Full:
            logger.warning("Audio queue full, dropping chunk")
