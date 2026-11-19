"""Round 8 rendered-pixel and stroke-shape diagnostics (informational only).

Diagnostics inspect real Krita-exported PNG files or safe compiled brush plans.
Neither one judges artwork acceptance or fabricates preview images.
"""
import hashlib
import math
from collections import Counter
from pathlib import Path

from .protocol import TaskError


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _shape(points):
    if len(points) < 2:
        return None
    first, last = points[0], points[-1]
    distance = math.hypot(last["x"]-first["x"], last["y"]-first["y"])
    if distance < .01:
        return None
    heading = math.atan2(last["y"]-first["y"], last["x"]-first["x"])
    signed_curvature, arclength = 0.0, 0.0
    last_angle = None
    for a, b in zip(points, points[1:]):
        dx, dy = b["x"]-a["x"], b["y"]-a["y"]
        step = math.hypot(dx, dy)
        if step < .000001:
            continue
        angle = math.atan2(dy, dx)
        if last_angle is not None:
            signed_curvature += (angle-last_angle+math.pi)%(2*math.pi)-math.pi
        last_angle = angle
        arclength += step
    return (
        round(distance/8), round(arclength/max(.01, distance)*8),
        round(signed_curvature*4/math.pi), round(heading*9/math.pi),
    )


def plan_mark_diagnostics(scene):
    """Detect potential repeats using geometry, not just brush/stroke counts."""
    if not isinstance(scene, dict) or not isinstance(scene.get("objects"), list):
        raise TaskError("A compiled or normalized v3 scene is required")
    results = []
    for obj in scene["objects"]:
        signatures = Counter()
        directions = Counter()
        lengths = []
        mark_count = 0
        for item in obj.get("elements", []):
            if item.get("kind") != "stroke":
                continue
            points = item.get("points", [])
            shape = _shape(points)
            if shape is None:
                continue
            mark_count += 1
            signatures[shape] += 1
            directions[shape[-1]] += 1
            lengths.append(math.hypot(points[-1]["x"]-points[0]["x"],
                                      points[-1]["y"]-points[0]["y"]))
        repeated = sum(max(0, n-1) for n in signatures.values())
        mean = sum(lengths)/len(lengths) if lengths else 0
        spread = (math.sqrt(sum((x-mean)**2 for x in lengths)/len(lengths))/mean
                  if mean else 0)
        largest = max(directions.values()) if directions else 0
        record = {
            "object_id": obj.get("id"),
            "brush_strokes": mark_count,
            "repeated_shape_fraction": round(repeated/max(1,mark_count), 4),
            "dominant_direction_fraction": round(largest/max(1,mark_count), 4),
            "length_coefficient_of_variation": round(spread, 4),
            "notes": [],
        }
        if mark_count >= 8 and repeated/max(1,mark_count) >= .4:
            record["notes"].append("Repeated geometric stroke shapes; visually inspect purpose")
        if mark_count >= 8 and largest/max(1,mark_count) >= .8:
            record["notes"].append("Strongly uniform orientation; may be intentional graphic style")
        results.append(record)
    return {"schema": "krita-agent-material-plan-qc/1", "objects": results,
            "artwork_accepted": False, "actual_pixels_inspected": False}


def compare_actual_pngs(before, after, max_pixels=32000000):
    """Pixel delta from two supplied REAL images; no synthetic render or art pass."""
    from PIL import Image, ImageChops
    a, b = Path(before), Path(after)
    for p in (a, b):
        if not p.is_file() or p.suffix.lower() != ".png":
            raise TaskError("Real PNG file required for rendered pixel diagnostics")
        if p.stat().st_size > 256*1024*1024:
            raise TaskError("Pixel evidence file exceeds 256 MiB")
    with Image.open(a) as old, Image.open(b) as new:
        if old.size != new.size:
            raise TaskError("Native stages have inconsistent dimensions")
        w, h = old.size
        if w*h > max_pixels:
            raise TaskError("Stage PNG exceeds pixel QA budget")
        before_color = {"mode": old.mode, "icc_sha256": (
            hashlib.sha256(old.info["icc_profile"]).hexdigest()
            if old.info.get("icc_profile") else None)}
        after_color = {"mode": new.mode, "icc_sha256": (
            hashlib.sha256(new.info["icc_profile"]).hexdigest()
            if new.info.get("icc_profile") else None)}
        lhs, rhs = old.convert("RGBA"), new.convert("RGBA")
        delta = ImageChops.difference(lhs, rhs)
        # Loop over actual decoded pixel tuples; transparent RGB must still count
        # as a difference, because strict Reopen Stability has no tolerance.
        changed, alpha_changed, maximum, rgb_sum = 0, 0, 0, 0
        pixel_rows = (delta.get_flattened_data() if hasattr(delta, "get_flattened_data")
                      else delta.getdata())
        for channels in pixel_rows:
            if any(channels):
                changed += 1
                if channels[3]:
                    alpha_changed += 1
                maximum = max(maximum, *channels)
                rgb_sum += sum(channels[:3])
        fraction = changed/(w*h)
        notes = []
        if fraction < .001:
            notes.append("Tiny stage-to-stage pixel contribution; inspect whether intended detail is missing")
        if before_color != after_color:
            notes.append("Color modes or ICC bytes differ; inspect native color settings")
        return {
            "schema": "krita-agent-real-stage-delta/1",
            "source_png_sha256": _sha(a),
            "target_png_sha256": _sha(b),
            "width": w, "height": h,
            "changed_rgba_pixels": changed,
            "changed_fraction": round(fraction, 8),
            "changed_alpha_pixels": alpha_changed,
            "maximum_channel_difference": maximum,
            "mean_rgb_delta_per_canvas_pixel": round(rgb_sum/(3*w*h), 6),
            "before_color": before_color, "after_color": after_color,
            "notes": notes, "artwork_accepted": False,
        }


