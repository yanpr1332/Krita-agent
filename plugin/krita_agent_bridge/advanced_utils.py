"""Shared validation and safe selectors for second-round Krita commands."""
import math
import os
from pathlib import Path


def integer(value, name, minimum=None, maximum=None):
    if type(value) is not int or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError(name + " must be an integer in range")
    return value


def finite(value, name, minimum=None, maximum=None):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(name + " must be a finite number")
    val = float(value)
    if (minimum is not None and val < minimum) or (maximum is not None and val > maximum):
        raise ValueError(name + " out of range")
    return val


def word(value, name="name", length=120):
    if not isinstance(value, str) or not value.strip() or len(value) > length or any(c in value for c in ("\x00", "\n", "\r")):
        raise ValueError("Invalid " + name)
    return value.strip()


def flag(value, name):
    if type(value) is not bool:
        raise ValueError(name + " must be boolean")
    return value


def safe_input(bridge, filename, extensions=(".png", ".jpg", ".jpeg", ".webp")):
    """Input access is limited to the explicit KRITA_AGENT_INPUT_DIR sandbox."""
    root = Path(os.environ.get("KRITA_AGENT_INPUT_DIR") or bridge.output_dir).resolve()
    source = Path(word(filename, "input path", 500))
    path = (source if source.is_absolute() else root / source).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Input path outside authorized root")
    if path.suffix.lower() not in extensions or not path.is_file():
        raise ValueError("Input file missing or unsupported")
    return path


def node_id(node):
    return str(node.uniqueId().toString())


def walk(node, depth=0):
    for child in node.childNodes():
        yield child, depth
        yield from walk(child, depth+1)


def find_node(doc, parameters, paint_only=False):
    uid, name = parameters.get("id"), parameters.get("name")
    if uid is not None:
        uid = word(uid, "node id", 120)
        found = [n for n, _ in walk(doc.rootNode()) if node_id(n) == uid]
    elif name is not None:
        name = word(name, "node name")
        found = [n for n, _ in walk(doc.rootNode()) if n.name() == name]
    else:
        found = [doc.activeNode()] if doc.activeNode() is not None else []
    if len(found) != 1:
        raise ValueError("Layer selector did not match exactly one node")
    node = found[0]
    if paint_only and node.type() != "paintlayer":
        raise ValueError("Target must be a paint layer")
    return node


def describe(node, depth=0):
    position = node.position()
    return {"id": node_id(node), "name": node.name(), "type": node.type(),
            "visible": node.visible(), "locked": node.locked(),
            "opacity": node.opacity()/255.0, "blending_mode": node.blendingMode(),
            "position": [position.x(), position.y()], "depth": depth,
            "children": len(node.childNodes())}
