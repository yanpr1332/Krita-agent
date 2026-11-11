"""Round 7 generalist staged painting contract (OFFLINE ONLY).

These tests never run Krita, simulate artwork pixels or claim artistic approval.
They assert that generalist plans stay safe, deterministic, reversible and staged.
"""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from krita_agent import creative_workflow as module
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.generalist_director import propose_generalist
from krita_agent.protocol import TaskError
from krita_agent.scene_v3 import compile_scene_v3, digest
from krita_agent.scene_v4 import (
    compile_scene_v4, lower_scene_v4, validate_scene_v4,
)
from test_round5_creative_scene import sample_scene


EXAMPLE = (Path(__file__).resolve().parents[1] /
           "examples/round7-generalist-scene.json")


def sample_v4():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_v4_generic_subjects_are_separate_from_materials_and_styles():
    scene = validate_scene_v4(sample_v4())
    assert [s["kind"] for s in scene["subjects"]] == [
        "interior architecture", "human figure", "ceramic still life"]
    assert scene["subjects"][1]["materials"] == ["skin", "hair", "cloth"]
    assert [s["phase"] for s in scene["stages"]] == [
        "sketch", "block_in", "detail"]
    assert digest(scene) == digest(validate_scene_v4(scene))
    assert len(scene["stages"][1]["intents"]) == 3


def test_v4_lowering_produces_only_native_v3_strokes_not_raster_pastes():
    scene = sample_v4()
    lowered, rows = lower_scene_v4(scene)
    assert lowered["schema"] == "krita-agent-scene/3"
    assert len(rows) == 9
    assert set(o["kind"] for o in lowered["objects"]) == {"custom"}
    assert len({row["stage_index"] for row in rows}) == 3
    assert all(o["elements"] and all(e["kind"] == "stroke"
                                    for e in o["elements"])
               for o in lowered["objects"])
    compiled = compile_scene_v4(scene, preview_prefix="r5-runs/"+"a"*32)
    commands = [s["command"] for s in compiled["steps"]]
    assert commands.count("canvas.create") == 1
    assert commands.count("layer.create") == len(rows)
    assert commands.count("draw.stroke") > len(scene["stages"])
    assert "image.import" not in commands
    assert "reference.import" not in commands
    assert "preview.canvas" in commands
    assert len(compiled["stage_preview_paths"]) == 6  # 3 phases + 3 milestones
    assert any(path.endswith("03-final.png")
               for path in compiled["stage_preview_paths"])
    assert compiled["not_artwork_acceptance"] is True
    assert compiled["requires_native_approval"] is True
    assert compiled["source_sha256"] == digest(lowered)


def test_stage_boundaries_deterministic_and_contiguous():
    candidate = sample_v4()
    a = compile_scene_v4(candidate, preview_prefix="r5-runs/"+"d"*32)
    b = compile_scene_v4(deepcopy(candidate), preview_prefix="r5-runs/"+"d"*32)
    assert a["native_steps_sha256"] == b["native_steps_sha256"]
    assert a["source_v4_sha256"] == digest(validate_scene_v4(candidate))
    assert [s["id"] for s in a["stage_spans"]] == ["gesture", "block", "detail"]
    cursor = 0
    for span in a["stage_spans"]:
        assert span["start"] == cursor
        steps = a["steps"][span["start"]:span["stop"]]
        assert span["steps_sha256"] == digest(steps)
        assert any(s["command"] == "draw.stroke" for s in steps)
        cursor = span["stop"]
    assert cursor == len(a["steps"])


def test_v3_contract_and_existing_native_compilation_untouched():
    old = sample_scene()
    assert compile_scene_v3(old)["schema"] == "krita-agent-scene-compiled/3"
    with pytest.raises(TaskError, match="Expected ScenePlan v4"):
        validate_scene_v4(old)


@pytest.mark.parametrize("mutate,match", [
    (lambda s: s.update(shell="os.system"), "unsupported fields"),
    (lambda s: s["subjects"][1].update(kind=None), "subject kind"),
    (lambda s: s["subjects"][1].update(parent="cup")
     or s["subjects"][2].update(parent="person"), "cyclic"),
    (lambda s: s["subjects"][1]["brush"].update(size=-5), "brush size"),
    (lambda s: s["stages"][0]["intents"][0].update(command="image.import"),
     "unsupported fields"),
    (lambda s: s["stages"][0]["intents"][1].update(path=[[999, 9], [1000, 20]]),
     "paint x"),
    (lambda s: s["stages"][1]["intents"][0].update(
        polygon=[[0, 0], [512, 160], [90, 165], [480, 0]]), "self-intersecting"),
    (lambda s: s["stages"][1]["intents"][0].update(
        polygon=[[0, 0], [512, 0], [512, 384], [0, 384]], spacing=1),
     "240 scanline"),
    (lambda s: s["stages"][1]["intents"][1].update(material="metal"),
     "not declared"),
    (lambda s: s["stages"][2]["intents"][0].update(style="unknown_style"),
     "named stroke style"),
    (lambda s: s["stages"][1].update(phase="sketch"),
     "advance in order"),
])
def test_reject_unsafe_or_bad_generalist_plan(mutate, match):
    scene = sample_v4()
    mutate(scene)
    with pytest.raises(TaskError, match=match):
        compile_scene_v4(scene)


