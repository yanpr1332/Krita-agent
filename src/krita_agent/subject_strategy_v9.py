"""Round 9: material + geometry + phase guidance without scene-specific recipes.

Strategies are inspectable recommendations, not automatic artistry, raster
generation, or permission to call the Krita Bridge.
"""
from .protocol import TaskError

# Material-family hints may be expanded; none forces a fixed subject ontology.
# Every suggestion names one of the existing Round 8 material techniques.
MATERIAL_HINTS = {
    "skin": ("wash", "planes", "specular"),
    "fabric": ("folds", "wash", "contour"),
    "cloth": ("folds", "wash", "contour"),
    "water": ("ripples", "wash", "specular"),
    "ceramic": ("planes", "wash", "specular"),
    "metal": ("specular", "planes", "contour"),
    "glass": ("specular", "contour", "wash"),
    "wood": ("planes", "growth", "contour"),
    "plaster": ("wash", "planes", "contour"),
    "grass": ("growth", "wisps", "wash"),
    "foliage": ("growth", "wisps", "wash"),
    "hair": ("strands", "contour", "wash"),
    "fur": ("strands", "growth", "wash"),
    "stone": ("facets", "planes", "wash"),
    "rock": ("facets", "planes", "wash"),
    "paint": ("wash", "contour", "planes"),
}
PHASE_GOALS = {
    "sketch": "resolve subject anchor positions, silhouette and major joints",
    "block_in": "establish distinct large value and color masses",
    "form": "resolve surface orientation, depth and volume transitions",
    "material": "select material-specific native brush recipe and light direction",
    "detail": "refine silhouette breaks, joints, necessary accents and identity",
    "polish": "check edges, negative spaces, readability and visual hierarchy",
}


def subject_strategy(scene, subject_id):
    """Return deterministic guidance grounded in the actual scene structure."""
    subjects = scene.get("subjects", [])
    target = next((s for s in subjects if s["id"] == subject_id), None)
    if target is None:
        raise TaskError("Unknown structural strategy subject ID")
    structure = scene.get("structure") or {}
    struct = next((s for s in structure.get("subjects", [])
                   if s["subject_id"] == subject_id), None)
    perspective = structure.get("perspective") or {}
    interactions = [r for r in structure.get("relations", [])
                    if subject_id in (r["a"], r["b"])]
    materials = []
    for material in target["materials"]:
        material_key = material.lower()
        picked = MATERIAL_HINTS.get(material_key)
        materials.append({
            "material": material,
            "techniques": list(picked or ("wash", "contour", "planes")),
            "known_material_hint": picked is not None,
            "requires_visual_calibration": True,
        })
    stage_order = [s["phase"] for s in scene["stages"]]
    anchors = len(struct["anchors"]) if struct else 0
    parts = len(struct["parts"]) if struct else 0
    occlusion = sum(r["kind"] == "front_of" for r in interactions)
    needs_structure_review = anchors < 2 or (
        target["kind"].lower().find("person") >= 0 and parts < 2)
    return {
        "schema": "krita-agent-subject-strategy/1",
        "subject_id": subject_id,
        "subject_kind": target["kind"],
        "subject_materials": materials,
        "structural_anchors": anchors,
        "semantic_parts": parts,
        "relationships": len(interactions),
        "occlusion_constraints": occlusion,
        "perspective_ray_count": len(perspective.get("rays", [])),
        "stage_goals": [{"phase": p, "goal": PHASE_GOALS[p]} for p in stage_order],
        "flags": {
            "needs_structure_review": needs_structure_review,
            "needs_occlusion_review": bool(occlusion),
            "needs_perspective_review": bool(perspective.get("rays")),
            "requires_real_krita_material_acceptance": True,
        },
        "artwork_accepted": False,
        "not_native_commands": True,
    }


def all_subject_strategies(scene):
    return {
        "schema": "krita-agent-subject-strategy-collection/1",
        "subjects": [subject_strategy(scene, s["id"]) for s in scene["subjects"]],
        "not_artwork_acceptance": True,
    }
