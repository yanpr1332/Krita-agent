"""Safety router for checkpoint, pixel history, and cross-session clipboard."""
from . import checkpoints, pixel_history, clipboard_store

HANDLERS = (checkpoints, pixel_history, clipboard_store)
COMMANDS = frozenset().union(*(m.COMMANDS for m in HANDLERS))


def execute(bridge, command, params):
    for handler in HANDLERS:
        if command in handler.COMMANDS:
            return handler.execute(bridge, command, params)
    raise ValueError("No matching checkpoint handler")
