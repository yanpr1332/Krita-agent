"""Bounded, deterministic Round 8 material-aware native brush mark compiler.

A material recipe adds direction fields, calibrated stroke geometry, layers,
per-mark color/pressure and edge stitching. Only editable native stroke
elements are emitted; no image paste, pixel fabrication or arbitrary IPC.
Simple ScenePlan v4 intents without 'render' use their original R7 compiler.
"""
import math
import random
import re

from .protocol import TaskError, integer, number

MAX_MARKS = 400
TECHNIQUES = frozenset((
    "wash", "wisps", "ripples", "facets", "growth",
    "contour", "folds", "strands", "planes", "specular",
))
FLOWS = frozenset(("linear", "radial", "tangential", "perspective", "growth"))
EDGES = frozenset(("none", "stitch"))
HEX = re.compile(r"#[0-9A-Fa-f]{6}\Z")
DEFAULTS = {
    "wash": ("linear", 20, 55, 0.045),
    "wisps": ("linear", 24, 94, 0.23),
    "ripples": ("linear", 19, 55, 0.12),
    "facets": ("radial", 24, 48, 0.12),
    "growth": ("growth", 20, 42, 0.18),
    "contour": ("tangential", 19, 62, 0.22),
    "folds": ("growth", 22, 75, 0.30),
    "strands": ("growth", 14, 65, 0.23),
    "planes": ("radial", 22, 65, 0.09),
    "specular": ("linear", 26, 38, 0.04),
}


def validate_render(raw, kind):
    """An opt-in, immutable, bounded material recipe for ScenePlan v4 intents."""
    if kind not in ("gesture", "accents", "coverage"):
        raise TaskError("Material recipe only supports original brush intents")
    if not isinstance(raw, dict):
        raise TaskError("Render recipe must be a JSON object")
    allowed = {"technique", "flow", "angle", "spacing", "length",
               "curvature", "irregularity", "layers", "edge_mode",
               "edge_inset", "palette", "seed"}
    extra = set(raw) - allowed
    if extra:
        raise TaskError("Unsupported material recipe fields: " + ", ".join(sorted(extra)))
    technique = raw.get("technique")
    if technique not in TECHNIQUES:
        raise TaskError("Unknown material technique")
    flow, spacing, length, curvature = DEFAULTS[technique]
    palette = raw.get("palette", [])
    if not isinstance(palette, list) or len(palette) > 8:
        raise TaskError("Material palette must contain 0..8 RGB colors")
    if any(not isinstance(v, str) or not HEX.fullmatch(v) for v in palette):
        raise TaskError("Material palette colors must be #RRGGBB")
    return {
        "technique": technique,
        "flow": (lambda v: v if v in FLOWS else _bad_flow())(raw.get("flow", flow)),
        "angle": number(raw.get("angle", 0), "material angle", -180, 180),
        "spacing": number(raw.get("spacing", spacing), "material spacing", 3, 100),
        "length": number(raw.get("length", length), "material length", 4, 240),
        "curvature": number(raw.get("curvature", curvature), "material curvature", 0, .6),
        "irregularity": number(raw.get("irregularity", .16), "material irregularity", 0, .4),
        "layers": integer(raw.get("layers", 1), "material layers", 1, 3),
        "edge_mode": (lambda v: v if v in EDGES else _bad_edge())(raw.get("edge_mode", "stitch")),
        "edge_inset": number(raw.get("edge_inset", 1), "material edge inset", 0, 14),
        "palette": [v.upper() for v in palette],
        "seed": integer(raw.get("seed", 0), "material seed", 0, 2147483647),
    }


def _bad_flow():
    raise TaskError("Unknown surface flow field")


def _bad_edge():
    raise TaskError("Unknown material edge treatment")


def _inside(x, y, poly):
    """Even-odd point-in-polygon; boundary points are handled by edge distance."""
    inside = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > y) != (b[1] > y):
            crossing = a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if x < crossing:
                inside = not inside
    return inside


