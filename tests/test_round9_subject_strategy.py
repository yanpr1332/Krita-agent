"""Round 9 strategies cannot silently change Krita plans or claim art approval."""
import copy

import pytest

from krita_agent.protocol import TaskError
from krita_agent.scene_v4 import validate_scene_v4, compile_scene_v4
from krita_agent.subject_strategy_v9 import subject_strategy, all_subject_strategies
from test_round9_structure import fixture


def test_strategy_combines_material_phase_part_geometry_without_native_effect():
    scene = validate_scene_v4(fixture("animal", mode="audit_only"))
    original = copy.deepcopy(scene)
    report = subject_strategy(scene, "main")
    assert report["schema"] == "krita-agent-subject-strategy/1"
    assert report["subject_materials"][0]["techniques"] == ["wash", "contour", "planes"]
    assert report["structural_anchors"] == 3
    assert report["semantic_parts"] == 2
    assert [row["phase"] for row in report["stage_goals"]] == ["sketch", "block_in", "detail"]
    assert report["not_native_commands"] and not report["artwork_accepted"]
    assert scene == original


def test_unknown_material_family_falls_back_to_bounded_generic_technique():
    source = fixture()
    source["subjects"][0]["materials"] = ["unknown_matte_finish"]
    source["structure"]["subjects"][0]["parts"][0]["material"] = "unknown_matte_finish"
    source["structure"]["subjects"][0]["parts"][1]["material"] = "unknown_matte_finish"
    scene = validate_scene_v4(source)
    material = subject_strategy(scene, "main")["subject_materials"][0]
    assert not material["known_material_hint"]
    assert material["techniques"] == ["wash", "contour", "planes"]


def test_strategy_rejects_unknown_subject_without_native_side_effect():
    scene = validate_scene_v4(fixture())
    with pytest.raises(TaskError, match="Unknown structural strategy"):
        subject_strategy(scene, "imaginary")
    result = all_subject_strategies(scene)
    assert result["not_artwork_acceptance"]
    assert len(result["subjects"]) == 1
    compiled = compile_scene_v4(scene)
    assert len(compiled["subject_strategies"]["subjects"]) == 1
