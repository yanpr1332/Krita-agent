"""CreativeWorkflow lifecycle, approval gates and fail-closed native actions."""
import io
import json
import zipfile

import pytest
from krita_agent import creative_workflow as module
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.protocol import TaskError
from test_round5_creative_scene import sample_scene


def brief():
    return {
        "prompt": "Paint a mountain and cloud landscape in a warm evening light.",
        "width": 512, "height": 384, "title": "Artwork acceptance candidate",
    }


def native_fixture(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    image = tmp_path / "native-output.png"
    Image.new("RGB", (512, 384), (20, 30, 40)).save(image)
    kra = tmp_path / "native-output.kra"
    with zipfile.ZipFile(kra, "w") as archive:
        archive.writestr("maindoc.xml", "<DOC/>")
        archive.writestr("mergedimage.png", image.read_bytes())
    return kra, image


def test_lifecycle_requires_approval_before_native_mutation(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "artwork-results" / "run-1", brief())
    assert flow.read()["status"] == "initialized"
    assert flow.plan(candidate=sample_scene())["status"] == "planned"
    with pytest.raises(TaskError, match="approval"):
        flow.approve_plan()
    with pytest.raises(TaskError, match="expected plan_approved"):
        flow.paint(object())
    flow.approve_plan(confirm=True)
    calls = []
    def simulate_native(client, spec, ledger_dir, batch_steps=120):
        calls.append(spec)
        return {"state": "completed", "ledger": "fake-unit-test-ledger"}
    monkeypatch.setattr(module, "run_longjob", simulate_native)
    result = flow.paint(object())
    assert result["status"] == "awaiting_export"
    assert len(calls) == 1
    with pytest.raises(TaskError, match="expected plan_approved"):
        flow.paint(object())
    assert len(calls) == 1
    kra, png = native_fixture(tmp_path)
    saved = flow.record_artwork(kra, png)
    assert saved["version"] == 1
    assert (flow.root / "versions/v01.kra").is_file()
    assert (flow.root / "versions/v01.png").is_file()
    assert flow.read()["status"] == "awaiting_critique"


def test_critique_creates_internal_report_not_fake_human_acceptance(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "r", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *args, **kw: {"state": "completed", "ledger": "unit-test"})
    flow.paint(object())
    kra, png = native_fixture(tmp_path)
    flow.record_artwork(kra, png)

    class PassingCritic:
        model = "test-only"
        def complete_json(self, system, prompt, image_paths=()):
            assert len(image_paths) == 1
            return {
                "decision": "pass",
                "observations": (
                    "Actual PNG pixels were reviewed in this stub test. "
                    "This is not an independent real artistic review."
                ),
                "issues": [],
            }

    result = flow.critique(PassingCritic())
    assert result["status"] == "ready_for_delivery"
    delivery = flow.prepare_delivery()
    assert delivery["status"] == "delivery_prepared"
    assert delivery["delivery"]["full_artwork_accepted"] is False
    assert delivery["delivery"]["independent_visual_review"] == "pending"
    assert (flow.root / "artwork.kra").is_file()
    assert (flow.root / "artwork.png").is_file()
    with pytest.raises(TaskError, match="expected ready_for_delivery"):
        flow.prepare_delivery()


def test_unknown_paint_state_never_resubmits(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    calls = []
    def unknown(*args, **kwargs):
        calls.append(1)
        return {"state": "unknown_needs_review", "ledger": "unit-test"}
    monkeypatch.setattr(module, "run_longjob", unknown)
    assert flow.paint(object())["status"] == "unknown_needs_review"
    with pytest.raises(TaskError):
        flow.paint(object())
    assert len(calls) == 1


def test_unknown_export_does_not_auto_retry(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *args, **kw: {"state": "completed", "ledger": "unit-test"})
    flow.paint(object())
    class LostReply:
        count = 0
        def request(self, command, **params):
            self.count += 1
            raise TimeoutError("Reply lost after possible native save")
    client = LostReply()
    with pytest.raises(TimeoutError):
        flow.export_native(client)
    assert flow.read()["status"] == "export_unknown"
    with pytest.raises(TaskError):
        flow.export_native(client)
    assert client.count == 1


def test_model_candidate_cannot_change_approved_canvas(tmp_path):
    flow = CreativeWorkflow.create(tmp_path / "r", brief())
    scene = sample_scene()
    scene["document"]["width"] += 1
    with pytest.raises(TaskError, match="dimensions"):
        flow.plan(candidate=scene)
    assert flow.read()["status"] == "initialized"