def _distance_edges(x, y, poly):
    best = math.inf
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        size2 = dx*dx + dy*dy
        t = max(0.0, min(1.0, ((x-a[0])*dx+(y-a[1])*dy)/size2)) if size2 else 0
        best = min(best, math.hypot(x-a[0]-t*dx, y-a[1]-t*dy))
    return best


def _safe_point(point, poly, inset):
    x, y = point
    return _inside(x, y, poly) and _distance_edges(x, y, poly) >= inset


def _field(x, y, subject, recipe):
    left, top, width, height = subject["bounds"]
    cx, cy = left+width/2, top+height/2
    mode = recipe["flow"]
    if mode == "radial":
        dx, dy = x-cx, y-cy
    elif mode == "tangential":
        dx, dy = cy-y, x-cx
    elif mode == "perspective":
        dx, dy = x-cx, y-(top-height*.35)
    elif mode == "growth":
        dx, dy = x-cx, y-(top+height*1.15)
    else:
        dx, dy = 1.0, 0.0
    if dx == 0 and dy == 0:
        dx = 1.0
    base = math.atan2(dy, dx) + math.radians(recipe["angle"])
    return math.cos(base), math.sin(base)


def _mark_geometry(x, y, dx, dy, length, curve, technique, noise):
    """Different mark silhouettes, all in genuine continuous native strokes."""
    px, py = -dy, dx
    samples = (-.5, -.25, 0, .25, .5)
    result = []
    for t in samples:
        phase = t+.5
        if technique == "wisps":
            lateral = curve*length*(.55*math.sin(2*math.pi*phase)
                                     +.25*math.sin(math.pi*phase))
        elif technique == "ripples":
            lateral = curve*length*.28*math.sin(2*math.pi*phase)
        elif technique == "facets":
            lateral = curve*length*(.4 if t == 0 else -.1)
        elif technique == "growth":
            lateral = curve*length*(phase*phase-.25)*noise
        elif technique == "contour":
            lateral = curve*length*math.sin(math.pi*phase)
        elif technique == "folds":
            lateral = curve*length*math.sin(2*math.pi*phase)
        elif technique == "strands":
            lateral = curve*length*(.5*math.sin(2*math.pi*phase)
                                     +.3*math.sin(math.pi*phase))*noise
        elif technique == "planes":
            lateral = curve*length*.33*math.sin(math.pi*phase)
        elif technique == "specular":
            lateral = curve*length*(.2 if t == 0 else 0)
        else:
            lateral = curve*length*.18*math.sin(math.pi*phase)
        result.append((x+dx*length*t+px*lateral,
                       y+dy*length*t+py*lateral))
    return result


def _clip_mark(path, polygon, inset):
    """Sample along each mark; output only contiguous interior line pieces.

    The restriction is on stroke CENTERLINES. Brush footprint may still extend
    beyond these points, so native pixels and boundary quality must be checked.
    """
    fragments, current = [], []
    for index, (a, b) in enumerate(zip(path, path[1:])):
        for i in range(11):
            if index and i == 0:
                continue
            t = i/10
            p = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
            if _safe_point(p, polygon, inset):
                xy = {"x": round(p[0], 4), "y": round(p[1], 4)}
                if not current or xy != current[-1]:
                    current.append(xy)
            elif current:
                if len(current) >= 2:
                    fragments.append(current)
                current = []
    if len(current) >= 2:
        fragments.append(current)
    return fragments


