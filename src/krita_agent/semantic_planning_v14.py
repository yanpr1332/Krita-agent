"""Round 14: bounded semantic composition -> deterministic paint intents -> v4.

The model describes only subjects, optional parts, simple normalized layout,
and declared spatial relations. Python computes all pixel geometry and all
native-intent parameters. This scaffolding is NOT a finished-artwork renderer:
the region fill and high-quality natural brush engines are later work.

No native effects, filesystem writes, images, or external calls occur here.
"""
import math
import re

from .creative_director import validate_brief
from .protocol import TaskError
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4

COMPOSITION_SCHEMA = "krita-agent-composition/1"
PAINT_PLAN_SCHEMA = "krita-agent-paint-plan/1"
MAX_NODES = 10  # 3 stages * 10 nodes leaves room under v4's 32 layer limit
MAX_PARTS = 4
ID = re.compile(r"[a-z][a-z0-9_-]{0,19}\Z")
HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
OUTLINES = frozenset(("ellipse", "rectangle", "diamond", "triangle", "capsule"))
RELATIONS = frozenset(("left_of", "above", "inside", "front_of"))

SEMANTIC_SYSTEM = """You are a Krita painting composition director, NOT an
executor. Return one small JSON object with schema krita-agent-composition/1.
Do NOT return brush strokes, paths, pixels, commands, KRA paths, code, scripts,
or any unrequested uploads. This is a geometric scaffold, NOT final artwork.
Allowed top-level keys: schema, style, subjects, relations, notes.
Supply 1..10 meaningful subjects with:
{id:"cat",name:"Sitting cat",kind:"animal",bbox:[0.25,0.18,0.42,0.70],
 depth:0.7,color:"#9a7566",detail_color:"#3b3539",
 outline:"ellipse",materials:["fur"],
 parts:[{id:"head",name:"Head",bbox:[0.25,0.03,0.5,0.30],
         outline:"ellipse",color:"#9a7566"}]}.
All bbox coordinates are [x,y,width,height] normalized to 0..1, NOT pixels;
part boxes are normalized inside their parent subject box. Do not make
objects overlap unless the intended composition needs it. Keep the total
count of subjects and parts <=10. The id is lowercase, at most 20
characters, and a part's joined id uses parent_id + "_" + part_id.
Outlines: ellipse, rectangle, diamond, triangle, capsule. Do not invent
shape kinds. Relation entries are optional, only
{kind:"left_of|above|inside|front_of",a:"id",b:"id"}.
Use relations ONLY when they actually hold geometrically; a is in front of b
when a.depth>b.depth. Do not guess unknown anatomy or perspective.
Keep semantic classes, separate parts, distinct objects, occlusion, and
plausible color grouping. No stage lists or complicated native schemas.
This output is a PROPOSAL that will be strictly validated and reviewed
before Krita drawing."""


def _mapping(raw, keys, where):
    if type(raw) is not dict:
        raise TaskError(where + " must be an object")
    extra = set(raw) - set(keys)
    if extra:
        raise TaskError(where + " has unsupported fields: " +
                        ", ".join(sorted(extra)))
    return raw


def _text(value, label, maximum=80):
    if type(value) is not str or not 1 <= len(value.strip()) <= maximum:
        raise TaskError(label + " must be non-empty bounded text")
    return value.strip()


def _id(value, label):
    if type(value) is not str or ID.fullmatch(value) is None:
        raise TaskError(label + " must be a lowercase safe identifier")
    return value


def _color(value, label):
    if type(value) is not str or HEX.fullmatch(value) is None:
        raise TaskError(label + " must be #RRGGBB")
    return value.lower()


def _scalar(value, label, minimum=0.0, maximum=1.0):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise TaskError(label + " must be a finite number")
    if not minimum <= value <= maximum:
        raise TaskError(label + " is outside the allowed range")
    return float(value)


def _bbox(value, label, min_extent=.03):
    if not isinstance(value, list) or len(value) != 4:
        raise TaskError(label + " must contain [x,y,width,height]")
    x, y, w, h = [_scalar(z, label) for z in value]
    if w < min_extent or h < min_extent or x+w > 1.000000001 or y+h > 1.000000001:
        raise TaskError(label + " must be a nontrivial box inside 0..1")
    return [x, y, w, h]


