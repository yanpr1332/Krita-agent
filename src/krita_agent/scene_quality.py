"""Offline ScenePlan preflight checks; this is not semantic artwork acceptance."""
from collections import Counter

from .scene_v2 import compile_plan


def validate(scene, min_painted_layers=1):
    if type(min_painted_layers) is not int or not 1 <= min_painted_layers <= 64:
        raise ValueError("min_painted_layers must be in [1,64]")
    plan = compile_plan(scene)
    document = scene.get("document") or {}
    width = document.get("width")
    height = document.get("height")
    layers = plan["layers"]
    painted = [layer for layer in layers if layer.get("compiled_elements", 0) > 0]
    commands = Counter(step["command"] for step in plan["steps"])
    stroke_count = 0
    shape_count = 0
    point_count = 0
    out_of_canvas = []
    if width and height:
        def check_point(point, location):
            if not (0 <= point.get("x", -1) <= width and 0 <= point.get("y", -1) <= height):
                out_of_canvas.append(location)
        for index, step in enumerate(plan["steps"]):
            params = step.get("parameters", {})
            if step["command"] == "draw.stroke":
                stroke_count += 1
                points = params.get("points", [])
                point_count += len(points)
                for point_index, point in enumerate(points):
                    check_point(point, "step {} point {}".format(index, point_index))
            elif step["command"] == "draw.shape":
                shape_count += 1
                for point_index, point in enumerate(params.get("points", [])):
                    check_point(point, "step {} point {}".format(index, point_index))
                rect = params.get("rect")
                if rect:
                    x, y, w, h = rect
                    if x < 0 or y < 0 or x + w > width or y + h > height:
                        out_of_canvas.append("step {} rectangle".format(index))
            elif step["command"] == "draw.line":
                stroke_count += 1
                for key in ("x1", "y1", "x2", "y2"):
                    if not 0 <= params.get(key, -1) <= (width if key.startswith("x") else height):
                        out_of_canvas.append("step {} {}".format(index, key))
    else:
        for step in plan["steps"]:
            params = step.get("parameters", {})
            if step["command"] == "draw.stroke":
                stroke_count += 1
                point_count += len(params.get("points", []))
            elif step["command"] == "draw.shape":
                shape_count += 1
            elif step["command"] == "draw.line":
                stroke_count += 1
    errors = []
    warnings = []
    if len(painted) < min_painted_layers:
        errors.append(
            "Only {} layers contain compiled drawing elements; {} required".format(
                len(painted), min_painted_layers
            )
        )
    if stroke_count + shape_count == 0:
        errors.append("Scene contains no native drawing operations")
    if out_of_canvas:
        warnings.append(
            "{} drawing coordinates extend beyond the declared canvas".format(len(out_of_canvas))
        )
    empty = [layer["name"] for layer in layers if layer.get("compiled_elements", 0) == 0]
    if empty:
        warnings.append("Empty/non-drawing layers: " + ", ".join(empty))
    if stroke_count == 0:
        warnings.append("No freeform strokes; scene uses shapes only")
    return {
        "schema": "krita-agent-scene-validation/1",
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "layer_count": len(layers),
            "painted_layer_count": len(painted),
            "stroke_count": stroke_count,
            "shape_count": shape_count,
            "point_count": point_count,
            "command_count": sum(commands.values()),
            "commands": dict(sorted(commands.items())),
            "roles": dict(sorted(Counter(layer["role"] for layer in layers).items())),
            "out_of_canvas_examples": out_of_canvas[:20],
        },
        "plan_sha256": plan["sha256"],
        "side_effects": "none; compile-only preflight",
        "limitation": "Structural checks do not establish visual coherence or artwork acceptance",
    }