def _brush_style(selected, subject, color, size, opacity, index):
    base = {**subject["brush"], **selected.get("brush", {})}
    base.update({
        "color": color,
        "size": round(max(0.5, min(600.0, size)), 4),
        "opacity": round(max(.05, min(1.0, opacity)), 4),
    })
    result = {"brush": base}
    for field in ("brush_category", "pressure_curve", "pressure_variation",
                  "variation_frequency", "variation_seed",
                  "speed_sensitivity", "pressure_interpolation"):
        if field in selected:
            result[field] = selected[field]
    if "pressure_curve" not in result:
        if index == "wash":
            result["pressure_curve"] = [[0, .8], [.2, .94], [.8, .94], [1, .8]]
        elif index in ("facets", "specular"):
            result["pressure_curve"] = [[0, .58], [.23, .9], [.76, .82], [1, .48]]
        else:
            result["pressure_curve"] = [[0, .4], [.2, .85], [.7, .85], [1, .35]]
    return result


def _stroke(points, selected, subject, color, size, opacity, technique):
    style = _brush_style(selected, subject, color, size, opacity, technique)
    return {"kind": "stroke", "mode": "auto", "points": points, **style}


def _colors(recipe, selected, subject):
    return recipe["palette"] or [selected.get("brush", {}).get("color", subject["brush"]["color"])]


def _render_coverage(intent, selected, subject, recipe):
    polygon = intent["polygon"]
    left = min(x for x, _ in polygon)
    top = min(y for _, y in polygon)
    right = max(x for x, _ in polygon)
    bottom = max(y for _, y in polygon)
    spacing = recipe["spacing"]
    rows = math.ceil((bottom-top)/spacing)+1
    cols = math.ceil((right-left)/spacing)+1
    if rows*cols*recipe["layers"] > 2500:
        raise TaskError("Material grid exceeds safe candidate budget; split region or increase spacing")
    rng = random.Random((recipe["seed"] << 8) ^ intent["seed"])
    marks = []
    colors = _colors(recipe, selected, subject)
    technique = recipe["technique"]
    base = {**subject["brush"], **selected.get("brush", {})}
    nominal_size = base["size"]
    nominal_alpha = base.get("opacity", 1.0)
    for layer in range(recipe["layers"]):
        for row in range(rows):
            cy = top+(row+.46+(layer/recipe["layers"]-.5)*.65)*spacing
            if cy > bottom:
                continue
            for col in range(cols):
                stagger = .46 if row % 2 else 0
                cx = left+(col+.48+stagger)*spacing
                x = cx+(rng.random()-.5)*spacing*recipe["irregularity"]
                y = cy+(rng.random()-.5)*spacing*recipe["irregularity"]
                if not _safe_point((x, y), polygon, recipe["edge_inset"]):
                    continue
                dx, dy = _field(x, y, subject, recipe)
                jitter = (rng.random()-.5)*recipe["irregularity"]*.75
                cs, sn = math.cos(jitter), math.sin(jitter)
                dx, dy = dx*cs-dy*sn, dx*sn+dy*cs
                length = recipe["length"]*(.77+.46*rng.random())
                curvature = recipe["curvature"]*(.72+.45*rng.random())
                if technique in ("strands", "specular"):
                    length *= .65
                path = _mark_geometry(x, y, dx, dy, length, curvature,
                                      technique, .7+.6*rng.random())
                for fragment in _clip_mark(path, polygon, recipe["edge_inset"]):
                    # Taper and palette choice follow depth/lighting and pass,
                    # never independent per-pixel random paint.
                    normalized_y = (y-top)/max(1.0, bottom-top)
                    ci = min(len(colors)-1, int(
                        (normalized_y*.55+layer/max(1, recipe["layers"])*.45)
                        * len(colors)
                    ))
                    nominal = nominal_size * (
                        .95 if technique == "wash" else
                        .62 if technique in ("wisps", "planes", "contour") else
                        .23 if technique in ("strands", "specular") else
                        .46 if technique in ("ripples", "growth") else .54
                    )
                    size = nominal*(.82+.32*rng.random())*(1+.1*layer)
                    alpha = nominal_alpha*(.72 if layer == 0 else .53)
                    marks.append(_stroke(fragment, selected, subject,
                                         colors[ci], size, alpha, technique))
                    if len(marks) > MAX_MARKS:
                        raise TaskError("Material intent exceeds 400 native strokes")
    if recipe["edge_mode"] == "stitch":
        center = (sum(x for x, _ in polygon)/len(polygon),
                  sum(y for _, y in polygon)/len(polygon))
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            segment = math.hypot(dx, dy)
            count = max(1, math.ceil(segment/max(10.0, recipe["length"]*.7)))
            if count > 120:
                raise TaskError("Material boundary requires excessive edge segments")
            for i in range(count):
                t0, t1 = i/count, (i+1)/count
                p0 = (a[0]+dx*t0, a[1]+dy*t0)
                p1 = (a[0]+dx*t1, a[1]+dy*t1)
                # Shift only a small amount toward the polygon interior.
                midpoint = ((p0[0]+p1[0])/2, (p0[1]+p1[1])/2)
                toward = (center[0]-midpoint[0], center[1]-midpoint[1])
                dist = math.hypot(*toward) or 1
                inset = min(8.0, recipe["edge_inset"]+1.25)
                p0 = (p0[0]+toward[0]/dist*inset,
                      p0[1]+toward[1]/dist*inset)
                p1 = (p1[0]+toward[0]/dist*inset,
                      p1[1]+toward[1]/dist*inset)
                for fragment in _clip_mark((p0, p1), polygon, .1):
                    marks.append(_stroke(fragment, selected, subject,
                                         colors[-1], nominal_size*.34,
                                         nominal_alpha*.65, technique))
                    if len(marks) > MAX_MARKS:
                        raise TaskError("Material edge work exceeds 400 native strokes")
    if not marks:
        raise TaskError("Material renderer produced no native strokes")
    return marks


