"""Public Round 9 structural studies are bounded integration fixtures, not art scores."""
import json
from pathlib import Path

import pytest

from krita_agent.scene_v4 import validate_scene_v4, compile_scene_v4


@pytest.mark.parametrize("name", [
    "round9-figure-and-room.json",
    "round9-perspective-interior.json",
])
def test_reviewed_examples_compile_and_preserve_native_intents(name):
    path = Path(__file__).parents[1] / "examples" / name
    source = json.loads(path.read_text(encoding="utf-8"))
    scene = validate_scene_v4(source)
    compiled = compile_scene_v4(scene)
    assert compiled["structure_diagnostics"]["validated"]
    assert compiled["structure_diagnostics"]["rendered_skeleton_chains"] >= 2
    assert len(compiled["stage_spans"]) == 3
    assert 6 <= sum(x["command"] == "draw.stroke" for x in compiled["steps"])
    assert compiled["native_steps_sha256"] == compile_scene_v4(scene)["native_steps_sha256"]
    assert compiled["requires_native_approval"] is True
