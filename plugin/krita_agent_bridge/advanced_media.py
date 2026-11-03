"""Sandboxed image import, native reference layer, and preview snapshots."""
import hashlib
from krita import Krita
from .advanced_utils import find_node, integer, safe_input, word

try:
    from PyQt5.QtCore import QByteArray
    from PyQt5.QtGui import QColor, QImage
    ARGB32 = QImage.Format_ARGB32
except ImportError:
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtGui import QColor, QImage
    ARGB32 = QImage.Format.Format_ARGB32

COMMANDS = frozenset((
    "brush.list", "brush.inspect",
    "reference.import", "image.import", "preview.canvas", "preview.layer",
    "preview.region", "pixel.fill", "pixel.clear"
))


def _save(bridge, image, filename):
    target = bridge._safe_path(word(filename, "preview filename", 240), ".png", False)
    if image.isNull() or not image.save(target, "PNG"):
        raise RuntimeError("Krita preview could not be saved")
    digest = hashlib.sha256()
    with open(target, "rb") as source:
        for block in iter(lambda: source.read(128*1024), b""):
            digest.update(block)
    return {"path": target, "width": image.width(), "height": image.height(),
            "sha256": digest.hexdigest()}


def _rgba(doc):
    if doc.colorModel() != "RGBA" or doc.colorDepth() != "U8":
        raise RuntimeError("This operation requires RGBA U8 document")


def execute(bridge, command, p):
    app = Krita.instance()
    if command in ("brush.list", "brush.inspect"):
        resources = app.resources("preset")
        if command == "brush.inspect":
            name = word(p.get("name"), "preset name")
            matching = [resource for resource in resources.values() if resource.name() == name]
            if len(matching) != 1:
                raise ValueError("No unique matching brush preset")
            resource = matching[0]
            return {"name": resource.name(), "filename": resource.filename(),
                    "valid": bool(resource.name() and resource.filename()), "notice": "Pressure mapping depends on preset settings"}
        query = p.get("query", "")
        if query:
            query = word(query, "query", 120).casefold()
        limit = integer(p.get("limit", 100), "limit", 1, 500)
        matching = [{"name": item.name(), "key": key}
                    for key, item in resources.items() if query in item.name().casefold()]
        return {"total": len(matching), "presets": matching[:limit],
                "truncated": len(matching) > limit}
    doc = bridge._doc()
    if command == "reference.import":
        source = safe_input(bridge, p.get("path"))
        layer = doc.createFileLayer(word(p.get("name", source.stem)), str(source), "None")
        if layer is None or not doc.rootNode().addChildNode(layer, doc.activeNode()):
            raise RuntimeError("Could not add file reference layer")
        return {"name": layer.name(), "type": layer.type(), "source": str(source)}
    if command == "image.import":
        _rgba(doc)
        source = safe_input(bridge, p.get("path"))
        image = QImage(str(source))
        if image.isNull():
            raise ValueError("Image could not be decoded")
        image = image.convertToFormat(ARGB32)
        width, height = image.width(), image.height()
        if width*height > 4000000:
            raise ValueError("Imported image exceeds 4 million pixels")
        x = integer(p.get("x", 0), "x", 0, doc.width()-1)
        y = integer(p.get("y", 0), "y", 0, doc.height()-1)
        if x+width > doc.width() or y+height > doc.height():
            raise ValueError("Image would extend beyond canvas")
        pointer = image.bits()
        size = width*height*4
        try:
            pointer.setsize(size)
        except AttributeError:
            pass
        pixel_bytes = bytes(pointer[:size])
        if len(pixel_bytes) != size:
            raise RuntimeError("Invalid Qt pixel buffer size")
        layer = doc.createNode(word(p.get("name", source.stem)), "paintlayer")
        if layer is None or not layer.setPixelData(QByteArray(pixel_bytes), x, y, width, height):
            raise RuntimeError("Krita rejected RGBA pixels")
        if not doc.rootNode().addChildNode(layer, doc.activeNode()):
            raise RuntimeError("Krita rejected imported layer")
        doc.setActiveNode(layer)
        return {"name": layer.name(), "width": width, "height": height, "type": "paintlayer"}
    if command.startswith("preview."):
        doc.waitForDone()
        if command == "preview.region":
            x = integer(p.get("x"), "x", 0, doc.width()-1)
            y = integer(p.get("y"), "y", 0, doc.height()-1)
            w = integer(p.get("width"), "width", 1, min(2048, doc.width()-x))
            h = integer(p.get("height"), "height", 1, min(2048, doc.height()-y))
            if w*h > 2000000:
                raise ValueError("Preview too large")
            image = doc.projection(x, y, w, h)
        else:
            w = integer(p.get("width", 512), "width", 1, 2048)
            h = integer(p.get("height", 512), "height", 1, 2048)
            if w*h > 2000000:
                raise ValueError("Preview too large")
            image = (doc.thumbnail(w, h) if command == "preview.canvas" else
                     find_node(doc, p).thumbnail(w, h))
        return _save(bridge, image, p.get("filename", "preview/snapshot.png"))
    if command in ("pixel.fill", "pixel.clear"):
        _rgba(doc)
        if p.get("confirm") is not True:
            raise ValueError("Pixel changes require confirm=true")
        node = find_node(doc, p, paint_only=True)
        if node.locked():
            raise ValueError("Target layer locked")
        x = integer(p.get("x"), "x", 0, doc.width()-1)
        y = integer(p.get("y"), "y", 0, doc.height()-1)
        width = integer(p.get("width"), "width", 1, doc.width()-x)
        height = integer(p.get("height"), "height", 1, doc.height()-y)
        if width*height > 4000000:
            raise ValueError("Pixel region too large")
        if command == "pixel.clear":
            data = b"\x00"*(width*height*4)
        else:
            color = QColor(word(p.get("color"), "color", 9))
            if not color.isValid():
                raise ValueError("Invalid fill color")
            data = bytes((color.blue(), color.green(), color.red(), color.alpha()))*(width*height)
        if not node.setPixelData(QByteArray(data), x, y, width, height):
            raise RuntimeError("Krita rejected direct pixel replacement")
        doc.refreshProjection()
        return {"region": [x, y, width, height], "layer_id": str(node.uniqueId().toString())}
    raise ValueError("Unsupported image operation")
