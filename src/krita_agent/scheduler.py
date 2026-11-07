"""Durable orchestration of bounded Krita jobs with explicit safe continuation.

A batch is submitted only after its intent is durably written. Unknown effects
are never replayed. Continuation is allowed only from a known batch boundary
whose latest KRA checkpoint still exists and matches its recorded SHA-256.
"""
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .protocol import TaskError
from .workflow import compile_workflow

MAX_TOTAL_STEPS = 10000
MAX_WIRE_BYTES = 750000
LEDGER_SCHEMA = "krita-agent-long-job/1"


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_checkpoint(value):
    """Return a normalized checkpoint record or refuse continuation."""
    if not isinstance(value, dict):
        raise ValueError("Completed batch has no checkpoint result")
    filename = value.get("path")
    expected = value.get("sha256")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Checkpoint path is missing")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Checkpoint SHA-256 is invalid")
    path = Path(filename).expanduser().resolve()
    if path.suffix.lower() != ".kra" or not path.is_file():
        raise ValueError("Checkpoint KRA is missing")
    if _file_digest(path) != expected:
        raise ValueError("Checkpoint KRA SHA-256 mismatch")
    return {"path": str(path), "sha256": expected}


def split_workflow(spec, batch_steps=120):
    if not isinstance(spec, dict) or not isinstance(spec.get("steps"), list):
        raise TaskError("Long workflow requires an explicit steps array")
    if type(batch_steps) is not int or not 1 <= batch_steps <= 380:
        raise TaskError("Batch size must be in [1,380]")
    raw = spec["steps"]
    if not 1 <= len(raw) <= MAX_TOTAL_STEPS:
        raise TaskError("Long workflow accepts 1..10000 steps")
    prepared = []
    for step in raw:
        compiled = compile_workflow({"steps": [step]})[0]
        encoded = json.dumps(compiled, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_WIRE_BYTES - 4096:
            raise TaskError("A single step exceeds IPC budget; split stroke intentionally")
        prepared.append(compiled)
    batches = []
    cursor = []
    for step in prepared:
        proposed = cursor + [step, {"command": "checkpoint.create", "parameters": {}}]
        encoded_size = len(json.dumps(proposed, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        if cursor and (len(cursor) >= batch_steps or encoded_size > MAX_WIRE_BYTES):
            batches.append(cursor + [{"command": "checkpoint.create", "parameters": {}}])
            cursor = []
        cursor.append(step)
    if cursor:
        batches.append(cursor + [{"command": "checkpoint.create", "parameters": {}}])
    return batches


class Ledger:
    """Single-writer atomic ledger."""
    def __init__(self, directory, identifier=None):
        self.root = Path(directory).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.id = identifier or uuid.uuid4().hex
        if len(self.id) != 32 or any(c not in "0123456789abcdef" for c in self.id):
            raise ValueError("Invalid ledger ID")
        self.path = self.root / ("long-job-" + self.id + ".json")

    def write(self, value):
        temp = self.path.with_name(self.path.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            with temp.open("w", encoding="utf-8") as stream:
                json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            for attempt in range(8):
                try:
                    os.replace(temp, self.path)
                    break
                except PermissionError:
                    if attempt == 7:
                        raise
                    time.sleep(0.05)
        finally:
            temp.unlink(missing_ok=True)

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))


def _execute_batches(client, batches, ledger, record, start_index=0,
                     poll_interval=0.3, terminal_timeout=1800, on_progress=None):
    for index in range(start_index, len(batches)):
        batch = batches[index]
        record["state"] = "submitting"
        record["current"] = {
            "index": index,
            "batch_sha256": _digest(batch),
            "job_id": None,
            "state": "unknown",
        }
        ledger.write(record)
        try:
            result = client.submit(batch)
            record["current"]["job_id"] = result["id"]
            record["current"]["state"] = "submitted"
            record["state"] = "running"
            ledger.write(record)
            started = time.monotonic()
            while True:
                if time.monotonic() - started > terminal_timeout:
                    raise TimeoutError("Sub-job completion not confirmed")
                status = client.request("job.status", id=result["id"])
                record["current"]["done"] = status.get("done")
                record["current"]["state"] = status.get("state")
                ledger.write(record)
                if on_progress is not None:
                    on_progress({"batch": index + 1, "total_batches": len(batches), "job": status})
                if status.get("state") == "completed":
                    checkpoint = _verified_checkpoint(status.get("last_result"))
                    record["completed"].append({
                        "index": index,
                        "job_id": result["id"],
                        "checkpoint": checkpoint,
                        "batch_sha256": _digest(batch),
                        "steps": len(batch),
                        "elapsed_seconds": round(time.monotonic() - started, 6),
                    })
                    record["next_batch"] = index + 1
                    record["current"] = None
                    record["state"] = "ready_for_next_batch"
                    ledger.write(record)
                    break
                if status.get("state") in ("failed", "cancelled", "interrupted"):
                    raise RuntimeError(
                        "Sub-job ended in " + str(status.get("state")) +
                        "; inspect the saved KRA checkpoint before taking further action"
                    )
                time.sleep(poll_interval)
        except Exception as exc:
            record["state"] = "unknown_needs_review"
            record["error"] = str(exc)
            try:
                ledger.write(record)
            except OSError as storage_error:
                record["ledger_write_error"] = str(storage_error)
            return {
                "state": record["state"],
                "ledger": str(ledger.path),
                "completed_batches": len(record["completed"]),
                "error": str(exc),
            }

    record["state"] = "completed"
    record["current"] = None
    ledger.write(record)
    return {"state": "completed", "ledger": str(ledger.path), "batches": len(batches)}


def run(client, spec, ledger_dir, batch_steps=120, poll_interval=0.3,
        terminal_timeout=1800, on_progress=None):
    """Start a new serial run. Transport ambiguity is never retried."""
    batches = split_workflow(spec, batch_steps)
    ledger = Ledger(ledger_dir)
    record = {
        "schema": LEDGER_SCHEMA,
        "id": ledger.id,
        "state": "prepared",
        "source_sha256": _digest(spec),
        "batch_steps": batch_steps,
        "batch_count": len(batches),
        "next_batch": 0,
        "completed": [],
        "current": None,
        "resume_count": 0,
        "policy": "no auto replay of uncertain native effects",
    }
    ledger.write(record)
    return _execute_batches(
        client, batches, ledger, record, 0,
        poll_interval=poll_interval, terminal_timeout=terminal_timeout,
        on_progress=on_progress,
    )


def resume(client, spec, ledger_path, confirm=False, poll_interval=0.3,
           terminal_timeout=1800, on_progress=None):
    """Continue only from a known checkpoint boundary after explicit approval.

    Ledgers left in submitting/running/unknown states are deliberately refused.
    They require manual inspection because a native effect may have happened.
    """
    if confirm is not True:
        raise ValueError("Continuation requires explicit --confirm")
    path = Path(ledger_path).expanduser().resolve()
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != LEDGER_SCHEMA:
        raise ValueError("Not a recognized long-job ledger")
    if record.get("state") not in ("prepared", "ready_for_next_batch"):
        raise ValueError("Ledger is not at a known safe boundary; inspect manually, never replay")
    if record.get("current") is not None:
        raise ValueError("Ledger has an unresolved current batch; automatic continuation is refused")
    if record.get("source_sha256") != _digest(spec):
        raise ValueError("Workflow differs from the original long-job source")
    batch_steps = record.get("batch_steps")
    if type(batch_steps) is not int:
        raise ValueError("Ledger predates resumable batch metadata")
    batches = split_workflow(spec, batch_steps)
    if record.get("batch_count") != len(batches):
        raise ValueError("Workflow batch count no longer matches the ledger")
    completed = record.get("completed")
    next_batch = record.get("next_batch")
    if not isinstance(completed, list) or type(next_batch) is not int:
        raise ValueError("Ledger completion metadata is malformed")
    if next_batch != len(completed) or not 0 <= next_batch <= len(batches):
        raise ValueError("Ledger does not describe a contiguous completed prefix")
    for index, item in enumerate(completed):
        if not isinstance(item, dict) or item.get("index") != index:
            raise ValueError("Completed batches are not a contiguous prefix")
        if item.get("batch_sha256") != _digest(batches[index]):
            raise ValueError("A completed batch no longer matches the original workflow")
        if item.get("steps") != len(batches[index]):
            raise ValueError("Completed batch step count mismatch")
    if completed:
        _verified_checkpoint(completed[-1].get("checkpoint"))
    identifier = record.get("id")
    ledger = Ledger(path.parent, identifier)
    if ledger.path != path:
        raise ValueError("Ledger filename does not match its embedded ID")
    record["resume_count"] = int(record.get("resume_count", 0)) + 1
    record["last_resumed_at"] = datetime.now(timezone.utc).isoformat()
    ledger.write(record)
    if next_batch == len(batches):
        record["state"] = "completed"
        ledger.write(record)
        return {"state": "completed", "ledger": str(ledger.path), "batches": len(batches)}
    return _execute_batches(
        client, batches, ledger, record, next_batch,
        poll_interval=poll_interval, terminal_timeout=terminal_timeout,
        on_progress=on_progress,
    )


def inspect_ledger(path):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("schema") != LEDGER_SCHEMA:
        raise ValueError("Not a recognized long-job ledger")
    return record
