"""Round 13 offline regression fixtures; never claim native Krita visual acceptance.

All PNGs in this file are synthetic *path and integrity test data*, not
artwork made by Krita. Installed-build pressure/opacity still needs R13 T3.
"""
import hashlib
import json

import pytest
from PIL import Image

from krita_agent import creative_workflow as workflow_module
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.native_continuity_v13 import (
    inspect_stroke_continuity, reject_unsafe_segmented_joins,
)
from krita_agent.protocol import TaskError
from test_round7_generalist_scene import sample_v4


def capabilities(continuous):
    return {
        "krita_version": "mock-stable" if not continuous else "mock-next",
        "qt_version": "mock",
        "qt_binding": "PyQt5",
        "symbols": {
            "Node.paintPolylineStroke": continuous,
            "StrokePoint": continuous,
        },
    }


def stroke(points, mode="auto"):
    return {"command": "draw.stroke", "parameters": {
        "points": [{"x": i * 10, "y": i * 2} for i in range(points)],
        "mode": mode,
    }}


@pytest.mark.parametrize("has_api,mode,points,risks,unsupported", [
    (False, "auto", 5, 1, 0),
    (False, "segmented", 3, 1, 0),
    (False, "auto", 2, 0, 0),
    (False, "continuous", 2, 0, 1),
    (True, "auto", 7, 0, 0),
    (True, "continuous", 7, 0, 0),
    (True, "segmented", 4, 1, 0),
])
def test_runtime_stroke_join_path_audit(has_api, mode, points, risks, unsupported):
    report = inspect_stroke_continuity([stroke(points, mode)], capabilities(has_api))
    assert report["segmented_join_risk_strokes"] == risks
    assert report["unsupported_continuous_strokes"] == unsupported
    assert report["continuous_visual_response_verified"] is False
    assert report["artwork_accepted"] is False
    assert report["reject_segmented_joins_preflight_passed"] is not bool(risks or unsupported)


def test_audit_requires_real_capability_inventory_and_bounded_steps():
    with pytest.raises(TaskError, match="unavailable"):
        inspect_stroke_continuity([stroke(3)], None)
    with pytest.raises(TaskError, match="symbol inventory"):
        inspect_stroke_continuity([stroke(3)], {})
    with pytest.raises(TaskError, match="Malformed"):
        inspect_stroke_continuity([{"command": "draw.stroke", "parameters": {
            "points": [], "mode": "auto"}}], capabilities(True))
    with pytest.raises(TaskError, match="blocked"):
        reject_unsafe_segmented_joins([stroke(3)], capabilities(False))
    # Two-point legacy paintLine has no interior segmented joint.
    assert reject_unsafe_segmented_joins(
        [stroke(2)], capabilities(False)
    )["reject_segmented_joins_preflight_passed"]


class CapClient:
    def __init__(self, continuous):
        self.continuous = continuous
        self.calls = []

    def request(self, command, **kwargs):
        self.calls.append(command)
        if command == "capabilities":
            return capabilities(self.continuous)
        raise AssertionError("Unexpected native request: " + command)


def prepared_flow(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "run", {
        "prompt": "A character in a room with a ceramic cup.",
        "width": 512, "height": 384,
    })
    flow.plan(candidate=sample_v4())
    flow.approve_plan(confirm=True)
    return flow


def test_read_only_preflight_does_not_mutate_workflow_or_draw(tmp_path):
    flow = prepared_flow(tmp_path)
    client = CapClient(False)
    before = flow.manifest.read_bytes()
    result = flow.native_stage_preflight(client)
    assert result["stage"] == 1
    assert result["draw_strokes_scanned"] > 0
    assert result["segmented_join_risk_strokes"] > 0
    assert result["approved_stage_sha256"]
    assert flow.manifest.read_bytes() == before
    assert client.calls == ["capabilities"]


def test_strict_preflight_refuses_before_native_submission(tmp_path, monkeypatch):
    flow = prepared_flow(tmp_path)
    client = CapClient(False)
    calls = []
    monkeypatch.setattr(workflow_module, "run_longjob",
                        lambda *a, **kw: calls.append(1))
    with pytest.raises(TaskError, match="preflight blocked"):
        flow.paint_stage(client, confirm=True, reject_segmented_joins=True)
    assert not calls
    assert flow.read()["status"] == "plan_approved"
    assert flow.read()["staged"]["next_stage"] == 0
    assert client.calls == ["capabilities"]


def test_supported_continuous_build_can_pass_strict_stage_gate(tmp_path, monkeypatch):
    flow = prepared_flow(tmp_path)
    client = CapClient(True)
    calls = []
    def native(*args, **kwargs):
        calls.append(args)
        return {"state": "completed", "ledger": "offline-fixture"}
    monkeypatch.setattr(workflow_module, "run_longjob", native)
    monkeypatch.setattr(flow, "_stage_live_identity",
                        lambda _client, _document: {"test_only": True})
    result = flow.paint_stage(client, confirm=True, reject_segmented_joins=True)
    assert len(calls) == 1
    assert result["status"] == "awaiting_stage_approval"
    assert flow.read()["staged"]["next_stage"] == 1


