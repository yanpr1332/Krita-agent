"""Multiple documents, non-destructive selections and bounded document crop."""
from krita import Krita, Selection
from .advanced_utils import integer, word
try:
    from PyQt5.QtCore import QByteArray
except ImportError:
    from PyQt6.QtCore import QByteArray

COMMANDS = frozenset((
    "document.list", "document.activate", "document.close", "document.crop",
    "selection.rectangle", "selection.clear", "selection.info",
    "selection.copy", "selection.cut", "selection.paste"
))


def _lookup(app, p):
    documents = list(app.documents())
    if "index" in p:
        return documents[integer(p["index"], "index", 0, len(documents)-1)]
    name = word(p.get("name"), "document name")
    matching = [d for d in documents if d.name() == name]
    if len(matching) != 1:
        raise ValueError("Select a unique document name or index")
    return matching[0]


def execute(bridge, command, p):
    app = Krita.instance()
    if command == "document.list":
        active = app.activeDocument()
        return [{"index": i, "name": d.name(), "width": d.width(), "height": d.height(),
                 "modified": d.modified(), "active": d is active}
                for i, d in enumerate(app.documents())]
    if command == "document.activate":
        document = _lookup(app, p)
        window = app.activeWindow()
        if window is None:
            raise RuntimeError("No active Krita window")
        views = window.views()
        view = next((v for v in views if v.document() is document), None)
        if view is None:
            window.addView(document)
        else:
            window.activateView(view)
        return {"active": document.name()}
    if command == "document.close":
        document = _lookup(app, p)
        if p.get("confirm") is not True:
            raise ValueError("Close requires confirm=true")
        if document.modified():
            raise RuntimeError("Refusing to close an unsaved document")
        if not document.close():
            raise RuntimeError("Krita refused document close")
        return {"closed": True}
    doc = bridge._doc()
    if command == "document.crop":
        if p.get("confirm") is not True:
            raise ValueError("Crop requires confirm=true")
        x = integer(p.get("x"), "x", 0, doc.width()-1)
        y = integer(p.get("y"), "y", 0, doc.height()-1)
        w = integer(p.get("width"), "width", 1, doc.width()-x)
        h = integer(p.get("height"), "height", 1, doc.height()-y)
        doc.crop(x, y, w, h)
        return {"crop": [x, y, w, h]}
    if command == "selection.info":
        selection = doc.selection()
        return {"selected": selection is not None,
                "rect": [selection.x(), selection.y(), selection.width(), selection.height()]
                if selection is not None else None}
    if command == "selection.clear":
        doc.setSelection(None)
        doc.waitForDone()
        return {"cleared": True}
    if command == "selection.rectangle":
        x = integer(p.get("x"), "x", 0, doc.width()-1)
        y = integer(p.get("y"), "y", 0, doc.height()-1)
        w = integer(p.get("width"), "width", 1, doc.width()-x)
        h = integer(p.get("height"), "height", 1, doc.height()-y)
        selection = Selection()
        selection.select(x, y, w, h, integer(p.get("strength", 255), "strength", 0, 255))
        doc.setSelection(selection)
        return {"selection": [x, y, w, h]}
    selection = doc.selection()
    if selection is None:
        raise RuntimeError("No selection")
    node = bridge._node()
    if node.locked() and command != "selection.copy":
        raise ValueError("Target layer locked")
    if doc.colorModel() != "RGBA" or doc.colorDepth() != "U8":
        raise RuntimeError("Selection transfer requires RGBA U8")
    if command in ("selection.copy", "selection.cut"):
        if command == "selection.cut" and p.get("confirm") is not True:
            raise ValueError("Cut requires confirm=true")
        x, y, w, h = selection.x(), selection.y(), selection.width(), selection.height()
        if w < 1 or h < 1 or w*h > 4000000:
            raise ValueError("Selection must contain 1 to 4 million pixels")
        data = bytearray(node.pixelData(x, y, w, h))
        mask = bytes(selection.pixelData(x, y, w, h))
        if len(data) != w*h*4 or len(mask) != w*h:
            raise RuntimeError("Invalid selection pixel buffer")
        for i, coverage in enumerate(mask):
            data[i*4+3] = (data[i*4+3]*coverage+127)//255
        bridge.selection_clip = (w, h, bytes(data))
        if command == "selection.cut":
            selection.cut(node)
            doc.refreshProjection()
            doc.waitForDone()
        return {"copied": True, "cut": command == "selection.cut", "width": w, "height": h}
    if command == "selection.paste":
        clip = getattr(bridge, "selection_clip", None)
        if clip is None:
            raise RuntimeError("Copy or cut a selection in this Bridge session first")
        w, h, source = clip
        x = integer(p.get("x", selection.x()), "x", 0, doc.width()-w)
        y = integer(p.get("y", selection.y()), "y", 0, doc.height()-h)
        target = bytearray(node.pixelData(x, y, w, h))
        for i in range(w*h):
            offset = i*4
            sa, da = source[offset+3], target[offset+3]
            alpha = sa*255 + da*(255-sa)
            for channel in range(3):
                target[offset+channel] = ((source[offset+channel]*sa*255 + target[offset+channel]*da*(255-sa) + alpha//2)//alpha) if alpha else 0
            target[offset+3] = (alpha+127)//255
        if not node.setPixelData(QByteArray(bytes(target)), x, y, w, h):
            raise RuntimeError("Krita refused selection paste")
        doc.refreshProjection()
        doc.waitForDone()
        return {"pasted": [x, y], "width": w, "height": h}
    raise ValueError("Unknown document command")