def _render_guide(intent, selected, subject, recipe):
    """Add deliberate parallel/curved variations to an approved guide line."""
    from .intent_strokes_v4 import expand_intent
    old = expand_intent(intent, selected, subject, {})
    rng = random.Random((recipe["seed"] << 8) ^ intent["seed"])
    base = {**subject["brush"], **selected.get("brush", {})}
    colors = _colors(recipe, selected, subject)
    marks = []
    for layer in range(recipe["layers"]):
        for idx, mark in enumerate(old):
            points = mark["points"]
            dx = points[-1]["x"]-points[0]["x"]
            dy = points[-1]["y"]-points[0]["y"]
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy/length, dx/length
            offset = (layer-(recipe["layers"]-1)/2)*recipe["spacing"]*.15
            transformed = []
            left, top, w, h = subject["bounds"]
            for p in points:
                x = max(left, min(left+w, p["x"]+nx*offset))
                y = max(top, min(top+h, p["y"]+ny*offset))
                q = {"x": round(x, 4), "y": round(y, 4)}
                if not transformed or q != transformed[-1]:
                    transformed.append(q)
            if len(transformed) < 2:
                continue
            tone = colors[min(len(colors)-1, (idx+layer) % len(colors))]
            width = base["size"]*(.9 if layer == 0 else .55)*(.9+.2*rng.random())
            marks.append(_stroke(transformed, selected, subject, tone, width,
                                 base.get("opacity", 1)*(.8 if layer == 0 else .6),
                                 recipe["technique"]))
            if len(marks) > MAX_MARKS:
                raise TaskError("Guide material intent exceeds 400 strokes")
    if not marks:
        raise TaskError("Material guide produced no native strokes")
    return marks


def expand_render_intent(intent, selected_style, subject, document):
    """Validated opt-in recipe expansion; untrusted plans never issue native IPC."""
    recipe = intent.get("render")
    if recipe is None:
        raise TaskError("Missing opt-in Round 8 material recipe")
    recipe = validate_render(recipe, intent["kind"])
    if intent["kind"] == "coverage":
        return _render_coverage(intent, selected_style, subject, recipe)
    return _render_guide(intent, selected_style, subject, recipe)
