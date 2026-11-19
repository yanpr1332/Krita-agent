"""Opt-in Round 10 reference semantics from an explicitly authorized VLM.

Unlike pixel statistics, these are fallible *model hypotheses*, not actual
Krita painting or verified object detection. The user must separately permit
external upload and confirm per-source reuse rights; never silent network.
"""
from .protocol import TaskError, label, number
from .reference_assets_v10 import (validate_reference_manifest, analyze_references,
                                   _check_id, _rect, _safe_image)
from .scene_v3 import digest

SYSTEM = """Inspect the ACTUAL provided image pixels and respond ONLY with JSON:
{"schema":"krita-agent-reference-annotations/1","sources":[
{"source_id":"same_manifest_source_id","subjects":[
{"id":"simple-id","kind":"person/animal/room/object/etc",
"bounds":[normalized_x,normalized_y,normalized_width,normalized_height],
"materials":["fabric","skin"],"confidence":0.0}],
"visual_notes":"Short concrete observations of visible composition, perspective,
light and material uncertainty; no unseen content."}]}
All bounds are [0..1] image-relative and never infer a real subject outside
visible pixels. Avoid asserting visual facts without evidence. State
uncertainty; confidence is a self-estimate, not externally calibrated.
Do not output arbitrary commands, paths, image data, or copyrighted text.
Never suggest copying raster pixels into the Krita canvas.
"""


def annotate_references(root, manifest, provider, *, allow_external_upload=False):
    if allow_external_upload is not True:
        raise TaskError("Opt-in external image upload permission is required")
    normalized = validate_reference_manifest(manifest)
    if any(s["rights"]["external_upload_permitted"] is not True
           for s in normalized["sources"]):
        raise TaskError("Each reference must explicitly authorize external model upload")
    evidence = analyze_references(root, normalized)
    # Access to image bytes is scoped to known, safe files with bounded size.
    filenames = []
    for source in normalized["sources"]:
        _safe_image(root, source["file"])
        filenames.append(str(__import__("pathlib").Path(root) / source["file"]))
    prompt = (
        "Describe only what is genuinely visible in each image, respecting "
        "the source order and IDs: " +
        ", ".join(s["id"] for s in normalized["sources"]) +
        ". Each source ID must appear exactly once. No pasted-image output."
    )
    result = provider.complete_json(SYSTEM, prompt, image_paths=filenames)
    if not isinstance(result, dict) or set(result) != {"schema", "sources"} or result.get(
            "schema") != "krita-agent-reference-annotations/1":
        raise TaskError("Unrecognized visual annotation schema")
    rows = result["sources"]
    if not isinstance(rows, list) or len(rows) != len(normalized["sources"]):
        raise TaskError("Visual model did not report every provided reference")
    allowed = {s["id"] for s in normalized["sources"]}
    seen = set()
    output = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"source_id", "subjects", "visual_notes"}:
            raise TaskError("Unknown visual annotation fields")
        sid = _check_id(row.get("source_id"), "annotation source ID")
        if sid not in allowed or sid in seen:
            raise TaskError("Wrong or duplicate annotated reference source")
        seen.add(sid)
        subjects = row["subjects"]
        if not isinstance(subjects, list) or len(subjects) > 24:
            raise TaskError("Visual annotation exceeds 24 visible subjects")
        seen_subjects, interpreted = set(), []
        for s in subjects:
            if not isinstance(s, dict) or set(s) != {
                    "id", "kind", "bounds", "materials", "confidence"}:
                raise TaskError("Unknown visual subject annotation fields")
            ident = _check_id(s.get("id"), "annotated subject ID")
            if ident in seen_subjects:
                raise TaskError("Duplicate visual subject annotation")
            seen_subjects.add(ident)
            mats = s.get("materials")
            if not isinstance(mats, list) or not 1 <= len(mats) <= 8:
                raise TaskError("Visual material hypotheses require 1..8 entries")
            interpreted.append({
                "id": ident,
                "kind": label(s.get("kind"), "visual subject", 80),
                "bounds": _rect(s.get("bounds")),
                "materials": [label(m, "material hypothesis", 64) for m in mats],
                "confidence_uncalibrated": number(
                    s.get("confidence"), "model confidence", 0, 1),
            })
        output.append({
            "source_id": sid,
            "source_sha256": next(r["sha256"] for r in evidence["sources"]
                                  if r["source_id"] == sid),
            "subjects": interpreted,
            "visual_notes": label(row.get("visual_notes"), "observations", 1000),
        })
    payload = {
        "schema": "krita-agent-visual-hypotheses/1",
        "reference_analysis_sha256": evidence["analysis_sha256"],
        "model_id": label(getattr(provider, "model", "externally_provided"),
                          "provider model", 128),
        "sources": output,
        "model_api": "explicitly_called", "side_effects": "image_upload_only",
        "not_native_commands": True,
        "geometry_requires_manual_scene_mapping": True,
        "visual_observations_are_unverified_hypotheses": True,
        "artwork_accepted": False,
    }
    payload["sha256"] = digest(payload)
    return payload
