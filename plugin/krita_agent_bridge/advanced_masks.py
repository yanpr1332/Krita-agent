"""Native non-destructive masks and filter layers; actual behavior is build-dependent."""
from krita import Krita, Selection
from .advanced_utils import find_node, integer, word

COMMANDS = frozenset(("mask.create", "mask.inspect", "mask.selection.set",
                      "filter.list", "filter.layer.create", "filter.mask.create",
                      "filter.configure"))
MASK_TYPES = {"transparency": "transparencymask", "selection": "selectionmask"}


def _new(doc, kind, name):
    preferred = {"transparency": "createTransparencyMask", "selection": "createSelectionMask"}[kind]
    factory = getattr(doc, preferred, None)
    node = factory(name) if callable(factory) else doc.createNode(name, MASK_TYPES[kind])
    if node is None or node.type() != MASK_TYPES[kind]:
        raise RuntimeError("Installed Krita build cannot create this mask")
    return node


def _filter(app, name):
    name = word(name, "filter name", 90)
    available = app.filters()
    if name not in available:
        raise ValueError("Filter not available on installed Krita build")
    instance = app.filter(name)
    if instance is None:
        raise RuntimeError("Krita refused filter")
    return instance


def execute(bridge, command, p):
    app = Krita.instance()
    if command == "filter.list":
        return {"filters": sorted(app.filters())[:300]}
    doc = bridge._doc()
    if command == "mask.inspect":
        node = find_node(doc, p)
        if node.type() not in ("transparencymask", "selectionmask", "filtermask"):
            raise ValueError("Specified layer is not a supported mask")
        return {"id": str(node.uniqueId().toString()), "type": node.type(),
                "name": node.name(), "parent": node.parentNode().name(),
                "visible": node.visible(), "locked": node.locked()}
    if command == "mask.create":
        kind = p.get("kind")
        if kind not in MASK_TYPES:
            raise ValueError("Mask kind must be transparency or selection")
        parent = find_node(doc, {"id": p.get("parent_id")} if p.get("parent_id")
                           else {"name": p.get("parent_name")})
        if parent.locked() or parent.type() in ("transparencymask", "selectionmask", "filtermask"):
            raise ValueError("Mask parent is locked or is a mask")
        mask = _new(doc, kind, word(p.get("name"), "mask name"))
        if kind == "transparency":
            selection = doc.selection()
            if selection is None:
                if p.get("require_selection", True) is not False:
                    raise ValueError("A selection is required for transparency mask creation")
                selection = Selection()
                selection.select(0, 0, doc.width(), doc.height(), 255)
            mask.setSelection(selection.duplicate())
        if not parent.addChildNode(mask, None):
            raise RuntimeError("Could not attach mask")
        doc.refreshProjection()
        return {"id": str(mask.uniqueId().toString()), "type": mask.type(),
                "parent": parent.name()}
    if command == "mask.selection.set":
        mask = find_node(doc, p)
        if mask.type() not in ("transparencymask", "selectionmask"):
            raise ValueError("Selection can only be set on supported selection masks")
        if mask.locked():
            raise ValueError("Mask locked")
        selection = doc.selection()
        if selection is None:
            raise ValueError("An active selection is required")
        mask.setSelection(selection.duplicate())
        doc.refreshProjection()
        return {"mask": mask.name(), "selection_applied": True}
    if command in ("filter.layer.create", "filter.mask.create"):
        if p.get("confirm") is not True:
            raise ValueError("Explicit confirm=true required for a filter layer/mask")
        filter_obj = _filter(app, p.get("filter"))
        name = word(p.get("name"), "filter layer name")
        if command == "filter.layer.create":
            selection = doc.selection() or Selection()
            if doc.selection() is None:
                selection.select(0, 0, doc.width(), doc.height(), 255)
            layer = doc.createFilterLayer(name, filter_obj, selection)
            parent = doc.rootNode()
        else:
            parent = find_node(doc, {"id": p.get("parent_id")} if p.get("parent_id")
                               else {"name": p.get("parent_name")})
            if parent.locked():
                raise ValueError("Cannot attach filter mask to locked parent")
            layer = doc.createFilterMask(name, filter_obj, parent)
        if layer is None or not parent.addChildNode(layer, None):
            raise RuntimeError("Krita rejected non-destructive filter insertion")
        doc.refreshProjection()
        return {"id": str(layer.uniqueId().toString()), "type": layer.type(),
                "filter": filter_obj.name()}
    if command == "filter.configure":
        if p.get("confirm") is not True:
            raise ValueError("Filter configuration requires confirm=true")
        node = find_node(doc, p)
        if node.type() not in ("filterlayer", "filtermask") or node.locked():
            raise ValueError("Target must be an unlocked filter layer or mask")
        settings = p.get("properties")
        if not isinstance(settings, dict) or not 1 <= len(settings) <= 24:
            raise ValueError("Provide 1..24 filter configuration properties")
        for key, val in settings.items():
            word(key, "filter property", 80)
            if type(val) not in (str, int, float, bool) or (isinstance(val, str) and len(val) > 200):
                raise ValueError("Filter setting must be a bounded scalar value")
        filter_obj = node.filter()
        info = filter_obj.configuration()
        for key, val in settings.items():
            info.setProperty(key, val)
        filter_obj.setConfiguration(info)
        node.setFilter(filter_obj)
        doc.refreshProjection()
        return {"id": str(node.uniqueId().toString()), "configured": list(settings),
                "notice": "Visual filter result must be verified on the installed build"}
    raise ValueError("Unsupported mask/filter command")
