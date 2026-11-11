"""ScenePlan v4: generalist subjects, stages, paint intents and safe v3 lowering.

There is deliberately no finite "landscape object kind" ontology here.
The model plans purpose and geometry; this compiler owns bounded native marks.
Legacy ScenePlan v3 is kept intact and remains independently usable.
"""
import math
import re

from .brush_dynamics import combine_style, validate_palette
from .intent_strokes_v4 import expand_intent
from .protocol import TaskError, brush_settings, integer, label, number
from .scene_v3 import compile_scene_v3, digest, validate_scene
from .workflow import compile_workflow

SCHEMA = "krita-agent-scene/4"
PHASES = ("sketch", "block_in", "form", "material", "detail", "polish")
ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,23}\Z")
MAX_SUBJECTS = 24
MAX_GROUPS = 32
MAX_TOTAL_INTENTS = 192


def _mapping(raw, allowed, name):
    if not isinstance(raw, dict):
        raise TaskError(name + " must be an object")
    extras = set(raw)-set(allowed)
    if extras:
        raise TaskError(name + " has unsupported fields: " + ", ".join(sorted(extras)))
    return raw


def _id(raw, name):
    if not isinstance(raw, str) or not ID_RE.fullmatch(raw):
        raise TaskError("Invalid " + name)
    return raw


def _bounds(raw, width, height):
    if not isinstance(raw, list) or len(raw) != 4:
        raise TaskError("Subject bounds must be [x,y,width,height]")
    x, y, w, h = [number(v, "subject bound", 0, 8192) for v in raw]
    if w <= 0 or h <= 0 or x+w > width or y+h > height:
        raise TaskError("Subject bounds must stay on the canvas")
    return [x, y, w, h]


def _path(raw, subject, min_points=2, max_points=128):
    if not isinstance(raw, list) or not min_points <= len(raw) <= max_points:
        raise TaskError("Paint path point count outside bounds")
    x, y, w, h = subject["bounds"]
    result = []
    for source in raw:
        if not isinstance(source, list) or len(source) != 2:
            raise TaskError("Paint path coordinates must be [x,y]")
        px = number(source[0], "paint x", x, x+w)
        py = number(source[1], "paint y", y, y+h)
        result.append([px, py])
    if any(a == b for a, b in zip(result, result[1:])):
        raise TaskError("Paint path has duplicate consecutive points")
    return result


