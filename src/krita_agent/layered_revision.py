"""Approved opaque-overlay revision for complex multi-layer RGBA U8 documents.

Never attempts to infer buried paint layers from a composited image. A
brand-new top-level layer contains only opaque goal pixels for changed ROIs.
All existing layer nodes/masks remain editable and byte-untouched.
"""
import json
import time
import uuid
from pathlib import Path
from .document_graph import fingerprint
from .large_canvas import plan_overlay, image_metadata
from .protocol import TaskError
from .scheduler import MAX_WIRE_BYTES


def create_plan(before, target, graph_file, output, tile_size=512):
    graph=json.loads(Path(graph_file).read_text(encoding="utf-8"))
    plan=plan_overlay(before,target,graph,tile_size=tile_size)
    from .large_canvas import write_plan
    plan["id"]=uuid.uuid4().hex
    plan["graph_file"]=str(Path(graph_file).resolve())
    plan["file"]=write_plan(plan,output)
    return plan


def load(filename):
    path=Path(filename)
    plan=json.loads(path.read_text(encoding="utf-8"))
    if plan.get("schema")!="krita-agent-overlay/1":
        raise TaskError("Unknown layered revision plan schema")
    if type(plan.get("changes")) is not list or len(plan["changes"])>128:
        raise TaskError("Invalid changed-tile count")
    if plan.get("status") not in ("no_change","requires_approval"):
        raise TaskError("Invalid layered revision state")
    return plan


def _rgba_sha(path):
    from PIL import Image
    import hashlib
    with Image.open(path) as img:
        return hashlib.sha256(img.convert("RGBA").tobytes()).hexdigest()


def _source_tile_sha(path, box):
    from PIL import Image
    import hashlib
    x,y,w,h=box
    with Image.open(path) as img:
        pixels=img.crop((x,y,x+w,y+h)).convert("RGBA").tobytes()
    return hashlib.sha256(pixels).hexdigest()


def _goal_tile_matches(preview_file, target_file, box):
    from PIL import Image, ImageChops
    x,y,w,h=box
    with Image.open(preview_file) as current, Image.open(target_file) as target:
        current=current.convert("RGBA")
        goal=target.crop((x,y,x+w,y+h)).convert("RGBA")
        if current.size!=goal.size:
            return False
        return current.tobytes()==goal.tobytes()


def apply(client, plan, confirm=False, wait=True, timeout=1800):
    if confirm is not True:
        raise TaskError("Layered revision requires explicit user confirmation")
    if plan["status"]=="no_change":
        return {"state":"no_change","mutated":False}
    from .large_canvas import image_metadata
    if image_metadata(plan["source"]["path"])["sha256"]!=plan["source"]["sha256"]:
        raise TaskError("Baseline reference changed since approval")
    if image_metadata(plan["target"]["path"])["sha256"]!=plan["target"]["sha256"]:
        raise TaskError("Goal reference changed since approval")
    info=client.request("status")
    input_root=Path(info["input_dir"]).resolve()
    target=Path(plan["target"]["path"]).resolve()
    if target!=input_root and input_root not in target.parents:
        raise TaskError("Goal file must be inside the authorized input directory")
    current=client.request("document.graph")
    if fingerprint(current)!=plan["graph_sha256"]:
        raise TaskError("Live Krita layer tree changed since plan creation")
    if [current["document"]["width"],current["document"]["height"]]!=plan["source"]["size"]:
        raise TaskError("Live canvas differs from reference")
    if current["document"]["model"]!="RGBA" or current["document"]["depth"]!="U8":
        raise TaskError("Overlay requires RGBA U8")
    # Every changed tile must match the approved baseline. This is a strict
    # preflight before ANY mutation; unique filenames avoid silent overwrites.
    for index,item in enumerate(plan["changes"]):
        tile=item["tile"]
        result=client.request("preview.tile",x=tile[0],y=tile[1],
                   width=tile[2],height=tile[3],
                   filename="previews/overlay-preflight-"+uuid.uuid4().hex+".png")
        if _rgba_sha(result["path"])!=item["preflight_sha256"]:
            raise TaskError("Stale live canvas tile: "+str(index))
    checkpoint=client.request("checkpoint.create")
    overlay=client.request("revision.overlay.begin",confirm=True,checkpoint_id=checkpoint["id"],
                           name="AgentOverlay-"+plan["id"][:12])
    steps=[]
    for entry in plan["changes"]:
        x,y,w,h=entry["rect"]
        steps.append({"command":"pixel.transaction.patch","parameters":{
            "name":overlay["name"],"path":str(target),
            "x":x,"y":y,"width":w,"height":h,
            "source_x":x,"source_y":y,"confirm":True}})
    # A new KRA avoids changing the original file. The checkpoint pre-dates
    # overlay creation, so rollback always has the original full KRA.
    steps.append({"command":"document.save","parameters":{
        "path":"layered-revisions/"+plan["id"]+".kra","overwrite":False}})
    if len(json.dumps({"steps":steps},ensure_ascii=False).encode())>MAX_WIRE_BYTES:
        raise TaskError("Revision request exceeds IPC limit")
    try:
        job=client.submit(steps)
    except Exception:
        # The server may have applied the request, so NEVER resubmit.
        raise
    result={"state":"submitted","job_id":job["id"],"overlay":overlay,
            "checkpoint":checkpoint,"changed_tiles":len(plan["changes"])}
    if not wait:
        return result
    started=time.monotonic()
    while time.monotonic()-started<timeout:
        status=client.request("job.status",id=job["id"])
        if status["state"] in ("failed","cancelled","completed","interrupted"):
            result["state"]=status["state"]
            result["job"]=status
            break
        time.sleep(.3)
    else:
        result["state"]="unknown_needs_review"
        return result
    if result["state"]=="completed":
        verified=[]
        for entry in plan["changes"]:
            tile=entry["tile"]
            preview=client.request("preview.tile",x=tile[0],y=tile[1],
                width=tile[2],height=tile[3],
                filename="previews/overlay-result-"+uuid.uuid4().hex+".png")
            verified.append(_goal_tile_matches(preview["path"],str(target),tile))
        result["changed_tile_pixel_match"]=all(verified)
        result["changed_tiles_verified"]=len(verified)
        result["warning"]="Non-target tiles are unchanged only if the overlay was actually topmost and transparent outside patch; inspect KRA"
    return result