def test_reference_aware_generalist_model_is_opt_in_and_no_native_commands():
    scene = sample_v4()
    class FakeProvider:
        model = "mock-generalist"
        def complete_json(self, system, prompt, image_paths=()):
            assert "gesture" in system
            assert "pixels" in system or "pasted image" in system or "reference" in system
            assert "512 x 384" in prompt
            assert image_paths == ["provided-reference.png"]
            return scene
    result = propose_generalist({
        "prompt": "Plan a human in a quiet room with a ceramic cup.",
        "width": 512, "height": 384,
    }, FakeProvider(), "provided-reference.png")
    assert result["scene_v4_sha256"] == digest(validate_scene_v4(scene))
    assert result["provider_model"] == "mock-generalist"
    assert result["approval"] == "required"


def test_intent_expansion_cost_bounded_and_pressure_styles_propagate():
    scene = sample_v4()
    lowered, _ = lower_scene_v4(scene)
    hair = next(o for o in lowered["objects"] if o["id"] == "s02_person")
    assert len(hair["elements"]) == 9
    assert hair["elements"][0]["brush"]["color"] == "#383744"
    assert hair["elements"][0]["points"][0]["pressure"] == pytest.approx(0.1)
    assert all(0 <= p["pressure"] <= 1 for e in hair["elements"]
               for p in e["points"])


def _brief():
    return {
        "prompt": "Paint a character in a room with a ceramic cup.",
        "width": 512, "height": 384,
    }


class StableStageClient:
    def __init__(self):
        self.graph = {"layers": ["room", "person", "cup"]}
        self.calls = []
    def request(self, command, **params):
        self.calls.append(command)
        if command == "document.list":
            return [{"index": 1, "name": "Round 7 Generalist Study",
                     "width": 512, "height": 384, "active": True,
                     "file_path": "", "color_model": "RGBA",
                     "color_depth": "U8", "color_profile": "sRGB"}]
        if command == "layer.tree":
            return self.graph
        raise AssertionError("Unexpected native request: " + command)


def test_creative_workflow_v4_requires_explicit_each_stage(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path/"v4", _brief())
    planned = flow.plan(candidate=sample_v4())
    assert planned["status"] == "planned"
    assert len(planned["stage_spans"]) == 3
    assert (flow.root/"scene-plan-v4.json").is_file()
    assert (flow.root/"scene-plan-v3.json").is_file()
    with pytest.raises(TaskError, match="--confirm"):
        flow.paint_stage(object())
    flow.approve_plan(confirm=True)
    with pytest.raises(TaskError, match="paint-stage"):
        flow.paint(object())
    called = []
    def native_stub(client, spec, ledger_dir, batch_steps=120):
        called.append(spec)
        return {"state": "completed", "ledger": "offline-only"}
    monkeypatch.setattr(module, "run_longjob", native_stub)
    client = StableStageClient()
    for idx in range(3):
        result = flow.paint_stage(client, confirm=True)
        assert result["stage"] == idx+1
        assert len(called) == idx+1
        assert sum(s["command"] == "draw.stroke"
                   for s in called[-1]["steps"]) >= 1
        if idx != 2:
            assert result["status"] == "awaiting_stage_approval"
        else:
            assert result["status"] == "awaiting_export"
    assert flow.read()["staged"]["next_stage"] == 3
    assert len(flow.read()["staged"]["completed"]) == 3
    with pytest.raises(TaskError, match="expected"):
        flow.paint_stage(client, confirm=True)


def test_staged_preflight_rejects_changed_active_art_without_replaying(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path/"v4", _brief())
    flow.plan(candidate=sample_v4())
    flow.approve_plan(confirm=True)
    called = []
    monkeypatch.setattr(module, "run_longjob", lambda *args, **kwargs:
                        called.append(args[1]) or {"state": "completed", "ledger": "fake"})
    client = StableStageClient()
    flow.paint_stage(client, confirm=True)
    client.graph = {"layers": ["foreign-modification"]}
    with pytest.raises(TaskError, match="changed"):
        flow.paint_stage(client, confirm=True)
    assert len(called) == 1
    assert flow.read()["status"] == "awaiting_stage_approval"


def test_stage_ledger_failure_stays_unknown_not_replayed(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path/"v4", _brief())
    flow.plan(candidate=sample_v4())
    flow.approve_plan(confirm=True)
    called = []
    monkeypatch.setattr(module, "run_longjob", lambda *args, **kwargs:
                        called.append(True) or
                        {"state": "unknown_needs_review", "ledger": "fixture"})
    result = flow.paint_stage(StableStageClient(), confirm=True)
    assert result["status"] == "unknown_needs_review"
    with pytest.raises(TaskError, match="expected"):
        flow.paint_stage(StableStageClient(), confirm=True)
    assert called == [True]


def test_generalist_source_and_compiled_hashes_rechecked_before_approval(tmp_path):
    flow = CreativeWorkflow.create(tmp_path/"v4", _brief())
    flow.plan(candidate=sample_v4())
    p = flow.root/"scene-plan-v4.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    payload["subjects"][0]["kind"] = "an unrelated rewrite"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TaskError, match="source artifact changed"):
        flow.approve_plan(confirm=True)



def test_coverage_strokes_have_effective_pressure_and_respect_explicit_curve():
    candidate = sample_v4()
    lowered, _ = lower_scene_v4(candidate)
    wall = next(item for item in lowered["objects"] if item["id"] == "s01_room")
    points = wall["elements"][0]["points"]
    assert len(points) == 3
    assert [point["pressure"] for point in points] == [0.85, 0.85, 0.85]

    candidate["stages"][1]["intents"][0]["pressure_curve"] = [
        [0, 0.1], [0.5, 0.9], [1, 0.2]
    ]
    lowered, _ = lower_scene_v4(candidate)
    wall = next(item for item in lowered["objects"] if item["id"] == "s01_room")
    pressures = [point["pressure"] for point in wall["elements"][0]["points"]]
    assert pressures == [0.1, 0.9, 0.2]