def _polygon(raw, subject):
    vertices = _path(raw, subject, 3, 32)
    area = sum(a[0]*b[1]-a[1]*b[0]
               for a, b in zip(vertices, vertices[1:]+vertices[:1]))/2
    if abs(area) < 1:
        raise TaskError("Coverage polygon has zero or negligible area")
    edges = list(zip(vertices, vertices[1:]+vertices[:1]))
    def orientation(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for i, (a,b) in enumerate(edges):
        for j, (c,d) in enumerate(edges):
            if j <= i or j == i+1 or (i == 0 and j == len(edges)-1):
                continue
            q1, q2 = orientation(a,b,c), orientation(a,b,d)
            q3, q4 = orientation(c,d,a), orientation(c,d,b)
            if q1*q2 <= 0 and q3*q4 <= 0:
                raise TaskError("Coverage polygon is self-intersecting or touching")
    return vertices


def validate_scene_v4(candidate):
    if not isinstance(candidate, dict) or candidate.get("schema") != SCHEMA:
        raise TaskError("Expected ScenePlan v4")
    _mapping(candidate, ("schema", "document", "style", "subjects", "stages"),
             "ScenePlan v4")
    doc = _mapping(candidate.get("document"), ("width", "height", "name"), "document")
    width = integer(doc.get("width"), "width", 1, 8192)
    height = integer(doc.get("height"), "height", 1, 8192)
    if width*height > 32000000:
        raise TaskError("Canvas exceeds 32 million pixels")
    document = {"width": width, "height": height,
                "name": label(doc.get("name", "Generalist Study"), "document name")}
    raw_subjects = candidate.get("subjects")
    if not isinstance(raw_subjects, list) or not 1 <= len(raw_subjects) <= MAX_SUBJECTS:
        raise TaskError("ScenePlan v4 requires 1..24 subjects")
    subjects = []
    ids = set()
    for raw in raw_subjects:
        _mapping(raw, ("id", "name", "kind", "material", "materials", "parent",
                       "bounds", "depth", "brush", "styles"), "subject")
        ident = _id(raw.get("id"), "subject ID")
        if ident in ids:
            raise TaskError("Duplicate subject ID")
        ids.add(ident)
        brush = brush_settings(raw.get("brush"))
        if "size" not in brush or "color" not in brush:
            raise TaskError("Each subject needs explicit baseline size and color")
        materials = raw.get("materials", [raw.get("material", "paint")])
        if not isinstance(materials, list) or not 1 <= len(materials) <= 12:
            raise TaskError("Subject materials require 1..12 entries")
        material_names = [label(x, "material", 64) for x in materials]
        if len(set(material_names)) != len(material_names):
            raise TaskError("Duplicate subject material")
        parent = raw.get("parent")
        if parent is not None:
            parent = _id(parent, "parent ID")
        subjects.append({
            "id": ident, "name": label(raw.get("name", ident), "subject name", 80),
            "kind": label(raw.get("kind"), "generic subject kind", 64),
            "materials": material_names, "parent": parent,
            "bounds": _bounds(raw.get("bounds"), width, height),
            "depth": number(raw.get("depth", 0.5), "depth", 0, 1),
            "brush": brush, "styles": validate_palette(raw.get("styles")),
        })
    by_id = {s["id"]: s for s in subjects}
    for subject in subjects:
        seen = {subject["id"]}
        current = subject
        while current["parent"] is not None:
            parent = current["parent"]
            if parent not in by_id or parent in seen:
                raise TaskError("Invalid or cyclic subject hierarchy")
            seen.add(parent)
            current = by_id[parent]
    raw_stages = candidate.get("stages")
    if not isinstance(raw_stages, list) or not 3 <= len(raw_stages) <= 6:
        raise TaskError("ScenePlan v4 requires 3..6 reviewable painting stages")
    stages = []
    phase_seen = set()
    last_phase = -1
    total_intents = 0
    for raw in raw_stages:
        _mapping(raw, ("id", "phase", "goal", "intents"), "stage")
        ident = _id(raw.get("id"), "stage ID")
        phase = raw.get("phase")
        if ident in phase_seen or phase not in PHASES:
            raise TaskError("Duplicate stage or unknown painting phase")
        idx = PHASES.index(phase)
        if idx <= last_phase:
            raise TaskError("Painting phases must advance in order")
        phase_seen.add(ident)
        last_phase = idx
        raw_intents = raw.get("intents")
        if not isinstance(raw_intents, list) or not 1 <= len(raw_intents) <= 32:
            raise TaskError("Each stage needs 1..32 paint intents")
        intents = []
        intent_ids = set()
        for item in raw_intents:
            _mapping(item, ("id", "subject_id", "kind", "purpose", "material",
                            "style", "brush", "brush_category",
                            "pressure_curve", "pressure_variation",
                            "variation_frequency", "variation_seed",
                            "speed_sensitivity", "pressure_interpolation",
                            "path", "polygon", "spacing", "angle",
                            "jitter", "seed", "count", "length"), "paint intent")
            iid = _id(item.get("id"), "paint-intent ID")
            sid = _id(item.get("subject_id"), "intent subject ID")
            if iid in intent_ids or sid not in by_id:
                raise TaskError("Duplicate intent or unknown subject")
            intent_ids.add(iid)
            kind = item.get("kind")
            if kind not in ("gesture", "coverage", "accents"):
                raise TaskError("Unsupported high-level paint intent")
            subject = by_id[sid]
            mat = label(item.get("material", subject["materials"][0]), "intent material", 64)
            if mat not in subject["materials"]:
                raise TaskError("Paint intent material not declared by subject")
            purpose = label(item.get("purpose"), "paint purpose", 180)
            if len(purpose) < 8:
                raise TaskError("Every intent needs a meaningful paint purpose")
            # Merge+validate the named style and its direct sensor/brush overrides.
            style = combine_style(subject["styles"], item)
            normalized = {
                "id": iid, "subject_id": sid, "kind": kind,
                "purpose": purpose, "material": mat,
                "seed": integer(item.get("seed", 0), "intent seed", 0, 2147483647),
                "jitter": number(item.get("jitter", 0), "geometric jitter", 0, .25),
            }
            if "style" in item:
                normalized["style"] = item["style"]
            for key in ("brush", "brush_category", "pressure_curve",
                        "pressure_variation", "variation_frequency",
                        "variation_seed", "speed_sensitivity",
                        "pressure_interpolation"):
                if key in item:
                    normalized[key] = style[key] if key in style else item[key]
            if kind in ("gesture", "accents"):
                normalized["path"] = _path(item.get("path"), subject)
                if kind == "accents":
                    normalized["count"] = integer(item.get("count", 6), "accent count", 1, 64)
                    normalized["length"] = number(item.get("length", 12), "accent length", 1, 200)
            else:
                normalized["polygon"] = _polygon(item.get("polygon"), subject)
                normalized["spacing"] = number(item.get("spacing", 18),
                                               "coverage spacing", 1, 200)
                normalized["angle"] = number(item.get("angle", 0),
                                             "coverage angle", -180, 180)
            intents.append(normalized)
        total_intents += len(intents)
        if total_intents > MAX_TOTAL_INTENTS:
            raise TaskError("Scene exceeds 192 bounded intent descriptions")
        stages.append({
            "id": ident, "phase": phase,
            "goal": label(raw.get("goal"), "stage goal", 240),
            "intents": intents,
        })
    if stages[0]["phase"] != "sketch" or stages[-1]["phase"] not in ("detail", "polish"):
        raise TaskError("Stages require sketch first and detail/polish last")
    return {"schema": SCHEMA, "document": document,
            "style": label(candidate.get("style", "illustration"), "style", 160),
            "subjects": subjects, "stages": stages}


def lower_scene_v4(candidate):
    """Lower bounded intents into the existing reviewed ScenePlan v3 allowlist."""
    scene = validate_scene_v4(candidate)
    by_id = {s["id"]: s for s in scene["subjects"]}
    objects = []
    stage_layers = []
    for index, stage in enumerate(scene["stages"]):
        grouped = {}
        for item in stage["intents"]:
            grouped.setdefault(item["subject_id"], []).append(item)
        rows = []
        for sid in sorted(grouped, key=lambda key: (by_id[key]["depth"], key)):
            subject = by_id[sid]
            elements = []
            for item in grouped[sid]:
                selected = combine_style(subject["styles"], item)
                elements.extend(expand_intent(item, selected, subject, scene["document"]))
            if len(elements) > 900:
                raise TaskError("A stage/subject group exceeds 900 native elements")
            rows.append({
                "id": "s%02d_%s" % (index, sid),
                "name": stage["phase"] + " - " + subject["name"],
                "kind": "custom", "bounds": subject["bounds"],
                "brush": subject["brush"], "elements": elements,
                "parent": None,
            })
        for item in rows:
            if len(objects) >= MAX_GROUPS:
                raise TaskError("Scene exceeds 32 stage/subject layer groups")
            item["depth"] = (len(objects)+1)/33
            objects.append(item)
            stage_layers.append({"stage_index": index, "stage_id": stage["id"],
                                 "object_id": item["id"],
                                 "layer_name": item["id"] + " - " + item["name"]})
    lowered = validate_scene({
        "schema": "krita-agent-scene/3", "document": scene["document"],
        "style": scene["style"], "objects": objects,
    })
    return lowered, stage_layers


def compile_scene_v4(candidate, profile_directory=None, build=None,
                     preview_prefix=None):
    """Compile to native allowlisted steps plus bounded per-stage approval spans."""
    scene = validate_scene_v4(candidate)
    lowered, stage_layers = lower_scene_v4(scene)
    base = compile_scene_v3(lowered, profile_directory, build)
    stage_map = {row["layer_name"]: row["stage_index"] for row in stage_layers}
    groups = [[] for _ in scene["stages"]]
    current_stage = 0
    for step in base["steps"]:
        if step["command"] == "layer.create":
            current_stage = stage_map[step["parameters"]["name"]]
        groups[current_stage].append(step)
    if any(not any(step["command"] == "draw.stroke" for step in steps)
           for steps in groups):
        raise TaskError("Painting stage has no real native brush strokes")
    if preview_prefix is not None:
        if not isinstance(preview_prefix, str) or not re.fullmatch(
            r"r5-runs/[0-9a-f]{32}", preview_prefix
        ):
            raise TaskError("Stage preview prefix must be a unique approved run ID")
    from math import sqrt
    w, h = scene["document"]["width"], scene["document"]["height"]
    scale = min(1.0, 2048/w, 2048/h, sqrt(2000000/(w*h)))
    pw, ph = max(1, int(w*scale)), max(1, int(h*scale))
    n = len(groups)
    milestones = {max(0, (n+2)//3-1): "01-layout.png",
                  max(0, (2*n+2)//3-1): "02-color.png",
                  n-1: "03-final.png"}
    all_steps, spans, preview_paths = [], [], []
    for idx, steps in enumerate(groups):
        part = list(steps)
        if preview_prefix is not None:
            stage_filename = (preview_prefix + "/stages/stage-%02d-%s.png" %
                              (idx+1, scene["stages"][idx]["phase"]))
            names = [stage_filename]
            if idx in milestones:
                names.append(preview_prefix + "/stages/" + milestones[idx])
            for filename in names:
                preview = {"command": "preview.canvas", "parameters": {
                    "filename": filename, "width": pw, "height": ph}}
                part.extend(compile_workflow({"steps": [preview]}))
                preview_paths.append(filename)
        begin = len(all_steps)
        all_steps.extend(part)
        spans.append({
            "index": idx, "id": scene["stages"][idx]["id"],
            "phase": scene["stages"][idx]["phase"],
            "goal": scene["stages"][idx]["goal"],
            "start": begin, "stop": len(all_steps),
            "native_steps": len(part), "steps_sha256": digest(part),
        })
    if len(all_steps) > 10000:
        raise TaskError("ScenePlan v4 exceeds 10000 native steps")
    base.update({
        "schema": "krita-agent-scene-compiled/4",
        "source_v4_sha256": digest(scene),
        "stage_layers": stage_layers,
        "stage_spans": spans, "stage_preview_paths": preview_paths,
        "native_steps_sha256": digest(all_steps),
        "steps": all_steps,
        "not_artwork_acceptance": True, "requires_native_approval": True,
    })
    return base
