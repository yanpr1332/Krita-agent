"""Round 10 reference/technique tests: deterministic pixel evidence and fail-closed consent.

Pillow fixtures are *source references for tests*, never accepted Krita output.
Real painting and KRA proof run separately in the cloud-native Tier-2 job.
"""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from krita_agent.protocol import TaskError
from krita_agent.reference_assets_v10 import (
    analyze_references, validate_reference_manifest,
)
from krita_agent.reference_plan_v10 import (
    propose_reference_repaint, approve_reference_repaint,
)
from krita_agent.reference_vision_v10 import annotate_references
from krita_agent.reference_compare_v10 import compare_native_repaint
from krita_agent.technique_library_v10 import (
    validate_technique, save_technique, load_technique, list_techniques,
    propose_technique_application, approve_technique_application,
)


def _fixture(tmp_path, external=False):
    from scripts.cloud_staged_probe import synthetic_scene
    image = Image.new("RGB", (128, 128), (238, 232, 217))
    draw = ImageDraw.Draw(image)
    draw.rectangle([12, 12, 69, 115], fill=(190, 80, 49))
    draw.rectangle([72, 67, 127, 118], fill=(40, 105, 208))
    image.save(tmp_path / "synthetic.png")
    manifest = {
        "schema": "krita-agent-references/1",
        "sources": [
            {"id": "painted", "file": "synthetic.png",
             "rights": {"basis": "owned", "permission_confirmed": True,
                        "source_note": "Original synthetic CI reference",
                        "external_upload_permitted": external},
             "roles": ["palette", "material", "composition"],
             "regions": [
                 {"id": "vessel", "rect": [0.1, 0.1, 0.35, 0.7],
                  "subject_id": "vessel", "material": "ceramic"},
                 {"id": "water", "rect": [0.59, 0.53, 0.35, 0.34],
                  "subject_id": "water", "material": "water"},
             ]},
        ],
    }
    bindings = [
        {"subject_id": "vessel", "source_id": "painted", "region_id": "vessel",
         "role": "palette"},
        {"subject_id": "water", "source_id": "painted", "region_id": "water",
         "role": "material"},
    ]
    return synthetic_scene(), manifest, bindings


def _technique(analysis, status="hypothesis"):
    return {
        "schema": "krita-agent-technique/1",
        "id": "water_stripes", "version": 1, "title": "Water reflection strokes",
        "materials": ["water"], "subjects": ["water"],
        "phases": ["block_in"], "intent_kinds": ["coverage"],
        "render": {"technique": "ripples", "flow": "linear",
                   "placement": "blue_noise", "palette": ["#4477CC"]},
        "brush": {"size": 5, "opacity": .78},
        "provenance": {
            "source_id": "painted",
            "source_sha256": analysis["sources"][0]["sha256"],
            "rights_basis": "owned",
            "source_note": "CI original synthetic paint sample",
        },
        "status": status, "evidence": [],
        "limitations": "A color and direction hypothesis; requires real Krita visual acceptance",
        "builds": [],
    }


