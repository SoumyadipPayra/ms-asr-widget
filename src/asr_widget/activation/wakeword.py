from __future__ import annotations

import logging
from typing import Callable

from asr_widget.activation.base import ActivationSource

logger = logging.getLogger(__name__)


class WakeWordActivation(ActivationSource):
    """Activation via wake word detection.

    This is a placeholder for future implementation. To implement:

    1. Install a keyword-spotting model (e.g., openwakeword, Porcupine, Snowboy)
    2. In ``start()``, open a continuous audio stream (separate from the
       main recording stream) and feed frames to the KWS model
    3. When the model detects the wake word, call ``self.activate()``
    4. Deactivation can be triggered by:
       - A silence timeout after speech ends
       - A "stop" wake word
       - The user clicking the widget
       - A configurable duration limit

    The ``ActivationSource`` interface is designed so this drops in
    alongside ``HotkeyActivation`` and ``ClickActivation`` with no
    changes to the orchestrator.

    Example future implementation sketch::

        def start(self):
            self._kws_model = load_openwakeword("hey_jarvis")
            self._stream = sounddevice.InputStream(
                samplerate=16000, channels=1, dtype="int16",
                callback=self._on_audio,
            )
            self._stream.start()

        def _on_audio(self, indata, frames, time_info, status):
            prediction = self._kws_model.predict(indata)
            if prediction > self._threshold:
                self.activate()
    """

    def __init__(
        self,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
        wake_word: str = "hey computer",
    ) -> None:
        super().__init__(on_activate, on_deactivate)
        self._wake_word = wake_word

    def start(self) -> None:
        logger.info(
            "WakeWordActivation is a stub — wake word '%s' not active",
            self._wake_word,
        )

    def stop(self) -> None:
        pass
