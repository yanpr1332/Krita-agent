"""Round 10 — evidence-bounded visual difference against a REAL Krita KRA.

Metrics cover color/value/edge/regions, not semantic similarity or aesthetics.
KRA integrity is mandatory: a synthetic Pillow PNG cannot pass as an export.
"""
import zipfile
from pathlib import Path

from .protocol import TaskError
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4
from .reference_assets_v10 import _measure
from .reference_plan_v10 import _verify_analysis, _verify_bindings
from .artifact_integrity import export_integrity, reopen_stability, sha256


def _opened_kra_check(kra):
    try:
        with zipfile.ZipFile(kra) as archive:
            if archive.testzip() is not None:
                raise TaskError("KRA native ZIP CRC failed")
            names = set(archive.namelist())
            if not {"maindoc.xml", "mergedimage.png"}.issubset(names):
                raise TaskError("KRA lacks native metadata and merged PNG")
            xml = archive.read("maindoc.xml")
            if len(xml) > 16 * 1024 * 1024 or b"paintlayer" not in xml.lower():
                raise TaskError("KRA has no editable paint-layer evidence")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise TaskError("Not an independently valid Krita KRA") from exc


def _native_measure(image, rect):
    from PIL import Image
    x, y, w, h = rect
    l = int(x); top = int(y)
    r = min(image.width, int(x+w+0.9999)); bot = min(image.height, int(y+h+0.9999))
    if r <= l or bot <= top:
        raise TaskError("Native subject ROI has no pixels")
    cropped = image.crop((l, top, r, bot)).convert("RGBA")
    # White matte is a display-neutral comparison baseline for alpha PNGs;
    # it is not used as source of any Krita painting or acceptance result.
    white = Image.new("RGB", cropped.size, (255, 255, 255))
    white.paste(cropped.convert("RGB"), mask=cropped.getchannel("A"))
    return _measure(white)


def compare_native_repaint(scene, analysis, bindings, kra_path, png_path,
                           reopened_png_path=None, *, compiled_sha256=None):
    """Strict KRA+PNG proof plus read-only descriptive reference comparison."""
    source = validate_scene_v4(scene)
    refs = _verify_analysis(analysis)
    assigned = _verify_bindings(source, refs, bindings)
    if compiled_sha256 is not None:
        from .scene_v4 import compile_scene_v4
        digest_native = compile_scene_v4(source)["native_steps_sha256"]
        if digest_native != compiled_sha256:
            raise TaskError("Native plan digest differs from approved reference scene")
    kra = Path(kra_path)
    png = Path(png_path)
    if not kra.is_file() or not png.is_file() or kra.is_symlink() or png.is_symlink():
        raise TaskError("Real native KRA and PNG paths are required")
    if not 100 <= kra.stat().st_size <= 64 * 1024 * 1024:
        raise TaskError("KRA is outside read-only report budget")
    _opened_kra_check(kra)
    exported = export_integrity(kra, png)
    if exported["status"] != "pass":
        raise TaskError("Krita embedded image/export integrity failed")
    reopened = None
    if reopened_png_path is not None:
        fresh = Path(reopened_png_path)
        if not fresh.is_file() or fresh.is_symlink():
            raise TaskError("Fresh reopened Krita PNG missing")
        reopened = reopen_stability(png, fresh, sha256(kra))
        if reopened["status"] != "pass":
            raise TaskError("KRA reopened output not identical to initial PNG")

    from PIL import Image
    by_id = {s["id"]: s for s in source["subjects"]}
    with Image.open(png) as native:
        if native.size != (source["document"]["width"], source["document"]["height"]):
            raise TaskError("Krita native PNG size mismatches approved scene")
        rgba = native.convert("RGBA")
        alpha = rgba.getchannel("A")
        nonempty = sum(1 for v in (
            alpha.get_flattened_data() if hasattr(alpha, "get_flattened_data") else alpha.getdata()
        ) if v > 0)
        if nonempty <= 0:
            raise TaskError("Krita exported canvas is empty")
        comparisons = []
        for b in assigned:
            measured = _native_measure(native, by_id[b["subject_id"]]["bounds"])
            ref = b["measurements"]
            comparisons.append({
                "subject_id": b["subject_id"], "role": b["role"],
                "source_id": b["source_id"], "source_sha256": b["source_sha256"],
                "region_id": b["region_id"],
                "mean_rgb_difference": [
                    round(abs(a - q), 3) for a, q in zip(
                        measured["mean_rgb"], ref["mean_rgb"])
                ],
                "luminance_hist_l1": round(sum(abs(a - q) for a, q in zip(
                    measured["value_fractions"], ref["value_fractions"])), 4),
                "edge_density_proxy_difference": round(
                    abs(measured["edge_density_proxy"] - ref["edge_density_proxy"]), 4),
                "native_roi_measurements": measured,
                "reference_roi_measurements": ref,
                "metric_status": "descriptive_only_not_aesthetic_score",
            })
    return {
        "schema": "krita-agent-native-reference-comparison/1",
        "status": "native_evidence_checked",
        "scene_sha256": digest(source), "analysis_sha256": analysis["analysis_sha256"],
        "compiled_native_steps_sha256": compiled_sha256,
        "kra_sha256": sha256(kra), "png_sha256": sha256(png),
        "reopened_png_sha256": sha256(reopened_png_path) if reopened else None,
        "kra_export_integrity": exported,
        "native_reopen_stability": reopened,
        "nontransparent_pixels": nonempty,
        "regions": comparisons,
        "claim_limits": {
            "native_command_provenance": "requires_independent_bridge_execution_log",
            "semantic_similarity": "not_evaluated",
            "human_review": "required", "artwork_accepted": False,
        },
    }
