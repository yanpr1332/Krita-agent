"""Round 10 — immutable, licensed, versioned technique profiles.

A profile is an explicit, reviewable recipe; it does NOT retrain a model.
It cannot claim human-verified skill merely because its JSON validates.
"""
import json
import os
import re
from copy import deepcopy
from pathlib import Path

from .protocol import TaskError, brush_settings, label
from .material_rendering import validate_render
from .scene_v3 import digest
from .scene_v4 import validate_scene_v4

PROFILE_SCHEMA = "krita-agent-technique/1"
STATUS = ("hypothesis", "native_tested", "human_reviewed")
RIGHTS = ("owned", "public_domain", "licensed", "explicit_permission")
ID_RE = re.compile(r"[a-z][a-z0-9_-]{0,23}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _id(value, what):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise TaskError("Invalid technique " + what)
    return value


def _string_list(value, what, minimum=0, maximum=12):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise TaskError("Technique " + what + " requires bounded list")
    entries = [label(x, what, 80) for x in value]
    if len(set(entries)) != len(entries):
        raise TaskError("Duplicate technique " + what)
    return entries


def validate_technique(profile):
    if not isinstance(profile, dict) or set(profile) - {
            "schema", "id", "version", "title", "materials", "subjects",
            "phases", "intent_kinds", "render", "brush", "provenance",
            "status", "limitations", "builds", "evidence"}:
        raise TaskError("Invalid technique profile object")
    if profile.get("schema") != PROFILE_SCHEMA:
        raise TaskError("Unknown technique profile schema")
    from .protocol import integer
    version = integer(profile.get("version"), "technique version", 1, 9999)
    provenance = profile.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != {
            "source_id", "source_sha256", "rights_basis", "source_note"}:
        raise TaskError("Technique provenance requires source, hash and explicit rights")
    src_sha = provenance["source_sha256"]
    if not isinstance(src_sha, str) or not HEX64.fullmatch(src_sha):
        raise TaskError("Technique provenance SHA-256 must be 64 lowercase hex chars")
    if provenance["rights_basis"] not in RIGHTS:
        raise TaskError("Technique reference rights basis must be authorized")
    kinds = profile.get("intent_kinds", ["gesture", "coverage", "accents"])
    if not isinstance(kinds, list) or not kinds or any(
            v not in ("gesture", "coverage", "accents") for v in kinds) or len(set(kinds)) != len(kinds):
        raise TaskError("Invalid technique intent kinds")
    technique = profile.get("render")
    if not isinstance(technique, dict):
        raise TaskError("Technique requires an actual Round 8 render recipe")
    # Round 8 render validation; normalized values must remain bounded.
    recipe = validate_render(technique, kinds[0])
    brush = brush_settings(profile.get("brush"))
    status = profile.get("status", "hypothesis")
    if status not in STATUS:
        raise TaskError("Unknown technique evidence status")
    evidence = _string_list(profile.get("evidence", []), "evidence", 0, 8)
    if status != "hypothesis" and not evidence:
        raise TaskError("Native/human-tested profile must cite actual evidence")
    phases = _string_list(profile.get("phases", ["material", "detail"]), "phases", 1, 6)
    if any(p not in ("sketch", "block_in", "form", "material", "detail", "polish")
           for p in phases):
        raise TaskError("Technique phase outside v4 contract")
    builds = _string_list(profile.get("builds", []), "builds", 0, 8)
    return {
        "schema": PROFILE_SCHEMA,
        "id": _id(profile.get("id"), "ID"), "version": version,
        "title": label(profile.get("title"), "technique title", 120),
        "materials": _string_list(profile.get("materials"), "materials", 1, 12),
        "subjects": _string_list(profile.get("subjects", []), "subjects", 0, 12),
        "phases": phases, "intent_kinds": kinds,
        "render": recipe, "brush": brush,
        "provenance": {
            "source_id": _id(provenance["source_id"], "source ID"),
            "source_sha256": src_sha,
            "rights_basis": provenance["rights_basis"],
            "source_note": label(provenance["source_note"], "provenance note", 180),
        },
        "status": status, "evidence": evidence,
        "limitations": label(profile.get("limitations"), "limitations", 500),
        "builds": builds,
    }


def save_technique(root, profile):
    """Save one immutable, non-replaceable profile; no raw reference pixels."""
    p = validate_technique(profile)
    base = Path(root).expanduser().resolve()
    if base.is_symlink():
        raise TaskError("Technique library may not be a symlink")
    base.mkdir(parents=True, exist_ok=True)
    target = base / (p["id"] + "--v%04d.json" % p["version"])
    raw = (json.dumps(p, sort_keys=True, ensure_ascii=False, indent=2,
                      allow_nan=False) + "\n").encode("utf-8")
    if len(raw) > 65536:
        raise TaskError("Technique profile exceeds 64 KiB")
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise TaskError("Technique version exists and cannot be overwritten") from exc
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"id": p["id"], "version": p["version"], "profile_sha256": digest(p),
            "file": target.name, "status": p["status"], "artwork_accepted": False}


