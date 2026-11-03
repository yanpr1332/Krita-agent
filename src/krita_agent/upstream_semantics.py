"""Best-effort upstream API change classification and test suggestions.

Uses only existing parsed source records; this does NOT execute upstream code.
"""
from collections import defaultdict


AREAS = {
    "brush_stroke": ("paint", "stroke", "pressure", "tilt", "brush"),
    "layers": ("node", "layer", "group", "opacity", "blend"),
    "documents": ("document", "canvas", "image", "export", "save"),
    "plugin_compatibility": ("pykrita", "qt", "python", "sip", "binding"),
    "selection": ("selection", "mask", "pixel"),
}
STATES = ("source_seen", "documented", "present_in_build", "tested_working", "not_supported")


def categorize(candidate):
    text = " ".join(str(candidate.get(k, "")) for k in ("file", "symbol", "line")).lower()
    return [area for area, markers in AREAS.items() if any(token in text for token in markers)] or ["other"]


def suggest(candidate):
    kind = candidate.get("kind", "changed")
    symbol = candidate.get("symbol", "unknown")
    area = categorize(candidate)
    priority = "high" if "brush_stroke" in area or kind == "removed" else "medium"
    scenarios = ["Check callable presence and signature in each installed Krita build",
                 "Verify behavior using a disposable KRA and compare output"]
    if "brush_stroke" in area:
        scenarios += ["Compare continuous/segmented outputs, pressure dynamics and undo count"]
    if "plugin_compatibility" in area:
        scenarios += ["Load Bridge separately in Qt5 and Qt6 installations"]
    if "layers" in area:
        scenarios += ["Check node order and editable layer preservation after KRA roundtrip"]
    return {"symbol": symbol, "kind": kind, "areas": area,
            "priority": priority, "source_url": candidate.get("source_url"),
            "state": "source_seen", "runtime_verified": False,
            "suggested_tests": scenarios}


def enrich(report, matrix=None):
    report = dict(report)
    report["impact"] = [suggest(row) for row in report.get("candidates", [])]
    report["capabilities_by_build"] = matrix or {}
    report["evidence_policy"] = "Source changes are only candidates; never mark tested_working without a real test."
    summary = defaultdict(int)
    for item in report["impact"]:
        for area in item["areas"]:
            summary[area] += 1
    report["summary_by_area"] = dict(summary)
    return report


def ingest_probes(named_probes):
    matrix = {}
    for name, report in named_probes.items():
        symbols = report.get("symbols", report)
        matrix[name] = {}
        for symbol, present in symbols.items():
            if type(present) is bool:
                matrix[name][symbol] = {"state": "present_in_build" if present else "not_supported",
                                        "runtime_verified": False}
    return matrix
