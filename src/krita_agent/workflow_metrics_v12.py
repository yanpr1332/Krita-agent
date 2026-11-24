"""Privacy-safe, hash-chained timing and plan diagnostics for Round 12."""
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

SCHEMA = "krita-agent-workflow-operations/1"
LOG_NAME = "operation-metrics-v12.jsonl"
MAX_LOG_BYTES = 8 * 1024 * 1024
MAX_EVENTS = 50000
ZERO_HASH = "0" * 64
OPERATIONS = frozenset({
    "plan", "approve_plan", "paint", "paint_stage", "export_native",
    "record_artwork", "verify_reopen", "critique", "critique_v11",
    "propose_revision", "approve_revision", "apply_revision", "prepare_delivery",
})
_EVENT_KEYS = frozenset({
    "schema", "sequence", "operation", "started_at", "ended_at", "duration_ms",
    "outcome", "error_type", "run_id", "status_before", "status_after",
    "version_before", "version_after", "stage_cursor_before", "stage_cursor_after",
    "previous_sha256", "event_sha256",
})


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _snapshot(root):
    try:
        root = Path(root).expanduser().resolve()
        path = root / "creative-workflow.json"
        if path.is_symlink() or not path.is_file():
            return None
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("schema") != "krita-agent-creative-workflow/1":
            return None
        staged = record.get("staged", {})
        cursor = staged.get("next_stage") if isinstance(staged, dict) else None
        version = record.get("version")
        return {
            "run_id": record.get("id") if isinstance(record.get("id"), str) else None,
            "status": record.get("status") if isinstance(record.get("status"), str) else None,
            "version": version if type(version) is int and version >= 0 else None,
            "stage_cursor": cursor if type(cursor) is int and cursor >= 0 else None,
        }
    except (OSError, ValueError, TypeError):
        return None


def _lock(stream):
    if os.name == "nt":  # Existing workflow contract is single-writer.
        yield
        return
    import fcntl
    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _decode_events(raw):
    if len(raw) > MAX_LOG_BYTES or (raw and not raw.endswith(b"\n")):
        raise ValueError("metrics log size or record boundary is invalid")
    lines = raw.splitlines()
    if len(lines) > MAX_EVENTS:
        raise ValueError("metrics log exceeds event limit")
    events, previous = [], ZERO_HASH
    for index, line in enumerate(lines, 1):
        row = json.loads(line.decode("utf-8"))
        if not isinstance(row, dict) or set(row) != _EVENT_KEYS:
            raise ValueError("metrics event schema mismatch")
        stored = row.pop("event_sha256")
        if (row.get("schema") != SCHEMA or row.get("sequence") != index
                or row.get("previous_sha256") != previous):
            raise ValueError("metrics hash-chain sequence mismatch")
        if stored != hashlib.sha256(_canonical(row)).hexdigest():
            raise ValueError("metrics event digest mismatch")
        row["event_sha256"] = stored
        events.append(row)
        previous = stored
    return events