def _node(item, *, parent=None, absolute=None):
    is_part = parent is not None
    keys = ("id", "name", "kind", "bbox", "color", "detail_color",
            "outline", "depth", "materials", "parts") if not is_part else (
            "id", "name", "kind", "bbox", "color", "detail_color",
            "outline", "materials")
    _mapping(item, keys, "part" if is_part else "subject")
    local_id = _id(item.get("id"), "node ID")
    ident = parent["id"] + "_" + local_id if is_part else local_id
    _id(ident, "joined part ID")
    bbox = _bbox(item.get("bbox"), "part bbox" if is_part else "subject bbox")
    if is_part:
        px, py, pw, ph = absolute
        x, y, w, h = bbox
        bbox = [px+pw*x, py+ph*y, pw*w, ph*h]
    outline = item.get("outline", "ellipse")
    if outline not in OUTLINES:
        raise TaskError("Unsupported semantic outline")
    material_names = item.get("materials", parent["materials"] if is_part else ["paint"])
    if (not isinstance(material_names, list) or
            not 1 <= len(material_names) <= 8):
        raise TaskError("Semantic node materials need 1..8 names")
    materials = [_text(m, "material", 64) for m in material_names]
    if len(set(materials)) != len(materials):
        raise TaskError("Duplicate semantic material")
    color = _color(item.get("color", parent["color"] if is_part else None),
                   "subject color")
    node = {
        "id": ident,
        "name": _text(item.get("name", ident), "subject name", 80),
        "kind": _text(item.get("kind", parent["kind"] if is_part else None),
                      "semantic kind", 64),
        "bbox": bbox,
        "depth": parent["depth"] if is_part else _scalar(
            item.get("depth", .5), "depth"),
        "color": color,
        "detail_color": _color(item.get("detail_color",
                                       parent["detail_color"] if is_part
                                       else _shade(color, .45)), "detail color"),
        "outline": outline, "materials": materials,
        "parent": parent["id"] if is_part else None,
    }
    return node


def _shade(value, fraction):
    rgb = [int(value[i:i+2], 16) for i in (1, 3, 5)]
    return "#" + "".join("%02x" % max(0, min(255, round(c*fraction)))
                         for c in rgb)


def _check_relation(rel, nodes):
    _mapping(rel, ("kind", "a", "b"), "composition relation")
    kind = rel.get("kind")
    a, b = rel.get("a"), rel.get("b")
    if kind not in RELATIONS or type(a) is not str or type(b) is not str:
        raise TaskError("Invalid composition relation")
    if a == b or a not in nodes or b not in nodes:
        raise TaskError("Composition relation refers to unknown or identical nodes")
    A, B = nodes[a], nodes[b]
    x, y, w, h = A["bbox"]
    X, Y, W, H = B["bbox"]
    eps = 1e-8
    satisfied = {
        "left_of": x+w <= X+eps,
        "above": y+h <= Y+eps,
        "inside": x >= X-eps and y >= Y-eps and x+w <= X+W+eps
                  and y+h <= Y+H+eps,
        "front_of": A["depth"] > B["depth"]+eps,
    }[kind]
    if not satisfied:
        raise TaskError("Unsatisfied composition relation {}: {} / {}".format(
            kind, a, b))
    return {"kind": kind, "a": a, "b": b}


