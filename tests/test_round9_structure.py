"""Round 9 generalized structure, constraint and revision checks.

All fixtures are synthetic. They do not assert finished-art quality, native
pressure compatibility, or automatic repair of anatomical details.
"""
import copy

import pytest

from krita_agent.protocol import TaskError
from krita_agent.scene_v3 import digest
from krita_agent.scene_v4 import validate_scene_v4, compile_scene_v4
from krita_agent.structure_v9 import (validate_structure_plan, diagnose_structure,
                                     structural_guide_intents)
from krita_agent.structure_revision_v9 import (propose_structure_fix,
                                              approve_structure_fix)


def fixture(genre="person", mode="paint"):
    scene = {
        "schema": "krita-agent-scene/4",
        "document": {"width": 128, "height": 128, "name": genre + " layout"},
        "style": "transparent structural thumbnail",
        "subjects": [{
            "id": "main", "name": genre + " subject", "kind": genre,
            "materials": ["paint"], "bounds": [10, 10, 100, 100],
            "depth": 0.7, "brush": {"color": "#994433", "size": 4.0},
        }],
        "stages": [
            {"id": "sketch", "phase": "sketch", "goal": "Check the subject silhouette",
             "intents": [{
                 "id": "contour", "kind": "gesture", "subject_id": "main",
                 "purpose": "Outline overall subject proportion",
                 "path": [[20, 24], [25, 88], [85, 93]],
             }]},
            {"id": "block", "phase": "block_in", "goal": "Fill the large form",
             "intents": [{
                 "id": "color", "kind": "coverage", "subject_id": "main",
                 "purpose": "Block the principal colored shape",
                 "polygon": [[30, 38], [74, 38], [74, 80], [30, 80]],
                 "spacing": 10, "angle": 0,
             }]},
            {"id": "detail", "phase": "detail", "goal": "Mark significant anatomy",
             "intents": [{
                 "id": "edges", "kind": "accents", "subject_id": "main",
                 "purpose": "Clarify a few important surface edges",
                 "path": [[34, 45], [65, 72]], "count": 3, "length": 8,
             }]},
        ],
        "structure": {
            "version": 1, "guide_mode": mode,
            "subjects": [{
                "subject_id": "main", "category": genre,
                "anchors": [
                    {"id": "top", "xy": [48, 24]},
                    {"id": "middle", "xy": [48, 56]},
                    {"id": "bottom", "xy": [55, 95]},
                ],
                "parts": [
                    {"id": "upper", "tag": "main_mass", "bounds": [28, 27, 44, 34],
                     "anchor_id": "top"},
                    {"id": "lower", "tag": "lower_mass", "bounds": [28, 61, 46, 28],
                     "parent": "upper", "anchor_id": "bottom"},
                ],
                "chains": [
                    {"id": "axis", "anchors": ["top", "middle", "bottom"],
                     "purpose": "Establish the main construction axis"},
                ],
                "expectations": [
                    {"tag": "main_mass", "min": 1, "max": 1},
                    {"tag": "lower_mass", "min": 1, "max": 1},
                ],
            }],
            "relations": [],
        },
    }
    return scene


@pytest.mark.parametrize("genre", [
    "person", "animal", "still_life", "architecture", "vehicle", "comic",
])
def test_six_genres_share_one_structure_validator_and_native_compiler(genre):
    source = fixture(genre)
    normalized = validate_scene_v4(source)
    assert normalized["structure"]["subjects"][0]["category"] == genre
    assert validate_scene_v4(normalized) == normalized
    compiled = compile_scene_v4(source)
    assert compiled["schema"] == "krita-agent-scene-compiled/4"
    assert compiled["structure_diagnostics"]["validated"]
    assert compiled["structure_diagnostics"]["rendered_skeleton_chains"] == 1
    assert len(compiled["stage_spans"]) == 3
    assert len(compiled["stage_layers"]) == 3
    assert compiled["steps"][0]["command"] == "canvas.create"
    assert all(item["command"] != "pixel.transaction.patch" for item in compiled["steps"])
    assert sum(s["command"] == "draw.stroke" for s in compiled["steps"]) > 3


def test_legacy_no_structure_scene_preserves_exact_lowered_commands():
    bare = fixture()
    bare.pop("structure")
    same = copy.deepcopy(bare)
    assert compile_scene_v4(bare)["steps"] == compile_scene_v4(same)["steps"]
    assert "structure_diagnostics" not in compile_scene_v4(bare)
    assert "structure" not in validate_scene_v4(bare)


def test_audit_only_does_not_secretly_paint_extra_guides():
    with_structure = fixture(mode="audit_only")
    no_structure = copy.deepcopy(with_structure)
    no_structure.pop("structure")
    assert structural_guide_intents(validate_scene_v4(with_structure)) == []
    assert compile_scene_v4(with_structure)["steps"] == compile_scene_v4(no_structure)["steps"]
    assert diagnose_structure(validate_scene_v4(with_structure))["requires_visual_review"]


