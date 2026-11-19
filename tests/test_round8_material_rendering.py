"""Round 8 material grammar, readable pixel diagnostics and compat OFFLINE tests.

Generated Pillow images are synthetic QC fixtures, NOT artwork or native Krita.
Only installed Krita + independent reviewers can accept full illustrations.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from PIL import Image

from krita_agent.creative_workflow import CreativeWorkflow
from krita_agent.material_rendering import (
    MAX_MARKS, TECHNIQUES, _safe_point, expand_render_intent, validate_render,
)
from krita_agent.protocol import TaskError
from krita_agent.render_quality_v1 import (
    archived_stage_diagnostics, compare_actual_pngs, compare_actual_region,
    plan_mark_diagnostics,
)
from krita_agent.scene_v3 import digest
from krita_agent.scene_v4 import compile_scene_v4, lower_scene_v4, validate_scene_v4

ROOT = Path(__file__).resolve().parents[1]
R7 = ROOT / "examples/round7-generalist-scene.json"
R8 = ROOT / "examples/round8-material-study.json"


def old_scene():
    return json.loads(R7.read_text(encoding="utf-8"))


def new_scene():
    return json.loads(R8.read_text(encoding="utf-8"))


def test_legacy_round7_scene_remains_identical_and_unmodified():
    base = old_scene()
    validated = validate_scene_v4(deepcopy(base))
    assert digest(validated) == digest(validate_scene_v4(validated))
    assert all("render" not in x for stage in validated["stages"]
               for x in stage["intents"])
    lower, _ = lower_scene_v4(base)
    assert digest(lower) == digest(lower_scene_v4(validated)[0])
    assert compile_scene_v4(base)["native_steps_sha256"] == (
        compile_scene_v4(validated)["native_steps_sha256"])


def test_opt_in_materials_mix_independently_of_subject_labels():
    candidate = new_scene()
    normalized = validate_scene_v4(candidate)
    assert normalized == validate_scene_v4(normalized)
    modes = [x["render"]["technique"]
             for stage in normalized["stages"] for x in stage["intents"]
             if "render" in x]
    assert modes == ["wash", "planes", "contour", "strands", "specular", "facets"]
    lowered, rows = lower_scene_v4(candidate)
    assert len(rows) == 9
    assert lowered["schema"] == "krita-agent-scene/3"
    assert all(x["kind"] == "stroke" for obj in lowered["objects"]
               for x in obj["elements"])
    assert len({x["brush"]["color"] for obj in lowered["objects"]
                for x in obj["elements"] if "brush" in x}) >= 6
    compiled = compile_scene_v4(candidate, preview_prefix="r5-runs/"+"b"*32)
    assert compiled["requires_native_approval"]
    assert compiled["source_v4_sha256"] == digest(normalized)
    assert compiled["stage_spans"][-1]["stop"] == len(compiled["steps"])
    assert not any(step["command"] in ("image.import", "reference.import")
                   for step in compiled["steps"])
    assert compiled["native_steps_sha256"] == (
        compile_scene_v4(deepcopy(candidate),
                         preview_prefix="r5-runs/"+"b"*32)["native_steps_sha256"])


@pytest.mark.parametrize("technique", sorted(TECHNIQUES))
def test_each_material_technique_produces_bounded_native_brush_marks(technique):
    scene = old_scene()
    i = scene["stages"][1]["intents"][2]
    i["render"] = {
        "technique": technique, "spacing": 20, "length": 29,
        "curvature": .18, "layers": 1, "edge_mode": "stitch",
        "palette": ["#567890", "#BAC3CC"], "seed": 19,
    }
    normalized = validate_scene_v4(scene)
    lowered, _ = lower_scene_v4(normalized)
    target = next(o for o in lowered["objects"] if o["id"] == "s01_cup")
    assert 1 <= len(target["elements"]) <= MAX_MARKS
    for element in target["elements"]:
        assert element["kind"] == "stroke"
        assert 2 <= len(element["points"]) <= 256
        assert element["brush"]["size"] > 0
        assert element["brush"]["opacity"] > 0
        assert element["brush"]["color"] in ("#567890", "#BAC3CC")
        assert all(0 <= p["pressure"] <= 1 for p in element["points"])


@pytest.mark.parametrize("patch,expected", [
    ({"technique": "untrusted_python"}, "Unknown material technique"),
    ({"technique": "wash", "shell": "rm"}, "Unsupported material recipe fields"),
    ({"technique": "wash", "palette": ["not_hex"]}, "palette colors"),
    ({"technique": "wash", "flow": "teleport"}, "surface flow field"),
    ({"technique": "wash", "layers": 99}, "material layers"),
    ({"technique": "wash", "spacing": 0}, "material spacing"),
    ({"technique": "wash", "edge_inset": -10}, "edge inset"),
    ({"technique": "wash", "angle": 999}, "material angle"),
    ({"technique": "wash", "placement": "regular_grid_forever"}, "material placement"),
    ({"technique": "wash", "light_strength": 3}, "material light strength"),
])
def test_material_recipe_strictly_rejects_untrusted_parameters(patch, expected):
    with pytest.raises(TaskError, match=expected):
        validate_render(patch, "coverage")


def test_excessive_material_grid_fails_closed_without_native_execution():
    scene = old_scene()
    intent = scene["stages"][1]["intents"][0]
    intent["render"] = {
        "technique": "wash", "spacing": 3, "layers": 3,
        "palette": ["#112233"],
    }
    with pytest.raises(TaskError, match="candidate budget"):
        compile_scene_v4(scene)


def test_compiled_material_centerlines_inside_declared_polygon():
    scene = old_scene()
    source = scene["stages"][1]["intents"][2]
    source["render"] = {
        "technique": "contour", "spacing": 17, "length": 38,
        "layers": 1, "edge_mode": "stitch", "edge_inset": 1,
    }
    normalized = validate_scene_v4(scene)
    subject = next(x for x in normalized["subjects"] if x["id"] == "cup")
    selected = {"brush": {"color": "#665544"}}
    element = normalized["stages"][1]["intents"][2]
    marks = expand_render_intent(element, selected, subject, normalized["document"])
    poly = element["polygon"]
    for mark in marks:
        for p in mark["points"]:
            assert _safe_point((p["x"], p["y"]), poly, 0)


def test_material_plan_diagnostics_warns_without_approving_art():
    scene, _ = lower_scene_v4(new_scene())
    report = plan_mark_diagnostics(scene)
    assert report["artwork_accepted"] is False
    assert report["actual_pixels_inspected"] is False
    assert len(report["objects"]) == 9
    assert all(0 <= item["repeated_shape_fraction"] <= 1 for item in report["objects"])


def test_actual_png_stage_delta_is_strict_and_not_visual_acceptance(tmp_path):
    before, after = tmp_path/"before.png", tmp_path/"after.png"
    Image.new("RGBA", (12, 12), (200, 30, 40, 255)).save(before)
    im = Image.new("RGBA", (12, 12), (200, 30, 40, 255))
    im.putpixel((1, 2), (202, 30, 40, 255))
    im.putpixel((4, 6), (20, 40, 50, 80))
    im.save(after)
    result = compare_actual_pngs(before, after)
    assert result["changed_rgba_pixels"] == 2
    assert result["changed_alpha_pixels"] == 1
    assert result["maximum_channel_difference"] == 180
    assert result["artwork_accepted"] is False
    assert result["source_png_sha256"] == hashlib.sha256(before.read_bytes()).hexdigest()
    im = Image.new("RGBA", (10, 12), (0, 0, 0, 0))
    im.save(tmp_path/"mismatch.png")
    with pytest.raises(TaskError, match="dimensions"):
        compare_actual_pngs(before, tmp_path/"mismatch.png")


def test_hash_bound_stage_archive_and_read_only_workflow_qc(tmp_path):
    flow = CreativeWorkflow.create(tmp_path/"run", {
        "prompt": "An interior and a person holding a cup.",
        "width": 512, "height": 384,
    })
    flow.plan(candidate=new_scene())
    baseline = flow.diagnose_materials()
    assert baseline["native_stage_pixels"] == "not_archived"
    assert baseline["plan"]["artwork_accepted"] is False
    stages = validate_scene_v4(new_scene())["stages"]
    folder = flow.root/"stages"
    folder.mkdir()
    references = {}
    for i, stage in enumerate(stages):
        name = "stage-%02d-%s.png" % (i+1, stage["phase"])
        path = folder/name
        im = Image.new("RGBA", (12, 12), (20+30*i, 40, 60, 255))
        im.save(path)
        references[name] = {"path": "stages/"+name,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    record = flow.read()
    record["artifacts"]["stage_previews"] = references
    flow._save(record, "offline_test_stage_qc_fixtures")
    report = flow.diagnose_materials()
    assert report["native_stage_pixels"]["stages_verified"] == 3
    assert len(report["native_stage_pixels"]["transitions"]) == 2
    assert len(report["native_stage_pixels"]["transitions"][0]["subject_roi_deltas"]) == 3
    assert report["artwork_accepted"] is False
    first = folder/next(iter(references))
    first.write_bytes(b"tampered")
    with pytest.raises(TaskError, match="changed after archive"):
        flow.diagnose_materials()


def test_standalone_stage_archive_validation_rejects_missing_stage(tmp_path):
    with pytest.raises(TaskError, match="missing"):
        archived_stage_diagnostics(tmp_path, {}, [
            {"index": 0, "phase": "sketch"},
            {"index": 1, "phase": "block_in"},
        ])


def test_blue_noise_sampling_breaks_rigid_grid_without_losing_determinism():
    scene = old_scene()
    intent = scene["stages"][1]["intents"][0]
    shared = {"technique": "wash", "spacing": 35, "length": 60,
              "curvature": .12, "layers": 1, "edge_mode": "none",
              "palette": ["#556677", "#99AABB"], "seed": 57}
    intent["render"] = {**shared, "placement": "staggered"}
    a, _ = lower_scene_v4(scene)
    intent["render"] = {**shared, "placement": "blue_noise"}
    b, _ = lower_scene_v4(scene)
    c, _ = lower_scene_v4(deepcopy(scene))
    first = next(o for o in a["objects"] if o["id"] == "s01_room")
    second = next(o for o in b["objects"] if o["id"] == "s01_room")
    repeat = next(o for o in c["objects"] if o["id"] == "s01_room")
    assert first["elements"] != second["elements"]
    assert second["elements"] == repeat["elements"]
    assert 1 < len(second["elements"]) <= MAX_MARKS


def test_actual_subject_region_deltas_are_separate_from_global_metrics(tmp_path):
    before, after = tmp_path/"before.png", tmp_path/"after.png"
    Image.new("RGBA", (12, 12), (100, 120, 140, 255)).save(before)
    im = Image.new("RGBA", (12, 12), (100, 120, 140, 255))
    im.putpixel((2, 2), (110, 120, 140, 255))
    im.putpixel((10, 10), (110, 120, 140, 255))
    im.save(after)
    top_left = compare_actual_region(before, after, [0, 0, 6, 6], (12, 12))
    assert top_left["changed_pixels"] == 1
    assert top_left["region_pixels"] == 36
    assert "not layer-level attribution" in top_left["note"]
    assert compare_actual_pngs(before, after)["changed_rgba_pixels"] == 2
    with pytest.raises(TaskError, match="escapes"):
        compare_actual_region(before, after, [0, 0, 99, 3], (12, 12))


def test_material_light_direction_changes_value_group_without_changing_geometry():
    a = new_scene()
    b = new_scene()
    recipe_a = a["stages"][1]["intents"][2]["render"]
    recipe_b = b["stages"][1]["intents"][2]["render"]
    recipe_a.update(light_angle=-90, light_strength=1)
    recipe_b.update(light_angle=90, light_strength=1)
    left, _ = lower_scene_v4(a)
    right, _ = lower_scene_v4(b)
    def colors(scene):
        return [e["brush"]["color"] for obj in scene["objects"]
                if obj["id"] == "s01_cup" for e in obj["elements"]]
    assert colors(left) != colors(right)
    # Source order/geometry of paint marks are unchanged by the lighting palette.
    def geometries(scene):
        return [e["points"] for obj in scene["objects"]
                if obj["id"] == "s01_cup" for e in obj["elements"]]
    assert geometries(left) == geometries(right)
