"""Round 12 run-profile, telemetry and reopen-drift diagnostics."""
import json
import pytest
from krita_agent import creative_director
from krita_agent.artifact_integrity import compare_rgba
from krita_agent.creative_dashboard import render
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.protocol import TaskError
from krita_agent.workflow_metrics_v12 import summarize
from test_round5_creative_scene import sample_scene


def brief(**overrides):
    value = {"prompt": "Paint a coherent subject with distinct materials and lighting.",
             "width": 512, "height": 384, "title": "Round 12 profile test"}
    value.update(overrides)
    return value


def test_brief_effort_profiles_and_bounds():
    assert creative_director.validate_brief(brief(complexity="quick_sketch"))["max_native_steps"] == 2500
    assert creative_director.validate_brief(brief(complexity="standard"))["max_native_steps"] == 6000
    assert creative_director.validate_brief(brief(complexity="detailed"))["max_native_steps"] == 10000
    with pytest.raises(TaskError, match="complexity"):
        creative_director.validate_brief(brief(complexity=[]))
    with pytest.raises(TaskError, match="max_native_steps"):
        creative_director.validate_brief(brief(max_native_steps=10001))
    with pytest.raises(TaskError, match="time_budget_minutes"):
        creative_director.validate_brief(brief(time_budget_minutes=0))


def test_director_receives_effort_and_advisory_time_budget():
    captured = {}
    class Provider:
        model = "offline-test"
        def complete_json(self, system, prompt, image_paths=()):
            captured["prompt"] = prompt
            return sample_scene()
    creative_director.propose(brief(complexity="quick_sketch", time_budget_minutes=17), Provider())
    assert "quick_sketch" in captured["prompt"]
    assert "2500" in captured["prompt"]
    assert "17 minutes" in captured["prompt"]
    assert "advisory" in captured["prompt"]


def test_compiled_plan_cannot_exceed_user_native_step_ceiling(tmp_path):
    scene = sample_scene()
    scene["objects"][0]["elements"] = [
        {"kind": "stroke", "points": [{"x": 5, "y": 20}, {"x": 400, "y": 40}]}
        for _ in range(160)
    ]
    flow = CreativeWorkflow.create(tmp_path / "budget-run", brief(max_native_steps=100))
    with pytest.raises(TaskError, match="max_native_steps"):
        flow.plan(candidate=scene)
    assert flow.read()["status"] == "initialized"


def test_metrics_hash_chain_records_failure_without_exception_text(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "telemetry-run", brief())
    with pytest.raises(TaskError):
        flow.plan(candidate={"schema": "do-not-log-this-secret"})
    result = summarize(flow.root, flow.read())
    assert result["integrity"] == "verified"
    assert result["event_count"] == 1
    assert result["raised_invocations"] == 1
    assert result["operations"][0]["operation"] == "plan"
    assert result["operations"][0]["raised"] == 1
    raw = (flow.root / "operation-metrics-v12.jsonl").read_text(encoding="utf-8")
    assert "do-not-log-this-secret" not in raw


def test_metrics_detect_tampered_event(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "tamper-run", brief())
    with pytest.raises(TaskError):
        flow.plan(candidate={"schema": "invalid"})
    path = flow.root / "operation-metrics-v12.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["operation"] = "paint"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    result = summarize(flow.root, flow.read())
    assert result["integrity"] == "corrupt"
    assert result["event_count"] == 0


def test_metrics_include_hash_verified_planned_brush_diversity_and_dashboard(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "dashboard-run",
                                   brief(complexity="detailed", time_budget_minutes=45))
    flow.plan(candidate=sample_scene())
    result = summarize(flow.root, flow.read())
    assert result["integrity"] == "verified"
    assert result["compiled_plan"]["status"] == "verified"
    assert result["compiled_plan"]["planned_only"] is True
    assert result["compiled_plan"]["distinct_sizes"] >= 3
    assert result["compiled_plan"]["distinct_colors"] >= 3
    assert result["compiled_plan"]["pressure_samples"] >= 3
    assert result["compiled_plan"]["brush_quality_v12"]["status"] == "fail"
    output = render(flow)
    page = (flow.root / "dashboard.html").read_text(encoding="utf-8")
    assert output["read_only"] is True
    assert "Execution timings" in page
    assert "detailed" in page and "45 minutes" in page
    assert "Brush diversity: advisory" in page
    assert "planned parameters" in page


def test_reopen_drift_reports_channels_and_spatial_bounds():
    Image = pytest.importorskip("PIL.Image")
    first = Image.new("RGBA", (4, 3), (10, 20, 30, 255))
    second = first.copy()
    second.putpixel((1, 1), (11, 20, 30, 255))
    second.putpixel((2, 2), (10, 20, 32, 255))
    report = compare_rgba(first, second)
    assert report["strict_match"] is False
    assert report["channel_different_pixels"] == {"red": 1, "green": 0, "blue": 1, "alpha": 0}
    assert report["difference_bounds_xyxy"] == [1, 1, 3, 3]
    assert report["mean_absolute_channel_difference"] > 0
    assert report["minor_color_tolerance"]["within_tolerance"] is False


def rich_scene():
    scene = sample_scene()
    colors = ["#31516f", "#b5a17c", "#f0d6a0"]
    sizes = [4, 14, 42]
    opacities = [0.25, 0.55, 0.9]
    vectors = [(40, 0), (40, 40), (0, 40), (40, -40)]
    for obj in scene["objects"]:
        x, y, width, height = obj["bounds"]
        elements = []
        for i in range(24):
            dx, dy = vectors[i % len(vectors)]
            x0 = x + 5 + (i % 8) * 10
            y0 = y + 10 + (i // 8) * 15 + height // 3
            x1 = min(x + width - 1, x0 + dx)
            y1 = max(y, min(y + height - 1, y0 + dy))
            elements.append({
                "kind": "stroke",
                "brush": {
                    "size": sizes[i % 3],
                    "color": colors[i % 3],
                    "opacity": opacities[i % 3],
                },
                "points": [
                    {"x": x0, "y": y0, "pressure": 0.1 + 0.1 * (i % 3)},
                    {"x": x1, "y": y1, "pressure": 0.9 - 0.1 * (i % 3)},
                ],
            })
        obj["elements"] = elements
    return scene


def test_brush_diversity_enforce_rejects_sparse_passes(tmp_path):
    flow = CreativeWorkflow.create(
        tmp_path / "strict-brush-run",
        brief(complexity="detailed", brush_diversity_policy="enforce"),
    )
    with pytest.raises(TaskError, match="Brush diversity floor"):
        flow.plan(candidate=sample_scene())
    assert flow.read()["status"] == "initialized"


def test_detailed_brush_diversity_floor_accepts_a_varied_plan():
    from krita_agent.brush_quality_v12 import evaluate_brush_plan
    from krita_agent.scene_v3 import validate_scene
    result = evaluate_brush_plan(validate_scene(rich_scene()), "detailed")
    assert result["status"] == "pass"
    assert len(result["subjects"]) == 3
    assert all(row["status"] == "pass" for row in result["subjects"])


def test_advisory_brush_policy_preserves_legacy_plan_but_reports_failure(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "advisory-brush-run", brief())
    flow.plan(candidate=sample_scene())
    metrics = summarize(flow.root, flow.read())
    quality = metrics["compiled_plan"]["brush_quality_v12"]
    assert quality["policy"] == "advisory"
    assert quality["status"] == "fail"
