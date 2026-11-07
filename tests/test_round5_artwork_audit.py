import hashlib
import importlib.util
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "artwork_acceptance_audit.py"
SPEC = importlib.util.spec_from_file_location("artwork_acceptance_audit", SCRIPT)
AUDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDITOR)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _png_bytes(size=(1600, 900)):
    stream = io.BytesIO()
    Image.new("RGB", size, (32, 48, 64)).save(stream, format="PNG")
    return stream.getvalue()


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def make_run(tmp_path):
    root = tmp_path / "repo"
    (root / "benchmarks/artwork/contracts").mkdir(parents=True)
    (root / "benchmarks/artwork/reference").mkdir(parents=True)
    original_root = Path(__file__).resolve().parents[1]
    contract = json.loads(
        (original_root / "benchmarks/artwork/contracts/sunset_alpine_lake.v1.json")
        .read_text(encoding="utf-8")
    )
    shutil.copyfile(
        original_root / contract["reference"]["path"],
        root / contract["reference"]["path"],
    )
    _write_json(root / "benchmarks/artwork/contracts/sunset_alpine_lake.v1.json", contract)
    AUDITOR.ROOT = root
    run = root / "artwork-results" / "fixture"
    (run / "stages").mkdir(parents=True)
    (run / "reviews").mkdir()
    png = _png_bytes()
    for name in ("artwork.png", "krita-screen.png",
                 "stages/01-layout.png", "stages/02-color.png", "stages/03-final.png"):
        (run / name).write_bytes(png)
    (run / "scene-plan.json").write_text("{}", encoding="utf-8")
    _write_json(run / "execution.json", {
        "commands": [{"command": "draw.stroke"}],
        "imported_reference_as_final_artwork": False,
    })
    node_ids = ["paint-" + str(index) for index in range(8)]
    _write_json(run / "layer-graph.json", {
        "document": {"width": 1600, "height": 900},
        "nodes": [{"id": node_id, "type": "paintlayer"} for node_id in node_ids],
    })
    _write_json(run / "layer-contributions.json", {
        "layers": [{
            "node_id": node_id,
            "visible_contribution": True,
            "description": "Distinct painted contribution on this editable layer.",
        } for node_id in node_ids],
    })
    kra = run / "artwork.kra"
    with zipfile.ZipFile(kra, "w") as archive:
        archive.writestr("maindoc.xml", "<DOC/>")
        archive.writestr("mergedimage.png", png)
    required = [item["key"] for item in contract["subject"]["required_objects"]]
    stages = {
        rel: _sha(run / rel)
        for rel in ("stages/01-layout.png", "stages/02-color.png", "stages/03-final.png")
    }
    png_sha = _sha(run / "artwork.png")
    kra_sha = _sha(kra)
    visual = {
        "schema": "krita-agent-artwork-vlm/2",
        "model": "test-visual-reviewer",
        "reviewed_at": "2026-11-07T12:00:00Z",
        "reference_sha256": contract["reference"]["sha256"],
        "artwork_png_sha256": png_sha,
        "reviewed_inputs": {
            "artwork_kra_sha256": kra_sha,
            "stage_previews": stages,
        },
        "decision": "pass",
        "coherent_full_scene": True,
        "objects": {key: True for key in required},
        "object_evidence": {key: "Visible evidence for " + key + " in the final artwork." for key in required},
        "relations": [{
            "description": relation,
            "passes": True,
            "evidence": "The spatial relationship is directly visible in the reviewed image.",
        } for relation in contract["subject"]["required_relations"]],
        "failure_modes": [],
        "notes": "The final scene is coherent and all required subjects are recognizable.",
    }
    human = {
        "schema": "krita-agent-artwork-human/2",
        "decision": "pass",
        "reviewer": "Independent test reviewer",
        "reviewed_at": "2026-11-07T12:00:00Z",
        "artwork_png_sha256": png_sha,
        "artwork_kra_sha256": kra_sha,
        "coherent_full_scene": True,
        "kra_reopened_and_viewed": True,
        "all_required_objects_recognizable": True,
        "object_checks": {key: True for key in required},
        "observations": "The KRA reopened and the required visual elements were inspected.",
    }
    _write_json(run / "reviews/visual-model.json", visual)
    _write_json(run / "reviews/human.json", human)
    return run


def test_audit_accepts_only_consistent_hash_bound_review_records(tmp_path):
    run = make_run(tmp_path)
    result = AUDITOR.audit(run)
    assert result["status"] == "pass"
    assert result["schema"] == "krita-agent-artwork-audit/2"
    assert result["artwork_kra_sha256"] == _sha(run / "artwork.kra")


def test_audit_rejects_stale_human_review(tmp_path):
    run = make_run(tmp_path)
    record = json.loads((run / "reviews/human.json").read_text(encoding="utf-8"))
    record["artwork_png_sha256"] = "0" * 64
    _write_json(run / "reviews/human.json", record)
    result = AUDITOR.audit(run)
    assert result["status"] == "fail"
    assert any("Human review is not bound to the final PNG" in error for error in result["errors"])
