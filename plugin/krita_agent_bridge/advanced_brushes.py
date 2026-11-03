"""Brush metadata catalogue without making claims about pressure response."""
from krita import Krita
from .advanced_utils import integer, word

COMMANDS = frozenset(("brush.profile", "brush.presets"))


def execute(bridge, command, p):
    resources = Krita.instance().resources("preset")
    if command == "brush.presets":
        query = p.get("query", "")
        query = word(query, "query").casefold() if query else ""
        limit = integer(p.get("limit", 200), "limit", 1, 500)
        rows = [{"name": r.name(), "key": k, "file": r.filename()}
                for k, r in resources.items() if query in r.name().casefold()]
        return {"total": len(rows), "presets": rows[:limit], "truncated": len(rows) > limit}
    name = word(p.get("name"), "preset")
    found = [r for r in resources.values() if r.name() == name]
    if len(found) != 1:
        raise ValueError("Preset name is absent or ambiguous")
    r = found[0]
    view = bridge._view()
    return {"name": r.name(), "file": r.filename(),
            "selected": bool(view.currentBrushPreset() and view.currentBrushPreset().name() == name),
            "view_brush_size": view.brushSize(), "view_opacity": view.paintingOpacity(),
            "pressure_disabled": view.disablePressure(),
            "capability": "resource_metadata_only",
            "note": "True pressure-size and opacity mapping requires actual preset inspection/test"}
