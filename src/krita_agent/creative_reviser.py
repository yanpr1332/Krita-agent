"""Non-destructive, explicitly-approved semantic revision plan.

A revision paints new native strokes on a new editable layer. It never deletes,
merges, overwrites or rewrites original layers and never pastes reference art.
"""
import hashlib
import math
import json
import re
import uuid
from pathlib import Path

from .creative_plans import compile_scene
from .brush_dynamics import combine_style, pressure_samples, validate_palette
from .strategies_v3 import PRESSURE
from .protocol import TaskError, brush_settings, label, number, points
from .scene_v3 import validate_scene, digest
from .scheduler import run as run_longjob

SCHEMA = "krita-agent-creative-revision/1"
SYSTEM = """You are a Krita painting revision planner. You receive an actual
painted PNG image as pixels, an existing semantic object, and a localized
critic finding. Return ONLY JSON of this exact shape:
{"object_id":"existing-id","brush":{"color":"#RRGGBB","size":12,
"opacity":0.8},"styles":{"wash":{"brush":{"size":35,"opacity":0.4},
"pressure_curve":[[0,0.1],[0.3,0.8],[1,0.2]]}},"elements":[
{"kind":"stroke","style":"wash","points":[{"x":1,"y":2},{"x":3,"y":4}]},
{"kind":"stroke","brush":{"size":4,"color":"#CCCCAA"},"points":[
{"x":1,"y":2,"pressure":0.5},{"x":3,"y":4,"pressure":0.8}]}]}
Produce varied broad wash, mid-scale structure and fine native detail strokes
within the requested region. Use several colors, sizes and pressure behaviors
where the actual pixels call for them, without mechanical repetition. Do not alter other regions. No delete,
merge, image import, pasted image, shell command, code or hidden side effect.
The strokes will be placed on a NEW editable paint layer and require approval.
Do not pretend a plan has already changed the artwork."""


