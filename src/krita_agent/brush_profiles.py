"""Opt-in, evidence-backed brush calibration catalogue and selection."""
import hashlib
import json
import os
import uuid
from pathlib import Path

CATEGORIES={"ink","sketch","paint","texture","erase","mask"}


def calibration_task(preset, size=24):
    if not isinstance(preset,str) or not 1<=len(preset)<=120:
        raise ValueError("Invalid preset")
    if type(size) not in (int,float) or not 0.1<=size<=500:
        raise ValueError("Invalid brush size")
    pressures=(.1,.3,.6,.9)
    steps=[
        {"command":"canvas.create","parameters":{"width":640,"height":440,
                                                    "name":"Brush Calibration"}},
        {"command":"layer.create","parameters":{"name":"Pressure Response"}},
        {"command":"brush.configure","parameters":{"preset":preset,"size":size,
                 "color":"#294964","pressure_enabled":True}},
    ]
    for row,force in enumerate(pressures):
        y=65+row*90
        steps.append({"command":"draw.stroke","parameters":{
            "mode":"auto","points":[
                {"x":60,"y":y,"pressure":force,"time_ms":0},
                {"x":310,"y":y,"pressure":force,"time_ms":80},
                {"x":560,"y":y,"pressure":force,"time_ms":160}]}})
    steps.append({"command":"document.export","parameters":{
        "path":"brush-calibration/"+uuid.uuid4().hex+".png","overwrite":False}})
    return {"steps":steps,"purpose":"visual and pixel inspection required; code alone cannot certify brush dynamics"}


def record_profile(directory, record, evidence_path):
    required=("preset","build","category","pressure_size","pressure_opacity","confidence")
    if not isinstance(record,dict) or any(key not in record for key in required):
        raise ValueError("Incomplete brush calibration record")
    if record["category"] not in CATEGORIES:
        raise ValueError("Unknown brush category")
    if not isinstance(record["preset"],str) or len(record["preset"])>120:
        raise ValueError("Preset name invalid")
    if not isinstance(record["build"],str) or not record["build"]:
        raise ValueError("Build identifier required")
    for key in ("pressure_size","pressure_opacity"):
        if type(record[key]) is not bool:
            raise ValueError(key+" requires boolean")
    if type(record["confidence"]) not in (float,int) or not 0<=record["confidence"]<=1:
        raise ValueError("Confidence outside [0,1]")
    evidence=Path(evidence_path).resolve()
    if not evidence.is_file() or evidence.stat().st_size>5000000:
        raise ValueError("Missing/oversized evidence file")
    sha=hashlib.sha256(evidence.read_bytes()).hexdigest()
    destination=Path(directory).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    profile={"schema":"krita-agent-brush-profile/1",**record,"evidence_sha256":sha,
             "evidence_path":str(evidence),"status":"manually_reviewed",
             "id":uuid.uuid4().hex}
    target=destination/(profile["id"]+".json")
    with target.open("x",encoding="utf-8") as f:
        json.dump(profile,f,indent=2,ensure_ascii=False)
    return profile


def find_profiles(directory, build=None, category=None, min_confidence=0):
    root=Path(directory)
    if not 0<=min_confidence<=1:
        raise ValueError("Invalid min_confidence")
    profiles=[]
    if not root.is_dir():
        return profiles
    for path in sorted(root.glob("*.json")):
        if path.stat().st_size>250000:
            continue
        try:
            p=json.loads(path.read_text(encoding="utf-8"))
            if p.get("schema")!="krita-agent-brush-profile/1":
                continue
            if build and p.get("build")!=build:
                continue
            if category and p.get("category")!=category:
                continue
            if p.get("confidence",0)<min_confidence:
                continue
            profiles.append(p)
        except (ValueError,OSError,TypeError):
            continue
    return sorted(profiles,key=lambda x:(-x["confidence"],x["preset"]))


def choose(directory, build, category, min_confidence=.8):
    found=find_profiles(directory,build,category,min_confidence)
    if not found:
        raise ValueError("No manually reviewed brush profile meets requirements")
    return found[0]
