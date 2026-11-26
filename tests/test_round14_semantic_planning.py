"""Round 14 semantic composition/geometry/creative workflow OFFLINE tests.

All outputs are proposals and simulated steps. No Krita, paid API, or
finished artwork is invoked or accepted by these tests.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from krita_agent import creative_workflow as workflow_module
from krita_agent.cli import parser_build
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.protocol import TaskError
from krita_agent.scene_v3 import digest
from krita_agent.scene_v4 import compile_scene_v4, validate_scene_v4
from krita_agent.semantic_planning_v14 import (
    COMPOSITION_SCHEMA, PAINT_PLAN_SCHEMA, SEMANTIC_SYSTEM,
    compile_semantic, propose_semantic, validate_composition,
)


def brief():
    return {"prompt": "A sitting cat in a room beside a quiet cup and window.",
            "width": 512, "height": 384, "style": "natural lines",
            "title": "Semantic Cat Study"}


def proposal():
    return {
        "schema": COMPOSITION_SCHEMA,
        "style": "gentle line illustration",
        "notes": "The cat is in front of the wall and left of the cup.",
        "subjects": [
            {
                "id": "room", "name": "Warm room",
                "kind": "interior", "bbox": [0, 0, 1, 1],
                "outline": "rectangle", "color": "#e9dcc1", "depth": .1,
            },
            {
                "id": "cat", "name": "Cat in repose",
                "kind": "animal", "bbox": [.22, .24, .38, .62],
                "outline": "ellipse", "color": "#b09b80",
                "detail_color": "#403a38", "depth": .6,
                "materials": ["fur"],
                "parts": [
                    {"id": "head", "name": "Cat head",
                     "bbox": [.25, .02, .48, .33],
                     "outline": "ellipse", "color": "#c5ad92"},
                    {"id": "tail", "name": "Tail",
                     "bbox": [.72, .55, .21, .33],
                     "outline": "capsule", "color": "#c5ad92"},
                ],
            },
            {
                "id": "cup", "name": "Ceramic cup",
                "kind": "vessel", "bbox": [.72, .55, .18, .26],
                "outline": "capsule", "color": "#7b9cb6", "depth": .7,
            },
        ],
        "relations": [
            {"kind": "front_of", "a": "cat", "b": "room"},
            {"kind": "left_of", "a": "cat", "b": "cup"},
            {"kind": "inside", "a": "cat_head", "b": "cat"},
        ],
    }


def test_semantic_layer_produces_deterministic_reviewable_v4_and_tasks():
    candidate = proposal()
    composition, tasks, scene = compile_semantic(candidate, brief())
    assert composition == validate_composition(composition)
    assert len(composition["subjects"]) == 5
    assert [x["parent"] for x in composition["subjects"]] == [
        None, None, "cat", "cat", None]
    assert tasks["schema"] == PAINT_PLAN_SCHEMA
    assert tasks["status"] == "structural_scaffold_only"
    assert tasks["artwork_accepted"] is False
    assert tasks["scene_v4_sha256"] == digest(scene)
    assert tasks["source_composition_sha256"] == digest(composition)
    assert [s["phase"] for s in scene["stages"]] == [
        "sketch", "block_in", "detail"]
    # R17 adds clipped highlight/shadow region intents while retaining
    # exactly one R14 semantic subject layer per phase.
    assert [len(s["intents"]) for s in scene["stages"]] == [5, 15, 5]
    assert scene == validate_scene_v4(scene)
    assert compile_semantic(deepcopy(candidate), brief()) == (
        composition, tasks, scene)
    compiled = compile_scene_v4(scene)
    assert compiled["not_artwork_acceptance"] is True
    assert compiled["requires_native_approval"] is True
    assert len(compiled["stage_spans"]) == 3
    assert len(compiled["stage_layers"]) == 15
    assert not any(x["command"] in ("image.import", "reference.import",
                                    "pixel.fill", "shell.run")
                   for x in compiled["steps"])
    assert len(compiled["steps"]) <= 6000


@pytest.mark.parametrize("change,match", [
    (lambda p: p.update(command="shell.run"), "unsupported fields"),
    (lambda p: p.update(schema="unknown"), "Expected composition schema"),
    (lambda p: p["subjects"][1].update(bbox=[.8, .1, .6, .5]), "inside 0..1"),
    (lambda p: p["subjects"][1].update(bbox=[.2, .2, True, .5]), "finite number"),
    (lambda p: p["subjects"][1].update(color="red"), "#RRGGBB"),
    (lambda p: p["subjects"][1].update(outline="generate_png"), "outline"),
    (lambda p: p["subjects"][1].update(path=[[0,0],[1,1]]), "unsupported fields"),
    (lambda p: p["subjects"][1].update(depth=4), "allowed range"),
    (lambda p: p["subjects"][1].update(id="CAT"), "lowercase"),
    (lambda p: p["subjects"][1]["parts"][0].update(bbox=[.8,.8,.5,.3]), "inside 0..1"),
    (lambda p: p["subjects"][1]["parts"][0].update(extra="os.system"), "unsupported fields"),
    (lambda p: p["relations"].append(
        {"kind": "above", "a": "cat", "b": "room"}), "Unsatisfied"),
    (lambda p: p["relations"].append(
        {"kind": "left_of", "a": "ghost", "b": "room"}), "unknown"),
])
def test_invalid_or_untrusted_semantic_plans_fail_closed(change, match):
    candidate = proposal()
    change(candidate)
    with pytest.raises(TaskError, match=match):
        compile_semantic(candidate, brief())


def test_excessive_node_groups_and_duplicate_ids_are_rejected():
    candidate = proposal()
    candidate["subjects"].extend(deepcopy(candidate["subjects"][:1]))
    with pytest.raises(TaskError, match="Duplicate"):
        validate_composition(candidate)
    candidate = proposal()
    candidate["subjects"] = [
        dict(id="item{}".format(i), name="Object {}".format(i),
             kind="generic", bbox=[0,.1,.1,.5], color="#123456")
        for i in range(11)
    ]
    with pytest.raises(TaskError, match="1..10"):
        validate_composition(candidate)


def test_semantic_generator_does_not_produce_native_code_or_unbounded_retries():
    class Provider:
        model = "fixture-only"
        calls = 0
        def complete_json(self, system, prompt, image_paths=()):
            self.calls += 1
            assert system == SEMANTIC_SYSTEM
            assert "512x384" in prompt
            assert image_paths == ["AUTHORIZED_REFERENCE.png"]
            assert "paintLine" not in system
            return proposal()
    provider = Provider()
    meta = propose_semantic(brief(), provider, "AUTHORIZED_REFERENCE.png")
    assert meta["scene_v4_sha256"] == digest(meta["scene_v4"])
    assert meta["model_requests"] == 1
    assert meta["model_retries"] == 0
    assert provider.calls == 1
    assert meta["side_effects"] == "none"


def test_semantic_workflow_persists_all_sources_and_rechecks_on_approval(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    result = flow.plan(candidate=proposal())
    assert result["status"] == "planned"
    assert result["subjects"] == 5
    assert result["semantic_planning"]["quality"] == "structural_scaffold_not_artwork"
    assert result["semantic_planning"]["model_requests"] == 0
    for name in ("composition-v14.json", "paint-plan-v14.json",
                 "scene-plan-v4.json", "scene-plan-v3.json",
                 "generalist-proposal.json", "compiled-scene.json"):
        assert (flow.root / name).is_file()
    assert flow.approve_plan(confirm=True)["status"] == "plan_approved"
    assert flow._verified_staged_plan(flow.read())["not_artwork_acceptance"] is True


@pytest.mark.parametrize("tampered", ["composition-v14.json",
                                      "paint-plan-v14.json",
                                      "scene-plan-v4.json"])
def test_semantic_source_is_immutable_across_stage_approval(tmp_path, tampered):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=proposal())
    p = flow.root / tampered
    p.write_text(p.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(TaskError, match="changed"):
        flow.approve_plan(confirm=True)
    assert flow.read()["status"] == "planned"


def test_provider_opt_in_and_user_stages_cannot_execute_implicitly(tmp_path, monkeypatch):
    class Provider:
        model = "mock"
        called = 0
        def complete_json(self, *args, **kwargs):
            self.called += 1
            return proposal()
    provider = Provider()
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    result = flow.plan(provider=provider, semantic=True)
    assert provider.called == 1
    assert result["status"] == "planned"
    with pytest.raises(TaskError, match="--confirm"):
        flow.paint_stage(object())
    with pytest.raises(TaskError, match="approval"):
        flow.paint_stage(object(), confirm=True)
    assert flow.read()["status"] == "planned"
    with pytest.raises(TaskError, match="exactly one"):
        other = CreativeWorkflow.create(tmp_path / "run2", brief())
        other.plan(provider=provider, candidate=proposal(), semantic=True)
    with pytest.raises(TaskError, match="exactly one"):
        other = CreativeWorkflow.create(tmp_path / "run3", brief())
        other.plan(provider=provider, generalist=True, semantic=True)


def test_cli_routes_semantic_plan_without_changing_legacy_defaults():
    args = parser_build().parse_args([
        "creative", "plan", "--directory", "artwork-results/run",
        "--model", "mock", "--semantic",
    ])
    assert args.semantic is True and args.generalist is False
    args = parser_build().parse_args([
        "creative", "plan", "--directory", "artwork-results/run",
        "--candidate", "candidate.json",
    ])
    assert args.semantic is False and args.generalist is False
