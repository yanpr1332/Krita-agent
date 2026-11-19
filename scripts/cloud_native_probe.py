"""Real-Krita CI probe. Never synthesize images, KRA, or reviewer verdicts.

Run only against a disposable locally authenticated Krita Bridge and a scratch
output root. Any ambiguous mutating request aborts; it is never retried.
"""
import argparse
import json
import os
import shutil
import time
import traceback
import zipfile
from pathlib import Path

from PIL import Image

from krita_agent.artifact_integrity import (
    export_integrity, reopen_stability, sha256,
)
from krita_agent.client import BridgeError, Client


def _write_report(root, report):
    target = root / "cloud-native-report.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(target)


def wait_until_ready(client, *, seconds=90, sleep=time.sleep, clock=time.monotonic):
    """Retry only the read-only status probe; never retry a native mutation."""
    deadline = clock() + seconds
    last_error = "Bridge not responding"
    while clock() < deadline:
        try:
            status = client.request("status")
            if isinstance(status, dict) and status.get("connected") is True and status.get("krita_version"):
                return status
            last_error = "Bridge returned an invalid native status"
        except BridgeError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        sleep(1)
    raise RuntimeError("Real Krita Bridge did not become available: " + last_error)


def _ensure_real_files(root, kra, first, reopened):
    for file in (kra, first, reopened):
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
            raise RuntimeError("Expected real native output was not created inside sandbox: " + file.name)
        if file.stat().st_size < 100:
            raise RuntimeError("Native output unexpectedly small: " + file.name)
    with zipfile.ZipFile(kra) as archive:
        needed = {"maindoc.xml", "mergedimage.png"}
        if not needed.issubset(archive.namelist()):
            raise RuntimeError("KRA is missing required native archive contents")
        if archive.testzip() is not None:
            raise RuntimeError("KRA ZIP CRC validation failed")
        xml = archive.read("maindoc.xml")
        if b"paintlayer" not in xml.lower() and b"paint layer" not in xml.lower():
            raise RuntimeError("No editable paint layer evidence found in KRA metadata")
    with Image.open(first) as png:
        if png.size != (128, 128):
            raise RuntimeError("Native PNG dimensions differ from requested canvas")
        rgba = png.convert("RGBA")
        native_ink_pixels = sum(
            1 for r, g, b, a in rgba.getdata()
            if a > 0 and r > g + 12 and r > b + 12
        )
    if native_ink_pixels < 10:
        raise RuntimeError(f"Real PNG does not show the expected colored brushwork ({native_ink_pixels} pixels)")
    return native_ink_pixels


def perform_native_smoke(client, output_dir, *, wait=90):
    """Execute only the minimum native Krita operations on a new throwaway canvas."""
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "krita-agent-cloud-native-smoke/1",
        "runner": "cloud-real-krita-pilot",
        "is_simulated": False,
        "status": "running",
        "native_steps": [],
    }
    _write_report(root, report)

    def command(action, **kwargs):
        # Client.request generates a new request ID; on an ambiguous effect,
        # stop and preserve files/logs. Never do hidden retry.
        result = client.request(action, **kwargs)
        report["native_steps"].append(action)
        _write_report(root, report)
        return result

    try:
        status = wait_until_ready(client, seconds=wait)
        report["krita"] = {"version": status["krita_version"],
                           "output_root": str(root)}
        if Path(status.get("output_dir", "")).resolve() != root:
            raise RuntimeError("Bridge output sandbox does not match the isolated CI output root")

        command("canvas.create", width=128, height=128, name="Krita Agent CI Native Stroke")
        command("layer.create", name="Cloud CI Ink")
        command("brush.configure", color="#EE5544", size=15, opacity=1.0,
                pressure_enabled=False)
        stroke = command(
            "draw.stroke", mode="segmented",
            points=[{"x": 19, "y": 28, "pressure": 1.0},
                    {"x": 47, "y": 49, "pressure": 1.0},
                    {"x": 81, "y": 50, "pressure": 1.0},
                    {"x": 110, "y": 95, "pressure": 1.0}],
        )
        report["stroke"] = stroke
        report["document"] = command("document.info")
        report["layers"] = command("layer.list")
        command("document.save", path="native-smoke.kra")
        command("document.export", path="native-smoke.png")

        kra = root / "native-smoke.kra"
        initial = root / "native-smoke.png"
        copied = root / "native-smoke-fresh-copy.kra"
        reopened = root / "native-smoke-reopened.png"

        if not kra.is_file() or not initial.is_file():
            raise RuntimeError("Native save/export did not write expected files")
        # Keep the original immutable; the reopened document is a fresh independent copy.
        shutil.copy2(kra, copied)
        command("document.open", path=copied.name)
        command("document.export", path=reopened.name)

        ink_pixels = _ensure_real_files(root, kra, initial, reopened)
        report["native_ink_pixels"] = ink_pixels
        report["sha256"] = {p.name: sha256(p) for p in (kra, initial, copied, reopened)}
        report["export_integrity"] = export_integrity(kra, initial)
        report["reopen_stability"] = reopen_stability(
            initial, reopened, kra_sha256=report["sha256"][kra.name]
        )
        if report["export_integrity"]["status"] != "pass":
            raise RuntimeError("Native KRA embedded render differs from exported PNG")
        if report["reopen_stability"]["status"] != "pass":
            raise RuntimeError("Native freshly reopened KRA differs from the initial PNG/ICC")
        report["status"] = "cloud_native_verified"
        return report
    except Exception as exc:
        report["status"] = "cloud_native_unverified"
        report["failure"] = {"type": type(exc).__name__, "reason": str(exc)}
        raise
    finally:
        _write_report(root, report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--port", type=int, default=47653)
    parser.add_argument("--ready-timeout", type=int, default=90)
    args = parser.parse_args()
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.ready_timeout < 1 or args.ready_timeout > 240:
        parser.error("--ready-timeout must be 1..240")
    token = os.getenv("KRITA_AGENT_TOKEN")
    if not token or len(token) < 20:
        parser.error("A fresh KRITA_AGENT_TOKEN is required")
    client = Client(token, port=args.port, timeout=25)
    try:
        report = perform_native_smoke(client, root, wait=args.ready_timeout)
        print(json.dumps({"status": report["status"],
                          "krita_version": report["krita"]["version"],
                          "native_ink_pixels": report["native_ink_pixels"],
                          "strict_export": True, "strict_reopen": True}))
        return 0
    except Exception as exc:
        print(f"Cloud native probe FAILED (no native acceptance): {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
