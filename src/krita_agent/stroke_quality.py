"""Controller-only brush diversity and detail-budget diagnostics.

These measures describe stroke plans, not pixel quality or artistic acceptance.
They never synthesize paintings or claim that Krita actually rendered them.
"""
import math
from collections import Counter

from .strategies_v3 import SIZES


def _signature(points):
    if len(points) < 2:
        return None
    first, last = points[0], points[-1]
    dx, dy = last["x"]-first["x"], last["y"]-first["y"]
    distance = math.hypot(dx, dy)
    return (round(math.atan2(dy, dx)*6/math.pi),
            round(distance/12), round(first["x"]/12), round(first["y"]/12))


def analyze_scene(scene):
    results = []
    global_colors = set()
    global_sizes = set()
    warnings = []
    for obj in scene["objects"]:
        colors, sizes, opacities, presets = set(), set(), set(), set()
        pressures = []
        directions = set()
        signatures = Counter()
        painted = 0
        point_count = 0
        for element in obj["elements"]:
            if element["kind"] not in ("stroke", "bezier"):
                continue
            painted += 1
            brush = {"size": SIZES[obj["kind"]], "opacity": 0.95,
                     **obj.get("brush", {}), **element.get("brush", {})}
            if "color" in brush:
                colors.add(brush["color"].lower())
                global_colors.add(brush["color"].lower())
            if "size" in brush:
                sizes.add(round(brush["size"], 2))
                global_sizes.add(round(brush["size"], 2))
            if "opacity" in brush:
                opacities.add(round(brush["opacity"], 3))
            if "preset" in brush:
                presets.add(brush["preset"])
            samples = element.get("points", [])
            point_count += len(samples) if samples else element.get("samples", 0)
            pressures.extend(p["pressure"] for p in samples)
            geometry = samples or [
                {"x": x, "y": y} for x, y in (
                    element.get("controls", [])[:1] + element.get("controls", [])[-1:]
                )
            ]
            signature = _signature(geometry)
            if signature:
                signatures[signature] += 1
                directions.add(signature[0])
        area = obj["bounds"][2]*obj["bounds"][3]
        density = round(painted*10000/area, 3)
        duplicates = sum(v-1 for v in signatures.values() if v>1)
        spread = round(max(pressures)-min(pressures), 5) if pressures else None
        rows = {
            "id": obj["id"], "kind": obj["kind"],
            "stroke_count": painted, "min_strokes": obj.get("min_strokes", 1),
            "point_count": point_count,
            "strokes_per_10000_bbox_px": density,
            "distinct_colors": len(colors), "distinct_sizes": len(sizes),
            "distinct_opacities": len(opacities), "distinct_presets": len(presets),
            "pressure_span": spread, "direction_bins": len(directions),
            "repeated_trajectory_signatures": duplicates,
        }
        if painted >= 12 and len(sizes) < 2:
            warnings.append(obj["id"] + ": all strokes have one effective brush size")
        if painted >= 18 and len(colors) < 2:
            warnings.append(obj["id"] + ": all strokes have one effective color")
        if painted >= 18 and spread is not None and spread < 0.12:
            warnings.append(obj["id"] + ": little pressure variation")
        if painted >= 12 and duplicates*3 >= painted:
            warnings.append(obj["id"] + ": many geometrically repetitive trajectories")
        if area >= 50000 and painted < 8:
            warnings.append(obj["id"] + ": large region has very few native strokes")
        results.append(rows)
    return {
        "schema": "krita-agent-brush-diagnostics/1",
        "objects": results,
        "total_strokes": sum(o["stroke_count"] for o in results),
        "distinct_scene_colors": len(global_colors),
        "distinct_scene_sizes": len(global_sizes),
        "warnings": warnings,
        "status": "diagnostic_only",
        "not_artwork_acceptance": True,
    }
