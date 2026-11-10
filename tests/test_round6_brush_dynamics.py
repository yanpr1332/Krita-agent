"""Round 6 deterministic per-stroke brush flexibility and bounded diagnostics.

Controller-only fixtures: not proof of native Krita rendering or artistic quality.
"""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from krita_agent.brush_dynamics import pressure_samples, validate_style
from krita_agent.protocol import TaskError
from krita_agent.scene_v3 import compile_scene_v3, digest, validate_scene
from krita_agent.stroke_quality import analyze_scene
from test_round5_creative_scene import sample_scene


def styled_scene():
    scene = sample_scene()
    cloud = scene["objects"][1]
    cloud["min_strokes"] = 3
    cloud["styles"] = {
        "wash": {
            "brush": {"size": 75, "color": "#a997b6", "opacity": 0.28},
            "pressure_curve": [[0, 0.12], [0.18, 0.65], [0.65, 0.88], [1, 0.13]],
            "pressure_variation": 0.07, "variation_frequency": 3.5,
            "variation_seed": 17,
        },
        "edge": {
            "brush": {"size": 5, "color": "#f6e4ba", "opacity": 0.86},
            "pressure_curve": [[0, 0.05], [0.3, 0.94], [1, 0.08]],
        },
    }
    cloud["elements"] = [
        {"kind": "stroke", "style": "wash", "points": [
            {"x": 40, "y": 80, "time_ms": 0},
            {"x": 95, "y": 66, "time_ms": 60, "speed": 0.2},
            {"x": 180, "y": 70, "time_ms": 140},
        ]},
        {"kind": "stroke", "style": "edge", "points": [
            {"x": 52, "y": 50, "time_ms": 0},
            {"x": 125, "y": 48, "time_ms": 90},
            {"x": 205, "y": 57, "time_ms": 170},
        ]},
        {"kind": "stroke", "style": "wash", "brush": {"size": 31}, "points": [
            {"x": 80, "y": 94}, {"x": 190, "y": 110}, {"x": 330, "y": 88},
        ]},
    ]
    return scene


def test_color_size_opacity_change_between_native_continuous_strokes():
    compiled = compile_scene_v3(styled_scene())
    steps = compiled["steps"]
    start = next(i for i, s in enumerate(steps)
                 if s["command"] == "layer.create"
                 and s["parameters"]["name"].startswith("clouds -"))
    end = next(i for i in range(start+1, len(steps))
               if steps[i]["command"] == "layer.create")
    segment = steps[start:end]
    strokes = [s for s in segment if s["command"] == "draw.stroke"]
    brushes = [s["parameters"] for s in segment if s["command"] == "brush.configure"]
    assert len(strokes) == 3
    assert len(brushes) == 4  # base, wash, edge, modified wash
    assert [b["size"] for b in brushes] == [36.0, 75.0, 5.0, 31.0]
    assert brushes[1]["color"] == "#a997b6"
    assert brushes[2]["color"] == "#f6e4ba"
    assert brushes[2]["opacity"] == 0.86
    assert all(s["parameters"]["mode"] == "auto" for s in strokes)
    assert compiled["brush_diagnostics"]["distinct_scene_colors"] >= 4


def test_named_style_resolution_determinism_and_source_hash_idempotence():
    scene = styled_scene()
    one = compile_scene_v3(scene)
    two = compile_scene_v3(deepcopy(scene))
    assert one["native_steps_sha256"] == two["native_steps_sha256"]
    normalized = validate_scene(scene)
    assert digest(normalized) == digest(validate_scene(normalized))
    assert scene["objects"][1]["elements"][0]["points"][0].get("pressure") is None


