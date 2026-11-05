"""Tile budget, image-diff ROI planning and pyramid index for big canvases.

Only the matching changed tiles are inspected/modified. A pixel revision
is allowed only where target output alpha is fully opaque; otherwise the
native compositing inverse is not generally defined and we refuse.
"""
import hashlib
import json
import math
from pathlib import Path


def tiles(width, height, tile_size=512, max_total=32768*32768):
    if any(type(x) is not int for x in (width, height, tile_size)):
        raise ValueError("Dimensions must be integers")
    if not (1 <= width <= 32768 and 1 <= height <= 32768
            and 128 <= tile_size <= 1024 and width*height <= max_total):
        raise ValueError("Invalid tile budget")
    return [
        [x, y, min(tile_size, width-x), min(tile_size, height-y)]
        for y in range(0, height, tile_size) for x in range(0, width, tile_size)
    ]


def image_metadata(filename, max_pixels=32000000):
    from PIL import Image
    p = Path(filename).expanduser().resolve()
    with Image.open(p) as im:
        if im.width*im.height > max_pixels:
            raise ValueError("Image exceeds memory budget")
        size = [im.width, im.height]
        mode = im.mode
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(256*1024), b""):
            h.update(block)
    return {"path": str(p), "size": size, "mode": mode, "sha256": h.hexdigest()}


def _rgba_digest(image):
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def plan_overlay(before, target, graph, tile_size=512, max_changed_tiles=128):
    """Plan a safe top-level *overlay*, never direct modification of nested layers.

    No inversion of arbitrary blend modes/masks is attempted. Changed bounding
    boxes (including gaps) must be target-opaque to avoid covering unrelated
    underlying layers with transparency. Every tile stores a preflight hash.
    """
    from PIL import Image, ImageChops
    from .document_graph import fingerprint
    graph_sha = fingerprint(graph)
    a_meta = image_metadata(before)
    b_meta = image_metadata(target)
    if a_meta["size"] != b_meta["size"]:
        raise ValueError("Images have different dimensions")
    if a_meta["size"] != [graph["document"]["width"], graph["document"]["height"]]:
        raise ValueError("Document graph canvas dimensions differ")
    if graph["document"]["model"] != "RGBA" or graph["document"]["depth"] != "U8":
        raise ValueError("Only RGBA U8 document overlays are supported")
    if type(max_changed_tiles) is not int or not 1 <= max_changed_tiles <= 128:
        raise ValueError("max_changed_tiles must be 1..128")
    planned = []
    with Image.open(a_meta["path"]) as image_a, Image.open(b_meta["path"]) as image_b:
        for x,y,w,h in tiles(*a_meta["size"], tile_size):
            box = (x, y, x+w, y+h)
            a, b = image_a.crop(box).convert("RGBA"), image_b.crop(box).convert("RGBA")
            delta = ImageChops.difference(a, b)
            channels = delta.split()
            diff = ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),
                                     ImageChops.lighter(channels[2],channels[3]))
            bounds = diff.getbbox()
            if bounds is None:
                continue
            region = (bounds[0], bounds[1], bounds[2], bounds[3])
            crop = b.crop(region)
            alpha = crop.getchannel("A")
            if alpha.getextrema() != (255,255):
                raise ValueError("Changed region contains translucent target pixels; opaque overlay would not reproduce target")
            bx,by,bx2,by2 = bounds
            rect = [x+bx,y+by,bx2-bx,by2-by]
            if rect[2]*rect[3] > 500000:
                raise ValueError("Changed tile exceeds pixel transaction area")
            planned.append({"rect": rect, "preflight_sha256": _rgba_digest(a),
                            "tile": [x,y,w,h], "target_opaque": True})
            if len(planned) > max_changed_tiles:
                raise ValueError("Too many changed tiles for this revision")
    return {
        "schema": "krita-agent-overlay/1", "source": a_meta,
        "target": b_meta, "graph_sha256": graph_sha,
        "changes": planned, "tile_size": tile_size,
        "status": "no_change" if not planned else "requires_approval",
        "semantics": "top-level opaque overlay, originals untouched; no arbitrary blend inverse"
    }


def write_plan(plan, filename):
    if plan.get("schema") != "krita-agent-overlay/1":
        raise ValueError("Wrong plan type")
    destination = Path(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as file:
        json.dump(plan, file, ensure_ascii=False, indent=2)
    return str(destination)


def pyramid_layout(width, height, tile_size=512):
    """Metadata-only levels: rendering uses Krita per-tile projection."""
    result=[]
    level=0
    while True:
        result.append({"level": level, "width": width, "height": height,
                       "tiles": len(tiles(width,height,tile_size))})
        if max(width,height)<=tile_size:
            return result
        width=max(1,(width+1)//2)
        height=max(1,(height+1)//2)
        level+=1
