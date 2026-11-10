"""Safe per-stroke brush styles and deterministic pressure dynamics.

Style changes compile to existing Krita brush.configure commands *between*
native strokes. Within a continuous stroke, only supported sensor samples
(pressure/time/tilt/speed) vary. No fake in-stroke color/size IPC is invented.
"""
import math
import re

from .protocol import TaskError, brush_settings, integer, number, points

BRUSH_FIELDS = frozenset(("preset", "size", "opacity", "color", "pressure_enabled"))
STYLE_FIELDS = frozenset((
    "brush", "brush_category", "pressure_curve", "pressure_variation",
    "variation_frequency", "variation_seed", "speed_sensitivity",
    "pressure_interpolation",
))
ALIASES_MAX = 24


def validate_style(value):
    if not isinstance(value, dict):
        raise TaskError("Stroke style must be an object")
    unknown = set(value) - STYLE_FIELDS
    if unknown:
        raise TaskError("Unknown stroke-style fields: " + ", ".join(sorted(unknown)))
    result = {}
    if "brush" in value:
        raw = value["brush"]
        if not isinstance(raw, dict) or set(raw) - BRUSH_FIELDS:
            raise TaskError("Unknown or invalid stroke brush parameters")
        result["brush"] = brush_settings(raw)
    if "brush_category" in value:
        from .brush_profiles import CATEGORIES
        if not isinstance(value["brush_category"], str) or value["brush_category"] not in CATEGORIES:
            raise TaskError("Unknown stroke brush category")
        result["brush_category"] = value["brush_category"]
    if "pressure_curve" in value:
        raw = value["pressure_curve"]
        if not isinstance(raw, list) or not 2 <= len(raw) <= 24:
            raise TaskError("Pressure curve requires 2..24 control points")
        knots = []
        for pair in raw:
            if not isinstance(pair, list) or len(pair) != 2:
                raise TaskError("Pressure control point must be [position,pressure]")
            t = number(pair[0], "pressure curve position", 0, 1)
            v = number(pair[1], "pressure curve value", 0, 1)
            if knots and t <= knots[-1][0]:
                raise TaskError("Pressure curve positions must strictly increase")
            knots.append([t, v])
        if knots[0][0] != 0 or knots[-1][0] != 1:
            raise TaskError("Pressure curve must begin at 0 and end at 1")
        result["pressure_curve"] = knots
    if "pressure_variation" in value:
        result["pressure_variation"] = number(
            value["pressure_variation"], "pressure variation", 0, 0.3
        )
    if "variation_frequency" in value:
        result["variation_frequency"] = number(
            value["variation_frequency"], "variation frequency", 0.25, 32
        )
    if "variation_seed" in value:
        result["variation_seed"] = integer(
            value["variation_seed"], "variation seed", 0, 2147483647
        )
    if "speed_sensitivity" in value:
        result["speed_sensitivity"] = number(
            value["speed_sensitivity"], "speed sensitivity", 0, 1
        )
    if "pressure_interpolation" in value:
        if value["pressure_interpolation"] not in ("linear", "smooth"):
            raise TaskError("Pressure interpolation must be linear or smooth")
        result["pressure_interpolation"] = value["pressure_interpolation"]
    dynamics = STYLE_FIELDS - {"brush", "brush_category", "pressure_curve"}
    if any(key in result for key in dynamics) and "pressure_curve" not in result:
        raise TaskError("Pressure dynamics require an explicit pressure_curve")
    return result


def validate_palette(value):
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > ALIASES_MAX:
        raise TaskError("Style palette must have at most 24 named entries")
    result = {}
    for name, spec in value.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", name):
            raise TaskError("Invalid stroke style name")
        result[name] = validate_style(spec)
    return result


def combine_style(palette, element):
    """Resolve a named palette style, overridden by element-level settings."""
    name = element.get("style")
    if name is not None and (not isinstance(name, str) or name not in palette):
        raise TaskError("Unknown named stroke style")
    base = dict(palette.get(name, {}))
    direct = {key: element[key] for key in STYLE_FIELDS if key in element}
    merged = {**base, **direct}
    if "brush" in base or "brush" in direct:
        # A partial override changes only that setting, not the other fields
        # of the named style's brush.
        if "brush" in direct and not isinstance(direct["brush"], dict):
            raise TaskError("Stroke brush override must be an object")
        merged["brush"] = {**base.get("brush", {}), **direct.get("brush", {})}
    # Validate after composition so an element can override just the
    # variation/seeding of its palette's pre-existing pressure curve.
    return validate_style(merged)


def _pressure(knots, t, interpolation):
    for (lo_t, lo_v), (hi_t, hi_v) in zip(knots, knots[1:]):
        if t <= hi_t:
            u = (t - lo_t) / (hi_t - lo_t)
            if interpolation == "smooth":
                u = u*u*(3-2*u)
            return lo_v + (hi_v-lo_v)*u
    return knots[-1][1]


def pressure_samples(raw, default_envelope, style):
    """Resample pressure by arc length; explicit curve wins over raw pressures.

    Without a curve, retain every authored pressure and fill missing values
    using the object's historical semantic envelope (backward compatible).
    """
    normalized = points(raw)
    lengths = [0.0]
    for a, b in zip(normalized, normalized[1:]):
        lengths.append(lengths[-1] + math.hypot(b["x"] - a["x"], b["y"] - a["y"]))
    full = lengths[-1]
    knots = style.get("pressure_curve")
    if knots is None:
        initial, peak, final = default_envelope
        knots = [
            [0, initial],
            [0.18, 0.6*initial + 0.4*peak],
            [0.56, peak],
            [0.82, 0.35*peak + 0.65*final],
            [1, final],
        ]
    variation = style.get("pressure_variation", 0)
    freq = style.get("variation_frequency", 3)
    seed = style.get("variation_seed", 0)
    speed = style.get("speed_sensitivity", 0)
    interp = style.get("pressure_interpolation", "smooth")
    for i, (source, target) in enumerate(zip(raw, normalized)):
        if "pressure" in source and "pressure_curve" not in style:
            continue
        t = lengths[i] / full if full else i / max(1, len(raw)-1)
        value = _pressure(knots, t, interp)
        if variation:
            phase = 2*math.pi*freq*t + seed*0.61803398875
            ripple = 0.65*math.sin(phase) + 0.35*math.sin(phase*1.73 + 1.2)
            value += variation*ripple
        if speed:
            value *= 1 - speed*target["speed"]
        target["pressure"] = round(max(0, min(1, value)), 6)
    return normalized