def _sha(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise TaskError("Source PNG missing")
    digest = hashlib.sha256()
    with p.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def plan_revision(scene, critique, artwork_png, object_id, provider):
    scene = validate_scene(scene)
    if not isinstance(critique, dict) or critique.get("schema") != "krita-agent-creative-critique/1":
        raise TaskError("A real critique record is required")
    source_sha = _sha(artwork_png)
    if critique.get("artwork_png_sha256") != source_sha:
        raise TaskError("Critique image does not match source PNG")
    issues = [row for row in critique.get("issues", []) if row["object_id"] == object_id]
    if not issues:
        raise TaskError("No critic issue exists for this object")
    obj = next((o for o in scene["objects"] if o["id"] == object_id), None)
    if obj is None:
        raise TaskError("Unknown revision target object")
    issue = issues[0]
    payload = {
        "object": {"id": obj["id"], "kind": obj["kind"], "bounds": obj["bounds"]},
        "issue": issue,
        "canvas": scene["document"],
        "require_new_layer": True,
    }
    prompt = json.dumps(payload, ensure_ascii=False)
    proposed = provider.complete_json(SYSTEM, prompt, image_paths=[artwork_png])
    return validate_revision(scene, critique, artwork_png, proposed, issue["id"])


def validate_revision(scene, critique, artwork_png, candidate, issue_id):
    scene = validate_scene(scene)
    if not isinstance(critique, dict) or critique.get("schema") != "krita-agent-creative-critique/1":
        raise TaskError("Invalid revision critique")
    source_sha = _sha(artwork_png)
    if critique.get("artwork_png_sha256") != source_sha:
        raise TaskError("Revision is stale relative to the critic image")
    issue = next((row for row in critique.get("issues", []) if row.get("id") == issue_id), None)
    if issue is None or not isinstance(candidate, dict):
        raise TaskError("Invalid revision issue/candidate")
    if candidate.get("object_id") != issue["object_id"]:
        raise TaskError("Revision candidate targets the wrong object")
    brush = brush_settings(candidate.get("brush"))
    if "color" not in brush:
        raise TaskError("Revision requires an explicit brush color")
    palette = validate_palette(candidate.get("styles"))
    elements = candidate.get("elements")
    if not isinstance(elements, list) or not 1 <= len(elements) <= 400:
        raise TaskError("Revision requires 1..400 native brush strokes")
    x, y, w, h = issue["region"]
    target = next((obj for obj in scene["objects"]
                   if obj["id"] == issue["object_id"]), None)
    if target is None:
        raise TaskError("Revision targets an unknown semantic object")
    checked = []
    for item in elements:
        if not isinstance(item, dict) or item.get("kind") != "stroke":
            raise TaskError("Revision only accepts native brush strokes")
        selected = combine_style(palette, item)
        raw_points = item.get("points", [])
        pp = points(raw_points)
        if not all(x <= p["x"] <= x+w and y <= p["y"] <= y+h for p in pp):
            raise TaskError("Revision stroke escaped the approved ROI")
        pp = pressure_samples(raw_points, PRESSURE[target["kind"]], selected)
        stroke = {"kind": "stroke", "points": pp, "mode": "auto"}
        if "brush_category" in selected:
            raise TaskError("Revision requires explicit brush preset, not unreviewed category")
        if "brush" in selected:
            stroke["brush"] = selected["brush"]
        checked.append(stroke)
    suffix = re.sub(r"[^a-zA-Z0-9_-]", "-", issue["id"])[:32]
    name = label("R5 revision " + issue["object_id"] + " " + suffix, "revision layer")
    steps = compile_scene({"layers": [{
        "name": name, "brush": brush, "elements": checked
    }]})
    clean = {
        "schema": SCHEMA,
        "id": uuid.uuid4().hex,
        "source_png_sha256": source_sha,
        "source_scene_sha256": digest(scene),
        "issue_id": issue["id"],
        "object_id": issue["object_id"],
        "region": issue["region"],
        "layer_name": name,
        "steps": steps,
        "approval": "required",
        "non_destructive": "new editable paint layer; original layers untouched",
    }
    clean["sha256"] = digest({k: v for k, v in clean.items() if k != "sha256"})
    return clean


def execute_revision(client, plan, scene, artwork_png, ledger_directory,
                     confirm=False, current_graph_sha256=None):
    """Preflight against live pixels, then execute as one non-replaying job."""
    if confirm is not True:
        raise TaskError("Native revision requires explicit user approval")
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise TaskError("Unrecognized revision plan")
    signature = digest({k: v for k, v in plan.items() if k != "sha256"})
    if signature != plan.get("sha256"):
        raise TaskError("Revision plan was modified")
    if digest(validate_scene(scene)) != plan.get("source_scene_sha256"):
        raise TaskError("Scene changed after revision approval")
    if _sha(artwork_png) != plan.get("source_png_sha256"):
        raise TaskError("Approved source image changed")
    if current_graph_sha256 is not None:
        from .document_graph import fingerprint
        graph = client.request("document.graph")
        if fingerprint(graph) != current_graph_sha256:
            raise TaskError("Live layer graph changed before revision")
    # Capture an actual current full-size export from Krita, without
    # overwriting the source. Never trust a stored preview as live state.
    filename = "r5-preflight/" + uuid.uuid4().hex + ".png"
    live = client.request("document.export", path=filename, overwrite=False)
    from PIL import Image
    with Image.open(live["path"]) as a, Image.open(artwork_png) as b:
        if a.size != b.size or a.convert("RGBA").tobytes() != b.convert("RGBA").tobytes():
            raise TaskError("Live Krita pixels differ from approved baseline")
    # A bounded centerline does not bound the rendered brush footprint.
    x, y, width, height = plan["region"]
    left, top = math.ceil(x), math.ceil(y)
    right, bottom = math.floor(x + width), math.floor(y + height)
    if right <= left or bottom <= top:
        raise TaskError("Revision region contains no full pixels")
    selection = client.request("selection.info")
    if not isinstance(selection, dict) or selection.get("selected") is not False:
        raise TaskError("Clear the active selection before applying a revision")
    clip = {"command": "selection.rectangle", "parameters": {
        "x": left, "y": top, "width": right - left, "height": bottom - top,
    }}
    steps = [clip, *plan["steps"], {"command": "selection.clear", "parameters": {}}]
    # Save an immutable recovery point before creating a new revision layer.
    checkpoint = client.request("checkpoint.create")
    if not isinstance(checkpoint, dict) or not checkpoint.get("sha256"):
        raise TaskError("Krita did not confirm the revision checkpoint")
    result = run_longjob(client, {"steps": steps}, ledger_directory)
    return {
        "schema": "krita-agent-creative-revision-result/1",
        "state": result["state"],
        "ledger": result["ledger"],
        "checkpoint": checkpoint,
        "revision_sha256": plan["sha256"],
        "original_layers_rewritten": False,
        "error": result.get("error"),
    }
