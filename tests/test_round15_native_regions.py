"""R15 source-only native filled-region tests, not a substitute for Krita T3.

Mocked bridge execution and compiled shape commands are OFFLINE evidence.
The user-directed final concentrated native/artwork acceptance is deferred.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from krita_agent import creative_workflow as workflow_module
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.native_regions_v15 import (
    inspect_native_regions, require_supported_regions, requires_native_regions,
)
from krita_agent.protocol import TaskError
from krita_agent.scene_v4 import compile_scene_v4, lower_scene_v4, validate_scene_v4
from krita_agent.semantic_planning_v14 import compile_semantic
from test_bridge_native import dispatcher
from test_round14_semantic_planning import proposal, brief
from test_round7_generalist_scene import sample_v4


def compiled_semantic():
    _, plan, scene = compile_semantic(proposal(), brief())
    return plan, scene, compile_scene_v4(scene)


def test_semantic_block_in_uses_genuine_native_filled_shapes_not_broad_scans():
    plan, scene, compiled = compiled_semantic()
    assert plan["status"] == "structural_scaffold_only"
    assert scene == validate_scene_v4(scene)
    assert all(intent["kind"] == "region" for intent in scene["stages"][1]["intents"])
    assert all("spacing" not in intent and "render" not in intent
               for intent in scene["stages"][1]["intents"])
    span = compiled["stage_spans"][1]
    part = compiled["steps"][span["start"]:span["stop"]]
    fills = [step for step in part if step["command"] == "draw.shape"]
    assert len(fills) == len(scene["subjects"])
    assert all(item["parameters"]["shape"] == "polygon" and
               item["parameters"]["fill"] == "ForegroundColor" for item in fills)
    assert not any(s["command"] == "draw.stroke" for s in part)
    assert not any(s["command"] in ("image.import", "reference.import")
                   for s in compiled["steps"])
    assert compiled["requires_native_approval"] is True
    assert compiled["not_artwork_acceptance"] is True
    # Each filled area is an editable Krita paint-layer operation.
    assert sum(s["command"] == "layer.create" for s in part) == len(fills)


def test_native_polygon_fill_reaches_allowlisted_krita_paint_polygon():
    node = SimpleNamespace(paintPolygon=Mock())
    execute = dispatcher({
        "Krita": SimpleNamespace(instance=lambda: None),
        "_points": lambda p: [(q["x"], q["y"]) for q in p],
    })
    bridge = SimpleNamespace(_node=lambda: node)
    steps = compiled_semantic()[2]["steps"]
    step = next(s for s in steps if s["command"] == "draw.shape"
                and s["parameters"]["fill"] == "ForegroundColor")
    result = execute(bridge, step["command"], step["parameters"])
    assert result == {"shape": "polygon"}
    node.paintPolygon.assert_called_once()
    args = node.paintPolygon.call_args.args
    assert len(args[0]) >= 3
    assert args[1:] == ("ForegroundColor", "ForegroundColor")


def test_manual_v4_region_can_mix_with_legacy_brush_intents():
    scene = sample_v4()
    original = scene["stages"][1]["intents"][0]
    polygon = original["polygon"]
    # Keep only validated region-specific fields.
    scene["stages"][1]["intents"][0] = {
        "id": original["id"], "subject_id": original["subject_id"],
        "kind": "region", "purpose": "Fill the actual subject geometry with base color",
        "polygon": polygon,
    }
    validated = validate_scene_v4(scene)
    assert validated == validate_scene_v4(validated)
    lowered, _ = lower_scene_v4(validated)
    assert any(element["kind"] == "polygon" and
               element["fill"] == "ForegroundColor"
               for item in lowered["objects"] for element in item["elements"])
    compiled = compile_scene_v4(scene)
    assert any(step["command"] == "draw.shape"
               for step in compiled["steps"])
    assert any(step["command"] == "draw.stroke"
               for step in compiled["steps"])


@pytest.mark.parametrize("invalid", [
    {"brush": {"color": "#ffffff"}},
    {"style": "ink"},
    {"render": {"technique": "wash"}},
    {"spacing": 20},
    {"jitter": .2},
    {"seed": 1},
    {"angle": 20},
    {"path": [[20,20],[40,40]]},
    {"pressure_curve": [[0,.1],[1,.2]]},
])
def test_native_region_rejects_stroke_only_or_model_unsafe_settings(invalid):
    scene = sample_v4()
    original = scene["stages"][1]["intents"][0]
    scene["stages"][1]["intents"][0] = {
        "id": original["id"], "subject_id": original["subject_id"],
        "kind": "region", "purpose": "Fill only the declared bounded region",
        "polygon": original["polygon"], **invalid,
    }
    with pytest.raises(TaskError, match="forbids"):
        validate_scene_v4(scene)


def test_filled_region_area_is_bounded_before_native_execution():
    scene = sample_v4()
    scene["document"].update(width=6000, height=4000)
    scene["subjects"][0]["bounds"] = [0, 0, 6000, 4000]
    # Fixture uses a fill that is geometrically inside the resized subject.
    original = scene["stages"][1]["intents"][0]
    scene["stages"][1]["intents"][0] = {
        "id": original["id"], "subject_id": original["subject_id"],
        "kind": "region", "purpose": "Test oversized native filled region",
        "polygon": [[0,0],[6000,0],[6000,4000],[0,4000]],
    }
    with pytest.raises(TaskError, match="per-fill pixel budget"):
        validate_scene_v4(scene)


def test_zero_native_strokes_only_legal_for_filled_polygon():
    _, scene, compiled = compiled_semantic()
    stage = compiled["stage_spans"][1]
    steps = compiled["steps"][stage["start"]:stage["stop"]]
    assert requires_native_regions(steps)
    assert inspect_native_regions(steps, {
        "symbols": {"Node.paintPolygon": True},
    })["filled_region_steps"] == len(scene["subjects"])
    with pytest.raises(TaskError, match="requires Node.paintPolygon"):
        require_supported_regions(steps, {"symbols": {"Node.paintPolygon": False}})
    with pytest.raises(TaskError, match="filled polygons"):
        from krita_agent.scene_v3 import validate_scene
        validate_scene({
            "schema": "krita-agent-scene/3",
            "document": {"width": 512, "height": 384},
            "objects": [{
                "id": "bad", "name": "Bad", "kind": "custom",
                "bounds": [10,10,100,100], "min_strokes": 0,
                "elements": [{"kind": "rectangle", "rect": [20,20,30,30]}],
            }],
        })


class CapClient:
    def __init__(self, polygon):
        self.polygon = polygon
        self.calls = []

    def request(self, command, **kwargs):
        self.calls.append(command)
        if command == "capabilities":
            return {
                "krita_version": "mock-build",
                "symbols": {
                    "Node.paintPolylineStroke": True, "StrokePoint": True,
                    "Node.paintPolygon": self.polygon,
                },
            }
        raise AssertionError("Unexpected native command " + command)


def prepared_flow(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "study", brief())
    flow.plan(candidate=proposal())
    flow.approve_plan(confirm=True)
    return flow


def test_native_region_preflight_cannot_write_or_paint(tmp_path):
    flow = prepared_flow(tmp_path)
    record = flow.read()
    record["status"] = "awaiting_stage_approval"
    record["staged"]["next_stage"] = 1  # simulate already completed sketch
    record["stage_live"] = {"test_only": True}
    flow._save(record, "fixture_assume_sketch_complete")
    before = flow.manifest.read_bytes()
    client = CapClient(False)
    preflight = flow.native_stage_preflight(client)
    assert preflight["native_region_preflight"]["unsupported_region_steps"] > 0
    assert preflight["artwork_accepted"] is False
    assert flow.manifest.read_bytes() == before
    assert client.calls == ["capabilities"]


def test_native_region_missing_api_rejects_before_side_effects(tmp_path, monkeypatch):
    flow = prepared_flow(tmp_path)
    record = flow.read()
    record["status"] = "awaiting_stage_approval"
    record["staged"]["next_stage"] = 1
    record["stage_live"] = {"test_only": True}
    flow._save(record, "fixture_assume_sketch_complete")
    monkeypatch.setattr(flow, "_stage_live_identity",
                        lambda client, document: {"test_only": True})
    monkeypatch.setattr(workflow_module, "run_longjob",
                        lambda *args, **kw: pytest.fail("native executed"))
    old = flow.manifest.read_bytes()
    with pytest.raises(TaskError, match="requires Node.paintPolygon"):
        flow.paint_stage(CapClient(False), confirm=True)
    assert flow.manifest.read_bytes() == old


def test_native_region_supported_mock_still_needs_artwork_validation(tmp_path, monkeypatch):
    flow = prepared_flow(tmp_path)
    record = flow.read()
    record["status"] = "awaiting_stage_approval"
    record["staged"]["next_stage"] = 1
    record["stage_live"] = {"test_only": True}
    flow._save(record, "fixture_assume_sketch_complete")
    monkeypatch.setattr(flow, "_stage_live_identity",
                        lambda client, document: {"test_only": True})
    issued = []
    monkeypatch.setattr(workflow_module, "run_longjob",
                        lambda *args, **kw: issued.append(args) or
                        {"state": "completed", "ledger": "mock_only"})
    result = flow.paint_stage(CapClient(True), confirm=True)
    assert result["status"] == "awaiting_stage_approval"
    assert len(issued) == 1
    # Green offline tests cannot establish native pixels or artist acceptance.
    assert flow.read()["staged"]["next_stage"] == 2
