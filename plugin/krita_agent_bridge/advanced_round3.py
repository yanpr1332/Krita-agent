"""Round-three native non-destructive features and color/selection discovery."""
from . import advanced_masks, advanced_selection, advanced_color, advanced_brushes

HANDLERS = (advanced_masks, advanced_selection, advanced_color, advanced_brushes)
COMMANDS = frozenset().union(*(module.COMMANDS for module in HANDLERS))


def execute(bridge, command, parameters):
    for handler in HANDLERS:
        if command in handler.COMMANDS:
            return handler.execute(bridge, command, parameters)
    raise ValueError("Unknown round-three command")
