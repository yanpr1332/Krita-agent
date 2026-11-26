"""R18 local binary line-art guide extraction and opt-in reviewed scene binding.

Extracted skeleton segments are *estimated raster centerlines*, not the artist's
original stylus gestures, timestamps, tilt, pressure or real brush presets.
Only explicitly authorized local pixels are read; no image/model/native write.
"""
from copy import deepcopy
import hashlib
import math

from .protocol import TaskError, integer, number
from .lineart_library_v18 import validate_manifest, _safe_local_image
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4

SCHEMA = "krita-agent-lineart-guides/1"
MAX_PATHS = 16
MAX_DIM = 256
MAX_ITERATIONS = 24
NEIGHBORS = [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]


def _load_ink(root, filename, threshold):
    from PIL import Image, ImageOps
    path = _safe_local_image(root,filename)
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        with Image.open(path) as source:
            if source.width*source.height>16_000_000 or min(source.size)<8:
                raise TaskError("Lineart image outside safe pixel limits")
            oriented=ImageOps.exif_transpose(source)
            rgba=oriented.convert("RGBA")
            background=Image.new("RGBA",rgba.size,(255,255,255,255))
            flat=Image.alpha_composite(background,rgba).convert("L")
            flat.thumbnail((MAX_DIM,MAX_DIM))
            w,h=flat.size
            mask={(i%w,i//w) for i,value in enumerate(flat.getdata())
                  if value<=threshold}
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        raise TaskError("Unreadable or unsafe local lineart") from exc
    if not 8<=len(mask)<=int(w*h*.35):
        raise TaskError("Lineart mask empty or too dense to safely trace")
    return sha,w,h,mask


def _thin(ink,w,h):
    """Bounded Zhang-Suen binary morphology, with explicit convergence."""
    ink=set(ink)
    for _ in range(MAX_ITERATIONS):
        removed=0
        for phase in (0,1):
            drop=[]
            for x,y in sorted(ink):
                if x==0 or y==0 or x>=w-1 or y>=h-1:
                    continue
                b=[(x+dx,y+dy) in ink for dx,dy in NEIGHBORS]
                B=sum(b)
                A=sum(not b[i] and b[(i+1)%8] for i in range(8))
                if B<2 or B>6 or A!=1:
                    continue
                p2,p4,p6,p8=b[0],b[2],b[4],b[6]
                if phase==0:
                    valid=not(p2 and p4 and p6) and not(p4 and p6 and p8)
                else:
                    valid=not(p2 and p4 and p8) and not(p2 and p6 and p8)
                if valid:
                    drop.append((x,y))
            for p in drop:
                ink.remove(p)
            removed+=len(drop)
        if removed==0:
            return ink
    raise TaskError("Lineart skeleton did not converge within bounded iterations")


def _trace_paths(skeleton):
    graph={p: sorted((p[0]+dx,p[1]+dy) for dx,dy in NEIGHBORS
                     if (p[0]+dx,p[1]+dy) in skeleton)
           for p in skeleton}
    visited=set();found=[]
    def edge(a,b):
        return (a,b) if a<=b else (b,a)
    def walk(start,first):
        chain=[start,first];visited.add(edge(start,first))
        prev,cur=start,first
        while len(chain)<=MAX_DIM*MAX_DIM:
            options=[p for p in graph[cur] if p!=prev and
                     edge(cur,p) not in visited]
            if len(graph[cur])!=2 or not options:
                break
            nxt=options[0]
            visited.add(edge(cur,nxt))
            chain.append(nxt)
            prev,cur=cur,nxt
        return chain
    terminals=sorted(p for p,near in graph.items() if len(near)!=2)
    for p in terminals:
        for n in graph[p]:
            if edge(p,n) not in visited:
                found.append(walk(p,n))
    for p in sorted(graph):
        for n in graph[p]:
            if edge(p,n) not in visited:
                found.append(walk(p,n))  # closed loop
    return found


def _polyline_length(path):
    return sum(math.hypot(b[0]-a[0],b[1]-a[1])
               for a,b in zip(path,path[1:]))


def trace_authorized(root, raw_manifest, source_id, threshold=175, max_paths=12):
    """Return limited normalized vector *hypotheses* from explicit local image."""
    manifest=validate_manifest(raw_manifest)
    if type(source_id) is not str:
        raise TaskError("Source ID required for explicit trace")
    match=[a for a in manifest["assets"] if a["id"]==source_id]
    if len(match)!=1 or match[0]["kind"] not in ("lineart","sketch"):
        raise TaskError("Trace requires one authorized lineart/sketch asset ID")
    limit=integer(max_paths,"max_paths",1,MAX_PATHS)
    t=integer(threshold,"threshold",40,220)
    asset=match[0]
    if not asset["rights"]["can_analyze_locally"]:
        raise TaskError("Lineart tracing requires local analysis rights")
    sha,w,h,mask=_load_ink(root,asset["file"],t)
    skeleton=_thin(mask,w,h)
    chains=_trace_paths(skeleton)
    chains=sorted((p for p in chains if _polyline_length(p)>=8),
                  key=lambda p:(-_polyline_length(p),p[0]))[:limit]
    if not chains:
        raise TaskError("No reliably traversable line guides; ask for cleaner art")
    guides=[]
    for i,chain in enumerate(chains):
        # Bounded geometry derived from raster pixels, not actual pen events.
        step=max(1,math.ceil((len(chain)-1)/127))
        reduced=chain[::step]
        if reduced[-1]!=chain[-1]:
            reduced.append(chain[-1])
        if len(reduced)>128:
            reduced=reduced[:127]+[chain[-1]]
        coords=[[round(x/max(1,w-1),6),round(y/max(1,h-1),6)]
                for x,y in reduced]
        guides.append({
            "id":"guide_%02d"%(i+1),
            "path_normalized":coords,
            "raster_length_px":round(_polyline_length(chain),2),
        })
    return {
        "schema":SCHEMA,"source_id":asset["id"],"source_sha256":sha,
        "rights":asset["rights"],"guides":guides,
        "image_inspection":"local_skeleton_vector_hypothesis",
        "original_stroke_order_recovered":False,
        "original_pressure_recovered":False,
        "model_requests":0,"network_requests":0,
        "native_effects":"none","requires_scene_approval":True,
        "artwork_accepted":False,
    }


def propose_scene_guides(scene, guide_report, subject_id, confirm=False):
    """Explicitly add approximate gestures; returns NEW unapproved v4 scene.

    No image is pasted to Krita; source owner must independently approve
    the augmented ScenePlan before its existing staged native workflow.
    """
    if confirm is not True:
        raise TaskError("Explicit confirmation required to propose lineart guides")
    original=validate_scene_v4(scene)
    if type(guide_report) is not dict or guide_report.get("schema")!=SCHEMA:
        raise TaskError("Unknown lineart guide report")
    if guide_report.get("rights",{}).get("can_analyze_locally") is not True:
        raise TaskError("Lineart guide source is not authorized")
    if not isinstance(guide_report.get("source_sha256"),str) or not (
            len(guide_report["source_sha256"])==64 and all(
            c in "0123456789abcdef" for c in guide_report["source_sha256"])):
        raise TaskError("Lineart guide report lacks a SHA-256 source identity")
    by_id={s["id"]:s for s in original["subjects"]}
    if subject_id not in by_id:
        raise TaskError("Unknown reviewed scene subject for lineart placement")
    guides=guide_report.get("guides")
    if type(guides) is not list or not 1<=len(guides)<=MAX_PATHS:
        raise TaskError("Lineart guide report needs 1..16 bounded paths")
    new=deepcopy(original)
    target=next(s for s in new["stages"] if s["phase"]=="sketch")
    if len(target["intents"])+len(guides)>32:
        raise TaskError("Sketch stage exceeds 32 reviewed intents")
    node=by_id[subject_id]
    x,y,w,h=node["bounds"]
    for i,guide in enumerate(guides):
        path=guide.get("path_normalized") if type(guide) is dict else None
        if type(path) is not list or not 2<=len(path)<=128:
            raise TaskError("Lineart guide has invalid point count")
        points=[]
        for p in path:
            if type(p) is not list or len(p)!=2:
                raise TaskError("Lineart guide point must be normalized XY")
            u=number(p[0],"lineart x",0,1)
            v=number(p[1],"lineart y",0,1)
            points.append([round(min(x+w,max(x,x+u*w)),4),
                           round(min(y+h,max(y,y+v*h)),4)])
        if len(set(tuple(p) for p in points))<2:
            raise TaskError("Degenerate reference lineart guide")
        target["intents"].append({
            "id":"r18_%02d_%s"%(i+1,subject_id[:15]),
            "subject_id":subject_id,
            "kind":"gesture",
            "purpose":"Follow permitted raster line guide for "+node["name"],
            "path":points,
            "natural":{"purpose":"contour","spacing":3,
                       "smoothing_passes":1},
        })
    verified=validate_scene_v4(new)
    return {
        "schema":"krita-agent-lineart-scene-proposal/1",
        "source_scene_v4_sha256":digest(original),
        "source_lineart_sha256":guide_report["source_sha256"],
        "proposed_scene_v4_sha256":digest(verified),
        "scene_v4":verified,
        "stage_approval_required":True,
        "native_effects":"none",
        "reference_pixels_pasted":False,
        "actual_pen_pressure_recovered":False,
        "artwork_accepted":False,
    }
