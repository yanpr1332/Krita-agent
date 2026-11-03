"""Atomic job snapshots under the Bridge output root.

Never auto-replay a potentially partially executed native brush stroke.
Snapshots contain only task metadata, never session credentials.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .atomic_io import atomic_replace


class Journal:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        try:
            uuid.UUID(str(key))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Job ID is not a UUID")
        return self.root / (str(key) + ".json")

    def save(self, job):
        filename = self._path(job["id"])
        record = {k: v for k, v in job.items() if k not in ("_runtime",)}
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = filename.with_name(filename.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            atomic_replace(tmp, filename)
        finally:
            tmp.unlink(missing_ok=True)

    def load(self):
        jobs = {}
        for filename in sorted(self.root.glob("*.json"))[-500:]:
            try:
                data = json.loads(filename.read_text(encoding="utf-8"))
                key = data.get("id")
                if self._path(key) != filename or not isinstance(data.get("steps"), list):
                    continue
                # Restart never means automatic execution or replay.
                if data.get("state") in ("queued", "running", "paused"):
                    data["state"] = "interrupted"
                    data["error"] = ("Interrupted before clean completion; the last native "
                                     "step may have applied. Manual inspection required.")
                    data["recovery_required"] = True
                    self.save(data)
                jobs[key] = data
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                # Bad snapshots are not interpreted as runnable jobs.
                continue
        return jobs

    def history(self, key):
        return self._path(key).read_text(encoding="utf-8")
