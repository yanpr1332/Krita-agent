"""Read-only performance summaries and portable operational budgets."""
import math
import statistics
from pathlib import Path
import json

DEFAULTS={"max_ipc_bytes":750000,"max_steps_per_batch":120,
          "max_native_points":2048,"max_tile_pixels":1024*1024,
          "max_changed_tile_pixels":500000}


def summarize_job_snapshots(states):
    if not isinstance(states,list):
        raise ValueError("Expected list")
    durations=[]
    for state in states:
        metrics=state.get("metrics",{}) if isinstance(state,dict) else {}
        if type(metrics.get("last_step_ms")) in (int,float):
            value=metrics["last_step_ms"]
            if math.isfinite(value) and value>=0:
                durations.append(value)
    return {"samples":len(durations),
            "mean_step_ms":round(statistics.mean(durations),3) if durations else None,
            "p95_step_ms":round(sorted(durations)[math.ceil(len(durations)*.95)-1],3) if durations else None,
            "max_step_ms":max(durations) if durations else None,
            "budgets":DEFAULTS}


def summarize_ledger(filename):
    job=json.loads(Path(filename).read_text(encoding="utf-8"))
    return {"state":job.get("state"),"completed_batches":len(job.get("completed",[])),
            "batch_count":job.get("batch_count"),
            "needs_review":job.get("state")=="unknown_needs_review"}
