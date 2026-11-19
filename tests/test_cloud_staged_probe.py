"""Offline guardrails for the synthetic cloud Tier-2 staged fixture.

These tests check compilation and safety, not actual Krita painting.
"""
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

from krita_agent.client import BridgeError


def _module():
    source = Path(__file__).resolve().parents[1] / "scripts" / "cloud_staged_probe.py"
    spec = importlib.util.spec_from_file_location("cloud_staged_probe", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_staged_fixture_compiles_deterministically_with_bounded_native_commands():
    module = _module()
    a = module.compile_fixture()
    b = module.compile_fixture()
    assert a["source_v4_sha256"] == b["source_v4_sha256"]
    assert a["native_steps_sha256"] == b["native_steps_sha256"]
    assert a["steps"] == b["steps"]
    assert len(a["stage_spans"]) == 3
    assert len(a["stage_layers"]) == 6
    assert a["steps"][0]["command"] == "canvas.create"
    assert len(a["steps"]) <= 110
    assert {item["command"] for item in a["steps"]} <= module.ALLOWED_NATIVE
    assert sum(item["command"] == "draw.stroke" for item in a["steps"]) >= 8
    assert all(s["native_steps"] > 0 for s in a["stage_spans"])


def test_staged_probe_fails_closed_before_native_mutation_if_bridge_drops(tmp_path):
    module = _module()
    class FailOnFirstMutation:
        calls = []
        def request(self, action, **params):
            self.calls.append(action)
            if action == "status":
                return {"connected": True, "krita_version": "FAKE (not Krita)",
                        "output_dir": str(tmp_path)}
            raise BridgeError("lost response after unknown native effect")
    client = FailOnFirstMutation()
    with pytest.raises(BridgeError, match="unknown native"):
        module.execute_staged_fixture(client, tmp_path)
    report = json.loads((tmp_path / "cloud-staged-report.json").read_text())
    assert report["status"] == "cloud_native_unverified"
    assert report["commands_completed"] == 0
    assert client.calls == ["status", "canvas.create"]
    assert report["is_simulated"] is False


def test_staged_preview_delta_utility_does_not_conflate_same_images(tmp_path):
    module = _module()
    a = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    b = Image.new("RGBA", (128, 128), (255, 255, 255, 255))
    b.putpixel((10, 10), (70, 20, 130, 255))
    ap, bp = tmp_path / "a.png", tmp_path / "b.png"
    a.save(ap)
    b.save(bp)
    assert module._pixel_change(ap, ap) == 0
    assert module._pixel_change(ap, bp) == 1
