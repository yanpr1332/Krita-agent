"""Deterministic, auditable image revision planning; no generative-model calls.

Plans replace only a bounded changed rectangle on a duplicate paint layer.
They cannot change the user's existing layer in place. Their expected source
image must match a fresh Krita projection before execution is allowed.
"""
import hashlib
import json
import os
import uuid
from pathlib import Path

from .protocol import TaskError


def _images(before, target):
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Revision planning requires pip install -e '.[feedback]'") from exc
    with Image.open(before) as a, Image.open(target) as b:
        if a.width*a.height > 2000000 or a.size != b.size:
            raise TaskError("Both reference images must match, with area <= 2 million pixels")
        return a.convert("RGBA"), b.convert("RGBA")


def _rgba_sha(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def _file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(262144), b""):
            h.update(b)
    return h.hexdigest()


def propose(before, target, layer_id, threshold=2, region=None, max_patch_area=500000):
    """Locate changed pixels and produce a manual-approval-only patch plan."""
    from PIL import ImageChops
    before = Path(before).expanduser().resolve()
    target = Path(target).expanduser().resolve()
    old, goal = _images(before, target)
    if not isinstance(layer_id, str) or not layer_id.strip() or len(layer_id) > 120:
        raise TaskError("An explicit source paint-layer ID is required")
    if type(threshold) is not int or not 0 <= threshold <= 254:
        raise TaskError("threshold must be integer 0..254")
    if type(max_patch_area) is not int or not 1 <= max_patch_area <= 500000:
        raise TaskError("max_patch_area must be 1..500000")
    if region is not None:
        if not isinstance(region, (list, tuple)) or len(region) != 4 or any(type(v) is not int for v in region):
            raise TaskError("region requires [x,y,w,h] integers")
        x, y, w, h = region
        if x < 0 or y < 0 or w < 1 or h < 1 or x+w > old.width or y+h > old.height:
            raise TaskError("region is outside source image")
        crop_box = (x, y, x+w, y+h)
        left, top = x, y
        a, b = old.crop(crop_box), goal.crop(crop_box)
    else:
        a, b = old, goal
        left = top = 0
    channel_diffs = ImageChops.difference(a, b).split()
    mask = channel_diffs[0]
    for c in channel_diffs[1:]:
        mask = ImageChops.lighter(mask, c)
    mask = mask.point(lambda value: 255 if value > threshold else 0)
    local = mask.getbbox()
    rect = ([left+local[0], top+local[1], local[2]-local[0], local[3]-local[1]]
            if local else None)
    if rect and rect[2]*rect[3] > max_patch_area:
        raise TaskError("Patch area exceeds max_patch_area; specify a smaller region")
    return {
        "schema": "krita-agent-revision/1", "id": uuid.uuid4().hex,
        "status": "patch_required" if rect else "no_change",
        "before_file": str(before), "target_file": str(target),
        "target_file_sha256": _file_sha(target), "before_rgba_sha256": _rgba_sha(old),
        "target_rgba_sha256": _rgba_sha(goal), "size": [old.width, old.height],
        "layer_id": layer_id.strip(), "rect": rect, "threshold": threshold,
        "region_constraint": list(region) if region is not None else None,
        "safety": "Requires explicit confirmation, exact baseline projection, sole visible normal paint layer and a fresh checkpoint",
    }


def write_plan(plan, filename):
    target = Path(filename).expanduser()
    if target.exists():
        raise FileExistsError("Refusing to overwrite existing revision plan")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return str(target)


