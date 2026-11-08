"""Non-destructive, explicitly-approved semantic revision plan.

A revision paints new native strokes on a new editable layer. It never deletes,
merges, overwrites or rewrites original layers and never pastes reference art.
"""
import hashlib
import json
import re
import uuid
from pathlib import Path

from .creative_plans import compile_scene
from .protocol import TaskError, brush_settings, label, number, points
from .scene_v3 import validate_scene, digest
from .scheduler import run as run_longjob

SCHEMA = "krita-agent-creative-revision/1"
SYSTEM = """You are a Krita painting revision planner. You receive an actual
painted PNG image as pixels, an existing semantic object, and a localized
critic finding. Return ONLY JSON of this exact shape:
{"object_id":"existing-id","brush":{"color":"#RRGGBB","size":12,
"opacity":0.8},"elements":[{"kind":"stroke","points":[{"x":1,"y":2,
"pressure":0.5},{"x":3,"y":4,"pressure":0.8}]}]}
Produce multiple deliberate irregular native brush strokes within the requested
region to improve the existing object. Do not alter other regions. No delete,
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
    elements = candidate.get("elements")
    if not isinstance(elements, list) or not 1 <= len(elements) <= 120:
        raise TaskError("Revision requires 1..120 native brush strokes")
    x, y, w, h = issue["region"]
    checked = []
    for item in elements:
        if not isinstance(item, dict) or item.get("kind") != "stroke":
            raise TaskError("Revision only accepts native brush strokes")
        pp = points(item.get("points", []))
        if not all(x <= p["x"] <= x+w and y <= p["y"] <= y+h for p in pp):
            raise TaskError("Revision stroke escaped the approved ROI")
        checked.append({"kind": "stroke", "points": pp, "mode": "auto"})
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
    # Save an immutable recovery point before creating a new revision layer.
    checkpoint = client.request("checkpoint.create")
    if not isinstance(checkpoint, dict) or not checkpoint.get("sha256"):
        raise TaskError("Krita did not confirm the revision checkpoint")
    result = run_longjob(client, {"steps": plan["steps"]}, ledger_directory)
    return {
        "schema": "krita-agent-creative-revision-result/1",
        "state": result["state"],
        "ledger": result["ledger"],
        "checkpoint": checkpoint,
        "revision_sha256": plan["sha256"],
        "original_layers_rewritten": False,
        "error": result.get("error"),
    }
