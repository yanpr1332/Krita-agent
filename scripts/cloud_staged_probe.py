"""Cloud Tier-2 generalist staged fixture using *real* Krita native strokes.

The scene is tiny, synthetic, pre-reviewed test geometry, not user artwork.
No model API or raster paste is involved. Failed/unknown effects are never retried.
"""
import argparse
import json
import os
import shutil
import time
import zipfile
from pathlib import Path

from PIL import Image, ImageChops

from krita_agent.artifact_integrity import export_integrity, reopen_stability, sha256
from krita_agent.client import Client
from krita_agent.scene_v4 import compile_scene_v4

ALLOWED_NATIVE = frozenset({"canvas.create", "layer.create", "brush.configure",
                            "draw.stroke", "preview.canvas"})
PREVIEW_PREFIX = "r5-runs/" + "d" * 32


def synthetic_scene():
    """Reviewable deterministic 128x128 multi-subject, multi-phase source fixture."""
    return {
        "schema": "krita-agent-scene/4",
        "document": {"width": 128, "height": 128, "name": "Cloud CI Staged Native Test"},
        "style": "CI structural study, not a finished painting",
        "subjects": [
            {"id": "vessel", "name": "Ceramic vessel", "kind": "ceramic still life",
             "materials": ["ceramic"], "bounds": [12, 15, 58, 100],
             "brush": {"color": "#B65330", "size": 7, "opacity": 1}},
            {"id": "water", "name": "Water band", "kind": "water reflection",
             "materials": ["water"], "bounds": [72, 67, 54, 52],
             "brush": {"color": "#3266C7", "size": 5, "opacity": 1}},
        ],
        "stages": [
            {"id": "sketch", "phase": "sketch", "goal": "Establish two subject outlines",
             "intents": [
                 {"id": "vesselline", "subject_id": "vessel", "kind": "gesture",
                  "purpose": "Establish ceramic vessel silhouette",
                  "path": [[22, 33], [18, 55], [23, 93], [58, 93], [64, 52], [59, 34]]},
                 {"id": "waterline", "subject_id": "water", "kind": "gesture",
                  "purpose": "Establish a horizontal water horizon",
                  "path": [[76, 81], [121, 83]]},
             ]},
            {"id": "block", "phase": "block_in", "goal": "Build two flat material color zones",
             "intents": [
                 {"id": "vesselfill", "subject_id": "vessel", "kind": "coverage",
                  "purpose": "Fill the broad ceramic vessel face",
                  "polygon": [[25, 37], [58, 37], [58, 87], [25, 87]],
                  "spacing": 11, "angle": 3, "seed": 3, "jitter": 0.05},
                 {"id": "waterfill", "subject_id": "water", "kind": "coverage",
                  "purpose": "Fill a blue reflection water stripe",
                  "polygon": [[76, 92], [120, 92], [120, 110], [76, 110]],
                  "spacing": 8, "angle": 0, "seed": 4, "jitter": 0.08},
             ]},
            {"id": "detail", "phase": "detail", "goal": "Add contrasting material highlights",
             "intents": [
                 {"id": "vesselshine", "subject_id": "vessel", "kind": "accents",
                  "purpose": "Place small ceramic specular glints",
                  "path": [[34, 44], [38, 74]], "count": 4, "length": 8,
                  "brush": {"color": "#F5D9A8", "size": 4}},
                 {"id": "waterglints", "subject_id": "water", "kind": "accents",
                  "purpose": "Add broken water reflections",
                  "path": [[77, 102], [118, 101]], "count": 5, "length": 7,
                  "brush": {"color": "#90C7FF", "size": 3}},
             ]},
        ],
    }


