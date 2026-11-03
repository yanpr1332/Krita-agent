"""Controller-side local job plan archives, without secrets or auto replay."""
import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone


def archive_plan(steps, output_dir):
    """Persist compiled plan for later inspection, not automatic resubmission."""
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    identifier = uuid.uuid4().hex
    filename = root / ("workflow-" + identifier + ".json")
    payload = {"id": identifier, "created_at": datetime.now(timezone.utc).isoformat(),
               "replay_policy": "manual_only", "steps": steps}
    temp = filename.with_suffix(".tmp")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, allow_nan=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        temp.replace(filename)
    finally:
        temp.unlink(missing_ok=True)
    return {"plan_id": identifier, "path": str(filename), "steps": len(steps)}