def test_painted_guides_are_frozen_and_reproducible():
    compiled = compile_scene_v4(fixture())
    assert compiled["native_steps_sha256"] == compile_scene_v4(fixture())["native_steps_sha256"]
    assert compiled["source_v4_sha256"] == digest(validate_scene_v4(fixture()))
    assert len(structural_guide_intents(validate_scene_v4(fixture()))) == 1


def test_reject_anchor_outside_subject():
    source = fixture()
    source["structure"]["subjects"][0]["anchors"][0]["xy"] = [121, 24]
    with pytest.raises(TaskError, match="outside declared subject"):
        validate_scene_v4(source)


def test_reject_duplicate_anchor():
    source = fixture()
    source["structure"]["subjects"][0]["anchors"][1]["id"] = "top"
    with pytest.raises(TaskError, match="Duplicate structural anchor"):
        validate_scene_v4(source)


def test_reject_missing_structural_chain_endpoint():
    source = fixture()
    source["structure"]["subjects"][0]["chains"][0]["anchors"][0] = "missing"
    with pytest.raises(TaskError, match="missing anchor"):
        validate_scene_v4(source)


def test_reject_semantic_part_count_mismatch():
    source = fixture()
    source["structure"]["subjects"][0]["expectations"][0]["min"] = 2
    source["structure"]["subjects"][0]["expectations"][0]["max"] = 2
    with pytest.raises(TaskError, match="part-count"):
        validate_scene_v4(source)


def test_reject_part_outside_subject_and_undeclared_material():
    source = fixture()
    source["structure"]["subjects"][0]["parts"][0]["bounds"] = [5, 30, 44, 34]
    with pytest.raises(TaskError, match="Part bounds exceed"):
        validate_scene_v4(source)
    source = fixture()
    source["structure"]["subjects"][0]["parts"][0]["material"] = "imaginary"
    with pytest.raises(TaskError, match="material not declared"):
        validate_scene_v4(source)


def test_reject_part_parent_cycle():
    source = fixture()
    source["structure"]["subjects"][0]["parts"][0]["parent"] = "lower"
    with pytest.raises(TaskError, match="cyclic parent"):
        validate_scene_v4(source)


def test_reject_unknown_kind_and_incompatible_left_relation():
    source = fixture()
    source["subjects"].append({
        "id": "other", "name": "Other object", "kind": "object",
        "materials": ["paint"], "bounds": [65, 20, 50, 50], "depth": .4,
        "brush": {"color": "#556699", "size": 4},
    })
    source["structure"]["relations"] = [
        {"id": "left", "kind": "left_of", "a": "main", "b": "other"}
    ]
    with pytest.raises(TaskError, match="Left-of"):
        validate_scene_v4(source)
    source["structure"]["relations"][0]["kind"] = "invented"
    with pytest.raises(TaskError, match="Unknown semantic relationship"):
        validate_scene_v4(source)


def test_front_of_uses_declared_depth_and_emits_nonoverlap_warning():
    source = fixture()
    source["subjects"].append({
        "id": "other", "name": "Background object", "kind": "object",
        "materials": ["paint"], "bounds": [111, 12, 16, 60], "depth": .2,
        "brush": {"color": "#556699", "size": 4},
    })
    source["structure"]["relations"] = [
        {"id": "front", "kind": "front_of", "a": "main", "b": "other"}
    ]
    out = validate_scene_v4(source)
    assert diagnose_structure(out)["issues"][0]["code"] == "no_visible_occlusion"
    source["subjects"][1]["depth"] = .8
    with pytest.raises(TaskError, match="contradicts depth"):
        validate_scene_v4(source)


def test_attachment_requires_existing_subject_anchors_and_bounded_gap():
    source = fixture()
    source["subjects"].append({
        "id": "other", "name": "Attached object", "kind": "object",
        "materials": ["paint"], "bounds": [70, 10, 52, 100], "depth": .4,
        "brush": {"color": "#556699", "size": 4},
    })
    source["structure"]["subjects"].append({
        "subject_id": "other", "anchors": [{"id": "hook", "xy": [84, 56]}]
    })
    source["structure"]["subjects"][0]["anchors"].append({"id": "join", "xy": [84, 56]})
    source["structure"]["relations"] = [
        {"id": "attach", "kind": "attached", "a": "main", "b": "other",
         "anchor_a": "join", "anchor_b": "hook", "max_gap": 1}
    ]
    assert validate_scene_v4(source)["structure"]["relations"][0]["kind"] == "attached"
    source["structure"]["subjects"][1]["anchors"][0]["xy"] = [91, 56]
    with pytest.raises(TaskError, match="disconnected anchors"):
        validate_scene_v4(source)