def test_diagnose_accepts_historical_windows_stage_separator_paths(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "run", {
        "prompt": "An interior with objects and real layers.",
        "width": 512, "height": 384,
    })
    flow.plan(candidate=sample_v4())
    compiled = json.loads((flow.root / "compiled-scene.json").read_text("utf-8"))
    stage_dir = flow.root / "stages"
    stage_dir.mkdir()
    artifacts = {}
    for index, stage in enumerate(compiled["stage_spans"]):
        name = "stage-%02d-%s.png" % (index + 1, stage["phase"])
        path = stage_dir / name
        Image.new("RGBA", (64, 48), (20 + index * 50, 30, 50, 255)).save(path)
        artifacts[name] = {
            "path": "stages\\" + name,  # Windows Path.relative_to(root)
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    record = flow.read()
    record["artifacts"]["stage_previews"] = artifacts
    flow._save(record, "offline_windows_path_fixture")
    report = flow.diagnose_materials()["native_stage_pixels"]
    assert report["stages_verified"] == len(compiled["stage_spans"])
    assert len(report["transitions"]) == len(compiled["stage_spans"]) - 1

    first = next(iter(artifacts))
    record = flow.read()
    record["artifacts"]["stage_previews"][first]["path"] = "stages/../" + first
    flow._save(record, "offline_reject_traversal")
    with pytest.raises(TaskError, match="missing"):
        flow.diagnose_materials()


def test_diagnose_detects_bad_hash_on_windows_stage_paths(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "run", {
        "prompt": "A test scene for a safe path",
        "width": 512, "height": 384,
    })
    flow.plan(candidate=sample_v4())
    compiled = json.loads((flow.root / "compiled-scene.json").read_text("utf-8"))
    folder = flow.root / "stages"
    folder.mkdir()
    refs = {}
    for index, stage in enumerate(compiled["stage_spans"]):
        name = "stage-%02d-%s.png" % (index + 1, stage["phase"])
        p = folder / name
        Image.new("RGBA", (64, 48), (0, 50, 90, 255)).save(p)
        refs[name] = {"path": "stages\\" + name,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    record = flow.read()
    record["artifacts"]["stage_previews"] = refs
    flow._save(record, "offline_hash_bound")
    first = next(iter(refs))
    (folder / first).write_bytes(b"tampered")
    with pytest.raises(TaskError, match="changed after archive"):
        flow.diagnose_materials()


def test_cli_exposes_read_only_preflight_and_explicit_strict_mode():
    from krita_agent.cli import parser_build
    args = parser_build().parse_args([
        "creative", "native-preflight", "--directory", "artwork-results/run",
        "--session", "session.json",
    ])
    assert args.action == "native-preflight"
    args = parser_build().parse_args([
        "creative", "paint-stage", "--directory", "artwork-results/run",
        "--session", "session.json", "--confirm",
        "--reject-segmented-joins",
    ])
    assert args.reject_segmented_joins is True
    legacy = parser_build().parse_args([
        "creative", "paint-stage", "--directory", "artwork-results/run",
        "--session", "session.json", "--confirm",
    ])
    assert legacy.reject_segmented_joins is False


def test_bridge_fallback_matches_preflight_hazard_without_krita_import():
    """AST-extracted dispatcher demonstrates repeated native paintLine calls."""
    from types import SimpleNamespace
    from unittest.mock import Mock
    from test_bridge_native import dispatcher

    class Point:
        def __init__(self, x, y):
            self.x, self.y = x, y
        def toPoint(self):
            return (self.x, self.y)

    raw = [{"x": 10 * i, "y": 10 * i, "pressure": .25}
           for i in range(5)]
    node = SimpleNamespace(paintLine=Mock())  # Stable: no polyline method.
    execute = dispatcher({
        "Krita": SimpleNamespace(instance=lambda: None),
        "_points": lambda items: [Point(p["x"], p["y"]) for p in items],
        "_number": lambda value, *_args: float(value),
        "krita_module": SimpleNamespace(),
    })
    bridge = SimpleNamespace(_stroke_node=lambda: node)
    result = execute(bridge, "draw.stroke", {"points": raw, "mode": "auto"})
    assert result["mode"] == "segmented"
    assert node.paintLine.call_count == 4
    assert node.paintLine.call_args_list[0].args[1] == (
        node.paintLine.call_args_list[1].args[0]
    )
    assert inspect_stroke_continuity(
        [stroke(5, "auto")], capabilities(False)
    )["segmented_join_risk_strokes"] == 1
    with pytest.raises(RuntimeError, match="lacks continuous-stroke API"):
        execute(bridge, "draw.stroke", {"points": raw, "mode": "continuous"})
    assert node.paintLine.call_count == 4


def test_bridge_auto_uses_one_native_polyline_on_supported_mock():
    from types import SimpleNamespace
    from unittest.mock import Mock
    from test_bridge_native import dispatcher

    raw = [{"x": 10 * i, "y": 4 * i, "pressure": .6}
           for i in range(5)]
    node = SimpleNamespace(paintLine=Mock(), paintPolylineStroke=Mock())
    module = SimpleNamespace(StrokePoint=lambda *args: tuple(args))
    execute = dispatcher({
        "Krita": SimpleNamespace(instance=lambda: None),
        "_points": lambda items: [(p["x"], p["y"]) for p in items],
        "_number": lambda value, *_args: float(value),
        "krita_module": module,
    })
    bridge = SimpleNamespace(_stroke_node=lambda: node)
    result = execute(bridge, "draw.stroke", {"points": raw, "mode": "auto"})
    assert result["mode"] == "continuous"
    node.paintPolylineStroke.assert_called_once()
    node.paintLine.assert_not_called()
    assert inspect_stroke_continuity(
        [stroke(5, "auto")], capabilities(True)
    )["segmented_join_risk_strokes"] == 0
