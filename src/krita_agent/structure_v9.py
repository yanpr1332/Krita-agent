"""Round 9: generalist structure contracts for real, editable Krita painting.

These contracts describe *what* is drawn, not hard-coded human/animal artwork.
They validate named part counts, skeleton connection graph, perspective rays,
subject relations and user-locked anchors before the safe v4 native compiler.
No filesystem, model calls, image synthesis or Krita commands are executed here.
"""
import math
import re

from .protocol import TaskError, integer, label, number

IDENT = re.compile(r"[a-z][a-z0-9_-]{0,23}\Z")
MAX_SUBJECT_STRUCTURES = 24
MAX_PARTS = 192
MAX_ANCHORS = 256
MAX_CHAINS = 64
MAX_RELATIONS = 96
MAX_GUIDES = 24


def _id(value, name="identifier"):
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise TaskError("Invalid Round 9 " + name)
    return value


def _map(raw, keys, name):
    if not isinstance(raw, dict):
        raise TaskError(name + " must be an object")
    extra = set(raw) - set(keys)
    if extra:
        raise TaskError(name + " has unexpected keys: " + ", ".join(sorted(extra)))
    return raw


def _list(raw, name, lower=0, upper=128):
    if not isinstance(raw, list) or not lower <= len(raw) <= upper:
        raise TaskError(name + " must contain %d..%d entries" % (lower, upper))
    return raw


def _point(raw, canvas, bounds=None):
    if not isinstance(raw, list) or len(raw) != 2:
        raise TaskError("Round 9 anchor must be [x,y]")
    w, h = canvas
    x, y = number(raw[0], "anchor x", -65536, 65536), number(raw[1], "anchor y", -65536, 65536)
    if bounds is None:
        if not 0 <= x <= w or not 0 <= y <= h:
            raise TaskError("Anchor lies outside canvas")
    else:
        left, top, width, height = bounds
        if not left <= x <= left + width or not top <= y <= top + height:
            raise TaskError("Anchor lies outside declared subject bounds")
    return [x, y]


def _rect(raw, bounds):
    if not isinstance(raw, list) or len(raw) != 4:
        raise TaskError("Part bounds must be [x,y,width,height]")
    x, y, w, h = [number(v, "part bound", 0, 8192) for v in raw]
    l, t, bw, bh = bounds
    if not w > 0 or not h > 0 or x < l or y < t or x+w > l+bw or y+h > t+bh:
        raise TaskError("Part bounds exceed its subject or contain no area")
    return [x, y, w, h]


def _rect_overlap(a, b):
    return max(0, min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0])) * max(
        0, min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]))


def _inside(a, b):
    return (a[0] >= b[0] and a[1] >= b[1]
            and a[0]+a[2] <= b[0]+b[2] and a[1]+a[3] <= b[1]+b[3])


def _audit_part_graph(parts):
    by_id = {p["id"]: p for p in parts}
    for part in parts:
        seen = {part["id"]}
        parent = part["parent"]
        while parent is not None:
            if parent not in by_id or parent in seen:
                raise TaskError("Part graph has missing or cyclic parent")
            seen.add(parent)
            parent = by_id[parent]["parent"]
            if len(seen) > 32:
                raise TaskError("Part hierarchy exceeds bounded depth")


def _part_counts(parts, expectations):
    for rule in expectations:
        found = sum(p["tag"] == rule["tag"] for p in parts)
        if not rule["minimum"] <= found <= rule["maximum"]:
            raise TaskError("Semantic part-count constraint failed for tag " +
                            rule["tag"] + ": observed %d, expected %d..%d" %
                            (found, rule["minimum"], rule["maximum"]))


