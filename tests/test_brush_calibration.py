"""Native brush calibration matrix and evidence catalogue tests."""
import json

import pytest

from krita_agent.brush_profiles import (
    calibration_task, choose, find_profiles, record_profile,
)
from krita_agent.workflow import compile_workflow


def test_calibration_matrix_covers_pressure_ramps_and_size_ladder():
    task = calibration_task("Pencil-2", 24)
    assert task["schema"] == "krita-agent-brush-calibration-task/2"
    assert task["manual_review_required"] is True
    assert [item["id"] for item in task["checks"]] == [
        "pressure_ladder", "pressure_ramps", "size_ladder",
    ]
    compiled = compile_workflow(task)
    strokes = [
        step["parameters"] for step in compiled
        if step["command"] == "draw.stroke"
    ]
    brushes = [
        step["parameters"] for step in compiled
        if step["command"] == "brush.configure"
    ]
    assert len(strokes) == 9
    assert [stroke["points"][0]["pressure"] for stroke in strokes[:4]] == [
        0.1, 0.3, 0.6, 0.9,
    ]
    assert [point["pressure"] for point in strokes[4]["points"]] == [
        0.05, 0.25, 0.5, 0.75, 0.95,
    ]
    assert [point["pressure"] for point in strokes[5]["points"]] == [
        0.95, 0.75, 0.5, 0.25, 0.05,
    ]
    assert [item["size"] for item in brushes] == [24.0, 24.0, 12.0, 24.0, 48.0]
    assert all(item["pressure_enabled"] is True for item in brushes)
    assert all(
        point["time_ms"] >= 0 and 0 <= point["pressure"] <= 1
        for stroke in strokes for point in stroke["points"]
    )


@pytest.mark.parametrize("size", [0.1, 12, 250, 500])
def test_calibration_size_ladder_stays_inside_native_brush_bounds(size):
    task = calibration_task("Pencil-2", size)
    assert all(0.1 <= value <= 500 for value in task["size_levels"])
    assert float(size) in task["size_levels"]
    assert task["nominal_size"] == float(size)


@pytest.mark.parametrize("preset,size", [("", 24), ("x" * 121, 24), ("Pencil", 0), ("Pencil", 501)])
def test_calibration_task_rejects_invalid_inputs(preset, size):
    with pytest.raises(ValueError):
        calibration_task(preset, size)


def test_profile_recording_requires_reviewable_evidence_and_hashes_it(tmp_path):
    evidence = tmp_path / "calibration.png"
    evidence.write_bytes(b"reviewed native calibration evidence")
    record = {
        "preset": "Pencil-2",
        "build": "Krita 5.3.4.1 Qt5",
        "category": "paint",
        "pressure_size": True,
        "pressure_opacity": False,
        "confidence": 0.95,
    }
    profile = record_profile(tmp_path / "profiles", record, evidence)
    found = find_profiles(
        tmp_path / "profiles", build=record["build"],
        category="paint", min_confidence=0.9,
    )
    assert found == [profile]
    assert choose(tmp_path / "profiles", record["build"], "paint") == profile
    assert profile["status"] == "manually_reviewed"
    evidence.write_bytes(b"changed after review")
    assert find_profiles(tmp_path / "profiles") == []
    with pytest.raises(ValueError, match="No manually reviewed"):
        choose(tmp_path / "profiles", record["build"], "paint")


def test_profile_catalogue_skips_malformed_and_unreviewed_records(tmp_path):
    root = tmp_path / "profiles"
    root.mkdir()
    (root / "malformed.json").write_text(
        json.dumps({"schema": "krita-agent-brush-profile/1"}),
        encoding="utf-8",
    )
    (root / "unreviewed.json").write_text(
        json.dumps({
            "schema": "krita-agent-brush-profile/1",
            "preset": "Pencil", "build": "Build", "category": "paint",
            "pressure_size": True, "pressure_opacity": False,
            "confidence": 0.99, "evidence_path": str(tmp_path / "none.png"),
            "evidence_sha256": "0" * 64, "status": "generated",
        }),
        encoding="utf-8",
    )
    assert find_profiles(root) == []


@pytest.mark.parametrize("patch", [
    {"category": "unknown"},
    {"preset": ""},
    {"build": ""},
    {"pressure_size": 1},
    {"pressure_opacity": "yes"},
    {"confidence": True},
    {"confidence": 1.1},
])
def test_profile_recording_rejects_invalid_review_metadata(tmp_path, patch):
    evidence = tmp_path / "calibration.png"
    evidence.write_bytes(b"evidence")
    record = {
        "preset": "Pencil",
        "build": "Krita Build",
        "category": "paint",
        "pressure_size": True,
        "pressure_opacity": False,
        "confidence": 0.9,
    }
    record.update(patch)
    with pytest.raises(ValueError):
        record_profile(tmp_path / "profiles", record, evidence)


def test_profile_recording_does_not_allow_metadata_override(tmp_path):
    evidence = tmp_path / "calibration.png"
    evidence.write_bytes(b"reviewed evidence")
    record = {
        "preset": "Pencil",
        "build": "  Krita Build  ",
        "category": "paint",
        "pressure_size": True,
        "pressure_opacity": False,
        "confidence": 0.9,
        "schema": "attacker-schema",
        "status": "generated",
        "id": "caller-controlled-id",
        "evidence_sha256": "0" * 64,
        "evidence_path": "missing.png",
    }
    profile = record_profile(tmp_path / "profiles", record, evidence)
    assert profile["schema"] == "krita-agent-brush-profile/1"
    assert profile["status"] == "manually_reviewed"
    assert profile["id"] != "caller-controlled-id"
    assert profile["evidence_path"] == str(evidence.resolve())
    assert profile["evidence_sha256"] != "0" * 64
    assert profile["build"] == "Krita Build"
