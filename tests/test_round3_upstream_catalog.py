"""Offline synthetic Git tests; no network, no upstream code execution."""
import subprocess
from pathlib import Path
import pytest
from krita_agent.upstream3 import catalog, registry_record, registry_list


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_python_api_catalog(tmp_path):
    git(tmp_path, "init")
    src = tmp_path / "plugins/extensions/pykrita"
    src.mkdir(parents=True)
    p = src / "test.py"
    p.write_text("class Drawing:\n    def line(self, x):\n        pass\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=T", "-c", "user.email=t@example.invalid",
        "commit", "-m", "start")
    before = git(tmp_path, "rev-parse", "HEAD")
    p.write_text("class Drawing:\n    def line(self, x, pressure=1):\n        pass\n    def stroke(self, pts):\n        pass\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=T", "-c", "user.email=t@example.invalid",
        "commit", "-m", "change")
    report = catalog(tmp_path, before)
    changes = {item["symbol"]: item["kind"] for item in report["api_candidates"]}
    assert changes["Drawing.line"] == "signature_changed"
    assert changes["Drawing.stroke"] == "added"
    assert all(x["evidence"] == "source_seen" for x in report["api_candidates"])


def test_capability_registry_manual_evidence(tmp_path):
    evidence = tmp_path / "actual-report.txt"
    evidence.write_text("User-provided build-specific acceptance evidence", encoding="utf-8")
    store = tmp_path / "registry.json"
    with pytest.raises(ValueError):
        registry_record(store, "Stable", "Node.paintLine", "tested_working", evidence)
    registry_record(store, "Stable", "Node.paintLine", "present_in_build", evidence)
    registry_record(store, "Qt6", "Node.paintPolylineStroke", "tested_working", evidence,
                    confirm=True)
    assert len(registry_list(store)["entries"]) == 2
    with pytest.raises(ValueError):
        registry_record(store, "Stable", "Node.paintLine", "present_in_build", evidence)
