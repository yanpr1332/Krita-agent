"""Round 9: bounded, reviewable *structure* fixes with no native side effect.

A reviewer may propose changing a named anchor or semantic part box.
Every proposal is hash-bound to the exact prior ScenePlan v4, validates the
whole result and requires a separate explicit approval before it can be
used as a future drawing plan. It never repaints, deletes layers, auto-runs
Krita or overwrites the original scene.
"""
from copy import deepcopy

from .protocol import TaskError, label
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4


def propose_structure_fix(source, edits, rationale, *, expected_sha256=None):
    scene = validate_scene_v4(source)
    if "structure" not in scene:
        raise TaskError("A structure fix requires an explicit Round 9 plan")
    old_sha = digest(scene)
    if expected_sha256 is not None and expected_sha256 != old_sha:
        raise TaskError("Stale source plan: cannot revise an unknown revision")
    if not isinstance(edits, list) or not 1 <= len(edits) <= 8:
        raise TaskError("Propose 1..8 bounded structural fixes")
    explanation = label(rationale, "structural correction rationale", 240)
    changed = deepcopy(scene)
    by_subject = {s["subject_id"]: s for s in changed["structure"]["subjects"]}
    used = set()
    issues = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"subject_id", "target", "id", "value"}:
            raise TaskError("Structure fix requires subject_id, target, id and value")
        sid = edit["subject_id"]
        subject = by_subject.get(sid)
        if subject is None or subject["locked"]:
            raise TaskError("Cannot revise a missing or user-locked structured subject")
        target = edit["target"]
        if target not in ("anchor_xy", "part_bounds"):
            raise TaskError("Only anchor positions and part bounds can be revised")
        key = (sid, target, edit["id"])
        if key in used:
            raise TaskError("Duplicate edit target")
        used.add(key)
        rows = subject["anchors"] if target == "anchor_xy" else subject["parts"]
        row = next((x for x in rows if x["id"] == edit["id"]), None)
        if row is None or row["locked"]:
            raise TaskError("Cannot revise a missing or user-locked anchor or part")
        field = "xy" if target == "anchor_xy" else "bounds"
        old_value = row[field]
        new_value = edit["value"]
        if not isinstance(new_value, list):
            raise TaskError("Structure fix must supply numeric coordinates")
        row[field] = list(new_value)
        issues.append({
            "subject_id": sid, "target": target, "id": edit["id"],
            "before": old_value, "after": list(new_value),
            "stage": "sketch",
        })
    validated = validate_scene_v4(changed)
    if digest(validated) == old_sha:
        raise TaskError("The structural fix did not change the source")
    # Preserve every old native layer and published image: only emit a future
    # plan candidate. No arbitrary command strings or plugin calls.
    return {
        "schema": "krita-agent-structure-fix-proposal/1",
        "source_sha256": old_sha,
        "candidate_sha256": digest(validated),
        "candidate": validated,
        "edits": issues,
        "reason": explanation,
        "stage_to_revisit": "sketch",
        "approval": "required",
        "native_effects": "none",
        "original_artifacts_immutable": True,
    }


def approve_structure_fix(source, proposal, *, confirm=False):
    if confirm is not True:
        raise TaskError("Explicit human confirmation required for structure fix")
    if not isinstance(proposal, dict) or proposal.get(
            "schema") != "krita-agent-structure-fix-proposal/1":
        raise TaskError("Unknown structure fix proposal")
    scene = validate_scene_v4(source)
    if digest(scene) != proposal.get("source_sha256"):
        raise TaskError("Original scene changed after review")
    result = validate_scene_v4(proposal.get("candidate"))
    if digest(result) != proposal.get("candidate_sha256"):
        raise TaskError("Structure fix candidate changed after proposal")
    if not isinstance(proposal.get("edits"), list) or not proposal["edits"]:
        raise TaskError("Structure fix must contain a source-bound diff")
    if proposal.get("approval") != "required" or proposal.get("native_effects") != "none":
        raise TaskError("Structure fix proposal has unexpected side effects")
    return result
