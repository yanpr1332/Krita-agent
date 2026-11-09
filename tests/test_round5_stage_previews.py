"""Native stage-preview lifecycle and read-only status dashboard tests."""
import json
from pathlib import Path
import zipfile

import pytest

from krita_agent import creative_workflow as workflow_module
from krita_agent.creative_dashboard import render as render_dashboard
from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.scene_v3 import compile_scene_v3
from test_round5_creative_scene import sample_scene
from test_round5_creative_workflow import ReopenStub


def test_v3_compiles_three_actual_krita_stage_preview_commands():
    scene = sample_scene()
    compiled = compile_scene_v3(
        scene, preview_prefix="r5-runs/" + "a" * 32
    )
    paths = compiled["stage_preview_paths"]
    assert len(paths) == 3
    assert paths[0].endswith("/stages/01-layout.png")
    assert paths[1].endswith("/stages/02-color.png")
    assert paths[2].endswith("/stages/03-final.png")
    previews = [step for step in compiled["steps"]
                if step["command"] == "preview.canvas"]
    assert len(previews) == 3
    assert all(item["parameters"]["width"] == 512
               and item["parameters"]["height"] == 384
               for item in previews)


def test_native_export_archives_three_real_stage_previews(tmp_path, monkeypatch):
    Image = pytest.importorskip("PIL.Image")
    flow = CreativeWorkflow.create(
        tmp_path / "artwork-results" / "painting", {
            "prompt": "Draw an alpine landscape with clouds, mountains, water and light.",
            "width": 512, "height": 384
        }
    )
    flow.plan(candidate=sample_scene())
    flow.approve_plan(confirm=True)
    monkeypatch.setattr(workflow_module, "run_longjob",
                        lambda *args, **kw: {"state": "completed", "ledger": "stub"})
    flow.paint(object())
    exported = tmp_path / "native-output"
    exported.mkdir()
    png = exported / "actual.png"
    Image.new("RGB", (512, 384), (15, 30, 45)).save(png)
    kra = exported / "actual.kra"
    with zipfile.ZipFile(kra, "w") as archive:
        archive.writestr("maindoc.xml", "<DOC/>")
        archive.writestr("mergedimage.png", png.read_bytes())
    compiled = json.loads((flow.root/"compiled-scene.json").read_text())
    for index, rel in enumerate(compiled["stage_preview_paths"]):
        native_stage = exported / rel
        native_stage.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (512, 384), (30*index, 45, 65)).save(native_stage)

    class Client(ReopenStub):
        def __init__(self):
            super().__init__(tmp_path)
            self.root = exported

        def request(self, name, **params):
            if name == "document.save":
                return {"path": str(kra)}
            if name == "document.export" and self.opened is None:
                return {"path": str(png)}
            return super().request(name, **params)

    result = flow.export_native(Client())
    assert result["status"] == "awaiting_critique"
    stages = flow.read()["artifacts"]["stage_previews"]
    assert set(stages) == {"01-layout.png", "02-color.png", "03-final.png"}
    for name in stages:
        assert (flow.root / "stages" / name).is_file()

    # A subsequent export follows a revision and must reuse the original stages.
    record = flow.read()
    record["status"] = "awaiting_export"
    flow._save(record, "test_revision_completed")
    stage_bytes = {name: (flow.root / entry["path"]).read_bytes()
                   for name, entry in stages.items()}
    revised = flow.export_native(Client())
    assert revised["version"] == 2
    assert flow.read()["artifacts"]["stage_previews"] == stages
    assert all((flow.root / stages[name]["path"]).read_bytes() == content
               for name, content in stage_bytes.items())


def test_html_dashboard_escapes_user_title_and_shows_status(tmp_path):
    flow = CreativeWorkflow.create(
        tmp_path / "artwork-results" / "run", {
            "prompt": "Paint a landscape with multiple editable layers.",
            "title": "<script>not executable</script>"
        }
    )
    result = render_dashboard(flow)
    page = Path(result["path"]).read_text(encoding="utf-8")
    assert result["read_only"] is True
    assert "&lt;script&gt;" in page
    assert "<script>not executable</script>" not in page
    assert "initialized" in page
    with pytest.raises(FileExistsError):
        render_dashboard(flow)
    assert render_dashboard(flow, replace=True)["read_only"] is True
