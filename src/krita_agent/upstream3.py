"""Git SHA-based API inventory and explicit capability evidence registry.

This module reads only local checked-out KDE source. It never fetches,
executes upstream code, upgrades Krita or interprets source_seen as tested.
"""
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .upstream_semantics import suggest

SCOPES = ("libs/libkis/", "plugins/extensions/pykrita/")
MAX_FILES = 160
MAX_BYTES = 2000000
CPP_DECL = re.compile(r"(?m)^\s*(?:(?:virtual|static|Q_INVOKABLE|inline|explicit)\s+)*"
                      r"[\w:<>,*&\s]+\s+([A-Za-z_]\w*)\s*\(([^;{}]{0,400})\)\s*(?:const\s*)?;")


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, errors="replace", timeout=80, check=True).stdout.strip()


def _source(root, ref, path):
    result = subprocess.run(["git", "-C", str(root), "show", ref + ":" + path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=40, check=False)
    if result.returncode != 0:
        return ""
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("Upstream file exceeds source parser limit: " + path)
    return result.stdout.decode("utf-8", errors="replace")


def signatures(path, source):
    """Extract parseable Python signatures or heuristic C++ header declarations."""
    if not source:
        return {}
    if path.endswith(".py"):
        try:
            parsed = ast.parse(source)
        except SyntaxError:
            return {}
        result = {}
        for node in parsed.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[node.name] = ast.unparse(node.args)
            elif isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        result[node.name + "." + method.name] = ast.unparse(method.args)
        return result
    if path.endswith((".h", ".hpp")):
        return {name: re.sub(r"\s+", " ", params.strip())
                for name, params in CPP_DECL.findall(source)
                if name not in {"if", "while", "for", "switch"}}
    return {}


def catalog(repo, before, after="HEAD"):
    root = Path(repo).expanduser().resolve()
    old = git(root, "rev-parse", "--verify", before + "^{commit}")
    new = git(root, "rev-parse", "--verify", after + "^{commit}")
    changes = git(root, "diff", "--name-only", old, new, "--", *SCOPES).splitlines()
    paths = [path for path in changes if path.endswith((".py", ".h", ".hpp"))]
    if len(paths) > MAX_FILES:
        raise ValueError("Too many source files for one bounded inventory")
    records = []
    for path in paths:
        baseline = signatures(path, _source(root, old, path))
        current = signatures(path, _source(root, new, path))
        for key in sorted(set(baseline) | set(current)):
            old_sig = baseline.get(key)
            new_sig = current.get(key)
            if old_sig == new_sig:
                continue
            kind = ("added" if old_sig is None else "removed" if new_sig is None else "signature_changed")
            candidate = {"symbol": key, "file": path, "kind": kind,
                         "before": old_sig, "after": new_sig,
                         "source_url": "https://invent.kde.org/graphics/krita/-/blob/" + new + "/" + path,
                         "classification": "AST" if path.endswith(".py") else "heuristic_header",
                         "evidence": "source_seen"}
            candidate["impact"] = suggest(candidate)
            records.append(candidate)
    return {"repository": str(root), "baseline": old, "target": new,
            "scoped_paths": paths, "api_candidates": records,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "caveat": "Parsed signature delta is not proof of installed API or working behavior"}


def _load(path):
    path = Path(path)
    if not path.exists():
        return {"schema": 1, "entries": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or not isinstance(value.get("entries"), list):
        raise ValueError("Unknown capability evidence registry schema")
    return value


def registry_list(filename):
    return _load(filename)


def registry_record(filename, build, symbol, state, evidence_file, confirm=False):
    """Manual provenance registration; cannot infer runtime testing from source."""
    allowed = {"source_seen", "present_in_build", "not_supported", "tested_working"}
    if state not in allowed:
        raise ValueError("Unknown capability evidence state")
    if state == "tested_working" and confirm is not True:
        raise ValueError("Marking tested_working requires explicit reviewer confirmation")
    if not build or not symbol or len(build) > 120 or len(symbol) > 180:
        raise ValueError("Build and symbol must be named")
    evidence = Path(evidence_file).expanduser().resolve()
    if not evidence.is_file() or evidence.stat().st_size > 2000000:
        raise ValueError("Evidence file is missing or too large")
    h = hashlib.sha256(evidence.read_bytes()).hexdigest()
    registry = _load(filename)
    item = {"build": build, "symbol": symbol, "state": state,
            "evidence_path": str(evidence), "evidence_sha256": h,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "reviewer_confirmed": bool(confirm),
            "source": "manual_declared_evidence"}
    for old in registry["entries"]:
        if old.get("build") == build and old.get("symbol") == symbol:
            raise ValueError("Duplicate capability; revise explicitly rather than silently overwrite")
    registry["entries"].append(item)
    target = Path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as out:
        json.dump(registry, out, ensure_ascii=False, indent=2)
    return item


def save_catalog(data, filename):
    target = Path(filename).expanduser()
    if target.exists():
        raise FileExistsError("Catalog output exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(target)
