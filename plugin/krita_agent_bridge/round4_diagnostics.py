"""Read-only Bridge limits, progress metrics and revision capabilities."""
from .round4_layers import MAX_TILE_AREA

COMMANDS=frozenset(("runtime.limits","job.metrics","brush.calibration.support"))


def execute(bridge,command,p):
    if command=="runtime.limits":
        doc=bridge._doc()
        return {"protocol":1,"max_frame":bridge.MAX_FRAME if hasattr(bridge,"MAX_FRAME") else 1024*1024,
                "max_steps":400,"max_stroke_points":2048,
                "max_tile_area":MAX_TILE_AREA,
                "document":{"width":doc.width(),"height":doc.height(),
                            "model":doc.colorModel(),"depth":doc.colorDepth()},
                "continuous_stroke":bool(bridge._capabilities()["symbols"].get("Node.paintPolylineStroke"))}
    if command=="job.metrics":
        job_id=p.get("id")
        job=bridge.jobs.get(job_id)
        if job is None:
            raise ValueError("Job ID not found")
        return {"id":job_id,"state":job["state"],
                "completed_steps":job["done"],"total_steps":job["total"],
                "metrics":job.get("metrics",{}),
                "note":"Step timing is measured on GUI thread, not image quality."}
    if command=="brush.calibration.support":
        return {"protocol":"manual-calibration/1",
                "recording":"offline controller; no hidden automated quality claims"}
    raise ValueError("Unknown diagnostics command")
