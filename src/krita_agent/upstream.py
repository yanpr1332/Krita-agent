"""Read-only KDE upstream feature analysis, with explicit baseline/report writes."""
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

API_PATHS = ("libs/libkis", "plugins/extensions/pykrita", "plugins/paintops")
PATTERN = re.compile(r"\b([A-Za-z_]\w*)\s*\([^;]*")
INTERESTING = ("paint", "stroke", "pressure", "brush", "node", "document",
               "layer", "resource", "python", "plugin", "qt", "export", "save")


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60).stdout.strip()


def snapshot(repo):
    root = Path(repo).expanduser().resolve()
    return {"repository": str(root), "commit": _git(root, "rev-parse", "HEAD"),
            "branch": _git(root, "branch", "--show-current") or None,
            "dirty": bool(_git(root, "status", "--porcelain")),
            "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "evidence": "source snapshot only; runtime capabilities not verified"}


def compare(repo, baseline, target="HEAD"):
    root = Path(repo).expanduser().resolve()
    old = _git(root, "rev-parse", "--verify", baseline + "^{commit}")
    new = _git(root, "rev-parse", "--verify", target + "^{commit}")
    changed_files = _git(root, "diff", "--name-only", old, new, "--", *API_PATHS).splitlines()
    diff = _git(root, "diff", "--no-ext-diff", "--unified=0", old, new, "--", *API_PATHS)
    changes, current = [], None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif current and line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
            value = line[1:].strip()
            if not value or value.startswith(("//", "*", "#include", "/*")):
                continue
            match = PATTERN.search(value)
            if match and (current.endswith((".h", ".cpp", ".py"))):
                changes.append({"file": current, "kind": "added" if line[0] == "+" else "removed",
                                "symbol": match.group(1), "line": value[:500],
                                "source_url": "https://invent.kde.org/graphics/krita/-/blob/" + new + "/" + current})
    old_signatures = {}
    for item in changes:
        if item["kind"] == "removed":
            old_signatures.setdefault((item["file"], item["symbol"]), []).append(item)
    for item in changes:
        key = (item["file"], item["symbol"])
        if item["kind"] == "added" and key in old_signatures and old_signatures[key]:
            counterpart = old_signatures[key].pop(0)
            item["kind"] = "signature_or_implementation_changed"
            item["before"] = counterpart["line"]
            counterpart["paired"] = True
    changes = [item for item in changes if not item.pop("paired", False)]
    for item in changes:
        haystack = (item["file"] + item["symbol"] + item["line"]).lower()
        item["priority"] = "high" if any(k in haystack for k in ("stroke", "paint", "pressure", "libkis")) else "review"
        item["evidence"] = "source_seen"
        item["runtime"] = "not_probed"
        item["suggested_test"] = "Check API presence/signature on Stable and Next, then run isolated behavior test"
    commits = _git(root, "log", "--format=%h %s", "--max-count=30", old + ".." + new, "--", *API_PATHS).splitlines()
    return {"repository": str(root), "baseline": old, "target": new,
            "changed_files": changed_files, "commits": commits,
            "candidates": changes, "classification": "heuristic",
            "caveat": "Source sightings and diff heuristics are not proof of runtime support."}


def initialize(repo, baseline_file):
    data = snapshot(repo)
    target = Path(baseline_file).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("Baseline exists; refusing to overwrite: " + str(target))
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def check(repo, baseline_file, fetch=False, update=False):
    root = Path(repo).expanduser().resolve()
    if fetch:
        _git(root, "fetch", "--prune", "origin")
    saved = json.loads(Path(baseline_file).read_text(encoding="utf-8"))
    target_ref = ("origin/" + saved["branch"]) if fetch and saved.get("branch") else "HEAD"
    result = compare(root, saved["commit"], target_ref)
    result["baseline_file"] = str(baseline_file)
    if update:
        if result["baseline"] != result["target"]:
            replacement = snapshot(root)
            replacement["commit"] = result["target"]
            Path(baseline_file).write_text(
                json.dumps(replacement, ensure_ascii=False, indent=2), encoding="utf-8")
            result["baseline_updated"] = True
        else:
            result["baseline_updated"] = False
    return result


def markdown_report(result):
    lines = ["# Krita upstream change report", "",
             "- Baseline: " + str(result.get("baseline", "")),
             "- Target: " + str(result.get("target", "")),
             "- Classification: heuristic; source-only, not tested", "",
             "## Candidate API changes", ""]
    candidates = result.get("candidates", [])
    if not candidates:
        lines.append("No API signature candidates were identified in the scoped diff.")
    for item in candidates:
        lines += ["### " + item["kind"] + ": " + item["symbol"], "",
                  "- File: " + item["file"], "- Evidence: source_seen",
                  "- Priority: " + item["priority"],
                  "- Source: " + item["source_url"],
                  "- Line: " + item["line"], "- Suggested: " + item["suggested_test"], ""]
    lines += ["## Changed paths", ""] + ["- " + p for p in result.get("changed_files", [])]
    lines += ["", "## Relevant commits", ""] + ["- " + p for p in result.get("commits", [])]
    return "\n".join(lines) + "\n"


def capability_matrix(builds):
    """Convert runtime symbol probes to explicit NON-validated evidence states."""
    result = {}
    for build, probe in builds.items():
        result[build] = {}
        for name, present in probe.items():
            if type(present) is bool:
                result[build][name] = {
                    "state": "present_in_build" if present else "not_supported",
                    "tested_working": False}
    return result


def write_report(data, path):
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("Report exists; choose another filename: " + str(destination))
    content = markdown_report(data) if destination.suffix.lower() == ".md" else json.dumps(
        data, ensure_ascii=False, indent=2)
    destination.write_text(content, encoding="utf-8")
    return str(destination)
