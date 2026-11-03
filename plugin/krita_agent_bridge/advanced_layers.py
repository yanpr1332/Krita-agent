"""Native editable layer operations, addressed by stable Krita unique IDs."""
from .advanced_utils import describe, find_node, flag, finite, integer, walk, word


COMMANDS = frozenset((
    "layer.tree", "layer.inspect", "layer.select_id", "layer.rename",
    "layer.set", "layer.move", "layer.duplicate", "layer.group",
    "layer.reorder", "layer.delete"
))


def execute(bridge, command, p):
    doc = bridge._doc()
    root = doc.rootNode()
    if command == "layer.tree":
        return [describe(node, depth) for node, depth in walk(root)]
    if command == "layer.group":
        name = word(p.get("name"))
        parent = find_node(doc, {"id": p["parent_id"]}) if "parent_id" in p else root
        if parent != root and parent.type() != "grouplayer":
            raise ValueError("A group must be attached to root or another group")
        group = doc.createNode(name, "grouplayer")
        if group is None or not parent.addChildNode(group, None):
            raise RuntimeError("Krita rejected group insertion")
        return describe(group)
    node = find_node(doc, p)
    if command == "layer.inspect":
        return describe(node)
    if command == "layer.select_id":
        doc.setActiveNode(node)
        return describe(node)
    if command == "layer.rename":
        node.setName(word(p.get("new_name"), "new_name"))
    elif command == "layer.set":
        changes = p.get("properties")
        if not isinstance(changes, dict) or not changes:
            raise ValueError("properties must be a nonempty object")
        setters = {"visible": node.setVisible, "locked": node.setLocked,
                   "opacity": node.setOpacity, "blending_mode": node.setBlendingMode,
                   "alpha_locked": node.setAlphaLocked, "color_label": node.setColorLabel}
        if set(changes).difference(setters):
            raise ValueError("Unknown layer property")
        prepared = {}
        for key, val in changes.items():
            if key in ("visible", "locked", "alpha_locked"):
                prepared[key] = flag(val, key)
            elif key == "opacity":
                prepared[key] = int(round(finite(val, key, 0, 1)*255))
            elif key == "blending_mode":
                prepared[key] = word(val, key, 80)
            elif key == "color_label":
                prepared[key] = integer(val, key, 0, 8)
        for key, val in prepared.items():
            setters[key](val)
    elif command == "layer.move":
        if node.locked():
            raise ValueError("Layer locked")
        dx = integer(p.get("dx", 0), "dx", -32768, 32768)
        dy = integer(p.get("dy", 0), "dy", -32768, 32768)
        pos = node.position()
        node.move(pos.x()+dx, pos.y()+dy)
    elif command == "layer.duplicate":
        duplicate = node.duplicate()
        parent = node.parentNode()
        if duplicate is None or parent is None or not parent.addChildNode(duplicate, node):
            raise RuntimeError("Krita could not duplicate layer")
        duplicate.setName(word(p.get("new_name", node.name()+" Copy"), "new_name"))
        doc.setActiveNode(duplicate)
        return describe(duplicate)
    elif command == "layer.reorder":
        parent = node.parentNode()
        if parent is None:
            raise ValueError("Cannot reorder root")
        siblings = list(parent.childNodes())
        index = integer(p.get("index"), "index", 0, len(siblings)-1)
        siblings.remove(node)
        siblings.insert(index, node)
        parent.setChildNodes(siblings)
    elif command == "layer.delete":
        if p.get("confirm") is not True:
            raise ValueError("Delete requires confirm=true")
        result = {"removed_id": str(node.uniqueId().toString()), "name": node.name()}
        if not node.remove():
            raise RuntimeError("Krita refused layer removal")
        return result
    else:
        raise ValueError("Unknown layer operation")
    return describe(node)
