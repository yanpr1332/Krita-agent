"""Explicit native transforms and undo/redo with strict state checks."""
import math
from krita import Krita
from .advanced_utils import finite, find_node, integer

try:
    from PyQt5.QtCore import QPointF
except ImportError:
    from PyQt6.QtCore import QPointF

COMMANDS = frozenset(("layer.scale", "layer.rotate", "history.undo", "history.redo"))


def execute(bridge, command, p):
    if command.startswith("history."):
        if bridge.active:
            raise RuntimeError("Cannot undo/redo while a drawing job is running or paused")
        key = "edit_undo" if command == "history.undo" else "edit_redo"
        action = Krita.instance().action(key)
        if action is None or not action.isEnabled():
            raise RuntimeError("No enabled Krita action: " + key)
        action.trigger()
        doc = bridge._doc()
        doc.waitForDone()
        doc.refreshProjection()
        doc.waitForDone()
        return {"action": key, "triggered": True}
    doc = bridge._doc()
    node = find_node(doc, p)
    if node.locked():
        raise ValueError("Layer is locked")
    if p.get("confirm") is not True:
        raise ValueError("Transforms require confirm=true")
    if command == "layer.scale":
        ox = finite(p.get("origin_x", 0), "origin_x", -32768, 32768)
        oy = finite(p.get("origin_y", 0), "origin_y", -32768, 32768)
        width = integer(p.get("width"), "width", 1, 8192)
        height = integer(p.get("height"), "height", 1, 8192)
        node.scaleNode(QPointF(ox, oy), width, height, "Bicubic")
        return {"layer": node.name(), "scale": [width, height], "origin": [ox, oy]}
    if command == "layer.rotate":
        degrees = finite(p.get("degrees"), "degrees", -360, 360)
        node.rotateNode(degrees * math.pi / 180)
        return {"layer": node.name(), "degrees": degrees}
    raise ValueError("Unsupported transform")
