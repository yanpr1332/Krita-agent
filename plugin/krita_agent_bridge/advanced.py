"""Separate route table for second-round native Krita features."""
from . import advanced_layers, advanced_documents, advanced_media, advanced_transforms

HANDLERS = (advanced_layers, advanced_documents, advanced_media, advanced_transforms)
ADVANCED_COMMANDS = frozenset().union(*(handler.COMMANDS for handler in HANDLERS))


def dispatch_advanced(bridge, command, parameters):
    for handler in HANDLERS:
        if command in handler.COMMANDS:
            return handler.execute(bridge, command, parameters)
    raise ValueError("Unknown advanced command")