def _validate_structured_subject(raw, by_subject, canvas):
    _map(raw, ("subject_id", "category", "anchors", "parts", "chains",
               "expectations", "locked"), "structured subject")
    sid = _id(raw.get("subject_id"), "structured subject ID")
    subject = by_subject.get(sid)
    if subject is None:
        raise TaskError("Unknown subject in Round 9 structure: " + sid)
    bounds = subject["bounds"]
    anchors = []
    seen = set()
    for anchor in _list(raw.get("anchors", []), "anchors", 0, 64):
        _map(anchor, ("id", "xy", "locked", "role"), "structural anchor")
        key = _id(anchor.get("id"), "anchor ID")
        if key in seen:
            raise TaskError("Duplicate structural anchor " + key)
        seen.add(key)
        if type(anchor.get("locked", False)) is not bool:
            raise TaskError("Anchor locked must be a boolean")
        anchors.append({
            "id": key, "xy": _point(anchor.get("xy"), canvas, bounds),
            "locked": anchor.get("locked", False),
            "role": label(anchor.get("role", key), "anchor role", 80),
        })
    parts = []
    used = set()
    for raw_part in _list(raw.get("parts", []), "parts", 0, 32):
        _map(raw_part, ("id", "tag", "name", "bounds", "parent", "anchor_id",
                        "material", "locked"), "part")
        key = _id(raw_part.get("id"), "part ID")
        if key in used:
            raise TaskError("Duplicate structural part " + key)
        used.add(key)
        anchor_id = raw_part.get("anchor_id")
        if anchor_id is not None:
            anchor_id = _id(anchor_id, "part anchor ID")
            if anchor_id not in seen:
                raise TaskError("Part uses unknown structural anchor")
        material = label(raw_part.get("material", subject["materials"][0]), "part material", 64)
        if material not in subject["materials"]:
            raise TaskError("Part uses a material not declared by subject")
        if type(raw_part.get("locked", False)) is not bool:
            raise TaskError("Part locked must be a boolean")
        parent = raw_part.get("parent")
        if parent is not None:
            parent = _id(parent, "parent part ID")
        parts.append({
            "id": key, "name": label(raw_part.get("name", key), "part name", 80),
            "tag": _id(raw_part.get("tag", key), "semantic part tag"),
            "bounds": _rect(raw_part.get("bounds"), bounds),
            "parent": parent, "anchor_id": anchor_id,
            "material": material, "locked": raw_part.get("locked", False),
        })
    _audit_part_graph(parts)
    chains = []
    chain_ids = set()
    for chain in _list(raw.get("chains", []), "structural chains", 0, 8):
        _map(chain, ("id", "anchors", "purpose", "render"), "structural chain")
        key = _id(chain.get("id"), "chain ID")
        if key in chain_ids:
            raise TaskError("Duplicate structural chain ID")
        chain_ids.add(key)
        members = _list(chain.get("anchors"), "chain anchors", 2, 12)
        members = [_id(x, "chain anchor ID") for x in members]
        if any(a not in seen for a in members):
            raise TaskError("Chain refers to missing anchor")
        if any(a == b for a, b in zip(members, members[1:])):
            raise TaskError("Chain repeats consecutive anchors")
        if type(chain.get("render", True)) is not bool:
            raise TaskError("Chain render must be boolean")
        coords = {a["id"]: a["xy"] for a in anchors}
        if all(coords[a] == coords[b] for a, b in zip(members, members[1:])):
            raise TaskError("Chain has no drawable length")
        chains.append({
            "id": key, "anchors": members,
            "purpose": label(chain.get("purpose", "Plan the " + key + " structural axis"),
                             "chain purpose", 180),
            "render": chain.get("render", True),
        })
    expectations = []
    for rule in _list(raw.get("expectations", []), "part expectations", 0, 24):
        _map(rule, ("tag", "min", "max", "minimum", "maximum"), "part expectation")
        lo = integer(rule.get("min", rule.get("minimum")), "minimum part count", 0, 32)
        hi = integer(rule.get("max", rule.get("maximum")), "maximum part count", lo, 32)
        expectations.append({"tag": _id(rule.get("tag"), "expected part tag"),
                             "minimum": lo, "maximum": hi})
    if len({x["tag"] for x in expectations}) != len(expectations):
        raise TaskError("Duplicate part-count expectation")
    _part_counts(parts, expectations)
    if type(raw.get("locked", False)) is not bool:
        raise TaskError("Subject locked must be boolean")
    return {
        "subject_id": sid,
        "category": label(raw.get("category", subject["kind"]), "subject category", 80),
        "anchors": anchors, "parts": parts, "chains": chains,
        "expectations": expectations, "locked": raw.get("locked", False),
    }


