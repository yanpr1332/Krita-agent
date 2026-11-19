"""Round 10 — evidence-grounded *hypotheses* for reusable brush technique.

The source image is user-authorized and read locally. Measurable edge-tangent
orientation/contrast and region palette become a tentative R8 recipe; material
family and category are deliberately AUTHOR-declared, never AI-predicted.
The result is NOT evidence of painterly skill or visual likeness.
"""
import math
from pathlib import Path

from .protocol import TaskError, integer, label
from .reference_assets_v10 import (
    analyze_references, validate_reference_manifest, _safe_image,
)
from .technique_library_v10 import validate_technique

MATERIAL_HINT = {
    "water": ("ripples", "linear", ("coverage", "accents")),
    "glass": ("specular", "linear", ("coverage", "accents")),
    "metal": ("specular", "linear", ("coverage", "accents")),
    "fabric": ("folds", "growth", ("coverage", "gesture")),
    "cloth": ("folds", "growth", ("coverage", "gesture")),
    "hair": ("strands", "growth", ("gesture", "accents")),
    "fur": ("strands", "growth", ("gesture", "accents")),
    "ceramic": ("planes", "radial", ("coverage", "accents")),
    "stone": ("facets", "radial", ("coverage", "accents")),
    "rock": ("facets", "radial", ("coverage", "accents")),
    "wood": ("growth", "growth", ("coverage", "gesture")),
    "foliage": ("growth", "growth", ("coverage", "accents")),
    "cloud": ("wisps", "linear", ("coverage", "accents")),
    "sky": ("wash", "linear", ("coverage", "gesture")),
    "skin": ("wash", "radial", ("coverage", "accents")),
}


def _tangent_direction(image, roi):
    """Classify image edge tangent direction, not actual visible brush motion."""
    image = image.convert("L")
    x, y, w, h = roi
    l = int(x * image.width)
    t = int(y * image.height)
    r = max(l + 1, min(image.width, math.ceil((x+w)*image.width)))
    b = max(t + 1, min(image.height, math.ceil((y+h)*image.height)))
    segment = image.crop((l,t,r,b))
    segment.thumbnail((128, 128))
    pixels = segment.load()
    weights = [0.0,0.0,0.0,0.0]
    supported = 0
    for py in range(1, segment.height-1):
        for px in range(1, segment.width-1):
            dx = float(pixels[px+1,py]-pixels[px-1,py])
            dy = float(pixels[px,py+1]-pixels[px,py-1])
            strength = math.hypot(dx,dy)
            if strength < 18:
                continue
            tangent = math.degrees(math.atan2(dx,-dy)) % 180
            bucket = int(round(tangent / 45)) % 4
            weights[bucket] += strength
            supported += 1
    total = sum(weights)
    if total <= 0:
        return {"angle": 0.0, "anisotropy": 0.0, "samples": 0,
                "status": "indeterminate_no_oriented_edges"}
    winner = max(range(4), key=lambda i: weights[i])
    return {
        "angle": float(winner*45),
        "anisotropy": round(weights[winner]/total, 4),
        "samples": supported,
        "status": "image_edge_tangent_proxy_not_brush_detection",
    }


def extract_technique_hypothesis(root, manifest, *, source_id, region_id,
                                  profile_id, version=1, material=None,
                                  phase="material"):
    """Create a valid, reusable *hypothesis* profile from measured pixels."""
    normalized = validate_reference_manifest(manifest)
    proof = analyze_references(root, normalized)
    source = next((s for s in normalized["sources"] if s["id"] == source_id), None)
    data = next((s for s in proof["sources"] if s["source_id"] == source_id), None)
    if source is None or data is None or not any(
            role in source["roles"] for role in ("material", "technique")):
        raise TaskError("Technique source lacks declared material/technique rights")
    roi = next((r for r in source["regions"] if r["id"] == region_id), None)
    measure = next((r["measurements"] for r in data["regions"]
                    if r["id"] == region_id), None)
    if roi is None or measure is None:
        raise TaskError("Technique requires explicit analyzed reference ROI")
    mat = label(material or roi["material"], "declared technique material", 64)
    if roi["material"] and mat != roi["material"]:
        raise TaskError("Technique material contradicts manually labeled ROI")
    if phase not in ("block_in", "form", "material", "detail", "polish"):
        raise TaskError("Unsupported technique inference painting phase")
    image, _, actual_sha = _safe_image(root, source["file"])
    if actual_sha != data["sha256"]:
        raise TaskError("Reference changed between visual analysis and profile proposal")
    orientation = _tangent_direction(image, roi["rect"])
    choice = MATERIAL_HINT.get(mat.lower())
    technique, flow, kinds = choice or (
        "wash", "linear", ("coverage", "gesture"))
    edge = measure["edge_density_proxy"]
    spacing = max(5, min(60, round(26-17*edge)))
    length = max(8, min(100, round(28+36*(1-edge))))
    palette = [p["hex"] for p in measure["dominant_palette"][:5]]
    if not palette:
        raise TaskError("No measured color palette for technique hypothesis")
    p = {
        "schema": "krita-agent-technique/1",
        "id": profile_id,
        "version": integer(version, "technique version", 1, 9999),
        "title": "Reference hypothesis: " + mat,
        "materials": [mat],
        "subjects": [roi["subject_id"]] if roi["subject_id"] else [],
        "phases": [phase],
        "intent_kinds": list(kinds),
        "render": {
            "technique": technique, "flow": flow,
            "angle": orientation["angle"], "spacing": spacing, "length": length,
            "layers": 1 if edge < .2 else 2,
            "irregularity": .12 + .12*min(1,edge),
            "placement": "blue_noise", "palette": palette,
        },
        "brush": {},
        "provenance": {
            "source_id": source_id,
            "source_sha256": actual_sha,
            "rights_basis": source["rights"]["basis"],
            "source_note": source["rights"]["source_note"],
        },
        "status": "hypothesis",
        "evidence": ["analysis:" + proof["analysis_sha256"]],
        "limitations": (
            "Heuristic only: the material label was declared by the author; "
            "edge tangents are not measured brush strokes, and canvas-specific "
            "length, spacing, pressure, preset and lighting remain unverified. "
            "Actual native/human artwork acceptance required."
        ),
        "builds": [],
    }
    result = validate_technique(p)
    result["orientation_support"] = orientation
    result["reference_analysis_sha256"] = proof["analysis_sha256"]
    # These are explanation fields outside the storable library schema.
    # Only result['profile'] is valid for immutable saving/application.
    profile = {k:v for k,v in result.items()
               if k not in ("orientation_support","reference_analysis_sha256")}
    return {
        "schema": "krita-agent-technique-extraction/1",
        "profile": profile,
        "analysis_sha256": proof["analysis_sha256"],
        "image_orientation": orientation,
        "material_label_source": "human_authored_region",
        "technique_choice": "declared_material_default_hypothesis",
        "model_api": "not_called",
        "native_effects": "none", "artwork_accepted": False,
    }