def load_technique(root, identifier, version):
    from .protocol import integer
    key = _id(identifier, "ID")
    ver = integer(version, "technique version", 1, 9999)
    base = Path(root).expanduser().resolve()
    file = base / (key + "--v%04d.json" % ver)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > 65536:
        raise TaskError("Technique profile missing or unsafe")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TaskError("Unreadable technique profile") from exc
    normalized = validate_technique(data)
    if normalized["id"] != key or normalized["version"] != ver:
        raise TaskError("Technique identity does not match requested revision")
    return normalized


def list_techniques(root):
    base = Path(root).expanduser().resolve()
    if not base.exists():
        return []
    if not base.is_dir():
        raise TaskError("Technique library root is not a directory")
    result = []
    for file in sorted(base.glob("*--v*.json"))[:256]:
        if file.is_symlink():
            continue
        match = re.fullmatch(r"([a-z][a-z0-9_-]{0,23})--v([0-9]{4})\.json", file.name)
        if not match:
            continue
        p = load_technique(base, match.group(1), int(match.group(2)))
        result.append({"id": p["id"], "version": p["version"],
                       "title": p["title"], "materials": p["materials"],
                       "status": p["status"], "profile_sha256": digest(p)})
    return result


def propose_technique_application(scene, profile, subject_id, intent_id,
                                  *, build=None):
    """No native effect; changed v4 scene requires independent approval."""
    from .scene_v4 import compile_scene_v4
    source = validate_scene_v4(scene)
    technique = validate_technique(profile)
    if technique["builds"] and (not build or build not in technique["builds"]):
        raise TaskError("Technique was not characterized for requested Krita build")
    out = deepcopy(source)
    subject = next((s for s in out["subjects"] if s["id"] == subject_id), None)
    if subject is None:
        raise TaskError("Unknown technique subject")
    structure = out.get("structure") or {}
    if any(s["subject_id"] == subject_id and s["locked"]
           for s in structure.get("subjects", [])):
        raise TaskError("Technique would change user-locked subject")
    found = []
    for stage in out["stages"]:
        for intent in stage["intents"]:
            if intent["id"] != intent_id or intent["subject_id"] != subject_id:
                continue
            if not any(m in technique["materials"] for m in subject["materials"]):
                raise TaskError("Technique material is not declared for subject")
            if stage["phase"] not in technique["phases"] or intent["kind"] not in technique["intent_kinds"]:
                raise TaskError("Technique not supported at this phase/intent kind")
            intent["render"] = technique["render"]
            if technique["brush"]:
                intent["brush"] = {**intent.get("brush", {}), **technique["brush"]}
            found.append((stage["phase"], intent["id"]))
    if len(found) != 1:
        raise TaskError("Technique target must identify exactly one staged paint intent")
    candidate = validate_scene_v4(out)
    compiled = compile_scene_v4(candidate)
    return {
        "schema": "krita-agent-technique-application/1",
        "original_sha256": digest(source), "candidate_sha256": digest(candidate),
        "native_steps_sha256": compiled["native_steps_sha256"],
        "technique_sha256": digest(technique),
        "subject_id": subject_id, "intent_id": intent_id,
        "scene": candidate, "approval": "required", "native_effects": "none",
        "human_review_pending": True,
    }


def approve_technique_application(source, profile, proposal, *, confirm=False):
    from .scene_v4 import compile_scene_v4
    if confirm is not True:
        raise TaskError("Technique application requires explicit approval")
    if not isinstance(proposal, dict) or proposal.get("schema") != (
            "krita-agent-technique-application/1"):
        raise TaskError("Invalid technique proposal")
    if proposal.get("native_effects") != "none" or proposal.get("approval") != "required":
        raise TaskError("Technique proposal contains unauthorized native effects")
    original = validate_scene_v4(source)
    p = validate_technique(profile)
    candidate = validate_scene_v4(proposal["scene"])
    if (digest(original) != proposal.get("original_sha256") or
            digest(p) != proposal.get("technique_sha256") or
            digest(candidate) != proposal.get("candidate_sha256")):
        raise TaskError("Technique proposal changed since review")
    if compile_scene_v4(candidate)["native_steps_sha256"] != proposal.get("native_steps_sha256"):
        raise TaskError("Native technique compilation changed")
    return candidate