def compile_fixture():
    """Fail closed before touching Krita if fixture exceeds the reviewed budget."""
    first = compile_scene_v4(synthetic_scene(), preview_prefix=PREVIEW_PREFIX)
    steps = first["steps"]
    if len(first["stage_spans"]) != 3 or len(steps) > 110:
        raise RuntimeError("Unexpected staged fixture budget or phase count")
    if not steps or steps[0]["command"] != "canvas.create":
        raise RuntimeError("Staged fixture must create an isolated canvas")
    if any(step["command"] not in ALLOWED_NATIVE for step in steps):
        raise RuntimeError("Fixture compiler emitted a non-allowlisted native command")
    if sum(s["command"] == "draw.stroke" for s in steps) < 8:
        raise RuntimeError("Fixture must exercise multiple native brush strokes")
    if len(first["stage_preview_paths"]) < 3:
        raise RuntimeError("Each stage must have a genuine Krita preview")
    for item in first["stage_spans"]:
        part = steps[item["start"]:item["stop"]]
        if not part or not any(s["command"] == "preview.canvas" for s in part):
            raise RuntimeError("A planned native stage lacks a genuine preview")
    return first


def _save_report(root, value):
    path = root / "cloud-staged-report.json"
    temp = root / "cloud-staged-report.json.tmp"
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def _pixel_change(a, b):
    with Image.open(a) as ai, Image.open(b) as bi:
        aa, bb = ai.convert("RGBA"), bi.convert("RGBA")
        if aa.size != (128, 128) or bb.size != aa.size:
            raise RuntimeError("Unexpected real stage-preview dimensions")
        # Actual native snapshots only; no Python-synthesized image is accepted.
        diff = ImageChops.difference(aa, bb).convert("RGBA")
        return sum(1 for rgba in diff.getdata() if rgba != (0, 0, 0, 0))


def _real_material_pixels(path):
    with Image.open(path) as im:
        if im.size != (128, 128):
            raise RuntimeError("Native staged PNG has incorrect dimensions")
        rgba = im.convert("RGBA")
        counts = {"vessel_red": 0, "water_blue": 0}
        for y in range(128):
            for x in range(128):
                r, g, b, a = rgba.getpixel((x, y))
                if a == 0:
                    continue
                if 12 <= x < 70 and 15 <= y < 115 and r > b + 24 and r > g + 15:
                    counts["vessel_red"] += 1
                if 72 <= x < 126 and 67 <= y < 119 and b > r + 24 and b > g + 12:
                    counts["water_blue"] += 1
        return counts


