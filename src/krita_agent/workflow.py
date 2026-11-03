"""Safe explicit workflow compiler for existing documents and local revisions."""
import json
from pathlib import Path
from .protocol import TaskError, MAX_STEPS, points, label, compile_task
from .stroke_engine import plan_stroke

# Deliberately exclude save/export overwrites, deletion, remote access and
# arbitrary Python. Dangerous editing operations require direct invocation.
ALLOWED = frozenset((
    "canvas.create", "layer.create", "layer.select", "layer.select_id",
    "layer.rename", "layer.set", "layer.group", "layer.duplicate",
    "layer.move", "layer.tree", "layer.inspect", "layer.list",
    "brush.configure", "brush.list", "brush.inspect",
    "draw.stroke", "draw.line", "draw.shape",
    "image.import", "reference.import",
    "selection.rectangle", "selection.clear", "selection.info",
    "preview.canvas", "preview.layer", "preview.region",
    "document.info", "document.list", "document.save", "document.export"
))
# Queries stay available as direct commands, but have no side effects.
QUERY_ONLY = frozenset((
    "layer.tree", "layer.inspect", "layer.list",
    "brush.list", "brush.inspect", "selection.info",
    "document.info", "document.list"
))


def compile_workflow(spec):
    if not isinstance(spec, dict):
        raise TaskError("Workflow must be a JSON object")
    if "steps" not in spec:
        return compile_task(spec)
    stages = spec["steps"]
    if not isinstance(stages, list) or not 1 <= len(stages) <= MAX_STEPS:
        raise TaskError("Workflow requires 1..400 steps")
    result = []
    for index, step in enumerate(stages):
        if not isinstance(step, dict) or step.get("command") not in ALLOWED:
            raise TaskError("Unsupported workflow step at position " + str(index))
        params = step.get("parameters", {})
        if not isinstance(params, dict):
            raise TaskError("Step parameters must be an object")
        command = step["command"]
        params = dict(params)
        if command == "draw.stroke":
            params["points"] = plan_stroke(params)
            params.pop("spacing", None)
            params.pop("smooth", None)
            params.pop("smoothing_passes", None)
            params.pop("smoothing_strength", None)
            params.pop("spline", None)
            params.pop("samples_per_segment", None)
            params.pop("tension", None)
            if params.get("mode", "auto") not in ("auto", "continuous", "segmented"):
                raise TaskError("Unsupported stroke mode")
        if command in ("document.save", "document.export"):
            if params.get("overwrite", False) is not False:
                raise TaskError("Workflow outputs may not overwrite existing work")
            params["path"] = label(params.get("path"), "output path", 240)
        if command.startswith("preview."):
            params["filename"] = label(params.get("filename", "preview/step-%03d.png" % index),
                                       "preview filename", 240)
        result.append({"command": command, "parameters": params})
    # Bound JSON encoding size before the IPC layer.
    if len(json.dumps(result, allow_nan=False)) > 950000:
        raise TaskError("Workflow exceeds request transport size")
    return result


def load_workflow(filename):
    return compile_workflow(json.loads(Path(filename).read_text(encoding="utf-8")))
