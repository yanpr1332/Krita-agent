"""Combinatorial and feathered selections without arbitrary clipboard evaluation."""
from krita import Selection
from .advanced_utils import integer

COMMANDS = frozenset(("selection.combine", "selection.modify", "selection.metrics"))
AREA_LIMIT = 4_000_000


def _rect(doc, p):
    x = integer(p.get("x"), "x", 0, doc.width()-1)
    y = integer(p.get("y"), "y", 0, doc.height()-1)
    w = integer(p.get("width"), "width", 1, doc.width()-x)
    h = integer(p.get("height"), "height", 1, doc.height()-y)
    if w*h > AREA_LIMIT:
        raise ValueError("Selection area too large")
    return x, y, w, h


def execute(bridge, command, p):
    doc = bridge._doc()
    doc.waitForDone()
    current = doc.selection()
    selection = current.duplicate() if current is not None else None
    if command == "selection.combine":
        x, y, w, h = _rect(doc, p)
        incoming = Selection()
        incoming.select(x, y, w, h, integer(p.get("strength", 255), "strength", 0, 255))
        mode = p.get("mode", "add")
        if mode == "replace":
            doc.setSelection(incoming)
        elif mode in ("add", "subtract", "intersect", "xor"):
            if selection is None:
                raise ValueError("Active selection required for " + mode)
            method = {"add": "add", "subtract": "subtract", "intersect": "intersect",
                      "xor": "symmetricdifference"}[mode]
            getattr(selection, method)(incoming)
            doc.setSelection(selection)
        else:
            raise ValueError("Unknown selection combination")
        return {"mode": mode, "region": [x, y, w, h]}
    if selection is None:
        raise ValueError("Active selection required")
    if command == "selection.metrics":
        return {"bounds": [selection.x(), selection.y(), selection.width(), selection.height()],
                "note": "Bounds do not describe feather coverage at every pixel"}
    mode = p.get("mode")
    if mode == "feather":
        selection.feather(integer(p.get("radius"), "radius", 1, 200))
    elif mode == "grow":
        radius = integer(p.get("radius"), "radius", 1, 200)
        selection.grow(radius, radius)
    elif mode == "shrink":
        radius = integer(p.get("radius"), "radius", 1, 200)
        selection.shrink(radius, radius, True)
    elif mode == "border":
        radius = integer(p.get("radius"), "radius", 1, 200)
        selection.border(radius, radius)
    elif mode == "invert":
        selection.invert()
    elif mode == "smooth":
        selection.smooth()
    else:
        raise ValueError("Supported modes: feather/grow/shrink/border/invert/smooth")
    doc.setSelection(selection)
    return {"mode": mode, "bounds": [selection.x(), selection.y(),
                                    selection.width(), selection.height()]}
