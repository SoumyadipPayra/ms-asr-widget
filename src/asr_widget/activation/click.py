from __future__ import annotations

import logging
from typing import Callable

from asr_widget.activation.base import ActivationSource

logger = logging.getLogger(__name__)


class ClickActivation(ActivationSource):
    """Activation via widget click/tap.

    This source is driven externally by the UI — the widget calls
    ``on_click()`` when the user taps it.
    """

    def __init__(
        self,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
    ) -> None:
        super().__init__(on_activate, on_deactivate)

    def start(self) -> None:
        # Nothing to set up — driven by UI events
        pass

    def stop(self) -> None:
        pass

    def on_click(self) -> None:
        """Called by the UI when the widget is clicked."""
        logger.debug("Widget clicked")
        self.toggle()
