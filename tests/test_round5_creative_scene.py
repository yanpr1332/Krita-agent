"""Round 5 semantic planning, brush differentiation and provider safety."""
import json

import pytest

from krita_agent import creative_director, model_provider
from krita_agent.protocol import TaskError
from krita_agent.scene_v3 import compile_scene_v3, validate_scene
from krita_agent.strategies_v3 import CATEGORIES


def sample_scene():
    return {
        "schema": "krita-agent-scene/3",
        "document": {"width": 512, "height": 384, "name": "Real strokes"},
        "style": "Painterly landscape",
        "objects": [
            {
                "id": "sky", "name": "Dusk sky", "kind": "sky",
                "depth": 0.1, "bounds": [0, 0, 512, 200],
                "brush": {"color": "#a57b8b"},
                "elements": [{"kind": "stroke", "points": [
                    {"x": 5, "y": 20}, {"x": 250, "y": 40}, {"x": 500, "y": 60}
                ]}],
            },
            {
                "id": "clouds", "name": "Cloud formation", "kind": "cloud",
                "depth": 0.2, "bounds": [20, 30, 460, 130],
                "brush": {"color": "#d59aa6"},
                "elements": [{"kind": "stroke", "points": [
                    {"x": 30, "y": 80}, {"x": 200, "y": 55}, {"x": 420, "y": 85}
                ]}],
            },
            {
                "id": "mountain", "name": "Mountain ridge", "kind": "mountain",
                "depth": 0.6, "bounds": [0, 130, 512, 190],
                "brush": {"color": "#374b64"},
                "elements": [{"kind": "stroke", "points": [
                    {"x": 0, "y": 300, "pressure": 1},
                    {"x": 256, "y": 140, "pressure": 0.45},
                    {"x": 512, "y": 300, "pressure": 1}
                ]}],
            },
        ],
    }


def test_scene_v3_compiles_only_native_allowlisted_steps():
    compiled = compile_scene_v3(sample_scene())
    assert compiled["schema"] == "krita-agent-scene-compiled/3"
    assert compiled["steps"][0]["command"] == "canvas.create"
    assert [o["kind"] for o in compiled["objects"]] == ["sky", "cloud", "mountain"]
    assert len([s for s in compiled["steps"] if s["command"] == "draw.stroke"]) == 3
    assert [s["command"] for s in compiled["steps"]].count("layer.create") == 3
    assert compiled["requires_native_approval"]
    assert compiled["not_artwork_acceptance"] is True


def test_different_objects_have_distinct_pressure_profiles_and_brush_sizes():
    compiled = compile_scene_v3(sample_scene())
    brush_steps = [s["parameters"] for s in compiled["steps"]
                   if s["command"] == "brush.configure"]
    assert len({step["size"] for step in brush_steps}) == 3
    strokes = [s["parameters"]["points"] for s in compiled["steps"]
               if s["command"] == "draw.stroke"]
    assert strokes[0][0]["pressure"] != strokes[1][0]["pressure"]
    assert strokes[2][0]["pressure"] == 1  # Preserve deliberate author pressure.
    assert CATEGORIES["cloud"] != CATEGORIES["mountain"]


def test_scene_rejects_blank_objects_and_unsafe_geometry():
    scene = sample_scene()
    scene["objects"][0]["elements"] = [{"kind": "rectangle", "rect": [1, 2, 9, 10]}]
    with pytest.raises(TaskError, match="actual brush strokes"):
        compile_scene_v3(scene)
    scene = sample_scene()
    scene["objects"][1]["elements"][0]["points"][0]["x"] = 800
    with pytest.raises(TaskError, match="within the canvas"):
        compile_scene_v3(scene)


def test_scene_rejects_duplicate_and_cyclic_object_relations():
    scene = sample_scene()
    scene["objects"][1]["id"] = "sky"
    with pytest.raises(TaskError, match="Duplicate"):
        validate_scene(scene)
    scene = sample_scene()
    scene["objects"][0]["parent"] = "clouds"
    scene["objects"][1]["parent"] = "sky"
    with pytest.raises(TaskError, match="cycle"):
        validate_scene(scene)


def test_director_requires_real_provider_and_valid_canvas():
    scene = sample_scene()
    class Provider:
        model = "stub-json-model"
        calls = 0
        def complete_json(self, system, prompt, image_paths=()):
            self.calls += 1
            assert "brush" in system
            return scene
    provider = Provider()
    result = creative_director.propose(
        {"prompt": "Paint a colored evening sky with clouds and a snowy mountain.",
         "width": 512, "height": 384}, provider
    )
    assert result["scene_sha256"]
    assert result["approval"] == "required"
    assert provider.calls == 1
    wrong = sample_scene()
    wrong["document"]["width"] = 513
    with pytest.raises(TaskError, match="canvas dimensions"):
        creative_director.propose(
            {"prompt": "Paint a colored evening sky with clouds and a snowy mountain.",
             "width": 512, "height": 384},
            type("Other", (), {"complete_json": lambda *args, **kw: wrong})(),
        )


def test_https_provider_rejects_missing_key_or_insecure_url(monkeypatch):
    monkeypatch.delenv("KRITA_AGENT_MODEL_API_KEY", raising=False)
    with pytest.raises(model_provider.ProviderError, match="API_KEY"):
        model_provider.ChatJSONProvider("test-model")
    with pytest.raises(model_provider.ProviderError, match="HTTPS"):
        model_provider.ChatJSONProvider(
            "test-model", endpoint="http://example.com/v1/chat/completions",
            api_key="not-used",
        )


def test_provider_sends_actual_image_pixels_with_explicit_opt_in(tmp_path, monkeypatch):
    Image = pytest.importorskip("PIL.Image")
    picture = tmp_path / "actual.png"
    Image.new("RGB", (32, 16), (10, 20, 30)).save(picture)
    calls = []
    class Result:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, count): return json.dumps({
            "choices": [{"message": {"content": '{"decision":"needs_revision"}'}}]
        }).encode()
    def urlopen(request, timeout):
        calls.append(json.loads(request.data))
        assert request.get_header("Authorization") == "Bearer fake-key"
        assert timeout == 75
        return Result()
    monkeypatch.setattr(model_provider, "urlopen", urlopen)
    provider = model_provider.ChatJSONProvider(
        "vision-model", api_key="fake-key",
    )
    result = provider.complete_json("Return JSON.", "Inspect image.", [picture])
    assert result == {"decision": "needs_revision"}
    content = calls[0]["messages"][1]["content"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
