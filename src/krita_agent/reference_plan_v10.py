"""Round 10 — provenance-bound reference study -> reviewed native ScenePlan v4.

The deterministic path can transfer *measured colors* into manually authored
scene subjects; it cannot detect objects, poses, or learned stroke techniques.
More complicated composition/structure changes require a validated user/model
candidate rather than hidden pixel extraction or silent geometric warping.
"""
from copy import deepcopy

from .protocol import TaskError, label
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4, compile_scene_v4
from .reference_assets_v10 import analyze_references

MODES = frozenset(("palette_repaint", "material_study", "structure_study",
                   "free_adaptation"))
NATIVE_FORBIDDEN = frozenset(("image.import", "reference.import", "pixel.fill",
                             "pixel.clear", "image.paste", "draw.shape"))


def _verify_analysis(analysis):
    if not isinstance(analysis, dict) or analysis.get("schema") != "krita-agent-reference-analysis/1":
        raise TaskError("Missing genuine reference analysis")
    expected = analysis.get("analysis_sha256")
    value = dict(analysis)
    value.pop("analysis_sha256", None)
    if not isinstance(expected, str) or digest(value) != expected:
        raise TaskError("Reference analysis was modified after image measurement")
    sources = analysis.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 4:
        raise TaskError("Invalid reference evidence source list")
    if any(s.get("rights", {}).get("permission_confirmed") is not True
           or not isinstance(s.get("sha256"), str) or len(s["sha256"]) != 64
           for s in sources):
        raise TaskError("Reference evidence lacks confirmed permission/source SHA")
    return {s["source_id"]: s for s in sources}


def _verify_bindings(scene, sources, bindings):
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= 24:
        raise TaskError("Reference plan needs 1..24 explicit subject bindings")
    subject_ids = {s["id"] for s in scene["subjects"]}
    locked = {s["subject_id"] for s in (scene.get("structure") or {}).get("subjects", [])
              if s["locked"]}
    chosen, normalized = set(), []
    for b in bindings:
        if not isinstance(b, dict) or set(b) - {
                "subject_id", "source_id", "region_id", "role"}:
            raise TaskError("Invalid reference subject binding")
        sid, src_id, role = b.get("subject_id"), b.get("source_id"), b.get("role")
        if sid not in subject_ids or sid in locked:
            raise TaskError("Reference binding targets unknown/user-locked subject")
        source = sources.get(src_id)
        if source is None or role not in ("palette", "material", "composition", "structure"):
            raise TaskError("Reference binding uses invalid source/role")
        if role not in source["roles"]:
            raise TaskError("Reference does not permit requested reuse role")
        region_id = b.get("region_id")
        roi = None
        if region_id is not None:
            roi = next((r for r in source["regions"] if r["id"] == region_id), None)
            if roi is None:
                raise TaskError("Reference ROI ID was not analyzed")
            if roi.get("subject_id") is not None and roi["subject_id"] != sid:
                raise TaskError("Reference ROI is assigned to a different subject")
        key = (sid, role)
        if key in chosen:
            raise TaskError("Ambiguous second reference binding for same subject/role")
        chosen.add(key)
        normalized.append({
            "subject_id": sid, "source_id": src_id,
            "region_id": region_id, "role": role,
            "source_sha256": source["sha256"],
            "measurements": roi["measurements"] if roi else source["global_measurements"],
        })
    return normalized


