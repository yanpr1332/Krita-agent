"""ScenePlan v3: bounded semantic objects compiled into real Krita native operations.

The model never emits IPC commands, paths, code, plugins or arbitrary API calls.
All actual actions are compiled through the existing ScenePlan v2 allowlist.
"""
import hashlib
import json
import re

from .protocol import TaskError, brush_settings, integer, label, number, points
from .scene_v2 import compile_plan as compile_v2
from .brush_dynamics import combine_style, pressure_samples, validate_palette

SCHEMA = "krita-agent-scene/3"
KINDS = frozenset({
    "sky", "sun", "cloud", "mountain", "forest", "tree", "lake",
    "water", "reflection", "rock", "plant", "flower", "ground",
    "building", "object", "custom"
})
ROLES = {
    "sky": "background", "sun": "highlight", "cloud": "background",
    "mountain": "base_color", "forest": "foreground", "tree": "foreground",
    "lake": "base_color", "water": "base_color", "reflection": "effects",
    "rock": "foreground", "plant": "foreground", "flower": "foreground",
    "ground": "base_color", "building": "base_color", "object": "custom",
    "custom": "custom",
}
PAINT_KINDS = frozenset({"stroke", "bezier"})
ELEMENT_KINDS = frozenset({"stroke", "bezier", "rectangle", "ellipse", "polygon", "path"})
MAX_OBJECTS = 32
MAX_ELEMENTS = 6000


def _box(value, width, height):
    if not isinstance(value, list) or len(value) != 4:
        raise TaskError("object bounds require [x,y,width,height]")
    x, y, w, h = [number(v, "object bound", 0, 8192) for v in value]
    if w <= 0 or h <= 0 or x + w > width or y + h > height:
        raise TaskError("object bounds must remain on the canvas")
    return [x, y, w, h]


def _geometry_element(value, width, height, box, object_kind, palette):
    if not isinstance(value, dict) or value.get("kind") not in ELEMENT_KINDS:
        raise TaskError("Unsupported semantic drawing element")
    kind = value["kind"]
    element = dict(value)
    x, y, w, h = box
    if kind not in PAINT_KINDS and any(k in value for k in (
            "brush", "style", "brush_category", "pressure_curve",
            "pressure_variation", "variation_frequency", "variation_seed",
            "speed_sensitivity", "pressure_interpolation")):
        raise TaskError("Stroke styles require an actual brush stroke")
    selected_style = combine_style(palette, element) if kind in PAINT_KINDS else {}
    if kind in PAINT_KINDS:
        if kind == "bezier":
            controls = element.get("controls")
            if not isinstance(controls, list) or len(controls) != 4:
                raise TaskError("Bezier requires exactly four control points")
            for control in controls:
                if not isinstance(control, (list, tuple)) or len(control) != 2:
                    raise TaskError("Bezier control must contain x,y")
                number(control[0], "bezier x", 0, width)
                number(control[1], "bezier y", 0, height)
            element["samples"] = integer(element.get("samples", 48), "samples", 4, 256)
            for key in ("pressure_curve", "pressure_variation", "variation_frequency",
                        "variation_seed", "speed_sensitivity", "pressure_interpolation"):
                if key in selected_style:
                    element[key] = selected_style[key]
        else:
            raw_points = element.get("points", [])
            coords = points(raw_points)
            if not all(0 <= p["x"] <= width and 0 <= p["y"] <= height for p in coords):
                raise TaskError("Stroke coordinates must be within the canvas")
            from .strategies_v3 import PRESSURE
            element["points"] = pressure_samples(raw_points, PRESSURE[object_kind],
                                                  selected_style)
        if "brush" in selected_style:
            element["brush"] = selected_style["brush"]
        if "brush_category" in selected_style:
            element["brush_category"] = selected_style["brush_category"]
    elif kind in ("rectangle", "ellipse"):
        element["rect"] = _box(element.get("rect"), width, height)
    else:
        coords = points(element.get("points", []))
        if len(coords) < 2 or not all(0 <= p["x"] <= width and 0 <= p["y"] <= height for p in coords):
            raise TaskError("Polygon/path requires valid on-canvas points")
        element["points"] = coords
    # No other element-level command or file path is carried through.
    return {key: element[key] for key in (
        "kind", "points", "controls", "samples", "pressure", "spacing",
        "mode", "rect", "fill", "allow_seams", "brush", "brush_category",
        "pressure_curve", "pressure_variation", "variation_frequency",
        "variation_seed", "speed_sensitivity", "pressure_interpolation",
        "spline", "smooth", "smoothing_passes", "smoothing_strength"
    ) if key in element}