def execute_staged_fixture(client, output_dir):
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "krita-agent-cloud-staged-native/1",
        "fixture": "tiny-generalist-two-subject-three-phase",
        "status": "cloud_native_unverified",
        "is_simulated": False, "not_artwork_acceptance": True,
        "commands_completed": 0,
    }
    _save_report(root, report)
    try:
        compiled = compile_fixture()
        report.update({
            "scene_sha256": compiled["source_v4_sha256"],
            "compiled_steps_sha256": compiled["native_steps_sha256"],
            "stage_spans": compiled["stage_spans"],
        })
        status = client.request("status")
        if not isinstance(status, dict) or status.get("connected") is not True:
            raise RuntimeError("Real Krita Bridge is unavailable")
        if Path(status.get("output_dir", "")).resolve() != root:
            raise RuntimeError("Bridge scratch root mismatch")
        report["krita_version"] = status.get("krita_version")
        _save_report(root, report)

        # The entire synthetic fixture was reviewed and frozen at source time.
        # We execute all compiled stages without pretending the user approved a
        # real artwork; this is an isolated engine integration test only.
        for idx, step in enumerate(compiled["steps"]):
            result = client.request(step["command"], **step.get("parameters", {}))
            report["commands_completed"] = idx + 1
            report["last_command"] = step["command"]
            if step["command"] == "draw.stroke" and not isinstance(result, dict):
                raise RuntimeError("Native stroke response unexpectedly missing")
            _save_report(root, report)

        previews = []
        for stage in compiled["stage_spans"]:
            expected = [
                s["parameters"]["filename"]
                for s in compiled["steps"][stage["start"]:stage["stop"]]
                if s["command"] == "preview.canvas"
            ]
            path = root / expected[0]
            if not path.is_file():
                raise RuntimeError("Native Krita stage preview was not written: " + expected[0])
            previews.append(path)
        changes = [_pixel_change(a, b) for a, b in zip(previews, previews[1:])]
        if any(value < 4 for value in changes):
            raise RuntimeError("One or more real painting stages contributed no visible pixels")
        report["stage_pixel_changes"] = changes
        report["stage_preview_sha256"] = {
            p.relative_to(root).as_posix(): sha256(p) for p in previews
        }

        # The planned layers must really exist, not just be named in JSON.
        layer_graph = client.request("layer.list")
        if not isinstance(layer_graph, list):
            raise RuntimeError("No actual Krita layer graph")
        required = {r["layer_name"] for r in compiled["stage_layers"]}
        present = {r.get("name") for r in layer_graph}
        if not required.issubset(present):
            raise RuntimeError("Native Krita is missing stage paint layers")
        report["layer_count"] = len(layer_graph)
        report["stage_layer_count"] = len(required)

        client.request("document.save", path="native-staged.kra")
        client.request("document.export", path="native-staged.png")
        kra, initial = root / "native-staged.kra", root / "native-staged.png"
        fresh = root / "native-staged-copy.kra"
        reopened = root / "native-staged-reopened.png"
        if not kra.is_file() or not initial.is_file():
            raise RuntimeError("Staged native Krita files were not saved")
        shutil.copy2(kra, fresh)
        opened = client.request("document.open", path=fresh.name)
        active = client.request("document.info")
        if (Path(opened.get("opened", "")).resolve() != fresh.resolve()
                or Path(active.get("file_path", "")).resolve() != fresh.resolve()):
            raise RuntimeError("Krita did not open/activate the staged fresh KRA")
        client.request("document.export", path=reopened.name)
        with zipfile.ZipFile(kra) as archive:
            if archive.testzip() or not {"maindoc.xml", "mergedimage.png"}.issubset(archive.namelist()):
                raise RuntimeError("Staged native KRA ZIP invalid")
            if not any(b"paintlayer" in archive.read("maindoc.xml").lower() for _ in (0,)):
                raise RuntimeError("Staged KRA has no editable paint layer")
        counts = _real_material_pixels(initial)
        if counts["vessel_red"] < 15 or counts["water_blue"] < 15:
            raise RuntimeError("Staged native pixel output is missing colored materials")
        report["material_pixel_counts"] = counts
        report["export_integrity"] = export_integrity(kra, initial)
        report["reopen_stability"] = reopen_stability(initial, reopened, sha256(kra))
        report["sha256"] = {f.name: sha256(f) for f in (kra, initial, fresh, reopened)}
        if (report["export_integrity"]["status"] != "pass"
                or report["reopen_stability"]["status"] != "pass"):
            raise RuntimeError("Staged KRA failed strict native export/reopen check")
        report["status"] = "cloud_native_verified"
        return report
    except Exception as exc:
        report["failure"] = {"type": type(exc).__name__, "reason": str(exc)}
        raise
    finally:
        _save_report(root, report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--port", type=int, default=47653)
    args = parser.parse_args()
    token = os.getenv("KRITA_AGENT_TOKEN")
    if not token or len(token) < 20:
        parser.error("Authenticated cloud Bridge token missing")
    client = Client(token, port=args.port, timeout=25)
    try:
        result = execute_staged_fixture(client, args.output_dir)
        print(json.dumps({
            "status": result["status"], "stages": len(result["stage_spans"]),
            "stage_pixel_changes": result["stage_pixel_changes"],
            "material_pixel_counts": result["material_pixel_counts"],
        }, sort_keys=True))
        return 0
    except Exception as exc:
        print("Staged real Krita probe FAILED (no acceptance): " +
              type(exc).__name__ + ": " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
