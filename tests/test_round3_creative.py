"""Structured scene planning regressions; NOT executed in implementation round."""
import pytest
from krita_agent.creative_plans import compile_scene
from krita_agent.protocol import TaskError


def test_scene_creates_layer_strokes_preview_and_checkpoint():
    plan = compile_scene({
        "document": {"width": 128, "height": 128},
        "layers": [{"name": "Ink",
                    "brush": {"size": 9, "color": "#123456"},
                    "elements": [
                        {"kind": "stroke", "points": [{"x": 0, "y": 0},
                                                       {"x": 12, "y": 18}]},
                        {"kind": "rectangle", "rect": [10, 10, 40, 30]}],
                    "preview": True}],
        "checkpoint": True,
    })
    names = [x["command"] for x in plan]
    assert names[0] == "canvas.create"
    assert "draw.stroke" in names and "draw.shape" in names
    assert "preview.canvas" in names
    assert names[-1] == "checkpoint.create"


def test_scene_rejects_unknown_shapes_and_size():
    with pytest.raises(TaskError):
        compile_scene({"layers": [{"name": "Ink", "elements": [{"kind": "shell"}]}]})
    with pytest.raises(TaskError):
        compile_scene({"document": {"width": 100000, "height": 20},
                       "layers": [{"name": "Ink", "elements": []}]})