def append_operation(root, operation, started_ns, started_at, outcome,
                     error_type=None, before=None, after=None):
    if operation not in OPERATIONS or outcome not in ("returned", "raised"):
        return False
    root = Path(root).expanduser().resolve()
    manifest = root / "creative-workflow.json"
    if manifest.is_symlink() or not manifest.is_file():
        return False
    path = root / LOG_NAME
    if path.is_symlink():
        raise ValueError("metrics log must not be a symlink")
    before, after = before or {}, after or {}
    safe_error = error_type[:80] if (
        isinstance(error_type, str) and error_type.replace("_", "").isalnum()
    ) else None
    event = {
        "schema": SCHEMA, "sequence": 0, "operation": operation,
        "started_at": started_at, "ended_at": _utc(),
        "duration_ms": round(max(0, time.perf_counter_ns() - started_ns) / 1_000_000, 3),
        "outcome": outcome, "error_type": safe_error,
        "run_id": after.get("run_id") or before.get("run_id"),
        "status_before": before.get("status"), "status_after": after.get("status"),
        "version_before": before.get("version"), "version_after": after.get("version"),
        "stage_cursor_before": before.get("stage_cursor"),
        "stage_cursor_after": after.get("stage_cursor"),
        "previous_sha256": ZERO_HASH,
    }
    from contextlib import contextmanager
    with path.open("a+b") as stream:
        @contextmanager
        def locked():
            yield from _lock(stream)
        with locked():
            stream.seek(0)
            existing = _decode_events(stream.read(MAX_LOG_BYTES + 1))
            if len(existing) >= MAX_EVENTS:
                raise ValueError("metrics event limit reached")
            event["sequence"] = len(existing) + 1
            event["previous_sha256"] = existing[-1]["event_sha256"] if existing else ZERO_HASH
            event["event_sha256"] = hashlib.sha256(_canonical(event)).hexdigest()
            stream.seek(0, os.SEEK_END)
            stream.write(_canonical(event) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
    return True


def _plan_metrics(root, record):
    entry = record.get("artifacts", {}).get("compiled")
    if not isinstance(entry, dict):
        return {"status": "unavailable", "planned_only": True}
    root = Path(root).resolve()
    candidate = root / entry.get("path", "")
    if candidate.is_symlink():
        return {"status": "unavailable", "planned_only": True}
    path = candidate.resolve()
    if root not in path.parents or not path.is_file():
        return {"status": "unavailable", "planned_only": True}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != entry.get("sha256"):
        return {"status": "source_changed", "planned_only": True}
    try:
        compiled = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "unavailable", "planned_only": True}
    steps = compiled.get("steps", [])
    if not isinstance(steps, list):
        return {"status": "invalid", "planned_only": True}
    brush = [s.get("parameters", {}) for s in steps
             if isinstance(s, dict) and s.get("command") == "brush.configure"]
    strokes = [s.get("parameters", {}) for s in steps
               if isinstance(s, dict) and s.get("command") == "draw.stroke"]
    sizes, colors, opacities, presets, pressure = set(), set(), set(), set(), []
    for item in brush:
        if isinstance(item.get("size"), (int, float)) and not isinstance(item.get("size"), bool):
            sizes.add(round(float(item["size"]), 3))
        if isinstance(item.get("color"), str):
            colors.add(item["color"].casefold())
        if isinstance(item.get("opacity"), (int, float)) and not isinstance(item.get("opacity"), bool):
            opacities.add(round(float(item["opacity"]), 3))
        if isinstance(item.get("preset"), str):
            presets.add(item["preset"])
    for stroke in strokes:
        for point in stroke.get("points", []):
            value = point.get("pressure") if isinstance(point, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1:
                pressure.append(float(value))
    return {
        "status": "verified", "planned_only": True, "native_steps": len(steps),
        "planned_strokes": len(strokes), "brush_configurations": len(brush),
        "distinct_sizes": len(sizes), "distinct_colors": len(colors),
        "distinct_opacities": len(opacities), "distinct_presets": len(presets),
        "pressure_samples": len(pressure),
        "pressure_min": round(min(pressure), 4) if pressure else None,
        "pressure_max": round(max(pressure), 4) if pressure else None,
        "pressure_spread": round(max(pressure) - min(pressure), 4) if pressure else None,
    }


def summarize(root, record=None):
    root = Path(root).expanduser().resolve()
    if record is None:
        try:
            record = json.loads((root / "creative-workflow.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            record = {}
    path = root / LOG_NAME
    try:
        if path.is_symlink():
            raise ValueError("metrics log is a symlink")
        events = _decode_events(path.read_bytes() if path.is_file() else b"")
    except (OSError, ValueError, TypeError) as exc:
        return {
            "schema": SCHEMA, "integrity": "corrupt", "event_count": 0,
            "error_type": type(exc).__name__, "operations": [],
            "planning_profile": {}, "compiled_plan": {"status": "unavailable"},
            "artwork_acceptance": "not_evaluated_by_metrics",
        }
    grouped = {}
    for event in events:
        grouped.setdefault(event["operation"], []).append(event)
    operations = []
    for name, rows in sorted(grouped.items()):
        durations = sorted(row["duration_ms"] for row in rows)
        operations.append({
            "operation": name, "count": len(rows),
            "raised": sum(row["outcome"] == "raised" for row in rows),
            "total_ms": round(sum(durations), 3),
            "mean_ms": round(sum(durations) / len(durations), 3),
            "p95_ms": round(durations[max(0, math.ceil(len(durations) * .95) - 1)], 3),
            "max_ms": round(max(durations), 3),
        })
    brief = record.get("brief", {}) if isinstance(record, dict) else {}
    return {
        "schema": SCHEMA, "integrity": "verified" if events else "empty",
        "event_count": len(events),
        "raised_invocations": sum(row["outcome"] == "raised" for row in events),
        "workflow": {"status": record.get("status"), "version": record.get("version")},
        "planning_profile": {
            "complexity": brief.get("complexity"),
            "time_budget_minutes": brief.get("time_budget_minutes"),
            "max_native_steps": brief.get("max_native_steps"),
        },
        "compiled_plan": _plan_metrics(root, record),
        "operations": operations,
        "timing_note": "Command timings can be nested; do not sum them as wall-clock run time.",
        "artwork_acceptance": "not_evaluated_by_metrics",
    }


def measure_operation(operation):
    if operation not in OPERATIONS:
        raise ValueError("Unknown workflow operation")
    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            root = getattr(self, "root", None)
            before = _snapshot(root) if root is not None else None
            started_ns, started_at = time.perf_counter_ns(), _utc()
            outcome, error_type = "returned", None
            try:
                return function(self, *args, **kwargs)
            except BaseException as exc:
                outcome, error_type = "raised", type(exc).__name__
                raise
            finally:
                if root is not None and before is not None:
                    try:
                        append_operation(root, operation, started_ns, started_at,
                                         outcome, error_type, before, _snapshot(root))
                    except Exception:
                        pass
        return wrapped
    return decorate
