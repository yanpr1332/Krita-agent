"""Structured geometry-to-Krita plans, deterministic and human-reviewable."""
from .geometry import cubic_bezier
from .protocol import TaskError, label, number, points
from .stroke_engine import plan_stroke
from .workflow import compile_workflow

SHAPES = {"rectangle", "ellipse", "polygon", "path"}


def compile_scene(scene):
    """Build layers and brush strokes from a constrained scene description.

    This is a structured planner, not an image generation or natural-language
    understanding model. It does not synthesize brush presets or hidden assets.
    """
    if not isinstance(scene, dict):
        raise TaskError("scene must be a JSON object")
    layers = scene.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 32:
        raise TaskError("scene layers require 1..32 objects")
    stages = []
    if "document" in scene:
        d = scene["document"]
        if not isinstance(d, dict) or type(d.get("width")) is not int or type(d.get("height")) is not int:
            raise TaskError("scene document requires integer width/height")
        if not (1 <= d["width"] <= 8192 and 1 <= d["height"] <= 8192
                and d["width"]*d["height"] <= 32000000):
            raise TaskError("scene canvas exceeds bounds")
        stages.append({"command": "canvas.create", "parameters": {
            "width": d["width"], "height": d["height"],
            "name": label(d.get("name", "Planned Scene"), "document name")}})
    for layer in layers:
        if not isinstance(layer, dict):
            raise TaskError("layer must be an object")
        stages.append({"command": "layer.create", "parameters": {
            "name": label(layer.get("name"), "layer name")}})
        if "brush" in layer:
            from .protocol import brush_settings
            stages.append({"command": "brush.configure", "parameters": brush_settings(layer["brush"])})
        elements = layer.get("elements", [])
        if not isinstance(elements, list):
            raise TaskError("elements must be a list")
        for element in elements:
            if not isinstance(element, dict):
                raise TaskError("element must be an object")
            kind = element.get("kind")
            if kind == "bezier":
                controls = element.get("controls", [])
                if not isinstance(controls, list) or len(controls) != 4:
                    raise TaskError("bezier expects four control points")
                points_list = cubic_bezier(*controls,
                                           count=element.get("samples", 48),
                                           pressure=element.get("pressure", (.1, .85, .1)))
                spec = {"points": points_list, "spacing": element.get("spacing", 4.0)}
                stages.append({"command": "draw.stroke", "parameters": {"points": plan_stroke(spec),
                                "mode": element.get("mode", "auto")}})
            elif kind == "stroke":
                stages.append({"command": "draw.stroke", "parameters": {
                    "points": plan_stroke(element), "mode": element.get("mode", "auto")}})
            elif kind in SHAPES:
                params = {"shape": kind, "fill": element.get("fill", "None")}
                if kind in ("rectangle", "ellipse"):
                    rect = element.get("rect")
                    if not isinstance(rect, list) or len(rect) != 4 or any(
                            type(v) not in (int, float) for v in rect):
                        raise TaskError("shape rect expects four numbers")
                    params["rect"] = [number(v, "rect", -65536, 65536) for v in rect]
                else:
                    params["points"] = points(element.get("points", []))
                stages.append({"command": "draw.shape", "parameters": params})
            else:
                raise TaskError("Unsupported scene element kind")
        if layer.get("preview", False):
            stages.append({"command": "preview.canvas", "parameters": {
                "filename": "previews/scene-" + str(len(stages)) + ".png"}})
    if scene.get("checkpoint", False):
        stages.append({"command": "checkpoint.create", "parameters": {}})
    return compile_workflow({"steps": stages})