def validate_composition(candidate):
    """Pure, canonical and strict high-level proposal validation."""
    _mapping(candidate, ("schema", "style", "subjects", "relations", "notes"),
             "composition")
    if candidate.get("schema") != COMPOSITION_SCHEMA:
        raise TaskError("Expected composition schema /1")
    subjects = candidate.get("subjects")
    if not isinstance(subjects, list) or not 1 <= len(subjects) <= MAX_NODES:
        raise TaskError("Composition requires 1..10 semantic subjects")
    nodes, ids = [], set()
    # Normalized archives flatten parts into nodes with absolute normalized
    # bboxes and explicit parent IDs. Their deterministic round-trip MUST
    # match the initial model proposal or approval hashes would be unstable.
    canonical = all(type(item) is dict and "parent" in item
                    for item in subjects)
    if canonical:
        for item in subjects:
            _mapping(item, ("id", "name", "kind", "bbox", "color",
                            "detail_color", "outline", "depth",
                            "materials", "parent"), "canonical node")
            ident = _id(item.get("id"), "canonical node ID")
            if ident in ids:
                raise TaskError("Duplicate composition subject ID")
            ids.add(ident)
            box = _bbox(item.get("bbox"), "canonical bbox", min_extent=1e-8)
            parent_id = item.get("parent")
            if parent_id is not None:
                _id(parent_id, "canonical parent ID")
            if item.get("outline") not in OUTLINES:
                raise TaskError("Unsupported semantic outline")
            colors = (_color(item.get("color"), "subject color"),
                      _color(item.get("detail_color"), "detail color"))
            mats = item.get("materials")
            if (not isinstance(mats, list) or not 1 <= len(mats) <= 8):
                raise TaskError("Semantic node materials need 1..8 names")
            mats = [_text(m, "material", 64) for m in mats]
            if len(set(mats)) != len(mats):
                raise TaskError("Duplicate semantic material")
            nodes.append({
                "id": ident, "name": _text(item.get("name"), "subject name"),
                "kind": _text(item.get("kind"), "semantic kind", 64),
                "bbox": box, "depth": _scalar(item.get("depth"), "depth"),
                "color": colors[0], "detail_color": colors[1],
                "outline": item["outline"], "materials": mats,
                "parent": parent_id,
            })
        by_id = {n["id"]: n for n in nodes}
        for node in nodes:
            if node["parent"] is None:
                continue
            parent = by_id.get(node["parent"])
            if parent is None or parent["parent"] is not None:
                raise TaskError("Canonical part has an invalid parent")
            x, y, w, h = node["bbox"]
            X, Y, W, H = parent["bbox"]
            if not (x >= X-1e-8 and y >= Y-1e-8 and
                    x+w <= X+W+1e-8 and y+h <= Y+H+1e-8):
                raise TaskError("Canonical part escapes its parent")
    else:
        for item in subjects:
            parent = _node(item)
            if parent["id"] in ids:
                raise TaskError("Duplicate composition subject ID")
            ids.add(parent["id"])
            nodes.append(parent)
            parts = item.get("parts", [])
            if not isinstance(parts, list) or len(parts) > MAX_PARTS:
                raise TaskError("Composition subject exceeds four parts")
            for part in parts:
                node = _node(part, parent=parent, absolute=parent["bbox"])
                if node["id"] in ids:
                    raise TaskError("Duplicate composition part ID")
                ids.add(node["id"])
                nodes.append(node)
            if len(nodes) > MAX_NODES:
                raise TaskError("Composition exceeds ten drawable nodes")
    raw_relations = candidate.get("relations", [])
    if not isinstance(raw_relations, list) or len(raw_relations) > 30:
        raise TaskError("Composition supports at most 30 declared relations")
    by_id = {n["id"]: n for n in nodes}
    relations = [_check_relation(row, by_id) for row in raw_relations]
    if len({(r["kind"], r["a"], r["b"]) for r in relations}) != len(relations):
        raise TaskError("Duplicate composition relation")
    return {
        "schema": COMPOSITION_SCHEMA,
        "style": _text(candidate.get("style", "illustration"), "style", 160),
        "notes": _text(candidate.get("notes", "Coherent composition scaffold"),
                       "composition notes", 240),
        "subjects": nodes, "relations": relations,
    }


def _polygon(box, outline):
    """Deterministic bounded normalized outline with an interior inset.

    Geometries are simple *approximations* derived only from a box/primitive,
    not a hallucinated accurate human/animal contour.
    """
    x, y, w, h = box
    inset = .055
    left, top = x+w*inset, y+h*inset
    right, bottom = x+w*(1-inset), y+h*(1-inset)
    mid_x, mid_y = (left+right)/2, (top+bottom)/2
    if outline == "rectangle":
        pts = [(left, top), (right, top), (right, bottom), (left, bottom)]
    elif outline == "diamond":
        pts = [(mid_x, top), (right, mid_y), (mid_x, bottom), (left, mid_y)]
    elif outline == "triangle":
        pts = [(mid_x, top), (right, bottom), (left, bottom)]
    elif outline == "capsule":
        pts = [(left, mid_y), (left+w*.07, top+h*.12),
               (right-w*.07, top+h*.12), (right, mid_y),
               (right-w*.07, bottom-h*.12),
               (left+w*.07, bottom-h*.12)]
    else:
        pts = [(mid_x+math.cos(-math.pi/2+i*math.pi/6)*(right-left)/2,
                mid_y+math.sin(-math.pi/2+i*math.pi/6)*(bottom-top)/2)
               for i in range(12)]
    return [[round(a, 6), round(b, 6)] for a, b in pts]


def _to_pixels(normalized, width, height):
    return [[round(max(0, min(width, x*width)), 4),
             round(max(0, min(height, y*height)), 4)]
            for x, y in normalized]


def _pixel_box(box, width, height):
    x, y, w, h = box
    left, top = round(x*width, 4), round(y*height, 4)
    right = min(float(width), round((x+w)*width, 4))
    bottom = min(float(height), round((y+h)*height, 4))
    return [left, top, round(right-left, 4), round(bottom-top, 4)]


