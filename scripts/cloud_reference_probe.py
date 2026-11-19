"""Real cloud Krita reference study: no pasted reference and no paid model API.

Pre-authorized synthetic input -> real-pixel offline analysis -> explicitly
accepted ScenePlan v4 -> bounded technique profile -> REAL native Krita
strokes, editable KRA, PNG, fresh reopen, ROI comparison. Not art approval.
"""
import json
import os
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from krita_agent.client import Client
from krita_agent.artifact_integrity import sha256
from krita_agent.scene_v4 import compile_scene_v4
from krita_agent.reference_assets_v10 import analyze_references
from krita_agent.reference_plan_v10 import (
    propose_reference_repaint, approve_reference_repaint,
)
from krita_agent.reference_compare_v10 import compare_native_repaint
from krita_agent.technique_library_v10 import (
    propose_technique_application, approve_technique_application,
)
from cloud_staged_probe import synthetic_scene

ROOT_MODE = "synthetic_cloud_reference_never_user_artwork"
ALLOWED = frozenset(("canvas.create", "layer.create", "brush.configure",
                     "draw.stroke", "preview.canvas"))


def prepare(root, build):
    """One deterministic synthetic reference; explicitly authorized by fixture."""
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = root / "round10-synthetic-reference.png"
    # Synthetic test pixels are allowed ONLY as REFERENCE. Never use this
    # Pillow-generated raster as output or to fake the Krita native drawing.
    picture = Image.new("RGB", (128, 128), (238, 230, 219))
    paint = ImageDraw.Draw(picture)
    paint.rectangle([12, 12, 69, 115], fill=(183, 76, 45))
    paint.rectangle([72, 67, 126, 118], fill=(47, 99, 194))
    picture.save(source)

    manifest = {
        "schema": "krita-agent-references/1",
        "sources": [{
            "id": "ci_reference",
            "file": source.name,
            "rights": {
                "basis": "owned", "permission_confirmed": True,
                "source_note": "Original generated synthetic CI source only",
                "external_upload_permitted": False,
            },
            "roles": ["palette", "material", "composition"],
            "regions": [
                {"id": "ceramic_color", "subject_id": "vessel", "material": "ceramic",
                 "rect": [0.1, 0.12, 0.35, 0.72]},
                {"id": "water_color", "subject_id": "water", "material": "water",
                 "rect": [0.59, 0.53, 0.34, 0.35]},
            ],
        }],
    }
    bindings = [
        {"subject_id": "vessel", "source_id": "ci_reference",
         "region_id": "ceramic_color", "role": "palette"},
        {"subject_id": "water", "source_id": "ci_reference",
         "region_id": "water_color", "role": "material"},
    ]
    evidence = analyze_references(root, manifest)
    scene = synthetic_scene()
    proposed = propose_reference_repaint(
        scene, evidence, bindings, mode="material_study",
        rationale="Test reproducible authorized native-only color transfer")
    accepted = approve_reference_repaint(
        scene, manifest, root, proposed, confirm=True)
    profile = {
        "schema": "krita-agent-technique/1",
        "id": "ci_water_ripple", "version": 1,
        "title": "Cloud CI horizontal water glints",
        "materials": ["water"], "subjects": ["water"],
        "phases": ["block_in"], "intent_kinds": ["coverage"],
        "render": {
            "technique": "ripples", "layers": 1, "placement": "staggered",
            "flow": "linear", "spacing": 12, "length": 15, "curvature": .08,
            "palette": ["#326DBE", "#6095DE"],
        },
        "brush": {"size": 4.0, "opacity": .9},
        "provenance": {
            "source_id": "ci_reference",
            "source_sha256": evidence["sources"][0]["sha256"],
            "rights_basis": "owned",
            "source_note": "Original generated CI reference",
        },
        "status": "hypothesis", "evidence": [],
        "limitations": "CI structure fixture; no human or material quality acceptance",
        "builds": [build],
    }
    suggested = propose_technique_application(
        accepted, profile, "water", "waterfill", build=build)
    final = approve_technique_application(
        accepted, profile, suggested, confirm=True)
    approved_core = compile_scene_v4(final)
    if approved_core["native_steps_sha256"] != suggested["native_steps_sha256"]:
        raise RuntimeError("Approved core native brush steps differ from proposal")
    compiled = compile_scene_v4(final, preview_prefix="r5-runs/"+"e"*32)
    if (len(compiled["steps"]) > 150 or
            not all(item["command"] in ALLOWED for item in compiled["steps"])):
        raise RuntimeError("Round 10 preapproved test exceeded native brush-only budget")
    return {
        "manifest": manifest, "bindings": bindings, "evidence": evidence,
        "proposal": proposed, "technique_proposal": suggested,
        "scene": final, "compiled": compiled,
    }


