import pytest

from krita_agent.scene_quality import validate
from krita_agent.scene_v2 import compile_plan
from krita_agent.protocol import TaskError


def scene():
    return {
        "schema": "krita-agent-scene/2",
        "document": {"width": 512, "height": 512},
        "layers": [
            {"name": "Sky", "role": "background", "elements": [
                {"kind": "rectangle", "rect": [0, 0, 512, 240]}
            ]},
            {"name": "Mountains", "role": "lineart", "elements": [
                {"kind": "stroke", "points": [
                    {"x": 0, "y": 240}, {"x": 180, "y": 120}, {"x": 512, "y": 260}
                ]}
            ]},
        ],
    }


def test_scene_quality_reports_native_content_and_hash():
    report = validate(scene(), min_painted_layers=2)
    assert report["status"] == "ready"
    assert report["metrics"]["painted_layer_count"] == 2
    assert report["metrics"]["stroke_count"] == 1
    assert report["metrics"]["shape_count"] == 1
    assert len(report["plan_sha256"]) == 64
    assert report["side_effects"] == "none; compile-only preflight"


def test_scene_quality_blocks_empty_or_underfilled_scenes():
    candidate = scene()
    candidate["layers"] = [candidate["layers"][0], {"name": "Empty", "role": "custom", "elements": []}]
    report = validate(candidate, min_painted_layers=2)
    assert report["status"] == "blocked"
    assert any("Only 1 layers" in error for error in report["errors"])
    assert "Empty" in report["warnings"][0]


def test_scene_quality_warns_about_out_of_canvas_coordinates():
    candidate = scene()
    candidate["layers"][1]["elements"][0]["points"][1]["x"] = 700
    report = validate(candidate)
    assert report["status"] == "ready"
    assert any("beyond the declared canvas" in warning for warning in report["warnings"])


def test_scene_v2_compiler_still_rejects_untrusted_commands():
    candidate = scene()
    candidate["layers"][0]["elements"] = [{"kind": "shell", "command": "whoami"}]
    with pytest.raises((TaskError, ValueError)):
        compile_plan(candidate)
