"""Round 19 actual-PNG-grounded, bounded revision issue triage.

This is a source/hash-bound review-queue planner, NOT a human art verdict,
an AI painter, a generated final image, or permission to replay native effects.
External VLM review remains separately opt-in through existing R11 tooling.
"""
import hashlib
import math
import re
from pathlib import Path

from .protocol import TaskError, number, integer
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4

SCHEMA = "krita-agent-visual-triage/1"
REVIEW_SCHEMAS = frozenset((
    "krita-agent-multimodal-review/1",
    "krita-agent-creative-critique/1",
))
SEVERITY = {"critical":0, "major":1, "minor":2}
MAX_IMAGE_BYTES = 16*1024*1024
MAX_ISSUES = 30
MAX_TICKETS = 8


def _png(path, size):
    from PIL import Image
    source=Path(path).expanduser()
    if (source.is_symlink() or not source.is_file()
            or source.suffix.lower()!=".png"
            or not 0<source.stat().st_size<=MAX_IMAGE_BYTES):
        raise TaskError("Actual PNG unavailable, linked or oversized")
    try:
        with Image.open(source) as im:
            if im.format!="PNG" or im.size!=tuple(size):
                raise TaskError("Actual PNG dimensions differ from reviewed scene")
            im.verify()
        with Image.open(source) as im:
            image=im.convert("RGBA")
            if image.width*image.height>32_000_000:
                raise TaskError("Actual PNG pixel budget exceeded")
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        raise TaskError("Unreadable or unsafe actual PNG") from exc
    h=hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda:stream.read(65536),b""):
            h.update(block)
    return image,h.hexdigest()


