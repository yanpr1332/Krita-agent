"""Offline ScenePlan v2, feedback and manual brush profile tests; NOT RUN."""
import json
import pytest
from krita_agent.scene_v2 import compile_plan,load_ai_candidate
from krita_agent.brush_profiles import calibration_task,record_profile,choose
from krita_agent.feedback_v2 import assess


def test_scene_v2_is_reviewable():
    scene={"schema":"krita-agent-scene/2",
           "document":{"width":512,"height":512},
           "layers":[{"name":"Ink","role":"lineart","brush":{"size":13},
                      "elements":[{"kind":"rectangle","rect":[1,2,40,50]}]}]}
    plan=compile_plan(scene)
    assert plan["layers"][0]["role"]=="lineart"
    assert plan["steps"][0]["command"]=="canvas.create"
    assert plan["sha256"]==load_ai_candidate(json.dumps(scene))["sha256"]


def test_brush_profile_requires_evidence(tmp_path):
    task=calibration_task("Basic-5 Size")
    assert any(x["command"]=="draw.stroke" for x in task["steps"])
    p=tmp_path/"evidence.txt"
    p.write_text("Manually reviewed measured brush output")
    record_profile(tmp_path/"profiles",{"preset":"Basic-5 Size","build":"Qt5",
             "category":"ink","pressure_size":True,"pressure_opacity":False,
             "confidence":.9},p)
    result=choose(tmp_path/"profiles","Qt5","ink")
    assert result["status"]=="manually_reviewed"


def test_alpha_only_feedback_is_detected(tmp_path):
    Image=pytest.importorskip("PIL.Image")
    a=tmp_path/"a.png";b=tmp_path/"b.png"
    Image.new("RGBA",(3,3),(0,0,0,0)).save(a)
    goal=Image.new("RGBA",(3,3),(0,0,0,0))
    goal.putpixel((1,1),(0,0,0,255))
    goal.save(b)
    info=assess(a,b,{})
    assert info["pixel_goal_met"] is False
    assert info["difference_bbox"]==[1,1,2,2]