def load_plan(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema") != "krita-agent-revision/1":
        raise TaskError("Unrecognized revision plan schema")
    if obj.get("status") != "patch_required":
        raise TaskError("Revision plan contains no change to apply")
    region = obj.get("rect")
    if not isinstance(region, list) or len(region) != 4 or any(type(x) is not int for x in region):
        raise TaskError("Revision rectangle invalid")
    if region[2]*region[3] > 500000 or min(region[2:]) < 1:
        raise TaskError("Revision area exceeds maximum")
    return obj


def _same_image(path, digest, expected_size):
    with_size = _images(path, path)[0]
    if list(with_size.size) != expected_size or _rgba_sha(with_size) != digest:
        raise TaskError("Live Krita projection differs from approved revision baseline")


def apply(client, plan, confirm=False, wait=True):
    """Explicit, one-shot local plan application. Never automatically retries."""
    if confirm is not True:
        raise TaskError("Revision apply requires explicit --confirm")
    if plan.get("status") == "no_change":
        return {"status": "no_change", "mutated": False}
    if plan.get("schema") != "krita-agent-revision/1" or plan.get("status") != "patch_required":
        raise TaskError("Unrecognized revision plan")
    try:
        uuid.UUID(plan["id"])
        x, y, w, h = plan["rect"]
        width, height = plan["size"]
        if any(type(n) is not int for n in (x, y, w, h, width, height)) or min(x, y) < 0 or min(w, h) < 1 or w*h > 500000 or x+w > width or y+h > height:
            raise ValueError("bounds")
    except (KeyError, TypeError, ValueError):
        raise TaskError("Invalid revision identity or rectangle")
    if _file_sha(plan["target_file"]) != plan["target_file_sha256"]:
        raise TaskError("Target reference was modified after plan approval")
    status = client.request("status")
    source_root = Path(status["input_dir"]).resolve()
    source_file = Path(plan["target_file"]).resolve()
    if source_file != source_root and source_root not in source_file.parents:
        raise TaskError("Revision target must reside in the Bridge authorized input directory")
    doc = client.request("document.info")
    info = client.request("color.info")
    if [doc["width"], doc["height"]] != plan["size"]:
        raise TaskError("Krita document dimensions do not match plan")
    if info["model"] != "RGBA" or info["depth"] != "U8":
        raise TaskError("Pixel revision currently requires RGBA U8")
    tree = client.request("layer.tree")
    visible = [layer for layer in tree if layer["visible"] and layer["type"] == "paintlayer"]
    if len(visible) != 1 or visible[0]["id"] != plan["layer_id"]:
        raise TaskError("Safe revision requires exactly one visible source paint layer")
    if any(layer["visible"] and layer["type"] not in ("paintlayer",) for layer in tree):
        raise TaskError("Safe revision does not support visible groups, masks, or file/filter layers")
    source = visible[0]
    if source.get("locked") or source.get("blending_mode") != "normal" or source.get("opacity") != 1.0:
        raise TaskError("Source paint layer must be unlocked, normal blend, 100% opacity")
    # Capture Krita's full-canvas projection; digest a decoded RGBA image.
    inspection_name = "previews/revision-preflight-" + uuid.uuid4().hex + ".png"
    preview = client.request("preview.canvas", filename=inspection_name,
                             width=plan["size"][0], height=plan["size"][1])
    _same_image(preview["path"], plan["before_rgba_sha256"], plan["size"])
    # The snapshot is created BEFORE altering any layer; it remains immutable.
    checkpoint = client.request(
        "checkpoint.create",
        path="checkpoints/revision-before-" + plan["id"] + ".kra")
    new_layer = "Revision-" + plan["id"][:12]
    x, y, w, h = plan["rect"]
    steps = [
        {"command": "layer.duplicate", "parameters": {"id": plan["layer_id"], "new_name": new_layer}},
        {"command": "pixel.transaction.patch", "parameters": {
            "name": new_layer, "path": plan["target_file"],
            "x": x, "y": y, "width": w, "height": h, "source_x": x, "source_y": y,
            "confirm": True}},
        {"command": "layer.set", "parameters": {"id": plan["layer_id"], "properties": {"visible": False}}},
        {"command": "preview.canvas", "parameters": {
            "filename": "previews/revision-after-" + plan["id"] + ".png",
            "width": plan["size"][0], "height": plan["size"][1]}},
        {"command": "document.save", "parameters": {
            "path": "revisions/revision-" + plan["id"] + ".kra", "overwrite": False}},
    ]
    job = client.submit(steps)
    result = {"job": job, "checkpoint": checkpoint,
              "output_png": "previews/revision-after-" + plan["id"] + ".png"}
    if not wait:
        return result
    import time
    for _ in range(1200):
        state = client.request("job.status", id=job["id"])
        if state["state"] in ("completed", "failed", "cancelled", "interrupted"):
            result["terminal"] = state
            if state["state"] == "completed":
                from .feedback import compare
                # Using normalized pixel statistics rather than file byte equality.
                after_path = (Path(checkpoint["path"]).resolve().parent.parent
                              / result["output_png"])
                if after_path.is_file():
                    result["feedback"] = compare(plan["target_file"], after_path)
                    with _images(after_path, after_path)[0] as final_image:
                        result["goal_rgba_match"] = (
                            _rgba_sha(final_image) == plan["target_rgba_sha256"])
                else:
                    result["feedback"] = {"status": "missing_preview",
                                          "note": "The job finished but preview file was not found"}
            return result
        time.sleep(.25)
    result["terminal"] = {"state": "unknown", "error": "Polling deadline exceeded; inspect job manually"}
    return result