def _validate_relations(raw, by_subject, structs):
    relations = []
    used = set()
    anchor_maps = {x["subject_id"]: {a["id"]: a["xy"] for a in x["anchors"]} for x in structs}
    for relation in _list(raw, "subject relations", 0, MAX_RELATIONS):
        _map(relation, ("id", "kind", "a", "b", "anchor_a", "anchor_b",
                        "max_gap", "expected_ratio", "tolerance"), "subject relation")
        key = _id(relation.get("id"), "relation ID")
        if key in used:
            raise TaskError("Duplicate subject relation ID")
        used.add(key)
        kind = relation.get("kind")
        if kind not in ("front_of", "left_of", "above", "inside", "attached", "width_ratio"):
            raise TaskError("Unknown semantic relationship")
        a, b = _id(relation.get("a"), "relation subject a"), _id(relation.get("b"), "relation subject b")
        if a == b or a not in by_subject or b not in by_subject:
            raise TaskError("Relationship requires two known distinct subjects")
        one, two = by_subject[a], by_subject[b]
        result = {"id": key, "kind": kind, "a": a, "b": b}
        if kind == "front_of" and not one["depth"] > two["depth"]:
            raise TaskError("Front/occlusion relation contradicts depth order")
        if kind == "left_of" and one["bounds"][0] + one["bounds"][2] > two["bounds"][0]:
            raise TaskError("Left-of relation conflicts with subject bounds")
        if kind == "above" and one["bounds"][1] + one["bounds"][3] > two["bounds"][1]:
            raise TaskError("Above relation conflicts with subject bounds")
        if kind == "inside" and not _inside(one["bounds"], two["bounds"]):
            raise TaskError("Inside relation conflicts with subject bounds")
        if kind == "attached":
            aa, bb = _id(relation.get("anchor_a"), "attachment anchor a"), _id(
                relation.get("anchor_b"), "attachment anchor b")
            if aa not in anchor_maps.get(a, {}) or bb not in anchor_maps.get(b, {}):
                raise TaskError("Attached relationship refers to missing anchors")
            maximum = number(relation.get("max_gap", 6), "attachment gap", 0, 512)
            pa, pb = anchor_maps[a][aa], anchor_maps[b][bb]
            if math.dist(pa, pb) > maximum:
                raise TaskError("Attached subjects have disconnected anchors")
            result.update({"anchor_a": aa, "anchor_b": bb, "max_gap": maximum})
        if kind == "width_ratio":
            target = number(relation.get("expected_ratio"), "expected width ratio", .01, 100)
            tolerance = number(relation.get("tolerance", .1), "ratio tolerance", 0, 1)
            ratio = one["bounds"][2] / two["bounds"][2]
            if abs(ratio/target - 1) > tolerance:
                raise TaskError("Relative subject width violates declared proportion")
            result.update({"expected_ratio": target, "tolerance": tolerance})
        relations.append(result)
    # Reject incompatible explicit occlusion cycles even when depth data could
    # otherwise be manipulated to make a visually impossible order.
    adjacency = {}
    for row in relations:
        if row["kind"] == "front_of":
            adjacency.setdefault(row["a"], set()).add(row["b"])
    def visit(node, active, done):
        if node in active:
            raise TaskError("Occlusion relations contain a cycle")
        if node in done:
            return
        active.add(node)
        for nxt in adjacency.get(node, ()):
            visit(nxt, active, done)
        active.remove(node)
        done.add(node)
    done = set()
    for node in adjacency:
        visit(node, set(), done)
    return relations


def _validate_perspective(raw, document):
    if raw is None:
        return None
    _map(raw, ("horizon_y", "vanishing_points", "rays"), "perspective")
    width, height = document["width"], document["height"]
    horizon = number(raw.get("horizon_y", height / 2), "horizon y", -4*height, 5*height)
    vps = []
    ids = set()
    for v in _list(raw.get("vanishing_points", []), "vanishing points", 0, 4):
        _map(v, ("id", "xy"), "vanishing point")
        ident = _id(v.get("id"), "vanishing point ID")
        if ident in ids:
            raise TaskError("Duplicate vanishing point ID")
        ids.add(ident)
        point = v.get("xy")
        if not isinstance(point, list) or len(point) != 2:
            raise TaskError("Vanishing point must be [x,y]")
        xy = [number(q, "vanishing coordinate", -65536, 65536) for q in point]
        vps.append({"id": ident, "xy": xy})
    by_id = {v["id"]: v["xy"] for v in vps}
    rays = []
    for ray in _list(raw.get("rays", []), "perspective rays", 0, 32):
        _map(ray, ("id", "vanishing_point", "start", "end",
                   "max_deviation_deg", "measured_deviation_deg"), "perspective ray")
        ident = _id(ray.get("id"), "ray ID")
        vp_id = _id(ray.get("vanishing_point"), "ray VP ID")
        if vp_id not in by_id or any(i["id"] == ident for i in rays):
            raise TaskError("Duplicate ray or unknown vanishing point")
        start = _point(ray.get("start"), (width, height))
        end = _point(ray.get("end"), (width, height))
        vp = by_id[vp_id]
        a = (end[0]-start[0], end[1]-start[1])
        b = (vp[0]-start[0], vp[1]-start[1])
        la, lb = math.hypot(*a), math.hypot(*b)
        if la < 0.5 or lb < 0.5:
            raise TaskError("Perspective ray degenerates near its origin")
        cosine = max(-1.0, min(1.0, (a[0]*b[0]+a[1]*b[1])/(la*lb)))
        deviation = math.degrees(math.acos(cosine))
        maximum = number(ray.get("max_deviation_deg", 12), "perspective tolerance", 0, 30)
        if deviation > maximum + 1e-8:
            raise TaskError("Perspective edge does not converge to its declared VP")
        rays.append({"id": ident, "vanishing_point": vp_id,
                     "start": start, "end": end,
                     "max_deviation_deg": maximum,
                     "measured_deviation_deg": round(deviation, 4)})
    return {"horizon_y": horizon, "vanishing_points": vps, "rays": rays}


