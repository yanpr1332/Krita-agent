"""R19 hash-bound actual-PNG diagnostics; synthetic image fixtures are NOT Krita."""
import hashlib
import json
from copy import deepcopy

import pytest
from PIL import Image, ImageDraw

from krita_agent.art_diagnostics_v19 import (
    SCHEMA, triage, verify_triage,
)
from krita_agent.cli import parser_build
from krita_agent.art_review_cli_v19 import execute
from krita_agent.protocol import TaskError
from krita_agent.semantic_planning_v14 import compile_semantic
from test_round14_semantic_planning import proposal, brief


def fixture(tmp_path):
    _,_,scene=compile_semantic(proposal(),brief())
    image=Image.new("RGBA",(512,384),(236,232,221,255))
    draw=ImageDraw.Draw(image)
    draw.ellipse((114,94,305,326),fill=(168,133,110,255))
    draw.rectangle((366,212,458,311),fill=(70,130,185,255))
    png=tmp_path/"synthetic-offline-pixels.png"
    image.save(png)
    sha=hashlib.sha256(png.read_bytes()).hexdigest()
    review={
        "schema":"krita-agent-multimodal-review/1",
        "decision":"needs_revision",
        "artwork_png_sha256":sha,
        "issues":[
            {
                "id":"issue-cat-1","object_id":"s01_cat",
                "severity":"major","region":[135,120,60,80],
                "observation":"The lower face is flat and lacks visible contours",
                "recommendation":"Develop the localized head contour with reviewed brush strokes",
            },
            {
                "id":"issue-cup-1","object_id":"cup",
                "severity":"minor","region":[370,220,35,40],
                "observation":"The cup rim does not show a convincing upper ellipse",
                "recommendation":"Add a bounded visible rim inside the approved ROI",
            },
        ],
    }
    return scene,png,review


def test_r19_actual_pixels_create_hash_bound_prioritized_tickets(tmp_path):
    scene,png,review=fixture(tmp_path)
    report=triage(scene,png,review)
    assert report["schema"]==SCHEMA
    assert len(report["tickets"])==2
    assert report["tickets"][0]["subject_id"]=="cat"
    assert report["tickets"][0]["severity"]=="major"
    assert report["tickets"][1]["subject_id"]=="cup"
    assert all("pixel_evidence" in t for t in report["tickets"])
    assert report["tickets"][0]["pixel_evidence"]["samples"]>0
    assert report["tickets"][0]["pixel_evidence"]["not_human_quality_judgment"]
    assert report["model_requests"]==0
    assert report["native_effects"]=="none"
    assert report["image_upload_performed"] is False
    assert report["real_krita_provenance_verified"] is False
    assert report["independent_artwork_acceptance"] is False
    assert report==triage(deepcopy(scene),png,deepcopy(review))
    assert verify_triage(report,scene,png,review)["valid"] is True


def test_severity_and_explicit_area_budgets_do_not_silently_drop_issues(tmp_path):
    scene,png,review=fixture(tmp_path)
    report=triage(scene,png,review,max_tickets=1)
    assert len(report["tickets"])==1
    assert report["tickets"][0]["subject_id"]=="cat"
    assert report["deferred_issues"]==[{
        "subject_id":"cup","issue_id":"issue-cup-1",
        "reason":"review_budget_exceeded",
    }]
    blocked=triage(scene,png,review,max_area_fraction=.01)
    # The critical subject exceeds the budget, but the smaller minor ROI
    # still fits. Both outcomes must be explicit, not silently dropped.
    assert [x["subject_id"] for x in blocked["tickets"]]==["cup"]
    assert [x["subject_id"] for x in blocked["deferred_issues"]]==["cat"]
    assert blocked["total_selected_area_px"]==1400


def test_invalid_review_and_scene_region_are_refused(tmp_path):
    scene,png,review=fixture(tmp_path)
    bad=deepcopy(review)
    bad["issues"][0]["region"]=[500,100,50,50]
    with pytest.raises(TaskError,match="canvas"):
        triage(scene,png,bad)
    bad=deepcopy(review)
    bad["issues"][0]["region"]=[0,0,20,20]
    with pytest.raises(TaskError,match="subject bounds"):
        triage(scene,png,bad)
    bad=deepcopy(review)
    bad["issues"][0]["object_id"]="unknown"
    with pytest.raises(TaskError,match="unknown scene subject"):
        triage(scene,png,bad)
    bad=deepcopy(review)
    bad["issues"][0]["recommendation"]="short"
    with pytest.raises(TaskError,match="concrete"):
        triage(scene,png,bad)
    bad=deepcopy(review)
    bad["decision"]="provisional_pass"
    with pytest.raises(TaskError,match="contradicts"):
        triage(scene,png,bad)
    bad=deepcopy(review)
    bad["issues"].append(deepcopy(bad["issues"][0]))
    with pytest.raises(TaskError,match="Duplicate"):
        triage(scene,png,bad)
    bad=deepcopy(review)
    bad["issues"][0]["command"]="shell.run"
    with pytest.raises(TaskError,match="unsupported"):
        triage(scene,png,bad)


def test_actual_png_and_review_fingerprints_protect_replay(tmp_path):
    scene,png,review=fixture(tmp_path)
    report=triage(scene,png,review)
    edited=deepcopy(report)
    edited["tickets"][0]["roi"]=[1,2,3,4]
    with pytest.raises(TaskError,match="changed relative"):
        verify_triage(edited,scene,png,review)
    changed_review=deepcopy(review)
    changed_review["issues"][0]["observation"]+=" Another drawing problem."
    with pytest.raises(TaskError,match="changed relative"):
        verify_triage(report,scene,png,changed_review)
    Image.new("RGBA",(512,384),(0,0,0,255)).save(png)
    with pytest.raises(TaskError,match="different SHA-256"):
        verify_triage(report,scene,png,review)


def test_native_scene_source_hash_must_match_record(tmp_path):
    scene,png,review=fixture(tmp_path)
    report=triage(scene,png,review)
    modified=deepcopy(scene)
    modified["style"]="Another artistic mood"
    with pytest.raises(TaskError,match="changed relative"):
        verify_triage(report,modified,png,review)


def test_cli_can_write_exclusive_report_and_verify_without_vlm_or_krita(tmp_path):
    scene,png,review=fixture(tmp_path)
    scene_path=tmp_path/"scene.json"
    review_path=tmp_path/"review.json"
    out=tmp_path/"triage.json"
    scene_path.write_text(json.dumps(scene),encoding="utf-8")
    review_path.write_text(json.dumps(review),encoding="utf-8")
    a=parser_build().parse_args([
        "art-review","triage","--scene",str(scene_path),
        "--png",str(png),"--review",str(review_path),
        "--output",str(out)])
    result=execute(a)
    assert result["exclusive_create"]
    assert out.exists()
    with pytest.raises(TaskError,match="will not overwrite"):
        execute(a)
    check=parser_build().parse_args([
        "art-review","verify","--scene",str(scene_path),
        "--png",str(png),"--review",str(review_path),
        "--report",str(out)])
    verified=execute(check)
    assert verified["valid"] is True
    assert verified["native_effects"]=="none"
    assert not (tmp_path/"artwork.kra").exists()


@pytest.mark.parametrize("bad",[
    {"max_tickets":0},
    {"max_tickets":9},
    {"max_area_fraction":.001},
    {"max_area_fraction":2.0},
])
def test_budgets_fail_before_any_local_side_effect(tmp_path,bad):
    scene,png,review=fixture(tmp_path)
    with pytest.raises(TaskError):
        triage(scene,png,review,**bad)
