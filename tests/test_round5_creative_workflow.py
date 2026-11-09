"""CreativeWorkflow lifecycle, approval gates and fail-closed native actions."""
import io
import json
import zipfile
from pathlib import Path

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


class ReopenStub:
    """Offline Bridge double only; NOT evidence of a real Krita reopen."""
    def __init__(self, root, altered_pixels=0):
        from PIL import Image
        self.Image = Image
        self.root = root / "bridge-output"
        self.root.mkdir(exist_ok=True)
        self.altered_pixels = altered_pixels
        self.opened = None
        self.active = 0
        self.requests = []

    def request(self, command, **params):
        self.requests.append(command)
        if command == "status":
            return {"output_dir": str(self.root)}
        if command == "document.list":
            rows = [{"index": 0, "name": "Original painting", "active": self.active == 0,
                     "file_path": str(self.root / "original.kra")}]
            if self.opened is not None:
                rows.append({"index": 1, "name": "Fresh copy",
                             "active": self.active == 1,
                             "file_path": str(self.opened)})
            return rows
        if command == "document.open":
            path = (self.root / params["path"]).resolve()
            assert path.is_file() and self.opened is None
            self.opened = path
            self.active = 1
            return {"opened": str(path), "index": 1}
        if command == "document.activate":
            assert params["index"] in (0, 1)
            self.active = params["index"]
            return {"active": "Original painting" if self.active == 0 else "Fresh copy"}
        if command == "document.export":
            assert self.active == 1 and self.opened is not None
            path = (self.root / params["path"]).resolve()
            with zipfile.ZipFile(self.opened) as archive:
                pixels = archive.read("mergedimage.png")
            import io
            with self.Image.open(io.BytesIO(pixels)) as original:
                original_mode = original.mode
                fresh = original.convert("RGBA")
            for x in range(self.altered_pixels):
                red, green, blue, alpha = fresh.getpixel((x, 0))
                fresh.putpixel((x, 0), (red + 1, green, blue, alpha))
            fresh.convert(original_mode).save(path)
            return {"path": str(path), "format": "png"}
        if command == "document.close":
            assert params == {"index": 1, "confirm": True}
            self.opened = None
            self.active = 0
            return {"closed": True}
        raise AssertionError("Unexpected Bridge command: " + command)


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
    assert flow.read()["status"] == "awaiting_reopen"
    verified = flow.verify_reopen(ReopenStub(tmp_path))
    assert verified["status"] == "awaiting_critique"
    assert verified["reopen_stability"]["pixels"]["strict_match"] is True


def test_critique_creates_internal_report_not_fake_human_acceptance(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "r", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *args, **kw: {"state": "completed", "ledger": "unit-test"})
    flow.paint(object())
    kra, png = native_fixture(tmp_path)
    flow.record_artwork(kra, png)
    flow.verify_reopen(ReopenStub(tmp_path))

    class PassingCritic:
        model = "test-only"
        def complete_json(self, system, prompt, image_paths=()):
            assert len(image_paths) >= 2
            return {
                "decision": "pass",
                "observations": (
                    "Actual PNG pixels were reviewed in this stub test. "
                    "This is not an independent real artistic review."
                ),
                "object_findings": {
                    oid: {
                        "quality": "good", "recognizable": True,
                        "evidence": "A visible native artwork component is present for this object.",
                    } for oid in ("sky", "clouds", "mountain")
                },
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


def test_five_pixel_reopen_drift_is_reported_but_never_accepted(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *a, **k: {"state": "completed"})
    flow.paint(object())
    kra, png = native_fixture(tmp_path)
    flow.record_artwork(kra, png)
    first_sha = module._sha(flow.root / "versions/v01.kra")
    result = flow.verify_reopen(ReopenStub(tmp_path, altered_pixels=5))
    assert result["status"] == "review_blocked"
    metrics = result["reopen_stability"]["pixels"]
    assert metrics["different_pixels"] == 5
    assert metrics["max_channel_difference"] == 1
    assert metrics["alpha_different_pixels"] == 0
    assert metrics["minor_color_tolerance"]["within_tolerance"] is True
    assert module._sha(flow.root / "versions/v01.kra") == first_sha
    assert (flow.root / "versions/v01-reopened.png").is_file()
    assert (flow.root / "versions/v01-integrity-verified.json").is_file()
    with pytest.raises(TaskError, match="expected awaiting_critique"):
        flow.critique(object())
    with pytest.raises(TaskError, match="expected ready_for_delivery"):
        flow.prepare_delivery()


def test_export_mismatch_archives_original_failure_before_block(tmp_path, monkeypatch):
    from PIL import Image
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *a, **k: {"state": "completed"})
    flow.paint(object())
    kra, png = native_fixture(tmp_path)
    with Image.open(png) as image:
        altered = image.copy()
    altered.putpixel((0, 0), (21, 30, 40))
    altered.save(png)
    result = flow.record_artwork(kra, png)
    assert result["status"] == "review_blocked"
    assert result["export_integrity"]["pixels"]["different_pixels"] == 1
    assert (flow.root / "versions/v01.kra").is_file()
    assert (flow.root / "versions/v01.png").is_file()
    with pytest.raises(TaskError, match="new-version"):
        flow.record_artwork(kra, png)


def test_repaired_candidate_gets_new_version_and_preserves_failed_one(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *a, **k: {"state": "completed"})
    flow.paint(object())
    kra, png = native_fixture(tmp_path)
    flow.record_artwork(kra, png)
    assert flow.verify_reopen(ReopenStub(tmp_path, altered_pixels=5))["status"] == "review_blocked"
    failed_sha = module._sha(flow.root / "versions/v01.kra")
    repaired = tmp_path / "repaired.kra"
    with zipfile.ZipFile(repaired, "w") as archive:
        archive.writestr("maindoc.xml", "<DOC/>")
        archive.writestr("mergedimage.png", png.read_bytes())
        archive.writestr("editable-repair-layer", "synthetic-unit-fixture")
    candidate = flow.record_artwork(repaired, png, confirm_new_version=True)
    assert candidate["version"] == 2
    assert candidate["status"] == "awaiting_reopen"
    assert flow.verify_reopen(ReopenStub(tmp_path))["status"] == "awaiting_critique"
    assert module._sha(flow.root / "versions/v01.kra") == failed_sha
    assert module._sha(flow.root / "versions/v02.kra") != failed_sha


def test_lost_fresh_reopen_reply_is_never_retried(tmp_path, monkeypatch):
    flow = CreativeWorkflow.create(tmp_path / "run", brief())
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(module, "run_longjob",
                        lambda *a, **k: {"state": "completed"})
    flow.paint(object())
    kra, png = native_fixture(tmp_path)
    flow.record_artwork(kra, png)

    class LostOpen(ReopenStub):
        def request(self, command, **params):
            if command == "document.open":
                self.requests.append(command)
                raise TimeoutError("Lost acknowledgement for potentially opened document")
            return super().request(command, **params)

    stub = LostOpen(tmp_path)
    with pytest.raises(TimeoutError):
        flow.verify_reopen(stub)
    assert flow.read()["status"] == "unknown_needs_review"
    with pytest.raises(TaskError):
        flow.verify_reopen(stub)
    assert stub.requests.count("document.open") == 1
    assert (flow.root / "versions/v01.kra").is_file()