def validate_structure_plan(raw, subjects, document):
    """Normalize opt-in, bounded generic structure. No assumptions about species."""
    _map(raw, ("version", "guide_mode", "subjects", "relations", "perspective"), "structure")
    if type(raw.get("version", 1)) is not int or raw.get("version", 1) != 1:
        raise TaskError("Unsupported structure version")
    mode = raw.get("guide_mode", "audit_only")
    if mode not in ("audit_only", "paint"):
        raise TaskError("Unknown structural guide mode")
    by_subject = {x["id"]: x for x in subjects}
    width, height = document["width"], document["height"]
    structs = []
    ids = set()
    for item in _list(raw.get("subjects", []), "structured subjects", 0, MAX_SUBJECT_STRUCTURES):
        row = _validate_structured_subject(item, by_subject, (width, height))
        if row["subject_id"] in ids:
            raise TaskError("Duplicate structured subject ID")
        ids.add(row["subject_id"])
        structs.append(row)
    if sum(len(x["parts"]) for x in structs) > MAX_PARTS or sum(
            len(x["anchors"]) for x in structs) > MAX_ANCHORS or sum(
            len(x["chains"]) for x in structs) > MAX_CHAINS:
        raise TaskError("Structured geometry exceeds bounded budgets")
    relations = _validate_relations(raw.get("relations", []), by_subject, structs)
    perspective = _validate_perspective(raw.get("perspective"), document)
    guide_count = sum(1 for s in structs for c in s["chains"] if c["render"])
    if guide_count > MAX_GUIDES:
        raise TaskError("Too many native structural guide chains")
    return {"version": 1, "guide_mode": mode, "subjects": structs,
            "relations": relations, "perspective": perspective}


def structural_guide_intents(scene):
    """Derive model-reviewed skeleton axes as safe v4 gestures in sketch phase."""
    structure = scene.get("structure")
    if not structure or structure["guide_mode"] != "paint":
        return []
    guides = []
    for row in structure["subjects"]:
        by_anchor = {a["id"]: a["xy"] for a in row["anchors"]}
        for chain in row["chains"]:
            if chain["render"]:
                ident = "r9guide%02d" % (len(guides)+1)
                guides.append({
                    "id": ident, "subject_id": row["subject_id"], "kind": "gesture",
                    "purpose": chain["purpose"], "material": next(
                        s["materials"][0] for s in scene["subjects"]
                        if s["id"] == row["subject_id"]),
                    "path": [list(by_anchor[x]) for x in chain["anchors"]],
                    "seed": 0, "jitter": 0.0,
                })
    return guides


def diagnose_structure(scene):
    """Read-only semantic diagnostics; warnings never claim visual correctness."""
    structure = scene.get("structure")
    issues = []
    if not structure:
        return {"schema": "krita-agent-structure-diagnostics/1",
                "issues": [], "validated": False, "requires_visual_review": True}
    by_subject = {x["id"]: x for x in scene["subjects"]}
    for relation in structure["relations"]:
        if relation["kind"] == "front_of":
            a, b = by_subject[relation["a"]], by_subject[relation["b"]]
            if _rect_overlap(a["bounds"], b["bounds"]) == 0:
                issues.append({
                    "code": "no_visible_occlusion",
                    "severity": "warning", "stage": "sketch",
                    "subject_id": a["id"], "related_subject_id": b["id"],
                    "region": list(a["bounds"]),
                    "message": "Front/back ordering is declared but the 2D bounds do not overlap",
                })
    for subject in structure["subjects"]:
        if not subject["anchors"]:
            issues.append({
                "code": "no_structural_anchors",
                "severity": "info", "stage": "sketch",
                "subject_id": subject["subject_id"],
                "message": "This subject has no explicit structural anchor graph",
            })
        if any(p["locked"] for p in subject["parts"]) or subject["locked"]:
            issues.append({
                "code": "user_locked_structure",
                "severity": "info", "stage": "sketch",
                "subject_id": subject["subject_id"],
                "message": "Any future repair must preserve user-locked structure",
            })
    return {"schema": "krita-agent-structure-diagnostics/1",
            "validated": True, "requires_visual_review": True,
            "issues": issues,
            "subject_count": len(structure["subjects"]),
            "part_count": sum(len(s["parts"]) for s in structure["subjects"]),
            "relation_count": len(structure["relations"]),
            "perspective_ray_count": len((structure.get("perspective") or {}).get("rays", [])),
            "rendered_skeleton_chains": len(structural_guide_intents(scene))}
