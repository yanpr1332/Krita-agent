"""Separate reversible pixel transactions; never claim Krita native Undo support."""
import base64
import hashlib
import json
import os
import uuid
import zlib
from pathlib import Path
from .advanced_utils import find_node, integer, word, safe_input

try:
    from PyQt5.QtCore import QByteArray
    from PyQt5.QtGui import QColor
except ImportError:
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtGui import QColor

COMMANDS = frozenset(("pixel.transaction.fill", "pixel.transaction.clear",
                      "pixel.transaction.undo", "pixel.transaction.redo",
                      "pixel.transaction.inspect", "pixel.transaction.patch"))
MAX_PIXELS = 500000


def _storage(bridge):
    root = bridge.output_dir / ".krita-agent-pixel-history"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _encode(data):
    return base64.b64encode(zlib.compress(data, level=6)).decode("ascii")


def _decode(encoded, maximum):
    # Prevent malicious payload decompression expanding beyond allowed pixel bytes.
    packed = base64.b64decode(encoded, validate=True)
    decoder = zlib.decompressobj()
    result = decoder.decompress(packed, maximum + 1)
    if len(result) > maximum or decoder.unconsumed_tail:
        raise ValueError("Pixel history decompression limit exceeded")
    if not decoder.eof:
        raise ValueError("Pixel history stream incomplete")
    if len(result) > maximum:
        raise ValueError("Pixel history stream truncated or too large")
    return result


def _atomic(path, data):
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _read(bridge, identifier):
    key = uuid.UUID(word(identifier, "transaction id", 50)).hex
    path = _storage(bridge) / (key + ".json")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("id") != key or record.get("schema") != 1:
        raise ValueError("Invalid pixel transaction")
    return record, path


def _target(bridge, record):
    doc = bridge._doc()
    if [doc.name(), doc.fileName(), doc.width(), doc.height(),
            doc.colorModel(), doc.colorDepth()] != record["document"]:
        raise ValueError("Active document does not match pixel transaction")
    node = find_node(doc, {"id": record["node_id"]}, paint_only=True)
    if node.locked():
        raise ValueError("Target layer is locked")
    return doc, node


def execute(bridge, command, p):
    if command == "pixel.transaction.inspect":
        record, _ = _read(bridge, p.get("id"))
        return {key: record[key] for key in ("id", "state", "rect", "node_id", "document",
                                             "before_sha256", "after_sha256")}
    if command in ("pixel.transaction.undo", "pixel.transaction.redo"):
        if bridge.active:
            raise RuntimeError("Cannot restore pixels during a drawing job")
        if p.get("confirm") is not True:
            raise ValueError("Transaction restoration requires confirm=true")
        record, path = _read(bridge, p.get("id"))
        direction = command.rsplit(".", 1)[1]
        expected_state = "applied" if direction == "undo" else "undone"
        if record["state"] != expected_state:
            raise ValueError("Transaction is not in " + expected_state + " state")
        doc, node = _target(bridge, record)
        x, y, width, height = record["rect"]
        current = bytes(node.pixelData(x, y, width, height))
        if _sha(current) != record["after_sha256" if direction == "undo" else "before_sha256"]:
            raise ValueError("Current pixels have changed; refusing unsafe restoration")
        replacement = _decode(record["before" if direction == "undo" else "after"], width*height*4)
        if len(replacement) != width*height*4 or not node.setPixelData(QByteArray(replacement), x, y, width, height):
            raise RuntimeError("Krita rejected pixel transaction restoration")
        record["state"] = "undone" if direction == "undo" else "applied"
        _atomic(path, record)
        doc.refreshProjection()
        doc.waitForDone()
        return {"id": record["id"], "state": record["state"], "native_undo": False}
    if p.get("confirm") is not True:
        raise ValueError("Pixel transaction requires confirm=true")
    if bridge.active and not getattr(bridge, "_current_job_id", None):
        raise RuntimeError("Pixel transaction not allowed while another job is active")
    doc = bridge._doc()
    if doc.colorModel() != "RGBA" or doc.colorDepth() != "U8":
        raise RuntimeError("Pixel history requires RGBA U8")
    node = find_node(doc, p, paint_only=True)
    if node.locked():
        raise ValueError("Target layer locked")
    x = integer(p.get("x"), "x", 0, doc.width()-1)
    y = integer(p.get("y"), "y", 0, doc.height()-1)
    width = integer(p.get("width"), "width", 1, doc.width()-x)
    height = integer(p.get("height"), "height", 1, doc.height()-y)
    if width*height > MAX_PIXELS:
        raise ValueError("Pixel transaction too large")
    before = bytes(node.pixelData(x, y, width, height))
    if len(before) != width*height*4:
        raise RuntimeError("Invalid original pixel buffer")
    if command == "pixel.transaction.clear":
        after = b"\x00"*len(before)
    elif command == "pixel.transaction.fill":
        color = QColor(word(p.get("color"), "color", 9))
        if not color.isValid() or not color.name().startswith("#"):
            raise ValueError("Invalid color")
        after = bytes((color.blue(), color.green(), color.red(), color.alpha()))*(width*height)
    elif command == "pixel.transaction.patch":
        source = safe_input(bridge, p.get("path"))
        try:
            from PyQt5.QtGui import QImage
            argb = QImage.Format_ARGB32
        except ImportError:
            from PyQt6.QtGui import QImage
            argb = QImage.Format.Format_ARGB32
        image = QImage(str(source))
        if image.isNull() or image.width()*image.height() > 32000000:
            raise ValueError("Invalid or oversized reference image")
        source_x = integer(p.get("source_x", x), "source_x", 0, image.width()-1)
        source_y = integer(p.get("source_y", y), "source_y", 0, image.height()-1)
        if source_x+width > image.width() or source_y+height > image.height():
            raise ValueError("Patch exceeds reference image")
        patch_image = image.copy(source_x, source_y, width, height).convertToFormat(argb)
        pointer = patch_image.bits()
        try:
            pointer.setsize(width*height*4)
        except AttributeError:
            pass
        after = bytes(pointer[:width*height*4])
        if len(after) != len(before):
            raise RuntimeError("Qt reference pixel size mismatch")
    else:
        raise ValueError("Unsupported pixel transaction")
    identifier = uuid.uuid4().hex
    record = {
        "schema": 1, "id": identifier, "state": "prepared",
        "node_id": str(node.uniqueId().toString()), "rect": [x, y, width, height],
        "document": [doc.name(), doc.fileName(), doc.width(), doc.height(),
                     doc.colorModel(), doc.colorDepth()],
        "before_sha256": _sha(before), "after_sha256": _sha(after),
        "before": _encode(before), "after": _encode(after),
    }
    path = _storage(bridge) / (identifier + ".json")
    _atomic(path, record)  # Rollback bytes durably persisted BEFORE mutation.
    if not node.setPixelData(QByteArray(after), x, y, width, height):
        raise RuntimeError("Krita rejected pixel write; prepared record retained")
    doc.refreshProjection()
    doc.waitForDone()
    record["state"] = "applied"
    _atomic(path, record)
    return {"id": identifier, "state": "applied",
            "before_sha256": record["before_sha256"],
            "after_sha256": record["after_sha256"],
            "native_undo": False}
