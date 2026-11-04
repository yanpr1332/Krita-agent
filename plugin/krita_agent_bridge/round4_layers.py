"""Round 4 read-only document graph, bounded tile previews, and revision overlays.

Krita/Qt operations run through the existing GUI-thread Bridge dispatcher.
A revision overlay never mutates original paint layers or masks.
"""
import hashlib
import uuid
from .advanced_utils import describe, find_node, integer, walk, word

COMMANDS = frozenset(("document.graph", "preview.tile", "revision.overlay.begin",
                       "revision.overlay.inspect"))
MAX_TILE_AREA = 1024 * 1024


def graph(bridge):
    doc = bridge._doc()
    doc.waitForDone()
    rows = []
    def traverse(parent, parent_id, path, inherited_visible, depth):
        for index, child in enumerate(parent.childNodes()):
            item = describe(child, depth)
            item["parent_id"] = parent_id
            item["sibling_index"] = index
            item["path"] = path + [index]
            item["effective_visible"] = bool(child.visible() and inherited_visible)
            item["color_model"] = child.colorModel()
            item["color_depth"] = child.colorDepth()
            try:
                rect = child.bounds()
                item["bounds"] = [rect.x(), rect.y(), rect.width(), rect.height()]
            except (AttributeError, RuntimeError):
                item["bounds"] = None
            rows.append(item)
            if len(rows) > 512:
                raise ValueError("Layer graph exceeds 512 nodes")
            traverse(child, item["id"], item["path"], item["effective_visible"], depth+1)
    traverse(doc.rootNode(), None, [], True, 0)
    return {
        "schema": "krita-agent-document-graph/1",
        "document": {"name": doc.name(), "width": doc.width(), "height": doc.height(),
                     "model": doc.colorModel(), "depth": doc.colorDepth(),
                     "profile": doc.colorProfile()},
        "nodes": rows,
        "note": "Native node IDs may change after KRA reopening; path/type fallback requires explicit reconciliation."
    }


def execute(bridge, command, p):
    doc = bridge._doc()
    if command == "document.graph":
        return graph(bridge)
    if command == "preview.tile":
        x = integer(p.get("x"), "x", 0, doc.width()-1)
        y = integer(p.get("y"), "y", 0, doc.height()-1)
        w = integer(p.get("width"), "width", 1, min(1024, doc.width()-x))
        h = integer(p.get("height"), "height", 1, min(1024, doc.height()-y))
        if w*h > MAX_TILE_AREA:
            raise ValueError("Tile exceeds 1,048,576 pixels")
        from .advanced_media import _save
        doc.waitForDone()
        image = doc.projection(x, y, w, h)
        name = p.get("filename") or ("tiles/" + uuid.uuid4().hex + ".png")
        result = _save(bridge, image, name)
        result["origin"] = [x, y]
        result["coordinate_system"] = "document_pixels"
        return result
    if command == "revision.overlay.begin":
        if p.get("confirm") is not True or bridge.active:
            raise ValueError("Overlay creation requires confirm=true and no active job")
        if doc.colorModel() != "RGBA" or doc.colorDepth() != "U8":
            raise ValueError("Overlay requires RGBA U8 document")
        from .checkpoints import _manifest
        record = _manifest(bridge, p.get("checkpoint_id"))
        if (record["document_name"] != doc.name()
                or [record["width"], record["height"]] != [doc.width(), doc.height()]
                or doc.modified()):
            raise ValueError("Document differs from checkpoint; refuse overlay creation")
        if not record.get("sha256"):
            raise ValueError("Invalid checkpoint")
        name = word(p.get("name", "AgentOverlay-" + uuid.uuid4().hex[:12]))
        if any(n.name() == name for n, _ in walk(doc.rootNode())):
            raise ValueError("Overlay name already exists")
        root = doc.rootNode()
        layer = doc.createNode(name, "paintlayer")
        if layer is None or not root.addChildNode(layer, None):
            raise RuntimeError("Krita rejected overlay layer")
        if layer.type() != "paintlayer":
            raise RuntimeError("Krita did not return a paint layer")
        doc.setActiveNode(layer)
        doc.refreshProjection()
        return {"id": str(layer.uniqueId().toString()), "name": name,
                "checkpoint_id": record["id"], "original_layers_modified": False,
                "warning": "Overlay must be visually verified for exact output; opaque changed pixels only"}
    if command == "revision.overlay.inspect":
        node = find_node(doc, p, paint_only=True)
        return {"id": str(node.uniqueId().toString()), "name": node.name(),
                "visible": node.visible(), "locked": node.locked(), "bounds": (
                    [node.bounds().x(), node.bounds().y(),
                     node.bounds().width(), node.bounds().height()])}
    raise ValueError("Unknown Round 4 layer command")
