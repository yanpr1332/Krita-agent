"""Color model and ICC information, with backup-gated explicit conversions."""
from krita import Krita
from .advanced_utils import word

COMMANDS = frozenset(("color.info", "color.profiles", "color.convert"))
DEPTHS = {"U8", "U16", "F16", "F32"}
MODELS = {"RGBA", "CMYKA", "GRAYA", "LABA", "XYZA", "YCbCrA"}


def _info(doc):
    active = doc.activeNode()
    return {
        "document": doc.name(), "model": doc.colorModel(),
        "depth": doc.colorDepth(), "profile": doc.colorProfile(),
        "writable_rgba_u8_pixel_api": doc.colorModel() == "RGBA" and doc.colorDepth() == "U8",
        "active_layer": {"name": active.name(), "model": active.colorModel(),
                         "depth": active.colorDepth(), "profile": active.colorProfile()}
        if active is not None else None,
    }


def execute(bridge, command, p):
    doc = bridge._doc()
    if command == "color.info":
        return _info(doc)
    if command == "color.profiles":
        app = Krita.instance()
        model = word(p.get("model", doc.colorModel()), "model", 24)
        depth = word(p.get("depth", doc.colorDepth()), "depth", 10)
        if model not in MODELS or depth not in DEPTHS:
            raise ValueError("Unsupported model or depth")
        profiles_fn = getattr(app, "profiles", None)
        if not callable(profiles_fn):
            return {"model": model, "depth": depth,
                    "supported": False, "profiles": []}
        return {"model": model, "depth": depth, "supported": True,
                "profiles": list(profiles_fn(model, depth))[:300]}
    if command == "color.convert":
        model = word(p.get("model"), "model", 24)
        depth = word(p.get("depth"), "depth", 10)
        profile = word(p.get("profile"), "profile", 240)
        if model not in MODELS or depth not in DEPTHS:
            raise ValueError("Unknown color space")
        before = _info(doc)
        proposal = {"before": before, "target": {"model": model, "depth": depth, "profile": profile}}
        if p.get("confirm") is not True:
            return {"dry_run": True, **proposal, "requires": "confirm=true and verified checkpoint id"}
        from .checkpoints import _manifest
        record = _manifest(bridge, p.get("checkpoint_id"))
        if record["document_name"] != doc.name() or record["path"] != doc.fileName():
            raise ValueError("Current document is not the freshly saved checkpoint")
        if doc.modified() or (doc.width(), doc.height()) != (record["width"], record["height"]):
            raise ValueError("Document modified since checkpoint: refuse color conversion")
        if (doc.colorModel(), doc.colorDepth(), doc.colorProfile()) != (
                record["color_model"], record["color_depth"], record["color_profile"]):
            raise ValueError("Color state differs from checkpoint")
        if not doc.setColorSpace(model, depth, profile):
            raise RuntimeError("Krita rejected color conversion; backup checkpoint remains intact")
        doc.refreshProjection()
        doc.waitForDone()
        return {"converted": True, "before": before, "after": _info(doc),
                "backup_checkpoint": record["id"],
                "notice": "This does not establish colorimetric accuracy for arbitrary ICC workflows"}
    raise ValueError("Unknown color operation")
