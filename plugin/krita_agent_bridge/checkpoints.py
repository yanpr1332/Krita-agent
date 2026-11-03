"""Durable, explicit KRA checkpoints and recovery from verified fresh copies.

A checkpoint is one saved KRA plus an atomic manifest. A crashed stroke is
never assumed complete. Resume first restores the *known* KRA into a newly
named document, then submits only the suffix after its saved step boundary,
and only after explicit confirmation. No background replay on startup.
"""
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .atomic_io import atomic_replace
from krita import Krita
from .advanced_utils import storage_root, word

COMMANDS = frozenset(("checkpoint.create", "checkpoint.list", "checkpoint.inspect",
                      "checkpoint.restore", "checkpoint.resume"))
BASIC_RESUME_DENY = frozenset(("canvas.create", "document.open", "checkpoint.restore",
                               "checkpoint.resume", "job.submit"))


def _digest(path):
    sha = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def _fingerprint(steps):
    raw = json.dumps(steps, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _store(bridge):
    return storage_root(bridge, ".krita-agent-checkpoints")


def _manifest(bridge, identifier):
    try:
        key = uuid.UUID(word(identifier, "checkpoint id", 50)).hex
    except ValueError as exc:
        raise ValueError("Invalid checkpoint UUID") from exc
    path = _store(bridge) / (key + ".json")
    if path.stat().st_size > 2000000 or bridge.output_dir.resolve() not in path.resolve().parents:
        raise ValueError("Checkpoint metadata outside bounds")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("id") != key or data.get("schema") != 1:
        raise ValueError("Unknown checkpoint schema or ID")
    source = Path(data["path"]).resolve()
    if bridge.output_dir.resolve() not in source.parents or source.suffix.lower() != ".kra":
        raise ValueError("Checkpoint escaped the output sandbox")
    if not source.is_file() or _digest(source) != data.get("sha256"):
        raise ValueError("Checkpoint data missing or SHA-256 mismatch")
    return data


def _write_record(path, record):
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        atomic_replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def create(bridge, p):
    if bridge.active and not getattr(bridge, "_current_job_id", None):
        raise RuntimeError("Manual checkpoint not allowed while a job is active")
    identifier = uuid.uuid4().hex
    filename = p.get("path", "checkpoints/" + identifier + ".kra")
    target = Path(bridge._safe_path(filename, ".kra", overwrite=False))
    doc = bridge._doc()
    doc.waitForDone()
    prior_batch = doc.batchmode()
    doc.setBatchmode(True)
    try:
        ok = doc.saveAs(str(target))
    finally:
        doc.setBatchmode(prior_batch)
    if not ok or not target.is_file():
        raise RuntimeError("Krita failed to create a durable KRA checkpoint")
    import zipfile
    if not zipfile.is_zipfile(target):
        raise RuntimeError("Krita checkpoint is not a valid ZIP-based KRA archive")
    with zipfile.ZipFile(target) as archive:
        if not any(name.endswith("maindoc.xml") for name in archive.namelist()):
            raise RuntimeError("KRA checkpoint is missing maindoc.xml")
    job_id = getattr(bridge, "_current_job_id", None)
    job = bridge.jobs.get(job_id) if job_id else None
    after_step = (int(job["done"]) + 1) if job is not None else None
    record = {
        "schema": 1, "id": identifier, "created_at": datetime.now(timezone.utc).isoformat(),
        "path": str(target), "sha256": _digest(target),
        "document_name": doc.name(), "width": doc.width(), "height": doc.height(),
        "color_model": doc.colorModel(), "color_depth": doc.colorDepth(),
        "color_profile": doc.colorProfile(), "job_id": job_id,
        "after_step": after_step, "steps_sha256": _fingerprint(job["steps"]) if job else None,
        "policy": "immutable snapshot; never overwrite or automatically replay",
    }
    _write_record(_store(bridge) / (identifier + ".json"), record)
    return {k: v for k, v in record.items() if k != "steps_sha256"} | {
        "steps_sha256": record["steps_sha256"]}


def _steps(bridge, record):
    if record["job_id"] is None:
        raise ValueError("Checkpoint was created outside a job: no suffix to resume")
    job = bridge.jobs.get(record["job_id"])
    if job is None or _fingerprint(job["steps"]) != record["steps_sha256"]:
        raise ValueError("Original job absent or does not match checkpoint fingerprint")
    if job["state"] not in ("interrupted", "failed", "cancelled"):
        raise ValueError("Recovery requires a stopped/interrupted job")
    index = record.get("after_step")
    if type(index) is not int or not 0 <= index <= len(job["steps"]):
        raise ValueError("Invalid checkpoint step boundary")
    if index < 1 or job["steps"][index-1]["command"] != "checkpoint.create":
        raise ValueError("Checkpoint boundary is not a checkpoint step")
    steps = job["steps"][index:]
    if any(step["command"] in BASIC_RESUME_DENY for step in steps):
        raise ValueError("Suffix contains a non-resumable command")
    return steps


def _restore(bridge, record):
    """Open a new *copy*, so the interrupted in-memory document is untouched."""
    root = storage_root(bridge, "recovered")
    target = root / (record["id"] + "-" + uuid.uuid4().hex + ".kra")
    shutil.copyfile(record["path"], target)
    if _digest(target) != record["sha256"]:
        target.unlink(missing_ok=True)
        raise RuntimeError("Recovery copy integrity check failed")
    app = Krita.instance()
    win = app.activeWindow()
    if win is None:
        raise RuntimeError("No active Krita window")
    document = app.openDocument(str(target))
    if document is None:
        raise RuntimeError("Krita refused checkpoint KRA")
    win.addView(document)
    if document.width() != record["width"] or document.height() != record["height"]:
        raise RuntimeError("Recovery document dimensions differ from saved manifest")
    return {"path": str(target), "document": document.name()}


def execute(bridge, command, p):
    if command == "checkpoint.list":
        from pathlib import Path
        items = []
        for manifest in sorted(_store(bridge).glob("*.json"))[-200:]:
            try:
                record = json.loads(manifest.read_text(encoding="utf-8"))
                items.append({k: record.get(k) for k in ("id", "created_at", "document_name",
                              "job_id", "after_step", "path")})
            except (OSError, ValueError):
                continue
        return items
    if command == "checkpoint.create":
        return create(bridge, p)
    record = _manifest(bridge, p.get("id"))
    if command == "checkpoint.inspect":
        result = dict(record)
        result["integrity"] = "sha256_verified"
        if record["job_id"]:
            try:
                result["remaining_steps"] = len(_steps(bridge, record))
                result["resume_possible"] = True
            except ValueError as exc:
                result["remaining_steps"] = None
                result["resume_possible"] = False
                result["resume_blocked"] = str(exc)
        return result
    if p.get("confirm") is not True:
        raise ValueError("Explicit confirm=true required to open a recovery copy")
    if bridge.active:
        raise RuntimeError("Stop active jobs before restoring a checkpoint")
    steps = _steps(bridge, record) if command == "checkpoint.resume" else None
    recovered = _restore(bridge, record)
    if command == "checkpoint.restore":
        return {"restored": recovered, "replay": "none", "note": "Fresh copy only"}
    if command == "checkpoint.resume":
        if not steps:
            return {"restored": recovered, "remaining_steps": 0, "new_job": None}
        result = bridge._job("job.submit", {"steps": steps})
        return {"restored": recovered, "new_job": result,
                "source_job": record["job_id"], "from_step": record["after_step"],
                "explicitly_confirmed": True}
    raise ValueError("Unsupported checkpoint operation")
