"""Multiple documents, non-destructive selections and bounded document crop."""
from krita import Krita, Selection
from .advanced_utils import integer, word

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
        doc.setSelection(Selection())
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
    if command == "selection.copy":
        selection.copy(node)
        return {"copied": True}
    if command == "selection.cut":
        if p.get("confirm") is not True:
            raise ValueError("Cut requires confirm=true")
        selection.cut(node)
        return {"cut": True}
    if command == "selection.paste":
        x = integer(p.get("x", selection.x()), "x", -32768, 32768)
        y = integer(p.get("y", selection.y()), "y", -32768, 32768)
        selection.paste(node, x, y)
        return {"pasted": [x, y]}
    raise ValueError("Unknown document command")
