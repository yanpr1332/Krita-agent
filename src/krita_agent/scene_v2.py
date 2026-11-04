"""Reviewable ScenePlan v2: semantic layer descriptors plus exact native steps.

Optional external AI output is accepted ONLY as untrusted structured JSON and
passed through the same deterministic allowlist. No model execution here.
"""
import hashlib
import json
from .protocol import TaskError, brush_settings, label
from .creative_plans import compile_scene
from .workflow import compile_workflow

SCHEMA="krita-agent-scene/2"
ROLES={"background","lineart","base_color","shadow","highlight","texture",
       "foreground","reference","effects","custom"}


def compile_plan(scene):
    if not isinstance(scene,dict) or scene.get("schema")!=SCHEMA:
        raise TaskError("Expected ScenePlan v2 object")
    layers=scene.get("layers")
    if not isinstance(layers,list) or not 1<=len(layers)<=64:
        raise TaskError("ScenePlan v2 requires 1..64 layers")
    steps=[]
    doc=scene.get("document")
    if doc is not None:
        if not isinstance(doc,dict):
            raise TaskError("Invalid canvas")
        steps.extend(compile_scene({"document":doc,"layers":[{"name":"Placeholder","elements":[]} ]})[:1])
    diagnostics=[]
    used_names=set()
    for index,layer in enumerate(layers):
        if not isinstance(layer,dict):
            raise TaskError("Layer must be an object")
        name=label(layer.get("name"),"name")
        if name in used_names:
            raise TaskError("Duplicate layer name would make edits ambiguous: "+name)
        used_names.add(name)
        role=layer.get("role","custom")
        if role not in ROLES:
            raise TaskError("Unsupported layer role")
        stages=compile_scene({"layers":[{
            "name":name,"brush":layer.get("brush",{}),
            "elements":layer.get("elements",[])}]})
        steps.extend(stages)
        if "opacity" in layer or "visible" in layer:
            props={}
            if "opacity" in layer:
                from .protocol import number
                props["opacity"]=number(layer["opacity"],"opacity",0,1)
            if "visible" in layer:
                if type(layer["visible"]) is not bool:
                    raise TaskError("visible must be boolean")
                props["visible"]=layer["visible"]
            steps.append({"command":"layer.set","parameters":{"name":name,"properties":props}})
        if layer.get("preview",False):
            steps.append({"command":"preview.canvas","parameters":{
                "filename":"scene-v2/preview-"+str(index)+".png",
                "width":512,"height":512}})
        diagnostics.append({"name":name,"role":role,"elements":len(layer.get("elements",[]))})
    if len(steps)>10000:
        raise TaskError("Scene exceeds max 10000 steps")
    # Each command is individually rechecked. Large plans are submitted with
    # scheduler.run; here no side effects occur.
    verified=[]
    for step in steps:
        verified.extend(compile_workflow({"steps":[step]}))
    canonical=json.dumps(verified,sort_keys=True,ensure_ascii=False,allow_nan=False)
    return {"schema":SCHEMA,"steps":verified,"layers":diagnostics,
            "sha256":hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "side_effects":"requires explicit --submit and a validated Krita session",
            "note":"Semantic labels guide the human; Krita does not interpret layer roles natively"}


def load_ai_candidate(candidate):
    """No direct command authority for generated content."""
    if isinstance(candidate,str):
        candidate=json.loads(candidate)
    return compile_plan(candidate)