def test_perspective_convergence_accepts_correct_ray_and_rejects_wrong_ray():
    source = fixture()
    source["structure"]["perspective"] = {
        "horizon_y": 64,
        "vanishing_points": [{"id": "vp", "xy": [120, 64]}],
        "rays": [{"id": "edge", "vanishing_point": "vp",
                  "start": [20, 80], "end": [70, 72],
                  "max_deviation_deg": 3}],
    }
    normalized = validate_scene_v4(source)
    assert validate_scene_v4(normalized) == normalized
    assert normalized["structure"]["perspective"]["rays"][0]["measured_deviation_deg"] == 0
    source["structure"]["perspective"]["rays"][0]["end"] = [70, 82]
    with pytest.raises(TaskError, match="does not converge"):
        validate_scene_v4(source)


def test_optional_perspective_vanishing_point_can_be_outside_canvas():
    source = fixture()
    source["structure"]["perspective"] = {
        "vanishing_points": [{"id": "far", "xy": [2000, 64]}],
        "rays": [{"id": "edge", "vanishing_point": "far",
                  "start": [20, 70], "end": [95, 70], "max_deviation_deg": 1}],
    }
    assert validate_scene_v4(source)["structure"]["perspective"]["vanishing_points"]


def test_revision_proposal_requires_explicit_approval_and_sha_binding():
    source = fixture()
    original_digest = digest(validate_scene_v4(source))
    proposal = propose_structure_fix(
        source, [{"subject_id": "main", "target": "anchor_xy",
                  "id": "middle", "value": [49, 57]}],
        "Correct spine axis while preserving all native layers",
        expected_sha256=original_digest)
    assert proposal["source_sha256"] == original_digest
    assert proposal["native_effects"] == "none"
    assert proposal["approval"] == "required"
    assert source["structure"]["subjects"][0]["anchors"][1]["xy"] == [48, 56]
    with pytest.raises(TaskError, match="confirmation"):
        approve_structure_fix(source, proposal)
    reviewed = approve_structure_fix(source, proposal, confirm=True)
    assert reviewed["structure"]["subjects"][0]["anchors"][1]["xy"] == [49.0, 57.0]
    assert digest(reviewed) == proposal["candidate_sha256"]
    assert compile_scene_v4(reviewed)["schema"] == "krita-agent-scene-compiled/4"


def test_revision_rejects_stale_source_and_tampered_candidate():
    source = fixture()
    proposal = propose_structure_fix(
        source, [{"subject_id": "main", "target": "anchor_xy",
                  "id": "middle", "value": [49, 57]}],
        "Correct spine axis without changing the stored art")
    with pytest.raises(TaskError, match="Stale"):
        propose_structure_fix(source, proposal["edits"], "Stale", expected_sha256="0"*64)
    tampered = copy.deepcopy(proposal)
    tampered["candidate"]["structure"]["subjects"][0]["anchors"][1]["xy"] = [52, 57]
    with pytest.raises(TaskError, match="changed after proposal"):
        approve_structure_fix(source, tampered, confirm=True)
    shifted = fixture()
    shifted["style"] = "another style"
    with pytest.raises(TaskError, match="Original scene changed"):
        approve_structure_fix(shifted, proposal, confirm=True)


@pytest.mark.parametrize("target", ["anchor", "part", "subject"])
def test_revision_refuses_user_locked_geometry(target):
    source = fixture()
    row = source["structure"]["subjects"][0]
    if target == "anchor":
        row["anchors"][1]["locked"] = True
    if target == "part":
        row["parts"][0]["locked"] = True
    if target == "subject":
        row["locked"] = True
    edit = ({"subject_id": "main", "target": "part_bounds", "id": "upper",
             "value": [29, 28, 43, 34]} if target == "part" else
            {"subject_id": "main", "target": "anchor_xy", "id": "middle",
             "value": [49, 57]})
    with pytest.raises(TaskError, match="locked"):
        propose_structure_fix(source, [edit], "Preserve locked user geometry")


def test_revision_rejects_geometry_outside_subject():
    source = fixture()
    with pytest.raises(TaskError, match="outside declared subject"):
        propose_structure_fix(
            source, [{"subject_id": "main", "target": "anchor_xy",
                      "id": "middle", "value": [127, 57]}],
            "Move backbone beyond legal subject bounds")


def test_structure_rejects_oversized_guide_budget():
    source = fixture()
    base = source["structure"]["subjects"][0]["chains"][0]
    source["structure"]["subjects"][0]["chains"] = [
        dict(base, id="axis%d" % i) for i in range(9)
    ]
    with pytest.raises(TaskError, match="structural chains"):
        validate_scene_v4(source)


def test_structural_issues_do_not_claim_artwork_visual_acceptance():
    report = diagnose_structure(validate_scene_v4(fixture()))
    assert report["requires_visual_review"] is True
    assert "artwork_accepted" not in report
    assert report["subject_count"] == 1
    assert report["part_count"] == 2