def validate_scene(candidate):
    if not isinstance(candidate, dict) or candidate.get("schema") != SCHEMA:
        raise TaskError("Expected ScenePlan v3")
    doc = candidate.get("document")
    if not isinstance(doc, dict):
        raise TaskError("ScenePlan v3 needs a document")
    width = integer(doc.get("width"), "width", 1, 8192)
    height = integer(doc.get("height"), "height", 1, 8192)
    if width * height > 32000000:
        raise TaskError("Canvas exceeds 32M pixels")
    title = label(doc.get("name", "Creative Workflow"), "document name")
    objects = candidate.get("objects")
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
        raise TaskError("ScenePlan v3 needs 1..32 semantic objects")
    result = []
    ids = set()
    count = 0
    for value in objects:
        if not isinstance(value, dict):
            raise TaskError("Each semantic object must be a JSON object")
        oid = value.get("id")
        if not isinstance(oid, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", oid):
            raise TaskError("Invalid semantic object ID")
        if oid in ids:
            raise TaskError("Duplicate semantic object ID")
        ids.add(oid)
        kind = value.get("kind")
        if kind not in KINDS:
            raise TaskError("Unknown semantic object kind")
        name = label(value.get("name", oid), "object name", 80)
        box = _box(value.get("bounds"), width, height)
        depth = number(value.get("depth", 0.5), "depth", 0, 1)
        brush = brush_settings(value.get("brush", {}))
        palette = validate_palette(value.get("styles"))
        min_strokes = integer(value.get("min_strokes", 1),
                              "minimum object strokes", 1, 900)
        elements = value.get("elements")
        if not isinstance(elements, list) or not 1 <= len(elements) <= 900:
            raise TaskError("Each semantic object needs 1..900 drawing elements")
        compiled = [_geometry_element(e, width, height, box, kind, palette) for e in elements]
        count += len(compiled)
        if count > MAX_ELEMENTS:
            raise TaskError("Scene exceeds 6000 elements")
        actual_strokes = sum(e["kind"] in PAINT_KINDS for e in compiled)
        if actual_strokes < min_strokes:
            raise TaskError("Object needs actual brush strokes: below declared min_strokes budget")
        parent = value.get("parent")
        if parent is not None and not isinstance(parent, str):
            raise TaskError("Parent object ID must be text")
        result.append({
            "id": oid, "name": name, "kind": kind, "bounds": box,
            "depth": depth, "parent": parent, "brush": brush,
            "styles": palette, "min_strokes": min_strokes, "elements": compiled,
        })
    for item in result:
        if item["parent"] is not None and (item["parent"] == item["id"] or item["parent"] not in ids):
            raise TaskError("Invalid parent object reference")
    by_id = {item["id"]: item for item in result}
    for item in result:
        seen = {item["id"]}
        current = item
        while current["parent"] is not None:
            parent = current["parent"]
            if parent in seen:
                raise TaskError("Semantic object parent cycle")
            seen.add(parent)
            current = by_id[parent]
    return {
        "schema": SCHEMA,
        "document": {"width": width, "height": height, "name": title},
        "style": label(candidate.get("style", "illustration"), "style", 160),
        "objects": sorted(result, key=lambda item: (item["depth"], item["id"])),
    }


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def compile_scene_v3(candidate, profile_directory=None, build=None, preview_prefix=None):
    """Compile only to already-whitelisted ScenePlan v2 Krita steps."""
    from .strategies_v3 import brush_for_object, strokes_for_object
    scene = validate_scene(candidate)
    layers = []
    for item in scene["objects"]:
        brush = brush_for_object(item, profile_directory, build)
        elements = strokes_for_object(item, profile_directory, build)
        layers.append({
            "name": item["id"] + " - " + item["name"],
            "role": ROLES[item["kind"]],
            "brush": brush,
            "elements": elements,
            "preview": False,
        })
    plan_v2 = compile_v2({"schema": "krita-agent-scene/2",
                           "document": scene["document"], "layers": layers})
    native_steps = list(plan_v2["steps"])
    stage_paths = []
    if preview_prefix is not None:
        # Unique run-scoped native snapshots. The reference benchmark and
        # actual artwork are not synthesized or inserted as drawing commands.
        if not isinstance(preview_prefix, str) or not re.fullmatch(
            r"r5-runs/[0-9a-f]{32}", preview_prefix
        ):
            raise TaskError("Preview prefix must be a unique run ID")
        from math import sqrt
        width, height = scene["document"]["width"], scene["document"]["height"]
        scale = min(1.0, 2048 / width, 2048 / height,
                    sqrt(2000000 / (width * height)))
        preview_w = max(1, int(width * scale))
        preview_h = max(1, int(height * scale))
        markers = sorted({max(0, (len(layers) + 2)//3-1),
                          max(0, (2*len(layers)+2)//3-1),
                          len(layers)-1})
        step_with_stages = []
        layer_index = -1
        names = ("01-layout.png", "02-color.png", "03-final.png")
        for index, step in enumerate(native_steps):
            if step["command"] == "layer.create":
                layer_index += 1
            step_with_stages.append(step)
            last_step_of_layer = layer_index >= 0 and (
                index + 1 == len(native_steps) or
                native_steps[index+1]["command"] == "layer.create"
            )
            if last_step_of_layer and layer_index in markers:
                label_index = markers.index(layer_index)
                filename = preview_prefix + "/stages/" + names[label_index]
                snapshot = {"command": "preview.canvas", "parameters": {
                    "filename": filename, "width": preview_w, "height": preview_h
                }}
                from .workflow import compile_workflow
                step_with_stages.extend(compile_workflow({"steps": [snapshot]}))
                stage_paths.append(filename)
        native_steps = step_with_stages
    if len(native_steps) > 10000:
        raise TaskError("Scene with stage previews exceeds 10000 native steps")
    from .stroke_quality import analyze_scene
    brush_diagnostics = analyze_scene(scene)
    return {
        "brush_diagnostics": brush_diagnostics,
        "schema": "krita-agent-scene-compiled/3",
        "source_sha256": digest(scene),
        "native_steps_sha256": digest(native_steps),
        "stage_preview_paths": stage_paths,
        "document": scene["document"],
        "objects": [{"id": o["id"], "kind": o["kind"], "name": o["name"],
                     "bounds": o["bounds"], "depth": o["depth"],
                     "layer_name": o["id"] + " - " + o["name"],
                     "elements": len(o["elements"])} for o in scene["objects"]],
        "steps": native_steps,
        "requires_native_approval": True,
        "not_artwork_acceptance": True,
    }