def test_pressure_curve_uses_arc_length_and_author_override_policy():
    raw = [{"x": 0, "y": 0, "pressure": 0.95},
           {"x": 10, "y": 0, "pressure": 0.95},
           {"x": 90, "y": 0, "pressure": 0.95}]
    style = validate_style({
        "pressure_curve": [[0, 0.1], [0.5, 0.9], [1, 0.2]],
        "pressure_interpolation": "linear",
    })
    result = pressure_samples(raw, (0.2, 0.6, 0.2), style)
    assert [p["pressure"] for p in result] == pytest.approx([0.1, 0.277778, 0.2], abs=1e-5)
    preserved = pressure_samples(raw, (0.2, 0.6, 0.2), {})
    assert [p["pressure"] for p in preserved] == [0.95, 0.95, 0.95]


def test_deterministic_variation_and_speed_sensor_bounds():
    raw = [{"x": i*10, "y": 0, "speed": i/8} for i in range(9)]
    style = validate_style({
        "pressure_curve": [[0, 0.2], [0.45, 0.94], [1, 0.25]],
        "pressure_variation": 0.23, "variation_frequency": 6,
        "variation_seed": 47, "speed_sensitivity": 0.5,
    })
    a = pressure_samples(raw, (0.2, 0.6, 0.2), style)
    b = pressure_samples(raw, (0.2, 0.6, 0.2), style)
    assert a == b
    assert len({p["pressure"] for p in a}) >= 6
    assert all(0 <= p["pressure"] <= 1 for p in a)
    assert a[-1]["pressure"] < 0.25


def test_bezier_can_have_its_own_pressure_curve_and_brush():
    scene = sample_scene()
    scene["objects"][1]["elements"] = [{
        "kind": "bezier", "samples": 30,
        "controls": [[40, 60], [100, 30], [180, 100], [240, 70]],
        "brush": {"size": 7, "color": "#fff0bb"},
        "pressure_curve": [[0, 0.1], [0.25, 0.9], [1, 0.2]],
    }]
    compiled = compile_scene_v3(scene)
    strokes = [s for s in compiled["steps"] if s["command"] == "draw.stroke"]
    curve = strokes[1]["parameters"]["points"]
    assert len(curve) >= 30
    assert curve[0]["pressure"] == pytest.approx(0.1)
    assert curve[-1]["pressure"] == pytest.approx(0.2)
    assert any(s["command"] == "brush.configure" and s["parameters"].get("size") == 7
               for s in compiled["steps"])


@pytest.mark.parametrize("mutate,match", [
    (lambda s: s["objects"][1]["elements"][0].update(style="missing"), "named stroke style"),
    (lambda s: s["objects"][1]["styles"]["wash"].update(pressure_curve=[[0, 0.2], [0.6, 0.8]]),
     "begin at 0 and end at 1"),
    (lambda s: s["objects"][1]["styles"]["edge"].update(pressure_variation=0.8),
     "pressure variation"),
    (lambda s: s["objects"][1]["styles"]["wash"].update(no_command="shell"), "Unknown stroke-style"),
    (lambda s: s["objects"][1]["elements"][0].update(brush={"size": -1}), "brush size"),
    (lambda s: s["objects"][1].update(min_strokes=7), "min_strokes"),
    (lambda s: s["objects"][1]["elements"][0].update(brush_category="not-real"), "category"),
])
def test_unsafe_or_incomplete_stroke_styles_fail_closed(mutate, match):
    scene = styled_scene()
    mutate(scene)
    with pytest.raises(TaskError, match=match):
        compile_scene_v3(scene)


def test_calibrated_stroke_category_refuses_missing_build():
    scene = styled_scene()
    scene["objects"][1]["elements"][0]["brush_category"] = "texture"
    with pytest.raises(TaskError, match="profile directory"):
        compile_scene_v3(scene)


def test_large_single_object_plan_exceeds_old_240_element_limit():
    scene = sample_scene()
    points = [{"x": 5, "y": 15}, {"x": 200, "y": 40}]
    scene["objects"][0]["elements"] = [
        {"kind": "stroke", "points": points} for _ in range(410)
    ]
    plan = compile_scene_v3(scene)
    assert sum(s["command"] == "draw.stroke" for s in plan["steps"]) == 412
    assert len(plan["steps"]) < 10000


