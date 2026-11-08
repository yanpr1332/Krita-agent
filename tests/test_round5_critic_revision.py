"""Round 5 vision critic and bounded non-destructive revision."""
import hashlib
from pathlib import Path

import pytest
from krita_agent.protocol import TaskError
from krita_agent.visual_critic import critique
from krita_agent.creative_reviser import validate_revision, execute_revision
from test_round5_creative_scene import sample_scene


def make_image(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    path = tmp_path / "painted.png"
    Image.new("RGB", (512, 384), (15, 35, 55)).save(path)
    return path


def issue():
    return {
        "object_id": "clouds", "severity": "major",
        "region": [20, 40, 230, 100],
        "observation": "The clouds are mechanically repeated bands instead of natural volumes.",
        "recommendation": "Repaint the cloud edge with irregular pressure changes.",
    }


class FakeCritic:
    model = "stub-vision"
    def complete_json(self, system, prompt, image_paths=()):
        assert len(image_paths) == 1
        assert Path(image_paths[0]).exists()
        return {
            "decision": "needs_revision",
            "observations": "The cloud region is visibly repeated while the rest of the landscape is legible.",
            "issues": [issue()],
        }


def test_critic_binds_actual_pixels_and_reports_localized_issue(tmp_path):
    image = make_image(tmp_path)
    result = critique(sample_scene(), image, FakeCritic())
    assert result["schema"] == "krita-agent-creative-critique/1"
    assert result["decision"] == "needs_revision"
    assert result["independent_artwork_acceptance"] is False
    assert result["artwork_png_sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert result["issues"][0]["id"] == "issue-1"


def test_critic_refuses_claims_without_visible_observations(tmp_path):
    image = make_image(tmp_path)
    class Bad(FakeCritic):
        def complete_json(self, *args, **kwargs):
            return {"decision": "pass", "observations": "fine", "issues": []}
    with pytest.raises(TaskError, match="actual image"):
        critique(sample_scene(), image, Bad())


def test_critique_revision_compiles_native_strokes_into_new_layer(tmp_path):
    image = make_image(tmp_path)
    observed = critique(sample_scene(), image, FakeCritic())
    candidate = {
        "object_id": "clouds",
        "brush": {"color": "#e9a1b2", "size": 28},
        "elements": [{"kind": "stroke", "points": [
            {"x": 30, "y": 66, "pressure": .2},
            {"x": 110, "y": 50, "pressure": .8},
            {"x": 210, "y": 90, "pressure": .3},
        ]}],
    }
    plan = validate_revision(sample_scene(), observed, image, candidate, "issue-1")
    assert plan["schema"] == "krita-agent-creative-revision/1"
    assert plan["approval"] == "required"
    assert plan["steps"][0]["command"] == "layer.create"
    assert all(step["command"] in ("layer.create", "brush.configure", "draw.stroke")
               for step in plan["steps"])
    with pytest.raises(TaskError, match="explicit user approval"):
        execute_revision(object(), plan, sample_scene(), image, tmp_path)


def test_revision_rejects_unapproved_roi_and_stale_source(tmp_path):
    image = make_image(tmp_path)
    observed = critique(sample_scene(), image, FakeCritic())
    candidate = {
        "object_id": "clouds",
        "brush": {"color": "#ffffff"},
        "elements": [{"kind": "stroke", "points": [
            {"x": 30, "y": 70}, {"x": 400, "y": 100}
        ]}],
    }
    with pytest.raises(TaskError, match="escaped"):
        validate_revision(sample_scene(), observed, image, candidate, "issue-1")
    Image = pytest.importorskip("PIL.Image")
    Image.new("RGB", (512, 384), "red").save(image)
    with pytest.raises(TaskError, match="stale"):
        validate_revision(sample_scene(), observed, image, candidate, "issue-1")