def _roi_stats(image,roi):
    x,y,w,h=roi
    chunk=image.crop((x,y,x+w,y+h))
    chunk.thumbnail((96,96))
    pixels=list(chunk.getdata())
    n=len(pixels)
    if not n:
        raise TaskError("Empty pixel-evidence ROI")
    mean_rgb=[sum(p[c] for p in pixels)/n for c in range(3)]
    mean_luma=sum(.2126*p[0]+.7152*p[1]+.0722*p[2]
                  for p in pixels)/n
    variability=sum((.2126*p[0]+.7152*p[1]+.0722*p[2]-mean_luma)**2
                    for p in pixels)/n
    return {
        "roi":[x,y,w,h],
        "mean_rgb":[round(v,3) for v in mean_rgb],
        "mean_luminance":round(mean_luma,3),
        "luminance_variance":round(variability,3),
        "nontransparent_share":round(
            sum(p[3]>0 for p in pixels)/n,5),
        "rgb_buckets":len({(p[0]//32,p[1]//32,p[2]//32) for p in pixels}),
        "samples":n,
        "evidence_type":"actual_supplied_png_pixels_only",
        "not_human_quality_judgment":True,
    }


def _target_scene_id(row,by_id):
    value=row.get("object_id")
    if type(value) is not str:
        raise TaskError("Revision issue lacks object ID")
    if value in by_id:
        return value
    m=re.fullmatch(r"s\d\d_([a-z][a-z0-9_-]{0,31})",value)
    if m and m.group(1) in by_id:
        return m.group(1)
    raise TaskError("Revision issue refers to an unknown scene subject")


def _safe_issue(row,by_id,canvas):
    if type(row) is not dict:
        raise TaskError("Revision issue must be a JSON object")
    if set(row)-{"id","object_id","severity","region",
                 "observation","recommendation"}:
        raise TaskError("Revision issue contains unsupported fields")
    subject=_target_scene_id(row,by_id)
    severity=row.get("severity")
    if severity not in SEVERITY:
        raise TaskError("Invalid revision severity")
    for key,minimum in (("observation",20),("recommendation",15)):
        text=row.get(key)
        if type(text) is not str or not minimum<=len(text.strip())<=1200:
            raise TaskError("Revision issue lacks concrete visible evidence")
    box=row.get("region")
    if type(box) is not list or len(box)!=4:
        raise TaskError("Revision issue ROI must have x,y,width,height")
    x,y,w,h=[number(v,"revision ROI",0,max(canvas)) for v in box]
    if min(w,h)<=0 or x+w>canvas[0] or y+h>canvas[1]:
        raise TaskError("Revision ROI outside supplied canvas")
    bx,by,bw,bh=by_id[subject]["bounds"]
    if x<bx-1e-7 or y<by-1e-7 or x+w>bx+bw+1e-7 or y+h>by+bh+1e-7:
        raise TaskError("Revision ROI escaped declared subject bounds")
    left,top=math.floor(x),math.floor(y)
    right,bottom=math.ceil(x+w),math.ceil(y+h)
    bounded=[left,top,right-left,bottom-top]
    if bounded[0]<0 or bounded[1]<0 or right>canvas[0] or bottom>canvas[1]:
        raise TaskError("Rounded revision ROI escaped canvas")
    return {
        "id":str(row.get("id","issue"))[:64],
        "subject_id":subject, "severity":severity,
        "roi":bounded,"requested_region":[x,y,w,h],
        "observation":row["observation"].strip(),
        "recommendation":row["recommendation"].strip(),
    }


def triage(scene, actual_png, review, max_tickets=6, max_area_fraction=.2):
    """Prioritize real-image-bound ROI repairs, without composing brush commands."""
    source=validate_scene_v4(scene)
    cap=integer(max_tickets,"max_tickets",1,MAX_TICKETS)
    fraction=number(max_area_fraction,"max_area_fraction",.01,.5)
    if type(review) is not dict or review.get("schema") not in REVIEW_SCHEMAS:
        raise TaskError("Requires an existing explicit VLM/human review record")
    if review.get("decision") not in (
            "needs_revision","provisional_pass","pass","insufficient_evidence"):
        raise TaskError("Unrecognized review decision")
    canvas=[source["document"]["width"],source["document"]["height"]]
    image,sha=_png(actual_png,canvas)
    if review.get("artwork_png_sha256")!=sha:
        raise TaskError("Review and supplied actual PNG have different SHA-256")
    raw=review.get("issues")
    if type(raw) is not list or len(raw)>MAX_ISSUES:
        raise TaskError("Review issues exceed 30-item limit")
    if review["decision"]=="needs_revision" and not raw:
        raise TaskError("Needs-revision record must contain localized defects")
    by_id={s["id"]:s for s in source["subjects"]}
    seen=set()
    rows=[]
    for index,item in enumerate(raw):
        checked=_safe_issue(item,by_id,canvas)
        key=(checked["subject_id"],tuple(checked["roi"]),
             checked["observation"])
        if key in seen:
            raise TaskError("Duplicate revision issue")
        seen.add(key)
        rows.append(checked)
    if review["decision"] in ("pass","provisional_pass") and rows:
        raise TaskError("Reviewer pass contradicts unresolved localized issues")
    rows.sort(key=lambda r:(SEVERITY[r["severity"]],
                            -(r["roi"][2]*r["roi"][3]),
                            r["subject_id"],r["id"]))
    budget=math.floor(canvas[0]*canvas[1]*fraction)
    taken=0;tickets=[];deferred=[]
    for row in rows:
        area=row["roi"][2]*row["roi"][3]
        if len(tickets)>=cap or taken+area>budget:
            deferred.append({
                "subject_id":row["subject_id"],"issue_id":row["id"],
                "reason":"review_budget_exceeded",
            })
            continue
        taken+=area
        tickets.append({
            **row, "pixel_evidence":_roi_stats(image,row["roi"]),
            "next_action":"request_explicit_localized_native_repaint_plan",
            "native_operation_emitted":False,
            "human_review_required":True,
        })
    return {
        "schema":SCHEMA,
        "source_scene_v4_sha256":digest(source),
        "actual_png_sha256":sha,
        "source_review_sha256":digest(review),
        "tickets":tickets,
        "deferred_issues":deferred,
        "max_tickets":cap,"max_area_fraction":fraction,
        "total_selected_area_px":taken,
        "model_requests":0,"native_effects":"none",
        "image_upload_performed":False,
        "real_krita_provenance_verified":False,
        "independent_artwork_acceptance":False,
        "human_review_required":True,
    }


def verify_triage(report,scene,actual_png,review):
    """Replay immutable source/PNG/review bindings without any native effects."""
    if type(report) is not dict or report.get("schema")!=SCHEMA:
        raise TaskError("Unknown visual triage record")
    expected=triage(scene,actual_png,review,report.get("max_tickets"),
                    report.get("max_area_fraction"))
    if digest(expected)!=digest(report):
        raise TaskError("Visual triage changed relative to its reviewed evidence")
    return {
        "schema":"krita-agent-visual-triage-verification/1",
        "valid":True,"actual_png_sha256":expected["actual_png_sha256"],
        "tickets":len(expected["tickets"]),
        "native_effects":"none","artwork_accepted":False,
    }
