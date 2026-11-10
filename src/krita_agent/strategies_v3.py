"""Object-specific brush strategies; no fabricated visual-review results.

The input geometry comes from an explicit human/model ScenePlan. These
strategies tune native strokes and select only reviewed brush profiles.
"""
from .brush_profiles import choose
from .protocol import TaskError, brush_settings

CATEGORIES = {
    "sky": "paint", "sun": "paint", "cloud": "paint",
    "mountain": "texture", "forest": "texture", "tree": "texture",
    "lake": "paint", "water": "paint", "reflection": "paint",
    "rock": "texture", "plant": "sketch", "flower": "paint",
    "ground": "paint", "building": "ink", "object": "paint", "custom": "paint",
}
SIZES = {
    "sky": 100, "sun": 44, "cloud": 36, "mountain": 20, "forest": 14,
    "tree": 11, "lake": 22, "water": 12, "reflection": 13,
    "rock": 16, "plant": 8, "flower": 7, "ground": 25,
    "building": 6, "object": 14, "custom": 12,
}
PRESSURE = {
    "sky": (0.3, 0.5, 0.2), "sun": (0.6, 0.9, 0.6),
    "cloud": (0.28, 0.8, 0.18), "mountain": (0.65, 0.95, 0.4),
    "forest": (0.4, 0.9, 0.2), "tree": (0.3, 0.9, 0.2),
    "lake": (0.2, 0.55, 0.15), "water": (0.2, 0.5, 0.18),
    "reflection": (0.25, 0.55, 0.2), "rock": (0.45, 0.8, 0.3),
    "plant": (0.15, 0.75, 0.1), "flower": (0.2, 0.7, 0.2),
    "ground": (0.4, 0.9, 0.3), "building": (0.45, 0.65, 0.45),
    "object": (0.25, 0.7, 0.25), "custom": (0.25, 0.65, 0.25),
}


def brush_for_object(item, profile_directory=None, build=None):
    kind = item["kind"]
    brush = dict(item.get("brush", {}))
    brush.setdefault("size", SIZES[kind])
    brush.setdefault("opacity", 0.95)
    if "preset" not in brush and profile_directory is not None:
        if not build:
            raise TaskError("Selecting an evidence-backed brush requires a build")
        selected = choose(profile_directory, build, CATEGORIES[kind])
        brush["preset"] = selected["preset"]
        brush["pressure_enabled"] = bool(
            selected["pressure_size"] or selected["pressure_opacity"]
        )
    # No fallback preset is invented; without a reviewed profile or an explicit
    # preset, the active Krita brush is used and output depends on session state.
    return brush_settings(brush)


def strokes_for_object(item, profile_directory=None, build=None):
    """Resolve calibrated per-stroke presets without inventing capabilities.

    ScenePlan v3 normalizes sensor curves; this function changes only brush
    settings between strokes. Unknown/unreviewed categories fail closed.
    """
    result = []
    for source in item["elements"]:
        element = dict(source)
        category = element.pop("brush_category", None)
        if category is not None:
            if not profile_directory or not build:
                raise TaskError("Per-stroke brush category requires a reviewed build/profile directory")
            brush = dict(element.get("brush", {}))
            if "preset" in brush:
                raise TaskError("Specify either a calibrated category or an explicit preset")
            selected = choose(profile_directory, build, category)
            brush["preset"] = selected["preset"]
            brush["pressure_enabled"] = bool(
                selected["pressure_size"] or selected["pressure_opacity"]
            )
            element["brush"] = brush_settings(brush)
        result.append(element)
    return result
