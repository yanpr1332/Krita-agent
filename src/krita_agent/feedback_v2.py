"""Finite, review-first feedback loop. Never generates or applies edits silently."""
import json
import math
from pathlib import Path
from .large_canvas import plan_overlay


def assess(before, goal, graph, max_error=0.005):
    from PIL import Image, ImageChops, ImageStat
    if type(max_error) not in (float,int) or not 0<=max_error<=1:
        raise ValueError("Invalid error tolerance")
    with Image.open(before) as a, Image.open(goal) as b:
        if a.size!=b.size or a.width*a.height>32000000:
            raise ValueError("Can only compare equal-size images <=32M pixels")
        # Conversion and metrics on explicit images; no semantic inference.
        aa=a.convert("RGBA")
        bb=b.convert("RGBA")
        diff=ImageChops.difference(aa,bb).convert("RGB")
        mean=ImageStat.Stat(diff).mean
        error=sum(mean)/(3*255)
        return {"error_normalized":round(error,8),
                "pixel_goal_met":error<=max_error,
                "difference_bbox":list(diff.getbbox()) if diff.getbbox() else None,
                "threshold":max_error}


def review_iteration(current,goal,graph,round_index,max_rounds=3,max_error=.005):
    if type(max_rounds) is not int or not 1<=max_rounds<=5:
        raise ValueError("max_rounds requires 1..5")
    if type(round_index) is not int or not 0<=round_index<max_rounds:
        raise ValueError("Round index out of bounds")
    evaluation=assess(current,goal,graph,max_error)
    result={"round":round_index+1,"max_rounds":max_rounds,
            "evaluation":evaluation,"next":"stop" if evaluation["pixel_goal_met"] else "manual_approval_required"}
    if result["next"]=="manual_approval_required":
        result["proposal"]=plan_overlay(current,goal,graph)
        result["note"]="You must inspect and explicitly approve each new revision. No automatic loop."
    return result


def write_review(review,filename):
    target=Path(filename)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as f:
        json.dump(review,f,indent=2,ensure_ascii=False)
    return str(target)