def propose_reference_repaint(scene, analysis, bindings, *, mode="palette_repaint",
                              candidate_scene=None, rationale="Review authorized reference"):
    """Produce a new source-bound scene; never execute native or upload images."""
    source_scene = validate_scene_v4(scene)
    sources = _verify_analysis(analysis)
    if mode not in MODES:
        raise TaskError("Unknown authorized reference repaint mode")
    bound = _verify_bindings(source_scene, sources, bindings)
    reason = label(rationale, "reference study rationale", 240)
    if mode in ("palette_repaint", "material_study"):
        if candidate_scene is not None:
            raise TaskError("Color-only studies cannot smuggle alternate scene geometry")
        if any(b["role"] not in ("palette", "material") for b in bound):
            raise TaskError("Color study requires a palette/material-specific binding")
        out = deepcopy(source_scene)
        subject_by_id = {s["id"]: s for s in out["subjects"]}
        changes = []
        for b in bound:
            palette = b["measurements"]["dominant_palette"]
            if not palette:
                raise TaskError("Reference has no measured palette")
            color = palette[0]["hex"]
            subject = subject_by_id[b["subject_id"]]
            old_color = subject["brush"]["color"]
            subject["brush"]["color"] = color
            if mode == "material_study":
                # Existing MATERIAL technique is chosen by the painter, not guessed
                # from histogram; only its explicit palette gets bound to evidence.
                for stage in out["stages"]:
                    for intent in stage["intents"]:
                        if (intent["subject_id"] == b["subject_id"] and
                                isinstance(intent.get("render"), dict)):
                            intent["render"]["palette"] = [
                                entry["hex"] for entry in palette[:4]]
            changes.append({"subject_id": subject["id"],
                            "old_color": old_color, "new_color": color,
                            "source_id": b["source_id"], "role": b["role"],
                            "palette_is_measured": True,
                            "material_technique_inferred": False})
    else:
        # Structural semantics are not derivable from low-level histograms.
        # They must arrive as a user-authored/reviewable candidate ScenePlan.
        if candidate_scene is None:
            raise TaskError("Composition/structure study requires an explicit candidate scene")
        out = validate_scene_v4(candidate_scene)
        if out["document"] != source_scene["document"]:
            raise TaskError("Reference candidate may not change approved canvas")
        if {s["id"] for s in out["subjects"]} != {
                s["id"] for s in source_scene["subjects"]}:
            raise TaskError("Reference candidate changes protected subject identities")
        if mode == "structure_study" and not any(b["role"] in (
                "structure", "composition") for b in bound):
            raise TaskError("Structural study needs actual structure/composition provenance")
        changes = [{"kind": "reviewed_candidate",
                    "geometry_claim": "user_or_model_authored_not_pixel_inferred"}]
    out = validate_scene_v4(out)
    compiled = compile_scene_v4(out)
    if any(x["command"] in NATIVE_FORBIDDEN for x in compiled["steps"]):
        raise TaskError("A reference study attempted raster paste/non-brush commands")
    return {
        "schema": "krita-agent-reference-proposal/1",
        "mode": mode,
        "rationale": reason,
        "source_scene_sha256": digest(source_scene),
        "reference_analysis_sha256": analysis["analysis_sha256"],
        "reference_source_sha256": {key: s["sha256"] for key, s in sources.items()},
        "bindings": [{k: v for k, v in b.items() if k != "measurements"} for b in bound],
        "scene": out, "scene_sha256": digest(out),
        "compiled_native_steps_sha256": compiled["native_steps_sha256"],
        "changes": changes,
        "approval": "required", "side_effects": "none",
        "native_draw": "requires_separate_existing_stage_approval",
        "artwork_accepted": False,
    }


def approve_reference_repaint(original_scene, manifest, reference_root,
                              proposal, *, confirm=False):
    """Fail closed if the real image or candidate changed before approval."""
    if confirm is not True:
        raise TaskError("Explicit confirmation required before using reference plan")
    if not isinstance(proposal, dict) or proposal.get(
            "schema") != "krita-agent-reference-proposal/1":
        raise TaskError("Invalid reference proposal")
    if proposal.get("approval") != "required" or proposal.get("side_effects") != "none":
        raise TaskError("Reference plan has unexpected authority")
    source = validate_scene_v4(original_scene)
    if digest(source) != proposal.get("source_scene_sha256"):
        raise TaskError("Original scene changed after reference analysis")
    live = analyze_references(reference_root, manifest)
    if live["analysis_sha256"] != proposal.get("reference_analysis_sha256"):
        raise TaskError("Reference pixels, consent, or ROIs changed after proposal")
    candidate = validate_scene_v4(proposal.get("scene"))
    if digest(candidate) != proposal.get("scene_sha256"):
        raise TaskError("Reference candidate was modified after proposal")
    compiled = compile_scene_v4(candidate)
    if compiled["native_steps_sha256"] != proposal.get("compiled_native_steps_sha256"):
        raise TaskError("Native compiled reference plan changed after approval")
    if any(s["command"] in NATIVE_FORBIDDEN for s in compiled["steps"]):
        raise TaskError("Reference approval cannot authorize image pasting")
    return candidate
