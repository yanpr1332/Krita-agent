"""R18 extracted raster line guides: offline, consent-gated, NOT pen strokes."""
import json
from copy import deepcopy

import pytest
from PIL import Image, ImageDraw

from krita_agent.cli import parser_build
from krita_agent.lineart_cli_v18 import execute
from krita_agent.lineart_guides_v18 import (
    SCHEMA, trace_authorized, propose_scene_guides,
)
from krita_agent.protocol import TaskError
from krita_agent.scene_v4 import validate_scene_v4, compile_scene_v4
from krita_agent.semantic_planning_v14 import compile_semantic
from test_round18_lineart_library import manifest, rights
from test_round14_semantic_planning import proposal, brief


def fixture(tmp_path):
    im=Image.new("RGB",(128,128),"white")
    draw=ImageDraw.Draw(im)
    draw.line([(10,115),(28,70),(41,27),(78,21),(109,53)],
              fill="black",width=3,joint="curve")
    draw.line([(28,70),(70,101),(111,111)],fill="black",width=2)
    im.save(tmp_path/"ink.png")
    src=manifest()
    src["assets"]=src["assets"][:1]
    return src


def test_real_local_raster_line_is_traced_as_finite_normalized_proxy(tmp_path):
    src=fixture(tmp_path)
    report=trace_authorized(tmp_path,src,"cat_ink",max_paths=8)
    assert report["schema"]==SCHEMA
    assert report["source_id"]=="cat_ink"
    assert len(report["source_sha256"])==64
    assert 1<=len(report["guides"])<=8
    assert report["original_pressure_recovered"] is False
    assert report["original_stroke_order_recovered"] is False
    assert report["native_effects"]=="none" and report["model_requests"]==0
    for guide in report["guides"]:
        assert 2<=len(guide["path_normalized"])<=128
        assert guide["raster_length_px"]>=8
        assert all(0<=x<=1 and 0<=y<=1 for x,y in guide["path_normalized"])
    assert report==trace_authorized(tmp_path,src,"cat_ink",max_paths=8)


def test_opt_in_binding_generates_new_v4_proposal_without_native_effect(tmp_path):
    src=fixture(tmp_path)
    report=trace_authorized(tmp_path,src,"cat_ink",max_paths=5)
    _,_,scene=compile_semantic(proposal(),brief())
    original=deepcopy(scene)
    with pytest.raises(TaskError,match="Explicit confirmation"):
        propose_scene_guides(scene,report,"cat")
    joined=propose_scene_guides(scene,report,"cat",confirm=True)
    assert joined["scene_v4"]!=scene
    assert joined["source_lineart_sha256"]==report["source_sha256"]
    assert joined["native_effects"]=="none"
    assert joined["reference_pixels_pasted"] is False
    assert joined["actual_pen_pressure_recovered"] is False
    assert joined["stage_approval_required"] is True
    assert scene==original
    vetted=validate_scene_v4(joined["scene_v4"])
    assert vetted==joined["scene_v4"]
    compiled=compile_scene_v4(vetted)
    assert compiled["requires_native_approval"] is True
    assert compiled["not_artwork_acceptance"] is True
    assert all(x["command"] not in ("image.import","reference.import")
               for x in compiled["steps"])
    added=[i for i in vetted["stages"][0]["intents"] if i["id"].startswith("r18_")]
    assert len(added)==len(report["guides"])
    assert all(i["subject_id"]=="cat" and "natural" in i for i in added)


def test_binding_fails_closed_on_forged_rights_geometry_and_unknown_target(tmp_path):
    src=fixture(tmp_path)
    result=trace_authorized(tmp_path,src,"cat_ink")
    _,_,scene=compile_semantic(proposal(),brief())
    with pytest.raises(TaskError,match="Unknown reviewed"):
        propose_scene_guides(scene,result,"not_a_subject",confirm=True)
    forged=deepcopy(result)
    forged["rights"]["can_analyze_locally"]=False
    with pytest.raises(TaskError,match="not authorized"):
        propose_scene_guides(scene,forged,"cat",confirm=True)
    forged=deepcopy(result)
    forged["guides"][0]["path_normalized"][0][0]=1.5
    with pytest.raises(TaskError,match="lineart x"):
        propose_scene_guides(scene,forged,"cat",confirm=True)
    forged=deepcopy(result)
    forged["source_sha256"]="not_a_real_hash"
    with pytest.raises(TaskError,match="SHA-256"):
        propose_scene_guides(scene,forged,"cat",confirm=True)


def test_trace_rejects_unlicensed_colored_and_unsafe_masks(tmp_path):
    src=fixture(tmp_path)
    src["assets"][0]["rights"]["basis"]="unknown"
    with pytest.raises(TaskError,match="basis"):
        trace_authorized(tmp_path,src,"cat_ink")
    src=fixture(tmp_path)
    src["assets"][0]["kind"]="photo"
    with pytest.raises(TaskError,match="lineart/sketch"):
        trace_authorized(tmp_path,src,"cat_ink")
    src=fixture(tmp_path)
    Image.new("RGB",(128,128),"black").save(tmp_path/"ink.png")
    with pytest.raises(TaskError,match="mask empty or too dense"):
        trace_authorized(tmp_path,src,"cat_ink")


def test_trace_and_bind_cli_are_opt_in_and_create_no_native_art(tmp_path):
    src=fixture(tmp_path)
    request=tmp_path/"request.json"
    request.write_text(json.dumps(src),encoding="utf-8")
    guides=tmp_path/"guides.json"
    args=parser_build().parse_args([
        "lineart","trace","--root",str(tmp_path),
        "--manifest",str(request),"--source-id","cat_ink",
        "--output",str(guides)])
    output=execute(args)
    assert output["exclusive_create"]
    assert guides.exists()
    _,_,scene=compile_semantic(proposal(),brief())
    scene_path=tmp_path/"scene.json"
    scene_path.write_text(json.dumps(scene),encoding="utf-8")
    target=tmp_path/"candidate.json"
    deny=parser_build().parse_args([
        "lineart","bind","--scene",str(scene_path),"--guides",str(guides),
        "--subject-id","cat","--output",str(target)])
    with pytest.raises(TaskError,match="Explicit confirmation"):
        execute(deny)
    assert not target.exists()
    allow=parser_build().parse_args([
        "lineart","bind","--scene",str(scene_path),"--guides",str(guides),
        "--subject-id","cat","--confirm-proposal","--output",str(target)])
    result=execute(allow)
    assert result["exclusive_create"] and target.exists()
    saved=json.loads(target.read_text(encoding="utf-8"))
    assert saved["stage_approval_required"] is True
    assert not (tmp_path/"artwork.kra").exists()
