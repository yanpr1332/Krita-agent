"""Evidence-bound review validation for complete-artwork acceptance.

These checks validate that review records refer to the exact local artifacts.
They do not decide whether an image is aesthetically or semantically good.
"""
from datetime import datetime


VISUAL_SCHEMA = "krita-agent-artwork-vlm/2"
HUMAN_SCHEMA = "krita-agent-artwork-human/2"


def _timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _text(value, minimum=12):
    return isinstance(value, str) and len(value.strip()) >= minimum


def validate_visual_review(review, required_objects, required_relations,
                           reference_sha256, artwork_sha256, kra_sha256,
                           stage_sha256):
    errors = []
    if not isinstance(review, dict):
        return {"valid": False, "errors": ["Visual review must be an object"]}
    if review.get("schema") != VISUAL_SCHEMA:
        errors.append("Visual review schema must be " + VISUAL_SCHEMA)
    if review.get("decision") != "pass" or review.get("coherent_full_scene") is not True:
        errors.append("Visual reviewer did not approve a coherent full scene")
    if not _text(review.get("model"), 2) or not _timestamp(review.get("reviewed_at")):
        errors.append("Visual review model or timestamp is missing")
    if review.get("reference_sha256") != reference_sha256:
        errors.append("Visual review is not bound to the locked benchmark reference")
    if review.get("artwork_png_sha256") != artwork_sha256:
        errors.append("Visual review is not bound to the final PNG")
    inputs = review.get("reviewed_inputs", {})
    if inputs.get("artwork_kra_sha256") != kra_sha256:
        errors.append("Visual review is not bound to the editable KRA")
    if inputs.get("stage_previews") != stage_sha256:
        errors.append("Visual review stage-preview hashes do not match the run")
    objects = review.get("objects", {})
    evidence = review.get("object_evidence", {})
    for key in required_objects:
        if objects.get(key) is not True:
            errors.append("Required object not approved: " + key)
        if not _text(evidence.get(key)):
            errors.append("Missing visible evidence for object: " + key)
    relation_rows = review.get("relations", [])
    relation_map = {}
    if isinstance(relation_rows, list):
        for row in relation_rows:
            if isinstance(row, dict) and isinstance(row.get("description"), str):
                if row["description"] in relation_map:
                    errors.append("Duplicate relation review: " + row["description"])
                relation_map[row["description"]] = row
    else:
        errors.append("Relations must be an array")
    for relation in required_relations:
        row = relation_map.get(relation)
        if not row or row.get("passes") is not True or not _text(row.get("evidence")):
            errors.append("Required relation lacks positive visual evidence: " + relation)
    if review.get("failure_modes") not in ([], None):
        errors.append("Visual review records unresolved failure modes")
    if not _text(review.get("notes"), 20):
        errors.append("Visual review notes are too short to be auditable")
    return {"valid": not errors, "errors": errors}


def validate_human_review(review, artwork_sha256, kra_sha256, required_objects):
    errors = []
    if not isinstance(review, dict):
        return {"valid": False, "errors": ["Human review must be an object"]}
    if review.get("schema") != HUMAN_SCHEMA:
        errors.append("Human review schema must be " + HUMAN_SCHEMA)
    if review.get("decision") != "pass" or review.get("coherent_full_scene") is not True:
        errors.append("Human reviewer did not approve a coherent full scene")
    if review.get("artwork_png_sha256") != artwork_sha256:
        errors.append("Human review is not bound to the final PNG")
    if review.get("artwork_kra_sha256") != kra_sha256:
        errors.append("Human review is not bound to the editable KRA")
    if not _text(review.get("reviewer"), 2) or not _timestamp(review.get("reviewed_at")):
        errors.append("Human reviewer identity or timestamp is missing")
    if review.get("kra_reopened_and_viewed") is not True:
        errors.append("Human reviewer did not confirm reopening and viewing the KRA")
    if review.get("all_required_objects_recognizable") is not True:
        errors.append("Human reviewer did not confirm all required objects")
    object_checks = review.get("object_checks", {})
    for key in required_objects:
        if object_checks.get(key) is not True:
            errors.append("Human review did not approve object: " + key)
    if not _text(review.get("observations"), 40):
        errors.append("Human observations must contain at least 40 characters")
    return {"valid": not errors, "errors": errors}