def test_reference_pixels_are_measured_and_digest_bound(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    a = analyze_references(tmp_path, manifest)
    b = analyze_references(tmp_path, manifest)
    assert a == b
    assert len(a["sources"][0]["sha256"]) == 64
    assert a["sources"][0]["rights"]["permission_confirmed"]
    assert a["sources"][0]["regions"][0]["measurements"]["dominant_palette"]
    assert a["sources"][0]["global_measurements"]["semantic_objects_detected"] is False
    assert a["limits"]["model_api"] == "not_called"
    assert "synthetic.png" not in json.dumps(a)  # no private input path leaked


def test_reference_requires_actual_authorized_nontraversing_source(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    bad = copy.deepcopy(manifest)
    bad["sources"][0]["rights"]["permission_confirmed"] = False
    with pytest.raises(TaskError, match="confirmation"):
        analyze_references(tmp_path, bad)
    bad = copy.deepcopy(manifest)
    bad["sources"][0]["file"] = "../synthetic.png"
    with pytest.raises(TaskError, match="single local"):
        analyze_references(tmp_path, bad)
    bad = copy.deepcopy(manifest)
    bad["sources"][0]["file"] = "hidden.png"
    (tmp_path / "hidden.png").symlink_to(tmp_path / "synthetic.png")
    with pytest.raises(TaskError, match="links/unsafe"):
        analyze_references(tmp_path, bad)


def test_reference_rejects_ambiguous_roles_and_invalid_roi(tmp_path):
    _, manifest, _ = _fixture(tmp_path)
    bad = copy.deepcopy(manifest)
    bad["sources"].append(dict(bad["sources"][0], id="second"))
    with pytest.raises(TaskError, match="Ambiguous"):
        validate_reference_manifest(bad)
    bad = copy.deepcopy(manifest)
    bad["sources"][0]["regions"][0]["rect"] = [.93, 0, .2, .3]
    with pytest.raises(TaskError, match="outside"):
        validate_reference_manifest(bad)


def test_palette_repaint_is_a_new_native_brush_plan_not_a_raster_paste(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    analysis = analyze_references(tmp_path, manifest)
    before = copy.deepcopy(scene)
    p = propose_reference_repaint(scene, analysis, bindings, mode="palette_repaint")
    assert p["approval"] == "required" and p["side_effects"] == "none"
    assert p["source_scene_sha256"] and p["reference_analysis_sha256"]
    assert p["scene"] != scene
    assert scene == before
    assert any("new_color" in row for row in p["changes"])
    with pytest.raises(TaskError, match="confirmation"):
        approve_reference_repaint(scene, manifest, tmp_path, p)
    approved = approve_reference_repaint(scene, manifest, tmp_path, p, confirm=True)
    assert approved == p["scene"]
    assert all("image" not in x for x in p["native_draw"].split("_"))


def test_material_repaint_retains_user_chosen_render_method(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    scene["stages"][1]["intents"][0]["render"] = {
        "technique": "planes", "palette": ["#EEAA55"]}
    analysis = analyze_references(tmp_path, manifest)
    p = propose_reference_repaint(scene, analysis, bindings, mode="material_study")
    render = p["scene"]["stages"][1]["intents"][0]["render"]
    assert render["technique"] == "planes"
    assert len(render["palette"]) >= 1


def test_cannot_do_pixel_inferred_anatomy_without_user_authored_plan(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    analysis = analyze_references(tmp_path, manifest)
    b = [{"subject_id": "vessel", "source_id": "painted", "role": "composition"}]
    with pytest.raises(TaskError, match="explicit candidate"):
        propose_reference_repaint(scene, analysis, b, mode="structure_study")
    cand = copy.deepcopy(scene)
    cand["style"] = "Reviewed composition study"
    p = propose_reference_repaint(scene, analysis, b, mode="structure_study",
                                  candidate_scene=cand)
    assert p["changes"][0]["geometry_claim"] == "user_or_model_authored_not_pixel_inferred"
    assert approve_reference_repaint(scene, manifest, tmp_path, p, confirm=True)["style"] == (
        "Reviewed composition study")


def test_image_change_between_analysis_and_approval_fails_closed(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    analysis = analyze_references(tmp_path, manifest)
    p = propose_reference_repaint(scene, analysis, bindings)
    img = Image.new("RGB", (128, 128), "#000000")
    img.save(tmp_path / "synthetic.png")
    with pytest.raises(TaskError, match="pixels, consent, or ROIs changed"):
        approve_reference_repaint(scene, manifest, tmp_path, p, confirm=True)


def test_untrusted_analysis_and_duplicate_bindings_are_rejected(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    a = analyze_references(tmp_path, manifest)
    a["sources"][0]["global_measurements"]["mean_rgb"][0] = 100
    with pytest.raises(TaskError, match="modified"):
        propose_reference_repaint(scene, a, bindings)
    a = analyze_references(tmp_path, manifest)
    with pytest.raises(TaskError, match="Ambiguous second"):
        propose_reference_repaint(scene, a, [bindings[0], bindings[0]])


def test_technique_versions_are_immutable_and_source_bound(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    a = analyze_references(tmp_path, manifest)
    p = _technique(a)
    record = save_technique(tmp_path / "library", p)
    assert record["status"] == "hypothesis"
    assert load_technique(tmp_path / "library", "water_stripes", 1) == validate_technique(p)
    assert len(list_techniques(tmp_path / "library")) == 1
    with pytest.raises(TaskError, match="cannot be overwritten"):
        save_technique(tmp_path / "library", p)
    tampered = copy.deepcopy(p)
    tampered["status"] = "human_reviewed"
    with pytest.raises(TaskError, match="must cite actual evidence"):
        validate_technique(tampered)


def test_technique_application_remains_a_manual_candidate(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    a = analyze_references(tmp_path, manifest)
    p = _technique(a)
    old = copy.deepcopy(scene)
    proposed = propose_technique_application(scene, p, "water", "waterfill")
    assert scene == old
    assert proposed["approval"] == "required"
    with pytest.raises(TaskError, match="explicit approval"):
        approve_technique_application(scene, p, proposed)
    approved = approve_technique_application(scene, p, proposed, confirm=True)
    assert approved["stages"][1]["intents"][1]["render"]["technique"] == "ripples"
    edited = copy.deepcopy(proposed)
    edited["scene"]["stages"][1]["intents"][1]["render"]["seed"] = 12
    with pytest.raises(TaskError, match="changed since review"):
        approve_technique_application(scene, p, edited, confirm=True)


def test_technique_restricts_build_and_material_compatibility(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    p = _technique(analyze_references(tmp_path, manifest))
    p["builds"] = ["Krita 5.3.4.1 Linux"]
    with pytest.raises(TaskError, match="not characterized"):
        propose_technique_application(scene, p, "water", "waterfill", build="Krita 6")
    with pytest.raises(TaskError, match="material"):
        propose_technique_application(scene, p, "vessel", "vesselfill",
                                      build="Krita 5.3.4.1 Linux")


class FakeProvider:
    model = "fake-visually-aware"
    def __init__(self):
        self.calls = 0
    def complete_json(self, system, prompt, image_paths=()):
        self.calls += 1
        assert len(image_paths) == 1 and Path(image_paths[0]).is_file()
        return {"schema": "krita-agent-reference-annotations/1",
                "sources": [{"source_id": "painted", "subjects": [
                    {"id": "vessel", "kind": "ceramic", "bounds": [.1,.1,.4,.8],
                     "materials": ["ceramic"], "confidence": .8}],
                    "visual_notes": "Red object and a blue band are visible"}]}


def test_visual_model_never_called_without_both_levels_of_permission(tmp_path):
    scene, manifest, _ = _fixture(tmp_path)
    provider = FakeProvider()
    with pytest.raises(TaskError, match="Opt-in external"):
        annotate_references(tmp_path, manifest, provider)
    with pytest.raises(TaskError, match="Each reference"):
        annotate_references(tmp_path, manifest, provider, allow_external_upload=True)
    assert provider.calls == 0


def test_authorized_opt_in_model_is_untrusted_annotator_only(tmp_path):
    scene, manifest, _ = _fixture(tmp_path, external=True)
    provider = FakeProvider()
    out = annotate_references(tmp_path, manifest, provider, allow_external_upload=True)
    assert provider.calls == 1
    assert out["model_api"] == "explicitly_called"
    assert out["geometry_requires_manual_scene_mapping"]
    assert out["sources"][0]["subjects"][0]["confidence_uncalibrated"] == .8
    assert not out["artwork_accepted"]


def test_pillow_generated_png_does_not_prove_native_kra_integrity(tmp_path):
    scene, manifest, bindings = _fixture(tmp_path)
    a = analyze_references(tmp_path, manifest)
    kra = tmp_path / "fake.kra"
    kra.write_bytes(b"not a KRA, even if a picture looks plausible"*10)
    with pytest.raises(TaskError, match="Not an independently valid Krita KRA"):
        compare_native_repaint(scene, a, bindings, kra, tmp_path / "synthetic.png")


def test_reference_cli_is_registered_without_auth_or_network():
    from krita_agent.cli import parser_build
    parser = parser_build()
    args = parser.parse_args(["reference", "analyze", "--root", ".",
                              "--manifest", "manifest.json"])
    assert args.command == "reference" and args.reference_action == "analyze"
    args = parser.parse_args(["reference", "technique-list", "--library", "."])
    assert args.reference_action == "technique-list"


def test_cloud_fixture_separates_approved_brush_hash_from_preview_execution_hash(tmp_path):
    from scripts.cloud_reference_probe import prepare
    from krita_agent.scene_v4 import compile_scene_v4
    fixture = prepare(tmp_path, "5.3.4.1 (git bd6e8d0)")
    core = compile_scene_v4(fixture["scene"])["native_steps_sha256"]
    assert fixture["approved_native_steps_sha256"] == core
    assert fixture["compiled"]["native_steps_sha256"] != core
    assert len(fixture["compiled"]["stage_preview_paths"]) >= 3
    assert all(step["command"] not in ("image.import", "reference.import", "pixel.fill")
               for step in fixture["compiled"]["steps"])


def test_technique_extraction_uses_declared_material_and_real_roi_edges(tmp_path):
    from krita_agent.technique_extraction_v10 import extract_technique_hypothesis
    scene, manifest, bindings = _fixture(tmp_path)
    out = extract_technique_hypothesis(
        tmp_path, manifest, source_id="painted", region_id="water",
        profile_id="learned_water", material="water", phase="block_in",
    )
    again = extract_technique_hypothesis(
        tmp_path, manifest, source_id="painted", region_id="water",
        profile_id="learned_water", material="water", phase="block_in",
    )
    assert out == again
    assert out["model_api"] == "not_called"
    assert out["native_effects"] == "none"
    assert out["material_label_source"] == "human_authored_region"
    assert out["image_orientation"]["status"] in (
        "image_edge_tangent_proxy_not_brush_detection",
        "indeterminate_no_oriented_edges",
    )
    profile = out["profile"]
    assert validate_technique(profile) == profile
    assert profile["status"] == "hypothesis"
    assert profile["render"]["technique"] == "ripples"
    proposed = propose_technique_application(scene, profile, "water", "waterfill")
    assert len(proposed["candidate_sha256"]) == 64
    assert approve_technique_application(
        scene, profile, proposed, confirm=True,
    )["stages"][1]["intents"][1]["render"]["technique"] == "ripples"


def test_technique_extraction_refuses_mismatched_material_and_missing_roi(tmp_path):
    from krita_agent.technique_extraction_v10 import extract_technique_hypothesis
    _, manifest, _ = _fixture(tmp_path)
    with pytest.raises(TaskError, match="contradicts manually labeled"):
        extract_technique_hypothesis(
            tmp_path, manifest, source_id="painted", region_id="water",
            profile_id="bad_material", material="fabric")
    with pytest.raises(TaskError, match="explicit analyzed reference ROI"):
        extract_technique_hypothesis(
            tmp_path, manifest, source_id="painted", region_id="unknown",
            profile_id="no_roi", material="water")


def test_technique_extraction_requires_material_or_technique_right(tmp_path):
    from krita_agent.technique_extraction_v10 import extract_technique_hypothesis
    _, manifest, _ = _fixture(tmp_path)
    manifest["sources"][0]["roles"] = ["composition"]
    with pytest.raises(TaskError, match="material/technique rights"):
        extract_technique_hypothesis(
            tmp_path, manifest, source_id="painted", region_id="water",
            profile_id="not_authorized", material="water")


def test_technique_extract_cli_requires_explicit_source_and_roi():
    from krita_agent.cli import parser_build
    parser = parser_build()
    args = parser.parse_args([
        "reference", "technique-extract", "--root", "./authorized",
        "--manifest", "refs.json", "--source-id", "ref",
        "--region-id", "water", "--id", "learned_water",
        "--phase", "block_in", "--profile-only"])
    assert args.reference_action == "technique-extract"
    assert args.profile_only and args.source_id == "ref"


def test_technique_extraction_detects_authored_horizontal_reference_edges(tmp_path):
    from krita_agent.technique_extraction_v10 import extract_technique_hypothesis
    scene, manifest, _ = _fixture(tmp_path)
    with Image.open(tmp_path / "synthetic.png") as original:
        image = original.convert("RGB")
    drawer = ImageDraw.Draw(image)
    # Deliberately visible source-image texture, NOT a Krita output image.
    for y in (77, 86, 95, 104):
        drawer.line([(77, y), (118, y)], fill=(220, 229, 247), width=3)
    image.save(tmp_path / "synthetic.png")
    hypothesis = extract_technique_hypothesis(
        tmp_path, manifest, source_id="painted", region_id="water",
        profile_id="horizontal_reference", phase="block_in", material="water")
    orientation = hypothesis["image_orientation"]
    assert orientation["status"] == "image_edge_tangent_proxy_not_brush_detection"
    assert orientation["samples"] > 0
    assert orientation["angle"] == 0.0
    assert orientation["anisotropy"] > .5
    assert hypothesis["profile"]["status"] == "hypothesis"
    assert hypothesis["profile"]["render"]["technique"] == "ripples"
    assert hypothesis["profile"]["render"]["angle"] == 0.0
