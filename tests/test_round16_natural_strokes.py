"""Round 16 natural stroke geometry tests. These are NOT native Krita visuals."""
from copy import deepcopy
import math

import pytest

from krita_agent.native_continuity_v13 import inspect_stroke_continuity
from krita_agent.natural_strokes_v16 import (
    natural_points, validate_natural,
)
from krita_agent.protocol import TaskError
from krita_agent.scene_v3 import digest
from krita_agent.scene_v4 import (
    compile_scene_v4, lower_scene_v4, validate_scene_v4,
)
from krita_agent.semantic_planning_v14 import compile_semantic
from test_round14_semantic_planning import brief, proposal
from test_round7_generalist_scene import sample_v4


PATH = [[10, 50], [25, 20], [55, 18], [80, 45], [90, 55]]
BOUNDS = [0, 0, 100, 100]


def test_natural_pressure_and_position_have_real_within_stroke_variation():
    settings = {"purpose": "contour", "spacing": 2.0,
                "smoothing_passes": 1}
    a = natural_points(PATH, settings, BOUNDS)
    b = natural_points(deepcopy(PATH), deepcopy(settings), BOUNDS)
    assert a == b
    assert len(a) > len(PATH)
    assert a[0]["x"] == PATH[0][0] and a[0]["y"] == PATH[0][1]
    assert a[-1]["x"] == PATH[-1][0] and a[-1]["y"] == PATH[-1][1]
    assert all(0 <= p["x"] <= 100 and 0 <= p["y"] <= 100 for p in a)
    assert all(0.02 <= p["pressure"] <= 1 for p in a)
    assert max(p["pressure"] for p in a) > a[0]["pressure"] + .25
    assert max(p["pressure"] for p in a) > a[-1]["pressure"] + .25
    assert len({p["pressure"] for p in a}) > 8
    assert [p["time_ms"] for p in a] == list(range(0, len(a)*16, 16))


def test_natural_profile_is_bounded_idempotent_and_deterministic():
    a = validate_natural({"purpose": "fur"})
    assert validate_natural(a) == a
    assert a["end_pressure"] < a["peak_pressure"]
    assert len(natural_points([[1,1],[99,99]], a, BOUNDS)) <= 2048
    assert natural_points([[1,1],[99,99]], a, BOUNDS) == (
        natural_points([[1,1],[99,99]], a, BOUNDS))


@pytest.mark.parametrize("patch,match", [
    ({"command":"image.import"}, "Unsupported natural stroke fields"),
    ({"purpose":"model-paints-it"}, "Unsupported natural stroke purpose"),
    ({"spacing":.2}, "stroke spacing"),
    ({"smoothing_passes":5}, "smoothing passes"),
    ({"start_pressure":0}, "start_pressure"),
    ({"peak_pressure":.1,"start_pressure":.6}, "peak pressure"),
    ({"corner_relief":.6}, "corner relief"),
])
def test_natural_settings_fail_closed(patch, match):
    with pytest.raises(TaskError, match=match):
        validate_natural(patch)


@pytest.mark.parametrize("path,bounds,match", [
    ([[0,0]], BOUNDS, "2..128"),
    ([[0,0],[120,20]], BOUNDS, "leaves its approved bbox"),
    ([[0,0],[0,0]], BOUNDS, "Consecutive duplicate"),
    ([[0,0],[10,10]], [0,0,0,100], "bbox is invalid"),
    ([[0,0],[True,10]], BOUNDS, "leaves its approved bbox"),
    ([[0,0],[float("inf"),10]], BOUNDS, "leaves its approved bbox"),
])
def test_invalid_geometry_fails_without_emitting_native_actions(path, bounds, match):
    with pytest.raises(TaskError, match=match):
        natural_points(path, {}, bounds)


def test_sampling_budget_is_strict_and_not_silently_truncated():
    # A high-resolution winding line can exceed 2048 native samples.
    path = [[i*5, 500+math.sin(i)*250] for i in range(100)]
    with pytest.raises(TaskError, match="2048"):
        natural_points(path, {"spacing": .75, "smoothing_passes": 2},
                       [0,0,500,1000])


def test_round16_semantic_strokes_are_natural_but_region_fill_is_r15():
    comp, plan, scene = compile_semantic(proposal(), brief())
    assert plan["status"] == "structural_scaffold_only"
    assert all(i["kind"] == "region" for i in scene["stages"][1]["intents"])
    for phase in (0, 2):
        for intent in scene["stages"][phase]["intents"]:
            assert intent["kind"] == "gesture"
            assert intent["natural"]["purpose"] in (
                "contour", "fine_detail", "fur")
            assert "pressure_curve" not in intent
    assert scene == validate_scene_v4(scene)
    lowered, rows = lower_scene_v4(scene)
    a = next(o for o in lowered["objects"] if o["id"] == "s00_cat")
    assert a["elements"][0]["kind"] == "stroke"
    pts = a["elements"][0]["points"]
    assert len(pts) > 13
    assert len({round(p["pressure"],3) for p in pts}) > 6
    assert pts[0]["pressure"] != pts[len(pts)//2]["pressure"]
    assert all("pressure" in p and "time_ms" in p for p in pts)
    compiled = compile_scene_v4(scene)
    assert compiled["not_artwork_acceptance"] is True
    assert compiled["requires_native_approval"] is True
    assert compiled["source_sha256"] == digest(lowered)
    assert [s["phase"] for s in compiled["stage_spans"]] == [
        "sketch", "block_in", "detail"]


def test_mixed_v4_legacy_remains_deterministic_and_unchanged():
    old = sample_v4()
    assert compile_scene_v4(old)["source_v4_sha256"] == (
        compile_scene_v4(deepcopy(old))["source_v4_sha256"])
    assert "natural" not in str(old)
    # Opt-in route doesn't require model or dynamic host brush extensions.
    result = inspect_stroke_continuity([{
        "command": "draw.stroke", "parameters": {
            "points": natural_points(PATH, {}, BOUNDS), "mode": "auto"}}],
        {"symbols": {"Node.paintPolylineStroke": False,
                     "StrokePoint": False}})
    assert result["segmented_join_risk_strokes"] == 1
    assert result["continuous_visual_response_verified"] is False


def test_natural_intent_cannot_compete_with_other_pressure_rules():
    candidate = sample_v4()
    gesture = candidate["stages"][0]["intents"][0]
    gesture["natural"] = {"purpose": "contour"}
    gesture["pressure_curve"] = [[0,.2],[1,.7]]
    with pytest.raises(TaskError, match="competing pressure"):
        validate_scene_v4(candidate)
    del gesture["pressure_curve"]
    assert validate_scene_v4(candidate)["stages"][0]["intents"][0]["natural"]
