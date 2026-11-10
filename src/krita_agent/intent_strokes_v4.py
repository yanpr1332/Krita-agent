"""Deterministic, bounded high-level paint-intent geometry for ScenePlan v4.

The module only proposes real Krita brush stroke paths. It cannot draw, read
external assets, paste raster references or send IPC commands. It is a StagePlan
foundation, not a claim that its procedural marks are artistic on their own.
"""
import math
import random

from .protocol import TaskError

MAX_EXPANDED_PER_INTENT = 240


def _to_xy(u, v, cosine, sine, width, height):
    x = cosine * u - sine * v
    y = sine * u + cosine * v
    return {"x": round(max(0.0, min(width, x)), 4),
            "y": round(max(0.0, min(height, y)), 4)}


def _stroke(coords, selected):
    mark = {"kind": "stroke", "points": coords, "mode": "auto"}
    for key in ("brush", "brush_category", "pressure_curve",
                "pressure_variation", "variation_frequency",
                "variation_seed", "speed_sensitivity",
                "pressure_interpolation"):
        if key in selected:
            mark[key] = selected[key]
    return mark


def _coverage(intent, selected, width, height):
    polygon = intent["polygon"]
    spacing = intent["spacing"]
    radians = math.radians(intent["angle"])
    cosine, sine = math.cos(radians), math.sin(radians)
    transformed = [(cosine*x + sine*y, -sine*x + cosine*y)
                   for x, y in polygon]
    lo = min(v for _, v in transformed)
    hi = max(v for _, v in transformed)
    if (hi-lo)/spacing > MAX_EXPANDED_PER_INTENT:
        raise TaskError("Coverage intent exceeds 240 scanline rows")
    rng = random.Random(intent["seed"])
    result = []
    v = lo + spacing / 2
    while v < hi:
        row = min(hi - 0.000001, v + (rng.random()-.5)*spacing*intent["jitter"])
        intersections = []
        for a, b in zip(transformed, transformed[1:] + transformed[:1]):
            au, av = a
            bu, bv = b
            if (av <= row < bv) or (bv <= row < av):
                frac = (row-av)/(bv-av)
                intersections.append(au + frac*(bu-au))
        intersections.sort()
        if len(intersections) % 2:
            raise TaskError("Coverage polygon has inconsistent scanline intersections")
        for j in range(0, len(intersections), 2):
            left, right = intersections[j:j+2]
            if right-left < 1.0:
                continue
            a = _to_xy(left, row, cosine, sine, width, height)
            b = _to_xy(right, row, cosine, sine, width, height)
            if a["x"] != b["x"] or a["y"] != b["y"]:
                if len(result) % 2:
                    a, b = b, a
                midpoint = {"x": round((a["x"] + b["x"]) / 2, 4),
                            "y": round((a["y"] + b["y"]) / 2, 4)}
                coverage_style = dict(selected)
                coverage_style.setdefault("pressure_curve", [[0.0, 0.85], [1.0, 0.85]])
                result.append(_stroke([a, midpoint, b], coverage_style))
                if len(result) > MAX_EXPANDED_PER_INTENT:
                    raise TaskError("Coverage intent expands beyond 240 native strokes")
        v += spacing
    if not result:
        raise TaskError("Coverage intent produced no visible stroke")
    return result


def _point_at(path, distances, target):
    for i in range(1, len(path)):
        if target <= distances[i]:
            a, b = path[i-1], path[i]
            delta = distances[i]-distances[i-1]
            t = (target-distances[i-1])/delta if delta else 0
            x = a[0]+(b[0]-a[0])*t
            y = a[1]+(b[1]-a[1])*t
            norm = math.hypot(b[0]-a[0], b[1]-a[1])
            if norm:
                return x, y, (b[0]-a[0])/norm, (b[1]-a[1])/norm
    a, b = path[-2], path[-1]
    norm = math.hypot(b[0]-a[0], b[1]-a[1])
    return b[0], b[1], (b[0]-a[0])/norm, (b[1]-a[1])/norm


def _accents(intent, selected, subject):
    path = intent["path"]
    distances = [0.0]
    for a, b in zip(path, path[1:]):
        distances.append(distances[-1]+math.hypot(b[0]-a[0], b[1]-a[1]))
    if distances[-1] <= 0:
        raise TaskError("Accent guide is degenerate")
    rng = random.Random(intent["seed"])
    left, top, w, h = subject["bounds"]
    result = []
    for i in range(intent["count"]):
        base_t = (i+.5)/intent["count"]
        t = max(0, min(1, base_t+(rng.random()-.5)*intent["jitter"]/intent["count"]))
        x, y, dx, dy = _point_at(path, distances, distances[-1]*t)
        length = intent["length"]*(1+(rng.random()-.5)*intent["jitter"])
        start = {"x": round(max(left, min(left+w, x-dx*length/2)), 4),
                 "y": round(max(top, min(top+h, y-dy*length/2)), 4)}
        end = {"x": round(max(left, min(left+w, x+dx*length/2)), 4),
               "y": round(max(top, min(top+h, y+dy*length/2)), 4)}
        if start != end:
            result.append(_stroke([start, end], selected))
    if not result:
        raise TaskError("Accents intent produced no visible stroke")
    return result


def expand_intent(intent, selected_style, subject, document):
    """Expand a validated v4 intent into native v3 freehand brush elements."""
    kind = intent["kind"]
    if kind == "gesture":
        return [_stroke([{"x": x, "y": y} for x, y in intent["path"]], selected_style)]
    if kind == "coverage":
        return _coverage(intent, selected_style,
                         document["width"], document["height"])
    if kind == "accents":
        return _accents(intent, selected_style, subject)
    raise TaskError("Unsupported paint intent")