def compare_actual_region(before, after, bounds, canvas_size):
    """Count actual changed pixels in one approved subject rectangle.

    A subject ROI may overlap another subject. This reports local evidence,
    NOT which layer or artist is responsible and NOT artwork completeness.
    """
    from PIL import Image, ImageChops
    if (not isinstance(bounds, list) or len(bounds) != 4
            or not isinstance(canvas_size, (list, tuple)) or len(canvas_size) != 2):
        raise TaskError("Invalid subject pixel region")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds):
        raise TaskError("Invalid subject bound")
    width, height = canvas_size
    if (type(width) is not int or type(height) is not int
            or width <= 0 or height <= 0):
        raise TaskError("Invalid approved source canvas")
    x, y, w, h = bounds
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x+w > width or y+h > height:
        raise TaskError("Subject pixel region escapes approved canvas")
    with Image.open(before) as a, Image.open(after) as b:
        if a.size != b.size:
            raise TaskError("Stage dimensions differ for subject region")
        iw, ih = a.size
        box = (
            max(0, min(iw, math.floor(x*iw/width))),
            max(0, min(ih, math.floor(y*ih/height))),
            max(0, min(iw, math.ceil((x+w)*iw/width))),
            max(0, min(ih, math.ceil((y+h)*ih/height))),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            raise TaskError("Subject region is smaller than one native preview pixel")
        old = a.convert("RGBA").crop(box)
        new = b.convert("RGBA").crop(box)
        diff = ImageChops.difference(old, new)
        px = diff.get_flattened_data() if hasattr(diff, "get_flattened_data") else diff.getdata()
        changed = sum(any(channels) for channels in px)
        total = (box[2]-box[0])*(box[3]-box[1])
    return {"native_preview_roi": list(box),
            "changed_pixels": changed,
            "region_pixels": total,
            "changed_fraction": round(changed/total, 8),
            "note": "Overlapping subject regions are not layer-level attribution"}


def archived_stage_diagnostics(root, artifacts, stage_spans, subjects=None, canvas_size=None):
    """Hash-bound stage comparison from existing immutable CreativeWorkflow artifacts."""
    if not isinstance(artifacts, dict) or not isinstance(stage_spans, list):
        raise TaskError("Missing stage preview archive or stage plan")
    base = Path(root).resolve()
    paths = []
    for span in stage_spans:
        index, phase = span.get("index"), span.get("phase")
        if type(index) is not int or not isinstance(phase, str):
            raise TaskError("Invalid stage identity")
        name = "stage-%02d-%s.png" % (index+1, phase)
        entry = artifacts.get(name)
        if not isinstance(entry, dict) or entry.get("path") != "stages/"+name:
            raise TaskError("Native stage preview is missing: " + name)
        path = (base/entry["path"]).resolve()
        if base not in path.parents or not path.is_file() or _sha(path) != entry.get("sha256"):
            raise TaskError("Stage preview changed after archive: " + name)
        paths.append((name, path))
    rows = []
    for (left_name, before), (right_name, after) in zip(paths, paths[1:]):
        row = {"from_stage": left_name, "to_stage": right_name,
               "pixels": compare_actual_pngs(before, after)}
        if subjects is not None:
            if canvas_size is None:
                raise TaskError("Subject diagnostics need approved canvas dimensions")
            row["subject_roi_deltas"] = [
                {"subject_id": subject["id"],
                 **compare_actual_region(before, after, subject["bounds"], canvas_size)}
                for subject in subjects
            ]
        rows.append(row)
    return {"schema": "krita-agent-archived-stage-qc/1",
            "stages_verified": len(paths), "transitions": rows,
            "artwork_accepted": False,
            "notice": "Real pixel diagnostics are informational, not independent visual or human art judgement"}