def execute(client, output_dir):
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    report_path = root / "cloud-reference-report.json"
    report = {
        "schema": "krita-agent-cloud-reference-native/1", "status": "unverified",
        "fixture": ROOT_MODE, "is_simulated": False, "native_steps_complete": 0,
        "artwork_accepted": False,
    }

    def save_report():
        tmp = root / "cloud-reference-report.tmp"
        tmp.write_text(json.dumps(report, sort_keys=True, indent=2),
                       encoding="utf-8")
        tmp.replace(report_path)

    save_report()
    try:
        status = client.request("status")
        if status.get("connected") is not True or Path(
                status.get("output_dir", "")).resolve() != root:
            raise RuntimeError("Real Krita Bridge unavailable/wrong sandbox")
        fixture = prepare(root, status["krita_version"])
        compiled = fixture["compiled"]
        report.update({
            "krita_version": status["krita_version"],
            "reference_sha256": fixture["evidence"]["sources"][0]["sha256"],
            "reference_analysis_sha256": fixture["evidence"]["analysis_sha256"],
            "source_scene_sha256": fixture["proposal"]["source_scene_sha256"],
            "native_steps_sha256": compiled["native_steps_sha256"],
            "approved_technique_sha256": fixture["technique_proposal"]["technique_sha256"],
            "stage_count": len(compiled["stage_spans"]),
            "stage_guide_count": compiled["structure_diagnostics"]["rendered_skeleton_chains"],
        })
        save_report()

        # Native effects are never replayed if a command reply is uncertain.
        for step in compiled["steps"]:
            client.request(step["command"], **step["parameters"])
            report["native_steps_complete"] += 1
            save_report()

        paths = compiled["stage_preview_paths"]
        if len(paths) < 3 or any(not (root / p).is_file() for p in paths):
            raise RuntimeError("Krita did not create all real stage previews")
        from PIL import ImageChops
        actual_stages = []
        for span in compiled["stage_spans"]:
            preview = next(s["parameters"]["filename"] for s in
                           compiled["steps"][span["start"]:span["stop"]]
                           if s["command"] == "preview.canvas")
            actual_stages.append(root / preview)
        stage_differences = []
        for before, after in zip(actual_stages, actual_stages[1:]):
            with Image.open(before) as a, Image.open(after) as b:
                diff = ImageChops.difference(a.convert("RGBA"), b.convert("RGBA"))
                rgb = diff.get_flattened_data() if hasattr(diff, "get_flattened_data") else diff.getdata()
                stage_differences.append(sum(1 for color in rgb if color != (0,0,0,0)))
        if not all(n > 0 for n in stage_differences):
            raise RuntimeError("A Round 10 native painting stage failed to contribute")

        layers = client.request("layer.list")
        expected = {x["layer_name"] for x in compiled["stage_layers"]}
        if not isinstance(layers, list) or not expected.issubset(
                {row["name"] for row in layers}):
            raise RuntimeError("Native paint layers do not match approved plan")
        report.update({
            "stage_png_count": len(paths), "stage_pixel_changes": stage_differences,
            "native_layer_count": len(layers), "expected_paint_layers": len(expected),
        })

        client.request("document.save", path="native-reference-study.kra")
        client.request("document.export", path="native-reference-study.png")
        kra = root / "native-reference-study.kra"
        png = root / "native-reference-study.png"
        copied = root / "native-reference-copy.kra"
        reopened = root / "native-reference-reopened.png"
        if not kra.is_file() or not png.is_file():
            raise RuntimeError("No genuine Krita KRA/PNG output")
        shutil.copy2(kra, copied)
        opened = client.request("document.open", path=copied.name)
        active = client.request("document.info")
        if (Path(opened.get("opened", "")).resolve() != copied.resolve()
                or Path(active.get("file_path", "")).resolve() != copied.resolve()):
            raise RuntimeError("Krita did not re-open copied native KRA")
        client.request("document.export", path=reopened.name)

        comparison = compare_native_repaint(
            fixture["scene"], fixture["evidence"], fixture["bindings"],
            kra, png, reopened, compiled_sha256=compiled["native_steps_sha256"])
        report["native_reference_comparison"] = comparison
        report["source_approval"] = {
            "rights": "owned and explicitly confirmed", "external_upload": False,
            "reference_used_as_native_paste": False,
            "technique_status": "hypothesis",
        }
        report["sha256"] = {p.name: sha256(p) for p in
                            (kra, png, copied, reopened)}
        report["status"] = "cloud_native_verified_reference_pipeline"
        return report
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        save_report()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: cloud_reference_probe.py OUTPUT_DIRECTORY")
    root = Path(sys.argv[1]).resolve()
    token = os.getenv("KRITA_AGENT_TOKEN")
    port = int(os.getenv("KRITA_AGENT_PORT", "47653"))
    if not token or len(token) < 20:
        raise SystemExit("Missing ephemeral cloud Bridge token")
    try:
        output = execute(Client(token, port=port, timeout=25), root)
        print(json.dumps({
            "status": output["status"],
            "native_steps": output["native_steps_complete"],
            "stages": output["stage_count"],
            "stage_pixel_changes": output["stage_pixel_changes"],
            "reference_roi_metrics": len(output["native_reference_comparison"]["regions"]),
            "strict_reopen": True, "external_upload": False,
        }, sort_keys=True))
    except Exception as exc:
        print("Native reference study FAILED, no acceptance: " +
              type(exc).__name__ + ": " + str(exc))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
