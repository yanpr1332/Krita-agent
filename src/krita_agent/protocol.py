"""Pure-Python task validation and compilation; no Krita dependency."""
import math
from pathlib import Path

MAX_POINTS = 2048
MAX_STEPS = 400
MAX_SIZE = 8192
TERMINAL_STATES = frozenset(("completed", "failed", "cancelled"))


class TaskError(ValueError):
    """A task is outside the supported, safe protocol."""


def number(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TaskError(label + " must be numeric")
    value = float(value)
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        raise TaskError(label + " out of range")
    return value


def integer(value, label, low=None, high=None):
    if type(value) is not int or (low is not None and value < low) or (high is not None and value > high):
        raise TaskError(label + " must be an integer in range")
    return value


def label(value, key, limit=120):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(c in value for c in "\r\n\x00"):
        raise TaskError(key + " must be a nonempty, single-line string")
    return value.strip()


def output_name(value, ext):
    value = label(value, "output filename", 240)
    candidate = Path(value)
    if candidate.suffix.lower() != ext:
        raise TaskError("output file must end in " + ext)
    if ".." in candidate.parts:
        raise TaskError("output paths may not traverse parents")
    return str(candidate)


def points(values):
    if not isinstance(values, list) or not (1 <= len(values) <= MAX_POINTS):
        raise TaskError("stroke must contain 1 to 2048 points")
    result = []
    previous_time = -1.0
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise TaskError("point must be an object")
        point = {
            "x": number(value.get("x"), "x", -65536, 65536),
            "y": number(value.get("y"), "y", -65536, 65536),
            "pressure": number(value.get("pressure", 1), "pressure", 0, 1),
            "time_ms": number(value.get("time_ms", index * 16), "time_ms", 0, 3600000),
            "x_tilt": number(value.get("x_tilt", 0), "x_tilt", -90, 90),
            "y_tilt": number(value.get("y_tilt", 0), "y_tilt", -90, 90),
            "rotation": number(value.get("rotation", 0), "rotation", -360, 360),
            "speed": number(value.get("speed", 0), "speed", 0, 1),
            "tangential_pressure": number(value.get("tangential_pressure", 0), "tangential_pressure", 0, 1),
        }
        if point["time_ms"] < previous_time:
            raise TaskError("stroke time must be monotonically nondecreasing")
        previous_time = point["time_ms"]
        result.append(point)
    return result


def brush_settings(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TaskError("brush must be an object")
    result = {}
    if "preset" in value:
        result["preset"] = label(value["preset"], "preset")
    if "size" in value:
        result["size"] = number(value["size"], "brush size", 0.1, 1000)
    if "opacity" in value:
        result["opacity"] = number(value["opacity"], "opacity", 0, 1)
    if "color" in value:
        color = label(value["color"], "color", 9)
        if len(color) != 7 or color[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in color[1:]):
            raise TaskError("color must be #RRGGBB")
        result["color"] = color
    if "pressure_enabled" in value:
        if type(value["pressure_enabled"]) is not bool:
            raise TaskError("pressure_enabled must be boolean")
        result["pressure_enabled"] = value["pressure_enabled"]
    return result


def compile_task(task):
    """Return a validated sequence of whitelisted steps for a fresh canvas."""
    if not isinstance(task, dict):
        raise TaskError("task must be a JSON object")
    doc = task.get("document")
    if not isinstance(doc, dict):
        raise TaskError("document object is required")
    width = integer(doc.get("width"), "width", 1, MAX_SIZE)
    height = integer(doc.get("height"), "height", 1, MAX_SIZE)
    if width * height > 32000000:
        raise TaskError("canvas area exceeds 32 million pixels")
    commands = [{"command": "canvas.create", "parameters": {
        "width": width, "height": height, "name": label(doc.get("name", "Krita Agent"), "document name")}}]
    top_brush = brush_settings(task.get("brush"))
    layers = task.get("layers")
    if layers is None:
        layers = [{"name": task.get("layer", "Line Art"), "strokes": task.get("strokes", [])}]
    if not isinstance(layers, list) or not 1 <= len(layers) <= 64:
        raise TaskError("layers must have 1 to 64 entries")
    for layer in layers:
        if not isinstance(layer, dict):
            raise TaskError("layer must be an object")
        name = label(layer.get("name"), "layer name")
        commands.append({"command": "layer.create", "parameters": {"name": name}})
        settings = dict(top_brush)
        settings.update(brush_settings(layer.get("brush")))
        if settings:
            commands.append({"command": "brush.configure", "parameters": settings})
        strokes = layer.get("strokes", [])
        if not isinstance(strokes, list):
            raise TaskError("strokes must be an array")
        for stroke in strokes:
            if not isinstance(stroke, dict):
                raise TaskError("stroke must be an object")
            if "points" in stroke and "shape" not in stroke:
                mode = stroke.get("mode", "auto")
                if mode not in ("auto", "segmented", "continuous"):
                    raise TaskError("invalid stroke mode")
                if any(key in stroke for key in ("spline", "smooth", "spacing")):
                    from .stroke_engine import plan_stroke
                    sample = plan_stroke(stroke)
                else:
                    sample = points(stroke["points"])
                commands.append({"command": "draw.stroke", "parameters": {"points": sample, "mode": mode}})
            else:
                shape = stroke.get("shape")
                if shape not in ("rectangle", "ellipse", "polygon", "path"):
                    raise TaskError("stroke requires points or recognized shape")
                params = {"shape": shape}
                if shape in ("rectangle", "ellipse"):
                    rect = stroke.get("rect")
                    if not isinstance(rect, list) or len(rect) != 4:
                        raise TaskError("rect requires four numbers")
                    params["rect"] = [number(x, "rect", -65536, 65536) for x in rect]
                    if params["rect"][2] <= 0 or params["rect"][3] <= 0:
                        raise TaskError("rectangle dimensions must be positive")
                elif shape == "polygon":
                    poly = points(stroke.get("points", []))
                    if len(poly) < 3:
                        raise TaskError("polygon requires 3+ points")
                    params["points"] = [{"x": x["x"], "y": x["y"]} for x in poly]
                else:
                    poly = points(stroke.get("points", []))
                    if len(poly) < 2:
                        raise TaskError("path requires 2+ points")
                    params["points"] = [{"x": x["x"], "y": x["y"]} for x in poly]
                params["fill"] = stroke.get("fill", "None")
                if params["fill"] not in ("None", "ForegroundColor", "BackgroundColor"):
                    raise TaskError("invalid fill style")
                commands.append({"command": "draw.shape", "parameters": params})
            if len(commands) > MAX_STEPS:
                raise TaskError("too many steps")
    output = task.get("output", {})
    if not isinstance(output, dict):
        raise TaskError("output must be an object")
    if "kra" in output:
        commands.append({"command": "document.save", "parameters": {
            "path": output_name(output["kra"], ".kra"), "overwrite": False}})
    if "png" in output or "preview" in output:
        commands.append({"command": "document.export", "parameters": {
            "path": output_name(output.get("png", output.get("preview")), ".png"), "overwrite": False}})
    if len(commands) > MAX_STEPS:
        raise TaskError("too many steps")
    return commands
