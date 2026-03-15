from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Callable


class ActivationState(enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"


class ActivationSource(ABC):
    """Base class for all activation sources.

    Subclasses implement different ways to trigger recording:
    hotkey, click, wake word, etc. Multiple sources can be active
    simultaneously — they all call the same callbacks.
    """

    def __init__(
        self,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
    ) -> None:
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._state = ActivationState.INACTIVE

    @property
    def state(self) -> ActivationState:
        return self._state

    @abstractmethod
    def start(self) -> None:
        """Begin listening for activation signals."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop listening for activation signals."""
        ...

    def activate(self) -> None:
        """Trigger activation (called by subclass when activation event occurs)."""
        if self._state == ActivationState.INACTIVE:
            self._state = ActivationState.ACTIVE
            self._on_activate()

    def deactivate(self) -> None:
        """Trigger deactivation."""
        if self._state == ActivationState.ACTIVE:
            self._state = ActivationState.INACTIVE
            self._on_deactivate()

    def toggle(self) -> None:
        """Toggle between active and inactive."""
        if self._state == ActivationState.ACTIVE:
            self.deactivate()
        else:
            self.activate()