def test_adaptive_diagnostics_flag_uniform_large_area_and_repetition():
    scene = sample_scene()
    obj = scene["objects"][0]
    obj["elements"] = [
        {"kind": "stroke", "points": [
            {"x": 10, "y": 20+i}, {"x": 300, "y": 20+i}
        ]} for i in range(25)
    ]
    report = analyze_scene(validate_scene(scene))
    sky = next(row for row in report["objects"] if row["id"] == "sky")
    assert sky["distinct_sizes"] == 1  # planned default brush size
    assert sky["stroke_count"] == 25
    assert any("one effective color" in warning for warning in report["warnings"])
    assert report["not_artwork_acceptance"]


def test_committed_multistyle_example_compiles_with_distinct_materials():
    example = (Path(__file__).resolve().parents[1]
               / "examples/round6-multistyle-scene.json")
    plan = compile_scene_v3(json.loads(example.read_text(encoding="utf-8")))
    report = plan["brush_diagnostics"]
    assert report["total_strokes"] >= 9
    assert report["distinct_scene_sizes"] >= 5
    assert report["distinct_scene_colors"] >= 6
    assert plan["not_artwork_acceptance"] is True


def test_palette_dynamics_override_and_default_brush_restoration():
    scene = styled_scene()
    cloud = scene["objects"][1]
    cloud["elements"][0]["pressure_variation"] = 0.0
    cloud["elements"].append({"kind": "stroke", "points": [
        {"x": 40, "y": 120}, {"x": 240, "y": 125}
    ]})
    cloud["min_strokes"] = 4
    plan = compile_scene_v3(scene)
    steps = plan["steps"]
    start = next(i for i, step in enumerate(steps) if step["command"] == "layer.create"
                 and step["parameters"]["name"].startswith("clouds -"))
    end = next(i for i in range(start+1, len(steps))
               if steps[i]["command"] == "layer.create")
    brushes = [step["parameters"] for step in steps[start:end]
               if step["command"] == "brush.configure"]
    assert [brush["size"] for brush in brushes] == [36.0, 75.0, 5.0, 31.0, 36.0]
    assert brushes[-1]["color"] == "#d59aa6"
    strokes = [step["parameters"]["points"] for step in steps[start:end]
               if step["command"] == "draw.stroke"]
    assert strokes[0][0]["pressure"] == pytest.approx(0.12)
    assert len(strokes) == 4


def test_reject_partial_brush_without_restorable_baseline():
    from krita_agent.creative_plans import compile_scene
    candidate = {"layers": [{"name": "No baseline",
                             "elements": [
                                 {"kind": "stroke", "brush": {"color": "#111111"},
                                  "points": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]},
                                 {"kind": "stroke",
                                  "points": [{"x": 3, "y": 3}, {"x": 4, "y": 4}]},
                             ]}]}
    with pytest.raises(TaskError, match="baseline"):
        compile_scene(candidate)



def test_curve_saturating_at_one_remains_stable_when_revalidated():
    scene = styled_scene()
    stroke = scene["objects"][1]["elements"][0]
    stroke.pop("style")
    stroke["pressure_curve"] = [[0, 0.15], [0.5, 1], [1, 0.15]]
    stroke["points"] = [
        {"x": 40, "y": 80}, {"x": 100, "y": 80}, {"x": 160, "y": 80}
    ]
    normalized = validate_scene(scene)
    assert normalized["objects"][1]["elements"][0]["points"][1]["pressure"] == 1.0
    assert digest(normalized) == digest(validate_scene(normalized))
    from krita_agent.creative_director import compile_approved
    compile_approved({"schema": "krita-agent-creative-proposal/1",
                      "scene": normalized, "scene_sha256": digest(normalized)})
