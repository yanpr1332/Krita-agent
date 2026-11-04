"""Stable, inspectable document graphs; conservative matching after a KRA reload."""
import hashlib
import json
from pathlib import Path


def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def fingerprint(graph):
    if not isinstance(graph, dict) or graph.get("schema") != "krita-agent-document-graph/1":
        raise ValueError("Unknown document graph schema")
    return hashlib.sha256(canonical_json(graph).encode("utf-8")).hexdigest()


def save(graph, filename):
    fingerprint(graph)
    target = Path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(graph, ensure_ascii=False, indent=2))
    return str(target)


def rebind(before, after):
    """Propose ID mappings; conflicts do not silently resolve.

    Does not establish identity if two nodes have been reordered or renamed.
    Only exact structural paths, names and types can be mapped automatically.
    """
    fingerprint(before)
    fingerprint(after)
    if before["document"]["width"] != after["document"]["width"] or before["document"]["height"] != after["document"]["height"]:
        raise ValueError("Canvas dimensions differ")
    def key(node):
        return (tuple(node["path"]), node["name"], node["type"])
    old = {key(n): n for n in before["nodes"]}
    new = {key(n): n for n in after["nodes"]}
    proposals = []
    for entry, node in old.items():
        match = new.get(entry)
        proposals.append({"old_id": node["id"], "new_id": match["id"] if match else None,
                          "path": node["path"], "status": "candidate" if match else "ambiguous_or_missing"})
    return {"mapping": proposals, "note": "Review before using mappings for destructive edits."}


def changed_nodes(before, after):
    fingerprint(before)
    fingerprint(after)
    old = {tuple(n["path"]): n for n in before["nodes"]}
    new = {tuple(n["path"]): n for n in after["nodes"]}
    keys = sorted(set(old) | set(new))
    result = []
    for key in keys:
        a, b = old.get(key), new.get(key)
        if a != b:
            result.append({"path": list(key), "before": a, "after": b})
    return result
