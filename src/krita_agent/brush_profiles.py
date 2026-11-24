"""Opt-in, evidence-backed native brush calibration catalogue."""
import hashlib
import json
import os
import re
import uuid
from pathlib import Path

CATEGORIES = frozenset({"ink", "sketch", "paint", "texture", "erase", "mask"})
PROFILE_SCHEMA = "krita-agent-brush-profile/1"
TASK_SCHEMA = "krita-agent-brush-calibration-task/2"
MAX_EVIDENCE_BYTES = 5_000_000
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def calibration_task(preset, size=24):
    """Build a native calibration matrix; visual evidence still needs review."""
    if not isinstance(preset, str) or not 1 <= len(preset) <= 120:
        raise ValueError("Invalid preset")
    if type(size) not in (int, float) or not 0.1 <= size <= 500:
        raise ValueError("Invalid brush size")

    steps = [
        {"command": "canvas.create", "parameters": {
            "width": 640, "height": 640, "name": "Krita Agent Brush Calibration",
        }},
        {"command": "layer.create", "parameters": {"name": "01 - Pressure ladder"}},
        {"command": "brush.configure", "parameters": {
            "preset": preset, "size": size, "opacity": 0.9,
            "color": "#294964", "pressure_enabled": True,
        }},
    ]
    pressure_levels = (0.1, 0.3, 0.6, 0.9)
    for row, force in enumerate(pressure_levels):
        y = 65 + row * 66
        steps.append({"command": "draw.stroke", "parameters": {
            "mode": "auto",
            "points": [
                {"x": 60, "y": y, "pressure": force, "time_ms": 0},
                {"x": 310, "y": y, "pressure": force, "time_ms": 80},
                {"x": 560, "y": y, "pressure": force, "time_ms": 160},
            ],
        }})

    steps.extend([
        {"command": "layer.create", "parameters": {"name": "02 - Pressure ramps"}},
        {"command": "brush.configure", "parameters": {
            "preset": preset, "size": size, "opacity": 0.9,
            "color": "#a85f38", "pressure_enabled": True,
        }},
    ])
    for y, levels in (
        (360, (0.05, 0.25, 0.5, 0.75, 0.95)),
        (420, (0.95, 0.75, 0.5, 0.25, 0.05)),
    ):
        steps.append({"command": "draw.stroke", "parameters": {
            "mode": "auto",
            "points": [
                {"x": 60 + index * 125, "y": y,
                 "pressure": force, "time_ms": index * 45}
                for index, force in enumerate(levels)
            ],
        }})

    steps.append({"command": "layer.create", "parameters": {
        "name": "03 - Nominal brush size ladder",
    }})
    size_levels = tuple(dict.fromkeys((
        max(0.1, round(size * 0.5, 3)),
        round(float(size), 3),
        min(500.0, round(size * 2.0, 3)),
    )))
    for index, brush_size in enumerate(size_levels):
        y = 500 + index * 42
        steps.extend([
            {"command": "brush.configure", "parameters": {
                "preset": preset, "size": brush_size, "opacity": 0.9,
                "color": "#356b4a", "pressure_enabled": True,
            }},
            {"command": "draw.stroke", "parameters": {
                "mode": "auto",
                "points": [
                    {"x": 60, "y": y, "pressure": 0.6, "time_ms": 0},
                    {"x": 310, "y": y, "pressure": 0.6, "time_ms": 80},
                    {"x": 560, "y": y, "pressure": 0.6, "time_ms": 160},
                ],
            }},
        ])

    export_path = "brush-calibration/" + uuid.uuid4().hex + ".png"
    steps.append({"command": "document.export", "parameters": {
        "path": export_path, "overwrite": False,
    }})
    return {
        "schema": TASK_SCHEMA,
        "preset": preset,
        "nominal_size": float(size),
        "size_levels": list(size_levels),
        "pressure_levels": list(pressure_levels),
        "checks": [
            {
                "id": "pressure_ladder",
                "review": "Compare line width and opacity across four constant-pressure rows.",
            },
            {
                "id": "pressure_ramps",
                "review": "Check smooth response in both increasing and decreasing pressure strokes.",
            },
            {
                "id": "size_ladder",
                "review": "Confirm the three nominal brush sizes produce distinct widths.",
            },
        ],
        "manual_review_required": True,
        "steps": steps,
        "purpose": (
            "Native brush-engine calibration fixture. Exported pixels and the "
            "installed preset must be inspected by a human before recording a profile."
        ),
    }


