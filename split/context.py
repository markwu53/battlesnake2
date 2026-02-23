
# context.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import GameTurn

class _Context:
    def __init__(self):
        # We use _state internally to avoid name conflicts
        self._state: GameTurn | None = None

    @property
    def g(self):
        """Returns the proxy itself so 'g' remains a stable reference."""
        return self

    def __getattr__(self, name):
        """Forwards all property access (e.g., g.snakes) to the current state."""
        if self._state is None:
            raise AttributeError(f"Game context not initialized. Cannot access '{name}'")
        return getattr(self._state, name)

    def __setattr__(self, name, value):
        """Allows setting attributes on the live GameTurn object."""
        if name == "_state":
            super().__setattr__(name, value)
        else:
            if self._state is None:
                raise AttributeError(f"Game context not initialized. Cannot set '{name}'")
            setattr(self._state, name, value)

# The single instance used across your entire project
_helper = _Context()