"""Explicit long-stroke segmentation; cannot preserve native continuous semantics."""
from .protocol import TaskError, points, MAX_POINTS


def segment_long_stroke(samples, segment_points=1500, allow_seams=False):
    """Return bounded strokes with a one-point join; never silently degrade.

    The caller must explicitly allow new brush startup events and separate
    native undo steps. StrokePoint continuity and texture are not guaranteed.
    """
    if allow_seams is not True:
        raise TaskError("Long stroke splitting requires allow_seams=true")
    if type(segment_points) is not int or not 2 <= segment_points <= MAX_POINTS:
        raise TaskError("segment_points must be 2..2048")
    if not isinstance(samples,list) or not 2 <= len(samples) <= 100000:
        raise TaskError("long stroke must have 2..100000 raw points")
    normalized=[dict(value, time_ms=value.get("time_ms",index*16)) if isinstance(value,dict) else value
                for index,value in enumerate(samples)]
    result=[]
    start=0
    last_time=-1
    while start<len(normalized)-1:
        end=min(len(normalized),start+segment_points)
        chunk=points(normalized[start:end])
        if chunk[0]["time_ms"]<last_time:
            raise TaskError("time_ms must be nondecreasing across all segments")
        last_time=chunk[-1]["time_ms"]
        result.append(chunk)
        if end==len(samples):
            break
        start=end-1  # shared endpoint only
    return {"segments":result,"original_points":len(samples),
            "segment_count":len(result),
            "warning":"Separate native strokes: possible joins, texture seams and multiple Undo steps"}


def as_steps(samples, segment_points=1500, mode="auto", allow_seams=False):
    if mode not in ("auto","continuous","segmented"):
        raise TaskError("Invalid brush mode")
    planned=segment_long_stroke(samples,segment_points,allow_seams)
    return [{"command":"draw.stroke","parameters":{"points":chunk,"mode":mode}}
            for chunk in planned["segments"]],planned