def compile_semantic(candidate, brief):
    """Canonical composition + inspectable paint plan + validated legacy v4.

    No Krita commands are produced or executed by the model. For final
    execution the downstream existing v4 compiler and explicit approvals
    are still mandatory.
    """
    spec = validate_brief(brief)
    composition = validate_composition(candidate)
    width, height = spec["width"], spec["height"]
    if width * height > 32000000:
        raise TaskError("Canvas budget exceeded")
    nodes = composition["subjects"]
    v4_subjects = []
    outline_map = {}
    for n in nodes:
        box = _pixel_box(n["bbox"], width, height)
        if min(box[2], box[3]) < 8:
            raise TaskError("Semantic object too small for native drawing: " + n["id"])
        outline = _to_pixels(_polygon(n["bbox"], n["outline"]), width, height)
        v4_subjects.append({
            "id": n["id"], "name": n["name"], "kind": n["kind"],
            "materials": n["materials"], "parent": n["parent"],
            "depth": n["depth"], "bounds": box,
            "brush": {"size": round(min(20., max(2., min(box[2], box[3])*.045)), 3),
                      "color": n["color"], "opacity": .82,
                      "pressure_enabled": True},
        })
        outline_map[n["id"]] = outline
    semantic_stages, v4_stages = [], []
    stage_defs = [
        ("sketch", "Establish the visible silhouette and component placement",
         "contour"),
        ("block_in", "Mark the interior base-color regions before detailed work",
         "region_blockin"),
        ("detail", "Indicate form-sensitive detail with tapered native marks",
         "detail_line"),
    ]
    for phase, goal, operation in stage_defs:
        intents, tasks = [], []
        for n in nodes:
            sid, verts = n["id"], outline_map[n["id"]]
            bx, by, bw, bh = _pixel_box(n["bbox"], width, height)
            small = max(1.5, min(8., min(bw, bh)*.025))
            iid = phase[:3] + "_" + sid
            if phase == "sketch":
                payload = {
                    "kind": "gesture", "path": verts + [verts[0]],
                    "brush": {"size": round(small, 2), "color": n["detail_color"],
                              "opacity": .85, "pressure_enabled": True},
                    "pressure_curve": [[0, .2], [.2, .75], [.75, .68], [1, .2]],
                    "purpose": "Establish closed silhouette contour for " + n["name"],
                }
            elif phase == "block_in":
                # R15: use an actual editable Krita native filled polygon,
                # not hundreds of broad scanline paintLine fallbacks. The
                # subject's reviewed baseline foreground color is used.
                # Region area, shape and build capability are checked later.
                payload = {
                    "kind": "region", "polygon": verts,
                    "purpose": "Block in the base color for " + n["name"],
                }
            else:
                cx, cy = bx+bw*.5, by+bh*.5
                # All detail points are interior; this line is an *intention
                # placeholder*, not an assertion of true anatomical detail.
                guide = [[round(bx+bw*.25, 4), round(cy, 4)],
                         [round(cx, 4), round(cy-bh*.10, 4)],
                         [round(bx+bw*.75, 4), round(cy, 4)]]
                payload = {
                    "kind": "gesture", "path": guide,
                    "brush": {"size": round(small*.7, 2),
                              "color": n["detail_color"], "opacity": .75,
                              "pressure_enabled": True},
                    "pressure_curve": [[0, .15], [.35, .72], [1, .15]],
                    "purpose": "Indicate a form direction guide for " + n["name"],
                }
            intents.append({"id": iid, "subject_id": sid, **payload})
            tasks.append({"subject_id": sid, "operation": operation,
                          "purpose": payload["purpose"]})
        v4_stages.append({"id": phase, "phase": phase, "goal": goal,
                          "intents": intents})
        semantic_stages.append({"id": phase, "operation": operation,
                                "tasks": tasks})
    scene = validate_scene_v4({
        "schema": "krita-agent-scene/4",
        "document": {"width": width, "height": height,
                     "name": spec["title"]},
        "style": composition["style"],
        "subjects": v4_subjects, "stages": v4_stages,
    })
    paint_plan = {
        "schema": PAINT_PLAN_SCHEMA,
        "source_composition_sha256": digest(composition),
        "scene_v4_sha256": digest(scene),
        "stages": semantic_stages,
        "status": "structural_scaffold_only",
        "requires_native_approval": True,
        "artwork_accepted": False,
    }
    return composition, paint_plan, scene


def propose_semantic(brief, provider, reference_image=None):
    """One explicit remote model request, no paid repair/retry loop."""
    spec = validate_brief(brief)
    prompt = (
        "Plan a semantic object composition for a {}x{} Krita canvas. "
        "Title: {}. Style: {}. Brief: {}. "
        "Return only a bounded normalized composition, no pixel paths, "
        "no native commands. Keep layout plausible and subjects distinct."
    ).format(spec["width"], spec["height"], spec["title"],
             spec["style"], spec["prompt"])
    candidate = provider.complete_json(
        SEMANTIC_SYSTEM, prompt,
        image_paths=[reference_image] if reference_image else [],
    )
    composition, paint_plan, scene = compile_semantic(candidate, spec)
    return {
        "composition": composition, "paint_plan": paint_plan,
        "scene_v4": scene, "scene_v4_sha256": digest(scene),
        "provider_model": getattr(provider, "model", "externally_provided"),
        "approval": "required", "side_effects": "none",
        "model_requests": 1, "model_retries": 0,
    }