def record_profile(directory, record, evidence_path):
    required = (
        "preset", "build", "category", "pressure_size",
        "pressure_opacity", "confidence",
    )
    if not isinstance(record, dict) or any(key not in record for key in required):
        raise ValueError("Incomplete brush calibration record")
    if record["category"] not in CATEGORIES:
        raise ValueError("Unknown brush category")
    if not isinstance(record["preset"], str) or not 1 <= len(record["preset"]) <= 120:
        raise ValueError("Preset name invalid")
    if not isinstance(record["build"], str) or not record["build"].strip():
        raise ValueError("Build identifier required")
    for key in ("pressure_size", "pressure_opacity"):
        if type(record[key]) is not bool:
            raise ValueError(key + " requires boolean")
    confidence = record["confidence"]
    if type(confidence) not in (float, int) or not 0 <= confidence <= 1:
        raise ValueError("Confidence outside [0,1]")

    evidence = Path(evidence_path).expanduser().resolve()
    if (not evidence.is_file()
            or not 1 <= evidence.stat().st_size <= MAX_EVIDENCE_BYTES):
        raise ValueError("Missing, empty or oversized evidence file")
    sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    destination = Path(directory).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    profile = {
        "schema": PROFILE_SCHEMA,
        **record,
        "evidence_sha256": sha,
        "evidence_path": str(evidence),
        "status": "manually_reviewed",
        "id": uuid.uuid4().hex,
    }
    target = destination / (profile["id"] + ".json")
    with target.open("x", encoding="utf-8") as stream:
        json.dump(profile, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    return profile


def _valid_profile(profile):
    required = (
        "preset", "build", "category", "pressure_size",
        "pressure_opacity", "confidence", "evidence_path", "evidence_sha256",
    )
    if not isinstance(profile, dict) or profile.get("schema") != PROFILE_SCHEMA:
        return False
    if any(key not in profile for key in required):
        return False
    if profile.get("status") != "manually_reviewed":
        return False
    if not isinstance(profile["preset"], str) or not 1 <= len(profile["preset"]) <= 120:
        return False
    if not isinstance(profile["build"], str) or not profile["build"].strip():
        return False
    if profile["category"] not in CATEGORIES:
        return False
    if any(type(profile[key]) is not bool
           for key in ("pressure_size", "pressure_opacity")):
        return False
    confidence = profile["confidence"]
    if type(confidence) not in (float, int) or not 0 <= confidence <= 1:
        return False
    if (not isinstance(profile["evidence_path"], str)
            or not isinstance(profile["evidence_sha256"], str)
            or not SHA256_RE.fullmatch(profile["evidence_sha256"])):
        return False
    return True


def find_profiles(directory, build=None, category=None, min_confidence=0):
    if (type(min_confidence) not in (int, float)
            or not 0 <= min_confidence <= 1):
        raise ValueError("Invalid min_confidence")
    if category is not None and category not in CATEGORIES:
        raise ValueError("Unknown brush category")
    root = Path(directory).expanduser()
    if not root.is_dir():
        return []
    profiles = []
    for path in sorted(root.glob("*.json")):
        try:
            if path.is_symlink() or path.stat().st_size > 250_000:
                continue
            profile = json.loads(path.read_text(encoding="utf-8"))
            if not _valid_profile(profile):
                continue
            if build and profile["build"] != build:
                continue
            if category and profile["category"] != category:
                continue
            if profile["confidence"] < min_confidence:
                continue
            evidence = Path(profile["evidence_path"])
            if (not evidence.is_file()
                    or not 1 <= evidence.stat().st_size <= MAX_EVIDENCE_BYTES):
                continue
            if hashlib.sha256(evidence.read_bytes()).hexdigest() != profile["evidence_sha256"]:
                continue
            profiles.append(profile)
        except (ValueError, OSError, TypeError, KeyError):
            continue
    return sorted(profiles, key=lambda item: (-item["confidence"], item["preset"]))


def choose(directory, build, category, min_confidence=0.8):
    found = find_profiles(directory, build, category, min_confidence)
    if not found:
        raise ValueError("No manually reviewed brush profile meets requirements")
    return found[0]
