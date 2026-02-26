from contextvars import ContextVar
from typing import cast
from .models import GameTurn

_state_var: ContextVar[GameTurn] = ContextVar("game_state")

def set_current_state(state: GameTurn):
    """Call this at the start of main() to 'plug in' the data for THIS snake."""
    _state_var.set(state)

class _Proxy:
    """A proxy that always points to the GameTurn in the CURRENT context."""
    def __getattr__(self, name):
        try:
            state = _state_var.get()
            return getattr(state, name)
        except LookupError:
            raise AttributeError(f"Game context not initialized for this instance. Cannot access '{name}'")

    def __setattr__(self, name, value):
        # Allow setting attributes on the GameTurn object inside the context
        state = _state_var.get()
        setattr(state, name, value)

# This is the 'g' everyone imports. 
# It looks like one object, but it points to different data for different snakes.
g: GameTurn = cast("GameTurn", _Proxy())
